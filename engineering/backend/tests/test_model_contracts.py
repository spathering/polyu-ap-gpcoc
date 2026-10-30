import copy,concurrent.futures,json
from pathlib import Path
import pytest
from onlinecoc.model import validate
from onlinecoc.errors import DomainError
from onlinecoc.gateway import InProcessTransport
from onlinecoc_data import FileDataStore,MemoryDataStore
from test_host import host,message,invoke

def test_same_configuration_distinct_instances(host):
    a=host.command('kp',message(host,'kp','entity.create',{'configurationId':'demo.weapon','name':'洛阳铲','numbers':{'durability':85}},'a'))['result']
    b=host.command('kp',message(host,'kp','entity.create',{'configurationId':'demo.weapon','name':'洛阳铲','numbers':{'durability':95}},'b'))['result']
    assert a!=b
    host.command('kp',message(host,'kp','entity.patch',{'id':a,'name':'旧铲'},'rename'))
    x,y=host.state()['entities'][a],host.state()['entities'][b]
    assert x['configurationId']==y['configurationId'] and y['name']=='洛阳铲' and y['numbers']['durability']==95
    assert host.command('kp',message(host,'kp','configuration.remove',{'id':'demo.weapon'},'remove'))['code']=='REFERENCE_CONFLICT'

def test_relation_invariants(host):
    for args in [dict(sourceId='bag-player2',targetId='item-player1',relationType='contains'),dict(sourceId='bag-player1',targetId='missing',relationType='contains')]:
        r=host.command('kp',message(host,'kp','relation.set',args,str(args)));assert r['status']=='rejected'
    assert host.command('kp',message(host,'kp','entity.archive',{'id':'item-player1'},'archive'))['code']=='REFERENCE_CONFLICT'
    s=host.state();s['entities']['item-player1']['roomId']='other'
    with pytest.raises(DomainError):validate(s)
    s=host.state();s['entities']['bag-player1']['components']['core.container']['allowed']=['actor']
    s['relations']={k:r for k,r in s['relations'].items() if r['sourceId']!='bag-player1'}
    s['relations']['cycle']={'relationId':'cycle','sourceId':'bag-player1','targetId':'actor-player1','relationType':'contains','revision':1,'tags':[],'metadata':{}}
    with pytest.raises(DomainError,match='REFERENCE_CYCLE'):validate(s)

def test_concurrent_quantity_and_view_precondition(host):
    commands=[message(host,'player1','action.invoke',{'actionId':'demo.transfer','input':{'item':'item-player1','bag':'bag-player2','quantity':2}},str(i)) for i in range(2)]
    with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda m:host.command('player1',m),commands))
    assert sorted(r['status'] for r in results)==['committed','rejected']
    assert sum(e['numbers']['quantity'] for e in host.state()['entities'].values() if e['configurationId']=='demo.item' and e['instanceId']!='secret-clue')==6
    v=host.project('player1');m=message(host,'player1','entity.patch',{'id':'actor-player1','name':'stale'},'stale')
    m['payload']['expectedViews']={'actor-player1':v['entities']['actor-player1']['viewToken']}
    host.command('kp',message(host,'kp','entity.patch',{'id':'actor-player1','name':'new'},'new'))
    with pytest.raises(DomainError,match='VERSION_CONFLICT'):host.command('player1',m)

def test_behavior_entry_and_retry(host):
    config=copy.deepcopy(host.state()['configurations']['demo.actor']);config['revision']='2';config['behaviors']={'hurt':{'ruleId':'demo.damage'}}
    assert host.command('kp',message(host,'kp','configuration.put',config,'config'))['status']=='committed'
    result=host.command('player1',message(host,'player1','behavior.invoke',{'entityId':'actor-player1','event':'hurt','input':{'actor':'actor-player1','amount':7}},'hurt'))
    assert result['status']=='committed',result
    assert host.state()['entities']['actor-player1']['numbers']['hp']==4

def test_queue_and_internal_transport(host):
    t=InProcessTransport(host,'player1');m=message(host,'player1','entity.patch',{'id':'actor-player1','name':'端口'},'port')
    r=t.command(m);assert r==host.command('player1',m)==t.receipt('port')
    for _ in range(128):host.capacity.acquire()
    try:
        with pytest.raises(DomainError,match='LIMIT_EXCEEDED'):t.command(m)
    finally:
        for _ in range(128):host.capacity.release()

@pytest.mark.parametrize('factory',[MemoryDataStore,FileDataStore])
def test_storage_query_receipt_contract(factory,tmp_path):
    s=factory(tmp_path/'store') if factory is FileDataStore else factory()
    try:
        s.commit(0,{'entities':{'a':{'tag':'x'},'b':{'tag':'y'}},'commands':{'a:c':{'status':'committed'}}})
        assert s.query('entities',tag='x')==[{'tag':'x'}] and s.get_receipt('a','c')['status']=='committed'
    finally:s.close()

def test_machine_fixtures(host):
    from onlinecoc.contracts import validate_model,check
    root=Path(__file__).resolve().parents[2]/'contracts/fixtures'
    validate_model('Entity',json.loads((root/'entity-valid.json').read_text(encoding='utf-8')))
    with pytest.raises(DomainError):validate_model('Entity',json.loads((root/'entity-invalid-number.json').read_text(encoding='utf-8')))
    check('projection',host.project('player1'))
    check('receipt',host.receipt('player1','unknown'))

def test_host_storage_injection_and_author_helpers(tmp_path):
    from onlinecoc.host import Host
    from onlinecoc.lua_runtime import execute
    h=Host(tmp_path/'memory',bootstrap='test-password',store_factory=MemoryDataStore)
    try:
        src="return rule('helpers',{'target:actor'},function(r,target) assert(r.matches(target,'demo.actor')); assert(not r.hasTag(target,'missing')); return r.related(target,'owns-skill')[1] end,{mode='calculation'})"
        out=execute({'helpers.lua':src},{'kind':'run','rule':'helpers','mode':'calculation','input':{'target':'actor-player1'},'state':h.snapshot_for_execution(h.state()),'account':'player1'})
        assert out['result']=='skill-player1'
        assert invoke(h,'player1','demo.damage',{'actor':'actor-player1','amount':7})['status']=='committed'
    finally:h.close()
