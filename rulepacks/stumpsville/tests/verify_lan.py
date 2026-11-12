"""Real Tk window, package/host on a WLAN IPv4, and double-click CMD smoke test."""
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import secrets
import socket
import subprocess
import sys
import time
import tkinter as tk
from unittest.mock import patch

from harness import PACK, Account
from lan import LanService, LanWindow, discover_adapters, private_ipv4
import httpx


def pump(root, predicate, timeout=90):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        root.update()
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError('Timed out waiting for GUI/service state')


def available_port(ip):
    with socket.socket() as sock:
        sock.bind((ip, 0))
        return sock.getsockname()[1]


def screenshot(root, path):
    root.update()
    env = {**os.environ, 'SV_SHOT':str(path), 'SV_HWND':str(root.winfo_id())}
    script = """
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class LanCapture {
 [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint flags);
 [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out Rect r);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
 [StructLayout(LayoutKind.Sequential)] public struct Rect { public int left,top,right,bottom; }
}
'@
$handle=[LanCapture]::GetAncestor([IntPtr]([long]$env:SV_HWND),2)
$rect=New-Object LanCapture+Rect
[LanCapture]::GetClientRect($handle,[ref]$rect) | Out-Null
$bmp=New-Object System.Drawing.Bitmap $rect.right,$rect.bottom
$graphics=[System.Drawing.Graphics]::FromImage($bmp)
try {
 $dc=$graphics.GetHdc()
 try { if (-not [LanCapture]::PrintWindow($handle,$dc,3)) { throw 'Window capture failed' } }
 finally { $graphics.ReleaseHdc($dc) }
 $bmp.Save($env:SV_SHOT,[System.Drawing.Imaging.ImageFormat]::Png)
} finally { $graphics.Dispose(); $bmp.Dispose() }
"""
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],env=env,
                   capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)


def windows():
    rows = []
    user = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    @callback_type
    def visit(hwnd, _):
        title = ctypes.create_unicode_buffer(512)
        user.GetWindowTextW(ctypes.c_void_p(hwnd), title, 512)
        if title.value == '树桩镇 · 局域网启动':
            pid = ctypes.c_ulong()
            user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
            rows.append((hwnd,pid.value))
        return True
    user.EnumWindows(visit, 0)
    return rows


