"""Host protocol client, independent of Tk and of host implementation."""
import copy
import http.cookiejar
import ipaddress
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from websockets.sync.client import connect


class APIError(Exception):
    def __init__(self, message, status=0):
        super().__init__(message)
        self.status = status


def endpoint(address):
    u = urllib.parse.urlsplit(address.strip())
    try:
        ip = ipaddress.ip_address(u.hostname) if u.hostname != 'localhost' else ipaddress.ip_address('127.0.0.1')
        allowed = ip.version == 4 and any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8'))
    except ValueError:
        allowed = False
    if not allowed or u.scheme != 'http' or u.username or u.password or u.path not in ('', '/') or u.query or u.fragment:
        raise APIError('请输入本机或可信局域网 IPv4 的 HTTP 根地址')
    if not 1 <= (u.port or 80) <= 65535:
        raise APIError('端口不正确')
    return f'http://{u.hostname}:{u.port or 80}'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Assembler:
    def __init__(self):
        self.parts = None
        self.id = None
        self.size = 0

    def feed(self, message):
        kind = message.get('type')
        if kind == 'reset':
            raise APIError('AUTH_RESET', 403)
        if kind == 'pong':
            return
        if kind == 'snapshot.begin':
            n = message.get('parts')
            if self.parts is not None or type(n) is not int or not 1 <= n <= 128 or not message.get('id'):
                raise APIError('SNAPSHOT_INVALID')
            self.id, self.parts, self.size = message['id'], [None] * n, 0
        elif kind == 'snapshot.part':
            i, data = message.get('index'), message.get('data')
            if self.parts is None or message.get('id') != self.id or type(i) is not int or not 0 <= i < len(self.parts) or self.parts[i] is not None or not isinstance(data, str):
                raise APIError('SNAPSHOT_INVALID')
            self.size += len(data.encode())
            if self.size > 2 * 1024 * 1024:
                raise APIError('SNAPSHOT_TOO_LARGE')
            self.parts[i] = data
        elif kind == 'snapshot.end':
            if self.parts is None or message.get('id') != self.id or None in self.parts:
                raise APIError('SNAPSHOT_INCOMPLETE')
            result = json.loads(''.join(self.parts))
            if not isinstance(result, dict):
                raise APIError('SNAPSHOT_INVALID')
            self.parts = None
            return result
        else:
            raise APIError('PROTOCOL_UNSUPPORTED')


