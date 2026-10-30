import asyncio,time,copy
import pytest
from fastapi.testclient import TestClient
from onlinecoc.host import Host
from onlinecoc.server import create_app
from onlinecoc.gateway import InProcessTransport
from test_host import host,message

def test_http_inprocess_equivalent(host,tmp_path,monkeypatch):
    other=Host(tmp_path/'other',bootstrap='test-password');other.commit(copy.deepcopy(host.state()));other.epoch=host.epoch
    monkeypatch.setattr('onlinecoc.host.secrets.randbelow',lambda sides:24)
    try:
        with TestClient(create_app(other,8765),base_url='http://127.0.0.1:8765') as c:
            c.headers['origin']='http://127.0.0.1:8765'
            csrf=c.post('/api/v1/login',json={'loginName':'player1','password':'test-password'}).json()['csrf'];c.headers['x-csrf-token']=csrf
            direct=InProcessTransport(host,'player1')
            for i,(rule,args) in enumerate([('demo.damage',{'actor':'actor-player1','amount':7}),('demo.check',{'actor':'actor-player1','skill':'skill-player1'}),('demo.damage',{'actor':'actor-player2','amount':7})]):
                m=message(host,'player1','action.invoke',{'actionId':rule,'input':args},str(i))
                expected=direct.command(m);actual=c.post('/api/v1/commands',json=m).json();assert actual==expected
                assert other.state()['entities']==host.state()['entities']
            assert c.get('/api/v1/receipts/0').json()==direct.receipt('0')
    finally:other.close()

def test_slow_sender_is_closed(host):
    token,_=host.identity.login('player1','test-password');app=create_app(host,8765);events=[]
    async def test():
        first=True
        async def receive():
            nonlocal first
            if first:first=False;return {'type':'websocket.connect'}
            await asyncio.sleep(30)
        async def send(event):
            events.append(event)
            if event['type']=='websocket.send':await asyncio.sleep(30)
        scope={'type':'websocket','asgi':{'version':'3.0'},'scheme':'ws','path':'/api/v1/connect','raw_path':b'/api/v1/connect','query_string':b'','root_path':'','headers':[(b'host',b'127.0.0.1:8765'),(b'origin',b'http://127.0.0.1:8765'),(b'cookie',('onlinecoc='+token).encode())],'client':('127.0.0.1',1),'server':('127.0.0.1',8765),'subprotocols':[]}
        await asyncio.wait_for(app(scope,receive,send),5)
    start=time.perf_counter();asyncio.run(test())
    assert 1.9<time.perf_counter()-start<5
    assert any(e['type']=='websocket.close' and e['code']==1013 for e in events)
    assert host.project('player1')['entities']
