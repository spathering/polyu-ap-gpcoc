import asyncio
import ipaddress
import re
import threading
from dataclasses import dataclass
from urllib.parse import urlsplit

from aiohttp import web, ClientSession, ClientTimeout, DummyCookieJar, WSMsgType

PRIVATE = tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8'))


def local_ip(value):
    ip = ipaddress.ip_address(value)
    if ip.version != 4 or not any(ip in net for net in PRIVATE):
        raise ValueError('请选择明确的局域网 IPv4 或 127.0.0.1，不支持公网地址或 0.0.0.0')
    return str(ip)


@dataclass(frozen=True)
class Config:
    upstream: str = 'http://127.0.0.1:8765'
    bind: str = '127.0.0.1'
    port: int = 8877
    max_connections: int = 32

    def validate(self):
        u = urlsplit(self.upstream)
        if u.scheme != 'http' or u.hostname not in ('127.0.0.1', 'localhost') or u.username or u.password or u.path not in ('', '/') or u.query or u.fragment:
            raise ValueError('上游必须是真实本机宿主的 HTTP 根地址')
        if not 1 <= (u.port or 80) <= 65535 or not 1 <= int(self.port) <= 65535:
            raise ValueError('端口应为 1—65535')
        local_ip(self.bind)
        if self.bind == u.hostname and self.port == (u.port or 80):
            raise ValueError('网关不能指向自身')
        if not 1 <= self.max_connections <= 128:
            raise ValueError('连接上限应为 1—128')
        return self

    @property
    def url(self):
        return f'http://{self.bind}:{self.port}'


GET = re.compile(r'^/api/v1/(capabilities|me|view|contracts|catalog|admin|chat/members|receipts/[\w.-]+|assets/[\w.-]+|admin/artifacts/[\w.-]+)$')
POST = re.compile(r'^/api/v1/(login|logout|query|commands|calculate|preview|assets|backup|chat/history)$')
STATIC = re.compile(r'^/(?:|index\.html|[\w.-]+\.(?:js|css)|sdk/[\w./-]+)$')


