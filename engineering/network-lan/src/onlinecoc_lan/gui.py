import queue
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from .gateway import Config, Gateway, local_ip


class LanPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.gateway = None
        self.busy = False
        self.stop_requested = False
        self.events = queue.Queue()
        self.upstream = tk.StringVar(value='http://127.0.0.1:8765')
        addresses = ['127.0.0.1']
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            try:
                address = local_ip(info[4][0])
                if address not in addresses:
                    addresses.append(address)
            except ValueError:
                pass
        self.bind = tk.StringVar(value=next((a for a in addresses if not a.startswith('127.')), addresses[0]))
        self.port = tk.StringVar(value='8877')
        self.trusted = tk.BooleanVar()
        self.status = tk.StringVar(value='未启动；仅选择明确的本机网卡 IP')
        self.url = tk.StringVar()
        ttk.Label(self, text='局域网联机网关', font=('', 16)).grid(row=0, column=0, columnspan=2, sticky='w', pady=12)
        for row, (label, var) in enumerate((('真实宿主地址', self.upstream), ('监听网卡 IPv4', self.bind), ('共享端口', self.port)), 1):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky='w', padx=6, pady=8)
            widget = ttk.Combobox(self, textvariable=var, values=addresses) if var is self.bind else ttk.Entry(self, textvariable=var)
            widget.grid(row=row, column=1, sticky='ew', padx=6)
        ttk.Checkbutton(self, text='仅用于可信局域网（HTTP 不加密）；允许局域网成员使用宿主账号连接', variable=self.trusted).grid(row=4, column=0, columnspan=2, sticky='w', pady=12)
        buttons = ttk.Frame(self)
        buttons.grid(row=5, column=0, columnspan=2, sticky='w')
        self.start_button = ttk.Button(buttons, text='启动局域网', command=self.start)
        self.start_button.pack(side='left', padx=5)
        ttk.Button(buttons, text='停止局域网', command=self.stop).pack(side='left', padx=5)
        ttk.Button(buttons, text='复制连接地址', command=self.copy).pack(side='left', padx=5)
        ttk.Entry(self, textvariable=self.url, state='readonly').grid(row=6, column=0, columnspan=2, sticky='ew', pady=12)
        ttk.Label(self, textvariable=self.status, wraplength=850).grid(row=7, column=0, columnspan=2, sticky='w', pady=12)
        ttk.Label(self, text='先启动房间宿主。其他电脑可用上面的共享地址打开通用操作台，或在 Python 管理器中以 KP 登录。\n'
                            '停止网关只断开远程连接，不停止宿主、不更改存档。防火墙需由系统操作者允许所选端口。\n'
                            '本版不提供公网穿透、UDP 自动发现或配置包网页代理。', wraplength=900).grid(row=8, column=0, columnspan=2, sticky='w', pady=12)
        self.columnconfigure(1, weight=1)
        self.after(300, self.tick)

    def start(self):
        if self.busy or (self.gateway and self.gateway.running):
            return
        try:
            config = Config(self.upstream.get().strip(), self.bind.get().strip(), int(self.port.get())).validate()
            if not config.bind.startswith('127.') and not self.trusted.get():
                raise ValueError('请先确认这是可信局域网')
            self.gateway = Gateway(config)
        except Exception as exc:
            self.status.set(str(exc))
            return
        self.busy = True
        self.status.set('正在连接上游并监听…')
        self._run(self.gateway.start)

    def _run(self, action):
        def work():
            try:
                action()
                self.events.put(None)
            except Exception as exc:
                self.events.put(str(exc))
        threading.Thread(target=work, daemon=True).start()

    def stop(self):
        if self.gateway and self.busy:
            self.stop_requested = True
            return
        if self.gateway and not self.busy:
            self.busy = True
            self._run(self.gateway.stop)

    def copy(self):
        if self.url.get():
            self.clipboard_clear()
            self.clipboard_append(self.url.get())

    def tick(self):
        try:
            while True:
                error = self.events.get_nowait()
                self.busy = False
                if error:
                    self.status.set('启动/停止失败：' + error)
                elif self.gateway and not self.gateway.running:
                    self.status.set('已停止；宿主继续运行')
        except queue.Empty:
            pass
        if self.stop_requested and not self.busy:
            self.stop_requested = False
            self.stop()
        if self.gateway and self.gateway.running:
            self.url.set(self.gateway.config.url)
            self.status.set(f'运行中 · 实时连接 {self.gateway.connections} · HTTP 请求 {self.gateway.requests}')
        else:
            self.url.set('')
        self.start_button.configure(state='disabled' if self.busy or (self.gateway and self.gateway.running) else 'normal')
        self.after(300, self.tick)

    def shutdown(self):
        if self.gateway:
            self.gateway.stop()


def main():
    root = tk.Tk()
    root.title('OnlineCOC 局域网联机')
    root.geometry('940x500')
    panel = LanPanel(root)
    panel.pack(fill='both', expand=True)
    def close():
        panel.shutdown()
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', close)
    root.mainloop()
