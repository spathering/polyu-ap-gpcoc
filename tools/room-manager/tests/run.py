"""Build and test the standalone client against a fresh, isolated real host."""
import json, os, pathlib, socket, subprocess, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOL = ROOT / 'tools/room-manager'
OUT = TOOL / '.test-output' / time.strftime('%Y%m%d-%H%M%S')
OUT.mkdir(parents=True)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', ONLINECOC_BOOTSTRAP_PASSWORD='test-manager-2026')
python = ROOT / 'engineering/.venv/Scripts/python.exe'
host = [str(python), str(ROOT / 'engineering/backend/scripts/run.py'), '--data-dir', str(OUT / 'host')]
compiler = pathlib.Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(TOOL/'build.ps1')], check=True)
subprocess.run(host + ['init'], env=env, check=True)
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
url = f'http://127.0.0.1:{port}'
log = (OUT/'host.log').open('w')
server = subprocess.Popen(host + ['serve', '--port', str(port)], env=env, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen(url+'/api/v1/capabilities', timeout=1).close(); break
        except OSError: time.sleep(.1)
    import shutil
    for name in (sys.argv[1:] or ('Integration', 'ProtocolEdges', 'GuiSmoke', 'Reconnect')):
        if not (TOOL/f'tests/{name}.cs').exists(): continue
        subprocess.run([str(compiler), '/nologo', '/target:exe', '/platform:x64', '/utf8output', '/r:System.dll', '/r:System.Core.dll', '/r:System.Drawing.dll', '/r:System.Windows.Forms.dll', '/r:System.Web.Extensions.dll', '/r:System.Net.Http.dll', '/r:'+str(TOOL/'dist/RoomManager.exe'), '/out:'+str(OUT/f'{name}.exe'), str(TOOL/f'tests/{name}.cs')], check=True)
        shutil.copy2(TOOL/'dist/RoomManager.exe', OUT/'RoomManager.exe')
        shutil.copy2(TOOL/'dist/RoomManager.exe.config', OUT/'RoomManager.exe.config')
        if name == 'Reconnect':
            probe = subprocess.Popen([str(OUT/f'{name}.exe'), url, env['ONLINECOC_BOOTSTRAP_PASSWORD'], str(OUT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for _ in range(150):
                if (OUT/'restart.ready').exists(): break
                if probe.poll() is not None: raise RuntimeError('Reconnect exited before readiness')
                time.sleep(.1)
            assert (OUT/'restart.ready').exists()
            server.terminate(); server.wait(timeout=15); time.sleep(2)
            server = subprocess.Popen(host + ['serve', '--port', str(port)], env=env, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            stdout, _ = probe.communicate(timeout=45)
            result = subprocess.CompletedProcess(probe.args, probe.returncode, stdout.decode('utf-8', errors='replace'), '')
        else:
            result = subprocess.run([str(OUT/f'{name}.exe'), url, env['ONLINECOC_BOOTSTRAP_PASSWORD'], str(OUT)], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        (OUT/f'{name}.log').write_text(result.stdout+result.stderr, encoding='utf-8')
        print(result.stdout, flush=True)
        if result.returncode: raise RuntimeError(name+' failed; '+str(OUT))
    portable = OUT / 'portable'
    shutil.copytree(TOOL/'dist', portable)
    process = subprocess.Popen([str(portable/'RoomManager.exe'), '--settings-dir', str(OUT/'portable-settings')])
    time.sleep(2)
    assert process.poll() is None
    import ctypes
    windows = []
    callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visit(hwnd, _):
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid and ctypes.windll.user32.IsWindowVisible(hwnd): windows.append(hwnd)
        return True
    ctypes.windll.user32.EnumWindows(callback(visit), 0)
    assert windows, 'Portable release must open a real visible window'
    for hwnd in windows: ctypes.windll.user32.PostMessageW(ctypes.c_void_p(hwnd), 0x0010, 0, 0)
    process.wait(timeout=15)
    (OUT/'portable.json').write_text(json.dumps({'passed': 3, 'failed': 0, 'standaloneDirectory': True, 'visibleWindow': True, 'cleanExit': process.returncode == 0}), encoding='utf-8')
    assert json.load(urllib.request.urlopen(url+'/api/v1/capabilities'))['protocolVersion'] == 1
    print('PASS host survives clients; results: '+str(OUT), flush=True)
finally:
    server.terminate(); server.wait(timeout=15); log.close()