class Gateway:
    """One owned thread/event loop. stop() never stops or opens the upstream Host."""
    def __init__(self, config):
        self.config = config.validate()
        self.thread = None
        self.loop = None
        self.ready = threading.Event()
        self.error = ''
        self.connections = 0
        self.requests = 0
        self.active_requests = 0
        self.sockets = set()

    @property
    def running(self):
        return bool(self.thread and self.thread.is_alive() and self.ready.is_set() and not self.error)

    def start(self):
        if self.thread and self.thread.is_alive():
            raise RuntimeError('网关已经启动')
        self.ready.clear()
        self.error = ''
        self.thread = threading.Thread(target=self._run, daemon=True, name='LAN gateway')
        self.thread.start()
        if not self.ready.wait(12):
            raise TimeoutError('网关启动超时')
        if self.error:
            raise RuntimeError(self.error)

    def stop(self):
        if self.loop and self.thread and self.thread.is_alive():
            self.loop.call_soon_threadsafe(self.stopping.set)
            self.thread.join(8)
            if self.thread.is_alive():
                raise TimeoutError('网关仍在停止中')

    def _run(self):
        try:
            asyncio.run(self._serve())
        except Exception as exc:
            self.error = str(exc)
        finally:
            self.ready.set()

    async def _serve(self):
        self.loop = asyncio.get_running_loop()
        self.stopping = asyncio.Event()
        app = web.Application(client_max_size=10 * 1024 * 1024)
        app.router.add_route('*', '/{tail:.*}', self.handle)
        self.session = ClientSession(cookie_jar=DummyCookieJar(), trust_env=False,
                                     timeout=ClientTimeout(total=30, connect=5), auto_decompress=False)
        runner = web.AppRunner(app, access_log=None, shutdown_timeout=2)
        try:
            # This is a compatibility/readiness check, not an authenticated login.
            async with self.session.get(self.config.upstream.rstrip('/') + '/api/v1/capabilities', allow_redirects=False) as r:
                if r.status != 200 or (await r.json()).get('protocolVersion') != 1:
                    raise ValueError('上游不是可用的协议 1 宿主')
            await runner.setup()
            await web.TCPSite(runner, self.config.bind, self.config.port).start()
            self.ready.set()
            await self.stopping.wait()
        finally:
            for socket in tuple(self.sockets):
                await socket.close(code=1001, message=b'gateway stopped')
            await runner.cleanup()
            await self.session.close()
            self.connections = 0

    async def handle(self, request):
        origin = self.config.url
        if request.host != origin.split('//')[1]:
            return web.json_response({'code': 'HOST_REJECTED'}, status=403)
        incoming = request.headers.get('Origin')
        is_ws = request.path == '/api/v1/connect'
        if (incoming and incoming != origin) or ((request.method != 'GET' or is_ws) and incoming != origin):
            return web.json_response({'code': 'ORIGIN_REJECTED'}, status=403)
        if '%' in request.raw_path.split('?')[0] or '..' in request.path.split('/'):
            return web.json_response({'code': 'PATH_REJECTED'}, status=403)
        if is_ws and request.method == 'GET':
            return await self.websocket(request)
        if not ((request.method == 'GET' and (GET.fullmatch(request.path) or STATIC.fullmatch(request.path))) or
                (request.method == 'POST' and POST.fullmatch(request.path))):
            return web.json_response({'code': 'ROUTE_NOT_EXPOSED'}, status=404)
        if self.active_requests >= self.config.max_connections:
            return web.json_response({'code': 'GATEWAY_BUSY'}, status=503)
        self.active_requests += 1
        self.requests += 1
        try:
            limit = 10 * 1024 * 1024 if request.path == '/api/v1/assets' else 65536
            data = bytearray()
            async for chunk in request.content.iter_chunked(8192):
                data.extend(chunk)
                if len(data) > limit:
                    return web.json_response({'code': 'LIMIT_EXCEEDED'}, status=413)
            headers = {k: v for k, v in request.headers.items() if k.lower() in
                       ('cookie', 'x-csrf-token', 'content-type', 'x-asset-name', 'x-asset-visibility')}
            headers['Origin'] = self.config.upstream.rstrip('/')
            async with self.session.request(request.method, self.config.upstream.rstrip('/') + request.path_qs,
                                            headers=headers, data=bytes(data), allow_redirects=False) as upstream:
                if 300 <= upstream.status < 400:
                    return web.json_response({'code': 'UPSTREAM_REDIRECT_REJECTED'}, status=502)
                payload = bytearray()
                async for chunk in upstream.content.iter_chunked(65536):
                    payload.extend(chunk)
                    if len(payload) > 16 * 1024 * 1024:
                        return web.json_response({'code': 'UPSTREAM_TOO_LARGE'}, status=502)
                response = web.Response(status=upstream.status, body=bytes(payload))
                for name in ('Content-Type', 'Content-Encoding', 'Content-Disposition'):
                    if name in upstream.headers:
                        response.headers[name] = upstream.headers[name]
                for cookie in upstream.headers.getall('Set-Cookie', []):
                    response.headers.add('Set-Cookie', cookie)
                response.headers['Cache-Control'] = 'no-store'
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['Content-Security-Policy'] = "default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
                return response
        except (TimeoutError, OSError, __import__('aiohttp').ClientError):
            return web.json_response({'code': 'UPSTREAM_UNAVAILABLE'}, status=502)
        finally:
            self.active_requests -= 1

    async def websocket(self, request):
        if self.connections >= self.config.max_connections:
            return web.json_response({'code': 'CONNECTION_LIMIT'}, status=503)
        self.connections += 1
        downstream = web.WebSocketResponse(max_msg_size=65536, heartbeat=20)
        upstream = None
        try:
            upstream = await self.session.ws_connect(self.config.upstream.rstrip('/') + '/api/v1/connect',
                headers={'Origin': self.config.upstream.rstrip('/'), 'Cookie': request.headers.get('Cookie', '')},
                max_msg_size=262144, heartbeat=20, compress=0)
            await downstream.prepare(request)
            self.sockets.add(downstream)

            async def relay(source, target):
                async for message in source:
                    if message.type == WSMsgType.TEXT:
                        await asyncio.wait_for(target.send_str(message.data), 5)
                    elif message.type == WSMsgType.BINARY:
                        await target.close(code=1003)
                        break
                await target.close(code=source.close_code or 1001)

            tasks = [asyncio.create_task(relay(upstream, downstream)), asyncio.create_task(relay(downstream, upstream))]
            try:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            return downstream
        except __import__('aiohttp').WSServerHandshakeError as exc:
            return web.json_response({'code': 'UPSTREAM_WS_REJECTED', 'upstreamStatus': exc.status}, status=403 if exc.status in (401, 403) else 502)
        except (TimeoutError, OSError, __import__('aiohttp').ClientError):
            if downstream.prepared:
                await downstream.close(code=1011)
                return downstream
            return web.json_response({'code': 'UPSTREAM_UNAVAILABLE'}, status=502)
        finally:
            self.sockets.discard(downstream)
            if upstream:
                await upstream.close()
            self.connections -= 1
