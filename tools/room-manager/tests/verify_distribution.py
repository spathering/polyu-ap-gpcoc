"""Open both entry modes from a copied standalone distribution and close our windows only."""
import ctypes
import json
import shutil
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'.test-output'/time.strftime('portable-python-%Y%m%d-%H%M%S')
target=out/'RoomManager'
shutil.copytree(ROOT/'dist/RoomManager',target)
user=ctypes.windll.user32
callback=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
user.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p]
user.GetWindowTextW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_int]
user.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
user.IsWindowVisible.argtypes=[ctypes.c_void_p]
results=[]
for mode,title in (([], 'OnlineCOC 房间管理器'),(['--lan'],'OnlineCOC 局域网联机')):
    p=subprocess.Popen([str(target/'RoomManager.exe'),'--settings-dir',str(out/'settings')]+mode,cwd=out)
    windows=[]
    def visit(hwnd,_):
        pid=ctypes.c_ulong();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value==p.pid and user.IsWindowVisible(hwnd):
            text=ctypes.create_unicode_buffer(256);user.GetWindowTextW(hwnd,text,256)
            if text.value.startswith(title):windows.append(hwnd)
        return True
    try:
        for _ in range(120):
            user.EnumWindows(callback(visit),0)
            if windows:break
            if p.poll() is not None:raise AssertionError('打包程序提前退出')
            time.sleep(.1)
        assert windows, '未找到预期的原生窗口'
        user.PostMessageW(windows[0],0x10,None,None)
        assert p.wait(timeout=15)==0
        results.append({'mode':mode,'nativeWindow':True,'cleanExit':True})
    finally:
        if p.poll() is None:p.terminate();p.wait(10)
(ROOT/'tests/distribution-results.json').write_text(json.dumps({'passed':4,'failed':0,'modes':results},ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS independent Python EXE: manager + LAN panel, 4 checks')
