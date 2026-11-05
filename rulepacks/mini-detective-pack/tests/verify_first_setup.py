"""Fresh-device authentication regression, isolated from actual game data."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK / 'tools'))
from client import Client, HostError


def main():
    output = PACK / 'tests/output' / ('first-setup-' + uuid.uuid4().hex[:8])
    output.mkdir(parents=True)
    checks = []
    def ok(name, value):
        assert value, name
        checks.append(name)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
    for empty in (False, True):
        directory = output / ('empty-room' if empty else 'new-room')
        if empty:
            directory.mkdir()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        origin = 'http://127.0.0.1:' + str(port)
        log = (output / ('empty.log' if empty else 'new.log')).open('wb')
        client = None
        process = subprocess.Popen([sys.executable, '-B', str(PACK / 'tools/launch.py'), '--data-dir', str(directory), '--port', str(port), '--no-browser'], env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    with urllib.request.urlopen(origin + '/setup/status', timeout=5) as response:
                        status = json.load(response)
                    break
                except OSError:
                    if process.poll() is not None:
                        raise AssertionError('launcher exited; see isolated test log')
                    time.sleep(.1)
            else:
                raise AssertionError('launcher unavailable')
            label = 'empty directory' if empty else 'new clone'
            print(label + ': ' + json.dumps(status), flush=True)
            ok(label + ' offers first setup rather than unusable login', status['canSetup'] and not status['ready'])
            request = urllib.request.Request(origin + '/setup', data=json.dumps({'password': '12345678'}).encode(), headers={'Origin': origin, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=90) as response:
                ok(label + ' accepts valid eight-character first password', json.load(response)['ready'])
            for account in ('kp', 'player1', 'player2', 'player3', 'player4'):
                client = Client(origin, account, '12345678')
                ok(label + ' authenticates ' + account, client.request('/view')['accountId'] == account)
            try:
                Client(origin, 'kp', 'incorrect-password')
            except HostError as error:
                ok(label + ' wrong password is rejected', error.response['httpStatus'] in (400,401,403))
            else:
                raise AssertionError('wrong password authenticated')
            if not empty:
                from playwright.sync_api import sync_playwright, expect
                with sync_playwright() as playwright:
                    try:
                        browser = playwright.chromium.launch(headless=True)
                    except Exception:
                        browser = playwright.chromium.launch(channel='msedge', headless=True)
                    page = browser.new_page(viewport={'width': 1440, 'height': 900})
                    page.goto(origin + '/sessions/kp/')
                    page.locator('#login-form [name=password]').fill('incorrect-password')
                    page.locator('#login-form button').click()
                    expect(page.locator('#notice')).to_contain_text('此存档没有默认密码')
                    ok('browser explains AUTH_FAILED without a default password claim', True)
                    page.locator('#login-form [name=password]').fill('12345678')
                    page.locator('#login-form button').click()
                    expect(page.locator('nav')).to_be_visible(timeout=15000)
                    ok('browser enters KP with password explicitly set during first setup', True)
                    browser.close()
        finally:
            if client is not None:
                try:
                    admin=Client(origin,'kp','12345678')
                    request=urllib.request.Request(origin+'/package/shutdown',data=b'{}',headers={'Origin':origin,'X-CSRF-Token':admin.csrf})
                    admin.opener.open(request,timeout=5).close()
                    process.wait(timeout=15)
                except Exception:
                    pass
            if process.poll() is None:
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
                process.wait(timeout=15)
            log.close()
    report = {'passed': len(checks), 'checks': checks, 'mode': 'fresh local launcher + public host authentication'}
    (PACK / 'tests/first-setup-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
