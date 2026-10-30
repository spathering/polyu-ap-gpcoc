import json,sys,subprocess,copy
from pathlib import Path
import pytest
from onlinecoc.host import Host
from onlinecoc_data import FileDataStore,StoreError
from onlinecoc.assets import Assets,restore_host
from onlinecoc.errors import DomainError
from onlinecoc.registry import stage
from onlinecoc.lua_runtime import execute
from test_host import message,invoke,host
ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('point',['before_t1','after_t1','after_random','before_t2','after_t2'])
def test_real_host_crash(tmp_path,point):
    path=tmp_path/'data';h=Host(path,bootstrap='test-password')
    sources=copy.deepcopy(h.state()['artifacts'][h.state()['activeRuleset']]['sources'])
    sources['crash.lua']="return rule('crash', {'actor'}, function(r,a) local n=r.roll(100); r.damage(a,7); return n end)"
    rev=h.command('kp',message(h,'kp','rule.stage',{'sources':sources},'stage'))['result']
    h.command('kp',message(h,'kp','rule.activate',{'revision':rev},'activate'))
    m=message(h,'player1','action.invoke',{'actionId':'crash','input':{'actor':'actor-player1'}},'crash')
    # Authority epochs are per host: write the new process epoch just before submitting.
    command=tmp_path/'command.json';command.write_text(json.dumps(m));h.close()
    result=subprocess.run([sys.executable,str(ROOT/'acceptance/crash_worker.py'),'host',str(path),point,str(command)],capture_output=True,timeout=40)
    assert result.returncode==70,result.stderr.decode(errors='replace')
    with FileDataStore(path/'rooms/demo') as store:prior=store.snapshot()[1]
    h=Host(path)
    try:
        state=h.state();rec=state['commands'].get('player1:crash')
        if point=='before_t1':assert rec is None and state['entities']['actor-player1']['numbers']['hp']==9
        else:
            assert rec['status']=='committed',rec
            assert state['entities']['actor-player1']['numbers']['hp']==4
            assert len(rec['random'])==1 and rec['receipt']['result']==rec['random'][0]['value']
            if prior['commands']['player1:crash']['random']:assert rec['random']==prior['commands']['player1:crash']['random']
            # Exact original envelope can be retried after recovery regardless of the new authority epoch.
            saved=json.loads(command.read_text());assert h.command('player1',saved)['status']=='committed'
    finally:h.close()

@pytest.mark.parametrize('point',['half_write','before_sync','before_publish','after_publish'])
def test_real_file_crash(tmp_path,point):
    path=tmp_path/'store'
    with FileDataStore(path) as s:s.commit(0,{'n':1})
    result=subprocess.run([sys.executable,str(ROOT/'acceptance/crash_worker.py'),'store',str(path),point],capture_output=True,timeout=20)
    assert result.returncode==70
    with FileDataStore(path) as s:assert s.snapshot()[1]=={'n':2 if point=='after_publish' else 1}

def test_backup_restore_assets_identity(host,tmp_path):
    assets=Assets(host);asset=assets.upload('kp','秘密.txt','秘密'.encode(),'kp')
    assert assets.read('kp',asset)[0]=='秘密'.encode()
    with pytest.raises(DomainError,match='NOT_VISIBLE'):assets.read('player1',asset)
    before=host.state();assets.backup('kp',tmp_path/'backup',True)
    restore_host(tmp_path/'backup',tmp_path/'restored')
    restored=Host(tmp_path/'restored')
    try:
        assert restored.state()==before
        assert Assets(restored).read('kp',asset)[0]=='秘密'.encode()
        assert restored.identity.login('player1','test-password')
    finally:restored.close()
    raw=next((tmp_path/'backup/assets').iterdir());raw.write_bytes(b'corrupt')
    with pytest.raises(DomainError,match='ASSET_CORRUPT'):restore_host(tmp_path/'backup',tmp_path/'bad')
    assert not (tmp_path/'bad').exists() and host.state()==before

def test_wait_timeout_and_permission_recheck(host):
    now=[1000.];host.clock=lambda:now[0]
    r=invoke(host,'player1','demo.timed',{'actor':'actor-player1','amount':7},'timeout')
    fid=r['result']['flowId'];w=next(x for x in host.state()['waits'].values() if x['flowId']==fid)
    now[0]=1031;host.tick();assert host.state()['flows'][fid]['status']=='completed'
    assert host.command('player1',message(host,'player1','flow.respond',{'waitId':w['id'],'revision':1,'answer':True},'late'))['status']=='rejected'
    r=invoke(host,'player1','demo.timed',{'actor':'actor-player1','amount':7},'revoke')
    fid=r['result']['flowId'];s=host.state();s['entities']['actor-player1']['owner']='player2';s['entities']['actor-player1']['revision']+=1;host.commit(s)
    w=next(x for x in host.state()['waits'].values() if x['flowId']==fid)
    host.command('player1',message(host,'player1','flow.respond',{'waitId':w['id'],'revision':1,'answer':True},'respond'))
    assert host.state()['flows'][fid]['status']=='needs_attention'
    assert host.state()['entities']['actor-player1']['numbers']['hp']==9

