"""Real-host workflow and desktop browser regression; never uses live saves."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import ThreadingHTTPServer

PACK = Path(__file__).resolve().parents[1]
ROOT = PACK.parents[1]
sys.path.insert(0, str(PACK / 'tools'))
from automation import Automation
from client import Client, HostError
from launch import handler
from package import install, bundle


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def main():
    out = PACK / 'tests/output' / ('automation-' + uuid.uuid4().hex[:8])
    out.mkdir(parents=True)
    password = secrets.token_urlsafe(20)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', ONLINECOC_BOOTSTRAP_PASSWORD=password, PYTHONIOENCODING='utf-8')
    run = [sys.executable, '-B', str(ROOT / 'engineering/backend/scripts/run.py'), '--data-dir', str(out / 'room')]
    subprocess.run(run + ['init'], env=env, capture_output=True, check=True, timeout=30)
    backend, origin = 'http://127.0.0.1:' + str(port()), 'http://127.0.0.1:' + str(port())
    checks = []

    def ok(name, condition=True):
        assert condition, name
        checks.append(name)

    log = (out / 'host.log').open('wb')
    proc = subprocess.Popen(run + ['serve', '--port', backend.rsplit(':', 1)[1]], env=env, stdout=log, stderr=log)
    proxy = None
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(backend + '/api/v1/capabilities', timeout=1).close()
                break
            except OSError:
                time.sleep(.1)
        automation = Automation(backend, out / 'workflows')
        proxy = ThreadingHTTPServer(('127.0.0.1', int(origin.rsplit(':', 1)[1])), handler(backend, origin, automation=automation))
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        k, p, other = [Client(origin, a, password) for a in ('kp', 'player1', 'player2')]
        install(k)
        w = k.command('entity.create', {'configurationId': 'md.world', 'owner': 'kp', 'visibility': 'public'})
        people = []
        for account in ('player1', 'player2'):
            aid = k.command('entity.create', {'configurationId': 'md.character', 'owner': account, 'visibility': 'owner', 'name': '调查员' + account[-1]})
            k.invoke('md.profile', actor=aid, constitution=3, strength=2, speed=4, observation=5, spirit=3, intellect=3)
            people.append(aid)
        a, b = people

        def pack(client, path, body=None, csrf=True):
            headers = {'Origin': origin, 'Content-Type': 'application/json'}
            if csrf:
                headers['X-CSRF-Token'] = client.csrf
            req = urllib.request.Request(origin + '/package/' + path, headers=headers, data=None if body is None else json.dumps(body).encode())
            with client.opener.open(req, timeout=30) as r:
                return json.load(r)

        def act(client, actor, kind, **fields):
            return pack(client, 'action', {'id': str(uuid.uuid4()), 'actor': actor, 'kind': kind, **fields})

        def numbers(aid):
            return k.request('/view')['entities'][aid]['numbers']

        ok('KP login enables a dedicated automation session', pack(k, 'automation')['ready'])
        ok('automatic handling defaults to off', pack(k, 'automation')['enabled'] is False)
        for client, csrf, name in [(p, True, 'PL cannot change room automation switch'), (k, False, 'switch requires CSRF')]:
            try:
                pack(client, 'automation', {'enabled': True}, csrf)
            except urllib.error.HTTPError as e:
                ok(name, e.code == 403)
            else:
                raise AssertionError(name)
        content = bundle()
        legacy = json.loads(json.dumps(content['data']))
        legacy['scenario.json'].pop('automation')
        legacy['scenario.json']['locations'][0]['description'] = '测试保留的在线场景说明'
        revision = k.command('rule.stage', {'sources': content['sources'], 'data': legacy})
        k.command('rule.activate', {'revision': revision})
        pack(k, 'automation', {'enabled': True})
        active = k.request('/admin/artifacts/' + k.request('/view')['catalog']['rulesetRevision'])['artifact']['data']['scenario.json']
        ok('enabling switch upgrades legacy automation without separate import', 'automation' in active and pack(k, 'automation')['enabled'])
        ok('enabling upgrade retains active edits and character resources', active['locations'][0]['description'] == '测试保留的在线场景说明' and numbers(a)['slotUsed'] == 0)
        scene = pack(p, 'automation')['scenes'][a]
        ok('unexplored initial minimap only keeps current-position anchor', {x['id'] for x in scene['map']['nodes']} == {'loc-hall'} and not scene['map']['nodes'][0]['explored'])
        ok('fresh scene exposes reachable destinations without prior exploration', any(x['id'] == 'loc-village' and x['move'] for x in scene['exits']))
        ok('locked secret entrance absent from fresh scene and minimap', not any(x['id'] == 'loc-basement' for x in scene['exits'] + scene['map']['nodes']))
        ok('scene actions omit mechanisms belonging to other locations', not any(x['kind'] in ('start-boat', 'stop-tracking', 'open-maintenance') for x in scene['actions']))
        ok('all 23 scene public feature definitions configured', set(content['data']['scenario.json']['automation']['scenes']) == {x['id'] for x in active['locations']})
        ok('other account receives only its own scene projection', a not in pack(other, 'automation')['scenes'] and b in pack(other, 'automation')['scenes'])
        ok('scene uses active host description rather than stale local JSON', scene['location']['description'] == '测试保留的在线场景说明')
        try:
            urllib.request.urlopen(origin + '/package/automation')
        except urllib.error.HTTPError as e:
            ok('automation projection requires authentication', e.code == 401)
        else:
            raise AssertionError('anonymous projection')
        request = {'id': str(uuid.uuid4()), 'actor': a, 'kind': 'explore', 'destination': 1}
        try:
            pack(p, 'action', request, False)
        except urllib.error.HTTPError as e:
            ok('automation rejects missing CSRF', e.code == 403)
        else:
            raise AssertionError('csrf bypass')
        ok('players cannot automate another owner', act(other, a, 'sleep')['rejected'])
        try:
            pack(p, 'action', {'id': str(uuid.uuid4()), 'kind': 'sleep', 'actor': {}})
        except urllib.error.HTTPError as e:
            ok('malformed field rejected before journal allocation', e.code == 400 and pack(p, 'automation')['pending'] is None)
        else:
            raise AssertionError('malformed actor accepted')
        ok('locked underground entrance rejected', act(p, a, 'move', destination=22)['rejected'])
        start = numbers(a)['stamina']
        send = automation.client.send
        dropped = []
        def lose_resolve_response(envelope):
            receipt = send(envelope)
            if not dropped and envelope['payload']['op'] == 'action.invoke' and envelope['payload']['args']['actionId'] == 'md.resolve':
                dropped.append(True)
                raise OSError('Simulated response loss after host commit')
            return receipt
        automation.client.send = lose_resolve_response
        try:
            pack(p, 'action', request)
        except urllib.error.HTTPError as e:
            ok('uncertain committed response leaves workflow recoverable', e.code == 503 and bool(pack(p, 'automation')['pending']))
        else:
            raise AssertionError('fault injection did not execute')
        automation.client.send = send
        result = pack(p, 'action', request)
        ok('exploration auto settles and spends exactly one stamina', not result.get('rejected') and numbers(a)['stamina'] == start - 1)
        ok('exploration automatically rolls and closes request', numbers(a)['requestOpen'] == 0 and 1 <= numbers(a)['lastDie'] <= 6)
        scene = pack(p, 'automation')['scenes'][a]
        ok('exploration unlocks local puzzle and pickup affordances', scene['searched'] and any(x['id'] == 'P1' for x in scene['puzzles']) and any(x['index'] == 8 for x in scene['items']))
        expected = {'loc-hall'} | (set(active['locations'][0]['adjacentIds']) - {'loc-basement'})
        ok('map expands exactly one hop from this PL explored room', {x['id'] for x in scene['map']['nodes']} == expected)
        ok('public room and accumulated neighbor list do not reveal second hop', not any(x['id'] in ('loc-chief', 'loc-sauna') for x in scene['map']['nodes']))
        other_scene = pack(other, 'automation')['scenes'][b]
        ok('PL1 exploration does not expand PL2 minimap', {x['id'] for x in other_scene['map']['nodes']} == {'loc-hall'} and not other_scene['searched'])
        ok('spent main action explains unavailable scene travel', all(not x['move'] and x['reason'] for x in scene['exits']))
        ok('replay returns same result without duplicate resource cost', pack(p, 'action', request) == result and numbers(a)['stamina'] == start - 1)
        try:
            pack(p, 'action', {**request, 'kind': 'sleep'})
        except urllib.error.HTTPError as e:
            ok('same request cannot change payload', e.code == 400)
        else:
            raise AssertionError('changed replay accepted')
        ok('ordinary action generates log without KP queue', not pack(k, 'automation')['needs'] and bool(pack(k, 'automation')['logs']))
        ok('core clue delivered privately independent of die', any(c['id'] == 'C1' for c in pack(p, 'automation')['knowledge']['clues']))
        ok('other player cannot read private clue log', not pack(other, 'automation')['knowledge']['clues'] and not any(l['account'] == 'player1' for l in pack(other, 'automation')['logs']))
        ok('puzzle answers absent from player projection', 'answers' not in json.dumps(pack(p, 'automation')))
        ok('ordinary wrong puzzle answer stays out of KP queue', act(p, a, 'puzzle', puzzle='P1', answer='000').get('rejected') and not pack(k, 'automation')['needs'])
        ok('standard puzzle answer automatically resolves', not act(p, a, 'puzzle', puzzle='P1', answer='593').get('rejected'))
        ok('repeat main action in same slot is refused', act(p, a, 'sleep').get('rejected'))
        act(other, b, 'explore', destination=1)
        ok('all players complete slot then clock advances and synchronizes', numbers(w)['slot'] == 2 and numbers(a)['slotUsed'] == 0 and numbers(b)['slot'] == 2)
        ok('one actor cannot advance world alone', not act(p, a, 'wait').get('rejected') and numbers(w)['slot'] == 2)
        act(p, a, 'puzzle', puzzle='P4', answer='颠倒黑白等意思')
        needs = pack(k, 'automation')['needs']
        ok('semantic answer queues exactly one necessary ruling', len(needs) == 1 and needs[0]['state'] == 'open')
        act(other, b, 'wait')
        ok('unresolved ruling pauses automatic clock', numbers(w)['slot'] == 2)
        ok('player cannot close KP ruling', act(p, a, 'ruling', target=needs[0]['id'], text='通过').get('rejected'))
        act(k, a, 'ruling', target=needs[0]['id'], text='请将三句回答完整填写后再试。')
        ok('completing last ruling releases ready clock', numbers(w)['slot'] == 3)
        # Owner-writable progress cannot manufacture a server-side reward.
        k.command('entity.update', {'id': a, 'numbers': {'location': 10}})
        try:
            p.command('progress.set', {'ownerKind': 'member', 'ownerId': 'member-player1', 'eventKey': 'md.known', 'value': {'searched': ['loc-steward'], 'rewards': ['item-sword-key']}})
        except HostError:
            ok('host denies player-written discovery progress')
        # Even malformed legacy progress from a management tool is not a reward.
        k.command('progress.set', {'ownerKind': 'member', 'ownerId': 'member-player1', 'eventKey': 'md.known', 'value': {'searched': ['loc-steward'], 'rewards': ['item-sword-key']}})
        ok('forged private progress cannot grant inventory', act(p, a, 'take', item=15).get('rejected'))
        k.command('entity.update', {'id': a, 'numbers': {'location': 1}})
        ok('valid discovered item automatically creates confirmed card', not act(p, a, 'take', item=8).get('rejected'))
        hammer = next(i for i in k.request('/view')['entities'].values() if i['configurationId'] == 'md.item' and i['numbers']['itemIndex'] == 8)
        ok('item card automatically confirmed', hammer['numbers']['confirmed'] == 1)
        ok('unique shared stock not duplicated', act(other, b, 'take', item=8).get('rejected'))
        ok('equipment automatically updates actor', not act(p, a, 'equip', item=hammer['instanceId']).get('rejected') and numbers(a)['weapon'] == 2)
        act(p, a, 'offer', item=hammer['instanceId'], target=b)
        choice = next(n for n in pack(other, 'automation')['needs'] if n['title'] == '确认接收道具')
        ok('transfer is a recipient choice and does not notify KP', not any(n['title'] == '确认接收道具' for n in pack(k, 'automation')['needs']))
        act(other, b, 'respond', target=choice['id'], choice='accept')
        moved = k.request('/view')['entities'][hammer['instanceId']]
        ok('recipient consent automatically transfers ownership and unequips source', moved['owner'] == 'player2' and numbers(a)['weapon'] == 0)
        act(p, a, 'attack', target=b)
        defense = next(n for n in pack(other, 'automation')['needs'] if n['title'] == '选择防御')
        ok('attack requests defender choice without KP queue', not any(n['title'] == '选择防御' for n in pack(k, 'automation')['needs']))
        act(other, b, 'respond', target=defense['id'], choice='dodge')
        ok('defense confirmation automatically executes combat dice', numbers(a)['encounterActive'] == 1 and numbers(b)['encounterActive'] == 1)
        # DPAPI session reload and independent human logout.
        k.request('/logout', {})
        ok('human KP logout does not stop automatic session', pack(p, 'automation')['ready'])
        restored = Automation(backend, out / 'workflows')
        ok('Windows encrypted session restores after restart', os.name != 'nt' or restored.client is not None)
        ok('enabled switch persists across adapter restart', restored.enabled())
        own_view = p.request('/view');own_view['_members'] = automation.client.request('/chat/members')['items']
        ok('private explored-map scope persists across restart', restored.status(own_view)['scenes'][a]['map'] == pack(p, 'automation')['scenes'][a]['map'])
        ok('encrypted session file contains no human password', not (out / 'workflows/automation-session.bin').exists() or password.encode() not in (out / 'workflows/automation-session.bin').read_bytes())
        restored.db.close()
        k = Client(origin, 'kp', password)
        # Additional deterministic rules and global allocation limits.
        for aid in (a, b):
            k.command('entity.update', {'id': aid, 'numbers': {'encounterActive': 0, 'hp': 9, 'slotUsed': 0, 'location': 1}})
        intellect = numbers(a)['intellectRemaining']
        act(p, a, 'search')
        ok('second daily site search uses remaining free attempt', numbers(a)['intellectRemaining'] == intellect)
        act(p, a, 'search')
        ok('additional site search automatically spends intellect', numbers(a)['intellectRemaining'] == intellect - 1)
        for _ in range(2):
            assert not act(p, a, 'take', item=4).get('rejected')
        def give(owner, aid, index):
            iid = k.command('entity.create', {'configurationId': 'md.item', 'owner': owner, 'visibility': 'owner', 'numbers': {'itemIndex': index}})
            k.command('relation.set', {'sourceId': iid, 'targetId': aid, 'relationType': 'source'})
            k.command('relation.set', {'sourceId': aid, 'targetId': iid, 'relationType': 'references'})
            k.invoke('md.confirm', actor=iid)
            return iid
        give('player1', a, 15)
        quota = act(p, a, 'take', item=17)
        ok('daily team site quota enforced after three pickups', quota.get('rejected') and '三件' in quota['message'])
        give('player1', a, 3)
        act(p, a, 'explore', destination=2)
        full = act(p, a, 'take', item=6)
        ok('four card capacity enforced on automatic pickup', full.get('rejected') and '卡槽' in full['message'])
        k.command('entity.update', {'id': a, 'numbers': {'slotUsed': 0, 'hp': 3}})
        medkit = next(i for i in k.request('/view')['entities'].values() if i['configurationId'] == 'md.item' and i['owner'] == 'player1' and i['numbers']['itemIndex'] == 4 and i['numbers']['count'] > 0)
        act(p, a, 'consume', item=medkit['instanceId'])
        ok('medicine automatically heals and consumes exactly one card', numbers(a)['hp'] > 3 and numbers(medkit['instanceId'])['count'] == 0 and numbers(a)['slotUsed'] == 1)
        mask = give('player1', a, 20)
        intellect = numbers(a)['intellectRemaining']
        act(p, a, 'consume', item=mask)
        ok('mask protection automatically spends intellect and item', numbers(mask)['count'] == 0 and numbers(a)['intellectRemaining'] == intellect - 1 and pack(p, 'automation')['knowledge']['sheltered'])
        for pid, index, answer in [('P2', 3, '车、马、王'), ('P3', 19, '2257'), ('P4', 1, '人异之间／颠黑覆白／天野沙吾美'), ('P5', 10, '0712'), ('P6', 4, '红蓝白'), ('P7', 5, 'boat')]:
            k.command('entity.update', {'id': a, 'numbers': {'location': index, 'slotUsed': 0}})
            if pid != 'P4':
                assert not act(p, a, 'explore', destination=index).get('rejected')
            solved = act(p, a, 'puzzle', puzzle=pid, answer=answer)
            ok(pid + ' standard answer follows configured location and result', not solved.get('rejected') and pid in pack(p, 'automation')['knowledge']['puzzles'])
        ok('puzzles automatically open the two hidden world routes', numbers(w)['basementOpen'] == 1 and numbers(w)['cliffOpen'] == 1)
        k.command('entity.update', {'id': a, 'numbers': {'location': 23, 'slotUsed': 0}})
        act(p, a, 'explore', destination=23)
        k.command('entity.update', {'id': a, 'numbers': {'slotUsed': 0}})
        ok('boat mechanism automatically spends main action and starts boat', not act(p, a, 'start-boat').get('rejected') and numbers(w)['boatReady'] == 1 and numbers(a)['slotUsed'] == 1)
        k.command('entity.update', {'id': a, 'numbers': {'location': 22, 'slotUsed': 0}})
        act(p, a, 'explore', destination=22)
        k.command('entity.update', {'id': a, 'numbers': {'slotUsed': 0}})
        ok('tracking shutdown leaves boat operation independent', not act(p, a, 'stop-tracking').get('rejected') and numbers(w)['trackingOff'] == 1 and numbers(w)['boatReady'] == 1)
        k.command('entity.update', {'id': a, 'numbers': {'location': 10, 'slotUsed': 0}})
        ok('known maintenance record opens entrance automatically', not act(p, a, 'open-maintenance').get('rejected'))
        ok('explicit promise with evidence receives boat permission', not act(p, a, 'boat-key', choice='promise').get('rejected'))
        k.command('entity.update', {'id': a, 'numbers': {'location': 14, 'slotUsed': 0}})
        act(p, a, 'explore', destination=14)
        a_nodes = pack(p, 'automation')['scenes'][a]['map']['nodes']
        b_nodes = pack(other, 'automation')['scenes'][b]['map']['nodes']
        ok('exploring village reveals its neighbors only to that PL', any(x['id'] == 'loc-chief' for x in a_nodes) and not any(x['id'] == 'loc-chief' for x in b_nodes))
        ok('same room has independent explored marker per PL', next(x for x in a_nodes if x['id'] == 'loc-village')['explored'] and not next(x for x in b_nodes if x['id'] == 'loc-village')['explored'])
        # The final selection remains a player decision after the clock closes.
        k.command('entity.update', {'id': w, 'numbers': {'day': 2, 'slot': 8, 'closed': 1, 'boatReady': 1}})
        k.command('entity.update', {'id': a, 'numbers': {'location': 23}})
        ok('closed clock blocks new resource actions', act(p, a, 'sleep').get('rejected'))
        ok('player can still explicitly select valid ending after closure', not act(p, a, 'ending', choice='1').get('rejected') and numbers(a)['ending'] == 1)
        k.command('entity.update', {'id': w, 'numbers': {'day': 1, 'slot': 3, 'closed': 0}})
        # Restore a clean play state for the browser, preserving evidence above.
        for aid in (a, b):
            k.command('entity.update', {'id': aid, 'numbers': {'day': 1, 'slot': 3, 'ending': 0, 'encounterActive': 0, 'hp': 9, 'slotUsed': 0, 'location': 1}})
        pack(k, 'automation', {'enabled': False})
        before = numbers(a)
        manual = {'id': str(uuid.uuid4()), 'actor': a, 'kind': 'explore', 'destination': 1}
        queued = pack(p, 'action', manual)
        pack(p, 'action', manual)
        needs = [n for n in pack(k, 'automation')['needs'] if n['state'] == 'open']
        ok('off switch queues action once without rolling or spending resources', queued.get('queued') and numbers(a) == before and len(needs) == 1)
        ok('manual queue shows readable action and destination', '目的地：一楼走廊' in needs[0]['text'] and '{' not in needs[0]['text'])
        saved = Automation(backend, out / 'workflows')
        ok('disabled switch persists across restart', saved.enabled() is False)
        saved.db.close()
        pack(k, 'automation', {'enabled': True})
        ok('re-enabling does not execute old manual queue', numbers(a) == before and any(n['id'] == needs[0]['id'] and n['state'] == 'open' for n in pack(k, 'automation')['needs']))
        act(k, a, 'ruling', target=needs[0]['id'], text='取消这条测试行动，无资源变更。')
        pack(k, 'automation', {'enabled': False})
        prior_slot = numbers(w)['slot']
        ok('PL cannot use proactive KP round advance', act(p, a, 'advance').get('rejected') and numbers(w)['slot'] == prior_slot)
        advance = {'id': str(uuid.uuid4()), 'kind': 'advance'}
        advanced = pack(k, 'action', advance)
        ok('KP can advance before all actions finish with automation off', not advanced.get('rejected') and numbers(w)['slot'] == prior_slot + 1 and not pack(k, 'automation')['enabled'])
        ok('manual round advance synchronizes characters and resets main actions', all(numbers(aid)['slot'] == numbers(w)['slot'] and numbers(aid)['slotUsed'] == 0 for aid in (a,b)))
        ok('same KP advance request never skips a second round', pack(k, 'action', advance) == advanced and numbers(w)['slot'] == prior_slot + 1)
        pack(k, 'automation', {'enabled': True})
        browser_checks(origin, password, out, checks)
        report = {'passed': len(checks), 'checks': checks, 'mode': 'real host + authenticated pack workflows + Chromium desktop browser'}
        (PACK / 'tests/automation-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
    finally:
        if proxy:
            proxy.shutdown();proxy.server_close()
        proc.terminate();proc.wait(timeout=15);log.close()


def browser_checks(origin, password, out, checks):
    from playwright.sync_api import sync_playwright, expect
    def ok(name, condition=True):
        assert condition, name
        checks.append(name)
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception:
            browser = pw.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        errors = []
        pages = []
        for account in ('kp', 'player1', 'player2'):
            page = context.new_page();pages.append(page)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(origin + '/sessions/' + account + '/')
            page.locator('#login-form [name=loginName]').fill(account)
            page.locator('#login-form [name=password]').fill(password)
            page.locator('#login-form button').click()
            page.locator('header').wait_for()
        kp, pl, other = pages
        kp.on('dialog', lambda dialog: dialog.accept())
        ok('KP next-round shortcut is always visible and absent for PL', kp.locator('header [data-do=advance]').is_visible() and pl.locator('header [data-do=advance]').count() == 0)
        switch = kp.get_by_role('switch')
        expect(switch).to_have_attribute('aria-checked', 'true')
        ok('KP has one persistent automation switch and PL has no switch', switch.count() == 1 and pl.get_by_role('switch').count() == 0)
        switch.click()
        expect(switch).to_have_attribute('aria-checked', 'false')
        expect(pl.locator('#scene-actions [data-value=sleep]')).to_have_text('申请 · 休息恢复', timeout=10000)
        kp.locator('nav button[data-value=map]').click()
        ok('switch remains off across pages and PL receives manual mode', kp.get_by_role('switch').get_attribute('aria-checked') == 'false')
        kp.get_by_role('switch').click()
        expect(kp.get_by_role('switch')).to_have_attribute('aria-checked', 'true')
        expect(pl.locator('#scene-actions [data-value=sleep]')).to_have_text('执行 · 休息恢复', timeout=10000)
        kp.locator('nav button[data-value=room]').click()
        ok('KP manager has focused secondary navigation', kp.locator('.subnav button').count() == 5)
        ok('initial manager hides setup combat and file tools', kp.locator('#combat-form').count() == 0 and kp.locator('#upload-pack-form').count() == 0)
        kp.get_by_role('button', name='角色与战斗', exact=True).click()
        ok('role and combat section exposes only relevant controls', kp.locator('#combat-form').is_visible() and kp.locator('#worldflag-form').count() == 0)
        kp.get_by_role('button', name='场景资料', exact=True).last.click()
        ok('scenario editor groups fields by category in Chinese', kp.locator('#scenario-edit-form').is_visible() and 'locations /' not in kp.locator('#scenario-edit-form').inner_text())
        kp.get_by_role('button', name='开局与存档', exact=True).click()
        ok('configuration file tools are collapsed by default', not kp.locator('#upload-pack-form').is_visible())
        ok('PL scene navigation replaces separate map page', '主持管理' not in pl.locator('nav').inner_text() and pl.locator('nav button').count() == 4 and pl.locator('nav [data-value=map]').count() == 0)
        ok('PL current scene has contextual actions and exits without past-time selectors', pl.locator('#scene-actions').is_visible() and pl.locator('#scene-navigation').is_visible() and pl.locator('main [name=day]').count() == 0)
        ok('minimap is collapsed inside scene by default', pl.locator('#scene-map').count() == 1 and pl.locator('#scene-map').get_attribute('open') is None)
        pl.locator('#scene-map summary').click()
        expect(pl.locator('#scene-map svg')).to_be_visible()
        ok('minimap renders known relationship graph', pl.locator('#scene-map svg line').count() > 0)
        pl.locator('#scene-actions [data-value=sleep]').click()
        pl.wait_for_function("() => document.getElementById('notice').textContent.includes('休息于')")
        ok('browser executes ordinary action and shows readable result', '休息于' in pl.locator('#notice').inner_text() and '{' not in pl.locator('#notice').inner_text())
        ok('minimap expansion survives resource updates', pl.locator('#scene-map').get_attribute('open') is not None)
        ok('local puzzle form is accessible directly from scene', pl.locator('#scene-P1').count() == 1)
        pl.locator('#scene-P1 summary').click()
        expect(pl.locator('#scene-P1')).to_contain_text('机关已解开')
        other.locator('#scene-P1 summary').click()
        expect(other.locator('#puzzle-P1')).to_be_visible()
        ok('unsolved local puzzle can be expanded without leaving scene', other.locator('#puzzle-P1').is_visible())
        other.locator('#scene-navigation [data-exit="2"] [data-kind=move]').click()
        expect(other.locator('.scene-intro h2')).to_have_text('落尘间', timeout=15000)
        ok('scene exit performs actual movement and switches scene contents', other.locator('#scene-P1').count() == 0)
        other.locator('#scene-actions [data-value=explore]').click()
        expect(other.locator('.scene-intro .badge')).to_have_text('已探索', timeout=15000)
        expect(other.locator('#scene-items [data-value="6"]')).to_be_enabled()
        other.locator('#scene-items [data-value="6"]').click()
        expect(other.locator('#notice')).to_contain_text('已领取', timeout=15000)
        ok('scene exploration reveals local item and pickup completes on same page', other.locator('.scene-intro h2').inner_text() == '落尘间')
        pl.screenshot(path=str(out / 'pl-scene.png'), full_page=True)
        pl.get_by_role('button', name='线索与机关', exact=True).click()
        ok('clue page renders private cards without raw data objects', '线索 C1' in pl.locator('main').inner_text() and '"character"' not in pl.locator('main').inner_text())
        pl.get_by_role('button', name='背包', exact=True).click()
        pl.get_by_role('button', name='现场领取', exact=True).click()
        ok('inventory separates owned cards and discovery', pl.get_by_role('heading', name='已探索地点的物品').is_visible())
        if not kp.locator('#queue').is_visible():
            kp.locator('header [data-do=window][data-value=queue]').click()
        kp.locator('#queue').wait_for(state='visible')
        if 'collapsed' not in kp.locator('#queue').get_attribute('class'):
            kp.locator('#queue [data-do=collapse]').click()
        kp.locator('nav button[data-value=map]').click()
        ok('independent KP window preserves collapsed state across tabs', 'collapsed' in kp.locator('#queue').get_attribute('class'))
        ok('desktop page has no horizontal overflow at 1440px', pl.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        before_time = kp.locator('.state-line strong').inner_text()
        kp.locator('header [data-do=advance]').click()
        expect(kp.locator('.state-line strong')).not_to_have_text(before_time, timeout=15000)
        ok('KP header shortcut actually advances displayed world round', kp.locator('.state-line strong').inner_text() != before_time)
        kp.screenshot(path=str(out / 'kp-desktop.png'), full_page=True)
        pl.screenshot(path=str(out / 'pl-desktop.png'), full_page=True)
        ok('no browser runtime errors', not errors)
        browser.close()


if __name__ == '__main__':
    main()
