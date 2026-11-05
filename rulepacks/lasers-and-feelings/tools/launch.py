"""Independent local frontend and same-origin adapter for the existing host."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

sys.dont_write_bytecode = True
from package import PACK, bundle

ROOT = PACK.parents[1]
SLOTS = ('kp', 'player1', 'player2')


def handler(backend, origin):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, code, body, mime='application/json'):
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def handle_request(self):
            if self.headers.get('Host') != urllib.parse.urlsplit(origin).netloc:
                return self.respond(403, b'{"code":"HOST_REJECTED"}')
            incoming = self.headers.get('Origin')
            if incoming and incoming != origin:
                return self.respond(403, b'{"code":"ORIGIN_REJECTED"}')
            path = urllib.parse.urlsplit(self.path).path
            slot = None
            if path.startswith('/sessions/'):
                parts = path.split('/', 3)
                if len(parts) != 4 or parts[2] not in SLOTS:
                    return self.respond(404, b'{"code":"NOT_FOUND"}')
                slot = parts[2]
                path = '/' + parts[3]
            query = urllib.parse.urlsplit(self.path).query
            if path.startswith('/api/v1/'):
                if self.command == 'POST' and incoming != origin:
                    return self.respond(403, b'{"code":"ORIGIN_REQUIRED"}')
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    return self.respond(400, b'{"code":"BAD_LENGTH"}')
                if size < 0 or size > 10 * 1024 * 1024 or self.headers.get('Transfer-Encoding'):
                    return self.respond(413, b'{"code":"REQUEST_TOO_LARGE"}')
                headers = {'Origin': backend}
                for key in ('X-CSRF-Token', 'Content-Type'):
                    if self.headers.get(key):
                        headers[key] = self.headers[key]
                cookies = SimpleCookie()
                cookies.load(self.headers.get('Cookie', ''))
                prefix = f'lf_slot_{slot}__' if slot else ''
                # A slot is a cookie namespace, never an account identity.
                forwarded = SimpleCookie()
                for name, morsel in cookies.items():
                    if slot and name.startswith(prefix):
                        forwarded[name[len(prefix):]] = morsel.value
                    elif not slot and not name.startswith('lf_slot_'):
                        forwarded[name] = morsel.value
                if forwarded:
                    headers['Cookie'] = '; '.join(m.OutputString() for m in forwarded.values())
                req = urllib.request.Request(backend + path + ('?' + query if query else ''),
                    data=self.rfile.read(size) if self.command == 'POST' else None,
                    headers=headers, method=self.command)
                try:
                    response = urllib.request.urlopen(req, timeout=25)
                except urllib.error.HTTPError as e:
                    response = e
                except OSError:
                    return self.respond(502, b'{"code":"HOST_UNAVAILABLE"}')
                with response:
                    body = response.read()
                    self.send_response(response.code)
                    self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    for cookie in response.headers.get_all('Set-Cookie', []):
                        if slot:
                            parsed = SimpleCookie()
                            parsed.load(cookie)
                            for name, morsel in parsed.items():
                                scoped = SimpleCookie()
                                scoped[prefix + name] = morsel.value
                                for key, value in morsel.items():
                                    if value and key not in ('path', 'domain'):
                                        scoped[prefix + name][key] = value
                                scoped[prefix + name]['path'] = f'/sessions/{slot}/'
                                self.send_header('Set-Cookie', scoped[prefix + name].OutputString())
                        else:
                            self.send_header('Set-Cookie', cookie)
                    self.end_headers()
                    try:
                        self.wfile.write(body)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        pass
                return
            if self.command != 'GET':
                return self.respond(405, b'{"code":"METHOD_NOT_ALLOWED"}')
            if path == '/package/bundle.json':
                return self.respond(200, json.dumps(bundle(), ensure_ascii=False).encode())
            if path == '/package/data.json':
                return self.respond(200, (PACK / 'config/lf.json').read_bytes())
            static = {'/': ('ui/index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('ui/app.js', 'text/javascript; charset=utf-8'),
                      '/styles.css': ('ui/styles.css', 'text/css; charset=utf-8'),
                      '/original.pdf': ('sources/lasers-and-feelings-original.pdf', 'application/pdf')}
            if path not in static:
                return self.respond(404, b'{"code":"NOT_FOUND"}')
            file, mime = static[path]
            return self.respond(200, (PACK / file).read_bytes(), mime)
    return Handler


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description='启动《激光与情感》独立桌面')
    parser.add_argument('--data-dir', type=Path, default=PACK / 'runtime/room')
    parser.add_argument('--port', type=int, default=8877)
    parser.add_argument('--backend-port', type=int, default=0)
    parser.add_argument('--backend', help='连接已启动的本机宿主，使用 http://127.0.0.1:端口')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    data = args.data_dir.resolve()
    if data.is_relative_to(ROOT / 'engineering'):
        parser.error('配置包运行数据必须放在 engineering/ 外')
    origin = f'http://127.0.0.1:{args.port}'
    backend = args.backend
    process = None
    server = None
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        if backend:
            parsed = urllib.parse.urlsplit(backend)
            if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.path not in ('', '/') or parsed.username or parsed.query or parsed.fragment:
                parser.error('--backend 必须是无额外路径的本机 http://127.0.0.1:端口')
            backend = backend.rstrip('/')
        else:
            command = [sys.executable, '-B', str(ROOT / 'engineering/backend/scripts/run.py'), '--data-dir', str(data)]
            if not data.exists():
                print('首次创建独立存档。请按宿主提示设置账号密码。', flush=True)
                subprocess.run(command + ['init'], env=env, check=True)
            backend = f'http://127.0.0.1:{args.backend_port or free_port()}'
            process = subprocess.Popen(command + ['serve', '--port', str(urllib.parse.urlsplit(backend).port)], env=env)
        for _ in range(100):
            try:
                with urllib.request.urlopen(backend + '/api/v1/capabilities', timeout=1):
                    break
            except OSError:
                if process and process.poll() is not None:
                    raise RuntimeError('宿主启动失败，请检查其输出')
                time.sleep(.1)
        else:
            raise RuntimeError('未能连接宿主')
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(backend, origin))
        server.daemon_threads = True
        print('跑团桌面：' + origin + '（Ctrl+C 停止；数据保留）', flush=True)
        if not args.no_browser:
            webbrowser.open(origin)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.server_close()
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    main()