@pytest.mark.parametrize('source',[
"return rule('x',{},function(r) r.roll(100) end,{mode='calculation'})",
"return rule('x',{},function(r) local a={};a.x=a;return a end)",
"return rule('x',{},function(r) return 0/0 end)",
"return rule('x',{},function(r) return r.read.__globals__ end)",
"return rule('x',{},function(r) local x={}; while true do x[#x+1]=string.format('%01000d',1) end end)",
])
def test_lua_invalid_boundaries(host,source):
    with pytest.raises(DomainError):execute({'x.lua':source},{'kind':'run','rule':'x','mode':'calculation','input':{},'state':host.snapshot_for_execution(host.state()),'account':'player1'},timeout=3)
    assert host.project('player1')['entities']['actor-player1']['numbers']['hp']==9

def test_poison_cannot_be_caught(host):
    source="return rule('x',{'actor'},function(r,a) pcall(function() r.set(a,'quantity',1) end); r.set(a,'hp',1) end)"
    with pytest.raises(DomainError,match='EXECUTION_REJECTED'):
        execute({'x.lua':source},{'kind':'run','rule':'x','mode':'action','input':{'actor':'actor-player1'},'state':host.snapshot_for_execution(host.state()),'account':'player1'})

def test_invalid_dependency_and_wait():
    with pytest.raises(DomainError):stage({'a.lua':"return rule('a',{},function() end,{dependencies={'b'}})",'b.lua':"return rule('b',{},function() end,{dependencies={'a'}})"})
    with pytest.raises(DomainError):stage({'a.lua':"return flow('a',{}, {ask('w',{role='kp',seconds=1})})"})

def test_quota_and_sync_failure(tmp_path,monkeypatch):
    import os
    with FileDataStore(tmp_path/'s',max_bytes=10) as s:
        with pytest.raises(StoreError,match='STORE_FULL'):s.commit(0,{'n':1})
    with FileDataStore(tmp_path/'s') as s:
        with monkeypatch.context() as m:
            m.setattr(os,'fsync',lambda fd:(_ for _ in ()).throw(OSError('sync failed')))
            with pytest.raises(OSError):s.commit(0,{'n':1})
        assert s.snapshot()==(0,None)

@pytest.mark.parametrize('point',['before_t2','after_t2'])
def test_flow_stage_crash_preserves_wait_and_random(tmp_path,point):
    path=tmp_path/'flow';h=Host(path,bootstrap='test-password');s=h.state();s['entities']['skill-player1']['numbers']['value']=0;h.commit(s)
    m=message(h,'player1','action.invoke',{'actionId':'demo.ruling','input':{'actor':'actor-player1','skill':'skill-player1','amount':7}},'flow-crash')
    command=tmp_path/'command.json';command.write_text(json.dumps(m));h.close()
    r=subprocess.run([sys.executable,str(ROOT/'acceptance/crash_worker.py'),'host',str(path),point,str(command)],capture_output=True,timeout=40);assert r.returncode==70
    with FileDataStore(path/'rooms/demo') as store:prior=store.snapshot()[1]
    h=Host(path)
    try:
        state=h.state();flow=next(iter(state['flows'].values()));assert flow['status']=='waiting'
        assert len(state['waits'])==1
        for k,record in prior['commands'].items():
            if record['random']:assert state['commands'][k]['random']==record['random']
        if prior['waits']:assert state['waits']==prior['waits']
    finally:h.close()

def test_old_data_snapshot_survives_hot_reload(host):
    sources=copy.deepcopy(host.state()['artifacts'][host.state()['activeRuleset']]['sources'])
    sources['data-flow.lua']="return flow('data.flow',{'actor'}, {ask('wait',{role='initiator',seconds=60,yes='apply',no='end',timeout='end'}),step('apply',function(r,a) r.damage(a,r.readData('amount.json').value) end)})"
    rev=host.command('kp',message(host,'kp','rule.stage',{'sources':sources,'data':{'amount.json':{'value':7}}},'old-data'))['result']
    host.command('kp',message(host,'kp','rule.activate',{'revision':rev},'active-old'))
    fid=invoke(host,'player1','data.flow',{'actor':'actor-player1'},'data-flow')['result']['flowId']
    newer=host.command('kp',message(host,'kp','rule.stage',{'sources':sources,'data':{'amount.json':{'value':100}}},'new-data'))['result']
    host.command('kp',message(host,'kp','rule.activate',{'revision':newer},'active-new'));host.close();host.__init__(host.path)
    w=next(w for w in host.state()['waits'].values() if w['flowId']==fid)
    host.command('player1',message(host,'player1','flow.respond',{'waitId':w['id'],'revision':1,'answer':True},'yes'))
    assert host.state()['entities']['actor-player1']['numbers']['hp']==4

def test_second_host_process_is_rejected(host):
    result=subprocess.run([sys.executable,str(ROOT/'backend/scripts/run.py'),'--data-dir',str(host.path),'serve','--port','0'],capture_output=True,timeout=15)
    assert result.returncode!=0 and b'STORE_LOCKED' in result.stderr
    assert host.project('player1')['entities']
