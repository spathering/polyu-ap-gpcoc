"""Black-box package acceptance using only the existing host HTTP/CLI interfaces."""
import json, os, secrets, socket, subprocess, sys, time, urllib.request, uuid
from pathlib import Path
PACK=Path(__file__).resolve().parents[1]
ROOT=PACK.parents[1]
sys.path.insert(0,str(PACK/'tools'))
from client import Client,HostError
from package import install,bundle
from launch import handler
from http.server import ThreadingHTTPServer
import threading

def main():
    out=PACK/'tests/output'/('acceptance-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
    password=secrets.token_urlsafe(20);env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',ONLINECOC_BOOTSTRAP_PASSWORD=password)
    run=[sys.executable,'-B',str(ROOT/'engineering/backend/scripts/run.py'),'--data-dir',str(out/'room')]
    subprocess.run(run+['init'],env=env,capture_output=True,check=True,timeout=30)
    def port():
        with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
    backend='http://127.0.0.1:'+str(port());origin='http://127.0.0.1:'+str(port());checks=[]
    def ok(name,condition=True):
        assert condition,name
        checks.append(name)
    def rejects(name,fn):
        try:fn()
        except HostError:ok(name);return
        raise AssertionError(name)
    log=(out/'host.log').open('wb');proc=subprocess.Popen(run+['serve','--port',backend.rsplit(':',1)[1]],env=env,stdout=log,stderr=log)
    proxy=None
    try:
        for _ in range(100):
            try:urllib.request.urlopen(backend+'/api/v1/capabilities',timeout=1);break
            except OSError:time.sleep(.1)
        proxy=ThreadingHTTPServer(('127.0.0.1',int(origin.rsplit(':',1)[1])),handler(backend,origin));threading.Thread(target=proxy.serve_forever,daemon=True).start()
        k=Client(origin,'kp',password);p=Client(origin,'player1',password);other=Client(origin,'player2',password)
        install(k);ok('13 rules imported and activated',len(bundle()['sources'])==13)
        a=k.command('entity.create',{'configurationId':'md.character','owner':'player1','visibility':'owner','name':'观察员'})
        k.invoke('md.profile',actor=a,constitution=3,strength=2,speed=4,observation=5,spirit=3,intellect=3)
        ok('owner sees character',a in p.request('/view')['entities']);ok('other player cannot see character',a not in other.request('/view')['entities'])
        rejects('profile locked',lambda:k.invoke('md.profile',actor=a,constitution=3,strength=2,speed=4,observation=5,spirit=3,intellect=3))
        rejects('PL cannot settle resources',lambda:p.invoke('md.resolve',actor=a,kind='sleep',destination=1))
        rejects('PL cannot patch protected numbers',lambda:p.command('entity.update',{'id':a,'numbers':{'hp':100}}))
        rejects('cannot roll without KP request',lambda:p.invoke('md.check',actor=a))
        k.invoke('md.request',actor=a,attribute=3,talent=False)
        envelope=p.envelope('action.invoke',{'actionId':'md.check','input':{'actor':a}});r=p.send(envelope);ok('authoritative d6',1<=r['result']['die']<=6)
        ok('same command replay same dice',p.send(envelope)==r)
        rejects('request consumed once',lambda:p.invoke('md.check',actor=a))
        k.invoke('md.resolve',actor=a,kind='explore',destination=3);ok('explore cost and location',p.request('/view')['entities'][a]['numbers']['stamina']==1)
        rejects('one main action per slot',lambda:k.invoke('md.resolve',actor=a,kind='sleep',destination=3))
        k.invoke('md.sync',actor=a,day=1,slot=2);k.invoke('md.resolve',actor=a,kind='sleep',destination=3)
        ok('sleep restored stamina',p.request('/view')['entities'][a]['numbers']['stamina']==2)
        k.command('progress.set',{'ownerKind':'member','ownerId':'member-player1','eventKey':'md.known','value':{'locations':[22]}})
        ok('private reveal visible to recipient',any(x['eventKey']=='md.known' for x in p.request('/view')['progress'].values()))
        ok('private reveal hidden from others',not any(x['eventKey']=='md.known' for x in other.request('/view')['progress'].values()))
        dm=k.command('chat.direct.open',{'accountId':'player1'})['channelId'];k.command('chat.message.send',{'channelId':dm,'text':'私密线索'})
        rejects('private narration hidden',lambda:other.request('/chat/history',{'channelId':dm}))
        w=k.command('entity.create',{'configurationId':'md.world','visibility':'public','owner':'kp'})
        k.invoke('md.advance',actor=w);ok('world advanced',k.request('/view')['entities'][w]['numbers']['slot']==2)
        items=bundle()['data']['scenario.json']['items'];index=next(i+1 for i,x in enumerate(items) if x['id']=='item-shotgun')
        item=k.command('entity.create',{'configurationId':'md.item','owner':'player1','visibility':'owner','numbers':{'itemIndex':index}})
        k.command('relation.set',{'sourceId':item,'targetId':a,'relationType':'source'});k.command('relation.set',{'sourceId':a,'targetId':item,'relationType':'references'})
        k.invoke('md.confirm',actor=item);k.invoke('md.equip',actor=a,item=item)
        n=p.request('/view')['entities'];ok('confirmed weapon and ammunition',n[a]['numbers']['weapon']==5 and n[item]['numbers']['charges']==2)
        rejects('other player cannot equip item',lambda:other.invoke('md.equip',actor=a,item=item))
        try:p.opener.open(origin+'/package/bundle.json')
        except urllib.error.HTTPError as e:ok('PL cannot download secrets',e.code==403)
        else:raise AssertionError('secret bundle exposed')
        public=json.load(p.opener.open(origin+'/package/public.json'));ok('public metadata omits hidden basement',not any(x['id']=='loc-basement' for x in public['locations']))
        # Continue the same authoritative character through all remaining slots, noncombat route.
        shore=next(i+1 for i,x in enumerate(bundle()['data']['scenario.json']['locations']) if x['id']=='loc-shore')
        for absolute in range(3,17):
            k.invoke('md.advance',actor=w)
            day=(absolute-1)//8+1;slot=(absolute-1)%8+1
            k.invoke('md.sync',actor=a,day=day,slot=slot)
            kind='move' if absolute in (3,4) else 'sleep'
            destination=1 if absolute==3 else shore
            k.invoke('md.resolve',actor=a,kind=kind,destination=destination)
        k.command('entity.update',{'id':w,'numbers':{'boatReady':1,'closed':1}})
        k.command('entity.update',{'id':a,'numbers':{'ending':1}})
        final=k.request('/view')['entities'][a]['numbers']
        ok('two day noncombat route reaches shore and recorded ending',final['day']==2 and final['slot']==8 and final['location']==shore and final['ending']==1)
        backup=k.request('/backup',{});ok('host backup created',bool(backup))
        proc.terminate();proc.wait(timeout=15)
        proc=subprocess.Popen(run+['serve','--port',backend.rsplit(':',1)[1]],env=env,stdout=log,stderr=log)
        for _ in range(100):
            try:urllib.request.urlopen(backend+'/api/v1/capabilities',timeout=1);break
            except OSError:time.sleep(.1)
        again=Client(origin,'kp',password)
        ok('restart preserves character and ending',again.request('/view')['entities'][a]['numbers']['ending']==1)

        ok('scenario coverage',len(bundle()['data']['scenario.json']['locations'])==23 and len(items)==22)
        result={'passed':len(checks),'checks':checks,'mode':'real HTTP host + pack same-origin adapter'}
        (PACK/'tests/results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
    finally:
        if proxy:proxy.shutdown();proxy.server_close()
        proc.terminate();proc.wait(timeout=15);log.close()

if __name__=='__main__':main()
