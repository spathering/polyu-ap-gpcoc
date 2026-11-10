"""Build a self-contained Python/Tk desktop distribution (no host runtime bundled)."""
import os
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
lan=root.parents[1]/'engineering/network-lan/src'
os.environ['PYINSTALLER_CONFIG_DIR']=str(root/'.build/cache')
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--name','RoomManager',
                '--distpath',str(root/'dist'),'--workpath',str(root/'.build/work'),'--specpath',str(root/'.build'),
                '--paths',str(root/'python'),'--paths',str(lan),'--collect-all','websockets',
                str(root/'manager.py')],check=True)
dist=root/'dist/RoomManager'
shutil.copy2(root/'requirements-runtime.lock',dist/'requirements-runtime.lock')
sources=list((root/'python').rglob('*.py'))+list(lan.rglob('*.py'))+[root/'manager.py']
manifest={'version':'0.2.0','frontend':'Python/Tkinter','python':sys.version.split()[0],
          'sha256':hashlib.sha256((dist/'RoomManager.exe').read_bytes()).hexdigest(),
          'sources':{str(p.relative_to(root.parents[1])).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
(dist/'release.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(dist/'README.txt').write_text('OnlineCOC 0.2.0 Python 桌面管理器\n复制整个 RoomManager 文件夹。无需另外安装 Python。\n先启动宿主，在房间管理页填写真实宿主或 LAN 网关地址，以 KP 登录。\n局域网页选择上游本机宿主、明确的本机 LAN IPv4 和端口。只适用于可信 LAN（HTTP 不加密）。\n同一局域网的玩家可打开共享地址访问通用操作台。不要填写仅转发 HTTP 的配置包网页端口。\n启动独立 LAN 面板：RoomManager.exe --lan\n关闭工具会停止本工具启动的网关，宿主继续运行。\n',encoding='utf-8')
print(dist/'RoomManager.exe')