def test_cmd(data):
    before = {h for h,_ in windows()}
    command = f'"{os.environ["COMSPEC"]}" /d /s /c ""{PACK / "start-lan.cmd"}" --data-dir "{data}" --no-browser"'
    result = subprocess.run(command,timeout=20,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0
    target = None
    for _ in range(200):
        target = next(((h,p) for h,p in windows() if h not in before),None)
        if target:break
        time.sleep(.1)
    assert target,'Double-click entry did not open a native window'
    hwnd,pid = target
    ctypes.windll.user32.PostMessageW(ctypes.c_void_p(hwnd),0x0010,0,0)
    for _ in range(100):
        if not ctypes.windll.user32.IsWindow(ctypes.c_void_p(hwnd)):break
        time.sleep(.1)
    else:
        subprocess.run(['taskkill.exe','/PID',str(pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        raise AssertionError('Entry window did not close')
    assert not data.exists(),'Opening a launcher must not create/initialize a game'


def gui_suite():
    checks=[]
    adapters=discover_adapters()
    assert adapters and all(private_ipv4(a.address) for a in adapters)
    assert len({a.address for a in adapters}) == len(adapters)
    checks.append('real connected WLAN adapters are named, filtered to private IPv4 and deduplicated')
    folder=PACK/'tests/output'/('lan-'+secrets.token_hex(4))
    data=folder/'中文 存档'
    folder.mkdir(parents=True)
    shots=PACK/'tests/output/screenshots';shots.mkdir(exist_ok=True)
    root=tk.Tk();root.geometry('+60+60')
    window=LanWindow(root,data,open_browser=False)
    try:
        pump(root,lambda: not window.scanning)
        address=adapters[0].address
        window.network.set(next(a.label for a in window.adapters if a.address==address))
        port=available_port(address)
        password=secrets.token_urlsafe(16)
        window.password.set(password);window.confirm.set(password)
        window.port.set('invalid');window.start_button.invoke()
        assert '端口必须' in window.status.get() and not window.service.active
        window.port.set(str(port));window.confirm.set('mismatch');window.start_button.invoke()
        assert '不一致' in window.status.get() and not window.service.active
        window.confirm.set(password)
        checks.append('invalid port and mismatching first-run passwords are explained before starting or changing a save')

        window.start_button.invoke()
        pump(root,lambda: bool(window.url) or window.failed)
        assert window.url,window.status.get()
        origin=window.url.rstrip('/')
        assert window.url==f'http://{address}:{port}/'
        assert not window.password.get() and not window.confirm.get()
        assert window.service.runtime.command[0].endswith('python.exe')
        host=window.service.runtime.process
        assert host.poll() is None
        checks.append('first-run password setup initializes the real host locally; pythonw GUI serves the full package on selected IPv4 and port')

        kp,p1,p2=[Account(origin,n,password,n) for n in ('kp','player1','player2')]
        assert kp.state()['role']=='kp' and p1.state()['accountId']=='player1' and p2.state()['accountId']=='player2'
        p1.action('note',{'text':'LAN-PERSISTENCE'})
        with httpx.Client(base_url=origin,trust_env=False) as client:
            assert '树桩镇' in client.get('/').text
            assert client.get('/app.js').status_code==200
            assert client.post('/setup',headers={'Origin':origin},json={'password':'blocked'}).status_code==403
            assert client.get('/api/v1/host-control/accounts').status_code==404
            assert client.post('/api/v1/login',headers={'Origin':'http://invalid.example'},json={}).status_code==400
        checks.append('KP and two PL sessions use full game routes; remote bootstrap, local account control and forged origins stay blocked')
        window.copy_button.invoke();root.update()
        assert root.clipboard_get()==window.url
        with patch('lan.webbrowser.open') as opened:
            window.browser_button.invoke();opened.assert_called_once_with(origin+'/sessions/kp/')
        screenshot(root,shots/'lan-running.png')
        checks.append('native window shows/copies exact player address and opens the separate KP login entry')

        duplicate=LanService(data,queue.Queue())
        duplicate.start(address,available_port(address))
        pump(root,lambda:not duplicate.active)
        events=list(duplicate.events.queue)
        assert any(kind=='error' and '存档' in value for kind,value in events)
        assert host.poll() is None and p1.state()['note']=='LAN-PERSISTENCE'
        occupied=LanService(folder/'unused',queue.Queue())
        occupied.start(address,port,password)
        pump(root,lambda:not occupied.active)
        assert any(kind=='error' and '端口' in value for kind,value in list(occupied.events.queue))
        assert not (folder/'unused').exists()
        checks.append('duplicate save and occupied port fail clearly without stopping the existing room or creating another save')

        window.stop_button.invoke();pump(root,lambda:not window.service.active and not window.busy)
        assert not window.url and str(window.copy_button['state'])=='disabled' and host.poll() is not None
        with socket.socket() as sock: assert sock.connect_ex((address,port))!=0
        stored=json.loads((data/'lan-settings.json').read_text(encoding='utf8'))
        assert stored=={'address':address,'port':port}
        checks.append('stop clears the stale address, stops owned backend, releases listening port and saves only IP/port preferences')

        window.start_button.invoke();pump(root,lambda:bool(window.url) or window.failed)
        assert window.url,window.status.get()
        p1=Account(origin,'player1',password,'player1')
        assert p1.state()['note']=='LAN-PERSISTENCE'
        host=window.service.runtime.process
        checks.append('restart on the same data directory preserves existing accounts and saved game data without asking for a new password')
        window.close()
        deadline=time.monotonic()+30
        while window.service.active and time.monotonic()<deadline:
            root.update();time.sleep(.05)
        assert not window.service.active and host.poll() is not None
        checks.append('closing the native window stops the owned adapter and host while retaining the save')
    finally:
        window.service.stop()
        if window.service.thread:window.service.thread.join(30)
        try:root.destroy()
        except tk.TclError:pass
    test_cmd(folder/'entry 中文')
    checks.append('actual start-lan.cmd opens pythonw native window from a space/Chinese path and closes without modifying a save')
    report={'passed':True,'checkedAt':datetime.now().astimezone().isoformat(),'checks':checks,
            'network':'real private WLAN IPv4, all clients on this physical computer; cross-device firewall not tested'}
    (PACK/'tests/lan-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (PACK/'tests/output/lan-error.log').unlink(missing_ok=True)
    return report


if __name__=='__main__':
    # Run this with pythonw as the shipped entry does; preserve errors in a file.
    try:
        result=gui_suite()
        if sys.stdout:print(json.dumps(result,ensure_ascii=False))
    except Exception:
        import traceback
        (PACK/'tests/output/lan-error.log').write_text(traceback.format_exc(),encoding='utf8')
        raise
