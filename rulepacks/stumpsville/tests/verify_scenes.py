"""Preset integration through the same authenticated KP-page executor API as UI."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from harness import PACK, running, provision, Account


def main():
    checks, actions = [], set()
    with running('scene') as (runtime, password):
        kp, p1, p2 = provision(runtime, password)
        assert p1.state()['sceneAutomation'] == {'ready': True, 'executorOnline': False}
        key = str(uuid.uuid4())
        queued = p1.action('scene.action', {'action': 'tunnel-ground', 'choice': 'inspect'}, key)
        assert queued['status'] == 'processing' and not kp.state()['requests']
        assert p1.request('/package/scene-executor', {}, allow_error=True).get('code') == '需要主持权限'
        task = kp.request('/package/scene-executor', {})['jobs'][0]
        kp.action('scene.autorun', {'jobId': task['id']}, task['commandId'])
        assert p1.state()['sceneAutomation']['executorOnline']
        checks.append('offline executor queues automatic work separately from KP requests; only an existing authenticated KP page can execute it')
        def act(action, choice, account=p1, key=None):
            key = key or str(uuid.uuid4())
            args = {'action': action, 'choice': choice}
            result = account.action('scene.action', args, key)
            for _ in range(12):
                if result['status'] != 'processing': break
                for task in kp.request('/package/scene-executor', {})['jobs']:
                    kp.action('scene.autorun', {'jobId': task['id']}, task['commandId'])
                result = account.action('scene.action', args, key)
            assert result['sceneAction'] == action and result['status'] == 'completed', result
            assert result['narrative'] and result['process']
            actions.add(action)
            return result
        def move(destination):
            result = p1.action('request', {'kind': 'travel', 'destination': destination})
            assert result['status'] == 'automatic', result

        actor = p1.state()['character']['instanceId']
        kp.action('actor.update', {'id': actor, 'numbers': {'dexMax': 20, 'dex': 20, 'wilMax': 20, 'wil': 20, 'maxHp': 100, 'hp': 100}})
        first = act('tunnel-ground', 'inspect', key=key)
        assert first['checks'] == [] and any(x['index'] == 2 for x in p1.state()['locations'])
        assert act('tunnel-ground', 'inspect', key=key) == first
        act('tunnel-cheese', 'inspect')
        safe = act('tunnel-cheese', 'careful')
        assert safe['checks'][0]['passed'] and p1.state()['character']['numbers']['checks'] == 1
        assert any(c['title'] == '入口地面的压痕' for place in p1.state()['locations'] for c in place['clues'])
        assert all(c['id'] != 'tunnel-trap' for place in p2.state()['locations'] for c in place['clues'])
        assert act('tunnel-cheese', 'take')['outcome'] == 'blocked'
        move(2)
        act('gate-handle', 'inspect')
        opened = act('gate-open', 'brace')
        assert any(x['index'] == 3 for x in p1.state()['locations'])
        assert kp.state()['doors']['2-3'] == 'open' and opened['cost'] == 1
        move(3)
        act('courtyard-pool', 'inspect')
        old_money = p1.state()['character']['numbers']['pips']
        money = act('courtyard-pool', 'money')
        assert money['checks'][0]['passed']
        assert p1.state()['character']['numbers']['pips'] == old_money + 140
        assert act('courtyard-pool', 'money')['outcome'] == 'blocked'
        act('courtyard-ladders', 'inspect')
        assert {4, 5, 6, 7, 8} <= {x['index'] for x in p1.state()['locations']}
        checks.append('entry-to-courtyard loop reveals routes, resolves a real save, disables a trap, consumes rope and grants finite money without per-action KP intervention')

        move(4)
        pots = act('house-pots', 'search')
        count = next(x for x in kp.state()['allLocations']['4']['stock'] if x['item'] == 8)['count']
        assert 1 <= count <= 6 and len(pots['rolls']) == 1
        assert not act('house-pots', 'search')['rolls']
        act('house-pots', 'take')
        assert next(x for x in kp.state()['allLocations']['4']['stock'] if x['item'] == 8)['count'] == count - 1
        move(3); move(5)
        act('house-painting', 'inspect')
        assert any(c['id'] == 'festival' for place in p1.state()['locations'] for c in place['clues'])
        move(3); move(6)
        act('web-inspect', 'inspect'); act('web-call', 'whisper')
        rescue = act('web-call', 'rescue')
        assert rescue['checks'][0]['passed'] and runtime.package.state['sceneState']['villagersFreed'] == 1
        move(3); move(7)
        rats = act('hall-observe', 'inspect')
        assert len(rats['rolls']) == 2
        assert not act('hall-observe', 'inspect')['rolls']
        deal = act('hall-negotiate', 'talk')
        assert deal['checks'][0]['passed'] and kp.state()['doors']['7-8'] == 'open'
        assert any(p1.state()['character']['numbers']['item'+str(i)] == 9 for i in range(1, 21))
        move(8)
        act('factory-equipment', 'inspect')
        act('factory-equipment', 'paddle'); act('factory-equipment', 'cloth')
        act('factory-exits', 'survey'); act('factory-exits', 'iron')
        assert act('factory-exits', 'iron')['cost'] == 0
        move(9)
        act('cage-gate', 'inspect'); act('cage-listen', 'listen'); act('cage-listen', 'flute')
        act('cage-gate', 'open'); move(10)
        act('cave-cheese', 'inspect'); act('cave-sleeper', 'observe'); act('cave-sleeper', 'talk')
        act('cave-cheese', 'take')
        assert any(c['id'] == 'north' for place in p1.state()['locations'] for c in place['clues'])
        assert runtime.package.state['sceneState']['cheese10'] == 7
        assert len(actions) == 18 and not any(r['status'] == 'pending' for r in kp.state()['requests'])
        checks.append('all 18 preset actions produce narrative plus discoveries, persistent world facts, finite rewards or doors across the ten-room exploration loop')

        # A genuine failed die roll: close the door between attempts, retain all
        # authoritative dice, and use ample HP so fixture failures cannot kill it.
        kp.command('entity.update', {'id': actor, 'numbers': {'location': 9, 'dex': 1, 'hp': 100, 'armor': 0}})
        failed = None
        for _ in range(12):
            kp.action('door', {'edge': '9-10', 'status': 'closed'})
            attempt = act('cage-listen', 'sneak')
            if attempt['outcome'] == 'failure':
                failed = attempt
                break
        assert failed and failed['damage']['damage'] > 0 and failed['checks'][0]['passed'] is False
        assert any(r['sides'] == 8 for r in failed['rolls'])
        assert kp.state()['doors']['9-10'] == 'closed'
        assert p1.state()['character']['numbers']['hp'] < 100
        checks.append('failed risky preset exposes raw save/damage rolls, applies HP loss and leaves its intended door closed')

        bad = p1.action('scene.action', {'action': 'cave-cheese', 'choice': 'take'}, allow_error=True)
        assert '当前地点' in bad['code']
        bad = p1.action('scene.action', {'action': 'cage-listen', 'choice': 'award-everything'}, allow_error=True)
        assert '不存在' in bad['code']
        private_id = runtime.package.state['sceneId']
        world_id = kp.state()['world']['instanceId']
        denied = p1.command('action.invoke', {'actionId': 'sv.scene.resolve', 'input': {'actor': actor, 'scene': private_id, 'world': world_id, 'action': 'cage-listen', 'choice': 'listen'}}, True)
        assert denied.get('code') == 'PERMISSION_DENIED'
        assert 'sceneState' not in p1.state() and 'truth' not in json.dumps(p1.state(), ensure_ascii=False)
        assert private_id not in p1.request('/api/v1/view')['entities']
        checks.append('wrong-room, forged-choice and raw privileged-rule requests cannot bypass server validation or reveal private scene state')

        pending = p1.action('scene.action', {'action': 'cage-listen', 'choice': 'listen', 'manual': True})
        assert pending['status'] == 'pending'
        kp.action('resolve', {'requestId': pending['requestId'], 'approve': True, 'reason': '同意这个做法'})
        assert p1.state()['events'][-1]['result']['sceneAction'] == 'cage-listen'
        custom = p1.action('request', {'kind': 'free', 'text': '用未知法术改变蛇的记忆'})
        assert custom['status'] == 'pending'
        checks.append('explicit manual selection and out-of-preset free intent remain KP requests; approving a preset executes its actual recipe')

        # Competing clients cannot claim the last shared cheese twice.
        for account in (p1, p2):
            kp.command('entity.update', {'id': account.state()['character']['instanceId'], 'numbers': {'location': 10}})
        for _ in range(6): act('cave-cheese', 'take')
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda account: act('cave-cheese', 'take', account), (p1, p2)))
        assert sorted(x['outcome'] for x in results) == ['blocked', 'success']
        assert runtime.package.state['sceneState']['cheese10'] == 0
        checks.append('concurrent players cannot duplicate the last shared item')

        from package import Package
        saved = runtime.package.state['sceneState'].copy()
        runtime.package = Package(runtime.package.path)
        assert runtime.package.state['sceneState'] == saved
        assert p1.action('scene.action', {'action':'tunnel-ground','choice':'inspect'}, key) == first
        assert act('cave-cheese', 'take')['outcome'] == 'blocked'
        checks.append('scene flags, depleted stock and original action receipts survive package reload')
    report = {'passed': True, 'checkedAt': datetime.now().astimezone().isoformat(),
              'authority': 'existing authenticated KP-page executor; no service identity or stored KP credential',
              'presetActions': sorted(actions), 'checks': checks}
    (PACK/'tests/scene-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
