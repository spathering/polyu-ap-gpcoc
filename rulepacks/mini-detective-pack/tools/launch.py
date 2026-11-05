"""Independent local frontend and same-origin adapter for the existing host."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import threading
import signal
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

sys.dont_write_bytecode = True
from package import PACK, bundle, prepare_presets
from client import Client
from automation import Automation, ActionError

ROOT = PACK.parents[1]
SLOTS = ('kp', 'player1', 'player2', 'player3', 'player4')


def handler(backend, origin, setup=None, shutdown=None, automation=None):
    preset_lock=threading.Lock()
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
            if path == '/launcher/info' and self.command == 'GET':
                workspace=hashlib.sha256(str(PACK.resolve()).casefold().encode('utf-8')).hexdigest()
                return self.respond(200,json.dumps({'packId':'mini-detective-pack','workspace':workspace,'supervisorPid':int(os.environ.get('MD_LAUNCHER_PID','0')),'pid':os.getpid()}).encode())
            if path == '/setup/status' and self.command == 'GET':
                ready=False
                try:
                    with urllib.request.urlopen(backend+'/api/v1/capabilities',timeout=1): ready=True
                except OSError: pass
                return self.respond(200,json.dumps({'ready':ready,'canSetup':setup is not None}).encode())
            if path == '/setup' and self.command == 'POST':
                if incoming != origin: return self.respond(403,b'{"code":"ORIGIN_REQUIRED"}')
                if not setup: return self.respond(409,b'{"code":"SETUP_UNAVAILABLE"}')
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if size<1 or size>4096: raise ValueError('INVALID_SIZE')
                    password=json.loads(self.rfile.read(size)).get('password','')
                    if not isinstance(password,str) or len(password)<8 or len(password)>128: raise ValueError('PASSWORD_LENGTH_8_128')
                    setup(password)
                except Exception as e:
                    return self.respond(400,json.dumps({'code':str(e)},ensure_ascii=False).encode())
                return self.respond(200,b'{"ready":true}')
            slot = None
            if path.startswith('/sessions/'):
                parts = path.split('/', 3)
                if len(parts) != 4 or parts[2] not in SLOTS:
                    return self.respond(404, b'{"code":"NOT_FOUND"}')
                slot = parts[2]
                path = '/' + parts[3]
            query = urllib.parse.urlsplit(self.path).query
            if path in ('/package/automation', '/package/action'):
                if not automation: return self.respond(409, b'{"code":"AUTOMATION_UNAVAILABLE"}')
                cookies = SimpleCookie(); cookies.load(self.headers.get('Cookie', ''))
                forwarded = SimpleCookie(); prefix = f'md_slot_{slot}__' if slot else ''
                for name, morsel in cookies.items():
                    if slot and name.startswith(prefix): forwarded[name[len(prefix):]] = morsel.value
                    elif not slot and not name.startswith('md_slot_'): forwarded[name] = morsel.value
                opener = urllib.request.build_opener()
                opener.addheaders = [('Cookie', '; '.join(m.OutputString() for m in forwarded.values()))]
                try:
                    with opener.open(backend + '/api/v1/me', timeout=5) as r: me = json.load(r)
                    with opener.open(backend + '/api/v1/view', timeout=5) as r: caller = json.load(r)
                    if path.endswith('/action') or self.command == 'POST':
                        if self.command != 'POST' or incoming != origin or self.headers.get('X-CSRF-Token') != me['csrf']:
                            return self.respond(403, b'{"code":"CSRF_REQUIRED"}')
                        size = int(self.headers.get('Content-Length', '0'))
                        if size < 1 or size > 8192 or self.headers.get('Transfer-Encoding'):
                            return self.respond(413, b'{"code":"REQUEST_TOO_LARGE"}')
                        body = json.loads(self.rfile.read(size))
                        if path.endswith('/action'):
                            result = automation.action(caller, body)
                        else:
                            if caller['role'] != 'kp': return self.respond(403, b'{"code":"KP_REQUIRED"}')
                            if not isinstance(body, dict) or set(body) != {'enabled'}: raise ActionError('开关请求格式不正确')
                            result = automation.set_enabled(caller, body['enabled'])
                    else:
                        if self.command != 'GET': return self.respond(405, b'{}')
                        with opener.open(backend + '/api/v1/chat/members', timeout=5) as r: caller['_members'] = json.load(r)['items']
                        result = automation.status(caller)
                    return self.respond(200, json.dumps(result, ensure_ascii=False).encode())
                except urllib.error.HTTPError as e:
                    return self.respond(e.code, b'{"code":"LOGIN_REQUIRED"}')
                except (ActionError, ValueError) as e:
                    return self.respond(400, json.dumps({'code': str(e)}, ensure_ascii=False).encode())
                except Exception:
                    return self.respond(503, json.dumps({'code': '行动结果待确认，请恢复原行动；必要时请 KP 重新登录'}, ensure_ascii=False).encode())
            if path in ('/package/presets','/package/shutdown'):
                if self.command!='POST' or incoming!=origin: return self.respond(403,b'{"code":"ORIGIN_REQUIRED"}')
                cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''))
                prefix=f'md_slot_{slot}__' if slot else '';forwarded=SimpleCookie()
                for name,m in cookies.items():
                    if slot and name.startswith(prefix):forwarded[name[len(prefix):]]=m.value
                    elif not slot and not name.startswith('md_slot_'):forwarded[name]=m.value
                cookie='; '.join(m.OutputString() for m in forwarded.values())
                opener=urllib.request.build_opener();opener.addheaders=[('Cookie',cookie)]
                try:
                    with opener.open(backend+'/api/v1/me',timeout=5) as r:me=json.load(r)
                    with opener.open(backend+'/api/v1/view',timeout=5) as r:view=json.load(r)
                    if view['role']!='kp' or self.headers.get('X-CSRF-Token')!=me['csrf']: return self.respond(403,b'{"code":"KP_OR_CSRF_REQUIRED"}')
                    if path.endswith('shutdown'):
                        if not shutdown:return self.respond(409,b'{"code":"EXTERNAL_HOST"}')
                        self.respond(200,b'{"stopping":true}')
                        threading.Thread(target=shutdown,daemon=True).start();return
                    c=Client.__new__(Client);c.base=backend;c.csrf=me['csrf'];c.opener=opener
                    with preset_lock:result=prepare_presets(c)
                    return self.respond(200,json.dumps({'bindings':result},ensure_ascii=False).encode())
                except urllib.error.HTTPError as e:return self.respond(e.code,b'{"code":"AUTHENTICATION_REQUIRED"}')
                except Exception:return self.respond(500,b'{"code":"PRESET_PREPARATION_FAILED"}')
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
                prefix = f'md_slot_{slot}__' if slot else ''
                # A slot is a cookie namespace, never an account identity.
                forwarded = SimpleCookie()
                for name, morsel in cookies.items():
                    if slot and name.startswith(prefix):
                        forwarded[name[len(prefix):]] = morsel.value
                    elif not slot and not name.startswith('md_slot_'):
                        forwarded[name] = morsel.value
                if forwarded:
                    headers['Cookie'] = '; '.join(m.OutputString() for m in forwarded.values())
                request_body = self.rfile.read(size) if self.command == 'POST' else None
                req = urllib.request.Request(backend + path + ('?' + query if query else ''),
                    data=request_body,
                    headers=headers, method=self.command)
                try:
                    response = urllib.request.urlopen(req, timeout=25)
                except urllib.error.HTTPError as e:
                    response = e
                except OSError:
                    return self.respond(502, b'{"code":"HOST_UNAVAILABLE"}')
                with response:
                    body = response.read()
                    if automation and path == '/api/v1/login' and response.code == 200:
                        # A distinct session survives closing/logging out the human tab.
                        # Password exists only for this request; only the session is encrypted.
                        try:
                            login = json.loads(request_body)
                            c = Client(backend, login['loginName'], login['password'])
                            if c.request('/view')['role'] == 'kp': automation.attach(c)
                            else: c.request('/logout', {})
                        except Exception:
                            pass
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
            if path in ('/package/bundle.json', '/package/public.json'):
                cookies = SimpleCookie(); cookies.load(self.headers.get('Cookie', ''))
                prefix = f'md_slot_{slot}__' if slot else ''
                forwarded = SimpleCookie()
                for name, morsel in cookies.items():
                    if slot and name.startswith(prefix): forwarded[name[len(prefix):]] = morsel.value
                    elif not slot and not name.startswith('md_slot_'): forwarded[name] = morsel.value
                cookie = '; '.join(m.OutputString() for m in forwarded.values())
                try:
                    req = urllib.request.Request(backend + '/api/v1/view',headers={'Cookie':cookie})
                    with urllib.request.urlopen(req,timeout=5) as r: view=json.load(r)
                except urllib.error.HTTPError:
                    return self.respond(401,b'{"code":"LOGIN_REQUIRED"}')
                if path.endswith('bundle.json'):
                    if view.get('role') != 'kp': return self.respond(403,b'{"code":"KP_REQUIRED"}')
                    return self.respond(200,json.dumps(bundle(),ensure_ascii=False).encode())
                data=json.loads((PACK/'config/scenario.json').read_text(encoding='utf-8'))
                # Only initial public names are supplied; hidden room names never leave this endpoint.
                public_ids={'loc-hall','loc-mudroom','loc-lounge','loc-dining','loc-kitchen','loc-living','loc-library','loc-music','loc-projector','loc-steward','loc-store','loc-bath','loc-sauna','loc-shore'}
                safe={k:data[k] for k in ('attributeKeys','attributeNames','slots','presets') if k in data}
                safe['locations']=[{'id':x['id'],'name':x['name'],'index':i+1} for i,x in enumerate(data['locations']) if x['id'] in public_ids]
                return self.respond(200,json.dumps(safe,ensure_ascii=False).encode())
            if path.startswith('/assets/'):
                file=(PACK/path.lstrip('/')).resolve()
                if not file.is_relative_to((PACK/'assets').resolve()) or not file.is_file(): return self.respond(404,b'{}')
                if file.suffix not in ('.svg','.png') and file.name!='CREDITS.md': return self.respond(404,b'{}')
                mime='image/svg+xml' if file.suffix=='.svg' else 'image/png' if file.suffix=='.png' else 'application/json' if file.suffix=='.json' else 'text/plain; charset=utf-8'
                return self.respond(200,file.read_bytes(),mime)
            static = {'/': ('ui/index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('ui/app.js', 'text/javascript; charset=utf-8'),
                      '/workflow.js': ('ui/workflow.js', 'text/javascript; charset=utf-8'),
                      '/styles.css': ('ui/styles.css', 'text/css; charset=utf-8'),
                      '/credits': ('assets/placeholders/CREDITS.md', 'text/plain; charset=utf-8')}
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
    parser = argparse.ArgumentParser(description='启动《铃蔓回转录》独立桌面')
    parser.add_argument('--data-dir', type=Path, default=PACK / 'runtime/room')
    parser.add_argument('--port', type=int, default=8888)
    parser.add_argument('--backend-port', type=int, default=0)
    parser.add_argument('--backend', help='连接已启动的本机宿主，使用 http://127.0.0.1:端口')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
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
            backend = f'http://127.0.0.1:{args.backend_port or free_port()}'
            if data.exists():
                process = subprocess.Popen(command + ['serve', '--port', str(urllib.parse.urlsplit(backend).port)], env=env)
        for _ in range(100 if (process or args.backend) else 0):
            try:
                with urllib.request.urlopen(backend + '/api/v1/capabilities', timeout=1):
                    break
            except OSError:
                if process and process.poll() is not None:
                    raise RuntimeError('宿主启动失败，请检查其输出')
                time.sleep(.1)
        else:
            if process or args.backend: raise RuntimeError('未能连接宿主')
        setup_lock=threading.Lock()
        automation = Automation(backend, data.parent / (data.name + '-automation'))
        def setup(password):
            nonlocal process
            with setup_lock:
                if data.exists(): raise ValueError('ALREADY_INITIALIZED')
                init_env=env.copy(); init_env['ONLINECOC_BOOTSTRAP_PASSWORD']=password
                result=subprocess.run(command+['init'],env=init_env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if result.returncode: raise RuntimeError('INITIALIZATION_FAILED')
                for name in ('player3','player4'):
                    account_env=env.copy(); account_env['MD_SETUP_PASSWORD']=password
                    wrapper="import os,getpass,runpy,sys; getpass.getpass=lambda prompt='':os.environ['MD_SETUP_PASSWORD']; sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')"
                    result=subprocess.run([sys.executable,'-B','-c',wrapper]+command[2:]+['account-create',name,'--role','player'],env=account_env,capture_output=True,timeout=30)
                    if result.returncode: raise RuntimeError('ACCOUNT_CREATION_FAILED')
                process=subprocess.Popen(command+['serve','--port',str(urllib.parse.urlsplit(backend).port)],env=env)
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(backend+'/api/v1/capabilities',timeout=1):
                            c=Client(backend,'kp',password)
                            prepare_presets(c)
                            automation.attach(c)
                            return
                    except OSError: time.sleep(.1)
                raise RuntimeError('HOST_START_FAILED')
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(backend, origin,setup if not data.exists() and not args.backend else None,lambda: server.shutdown(),automation))
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
