"""Browser acceptance against a running isolated mini-pack launcher."""
import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
PACK=Path(__file__).resolve().parents[1]

def main():
    base=sys.argv[1];password=Path(sys.argv[2]).read_text(encoding='utf-8')
    errors=[];checks=[]
    def ok(name,condition=True):
        assert condition,name
        checks.append(name)
    with sync_playwright() as p:
        try:browser=p.chromium.launch(headless=True)
        except Exception:browser=p.chromium.launch(channel='msedge',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':900})
        pages=[]
        for user in ['kp','player1','player2']:
            page=context.new_page();pages.append(page);page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('dialog',lambda d:d.accept())
            page.goto(base+'/sessions/'+user+'/')
            page.locator('[name=loginName]').fill(user);page.locator('[name=password]').fill(password)
            page.locator('#login-form button').click();expect(page.locator('nav')).to_be_visible(timeout=15000)
            ok(user+' login and desktop')
        k,p1,p2=pages
        for page in pages:
            for name in (['主持地图','场景资料','人物道具','场景','主持总览'] if page==k else ['场景','线索与机关','背包','场景']):
                page.get_by_role('button',name=name,exact=True).click();expect(page.locator('main')).to_be_visible()
            ok('single tab navigation '+str(pages.index(page)))
        if not k.locator('#queue').is_visible():k.locator('header [data-do=window][data-value=queue]').click()
        expect(k.locator('#queue')).to_be_visible()
        if not k.locator('#queue').evaluate("e=>e.classList.contains('collapsed')"):k.locator('#queue [data-do=collapse]').click()
        ok('queue collapsible',k.locator('#queue').evaluate("e=>e.classList.contains('collapsed')"))
        k.get_by_role('button',name='主持地图',exact=True).click();expect(k.locator('#queue')).to_be_visible();ok('queue survives page change')
        p1.get_by_role('button',name='场景',exact=True).click();p1.locator('#scene-map summary').click();ok('authorized reveal visible','地下室' in p1.locator('#scene-map').inner_text())
        p2.get_by_role('button',name='场景',exact=True).click();ok('hidden room absent for other PL','地下室' not in p2.locator('main').inner_text())
        k.get_by_role('button',name='主持管理',exact=True).click();k.get_by_role('button',name='角色与战斗',exact=True).click();k.locator('summary').filter(has_text='建立其他角色').click();expect(k.locator('#create-form')).to_be_visible();ok('KP management forms')
        k.locator('.subnav button[data-value=scenario]').click();expect(k.locator('#scenario-edit-form')).to_be_visible();ok('scenario editing form')
        k.get_by_role('button',name='开局与存档',exact=True).click();k.locator('summary').filter(has_text='配置文件导入与导出').click();expect(k.locator('#upload-pack-form')).to_be_visible();ok('trusted file import form');k.get_by_role('button',name='角色与战斗',exact=True).click();k.locator('summary').filter(has_text='建立其他角色').click()
        k.locator('#create-form [name=name]').fill('浏览器验收角色')
        k.locator('#create-form [name=owner]').select_option('player2')
        k.locator('#create-form button[type=submit], #create-form button:not([type])').last.click()
        expect(k.locator('#notice')).to_contain_text('已提交至主机并完成',timeout=15000);ok('browser creates approved character and initial item')
        k.get_by_role('button',name='建立海岸追踪者',exact=True).click()
        expect(k.locator('#combat-form [name=attacker] option').filter(has_text='无名追踪者')).to_have_count(1,timeout=15000);ok('browser creates scenario NPC')
        ok('PL lacks KP management',p1.get_by_role('button',name='主持管理',exact=True).count()==0)
        k.screenshot(path=str(PACK/'tests/output/kp-desktop.png'),full_page=True)
        p1.screenshot(path=str(PACK/'tests/output/pl-map.png'),full_page=True)
        ok('no browser script errors',not errors)
        browser.close()
    result={'passed':len(checks),'checks':checks,'errors':errors,'viewport':[1440,900]}
    (PACK/'tests/ui-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
