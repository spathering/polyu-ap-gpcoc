"""Real Chromium/Edge browser acceptance with one browser context with independent account tabs."""
import json
import hashlib
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
import uuid

from playwright.sync_api import sync_playwright, expect

PACK = Path(__file__).resolve().parents[1]
ROOT = PACK.parents[1]
sys.path.insert(0, str(PACK / 'tools'))
from client import Client


def main():
    out = PACK / 'tests/output' / ('browser-' + uuid.uuid4().hex[:10])
    out.mkdir(parents=True)
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    password = secrets.token_urlsafe(20)
    env['ONLINECOC_BOOTSTRAP_PASSWORD'] = password
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        host_port = s.getsockname()[1]
    host_run = [sys.executable, '-B', str(ROOT/'engineering/backend/scripts/run.py'), '--data-dir', str(out/'data')]
    subprocess.run(host_run+['init'], env=env, capture_output=True, check=True, timeout=30)
    checks, errors = [], []

    def ok(name, condition=True):
        assert condition, name
        checks.append({'name': name, 'passed': True})

    with (out / 'launch.log').open('w', encoding='utf-8') as log:
        host_proc = subprocess.Popen(host_run+['serve','--port',str(host_port)], env=env, stdout=log, stderr=log,
                                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        proc = subprocess.Popen([sys.executable, '-B', str(PACK / 'tools/launch.py'),
                                 '--backend', f'http://127.0.0.1:{host_port}', '--port', str(port), '--no-browser'],
                                env=env, stdout=log, stderr=log,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(150):
                try:
                    with urllib.request.urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Frontend did not start; see launch.log')
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception:
                    browser = p.chromium.launch(channel='msedge', headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1050})
                root_page = context.new_page()
                root_page.goto(base)
                root_page.get_by_label('账号', exact=True).fill('kp')
                root_page.get_by_label('密码', exact=True).fill(password)
                root_page.get_by_role('button', name='登录', exact=True).click()
                expect(root_page.get_by_role('heading', name='故事记录')).to_be_visible(timeout=15000)
                pages = []
                for label in ['KP', '玩家1', '玩家2']:
                    with root_page.expect_popup() as popup:
                        root_page.get_by_role('link', name=label+' 测试窗口 ↗', exact=True).click()
                    pages.append(popup.value)
                kp, p1, p2 = pages
                for page, account in zip(pages, ['kp', 'player1', 'player2']):
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('dialog', lambda dialog: dialog.accept())
                    expect(page.get_by_role('heading', name='进入跑团桌面')).to_be_visible(timeout=15000)
                    page.get_by_label('账号', exact=True).fill(account)
                    page.get_by_label('密码', exact=True).fill(password)
                    page.get_by_role('button', name='登录', exact=True).click()
                    expect(page.get_by_role('heading', name='故事记录')).to_be_visible(timeout=15000)
                ok('three_logins_in_one_browser_context', len(context.pages)==4)
                def identity(page):
                    return page.evaluate("async () => (await (await fetch(new URL('api/v1/me', location.href))).json()).accountId")
                ok('root_and_slot_cookies_do_not_override_each_other',
                   [identity(p) for p in [root_page, *pages]]==['kp','kp','player1','player2'])
                for page, account in zip(pages, ['kp','player1','player2']):
                    page.reload()
                    expect(page.get_by_role('heading', name='故事记录')).to_be_visible(timeout=15000)
                    assert identity(page)==account
                ok('all_account_tabs_survive_reload')
                cookies=context.cookies()
                ok('slot_cookies_keep_httponly_samesite_and_scoped_paths',
                   all(any(c['name'].startswith('lf_slot_'+account+'__') and c['path']=='/sessions/'+account+'/'
                           and c['httpOnly'] and c['sameSite']=='Strict' for c in cookies)
                       for account in ['kp','player1','player2']))
                wrong_csrf=p1.evaluate("async () => (await (await fetch(new URL('api/v1/me',location.href))).json()).csrf")
                rejected=kp.evaluate("""async token => (await fetch(new URL('api/v1/logout',location.href), {
                    method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:'{}'})).status""",wrong_csrf)
                ok('csrf_from_another_slot_is_rejected',rejected==403 and identity(kp)=='kp')
                cross_origin=context.request.post(base+'/sessions/kp/api/v1/logout',data='{}',headers={'Origin':'http://example.invalid'})
                ok('adapter_keeps_origin_validation',cross_origin.status==403)
                expect(p1.get_by_role('button',name='导入并激活本包')).to_have_count(0)
                ok('player_tab_does_not_inherit_kp_interface')
                kp.get_by_role('button', name='导入并激活本包').click()
                expect(kp.get_by_role('button', name='导入并激活本包')).to_have_count(0, timeout=20000)
                ok('install_from_frontend')
                p1.locator('#character-form').get_by_label('角色姓名').fill('申请者')
                p1.locator('#character-form').get_by_role('button',name='发送角色申请').click()
                expect(kp.get_by_role('button',name='填入建卡表')).to_be_visible(timeout=15000)
                ok('player_can_request_character')
                kp.get_by_role('button',name='填入建卡表').click()
                expect(kp.locator('#character-form').get_by_label('角色姓名')).to_have_value('申请者')
                ok('kp_reviews_request_with_trusted_sender')
                kp.locator('summary').filter(has_text='冒险生成器').click()
                kp.locator('#adventure-form').get_by_role('button',name='生成并保存私密设定').click()
                expect(kp.locator('#adventure-result p')).to_be_visible(timeout=15000)
                expect(kp.get_by_role('heading',name='操作待处理')).to_have_count(0,timeout=15000)
                gm_api=Client(base,'kp',password)
                player_api=Client(base,'player1',password)
                gm_progress=gm_api.request('/view')['progress']
                player_progress=player_api.request('/view')['progress']
                ok('adventure_persists_for_kp',any(v['eventKey']=='lf.adventure' for v in gm_progress.values()))
                ok('adventure_secret_absent_from_player_view',not any(v['eventKey']=='lf.adventure' for v in player_progress.values()))
                form = kp.locator('#character-form')
                for owner, name in [('player1', '阿澈'), ('player2', '星河')]:
                    form.get_by_label('归属玩家').select_option(owner)
                    form.get_by_label('角色姓名').fill(name)
                    form.get_by_label('目标', exact=True).select_option('0')
                    form.get_by_label('自定义目标／补充说明').fill('寻找失联的同伴')
                    form.get_by_role('button', name='确认创建角色').click()
                    expect(kp.locator('.character-head strong').filter(has_text=name)).to_be_visible(timeout=20000)
                    expect(kp.get_by_role('heading', name='操作待处理')).to_have_count(0, timeout=15000)
                ok('create_characters_with_custom_goals')
                kp.locator('summary').filter(has_text='共同创建飞船').click()
                kp.locator('#ship-form').get_by_role('button', name='保存飞船').click()
                expect(kp.get_by_text('Raptor', exact=True)).to_be_visible(timeout=15000)
                ok('save_shared_ship')
                kp.locator('summary').filter(has_text='发布场景与叙事').click()
                scene = kp.locator('#scene-form')
                scene.get_by_label('场景标题').fill('寂静的边境信标')
                scene.get_by_label('玩家可知的描述').fill('信标停止回应，舷窗外只有一艘没有灯光的飞船。你们怎么办？')
                scene.get_by_role('button', name='向当前频道发布场景').click()
                expect(p1.locator('.scene h2')).to_have_text('寂静的边境信标', timeout=20000)
                ok('publish_scene_to_players')
                client = Client(base, 'kp', password)
                chars = {e['name']: key for key, e in client.request('/view')['entities'].items() if e['configurationId']=='lf.character'}
                action = kp.locator('#action-form')
                action.get_by_label('行动意图').fill('穿越敌舰封锁')
                action.get_by_label('主行动角色').select_option(chars['阿澈'])
                action.get_by_label('已充分准备', exact=True).check()
                action.get_by_label('属于角色专长', exact=True).check()
                action.get_by_label('星河', exact=True).check()
                action.get_by_role('button', name='确认裁定并开放协助').click()
                expect(p2.get_by_role('button', name='进行协助检定')).to_be_visible(timeout=20000)
                ok('create_action_without_new_ruleset')
                captured = {}

                def lose_response(route):
                    payload = route.request.post_data_json['payload']
                    if payload['op']=='action.invoke' and payload['args']['actionId']=='lf.help' and not captured:
                        response = route.fetch()
                        captured.update(response.json())
                        route.abort('failed')
                    else:
                        route.continue_()

                p2.route('**/api/v1/commands', lose_response)
                p2.get_by_role('button', name='进行协助检定').click()
                expect(p2.locator('.pending .long')).to_contain_text('连接中断', timeout=20000)
                assert captured.get('status')=='committed'
                p2.reload()
                expect(p2.get_by_role('button', name='查询并恢复原提交')).to_be_visible(timeout=15000)
                p2.get_by_role('button', name='查询并恢复原提交').click()
                expect(p2.get_by_role('heading', name='操作待处理')).to_have_count(0, timeout=15000)
                ok('reload_recovers_lost_committed_response', captured.get('status')=='committed')
                p2.get_by_role('button', name='分享到当前频道', exact=True).click()
                expect(kp.locator('.card').filter(has_text='lf.help')).to_be_visible(timeout=15000)
                ok('share_host_result_card')
                kp.get_by_role('button', name='关闭协助窗口').click()
                expect(p1.get_by_role('button', name='进行主检定')).to_be_visible(timeout=15000)
                p1.get_by_role('button', name='进行主检定').click()
                expect(p1.get_by_role('button', name='分享到当前频道', exact=True)).to_be_visible(timeout=15000)
                ok('main_roll_from_frontend')
                view = client.request('/view')
                main_id = next(key for key, e in view['entities'].items() if e['configurationId']=='lf.participant' and e['numbers']['role']==1)
                if view['entities'][main_id]['numbers']['insights']==0:
                    client.command('entity.update', {'id': main_id, 'numbers': {'insights': 1}})
                question = p1.locator('[data-form="question"]')
                expect(question).to_be_visible(timeout=15000)
                question.get_by_label('特殊洞察：向主持人提问').fill('谁在信标背后发送求救信号？')
                question.get_by_role('button', name='提交洞察问题').click()
                expect(p1.get_by_text('洞察待回答', exact=False)).to_be_visible(timeout=15000)
                dm = client.command('chat.direct.open', {'accountId': 'player1'})['channelId']
                kp.locator('#channel').select_option(dm, timeout=15000)
                answer = kp.locator('[data-form="answer"]')
                expect(answer).to_be_visible(timeout=15000)
                answer.get_by_label('如实回答').fill('失踪的科学家仍然活着，她正在被迫发送信号。')
                answer.get_by_role('button', name='回复并标记已回答').click()
                expect(p1.get_by_text('洞察已回答，文字保留在问答频道', exact=True)).to_be_visible(timeout=15000)
                ok('private_question_answer_and_durable_state')
                kp.locator('#channel').select_option('general')
                for selector in ['details']:
                    kp.locator(selector).evaluate_all('(items)=>items.forEach(e=>e.open=false)')
                kp.screenshot(path=str(out / 'desktop.png'), full_page=True)
                p1.set_viewport_size({'width': 390, 'height': 844})
                p1.screenshot(path=str(out / 'mobile.png'), full_page=True)
                ok('mobile_has_no_horizontal_overflow', p1.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                journal_keys=kp.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('lf-journal:'))")
                ok('operation_journals_are_scoped_by_slot_and_account',
                   all('lf-journal:slot:'+account+':'+account in journal_keys for account in ['kp','player1','player2']))
                p2.get_by_role('button',name='退出',exact=True).click()
                expect(p2.get_by_role('heading',name='进入跑团桌面')).to_be_visible(timeout=15000)
                ok('logout_only_clears_its_own_slot',identity(kp)=='kp' and identity(p1)=='player1' and identity(root_page)=='kp'
                   and kp.evaluate("localStorage.getItem('lf-journal:slot:kp:kp')!==null && localStorage.getItem('lf-journal:slot:player1:player1')!==null && localStorage.getItem('lf-journal:slot:player2:player2')===null"))
                p2.get_by_label('密码',exact=True).fill(password)
                p2.get_by_role('button',name='登录',exact=True).click()
                expect(p2.get_by_role('heading',name='故事记录')).to_be_visible(timeout=15000)
                ok('slot_relogin_restores_same_account',identity(p2)=='player2')
                ok('no_uncaught_browser_errors', not errors)
                browser.close()
            report = {'passed': len(checks), 'checks': checks, 'scope':'one real browser context, default tab plus three cookie-isolated account tabs; insight may use explicit synthetic state', 'screenshots':str(out.relative_to(PACK)),
                      'sourceHashes': {name: hashlib.sha256((PACK/name).read_bytes()).hexdigest()
                                       for name in ['ui/index.html','ui/app.js','ui/styles.css','tools/launch.py']}}
            (PACK / 'tests/ui-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print('PASS:',len(checks),'browser acceptance checks')
            print('Screenshots:', out.relative_to(ROOT))
        finally:
            proc.terminate()
            proc.wait(timeout=10)
            host_proc.terminate()
            host_proc.wait(timeout=10)


if __name__=='__main__':
    main()
