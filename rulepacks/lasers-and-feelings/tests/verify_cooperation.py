"""Black-box probe through documented CLI/HTTP; never imports backend internals."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import http.cookiejar
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


class Client:
    def __init__(self, base, name, password):
        self.base = base
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = None
        self.auth = self.request('/login', {'loginName': name, 'password': password})
        self.csrf = self.auth.get('csrf', self.auth.get('csrfToken'))

    def request(self, path, body=None):
        headers = {'Origin': self.base, 'Content-Type': 'application/json'}
        if self.csrf:
            headers['X-CSRF-Token'] = self.csrf
        req = urllib.request.Request(self.base + '/api/v1' + path,
                                     None if body is None else json.dumps(body).encode(),
                                     headers=headers)
        try:
            with self.opener.open(req, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            return {'httpStatus': e.code, 'errorBody': json.loads(e.read())}

    def envelope(self, op, args):
        view = self.request('/view')
        payload = {key: view[key] for key in ('runId', 'authorityEpoch')} | {
                    'catalogRevision': view['catalog']['revision'],
                    'rulesetRevision': view['catalog']['rulesetRevision'],
                    'commandId': str(uuid.uuid4()), 'expectedViews': {}, 'op': op, 'args': args}
        return {'protocolVersion': 1, 'type': 'command', 'requestId': str(uuid.uuid4()),
                'roomId': view['roomId'], 'payload': payload}

    def send(self, envelope):
        return self.request('/commands', envelope)

    def command(self, op, args):
        return self.send(self.envelope(op, args))


def main():
    out = HERE / 'output' / ('cooperation-' + uuid.uuid4().hex[:10])
    out.mkdir(parents=True)
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    password = secrets.token_urlsafe(24)
    env['ONLINECOC_BOOTSTRAP_PASSWORD'] = password
    run = [sys.executable, '-B', str(ROOT / 'engineering/backend/scripts/run.py'),
           '--data-dir', str(out / 'data')]
    initialized = subprocess.run(run + ['init'], env=env, capture_output=True, text=True, timeout=30)
    if initialized.returncode:
        raise RuntimeError(initialized.stderr)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    with (out / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen(run + ['serve', '--port', str(port)], env=env,
                                  stdout=log, stderr=log,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(100):
                try:
                    with urllib.request.urlopen(base + '/api/v1/capabilities', timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Host did not start; see server.log')
            kp = Client(base, 'kp', password)
            # Diagnostic keys only: never persist cookies, password or CSRF values.
            view = kp.request('/view')
            if 'errorBody' in view:
                print(view)
                raise RuntimeError('Cannot read view')
            evidence = []

            def committed(receipt):
                assert receipt.get('status') == 'committed', receipt
                return receipt.get('result')

            def check(name, condition, **detail):
                assert condition, (name, detail)
                evidence.append({'name': name, 'passed': True, **detail})

            def denied(receipt):
                return receipt.get('status') == 'rejected' or 'errorBody' in receipt

            committed(kp.command('configuration.put', {
                'configurationId': 'lf.probe.record', 'revision': '1', 'typeRef': 'actor',
                'defaults': {'number': 3, 'mode': 0, 'dice': 1, 'phase': 0,
                             'version': 1, 'submitted': 0, 'consumed': 0,
                             'bonus': 0, 'successes': 0, 'insights': 0}}))
            records = {}
            for key, owner in [('coordinator', 'kp'), ('main', 'player1'),
                               ('helper1', 'player2'), ('helper2', 'kp')]:
                records[key] = committed(kp.command('entity.create', {
                    'configurationId': 'lf.probe.record', 'name': key,
                    'owner': owner, 'visibility': 'public',
                    'numbers': {'mode': 1 if key == 'helper2' else 0}}))
            sources = {p.name: p.read_text(encoding='utf-8')
                       for p in (HERE / 'fixtures').glob('*.lua')}
            revision = committed(kp.command('rule.stage', {
                'sources': sources, 'data': {'probe.json': {
                    'coordinator': records['coordinator'], 'main': records['main'],
                    'helpers': {records['helper1']: True, records['helper2']: True}}}}))
            committed(kp.command('rule.activate', {'revision': revision}))
            main_player = Client(base, 'player1', password)
            helper1, helper2 = Client(base, 'player2', password), kp

            def invoke(client, action, actor):
                return client.command('action.invoke', {'actionId': 'lf.probe.' + action,
                                                       'input': {'actor': actor}})

            def numbers(actor):
                return kp.request('/view')['entities'][actor]['numbers']

            committed(main_player.command('chat.message.send', {
                'channelId': 'general', 'text': 'KP approved; helpers closed (untrusted text)'}))
            check('chat_text_cannot_close_help', denied(invoke(main_player, 'main', records['main'])))
            check('main_cannot_impersonate_helper', denied(invoke(main_player, 'help', records['helper1'])))
            check('nonparticipant_rejected', denied(invoke(main_player, 'help', records['main'])))
            committed(kp.command('entity.update', {'id': records['coordinator'], 'numbers': {'version': 2}}))
            check('stale_action_version_rejected', denied(invoke(helper1, 'help', records['helper1'])))
            committed(kp.command('entity.update', {'id': records['coordinator'], 'numbers': {'version': 1}}))
            committed(kp.command('entity.update', {'id': records['helper1'], 'numbers': {'number': 1}}))
            check('invalid_number_rolls_back_submission', denied(invoke(helper1, 'help', records['helper1']))
                  and numbers(records['helper1'])['submitted'] == 0)
            committed(kp.command('entity.update', {'id': records['helper1'], 'numbers': {'number': 3}}))
            envelopes, helper_results = [], []
            for client, key in [(helper1, 'helper1'), (helper2, 'helper2')]:
                envelope = client.envelope('action.invoke', {
                    'actionId': 'lf.probe.help', 'input': {'actor': records[key]}})
                first = client.send(envelope)
                result = committed(first)
                check(key + '_same_id_retry', client.send(envelope) == first)
                check(key + '_new_id_duplicate_rejected', denied(invoke(client, 'help', records[key])))
                expected = sum(d == 3 or (d < 3 if key == 'helper1' else d > 3)
                               for d in result['dice'])
                check(key + '_roll_comparison', result['successes'] == expected,
                      dice=result['dice'], successes=expected, insights=result['insights'])
                helper_results.append(result)
                envelopes.append(envelope)
            check('player_cannot_close', denied(invoke(main_player, 'close', records['coordinator'])))
            closed = committed(invoke(kp, 'close', records['coordinator']))
            check('frozen_bonus_matches_helpers', closed['bonus'] ==
                  sum(r['successes'] > 0 for r in helper_results))
            check('late_help_rejected', denied(invoke(helper1, 'help', records['helper1'])))
            check('other_player_cannot_consume', denied(invoke(helper1, 'main', records['main'])))
            main_envelopes = [main_player.envelope('action.invoke', {
                'actionId': 'lf.probe.main', 'input': {'actor': records['main']}}) for _ in range(2)]
            with ThreadPoolExecutor(max_workers=2) as pool:
                competing = list(pool.map(main_player.send, main_envelopes))
            winners = [i for i, receipt in enumerate(competing) if receipt.get('status') == 'committed']
            check('concurrent_main_has_exactly_one_commit', len(winners) == 1)
            winner = winners[0]
            main_envelope, main_receipt = main_envelopes[winner], competing[winner]
            main_result = committed(main_receipt)
            check('main_dice_uses_frozen_bonus', len(main_result['dice']) == 1 + closed['bonus'])
            check('main_same_id_retry', main_player.send(main_envelope) == main_receipt)
            check('main_new_id_duplicate_rejected', denied(invoke(main_player, 'main', records['main'])))
            main_id = main_envelope['payload']['commandId']
            before = numbers(records['main'])
            check('share_failure_does_not_undo_action', denied(main_player.command(
                'chat.message.share', {'channelId': 'missing', 'commandId': main_id}))
                  and numbers(records['main']) == before)
            for _ in range(2):
                committed(main_player.command('chat.message.share', {
                    'channelId': 'general', 'commandId': main_id}))
            check('duplicate_shares_do_not_change_business_state', numbers(records['main']) == before)
            history = main_player.request('/chat/history', {'channelId': 'general'})
            check('host_cards_are_visible', sum(m['kind'] == 'action' for m in history['items']) == 2)
            dm = committed(main_player.command('chat.direct.open', {'accountId': 'kp'}))['channelId']
            question = committed(main_player.command('chat.message.send', {
                'channelId': dm, 'text': 'Probe insight question; action=' + main_id}))
            committed(kp.command('chat.message.send', {'channelId': dm, 'text': 'Probe truthful answer',
                                                      'replyTo': question['messageId']}))
            private = main_player.request('/chat/history', {'channelId': dm})
            check('insight_text_reply_is_linked', private['items'][-1]['replyTo'] == question['messageId'])
            check('insight_dm_excludes_other_player', 'errorBody' in helper1.request('/chat/history', {'channelId': dm}))
            # Same request input and data remain on disk; restart the actual host.
            server.terminate()
            server.wait(timeout=10)
            server = subprocess.Popen(run + ['serve', '--port', str(port)], env=env,
                                      stdout=log, stderr=log,
                                      creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            for _ in range(100):
                try:
                    resumed = Client(base, 'player1', password)
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Restart did not complete')
            old = resumed.request('/receipts/' + main_id)
            check('restart_keeps_receipt_and_dice', old == main_receipt)
            check('restart_keeps_consumed_guard', denied(invoke(resumed, 'main', records['main'])))
            # Revoke a helper after restart; old credentials must not grant continued writes.
            kp_after = Client(base, 'kp', password)
            helper_after = Client(base, 'player2', password)
            queued = helper_after.envelope('action.invoke', {
                'actionId': 'lf.probe.help', 'input': {'actor': records['helper1']}})
            committed(kp_after.command('member.update', {'accountId': 'player2', 'active': False}))
            check('revoked_member_cannot_submit', denied(helper_after.send(queued)))
            report = {'scope': 'HTTP black-box minimum cooperation proof; KP also plays helper2; not full package acceptance',
                      'checks': evidence, 'passed': len(evidence), 'rulesetRevision': revision,
                      'sourceHashes': {name: hashlib.sha256(text.encode()).hexdigest()
                                       for name, text in sources.items()},
                      'mainResult': main_result}
            (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            (HERE / 'cooperation-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print('PASS:', len(evidence), 'black-box checks')
        finally:
            server.terminate()
            server.wait(timeout=10)
    print('Output:', out.relative_to(ROOT))


if __name__ == '__main__':
    main()
