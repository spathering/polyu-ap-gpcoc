"""Owner-scoped action feedback over the real public host API."""
import json
import uuid
from datetime import datetime
from harness import PACK, running, provision, Account


def last(account, operation):
    return next(e for e in reversed(account.state()['events']) if e['operation'] == operation)


def main():
    checks = []
    with running('feedback') as (runtime, password):
        kp, p1, p2 = provision(runtime, password)
        key = str(uuid.uuid4())
        args = {'attribute': 'dex', 'mode': 'advantage'}
        rolled = p1.action('check', args, key)
        event = last(p1, 'check')
        assert event['status'] == 'completed' and event['result'] == rolled
        assert rolled['rolled'] == min(rolled['first'], rolled['second'])
        assert p1.action('check', args, key) == rolled
        assert len([e for e in p1.state()['events'] if e['id'] == event['id']]) == 1
        assert all(e['account'] == 'player2' for e in p2.state()['events'])
        assert not any(e['id'] == event['id'] for e in p2.state()['events'])
        checks.append('automatic dice process and result persist once; feedback remains owner scoped')

        before = p1.state()['character']['numbers']
        slot = next(i for i in range(1, 21) if before['item' + str(i)] == 2)
        p1.action('inventory', {'operation': 'move', 'slot': slot, 'value': 8})
        changes = last(p1, 'inventory')['changes']
        assert any(c['key'] == 'slot8' and '火把' in c['after'] for c in changes)
        assert any(c['key'] == 'slot' + str(slot) and c['after'] == '空' for c in changes)
        p1.action('inventory', {'operation': 'light', 'slot': 8, 'value': 0})
        assert any(c['key'] == 'litSlot' and c['after'] == 8 for c in last(p1, 'inventory')['changes'])
        checks.append('inventory movements and light changes contain readable before/after values')

        checks_before = p1.state()['character']['numbers']['checks']
        requested = p1.action('request', {'kind': 'check', 'input': args, 'manual': True, 'text': '反馈人工检定'})
        pending = last(p1, 'request')
        assert pending['status'] == 'pending' and pending['changes'] == []
        assert p1.state()['character']['numbers']['checks'] == checks_before
        resolve_id = str(uuid.uuid4())
        ruling = {'requestId': requested['requestId'], 'approve': True, 'reason': '批准这次敏捷检定'}
        kp.action('resolve', ruling, resolve_id)
        reply = last(p1, 'resolve')
        assert reply['reason'] == ruling['reason'] and reply['status'] == 'approved'
        assert 'rolled' in reply['result'] and reply['mechanical']
        assert p1.state()['character']['numbers']['checks'] == checks_before + 1
        kp.action('resolve', ruling, resolve_id)
        assert len([e for e in p1.state()['events'] if e['id'] == reply['id']]) == 1
        denied = p1.action('request', {'kind': 'review', 'text': '请复核这次检定'})
        kp.action('resolve', {'requestId': denied['requestId'], 'approve': False, 'reason': '维持原结果'})
        assert last(p1, 'resolve')['status'] == 'rejected'
        assert last(p1, 'resolve')['changes'] == []
        assert p1.state()['character']['numbers']['checks'] == checks_before + 1
        checks.append('pending, approved and rejected stages reach original player without early or duplicate execution')

        transfer = p1.action('request', {'kind': 'transfer', 'slot': 8, 'targetAccount': 'player2', 'destination': 8, 'text': '交给豆叶火把'})
        kp.action('resolve', {'requestId': transfer['requestId'], 'approve': True, 'reason': '同处一地，可以交接'})
        assert any(c['key'] == 'slot8' and c['after'] == '空' for c in last(p1, 'resolve')['changes'])
        assert any(c['key'] == 'slot8' and '火把' in c['after'] for c in last(p2, 'resolve')['changes'])
        actor = p2.state()['character']['instanceId']
        hp = p2.state()['character']['numbers']['hp']
        kp.action('actor.update', {'id': actor, 'numbers': {'hp': max(0, hp - 1)}})
        assert any(c['key'] == 'hp' and c['before'] == hp and c['after'] == max(0, hp - 1) for c in last(p2, 'actor.update')['changes'])
        kp.action('world', {'operation': 'round'})
        assert '回合' in last(p1, 'world')['result']['message']
        checks.append('transfers notify both owners; KP resource changes and exploration updates reach affected players')

        kp.action('location.publish', {'index': 2})
        move = p1.action('request', {'kind': 'travel', 'destination': 2})
        assert move['status'] == 'automatic'
        assert any(c['key'] == 'location' and c['after'] == '主门' for c in last(p1, 'request')['changes'])
        serialized = json.dumps(p1.state()['events'], ensure_ascii=False)
        assert 'truth' not in serialized and 'sv.npc' not in serialized
        checks.append('movement explains destination; events do not contain hidden locations or NPC snapshots')

        # Interrupt only the package feedback phase after the host committed the die.
        # Loading the persisted package must recover its executed result, not reroll.
        from unittest.mock import patch
        from package import Package
        recovery_id = str(uuid.uuid4())
        before_checks = p1.state()['character']['numbers']['checks']
        with patch.object(runtime.package, 'record_feedback', side_effect=ConnectionError('feedback interrupted')):
            response = p1.http.post(p1.prefix + '/package/action', json={'id': recovery_id, 'operation': 'check', 'args': args})
            assert response.status_code == 503
        runtime.package = Package(runtime.package.path)
        p1.action('check', args, recovery_id)
        assert p1.state()['character']['numbers']['checks'] == before_checks + 1
        assert len([e for e in p1.state()['events'] if e['id'] == 'player1:' + recovery_id]) == 1
        checks.append('interrupted feedback generation resumes the committed result without rerolling')

        saved = p1.state()['events']
        runtime.process.terminate()
        runtime.process.wait(timeout=10)
        runtime.start()
        runtime.package = Package(runtime.package.path)
        p1 = Account(runtime.origin, 'player1', password, 'player1')
        assert p1.state()['events'] == saved
        assert p1.action('check', args, key) == rolled
        assert p1.state()['events'] == saved
        checks.append('feedback and fixed-id action receipts survive host and package restart')
    result = {'passed': True, 'checkedAt': datetime.now().astimezone().isoformat(), 'checks': checks}
    (PACK / 'tests/feedback-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
