"""Read public host behavior in an isolated disposable test room."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

sys.dont_write_bytecode = True
PACK = Path(__file__).resolve().parents[1]
ROOT = PACK.parents[1]
sys.path.insert(0, str(PACK / 'tools'))
from client import Client, HostError


def main():
    data = PACK / 'tests/output' / ('probe-' + secrets.token_hex(4))
    password = secrets.token_urlsafe(16)
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'ONLINECOC_BOOTSTRAP_PASSWORD': password}
    command = [sys.executable, '-B', str(ROOT / 'engineering/backend/scripts/run.py'), '--data-dir', str(data)]
    subprocess.run(command + ['init'], env=env, check=True, capture_output=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with (data.parent / (data.name + '.log')).open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command + ['serve', '--port', str(port)], env=env, stdout=log, stderr=log)
        try:
            for attempt in range(100):
                try:
                    kp = Client(f'http://127.0.0.1:{port}', 'kp', password)
                    break
                except OSError:
                    time.sleep(.1)
            pl = Client(kp.base, 'player1', password)
            members = pl.request('/chat/members')['items']
            member = next(x for x in members if x['accountId'] == 'player1')
            print('members', json.dumps(members, ensure_ascii=False))
            print('view keys', list(pl.request('/view')))
            for owner_kind, owner_id in [('member', member['memberId']), ('entity', 'actor-player1')]:
                try:
                    result = pl.command('progress.set', {'ownerKind': owner_kind, 'ownerId': owner_id, 'eventKey': 'sv.test-note', 'value': {'text': 'private test'}})
                    print('progress write', owner_kind, result)
                except HostError as error:
                    print('progress error', owner_kind, error.response)
            for client, label in [(pl, 'player'), (kp, 'kp'), (Client(kp.base, 'player2', password), 'other')]:
                print(label, 'progress', json.dumps(client.request('/view')['progress'], ensure_ascii=False))
            print('admin keys', list(kp.request('/admin')))
            print('player entity', json.dumps(pl.request('/view')['entities'], ensure_ascii=False)[:3000])
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    main()
