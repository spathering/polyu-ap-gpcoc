import os,sys,socket,subprocess,time,json,statistics
from pathlib import Path
import pytest,httpx
from playwright.sync_api import sync_playwright
from onlinecoc.host import Host
ROOT=Path(__file__).resolve().parents[2]

def wait(page,expression,timeout=15000,arg=None):
    deadline=time.monotonic()+timeout/1000
    while time.monotonic()<deadline:
        if page.evaluate(expression,arg):return
        page.wait_for_timeout(50)
    raise AssertionError('Browser state timeout: '+expression+'; UI: '+page.locator('#result').inner_text())


@pytest.fixture(scope='module')
def live_server(tmp_path_factory):
    folder=tmp_path_factory.mktemp('network');data=folder/'data'
    h=Host(data,bootstrap='test-password');h.close()
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    log=open(folder/'server.log','w',encoding='utf-8')
    process=subprocess.Popen([sys.executable,str(ROOT/'acceptance/offline_server.py'),'--data-dir',str(data),'serve','--port',str(port)],stdout=log,stderr=log)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(25):
            if process.poll() is not None:pytest.fail((folder/'server.log').read_text())
            try:
                response=httpx.get(url+'/api/v1/capabilities',timeout=1,trust_env=False)
                if response.status_code==200:break
                last_error=f'{response.status_code}: {response.text}'
            except httpx.HTTPError as error:last_error=str(error)
            time.sleep(.1)
        else:pytest.fail('Server probe failed: '+locals().get('last_error','unexpected status')+' '+(folder/'server.log').read_text())
        yield url,data,process
    finally:process.terminate();process.wait(timeout=10);log.close()

def test_http_boundary(live_server):
    url,_,_=live_server
    with httpx.Client(base_url=url,trust_env=False) as c:
        assert 'javascript' in c.get('/app.js').headers['content-type']
        assert c.post('/api/v1/login',json={'loginName':'kp','password':'test-password'}).status_code==403
        c.headers['origin']=url
        assert c.post('/api/v1/login',content='{').status_code==400
        r=c.post('/api/v1/login',json={'loginName':'player1','password':'test-password'});assert r.status_code==200,r.text
        csrf=r.json()['csrf'];assert c.get('/api/v1/admin').status_code==403
        assert c.post('/api/v1/calculate',json={'rule':'demo.attack','input':{'actor':'actor-player1'}}).status_code==403
        c.headers['x-csrf-token']=csrf
        assert c.post('/api/v1/calculate',json={'rule':'demo.attack','input':{'actor':'actor-player1'}}).json()['result']==7
        assert c.post('/api/v1/commands',content='x'*65537).status_code==413
        assert c.get('/api/v1/view',headers={'Host':'evil.example'}).status_code==403
        view=c.get('/api/v1/view').json();assert 'secret-clue' not in view['entities']
        assert 'passwordHash' not in json.dumps(view)
        assert c.post('/api/v1/logout').status_code==200
        assert c.get('/api/v1/view').status_code==401

def test_three_browsers_and_eight_connections(live_server):
    url,_,process=live_server;errors=[];reports=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        contexts=[];pages=[]
        try:
            for account in ['kp','player1','player2']:
                context=browser.new_context();contexts.append(context);page=context.new_page();pages.append(page)
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('console',lambda m: print('Browser console:',m.text) if m.type=='error' else None)
                page.goto(url);page.locator('#username').fill(account);page.locator('#password').fill('test-password');page.locator('#login button').click()
                wait(page,'window.playtest?.connected',timeout=15000)
            kp,p1,p2=pages
            assert p1.evaluate("'secret-clue' in playtest.view.entities") is False
            assert kp.evaluate("'secret-clue' in playtest.view.entities") is True
            result=p1.evaluate("async()=>await playtest.command('action.invoke',{actionId:'demo.damage',input:{actor:'actor-player1',amount:7}},'browser-damage')")
            assert result['status']=='committed',result
            for page in pages:wait(page,"playtest.view.entities['actor-player1'].numbers.hp===4")
            # Lost-response retry: retain the exact command envelope, close WS, then replay after snapshot.
            p1.evaluate('playtest.socket.close()');wait(p1,'playtest.connected',timeout=15000)
            duplicate=p1.evaluate("async()=>await playtest.command('action.invoke',{actionId:'demo.damage',input:{actor:'actor-player1',amount:7}},'browser-damage')")
            assert duplicate==result
            # Dynamic publication changes directory and form without reloading a browser page.
            sources={f.name:f.read_text(encoding='utf-8') for f in (ROOT/'rulepacks/demo').glob('*.lua')}
            sources['new.lua']="return rule('new.action', {'actor'}, function(r,a) r.damage(a,2) end)"
            revision=kp.evaluate("async sources=>(await playtest.command('rule.stage',{sources})).result",sources)
            kp.evaluate("async revision=>await playtest.command('rule.activate',{revision})",revision)
            wait(p1,"playtest.view.catalog.actions.some(a=>a.id==='new.action')")
            assert p1.locator('#actions option[value="new.action"]').count()==1
            # The same transport surface with three and eight isolated connections.
            for count in [3,8]:
                while len(pages)<count:
                    c=browser.new_context();contexts.append(c);page=c.new_page();pages.append(page);page.goto(url)
                    page.evaluate("async()=>await playtest.login('player1','test-password')");wait(page,'playtest.connected')
                times=[]
                for i in range(5):
                    start=time.perf_counter()
                    kp.evaluate("async name=>await playtest.command('entity.patch',{id:'actor-player1',name})",f'measure-{count}-{i}')
                    for page in pages:wait(page,'(name)=>playtest.view.entities["actor-player1"].name===name',arg=f'measure-{count}-{i}')
                    times.append((time.perf_counter()-start)*1000)
                sizes=[page.evaluate('new TextEncoder().encode(JSON.stringify(playtest.view)).length') for page in pages]
                server=kp.evaluate("async()=>await playtest.transport.request('admin')")
                servermetrics=server['metrics']
                reports.append({'connections':count,'rounds':len(times),'endToEndMsP50':statistics.median(times),'endToEndMsP95':max(times),'snapshotBytes':sizes,'serverTimings':servermetrics,'serverMemory':server['runtime']})
            # Revocation clears existing client cache, not just subsequent writes.
            kp.evaluate("async()=>await playtest.command('member.update',{accountId:'player1',active:false})")
            wait(p1,'playtest.view===null',timeout=10000)
            assert not errors,errors
            output=ROOT/'.test-output';output.mkdir(exist_ok=True)
            kp.screenshot(path=str(output/'console-kp.png'),full_page=True)
            (output/'network-metrics.json').write_text(json.dumps({'browser':browser.version,'serverPid':process.pid,'measurements':reports,'pageErrors':errors},indent=2),encoding='utf-8')
        finally:
            for c in contexts:c.close()
            browser.close()