class Client:
    def __init__(self, address):
        self.address = endpoint(address)
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPCookieProcessor(self.cookies))
        self.lock = threading.RLock()
        self.http_lock = threading.Lock()
        self.stop = threading.Event()
        self.csrf = ''
        self.view = None
        self.connected = False
        self.segment = 0
        self.error = ''
        self.fatal = False
        self.socket = None
        self.thread = None
        self.received_at = None

    def request(self, path, body=None, raw=None, headers=None, binary=False):
        if self.stop.is_set():
            raise APIError('连接已关闭')
        h = {'Origin': self.address, 'X-CSRF-Token': self.csrf, **(headers or {})}
        data = raw
        if body is not None:
            data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            h['Content-Type'] = 'application/json'
            if len(data) > 65536:
                raise APIError('命令超过 64 KiB')
        if raw is not None and len(raw) > 10 * 1024 * 1024:
            raise APIError('素材超过 10 MiB')
        req = urllib.request.Request(self.address + '/api/v1/' + path, data=data, headers=h)
        with self.http_lock:
            try:
                with self.opener.open(req, timeout=15) as r:
                    result = r.read(16 * 1024 * 1024 + 1)
                    if len(result) > 16 * 1024 * 1024:
                        raise APIError('响应过大')
                    return result if binary else json.loads(result)
            except urllib.error.HTTPError as exc:
                try:
                    code = json.loads(exc.read(65536)).get('code', f'HTTP_{exc.code}')
                except (ValueError, AttributeError):
                    code = f'HTTP_{exc.code}'
                raise APIError(code, exc.code) from None

    def _check(self, view):
        if view.get('role') != 'kp':
            raise APIError('需要 KP 权限', 403)
        if any(k not in view for k in ('roomId', 'runId', 'accountId', 'authorityEpoch', 'authorizationEpoch', 'entities', 'catalog')):
            raise APIError('PROTOCOL_UNSUPPORTED')

    def login(self, account, password):
        if self.request('capabilities').get('protocolVersion') != 1:
            raise APIError('PROTOCOL_UNSUPPORTED')
        self.csrf = self.request('login', {'loginName': account, 'password': password})['csrf']
        view = self.request('view')
        self._check(view)
        self.account = view['accountId']
        self.auth_epoch = view['authorizationEpoch']
        self.contracts = self.request('contracts')
        if self.contracts.get('protocolVersion') != 1 or not self.contracts.get('operations'):
            raise APIError('PROTOCOL_UNSUPPORTED')
        self.thread = threading.Thread(target=self._receive, daemon=True)
        self.thread.start()

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.view), self.segment, self.error, self.received_at

    def _receive(self):
        delay = .5
        while not self.stop.is_set():
            with self.lock:
                self.segment += 1
                self.view = None
                self.connected = False
            try:
                cookie = '; '.join(f'{c.name}={c.value}' for c in self.cookies)
                with connect(self.address.replace('http:', 'ws:') + '/api/v1/connect', origin=self.address,
                             additional_headers={'Cookie': cookie}, proxy=None, compression=None,
                             open_timeout=8, close_timeout=1, max_size=262144, max_queue=8) as ws:
                    self.socket = ws
                    parser = Assembler()
                    authority = None
                    while not self.stop.is_set():
                        try:
                            message = ws.recv(timeout=1)
                        except TimeoutError:
                            continue
                        result = parser.feed(json.loads(message))
                        if result is None:
                            continue
                        self._check(result)
                        if result['accountId'] != self.account or result['authorizationEpoch'] != self.auth_epoch:
                            raise APIError('AUTH_RESET', 403)
                        with self.lock:
                            if authority and authority != result['authorityEpoch']:
                                self.segment += 1
                            authority = result['authorityEpoch']
                            self.view = result
                            self.connected = True
                            self.error = ''
                            self.received_at = time.time()
                        delay = .5
            except APIError as exc:
                self.error = str(exc)
                if exc.status == 403:
                    self.fatal = True
                    self.stop.set()
            except Exception as exc:
                status = getattr(getattr(exc, 'response', None), 'status_code', None)
                self.error = ('WebSocket 路由不可用：请连接真实宿主或 LAN 网关，不要填写仅转发 HTTP 的网页端口'
                              if status in (404, 502) else f'实时连接中断，正在重连（{type(exc).__name__}）')
            finally:
                with self.lock:
                    self.socket = None
                    self.connected = False
                    self.view = None
            self.stop.wait(delay)
            delay = min(5, delay * 2)

    def admin(self):
        data = self.request('admin')
        view = self.request('view')
        self._check(view)
        if view['accountId'] != self.account or view['authorizationEpoch'] != self.auth_epoch:
            raise APIError('AUTH_RESET', 403)
        return data

    def envelope(self, op, args, tokens=None):
        view = self.snapshot()[0]
        if not self.connected or not view:
            raise APIError('未连接，不能提交')
        if op not in self.contracts['operations']:
            raise APIError('未知操作')
        return {'protocolVersion': 1, 'type': 'command', 'requestId': uuid.uuid4().hex, 'roomId': view['roomId'],
                'payload': {'commandId': uuid.uuid4().hex, 'authorityEpoch': view['authorityEpoch'],
                            'runId': view['runId'], 'catalogRevision': view['catalog']['revision'],
                            'rulesetRevision': view['catalog']['rulesetRevision'], 'expectedViews': tokens or {},
                            'op': op, 'args': copy.deepcopy(args)}}

    def close(self):
        self.stop.set()
        if self.socket:
            self.socket.close()
        with self.lock:
            self.connected = False
            self.view = None
        self.csrf = ''


def validate(schema, value, path='参数'):
    types = schema.get('type', [])
    types = [types] if isinstance(types, str) else types
    kind = 'null' if value is None else 'boolean' if isinstance(value, bool) else 'string' if isinstance(value, str) else 'object' if isinstance(value, dict) else 'array' if isinstance(value, list) else 'integer' if isinstance(value, int) else 'number'
    if types and kind not in types and not (kind == 'integer' and 'number' in types):
        raise APIError(f'{path} 类型应为 {types}')
    if 'enum' in schema and value not in schema['enum']:
        raise APIError(f'{path} 不在可选值中')
    if isinstance(value, str) and not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', 2**31):
        raise APIError(f'{path} 长度超限')
    if kind in ('integer', 'number') and not schema.get('minimum', -float('inf')) <= value <= schema.get('maximum', float('inf')):
        raise APIError(f'{path} 数值超限')
    if isinstance(value, dict):
        if len(value) > schema.get('maxProperties', 2**31) or any(k not in value for k in schema.get('required', [])):
            raise APIError(f'{path} 字段缺失或过多')
        for key, item in value.items():
            child = schema.get('properties', {}).get(key, schema.get('additionalProperties', {}))
            if child is False:
                raise APIError(f'{path} 未知字段 {key}')
            if isinstance(child, dict):
                validate(child, item, path + '.' + key)
    if isinstance(value, list):
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', 2**31):
            raise APIError(f'{path} 项数超限')
        if schema.get('uniqueItems') and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise APIError(f'{path} 不允许重复项')
        for item in value:
            validate(schema.get('items', {}), item, path + '[]')
