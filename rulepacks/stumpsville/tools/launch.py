"""Local package server. Uses only public host CLI and HTTP/WebSocket APIs."""
import argparse
import asyncio
from contextlib import asynccontextmanager
from http.cookies import SimpleCookie
import ipaddress
import json
import logging
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
import webbrowser

sys.dont_write_bytecode = True
import httpx
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import Response
import uvicorn
import websockets

from client import Client, HostError
from package import PACK, Package, PackageError, bundle

ROOT = PACK.parents[1]
SLOTS = re.compile(r'[a-zA-Z0-9_-]{1,40}')
STATIC = {'': ('ui/index.html', 'text/html; charset=utf-8'),
          'app.js': ('ui/app.js', 'text/javascript; charset=utf-8'),
          'styles.css': ('ui/styles.css', 'text/css; charset=utf-8')}


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def slot_path(path):
    if path.startswith('sessions/'):
        parts = path.split('/', 2)
        if len(parts) != 3 or not SLOTS.fullmatch(parts[1]):
            raise PackageError('入口不存在')
        return parts[1], parts[2]
    return None, path


def forwarded_cookie(header, slot):
    cookies = SimpleCookie()
    cookies.load(header)
    prefix = 'sv_' + slot + '__' if slot else ''
    values = []
    for name, morsel in cookies.items():
        if slot and name.startswith(prefix):
            values.append(name[len(prefix):] + '=' + morsel.coded_value)
        elif slot is None and not name.startswith('sv_'):
            values.append(name + '=' + morsel.coded_value)
    return '; '.join(values)


