"""Double-click LAN launcher for this package; no engine implementation imports."""
import argparse
import asyncio
from dataclasses import dataclass
import ipaddress
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

sys.dont_write_bytecode = True
PACK = Path(__file__).resolve().parents[1]
NETWORKS = tuple(ipaddress.ip_network(value) for value in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))


def private_ipv4(value):
    try:
        ip = ipaddress.ip_address(value)
        return ip.version == 4 and any(ip in network for network in NETWORKS)
    except ValueError:
        return False


@dataclass(frozen=True)
class Adapter:
    name: str
    address: str
    gateway: bool = False

    @property
    def label(self):
        return f'{self.name} · {self.address}' + ('（有默认网关）' if self.gateway else '')


def discover_adapters():
    """Read connected Windows adapters; never change routes or firewall settings."""
    found = []
    if os.name == 'nt':
        script = r"""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$rows = @(Get-NetIPConfiguration -All | Where-Object { $_.NetAdapter.Status -eq 'Up' } | ForEach-Object {
    $cfg = $_
    foreach ($ip in $cfg.IPv4Address) {
        [pscustomobject]@{name=$cfg.InterfaceAlias; address=$ip.IPAddress; gateway=([bool]$cfg.IPv4DefaultGateway)}
    }
})
ConvertTo-Json -InputObject $rows -Compress
"""
        try:
            result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                capture_output=True, timeout=15, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            rows = json.loads(result.stdout.decode('utf-8-sig'))
            for row in rows:
                if private_ipv4(row['address']):
                    found.append(Adapter(row['name'], row['address'], bool(row['gateway'])))
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
            pass
    if not found:
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                address = info[4][0]
                if private_ipv4(address):
                    found.append(Adapter('本机网卡（名称不可用）', address))
        except OSError:
            pass
    return sorted({a.address: a for a in found}.values(), key=lambda a: (not a.gateway, a.name, a.address))


class LanService:
    """Own exactly one package adapter and its child host, until stop/close."""
    def __init__(self, data, events):
        self.data, self.events = Path(data), events
        self.thread = None
        self.cancel = threading.Event()
        self.runtime = self.server = None

    @property
    def active(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, address, port, password=None):
        if self.active:
            raise ValueError('当前房间仍在运行，请先停止。')
        if not private_ipv4(address):
            raise ValueError('请选择本机实际的局域网 IPv4。')
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError('端口必须是 1–65535 的整数。')
        if not (self.data/'host').exists() and (not isinstance(password, str) or not 8 <= len(password) <= 128):
            raise ValueError('首次使用请设置8–128位初始密码。')
        self.cancel.clear()
        self.thread = threading.Thread(target=self._run, args=(address, port, password), daemon=False)
        self.thread.start()

    def stop(self):
        self.cancel.set()

    def _run(self, address, port, password):
        listener = None
        runtime = None
        try:
            # Retain the socket between validation and serving, avoiding a port race.
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name == 'nt':
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                listener.bind((address, port))
            except OSError as error:
                raise ValueError('无法使用所选 IP 或端口：端口可能已占用，或网卡已断开。请刷新网卡或换一个端口。') from error
            from launch import Runtime, create_app
            import uvicorn
            try:
                runtime = Runtime(argparse.Namespace(data_dir=self.data, bind=address, port=port, backend_port=0))
            except PermissionError as error:
                raise ValueError('存档正在被使用或没有写入权限。请先关闭树桩镇原启动器，再重试。') from error
            self.runtime = runtime
            if os.name == 'nt' and Path(runtime.command[0]).name.lower() == 'pythonw.exe':
                # The background CLI needs redirected standard streams even when
                # our GUI was launched without a console.
                runtime.command[0] = str(Path(runtime.command[0]).with_name('python.exe'))
            if self.cancel.is_set():
                return
            if not runtime.host_data.exists():
                self.events.put(('status', '正在首次准备房间，请稍候…'))
                runtime.setup(password)
            password = None
            if self.cancel.is_set():
                return
            self.server = uvicorn.Server(uvicorn.Config(create_app(runtime), log_config=None, access_log=False,
                log_level='warning', timeout_graceful_shutdown=8))

            async def serve():
                async def watch():
                    announced = False
                    while True:
                        if self.cancel.is_set():
                            self.server.should_exit = True
                        if self.server.started and not announced and not self.cancel.is_set():
                            announced = True
                            settings = {'address': address, 'port': port}
                            try:
                                (self.data/'lan-settings.json').write_text(json.dumps(settings, indent=2)+'\n', encoding='utf-8')
                            except OSError:
                                pass  # Preferences must not interrupt a running room.
                            self.events.put(('running', runtime.origin + '/'))
                        await asyncio.sleep(.1)
                watcher = asyncio.create_task(watch())
                try:
                    await self.server.serve(sockets=[listener])
                    if not self.server.started and not self.cancel.is_set():
                        raise RuntimeError('房间没有成功启动，请查看存档目录中的 host.log。')
                finally:
                    watcher.cancel()
                    await asyncio.gather(watcher, return_exceptions=True)
            asyncio.run(serve())
        except Exception as error:
            self.events.put(('error', str(error)))
        finally:
            password = None
            try:
                if runtime:
                    runtime.close()
            except Exception as error:
                self.events.put(('error', '房间清理失败：'+str(error)))
            finally:
                if listener:
                    listener.close()
                self.server = self.runtime = None
                self.events.put(('stopped', None))


