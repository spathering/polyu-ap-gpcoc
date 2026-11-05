"""Run all five actual EXEs against an isolated game directory, never user saves."""
import json,os,secrets,socket,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
PACK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACK/'tools'))
from client import Client,HostError
from playwright.sync_api import sync_playwright,expect

def main():
    out=PACK/'tests/output'/('exe-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    base='http://127.0.0.1:'+str(port);data=out/'room';checks=[];supervisor=None
    def ok(name,condition=True):
        assert condition,name
        checks.append(name)
    def info():
        with urllib.request.urlopen(base+'/launcher/info',timeout=3) as r:return json.load(r)
    targets=json.loads((PACK/'tools/launcher-build.json').read_text(encoding='utf-8'))['executables']
    password=secrets.token_urlsafe(20)
    try:
        for t in targets:
            capture=out/(t['account']+'.url.txt')
            p=subprocess.run([str(PACK/t['file']),'--port',str(port),'--data-dir',str(data),'--capture',str(capture)],timeout=65)
            ok(t['file']+' native exit',p.returncode==0)
            ok(t['account']+' correct URL',capture.read_text(encoding='utf-8')==base+'/sessions/'+t['account']+'/')
            current=info()['supervisorPid'];ok(t['account']+' reuses same service',supervisor is None or supervisor==current);supervisor=current
        req=urllib.request.Request(base+'/setup',data=json.dumps({'password':password}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=90) as r:ok('browser bootstrap ready',json.load(r)['ready'])
        k=Client(base,'kp',password);view=k.request('/view')
        presets=['观察员','护卫','文献员','医护员']
        actors=[e for e in view['entities'].values() if e['configurationId']=='md.character']
        for i,name in enumerate(presets,1):
            own=Client(base,'player'+str(i),password).request('/view')['entities']
            ok('player'+str(i)+' bound preset and private character',len([e for e in own.values() if e['configurationId']=='md.character'])==1 and any(e['name']==name and e['numbers']['approved']==1 for e in own.values()))
            ok('player'+str(i)+' starting card',len([e for e in own.values() if e['configurationId']=='md.item' and e['numbers']['confirmed']==1])==1)
        def post(client,path,csrf=True):
            headers={'Origin':base}
            if csrf:headers['X-CSRF-Token']=client.csrf
            return client.opener.open(urllib.request.Request(base+path,data=b'{}',headers=headers),timeout=30)
        before={e['instanceId']:e['numbers'] for e in actors}
        with post(k,'/package/presets') as r:ok('repeat preset preparation no duplicates',all(not b['created'] for b in json.load(r)['bindings']))
        after=k.request('/view');ok('repeat preserves gameplay',all(after['entities'][i]['numbers']==n for i,n in before.items()))
        try:post(Client(base,'player1',password),'/package/shutdown')
        except urllib.error.HTTPError as e:ok('PL cannot stop service',e.code==403)
        else:raise AssertionError('PL shutdown allowed')
        with sync_playwright() as pw:
            try:browser=pw.chromium.launch(headless=True)
            except Exception:browser=pw.chromium.launch(channel='msedge',headless=True)
            context=browser.new_context(viewport={'width':1440,'height':900})
            for t in targets:
                page=context.new_page();page.goto(base+'/sessions/'+t['account']+'/')
                expect(page.locator('[name=loginName]')).to_have_value(t['account']);ok(t['account']+' browser account preselected')
                page.locator('[name=password]').fill(password);page.locator('#login-form button').click();expect(page.locator('nav')).to_be_visible(timeout=15000)
                if t['account']!='kp':expect(page.locator('main')).to_contain_text(presets[int(t['account'][-1])-1])
                ok(t['account']+' authenticated correct browser view')
            ok('five cookie-isolated browser pages',len(context.pages)==5)
            browser.close()
        with post(k,'/package/shutdown') as r:ok('KP clean shutdown accepted',json.load(r)['stopping'])
        for _ in range(100):
            try:info();time.sleep(.1)
            except OSError:break
        else:raise AssertionError('Service did not stop')
        ok('service closed')
        result={'passed':len(checks),'checks':checks,'nativeExecutables':5,'browserContexts':1,'browserPages':5}
        (PACK/'tests/launcher-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
    finally:
        if supervisor:
            try:
                if info()['supervisorPid']==supervisor:subprocess.run(['taskkill','/PID',str(supervisor),'/T','/F'],capture_output=True)
            except OSError:pass

if __name__=='__main__':main()
