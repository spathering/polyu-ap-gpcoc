"""Actual native manager, isolated frontend/host trees, no live-game changes."""
import hashlib,json,os,secrets,socket,subprocess,sys,threading,time,urllib.error,urllib.request,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
PACK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACK/'tools'))
from client import Client

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    out=PACK/'tests/output'/('service-manager-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
    exe=PACK/'配置包服务管理.exe';number=port();base='http://127.0.0.1:'+str(number);data=out/'room';checks=[]
    def ok(name,value=True):assert value,name;checks.append(name);print('PASS '+name,flush=True)
    def manager(command,success=True,with_data=True):
        result=out/('result-'+uuid.uuid4().hex+'.json')
        args=[str(exe),command,'--port',str(number),'--result',str(result)]
        if with_data:args+=['--data-dir',str(data)]
        r=subprocess.run(args,capture_output=True,timeout=100)
        value=json.loads(result.read_text(encoding='utf-8-sig'))
        assert (r.returncode==0)==success,(command,value)
        return value
    def info():
        with urllib.request.urlopen(base+'/launcher/info',timeout=5) as r:return json.load(r)
    def denied(path,headers=None):
        req=urllib.request.Request(base+path,data=b'{}',headers=headers or {})
        try:urllib.request.urlopen(req,timeout=5)
        except urllib.error.HTTPError as e:return e.code==403
        return False
    unrelated=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(300)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    fake=None
    try:
        ok('native manager exists and is Windows PE',exe.read_bytes()[:2]==b'MZ')
        ok('initial state is stopped',manager('--status')['state']=='stopped')
        manager('--stop');ok('stopping absent instance is harmless')
        ok('native manager starts hidden pack service',manager('--start')['state']=='running')
        first=info();ok('service has valid pack fingerprint',first['workspace']==hashlib.sha256(str(PACK.resolve()).casefold().encode()).hexdigest())
        ok('first launch preserves web setup rather than setting password',json.load(urllib.request.urlopen(base+'/setup/status',timeout=5))['canSetup'])
        manager('--start');ok('repeat start reuses supervisor',info()['supervisorPid']==first['supervisorPid'])
        capture=out/'kp-url.txt'
        subprocess.run([str(PACK/'KP主持人.exe'),'--port',str(number),'--data-dir',str(data),'--capture',str(capture)],check=True,timeout=65)
        ok('existing account entry reuses manager service',info()['supervisorPid']==first['supervisorPid'] and capture.read_text(encoding='utf8')==base+'/sessions/kp/')
        smoke=manager('--smoke');ok('native management window loads',smoke['windowLoaded'])
        ok('closing manager window leaves service running',info()['supervisorPid']==first['supervisorPid'])
        ok('stop endpoint rejects unauthenticated local request',denied('/launcher/stop'))
        ok('stop endpoint rejects browser-origin requests',denied('/launcher/stop',{'Origin':base}))
        record_file=PACK/'runtime'/('service-control-'+str(number)+'.json')
        record=json.loads(record_file.read_text(encoding='utf8'))
        ok('local control record contains encrypted key only',record['pid']==first['pid'] and 'protectedKey' in record and 'key' not in record)
        password=secrets.token_urlsafe(20)
        request=urllib.request.Request(base+'/setup',data=json.dumps({'password':password}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=90) as r:ok('browser bootstrap still initializes five accounts',json.load(r)['ready'])
        kp=Client(base,'kp',password);view=kp.request('/view');actor=next(e for e in view['entities'].values() if e['configurationId']=='md.character' and e['owner']=='player1')
        hp=max(1,actor['numbers']['hp']-1)
        kp.command('entity.update',{'id':actor['instanceId'],'numbers':{'hp':hp}})
        before=info();restarted=manager('--restart',with_data=False)
        ok('restart uses actual custom save even without repeated argument',Path(restarted['dataDirectory']).resolve()==data.resolve())
        ok('restart creates a new supervisor',info()['supervisorPid']!=before['supervisorPid'])
        kp=Client(base,'kp',password)
        ok('restart preserves account password and gameplay',kp.request('/view')['entities'][actor['instanceId']]['numbers']['hp']==hp)
        stopped=manager('--stop');ok('stop returns stopped state',stopped['state']=='stopped')
        ok('graceful stop removes current local control record',not record_file.exists())
        ok('unrelated Python process survives pack stop',unrelated.poll() is None)
        ok('restart after stop preserves custom save',manager('--start')['state']=='running' and Client(base,'kp',password).request('/view')['entities'][actor['instanceId']]['numbers']['hp']==hp)
        manager('--stop')
        # A server cannot make the manager kill an arbitrary PID by spoofing info.
        class Foreign(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                payload={'packId':'mini-detective-pack','workspace':first['workspace'],'pid':unrelated.pid,'supervisorPid':unrelated.pid}
                body=json.dumps(payload).encode();self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        fake=ThreadingHTTPServer(('127.0.0.1',number),Foreign);threading.Thread(target=fake.serve_forever,daemon=True).start()
        ok('spoofed supervisor PID is refused',bool(manager('--stop',success=False).get('error')) and unrelated.poll() is None)
        fake.shutdown();fake.server_close();fake=None
        class Other(Foreign):
            def do_GET(self):
                body=b'{"packId":"other","workspace":"other"}';self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        fake=ThreadingHTTPServer(('127.0.0.1',number),Other);threading.Thread(target=fake.serve_forever,daemon=True).start()
        ok('foreign port service is refused',bool(manager('--stop',success=False).get('error')))
        report={'passed':len(checks),'checks':checks,'scope':'actual native manager + native account launcher + isolated room + protected local stop + GUI window smoke'}
        (PACK/'tests/service-manager-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(json.dumps(report,ensure_ascii=False))
    finally:
        if fake:fake.shutdown();fake.server_close()
        try:manager('--stop')
        except Exception:pass
        if unrelated.poll() is None:subprocess.run(['taskkill','/PID',str(unrelated.pid),'/T','/F'],capture_output=True)

if __name__=='__main__':main()