class LanWindow:
    def __init__(self, root, data=PACK/'runtime', open_browser=True):
        self.root, self.data, self.open_browser = root, Path(data), open_browser
        self.events = queue.Queue()
        self.service = LanService(self.data, self.events)
        self.adapters = []
        self.closing = self.scanning = self.busy = False
        self.url = ''
        self.failed = False
        root.title('树桩镇 · 局域网启动')
        root.geometry('780x630')
        root.minsize(700, 590)
        root.protocol('WM_DELETE_WINDOW', self.close)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text='树桩镇 · 局域网联机', font=('Microsoft YaHei UI', 18, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 8))
        ttk.Label(frame, text='同一局域网的玩家用浏览器打开连接地址，各自登录账号。').grid(row=1, column=0, columnspan=3, sticky='w', pady=(0, 20))
        ttk.Label(frame, text='网卡与本机 IP').grid(row=2, column=0, sticky='w', padx=(0, 12))
        self.network = tk.StringVar()
        self.combo = ttk.Combobox(frame, textvariable=self.network, state='readonly', width=48)
        self.combo.grid(row=2, column=1, sticky='ew')
        self.refresh_button = ttk.Button(frame, text='刷新网卡', command=self.scan)
        self.refresh_button.grid(row=2, column=2, padx=(8, 0))
        settings = {}
        try:
            settings = json.loads((self.data/'lan-settings.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
        self.preferred = settings.get('address') if isinstance(settings, dict) else None
        self.port = tk.StringVar(value=str(settings.get('port', 8899) if isinstance(settings, dict) else 8899))
        ttk.Label(frame, text='玩家连接端口').grid(row=3, column=0, sticky='w', pady=16)
        self.port_input = ttk.Spinbox(frame, from_=1, to=65535, textvariable=self.port, width=12)
        self.port_input.grid(row=3, column=1, sticky='w')
        self.setup_frame = ttk.LabelFrame(frame, text='首次使用：准备房间', padding=12)
        self.setup_frame.grid(row=4, column=0, columnspan=3, sticky='ew', pady=(0, 12))
        self.password, self.confirm = tk.StringVar(), tk.StringVar()
        ttk.Label(self.setup_frame, text='初始密码').grid(row=0, column=0, padx=(0, 12))
        ttk.Entry(self.setup_frame, textvariable=self.password, show='●', width=22).grid(row=0, column=1)
        ttk.Label(self.setup_frame, text='再次输入').grid(row=0, column=2, padx=12)
        ttk.Entry(self.setup_frame, textvariable=self.confirm, show='●', width=22).grid(row=0, column=3)
        ttk.Label(self.setup_frame, text='8–128位；用于首次创建 kp、player1、player2，已有账号不会重置。').grid(row=1, column=0, columnspan=4, sticky='w', pady=(8, 0))
        self.setup_visibility()
        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=3, sticky='w', pady=(0, 16))
        self.start_button = ttk.Button(buttons, text='启动局域网', command=self.start, state='disabled')
        self.start_button.pack(side='left')
        self.stop_button = ttk.Button(buttons, text='停止房间', command=self.stop, state='disabled')
        self.stop_button.pack(side='left', padx=10)
        self.status = tk.StringVar(value='正在识别网卡…')
        ttk.Label(frame, textvariable=self.status, wraplength=715).grid(row=6, column=0, columnspan=3, sticky='w', pady=(0, 12))
        links = ttk.LabelFrame(frame, text='玩家连接地址', padding=14)
        links.grid(row=7, column=0, columnspan=3, sticky='ew')
        links.columnconfigure(0, weight=1)
        self.address = tk.StringVar(value='启动成功后显示')
        ttk.Entry(links, textvariable=self.address, state='readonly', font=('Consolas', 14)).grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 12))
        self.copy_button = ttk.Button(links, text='复制玩家地址', command=self.copy, state='disabled')
        self.copy_button.grid(row=1, column=0, sticky='w')
        self.browser_button = ttk.Button(links, text='打开主持登录页', command=self.open_kp, state='disabled')
        self.browser_button.grid(row=1, column=1, sticky='e')
        ttk.Label(frame, text='启动窗口需保持打开；关闭窗口会停止房间，存档保留。\n自动裁决还需一个已登录的 KP 网页保持在线。\n若其他设备无法连接，请检查同网段／访客网络隔离，并允许 Windows 防火墙的所选端口。', wraplength=715).grid(row=8, column=0, columnspan=3, sticky='w', pady=16)
        ttk.Label(frame, text='存档：'+str(self.data.resolve()), wraplength=715, foreground='#666666').grid(row=9, column=0, columnspan=3, sticky='w')
        self.scan()
        root.after(100, self.tick)

    def setup_visibility(self):
        if (self.data/'host').exists():
            self.setup_frame.grid_remove()
        else:
            self.setup_frame.grid()

    def scan(self):
        if self.busy or self.scanning:
            return
        self.scanning = True
        self.refresh_button.configure(state='disabled')
        self.start_button.configure(state='disabled')
        self.status.set('正在识别已连接的网卡…')
        def work():
            self.events.put(('adapters', discover_adapters()))
        threading.Thread(target=work, daemon=True).start()

    def start(self):
        if self.busy:
            return
        try:
            adapter = next((a for a in self.adapters if a.label == self.network.get()), None)
            if not adapter:
                raise ValueError('没有可用的局域网网卡，请连接 Wi-Fi 或网线后刷新。')
            try:
                port = int(self.port.get())
            except ValueError:
                raise ValueError('端口必须是 1–65535 的整数。')
            if not (self.data/'host').exists() and self.password.get() != self.confirm.get():
                raise ValueError('两次输入的初始密码不一致。')
            self.service.start(adapter.address, port, self.password.get())
        except Exception as error:
            self.status.set(str(error))
            return
        self.password.set(''); self.confirm.set('')
        self.busy, self.failed = True, False
        self.status.set('正在启动房间…')
        self.start_button.configure(state='disabled')
        self.refresh_button.configure(state='disabled')
        self.combo.configure(state='disabled')
        self.port_input.configure(state='disabled')
        self.stop_button.configure(state='normal')

    def invalidate_url(self):
        self.url = ''
        self.address.set('尚未启动')
        self.copy_button.configure(state='disabled')
        self.browser_button.configure(state='disabled')

    def stop(self):
        self.service.stop()
        self.invalidate_url()
        self.stop_button.configure(state='disabled')
        self.status.set('正在停止房间，请稍候…')

    def copy(self):
        if self.url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.url)
            self.status.set('玩家地址已复制。请保持启动窗口和 KP 网页在线。')

    def open_kp(self):
        if self.url:
            webbrowser.open(self.url+'sessions/kp/')

    def close(self):
        self.closing = True
        if self.busy or self.service.active:
            self.stop()
        else:
            self.root.destroy()

    def tick(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'adapters':
                self.scanning = False
                self.adapters = payload
                old = self.network.get()
                labels = [a.label for a in payload]
                self.combo.configure(values=labels)
                chosen = next((a.label for a in payload if a.address == self.preferred), labels[0] if labels else '')
                self.network.set(old if old in labels else chosen)
                self.refresh_button.configure(state='normal')
                self.start_button.configure(state='normal' if labels else 'disabled')
                self.status.set('已识别网卡，请确认选择后启动。' if labels else '未找到局域网 IPv4。请连接 Wi-Fi 或网线后点击“刷新网卡”。')
            elif kind == 'status':
                if not self.closing:
                    self.status.set(payload)
            elif kind == 'running':
                if self.closing or self.service.cancel.is_set():
                    continue
                self.url = payload
                self.address.set(payload)
                self.copy_button.configure(state='normal')
                self.browser_button.configure(state='normal')
                self.setup_visibility()
                self.status.set('局域网已启动。将下方地址发给玩家，并在网页登录 KP。')
                if self.open_browser:
                    self.open_kp()
            elif kind == 'error':
                self.failed = True
                self.status.set('启动失败：'+payload)
            elif kind == 'stopped':
                self.busy = False
                self.invalidate_url()
                self.start_button.configure(state='normal' if self.adapters else 'disabled')
                self.refresh_button.configure(state='normal')
                self.combo.configure(state='readonly')
                self.port_input.configure(state='normal')
                self.stop_button.configure(state='disabled')
                self.setup_visibility()
                if not self.failed:
                    self.status.set('房间已停止，存档保留。')
        if self.closing and not self.service.active:
            self.root.destroy()
            return
        self.root.after(100, self.tick)


def main():
    parser = argparse.ArgumentParser(description='树桩镇局域网启动窗口')
    parser.add_argument('--data-dir', type=Path, default=PACK/'runtime')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    root = tk.Tk()
    try:
        LanWindow(root, args.data_dir, not args.no_browser)
        root.mainloop()
    except Exception as error:
        messagebox.showerror('树桩镇启动失败', str(error), parent=root)
        root.destroy()


if __name__ == '__main__':
    main()