class Runtime:
    def __init__(self, args):
        self.args = args
        self.data = args.data_dir.resolve()
        if self.data.is_relative_to(ROOT / 'engineering'):
            raise ValueError('运行存档应位于 engineering 目录外')
        self.data.mkdir(parents=True, exist_ok=True)
        self.lock = (self.data / 'package.lock').open('a+b')
        self.lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            if self.lock.read(1) == b'':
                self.lock.write(b'0')
                self.lock.flush()
            self.lock.seek(0)
            msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.package = Package(self.data / 'package.json')
        self.host_data = self.data / 'host'
        self.backend = 'http://127.0.0.1:' + str(args.backend_port or free_port())
        self.origin = f'http://{args.bind}:{args.port}'
        self.process = None
        self.log = None
        self.setup_lock = asyncio.Lock()
        self.command = [sys.executable, '-B', str(ROOT / 'engineering/backend/scripts/run.py'), '--data-dir', str(self.host_data)]
        self.env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

    def start(self):
        if self.process and self.process.poll() is None:
            return
        if not self.host_data.exists():
            return
        if self.log:
            self.log.close()
        self.log = (self.data / 'host.log').open('a', encoding='utf-8')
        self.process = subprocess.Popen(self.command + ['serve', '--port', self.backend.rsplit(':', 1)[1]],
                                        env=self.env, stdout=self.log, stderr=self.log,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for _ in range(150):
            if self.process.poll() is not None:
                raise RuntimeError('宿主启动失败，请查看运行目录 host.log')
            try:
                with urllib.request.urlopen(self.backend + '/api/v1/capabilities', timeout=.5):
                    return
            except OSError:
                time.sleep(.1)
        raise RuntimeError('宿主连接超时')

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)
        if self.log:
            self.log.close()
        self.lock.close()

    def setup(self, password):
        if self.host_data.exists():
            raise PackageError('存档已经存在')
        if not isinstance(password, str) or not 8 <= len(password) <= 128:
            raise PackageError('密码应为8至128位')
        subprocess.run(self.command + ['init'], env={**self.env, 'ONLINECOC_BOOTSTRAP_PASSWORD': password},
                       check=True, capture_output=True, timeout=45,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.start()
        client = Client(self.backend, 'kp', password)
        try:
            self.package.action(client, {'id': 'initial-install-0001', 'operation': 'initialize', 'args': {}})
        finally:
            client.request('/logout', {})

    def client(self, cookie):
        client = Client.__new__(Client)
        client.base = self.backend
        client.csrf = None
        client.opener = urllib.request.build_opener()
        client.opener.addheaders = [('Cookie', cookie)]
        client.csrf = client.request('/me')['csrf']
        return client


def create_app(runtime):
    @asynccontextmanager
    async def lifespan(app):
        await asyncio.to_thread(runtime.start)
        yield
        runtime.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    def response(value, status=200, mime='application/json'):
        body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
        return Response(body, status_code=status, media_type=mime, headers={
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"})

    def check_origin(headers, write=False):
        if headers.get('host') != runtime.origin.split('//')[1]:
            raise PackageError('HOST_REJECTED')
        origin = headers.get('origin')
        if (origin and origin != runtime.origin) or (write and origin != runtime.origin):
            raise PackageError('ORIGIN_REJECTED')

    @app.api_route('/{path:path}', methods=['GET', 'POST'])
    async def handle(path, request: Request):
        try:
            check_origin(request.headers, request.method == 'POST')
            slot, path = slot_path(path)
            if '%' in path or '..' in path or '\\' in path:
                return response({'code': 'NOT_FOUND'}, 404)
            cookie = forwarded_cookie(request.headers.get('cookie', ''), slot)
            body = await request.body()
            if len(body) > 10 * 1024 * 1024:
                return response({'code': 'REQUEST_TOO_LARGE'}, 413)
            if path == 'setup/status':
                return response({'ready': bool(runtime.process and runtime.process.poll() is None), 'canSetup': not runtime.host_data.exists()})
            if path == 'setup' and request.method == 'POST':
                if request.client.host not in {'127.0.0.1', '::1'}:
                    return response({'code': '首次准备请在本机完成'}, 403)
                async with runtime.setup_lock:
                    await asyncio.to_thread(runtime.setup, json.loads(body).get('password'))
                return response({'ready': True})
            if path.startswith('api/v1/'):
                if path.startswith('api/v1/host-control'):
                    return response({'code': 'NOT_FOUND'}, 404)
                headers = {'Origin': runtime.backend, 'Cookie': cookie}
                for key in ('content-type', 'x-csrf-token'):
                    if request.headers.get(key):
                        headers[key] = request.headers[key]
                async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as upstream:
                    result = await upstream.request(request.method, runtime.backend + '/' + path,
                        params=request.query_params, content=body, headers=headers)
                output = response(result.content, result.status_code, result.headers.get('content-type', 'application/json'))
                for raw in result.headers.get_list('set-cookie'):
                    if not slot:
                        output.headers.append('set-cookie', raw)
                        continue
                    cookies = SimpleCookie()
                    cookies.load(raw)
                    for name, morsel in cookies.items():
                        scoped = SimpleCookie()
                        scoped['sv_' + slot + '__' + name] = morsel.value
                        target = scoped['sv_' + slot + '__' + name]
                        for key, value in morsel.items():
                            if value and key not in {'path', 'domain'}:
                                target[key] = value
                        target['path'] = '/sessions/' + slot + '/'
                        output.headers.append('set-cookie', target.OutputString())
                return output
            if path.startswith('package/'):
                client = await asyncio.to_thread(runtime.client, cookie)
                if request.method == 'POST' and request.headers.get('x-csrf-token') != client.csrf:
                    return response({'code': 'CSRF_REQUIRED'}, 403)
                if path == 'package/state' and request.method == 'GET':
                    result = await asyncio.to_thread(runtime.package.projection, client, request.query_params.get('preview'))
                    return response(result)
                if path == 'package/scene-executor' and request.method == 'POST':
                    return response(await asyncio.to_thread(runtime.package.scene_executor, client))
                if path == 'package/action' and request.method == 'POST':
                    if len(body) > 65536:
                        return response({'code': 'REQUEST_TOO_LARGE'}, 413)
                    return response(await asyncio.to_thread(runtime.package.action, client, json.loads(body)))
                if path == 'package/bundle' and request.method == 'GET':
                    view = await asyncio.to_thread(client.request, '/view')
                    if view['role'] != 'kp':
                        return response({'code': 'KP_REQUIRED'}, 403)
                    content = bundle()
                    active = runtime.package.state.get('activeRevision')
                    if active in runtime.package.state['ruleRevisions']:
                        content.update(runtime.package.state['ruleRevisions'][active])
                    return response(content)
                return response({'code': 'NOT_FOUND'}, 404)
            if request.method != 'GET':
                return response({'code': 'METHOD_NOT_ALLOWED'}, 405)
            if path in STATIC:
                filename, mime = STATIC[path]
                return response((PACK / filename).read_bytes(), mime=mime)
            if path.startswith('art/') and path[4:] in {'welcome.png', 'courtyard.png', 'mouse.png'}:
                file = PACK / 'assets/runtime' / path[4:]
                if file.is_file():
                    return response(file.read_bytes(), mime='image/png')
            return response({'code': 'NOT_FOUND'}, 404)
        except urllib.error.HTTPError as error:
            return response({'code': '登录失效，请重新登录'}, error.code)
        except HostError as error:
            return response(error.response, error.response.get('httpStatus', 409))
        except (PackageError, ValueError, KeyError, TypeError) as error:
            return response({'code': str(error)}, 400)
        except (OSError, httpx.HTTPError):
            logging.getLogger('stumpsville').exception('Local host request failed')
            return response({'code': '主机连接失败，请恢复原行动'}, 503)

    @app.websocket('/{path:path}')
    async def websocket_proxy(socket: WebSocket, path):
        try:
            check_origin(socket.headers, True)
            slot, path = slot_path(path)
            if path != 'api/v1/connect':
                await socket.close(code=1008)
                return
            cookie = forwarded_cookie(socket.headers.get('cookie', ''), slot)
            uri = runtime.backend.replace('http://', 'ws://') + '/api/v1/connect'
            async with websockets.connect(uri, origin=runtime.backend, additional_headers={'Cookie': cookie}, max_size=2**21) as upstream:
                await socket.accept()

                async def incoming():
                    while True:
                        await upstream.send(await socket.receive_text())

                async def outgoing():
                    async for message in upstream:
                        await socket.send_text(message)

                tasks = {asyncio.create_task(incoming()), asyncio.create_task(outgoing())}
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            try:
                await socket.close(code=1011)
            except RuntimeError:
                pass

    return app


def main():
    parser = argparse.ArgumentParser(description='树桩镇配置包')
    parser.add_argument('--data-dir', type=Path, default=PACK / 'runtime')
    parser.add_argument('--port', type=int, default=8899)
    parser.add_argument('--backend-port', type=int, default=0)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    address = ipaddress.ip_address(args.bind)
    if address.version != 4 or not (address.is_loopback or (address.is_private and not address.is_unspecified)):
        parser.error('绑定地址应为明确的本机或可信局域网 IPv4')
    runtime = Runtime(args)
    print('树桩镇 ' + runtime.origin, flush=True)
    if not args.no_browser:
        import threading
        timer = threading.Timer(1.5, webbrowser.open, args=(runtime.origin,))
        timer.daemon = True
        timer.start()
    uvicorn.run(create_app(runtime), host=args.bind, port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
