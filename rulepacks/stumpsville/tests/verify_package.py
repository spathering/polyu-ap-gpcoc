"""Black-box package acceptance against an isolated real OnlineCOC host."""
import json
import sys
import uuid
import copy
import subprocess
from datetime import datetime
from websockets.sync.client import connect
from harness import PACK, Account, running, provision


def main():
    checks = []
    with running() as (runtime, password):
        kp, p1, p2 = provision(runtime, password)
        checks.append('real host initialized; KP + two scoped player sessions; approved characters')
        assert len(kp.state()['allLocations']) == 10
        assert len(p1.state()['locations']) == 1
        assert 'allLocations' not in p1.state()
        a = p1.state()['character']['instanceId']
        b = p2.state()['character']['instanceId']
        assert a != b
        check_id = str(uuid.uuid4())
        first = p1.action('check', {'attribute': 'dex', 'mode': 'normal'}, check_id)
        assert p1.action('check', {'attribute': 'dex', 'mode': 'normal'}, check_id) == first
        assert p1.state()['character']['numbers']['checks'] == 1
        checks.append('check receipt replay does not reroll')
        conflict = p1.action('check', {'attribute': 'str', 'mode': 'normal'}, check_id, True)
        assert '不可更改' in conflict['code']
        forbidden = p2.command('action.invoke', {'actionId': 'sv.inventory', 'input': {'actor': a, 'operation': 'use', 'slot': 3, 'value': 0}}, True)
        assert forbidden.get('status') == 'rejected', forbidden
        assert '主持权限' in p1.action('world', {'operation': 'round', 'round': 0}, allow_error=True)['code']
        p1.action('note', {'text': 'PRIVATE-NOTE-ONE'})
        assert 'PRIVATE-NOTE-ONE' not in json.dumps(p2.state())
        assert 'PRIVATE-NOTE-ONE' not in json.dumps(kp.state())
        assert '池底' not in json.dumps(p1.state(), ensure_ascii=False)
        assert p1.http.get('/sessions/player1/package/bundle').status_code == 403
        assert p1.http.get('/sessions/player1/config/game.json').status_code == 404
        assert p1.http.post('/sessions/player1/package/action', headers={'Origin': 'https://invalid.example'}, json={}).status_code == 400
        checks.append('private projections, ownership and role/origin boundaries')
        shared_id = str(uuid.uuid4())
        left = p1.action('request', {'kind': 'free', 'text': 'player one'}, shared_id)
        right = p2.action('request', {'kind': 'free', 'text': 'player two'}, shared_id)
        assert left['requestId'] != right['requestId']
        assert len([x for x in kp.state()['requests'] if x['id'] in {left['requestId'], right['requestId']}]) == 2
        kp.action('resolve', {'requestId': left['requestId'], 'approve': False})
        kp.action('resolve', {'requestId': right['requestId'], 'approve': False})
        old_location = kp.state()['allLocations']['2']
        kp.action('location.save', {'index': 2, 'revision': 0, 'description': 'must not appear', 'truth': 'x'*6001}, allow_error=True)
        assert kp.state()['allLocations']['2'] == old_location

        p1.action('inventory', {'operation': 'light', 'slot': 2, 'value': 0})
        for turn in range(6):
            key = str(uuid.uuid4())
            result = kp.action('world', {'operation': 'round', 'round': turn}, key)
            assert kp.action('world', {'operation': 'round', 'round': turn}, key) == result
            if turn == 2:
                p1.action('inventory', {'operation': 'extinguish', 'slot': 2, 'value': 0})
                p1.action('inventory', {'operation': 'light', 'slot': 2, 'value': 0})
        assert p1.state()['character']['numbers']['uses2'] == 2
        assert p2.state()['character']['numbers']['uses2'] == 3
        checks.append('six rounds consume only lit torch; relighting and retry preserve clock')

        before = p1.state()['character']['numbers']
        failure = kp.action('grant', {'actor': a, 'item': 7, 'slot': 5, 'uses': 0}, allow_error=True)
        assert failure.get('status') == 'rejected', failure
        assert p1.state()['character']['numbers'] == before
        p1.action('inventory', {'operation': 'move', 'slot': 5, 'value': 11})
        p1.action('inventory', {'operation': 'move', 'slot': 6, 'value': 12})
        kp.action('grant', {'actor': a, 'item': 7, 'slot': 5, 'uses': 0})
        assert p1.action('check', {'attribute': 'str', 'mode': 'advantage'})['mode'] == 'disadvantage'
        bad = p1.action('inventory', {'operation': 'move', 'slot': 1, 'value': 8}, allow_error=True)
        assert bad.get('status') == 'rejected'
        checks.append('four-slot collision rolls back; overflow applies disadvantage')

        req = p1.action('request', {'kind': 'transfer', 'slot': 11, 'targetAccount': 'player2', 'destination': 7, 'text': 'transfer ration'})
        kp.action('resolve', {'requestId': req['requestId'], 'approve': True, 'reason': '同地点转交'})
        assert p1.state()['character']['numbers']['item11'] == 0
        assert p2.state()['character']['numbers']['item7'] == 3
        checks.append('KP-approved transfer moves item atomically between private characters')

        kp.action('location.save', {'index': 2, 'revision': 0, 'description': 'PUBLIC-GATE', 'truth': 'SECRET-GATE'})
        kp.action('location.publish', {'index': 2})
        assert 'PUBLIC-GATE' in json.dumps(p1.state()) and 'SECRET-GATE' not in json.dumps(p1.state())
        req = p1.action('request', {'kind': 'travel', 'destination': 2})
        kp.action('resolve', {'requestId': req['requestId'], 'approve': True})
        kp.action('location.publish', {'index': 3})
        assert '尚未开放' in p1.action('request', {'kind': 'travel', 'destination': 3}, allow_error=True)['code']
        kp.action('door', {'edge': '2-3', 'status': 'open'})
        req = p1.action('request', {'kind': 'travel', 'destination': 3})
        kp.action('resolve', {'requestId': req['requestId'], 'approve': True})
        assert p1.state()['character']['numbers']['location'] == 3
        assert p2.state()['character']['numbers']['location'] == 1
        kp.action('location.publish', {'index': 5})
        assert not next(x for x in p1.state()['locations'] if x['index'] == 5)['clues']
        kp.action('location.publish', {'index': 5, 'clues': ['festival']})
        assert next(x for x in p1.state()['locations'] if x['index'] == 5)['clues']
        checks.append('01→02→03 travel; closed doors enforced; selected clues revealed separately')

        pot_id = str(uuid.uuid4())
        pots = kp.action('generate', {'kind': 'pots'}, pot_id)
        assert kp.action('generate', {'kind': 'pots'}, pot_id) == pots
        assert kp.state()['allLocations']['4']['stock'][0]['count'] == pots['count']
        assert kp.action('generate', {'kind': 'pots'}, allow_error=True).get('status') == 'rejected'
        take_id = str(uuid.uuid4())
        taken = kp.action('stock.take', {'index': 1, 'actor': b, 'item': 6, 'slot': 8}, take_id)
        assert kp.action('stock.take', {'index': 1, 'actor': b, 'item': 6, 'slot': 8}, take_id) == taken
        assert kp.state()['allLocations']['1']['stock'][0]['count'] == 0
        checks.append('persistent one-time generation; stock grants and retries cannot duplicate treasure')

        kp.action('actor.update', {'id': b, 'numbers': {'hp': 0, 'str': 6, 'dex': 7, 'wil': 8}})
        kp.action('rest', {'actor': b, 'kind': 'long', 'attribute': 'str'})
        numbers = p2.state()['character']['numbers']
        assert numbers['hp'] == numbers['maxHp'] and numbers['str'] == 6 and numbers['dex'] == 7 and numbers['wil'] == 8
        kp.action('rest', {'actor': b, 'kind': 'long', 'attribute': 'str'})
        numbers = p2.state()['character']['numbers']
        assert numbers['str'] > 6 and numbers['dex'] == 7 and numbers['wil'] == 8
        snake = next(x for x in kp.state()['npcs'] if x['name'] == '守卫蛇')['instanceId']
        damage = kp.action('damage', {'actor': snake, 'amount': 5, 'attribute': 'str'})
        assert damage['hp'] == 9 and damage['damage'] == 3
        assert 1 <= kp.action('morale', {'actor': snake})['rolled'] <= 20
        checks.append('long rest restores HP or one attribute; armor and WIL morale save')

        message = p1.action('chat', {'operation': 'chat.message.send', 'input': {'channelId': 'general', 'text': '<script>plain text</script>'}})
        p1.action('chat', {'operation': 'chat.message.edit', 'input': {'channelId': 'general', 'messageId': message['messageId'], 'revision': message['revision'], 'text': 'edited'}})
        p1.action('share.receipt', {'receiptId': check_id, 'channelId': 'general'})
        direct = p1.action('chat', {'operation': 'chat.direct.open', 'input': {'accountId': 'player2'}})['channelId']
        p1.action('chat', {'operation': 'chat.message.send', 'input': {'channelId': direct, 'text': 'PRIVATE-DIRECT'}})
        assert kp.request('/api/v1/chat/history', {'channelId': direct}, True).get('code') == 'NOT_VISIBLE'
        group = kp.action('chat', {'operation': 'chat.channel.create', 'input': {'name': 'one only', 'kind': 'group', 'participants': ['kp', 'player1']}})['channelId']
        assert group not in p2.state()['channels']
        checks.append('chat edit, server-derived receipt summary, direct/group audience isolation')

        kp.action('recap', {'recapDraft': 'PUBLIC-RECAP', 'recapPrivate': 'SECRET-RECAP', 'publish': True})
        assert p2.state()['recap'] == 'PUBLIC-RECAP' and 'SECRET-RECAP' not in json.dumps(p2.state())
        kp.action('room', {'status': 'paused'})
        assert '暂停' in p1.action('check', {'attribute': 'dex', 'mode': 'normal'}, allow_error=True)['code']
        kp.action('room', {'status': 'active'})
        checks.append('published recap excludes private notes; pause rejects gameplay')

        content = kp.request('/package/bundle')
        revision = kp.action('rules.stage', {'bundle': content})['revision']
        before = p2.state()['character']['numbers']
        preview = kp.action('rules.preview', {'revision': revision, 'rule': 'sv.check', 'input': {'actor': b, 'attribute': 'dex', 'mode': 'normal'}})
        assert p2.state()['character']['numbers'] == before
        kp.action('rules.activate', {'revision': revision})
        backup = kp.action('backup')
        assert backup['host'] and backup['packageFile']
        checks.append('stage, isolated preview, activate and paired backup')

        cookie = '; '.join(f'{x.name}={x.value}' for x in p1.http.cookies.jar)
        with connect(runtime.origin.replace('http://', 'ws://') + '/sessions/player1/api/v1/connect', origin=runtime.origin, additional_headers={'Cookie': cookie}, proxy=None) as ws:
            event = json.loads(ws.recv(timeout=10))
            assert event['type'] == 'snapshot.begin', event
        checks.append('authenticated scoped WebSocket proxy delivers host snapshots')

        from package import Package
        stored = copy.deepcopy(runtime.package.state)
        runtime.process.terminate()
        runtime.process.wait(timeout=10)
        runtime.start()
        runtime.package = Package(runtime.package.path)
        assert runtime.package.state == stored
        kp, p1 = [Account(runtime.origin, name, password, name) for name in ('kp', 'player1')]
        assert p1.action('check', {'attribute': 'dex', 'mode': 'normal'}, check_id) == first
        assert p1.state()['character']['numbers']['uses2'] == 2
        assert p1.state()['note'] == 'PRIVATE-NOTE-ONE'
        checks.append('host and adapter restart preserve resources, notes and idempotent receipts')
        # Restore the paired snapshot into a second, previously absent data directory.
        runtime.process.terminate()
        runtime.process.wait(timeout=10)
        restored = runtime.data.parent / (runtime.data.name + '-restored')
        stored_backup = json.loads(__import__('pathlib').Path(backup['packageFile']).read_text(encoding='utf-8'))
        restored.mkdir()
        restored_process = subprocess.run(runtime.command[:-1] + [str(restored / 'host'), 'restore', '--bundle',
            str(runtime.host_data / 'backups' / backup['host']['backupId']), '--identity-dir', str(runtime.host_data / 'identity')],
            env=runtime.env, capture_output=True, timeout=60)
        assert restored_process.returncode == 0, restored_process.stderr.decode('utf-8', errors='replace')
        (restored / 'package.json').write_text(json.dumps(stored_backup['package'], ensure_ascii=False), encoding='utf-8')
        with running('restore', restored) as (restored_runtime, _):
            restored_player = Account(restored_runtime.origin, 'player1', password, 'player1')
            assert restored_player.state()['character']['numbers']['location'] == 3
            assert restored_player.state()['note'] == 'PRIVATE-NOTE-ONE'
            assert restored_player.state()['recap'] == 'PUBLIC-RECAP'
        checks.append('paired host/package backup restores into a second empty directory')
        print(json.dumps({'passed': len(checks), 'checks': checks}, ensure_ascii=False))
    (PACK / 'tests/package-results.json').write_text(json.dumps({'passed': True, 'checkedAt': datetime.now().astimezone().isoformat(), 'checks': checks}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
