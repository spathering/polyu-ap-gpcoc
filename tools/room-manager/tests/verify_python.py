"""Isolated real host + native Tk + LAN interface regression. No production data."""
import ctypes
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1]
ROOT = TOOL.parents[1]
sys.path[:0] = [str(TOOL/'python'), str(ROOT/'engineering/network-lan/src')]
from room_manager.protocol import Client, APIError, Assembler, endpoint
from room_manager.state import Observer, Settings
from onlinecoc_lan import Config, Gateway

OUT = TOOL/'.test-output'/time.strftime('python-%Y%m%d-%H%M%S')
OUT.mkdir(parents=True)
checks = []

def check(ok, text):
    if not ok:
        raise AssertionError(text)
    checks.append(text)
    print('PASS', text, flush=True)

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def wait(predicate, root=None, timeout=12):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        if root:
            root.update()
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError('等待超时')

def command(c, op, args, success=True, tokens=None):
    r=c.request('commands', c.envelope(op,args,tokens))
    check(r['status']==('committed' if success else 'rejected'), op+': '+r['status'])
    time.sleep(.3)
    return r.get('result')

def token(c, key):
    return {key:c.snapshot()[0]['entities'][key]['viewToken']}

def request(url,path,headers=None,data=None):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(urllib.request.Request(url+path,headers=headers or {},data=data),timeout=5) as r:
            return r.status,r.read()
    except urllib.error.HTTPError as e:
        return e.code,e.read()

def screenshot(root, path):
    # Print only this native window, even when another user window occludes it.
    from PIL import Image
    root.update()
    hwnd=ctypes.windll.user32.GetParent(root.winfo_id())
    from ctypes import wintypes
    rect=wintypes.RECT();ctypes.windll.user32.GetWindowRect(hwnd,ctypes.byref(rect))
    width,height=rect.right-rect.left,rect.bottom-rect.top
    gdi,user=ctypes.windll.gdi32,ctypes.windll.user32
    user.GetWindowDC.restype=ctypes.c_void_p
    gdi.CreateCompatibleDC.argtypes=[ctypes.c_void_p];gdi.CreateCompatibleDC.restype=ctypes.c_void_p
    gdi.CreateCompatibleBitmap.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int];gdi.CreateCompatibleBitmap.restype=ctypes.c_void_p
    gdi.SelectObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p];gdi.SelectObject.restype=ctypes.c_void_p
    gdi.DeleteDC.argtypes=[ctypes.c_void_p];gdi.DeleteObject.argtypes=[ctypes.c_void_p]
    user.PrintWindow.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint]
    user.ReleaseDC.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
    dc=user.GetWindowDC(hwnd);mem=gdi.CreateCompatibleDC(dc);bmp=gdi.CreateCompatibleBitmap(dc,width,height);old=gdi.SelectObject(mem,bmp)
    class Header(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('width',wintypes.LONG),('height',wintypes.LONG),('planes',wintypes.WORD),('bits',wintypes.WORD),('compression',wintypes.DWORD),('image',wintypes.DWORD),('x',wintypes.LONG),('y',wintypes.LONG),('used',wintypes.DWORD),('important',wintypes.DWORD)]
    header=Header(ctypes.sizeof(Header),width,-height,1,32,0,0,0,0,0,0)
    try:
        user.PrintWindow(hwnd,mem,2)
        gdi.SelectObject(mem,old)
        pixels=ctypes.create_string_buffer(width*height*4)
        gdi.GetDIBits.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint]
        gdi.GetDIBits(mem,bmp,0,height,pixels,ctypes.byref(header),0)
        Image.frombuffer('RGB',(width,height),pixels,'raw','BGRX',0,1).save(path)
    finally:
        gdi.DeleteObject(bmp);gdi.DeleteDC(mem);user.ReleaseDC(hwnd,dc)

