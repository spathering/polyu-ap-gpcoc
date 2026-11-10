"""An isolated real host and package adapter, using documented CLI/API only."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import uuid

sys.dont_write_bytecode = True
PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK / 'tools'))
import httpx
import uvicorn
from launch import Runtime, create_app, free_port


class Account:
    def __init__(self, origin, name, password, slot=None):
        self.origin = origin
        self.prefix = '/sessions/' + slot if slot else ''
        self.http = httpx.Client(base_url=origin, headers={'Origin': origin}, timeout=60, trust_env=False)
        result = self.request('/api/v1/login', {'loginName': name, 'password': password})
        self.http.headers['X-CSRF-Token'] = result['csrf']
        self.name = name

    def request(self, path, body=None, allow_error=False):
        response = self.http.request('GET' if body is None else 'POST', self.prefix + path, json=body)
        data = response.json()
        if not allow_error:
            assert response.is_success, (response.status_code, data)
            assert not isinstance(data, dict) or data.get('status') != 'rejected' or 'commandId' not in data, data
        return data

    def state(self):
        return self.request('/package/state')

    def action(self, op, args=None, action_id=None, allow_error=False):
        return self.request('/package/action', {'id': action_id or str(uuid.uuid4()), 'operation': op, 'args': args or {}}, allow_error)

    def command(self, op, args, allow_error=False):
        view = self.request('/api/v1/view')
        return self.request('/api/v1/commands', {'protocolVersion': 1, 'type': 'command', 'requestId': str(uuid.uuid4()),
            'roomId': view['roomId'], 'payload': {'commandId': str(uuid.uuid4()), 'authorityEpoch': view['authorityEpoch'],
                'runId': view['runId'], 'catalogRevision': view['catalog']['revision'], 'rulesetRevision': view['catalog']['rulesetRevision'],
                'expectedViews': {}, 'op': op, 'args': args}}, allow_error)


@contextmanager
def running(label='verify', data=None):
    data = data or PACK / 'tests/output' / (label + '-' + secrets.token_hex(4))
    runtime = Runtime(argparse.Namespace(data_dir=data, backend_port=0, port=free_port(), bind='127.0.0.1'))
    server = uvicorn.Server(uvicorn.Config(create_app(runtime), host='127.0.0.1', port=runtime.args.port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(200):
            if server.started:
                break
            time.sleep(.05)
        assert server.started, 'adapter did not start'
        password = secrets.token_urlsafe(18)
        with httpx.Client(base_url=runtime.origin, headers={'Origin': runtime.origin}, timeout=90, trust_env=False) as http:
            status = http.get('/setup/status').json()
            if status['canSetup']:
                response = http.post('/setup', json={'password': password})
                assert response.is_success, response.text
        yield runtime, password
    finally:
        server.should_exit = True
        thread.join(15)
        runtime.close()


def provision(runtime, password):
    kp, p1, p2 = [Account(runtime.origin, name, password, name) for name in ('kp', 'player1', 'player2')]
    rolled = p2.action('draft.roll')
    assert all(2 <= rolled[x] <= 12 for x in ('str', 'dex', 'wil')) and 1 <= rolled['hp'] <= 6
    p1.action('draft', {'preset': 'mul', 'name': '木栗'})
    p2.action('draft', {'preset': 'dou', 'name': '豆叶'})
    kp.action('approve', {'account': 'player1'})
    kp.action('approve', {'account': 'player2'})
    p1.action('ready', {'ready': True})
    p2.action('ready', {'ready': True})
    kp.action('world', {'operation': 'start'})
    return kp, p1, p2
