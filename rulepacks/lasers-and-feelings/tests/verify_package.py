"""Reusable production package integration against a fresh, real host."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
import uuid

PACK = Path(__file__).resolve().parents[1]
ROOT = PACK.parents[1]
sys.path.insert(0, str(PACK / 'tools'))
from client import Client, HostError
from package import action, bundle, character, install


def main():
    out = PACK / 'tests/output' / ('package-' + uuid.uuid4().hex[:10])
    out.mkdir(parents=True)
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    password = secrets.token_urlsafe(20)
    env['ONLINECOC_BOOTSTRAP_PASSWORD'] = password
    run = [sys.executable, '-B', str(ROOT / 'engineering/backend/scripts/run.py'), '--data-dir', str(out / 'data')]
    subprocess.run(run + ['init'], env=env, capture_output=True, check=True, timeout=30)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    checks = []

    def ok(name, condition=True):
        assert condition, name
        checks.append({'name': name, 'passed': True})

    def rejects(name, call):
        try:
            call()
        except HostError:
            ok(name)
        else:
            raise AssertionError(name + ' unexpectedly committed')

    with (out / 'host.log').open('w', encoding='utf-8') as log:
        proc = subprocess.Popen(run + ['serve', '--port', str(port)], env=env, stdout=log, stderr=log,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(100):
                try:
                    with urllib.request.urlopen(base + '/api/v1/capabilities', timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            kp, p1, p2 = [Client(base, name, password) for name in ('kp', 'player1', 'player2')]
            revision = install(kp)
            ok('bundle_installed')
            a = character(kp, 'player1', '阿澈', number=2)
            b = character(kp, 'player2', '星河', number=5, style=7, job=3, goal=6)
            rejects('player_cannot_edit_profile', lambda: p1.invoke('lf.profile', actor=a, number=5, style=1, job=1, goal=1))
            rejects('invalid_number_rejected', lambda: kp.invoke('lf.profile', actor=a, number=6, style=1, job=1, goal=1))
            ship = kp.command('entity.create', {'configurationId': 'lf.ship', 'name': 'Raptor', 'owner': 'kp'})
            kp.invoke('lf.ship', actor=ship, first=1, second=2, problem=3)
            rejects('duplicate_ship_strength_rejected', lambda: kp.invoke('lf.ship', actor=ship, first=2, second=2, problem=1))
            adventure = kp.invoke('lf.adventure', threat=0, intent=0, object=0, consequence=0)
            ok('four_adventure_tables', len(adventure) == 4 and all(1 <= v['index'] <= 6 for v in adventure.values()))
            rejects('player_cannot_generate_secret', lambda: p1.invoke('lf.adventure', threat=0, intent=0, object=0, consequence=0))
            rounds = []
            for index in range(3):
                coord, participants = action(kp, f'穿越星云 {index+1}', [
                    {'character': a, 'mode': index % 2, 'prepared': 1, 'expert': 1},
                    {'character': b, 'mode': (index+1) % 2}])
                main_record, helper_record = participants
                rejects('main_before_close_' + str(index), lambda: p1.invoke('lf.main', actor=main_record))
                rejects('wrong_owner_help_' + str(index), lambda: p1.invoke('lf.help', actor=helper_record))
                helper_envelope = p2.envelope('action.invoke', {'actionId': 'lf.help', 'input': {'actor': helper_record}})
                help_receipt = p2.send(helper_envelope)
                ok('same_id_help_' + str(index), p2.send(helper_envelope) == help_receipt)
                rejects('new_id_help_' + str(index), lambda: p2.invoke('lf.help', actor=helper_record))
                closed = kp.invoke('lf.close', actor=coord)
                expected_bonus = int(help_receipt['result']['successes'] > 0)
                ok('frozen_bonus_' + str(index), closed['bonus'] == expected_bonus)
                rejects('late_help_' + str(index), lambda: p2.invoke('lf.help', actor=helper_record))
                envelopes = [p1.envelope('action.invoke', {'actionId': 'lf.main', 'input': {'actor': main_record}}) for _ in range(2)]

                def attempt(envelope):
                    try:
                        return p1.send(envelope)
                    except HostError:
                        return None

                with ThreadPoolExecutor(max_workers=2) as pool:
                    receipts = list(pool.map(attempt, envelopes))
                winners = [r for r in receipts if r]
                ok('concurrent_main_' + str(index), len(winners) == 1)
                result = winners[0]['result']
                number, mode = result['number'], result['mode']
                correct = sum(d == number or (d < number if mode == 0 else d > number) for d in result['dice'])
                ok('success_and_insight_' + str(index), result['successes'] == correct and
                   result['insights'] == sum(d == number for d in result['dice']))
                ok('prepared_expert_and_help_' + str(index), len(result['dice']) == 3 + expected_bonus)
                rejects('new_id_main_' + str(index), lambda: p1.invoke('lf.main', actor=main_record))
                p1.command('chat.message.share', {'channelId': 'general', 'commandId': winners[0]['commandId']})
                # Isolate the question-state test from randomness using an explicit KP fixture edit.
                kp.command('entity.update', {'id': main_record, 'numbers': {'insights': 1}})
                q = p1.invoke('lf.question', actor=main_record, question='幕后是谁？')
                ok('durable_insight_question_' + str(index), q['question'] == '幕后是谁？')
                rejects('duplicate_question_' + str(index), lambda: p1.invoke('lf.question', actor=main_record, question='再问一次'))
                rejects('player_cannot_mark_answered_' + str(index), lambda: p1.invoke('lf.answer', actor=main_record))
                kp.invoke('lf.answer', actor=main_record)
                ok('answered_state_' + str(index), p1.request('/view')['entities'][main_record]['numbers']['questionState'] == 2)
                rounds.append(coord)
            ok('three_actions_same_revision', p1.request('/view')['catalog']['rulesetRevision'] == revision)
            cancelled, records = action(kp, '取消的行动', [{'character': a}])
            kp.invoke('lf.cancel', actor=cancelled)
            rejects('cancelled_cannot_roll', lambda: p1.invoke('lf.main', actor=records[0]))
            # A pending helper is excluded when KP deliberately closes the window.
            pending, records = action(kp, '提前关闭', [{'character': a}, {'character': b}])
            kp.invoke('lf.close', actor=pending)
            rejects('unsubmitted_helper_is_late', lambda: p2.invoke('lf.help', actor=records[1]))
            result = p1.invoke('lf.main', actor=records[0])
            ok('zero_bonus_for_unsubmitted', len(result['dice']) == 1)
            kp.command('progress.set', {'ownerKind': 'entity', 'ownerId': ship, 'eventKey': 'lf.scene', 'value': {'title': '抵达边境'}})
            view = p1.request('/view')
            print('progress public shape:', json.dumps(view['progress'], ensure_ascii=False)[:600])
            report = {'passed': len(checks), 'checks': checks, 'rulesetRevision': revision,
                      'scope': 'production reusable rules, ordinary player main/helper, synthetic insight for question tests',
                      'sourceHashes': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in bundle()['sources'].items()}}
            (PACK / 'tests/package-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print('PASS:', len(checks), 'package integration checks')
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == '__main__':
    main()
