"""Scene upgrades, interrupted execution and finite inventory over real HTTP."""
import copy
import json
import uuid
from datetime import datetime
from unittest.mock import patch
from harness import PACK, running, provision
from package import Package


def main():
    checks = []
    with running('scene-recovery') as (runtime, password):
        kp, p1, _ = provision(runtime, password)
        actor = p1.state()['character']['instanceId']
        identity_files = sorted(str(p.relative_to(runtime.data)) for p in (runtime.data/'host/identity').rglob('*') if p.is_file())
        # Simulate an existing custom ruleset without scene automation.
        legacy = copy.deepcopy(runtime.package.state['ruleRevisions'][runtime.package.state['activeRevision']])
        legacy['sources'].pop('scene.lua')
        legacy['data'].pop('scene-actions.json')
        legacy['sources']['check.lua'] += '\n-- preserve this custom rule annotation\n'
        revision = kp.command('rule.stage', legacy)['result']
        kp.command('rule.activate', {'revision': revision})
        runtime.package.state['ruleRevisions'][revision] = legacy
        runtime.package.state['activeRevision'] = revision
        runtime.package.state.pop('sceneId')
        runtime.package.save()
        before = p1.state()['character']['numbers']
        assert not p1.state()['sceneAutomation']['ready']
        kp.action('scene.install')
        assert p1.state()['sceneAutomation']['ready']
        assert p1.state()['character']['numbers'] == before
        active = runtime.package.state['ruleRevisions'][runtime.package.state['activeRevision']]
        assert active['sources']['check.lua'] == legacy['sources']['check.lua']
        assert identity_files == sorted(str(p.relative_to(runtime.data)) for p in (runtime.data/'host/identity').rglob('*') if p.is_file())
        checks.append('scene upgrade preserves custom rules and character resources without adding an account or identity file')

        def submit(action, choice):
            key = str(uuid.uuid4())
            args = {'action': action, 'choice': choice}
            queued = p1.action('scene.action', args, key)
            assert queued['status'] == 'processing'
            task = kp.request('/package/scene-executor', {})['jobs'][0]
            return key, args, task

        def finish(task):
            return kp.action('scene.autorun', {'jobId': task['id']}, task['commandId'])

        key, args, task = submit('tunnel-ground', 'inspect')
        # Host effects committed, but event publication fails before completion.
        with patch.object(runtime.package, 'record_feedback', side_effect=ConnectionError('scene feedback interrupted')):
            response = kp.http.post(kp.prefix+'/package/action', json={'id':task['commandId'], 'operation':'scene.autorun', 'args':{'jobId':task['id']}})
            assert response.status_code == 503, response.text
        assert runtime.package.state['autoSceneQueue'][task['id']]['status'] == 'finishing'
        assert '恢复' in p1.action('check', {'attribute':'dex','mode':'normal'}, allow_error=True)['code']
        runtime.package = Package(runtime.package.path)
        assert kp.request('/package/scene-executor', {})['jobs'][0] == task
        result = finish(task)
        assert p1.action('scene.action', args, key) == result
        assert not runtime.package.state.get('scenePending')
        events = [e for e in p1.state()['events'] if e['id'] == 'player1:'+key]
        assert len(events) == 1 and events[0]['status'] == 'completed'
        assert not kp.request('/package/scene-executor', {})['jobs']
        assert finish(task) == result
        checks.append('interrupted feedback resumes after reload; the original waiting card becomes one completed result; duplicate executor delivery is idempotent')

        kp.action('actor.update', {'id':actor,'numbers':{'dexMax':20,'dex':20}})
        old_checks = p1.state()['character']['numbers']['checks']
        key, args, task = submit('tunnel-cheese', 'careful')
        # Interrupt package publication immediately after the atomic Lua transaction.
        with patch('scenes.apply_numbers', side_effect=ConnectionError('scene publication interrupted')):
            response = kp.http.post(kp.prefix+'/package/action', json={'id':task['commandId'], 'operation':'scene.autorun', 'args':{'jobId':task['id']}})
            assert response.status_code == 503, response.text
        committed = p1.state()['character']['numbers']
        assert committed['checks'] == old_checks+1
        runtime.package = Package(runtime.package.path)
        result = finish(task)
        assert result['checks'][0]['passed']
        assert p1.state()['character']['numbers'] == committed
        assert runtime.package.state['sceneState']['cheese1'] == 0
        assert p1.action('scene.action', args, key) == result
        checks.append('interruption after the host transaction cannot reroll the save, duplicate cheese or lose the finite-stock decrement')

        # Fill all normal and overflow cells; preflight must leave finite stock alone.
        full = {'location':10}
        full.update({'item'+str(i):6 for i in range(1,21)})
        full.update({'uses'+str(i):0 for i in range(1,21)})
        kp.command('entity.update', {'id':actor,'numbers':full})
        key, args, task = submit('cave-cheese','take')
        result = finish(task)
        assert result['outcome'] == 'blocked' and result['checks'] == []
        assert runtime.package.state['sceneState']['cheese10'] == 8
        assert p1.state()['character']['numbers']['checks'] == committed['checks']
        checks.append('full inventory blocks before rolling or reducing shared stock')

        kp.action('automation.configure', {'enabled':False})
        pending = p1.action('scene.action', {'action':'cave-cheese','choice':'inspect'})
        assert pending['status'] == 'pending'
        assert not kp.request('/package/scene-executor', {})['jobs']
        kp.action('automation.configure', {'enabled':True})
        assert not kp.request('/package/scene-executor', {})['jobs']
        assert any(r['id'] == pending['requestId'] and r['status'] == 'pending' for r in kp.state()['requests'])
        checks.append('deliberate global manual mode remains manual when automation is re-enabled')
    report = {'passed':True, 'checkedAt':datetime.now().astimezone().isoformat(), 'checks':checks}
    (PACK/'tests/scene-recovery-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
