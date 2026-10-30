import json
import pytest
from onlinecoc_data import FileDataStore, MemoryDataStore, StoreError
from onlinecoc.lua_runtime import execute
from onlinecoc.model import demo_state
from onlinecoc.errors import DomainError
from pathlib import Path

@pytest.mark.parametrize('implementation',[FileDataStore,MemoryDataStore])
def test_store_contract(tmp_path,implementation):
    store=implementation(tmp_path/'store') if implementation is FileDataStore else implementation()
    assert store.snapshot()==(0,None)
    store.commit(0,{'entities':{'a':{'x':1}}})
    _,snapshot=store.snapshot();snapshot['entities']['a']['x']=4
    assert store.snapshot()[1]['entities']['a']['x']==1
    with pytest.raises(StoreError):store.commit(0,{})
    if implementation is FileDataStore:
        with pytest.raises(StoreError):FileDataStore(tmp_path/'store')
        store.close()
        with FileDataStore(tmp_path/'store') as reopened:assert reopened.snapshot()[1]['entities']['a']['x']==1

def test_failed_publish(tmp_path):
    def fault(stage):
        if stage=='before_publish':raise OSError('disk full')
    with FileDataStore(tmp_path/'s') as s:s.commit(0,{'n':1})
    with FileDataStore(tmp_path/'s',fault=fault) as s:
        with pytest.raises(OSError):s.commit(1,{'n':2})
    with FileDataStore(tmp_path/'s') as s:assert s.snapshot()==(1,{'n':1})

def test_corruption_and_export(tmp_path):
    with FileDataStore(tmp_path/'s') as s:
        s.commit(0,{'n':1});s.commit(1,{'n':2});s.export_snapshot(tmp_path/'backup.json')
    FileDataStore.restore(tmp_path/'backup.json',tmp_path/'r')
    with FileDataStore(tmp_path/'r') as s:assert s.snapshot()[1]=={'n':2}
    (tmp_path/'s/generations/000000000002.json').write_text('{}')
    with pytest.raises(StoreError):FileDataStore(tmp_path/'s')

def sources():
    return {p.name:p.read_text(encoding='utf-8') for p in (Path(__file__).resolve().parents[2]/'rulepacks/demo').glob('*.lua')}

def test_lua_real_execution():
    src=sources();meta=execute(src,{'kind':'inspect'})['metadata'];assert 'demo.ruling' in meta
    state=demo_state([('kp','kp'),('p1','player'),('p2','player')])
    out=execute(src,{'kind':'run','rule':'demo.damage','mode':'action','state':state,'account':'p1','input':{'actor':'actor-p1','amount':7}})
    assert out['entities']['actor-p1']['numbers']['hp']==4
    assert state['entities']['actor-p1']['numbers']['hp']==9
    check=execute(src,{'kind':'run','rule':'demo.check','mode':'action','state':state,'account':'p1','input':{'actor':'actor-p1','skill':'skill-p1'}},lambda sides:25)
    assert check['result'] is True

def test_lua_timeout_and_restricted_globals():
    with pytest.raises(DomainError,match='RULE_TIMEOUT'):
        execute({'loop.lua':"while true do end"},{'kind':'inspect'},timeout=1)
    execute({'safe.lua':"assert(python==nil and io==nil and os==nil and debug==nil and math.random==nil); return rule('x',{},function() end)"},{'kind':'inspect'})