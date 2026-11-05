"""Native EXE startup, argument forwarding and process-tree cleanup smoke test."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid

PACK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACK/'tools'))
from client import Client


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        return s.getsockname()[1]


def main():
    exe=PACK/'启动激光与情感.exe'
    out=PACK/'tests/output'/('launcher-'+uuid.uuid4().hex[:10])
    out.mkdir(parents=True)
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    checks=[]

    def ok(name,condition=True):
        assert condition,name
        checks.append({'name':name,'passed':True})

    result=subprocess.run([str(exe),'--help'],cwd=out,stdin=subprocess.DEVNULL,
                          capture_output=True,timeout=15,creationflags=flags)
    ok('help_from_unrelated_working_directory',result.returncode==0 and b'--no-browser' in result.stdout)
    isolated=out/'single exe'
    isolated.mkdir()
    shutil.copy2(exe,isolated/exe.name)
    result=subprocess.run([str(isolated/exe.name)],cwd=out,stdin=subprocess.DEVNULL,
                          capture_output=True,timeout=10,creationflags=flags)
    ok('missing_companion_reports_error_without_hanging',result.returncode==1 and b'launch.py' in result.stderr)
    front,back=port(),port()
    env=os.environ.copy()
    password=secrets.token_urlsafe(24)
    env['ONLINECOC_BOOTSTRAP_PASSWORD']=password
    data=out/'临时 存档'
    base='http://127.0.0.1:'+str(front)
    command=[str(exe),'--data-dir',str(data),'--port',str(front),
             '--backend-port',str(back),'--no-browser']

    def is_open(number):
        with socket.socket() as s:
            s.settimeout(.15)
            return s.connect_ex(('127.0.0.1',number))==0

    for attempt in range(2):
        with (out/('run-'+str(attempt)+'.log')).open('wb') as log:
            process=subprocess.Popen(command,cwd=out,env=env,stdin=subprocess.DEVNULL,
                                     stdout=log,stderr=log,creationflags=flags)
            try:
                for _ in range(150):
                    if process.poll() is not None:
                        raise RuntimeError('EXE exited early; see '+str(out))
                    try:
                        with urllib.request.urlopen(base+'/api/v1/capabilities',timeout=1) as r:
                            assert r.status==200
                        break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError('EXE startup timed out')
                ok('fresh_start' if attempt==0 else 'restart_same_data_and_ports')
                ok('login_after_start_'+str(attempt),Client(base,'kp',password).request('/me')['accountId']=='kp')
                if attempt==0:
                    ok('unicode_and_space_data_argument', (data/'rooms/demo').is_dir())
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)
                for _ in range(60):
                    if not is_open(front) and not is_open(back):
                        break
                    time.sleep(.1)
                ok('launcher_exit_cleans_frontend_and_host_'+str(attempt),not is_open(front) and not is_open(back))
    build=json.loads((PACK/'tools/launcher-build.json').read_text(encoding='utf-8'))
    ok('exe_matches_build_record',hashlib.sha256(exe.read_bytes()).hexdigest()==build['executableSha256'])
    report={'passed':len(checks),'checks':checks,'executableSha256':build['executableSha256'],
            'scope':'native EXE; fresh isolated data; forced launcher exit and restart; no manual double-click interaction'}
    (PACK/'tests/launcher-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS:',len(checks),'native launcher checks')


if __name__=='__main__':
    main()
