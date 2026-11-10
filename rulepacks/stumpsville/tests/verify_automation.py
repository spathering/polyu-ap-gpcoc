"""Real-host acceptance for automatic rulings, manual requests and legacy upgrade."""
import copy
from datetime import datetime
import json
import uuid
from harness import PACK, Account, running, provision


def main():
    checks = []
    with running('automation') as (runtime, password):
        kp, p1, p2 = provision(runtime, password)
        assert p1.state()['automation'] == {'enabled': True, 'ready': True}
        assert all(v==0 for k,v in p1.state()['session']['numbers'].items() if k.startswith('door'))
        kp.action('door', {'edge':'3-4','status':'closed'})
        kp.action('door', {'edge':'3-4','status':'open'})
        assert p1.state()['session']['numbers']['door3_4']==0
        actor = p1.state()['character']['instanceId']
        other = p2.state()['character']['instanceId']
        kp.action('location.publish', {'index': 2})
        kp.action('location.publish', {'index': 3})
        target = next(x for x in p1.state()['locations'] if x['index'] == 2)['entityId']
        destination3 = next(x for x in p1.state()['locations'] if x['index'] == 3)['entityId']
        original = p1.state()['character']['numbers']['location']
        for target_actor, target_id in [(other, target), (actor, destination3)]:
            rejected = p1.command('action.invoke', {'actionId': 'sv.travel.auto', 'input': {'actor': target_actor, 'destination': target_id}}, True)
            assert rejected.get('status') == 'rejected', rejected
        assert p1.state()['character']['numbers']['location'] == original
        key = str(uuid.uuid4())
        moved = p1.action('request', {'kind': 'travel', 'destination': 2}, key)
        assert moved['status'] == 'automatic' and p1.state()['character']['numbers']['location'] == 2
        assert p1.action('request', {'kind': 'travel', 'destination': 2}, key) == moved
        assert p2.state()['character']['numbers']['location'] == 1
        assert not [x for x in kp.state()['requests'] if x['status'] == 'pending']
        closed = p1.command('action.invoke', {'actionId': 'sv.travel.auto', 'input': {'actor': actor, 'destination': destination3}}, True)
        assert closed.get('status') == 'rejected', closed
        hidden = next(x for x in kp.request('/api/v1/view')['entities'].values() if x['configurationId']=='sv.location' and x['numbers']['index']==4)
        assert p1.command('action.invoke', {'actionId':'sv.travel.auto','input':{'actor':actor,'destination':hidden['instanceId']}}, True).get('status')=='rejected'
        checks.append('default automatic travel; idempotent result; host rejects foreign, hidden, nonadjacent and closed destinations')

        kp.action('door', {'edge': '2-3', 'status': 'open'})
        manual = p1.action('request', {'kind': 'travel', 'destination': 3, 'manual': True})
        assert manual['status'] == 'pending' and p1.state()['character']['numbers']['location'] == 2
        kp.action('resolve', {'requestId': manual['requestId'], 'approve': True, 'reason': '允许通行'})
        assert p1.state()['character']['numbers']['location'] == 3
        checks.append('explicit KP request overrides automatic travel until approved')

        before = p1.state()['character']['numbers']['checks']
        manual_check = p1.action('request', {'kind': 'check', 'input': {'attribute': 'dex', 'mode': 'normal'}, 'manual': True})
        assert p1.state()['character']['numbers']['checks'] == before
        ruling_key = str(uuid.uuid4())
        ruled = kp.action('resolve', {'requestId': manual_check['requestId'], 'approve': True}, ruling_key)
        assert kp.action('resolve', {'requestId': manual_check['requestId'], 'approve': True}, ruling_key) == ruled
        assert p1.state()['character']['numbers']['checks'] == before + 1
        assert next(x for x in p1.state()['requests'] if x['id']==manual_check['requestId'])['result']['rolled']
        review = p1.action('request', {'kind':'review','receiptId':key,'text':'请复核移动判定'})
        kp.action('resolve', {'requestId':review['requestId'],'approve':True,'reason':'确认原结果，无需重复移动'})
        assert p1.state()['character']['numbers']['location'] == 3
        assert all(x['id'] != review['requestId'] for x in p2.state()['requests'])
        assert '只能复核' in p2.action('request', {'kind':'review','receiptId':key,'text':'other receipt'}, allow_error=True)['code']
        free = p1.action('request', {'kind':'interact','text':'调查未知机关'})
        assert free['status']=='pending'
        checks.append('manual checks roll once after approval; own event review does not replay effects; narrative actions remain pending')

        assert '主持权限' in p1.action('automation.configure', {'enabled':False},allow_error=True)['code']
        kp.action('automation.configure', {'enabled': False})
        assert p1.state()['automation']['enabled'] is False
        before = p1.state()['character']['numbers']
        queued_check = p1.action('check', {'attribute':'str','mode':'normal'})
        queued_use = p1.action('inventory', {'operation':'use','slot':5,'value':0})
        assert queued_check['status']=='pending' and queued_use['status']=='pending'
        assert p1.state()['character']['numbers']==before
        for action, inputs in [('sv.check', {'actor':actor,'attribute':'dex','mode':'normal'}),
                               ('sv.inventory', {'actor':actor,'operation':'use','slot':5,'value':0}),
                               ('sv.check.core', {'actor':actor,'attribute':'dex','mode':'normal'}),
                               ('sv.adjudicate', {'actor':actor,'kind':'check','attribute':'dex','mode':'normal','operation':'move','slot':0,'value':0})]:
            rejected = p1.command('action.invoke', {'actionId':action,'input':inputs},True)
            assert rejected.get('status')=='rejected' or rejected.get('code') == 'PERMISSION_DENIED', (action, rejected)
        kp.action('resolve', {'requestId':queued_use['requestId'],'approve':True})
        assert p1.state()['character']['numbers']['uses5']==before['uses5']-1
        kp.action('resolve', {'requestId':queued_check['requestId'],'approve':False,'reason':'无需检定'})
        assert p1.state()['character']['numbers']['checks']==before['checks']
        checks.append('KP toggle gates public host actions; players cannot bypass via raw API or internal rules; manual inventory executes once')

        kp.action('room', {'status':'paused'})
        assert '暂停' in p1.action('inventory', {'operation':'use','slot':5,'value':0},allow_error=True)['code']
        p1.action('request', {'kind':'review','text':'暂停时请求说明'})
        kp.action('room', {'status':'active'})
        runtime.process.terminate(); runtime.process.wait(timeout=10); runtime.start()
        from package import Package
        runtime.package = Package(runtime.package.path)
        kp, p1 = [Account(runtime.origin, n, password, n) for n in ('kp','player1')]
        assert not p1.state()['automation']['enabled']
        assert p1.action('request', {'kind':'travel','destination':2}, key)==moved
        kp.action('automation.configure', {'enabled':True})
        p1.action('ready', {'ready':False})
        assert p1.command('action.invoke', {'actionId':'sv.travel.auto','input':{'actor':actor,'destination':destination3}},True).get('status')=='rejected'
        checks.append('pause and readiness enforced; settings and original receipts survive host/package restart')

        # An older persisted rule revision must be upgraded without recreating actors.
        legacy = kp.request('/package/bundle')
        for name in ('automation.lua','auto-travel.lua','adjudicate.lua','check-core.lua','inventory-core.lua'): legacy['sources'].pop(name)
        legacy['sources']['check.lua']=(PACK/'rules/check-core.lua').read_text(encoding='utf-8').replace("'sv.check.core'", "'sv.check'").replace('public=false, ', '')
        legacy['sources']['inventory.lua']=(PACK/'rules/inventory-core.lua').read_text(encoding='utf-8').replace("'sv.inventory.core'", "'sv.inventory'").replace('public=false, ', '')
        revision = kp.action('rules.stage', {'bundle':legacy})['revision']
        kp.action('rules.activate', {'revision':revision})
        assert not p1.state()['automation']['ready']
        numbers = copy.deepcopy(p1.state()['character']['numbers'])
        kp.action('rules.install')
        assert p1.state()['automation']=={'enabled':True,'ready':True}
        assert p1.state()['character']['numbers']==numbers
        checks.append('old rule revision upgrades in place without changing character resources')
    result={'passed':True,'checkedAt':datetime.now().astimezone().isoformat(),'checks':checks}
    (PACK/'tests/automation-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