def run():
    for invalid in ('http://8.8.8.8:80','http://0.0.0.0:80','http://user@127.0.0.1:80','http://127.0.0.1/a'):
        try:
            endpoint(invalid)
            raise AssertionError('bad endpoint accepted')
        except APIError:
            check(True,'拒绝无效地址 '+invalid)
    o=Observer();o.sample('view',{'a/b':{'n':1,'viewToken':'old'}});check(not o.records,'首样本只作基线')
    o.sample('view',{'a/b':{'n':None,'viewToken':'new'}});check(len(o.records)==1 and o.records[0][0]['path']=='/a~1b/n','路径与 token 过滤')
    o.sample('view',{});check(o.records[-1][0]['kind']=='不再可见','消失不伪造删除')
    for n in range(2100):o.sample('limit',{'v':n})
    check(len(o.records)==2000,'观察环上限')
    parser=Assembler();parser.feed({'type':'snapshot.begin','id':'x','parts':2})
    parser.feed({'type':'snapshot.part','id':'x','index':1,'data':'1}'})
    parser.feed({'type':'snapshot.part','id':'x','index':0,'data':'{"a":'})
    check(parser.feed({'type':'snapshot.end','id':'x'})=={'a':1},'乱序完整分片')
    parser.feed({'type':'snapshot.begin','id':'bad','parts':1})
    try:parser.feed({'type':'snapshot.end','id':'bad'});raise AssertionError('missing part accepted')
    except APIError:check(True,'缺片不发布')
    password='python-lan-test-2026'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',ONLINECOC_BOOTSTRAP_PASSWORD=password)
    host=[str(ROOT/'engineering/.venv/Scripts/python.exe'),str(ROOT/'engineering/backend/scripts/run.py'),'--data-dir',str(OUT/'host')]
    subprocess.run(host+['init'],env=env,check=True,stdout=subprocess.DEVNULL)
    host_port=port();upstream=f'http://127.0.0.1:{host_port}'
    log=(OUT/'host.log').open('w')
    server=subprocess.Popen(host+['serve','--port',str(host_port),'--host-control-dir',str(OUT/'host-control')],env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    gateway=None;clients=[];root=None
    try:
        for _ in range(100):
            try:
                if request(upstream,'/api/v1/capabilities')[0]==200:break
            except OSError:time.sleep(.1)
        # Explicit physical LAN address when supplied; loopback is the repeatable default.
        bind=os.environ.get('ONLINECOC_TEST_LAN_IP','127.0.0.1')
        gateway=Gateway(Config(upstream,bind,port()));gateway.start();url=gateway.config.url
        check(request(url,'/')[0]==200,'经网关获取通用操作台')
        check(request(url,'/api/v1/host-control/accounts')[0]==404,'本机账号控制接口不暴露')
        check(request(url,'/api/v1/capabilities',{'Host':'evil.invalid'})[0]==403,'拒绝 Host 伪装')
        check(request(url,'/api/v1/login',{'Origin':'http://evil.invalid','Content-Type':'application/json'},b'{}')[0]==403,'拒绝跨来源写入')
        check(request(url,'/api/v1/login',{'Content-Type':'application/json'},b'{}')[0]==403,'写入必须带正确 Origin')
        check(request(url,'/api/v1/commands',{'Origin':url},b'x'*65537)[0]==413,'请求体限额')
        for account in ('kp','kp'):
            c=Client(url);clients.append(c);c.login(account,password);wait(lambda:c.connected)
        a,b=clients
        check(a.snapshot()[0]['accountId']=='kp' and b.connected,'两个独立会话通过 LAN 实时连接')
        player=Client(url);clients.append(player)
        try:player.login('player1',password);raise AssertionError('player manager accepted')
        except APIError:check(True,'玩家账号不可进入管理 GUI')
        player.close()
        command(a,'configuration.put',dict(configurationId='lan.item',revision='1',typeRef='item',defaults={'quantity':1},behaviors={}))
        key=command(a,'entity.create',dict(configurationId='lan.item',name='局域网物品'))
        wait(lambda:key in b.snapshot()[0]['entities'])
        old=b.envelope('entity.patch',{'id':key,'name':'过期'},token(b,key))
        command(a,'entity.patch',{'id':key,'name':'已改'},tokens=token(a,key))
        try:b.request('commands',old);raise AssertionError('stale token accepted')
        except APIError as e:check(str(e)=='VERSION_CONFLICT','跨网关旧令牌冲突')
        command(a,'entity.update',{'id':key,'numbers':{'quantity':2},'tags':['melee'],'rules':{},'owner':None,'visibility':'public'},tokens=token(a,key))
        relation=command(a,'relation.set',{'sourceId':'actor-player1','targetId':key,'relationType':'references'})
        command(a,'entity.archive',{'id':key},False,token(a,key))
        command(a,'relation.remove',{'id':relation})
        command(a,'configuration.remove',{'id':'lan.item'},False)
        command(a,'progress.set',{'ownerKind':'entity','ownerId':key,'eventKey':'unlock','value':True})
        command(a,'member.update',{'accountId':'kp','active':False},False)
        command(a,'room.status',{'status':'paused'});command(a,'room.status',{'status':'active'})
        envelope=a.envelope('entity.patch',{'id':key,'name':'幂等'},token(a,key));first=a.request('commands',envelope)
        check(first==a.request('commands',envelope)==a.request('receipts/'+envelope['payload']['commandId']),'回执与同封套重发幂等')
        asset=a.request('assets',raw=b'test',headers={'x-asset-name':'test.bin','x-asset-visibility':'public'})['assetId']
        check(a.request('assets/'+asset,binary=True)==b'test','LAN 素材上传下载')
        command(a,'asset.remove',{'assetId':asset})
        check(bool(a.request('backup',{})['backupId']),'LAN 请求宿主创建备份')
        revision=command(a,'rule.stage',{'sources':{'test.lua':"return flow('test.wait', {}, {ask('w', {role='kp', seconds=60, yes='end', no='end', timeout='end'})})"}})
        check('artifact' in a.request('admin/artifacts/'+revision),'规则工件查看')
        command(a,'rule.activate',{'revision':revision})
        flow=command(a,'action.invoke',{'actionId':'test.wait','input':{}})
        wait(lambda: bool(a.snapshot()[0]['waits']))
        wid,w=next(iter(a.snapshot()[0]['waits'].items()))
        command(a,'flow.respond',{'waitId':wid,'revision':w['revision'],'answer':False})
        command(a,'flow.cancel',{'flowId':flow['flowId']})
        command(a,'flow.retry',{'flowId':flow['flowId']},False)
        # Native Tk window, real handlers and real host state.
        import tkinter as tk
        from room_manager.gui import Manager
        root=tk.Tk();ui=Manager(root,Settings(OUT/'settings'))
        ui.address.set(url);ui.password.set(password);ui.connect_button.invoke()
        wait(lambda: bool(ui.admin),root)
        check(root.winfo_ismapped() and ui.password.get()=='','真实 Python 窗口登录并清空密码')
        ui.category.set('entities');ui.change_category();ui.selected_key=key;ui.selected=ui.view['entities'][key];ui.show(ui.selected)
        ui.operation.set('entity.patch');ui.build_fields();ui.fields['name'][1].set('Python 窗口修改')
        ui.submit_button.invoke();wait(lambda: not ui.busy and not ui.unknown,root)
        wait(lambda: a.snapshot()[0]['entities'][key]['name']=='Python 窗口修改',root)
        check(True,'Python 表单真实提交')
        ui.add_watch();check(len(ui.settings.data['watches'])==1,'关注定义保存')
        ui.unknown=True;ui.submit();check(ui.unknown,'结果未知不换 ID 重试');ui.unknown=False
        screenshot(root,OUT/'manager.png')
        ui.lan.upstream.set(upstream);ui.lan.bind.set(bind);ui.lan.port.set(str(port()));ui.lan.trusted.set(True)
        ui.lan.start_button.invoke();wait(lambda:ui.lan.gateway and ui.lan.gateway.running and not ui.lan.busy,root)
        check(True,'局域网 GUI 启动独立网关')
        notebook=ui.lan.master;notebook.select(ui.lan);root.update();screenshot(root,OUT/'lan-panel.png')
        ui.lan.stop();wait(lambda:not ui.lan.gateway.running and not ui.lan.busy,root)
        check(request(upstream,'/api/v1/capabilities')[0]==200,'GUI 停止网关不停止宿主')
        ui.disconnect();check(not ui.view and ui.baseline is None,'断开清理视图和草稿');root.destroy();root=None
        gateway.stop();wait(lambda:not a.connected)
        check(a.snapshot()[0] is None,'网关停止后清空实时视图')
        gateway.start();wait(lambda:a.connected)
        check(a.snapshot()[1]>1,'网关重启建立新观察段')
        (OUT/'results.json').write_text(json.dumps({'passed':len(checks),'failed':0,'checks':checks,'lanBind':bind,'upstreamPort':host_port,'gatewayPort':gateway.config.port},ensure_ascii=False,indent=2),encoding='utf-8')
        print('RESULTS',OUT,flush=True)
    finally:
        if root:
            ui.lan.shutdown()
            root.destroy()
        for c in clients:c.close()
        if gateway:gateway.stop()
        server.terminate();server.wait(timeout=15);log.close()

if __name__=='__main__':
    run()
