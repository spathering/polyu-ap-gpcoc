import copy
import json
import queue
import threading
import time
import tkinter as tk
import urllib.parse
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from .protocol import Client, APIError, validate
from .state import Observer, pointer
from onlinecoc_lan.gui import LanPanel

OPS = ('entity.create', 'entity.patch', 'entity.update', 'entity.archive', 'configuration.put', 'configuration.remove',
       'relation.set', 'relation.remove', 'progress.set', 'member.update', 'room.status', 'rule.stage', 'rule.activate',
       'flow.respond', 'flow.cancel', 'flow.retry', 'asset.attach', 'asset.remove')
CATEGORIES = ('概览', 'entities', 'configurations', 'relations', 'progress', 'members', 'assets', 'flows', 'waits',
              'artifacts', '观察到的变化', '关注', '宿主最近审计', '命令记录')
READONLY = ('观察到的变化', '关注', '宿主最近审计', '命令记录')
LABELS = {'id': '对象 ID', 'name': '名称', 'numbers': '数值表', 'tags': '标签', 'owner': '所有者', 'visibility': '可见性',
          'rules': '规则绑定', 'configurationId': '配置 ID', 'revision': '修订', 'typeRef': '类型', 'defaults': '默认数值',
          'behaviors': '默认行为', 'sourceId': '来源 ID', 'targetId': '目标 ID', 'relationType': '关系类型', 'metadata': '元数据',
          'ownerKind': '归属类型', 'ownerId': '归属 ID', 'eventKey': '事件键', 'value': '进度值', 'status': '状态',
          'accountId': '账号 ID', 'active': '启用', 'role': '角色', 'sources': 'Lua 文件组', 'data': '数据文件组',
          'waitId': '等待 ID', 'answer': '回答：是', 'flowId': '流程 ID', 'entityId': '实体 ID', 'assetId': '素材 ID'}


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


class Manager(ttk.Frame):
    def __init__(self, root, settings):
        super().__init__(root)
        self.root, self.settings = root, settings
        self.client = None
        self.view, self.admin = {}, {}
        self.observer = Observer()
        self.generation = 0
        self.segment = -1
        self.busy = self.polling = False
        self.unknown = False
        self.last_envelope = None
        self.next_poll = 0
        self.poll_delay = 2
        self.events = queue.Queue(maxsize=16)
        self.selected = None
        self.selected_key = ''
        self.baseline = self.baseline_view = None
        self.fields = {}
        self.structured = {}
        self.rows = []
        self.page = 0
        self.address = tk.StringVar(value='http://127.0.0.1:8765')
        self.account = tk.StringVar(value='kp')
        self.password = tk.StringVar()
        self.status = tk.StringVar(value='未连接')
        self.category = tk.StringVar(value='概览')
        self.operation = tk.StringVar(value='entity.create')
        self.search = tk.StringVar()
        self.receipt = tk.StringVar()
        self.watch_path = tk.StringVar()
        self.only_watched = tk.BooleanVar()
        self.count = tk.StringVar()
        root.title('OnlineCOC 房间管理器 0.2.0 · Python')
        root.geometry('1280x850')
        root.minsize(1000, 700)
        self.pack(fill='both', expand=True)
        tabs = ttk.Notebook(self)
        tabs.pack(fill='both', expand=True)
        manage = ttk.Frame(tabs)
        tabs.add(manage, text='房间管理')
        self.lan = LanPanel(tabs)
        tabs.add(self.lan, text='局域网联机')
        top = ttk.Frame(manage, padding=6)
        top.pack(fill='x')
        for label, var, width in (('宿主/网关', self.address, 31), ('账号', self.account, 12), ('密码', self.password, 15)):
            ttk.Label(top, text=label).pack(side='left', padx=3)
            ttk.Entry(top, textvariable=var, width=width, show='*' if var is self.password else '').pack(side='left')
        self.connect_button = ttk.Button(top, text='连接', command=self.connect)
        self.connect_button.pack(side='left', padx=6)
        ttk.Label(manage, textvariable=self.status).pack(fill='x', padx=8)
        self.log = tk.Text(manage, height=6, state='disabled', wrap='word')
        self.log.pack(side='bottom', fill='x', padx=6, pady=6)
        panes = ttk.Panedwindow(manage, orient='horizontal')
        panes.pack(fill='both', expand=True, padx=6)
        left, right = ttk.Frame(panes, width=300), ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)
        category = ttk.Combobox(left, textvariable=self.category, values=CATEGORIES, state='readonly')
        category.pack(fill='x')
        category.bind('<<ComboboxSelected>>', lambda e: self.change_category())
        ttk.Entry(left, textvariable=self.search).pack(fill='x', pady=5)
        self.search.trace_add('write', lambda *_: self.render())
        ttk.Checkbutton(left, text='仅关注的变化', variable=self.only_watched, command=self.render).pack(anchor='w')
        pages = ttk.Frame(left)
        pages.pack(fill='x')
        ttk.Button(pages, text='上一页', command=lambda: self.move_page(-1)).pack(side='left')
        ttk.Button(pages, text='下一页', command=lambda: self.move_page(1)).pack(side='left')
        ttk.Label(left, textvariable=self.count).pack(anchor='w')
        treebox = ttk.Frame(left)
        treebox.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(treebox, show='tree', selectmode='browse')
        scrollbar = ttk.Scrollbar(treebox, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        detail_box = ttk.Frame(right)
        detail_box.pack(fill='both', expand=True)
        self.detail = tk.Text(detail_box, height=12, wrap='none', state='disabled')
        ys = ttk.Scrollbar(detail_box, command=self.detail.yview)
        xs = ttk.Scrollbar(detail_box, orient='horizontal', command=self.detail.xview)
        self.detail.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        xs.pack(side='bottom', fill='x')
        ys.pack(side='right', fill='y')
        self.detail.pack(fill='both', expand=True)
        actions = ttk.Frame(right)
        actions.pack(fill='x', pady=4)
        for i, (label, command) in enumerate((('上传素材', self.upload), ('下载素材', self.download), ('创建备份', self.backup),
                                            ('导入完整规则组', self.import_rules), ('查看规则源', self.artifact))):
            ttk.Button(actions, text=label, command=command).grid(row=0, column=i, padx=2)
        receipts = ttk.Frame(right)
        receipts.pack(fill='x')
        ttk.Label(receipts, text='回执 ID').pack(side='left')
        ttk.Entry(receipts, textvariable=self.receipt, width=33).pack(side='left')
        ttk.Button(receipts, text='查询回执', command=self.query_receipt).pack(side='left')
        ttk.Button(receipts, text='原封套重发', command=self.resend).pack(side='left')
        watches = ttk.Frame(right)
        watches.pack(fill='x', pady=4)
        ttk.Label(watches, text='字段路径').pack(side='left')
        ttk.Entry(watches, textvariable=self.watch_path, width=22).pack(side='left')
        for text, action in (('关注对象/字段', self.add_watch), ('启用/禁用', self.toggle_watch), ('删除关注', self.delete_watch)):
            ttk.Button(watches, text=text, command=action).pack(side='left')
        toolbar = ttk.Frame(right)
        toolbar.pack(fill='x', pady=6)
        self.op_box = ttk.Combobox(toolbar, textvariable=self.operation, values=OPS, state='readonly', width=23)
        self.op_box.pack(side='left')
        self.op_box.bind('<<ComboboxSelected>>', lambda e: self.build_fields())
        self.submit_button = ttk.Button(toolbar, text='提交表单', command=self.submit, state='disabled')
        self.submit_button.pack(side='left')
        ttk.Button(toolbar, text='重建编辑基线', command=self.rebase).pack(side='left')
        ttk.Button(toolbar, text='比较最新值', command=self.compare).pack(side='left')
        formbox = ttk.Frame(right)
        formbox.pack(fill='both', expand=True)
        canvas = tk.Canvas(formbox, height=220, highlightthickness=0)
        bar = ttk.Scrollbar(formbox, command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)
        self.form = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.form, anchor='nw')
        self.form.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        self.after(200, self.tick)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def say(self, value):
        self.log.configure(state='normal')
        self.log.insert('end', time.strftime('%H:%M:%S ') + str(value) + '\n')
        if int(self.log.index('end-1c').split('.')[0]) > 250:
            self.log.delete('1.0', '100.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def show(self, value):
        self.detail.configure(state='normal')
        self.detail.delete('1.0', 'end')
        self.detail.insert('1.0', pretty(value))
        self.detail.configure(state='disabled')

    def job(self, action, success, poll=False):
        if (self.polling if poll else self.busy):
            return False
        if poll:
            self.polling = True
        else:
            self.busy = True
        generation = self.generation
        def work():
            try:
                result, error = action(), None
            except Exception as exc:
                result, error = None, exc
            self.events.put((generation, poll, success, result, error))
        threading.Thread(target=work, daemon=True).start()
        return True

    def connect(self):
        if self.client:
            self.disconnect()
            return
        if self.busy:
            return
        try:
            client = Client(self.address.get())
            account, password = self.account.get(), self.password.get()
            self.client = client
            self.password.set('')
            def login():
                try:
                    client.login(account, password)
                except Exception:
                    client.close()
                    raise
            self.job(login, lambda _: self.say('已登录；等待完整实时快照'))
            self.connect_button.configure(text='断开')
        except Exception as exc:
            self.say(exc)

    def disconnect(self):
        self.generation += 1
        old, self.client = self.client, None
        if old:
            old.close()
        self.view, self.admin = {}, {}
        self.selected = self.baseline = self.baseline_view = self.last_envelope = None
        self.unknown = False
        self.busy = self.polling = False
        self.segment = -1
        self.observer.reset()
        self.fields.clear()
        for widget in self.form.winfo_children():
            widget.destroy()
        self.tree.delete(*self.tree.get_children())
        self.show(None)
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self.receipt.set('')
        self.connect_button.configure(text='连接')
        self.status.set('未连接')

    def context(self):
        return {'endpoint': self.client.address if self.client else '', **{k: self.view.get(k) for k in ('accountId', 'roomId', 'runId')}}

    def matches(self, item):
        return all(item.get(k) == v for k, v in self.context().items())

    def data(self, category=None):
        cat = category or self.category.get()
        if cat == '概览':
            return {k: v for k, v in self.view.items() if k not in ('entities', 'relations', 'progress', 'waits', 'flows')} | {'运行信息': self.admin.get('runtime'), '存储信息': self.admin.get('store')}
        if cat == '观察到的变化':
            result = []
            for row, _ in self.observer.records:
                row = dict(row)
                row['关注命中'] = any(self.matches(w) and w.get('enabled') and
                    (row['path'] == w['path'] or row['path'].startswith(w['path'] + '/') or w['path'].startswith(row['path'] + '/'))
                    for w in self.settings.data['watches'])
                if not self.only_watched.get() or row['关注命中']:
                    result.append(row)
            return result
        if cat in ('关注', '命令记录'):
            return [x for x in self.settings.data['watches' if cat == '关注' else 'commands'] if self.matches(x)]
        if cat == '宿主最近审计':
            return self.admin.get('audit', [])
        return self.admin.get(cat, self.view.get(cat, {}))

    @staticmethod
    def pairs(data):
        return list(data.items()) if isinstance(data, dict) else [(str(i), v) for i, v in enumerate(data)] if isinstance(data, list) else []

    def change_category(self):
        self.page = 0
        self.selected = None
        self.render()
        self.build_fields()

    def move_page(self, amount):
        self.page = max(0, self.page + amount)
        self.render()

    def render(self):
        query = self.search.get().casefold()
        rows = [(k, v) for k, v in self.pairs(self.data()) if query in (str(k) + pretty(v)).casefold()]
        self.page = min(self.page, max(0, (len(rows) - 1) // 500))
        self.rows = rows[self.page * 500:(self.page + 1) * 500]
        self.tree.delete(*self.tree.get_children())
        for i, (key, value) in enumerate(self.rows):
            label = value.get('name', value.get('path', value.get('op', ''))) if isinstance(value, dict) else str(value)
            self.tree.insert('', 'end', iid=str(i), text=f'{key}  {label}')
        self.count.set(f'{len(rows)} 项 · 本地页 {self.page+1} · 淘汰 {self.observer.dropped}')

    def select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_key, self.selected = self.rows[int(selection[0])]
        self.show(self.selected)
        if self.category.get() == '命令记录':
            self.receipt.set(self.selected['commandId'])
        self.build_fields()

    def build_fields(self):
        for widget in self.form.winfo_children():
            widget.destroy()
        self.fields = {}
        self.structured = {}
        self.baseline = copy.deepcopy(self.selected)
        self.baseline_view = copy.deepcopy(self.view)
        self.baseline_category = self.category.get()
        if not self.client or not hasattr(self.client, 'contracts') or self.category.get() in READONLY:
            ttk.Label(self.form, text='此类别只读。请先连接并选择房间对象类别。').grid()
            return
        schema = self.client.contracts['operations'][self.operation.get()]
        ttk.Label(self.form, text='实体使用开始编辑时的版本；其余操作无原子版本保护。').grid(row=0, column=0, columnspan=3, sticky='w')
        selected = self.selected if isinstance(self.selected, dict) else {}
        for row, (key, prop) in enumerate(schema['properties'].items(), 1):
            required = key in schema.get('required', [])
            include = tk.BooleanVar(value=required)
            ttk.Checkbutton(self.form, text=LABELS.get(key, key) + (' *' if required else ''), variable=include,
                            state='disabled' if required else 'normal').grid(row=row, column=0, sticky='w', padx=6, pady=4)
            value = selected.get(key)
            if value is None and key in ('id', 'entityId', 'assetId', 'waitId', 'flowId'):
                value = self.selected_key if self.selected is not None else ''
            if prop.get('type') == 'boolean':
                var = tk.BooleanVar(value=bool(value))
                editor = ttk.Checkbutton(self.form, variable=var)
            else:
                structured = prop.get('type') in ('object', 'array', 'integer', 'number') or key == 'value'
                default = {} if prop.get('type') == 'object' else [] if prop.get('type') == 'array' else ''
                text = pretty(value if value is not None else default) if structured else str(value if value is not None else '')
                if key == 'owner' and value is None:
                    text = 'null'
                var = tk.StringVar(value=text)
                if 'enum' in prop:
                    var.set(value if value in prop['enum'] else prop['enum'][0])
                    editor = ttk.Combobox(self.form, textvariable=var, values=prop['enum'], state='readonly', width=55)
                elif structured:
                    editor = tk.Text(self.form, width=58, height=3, wrap='word')
                    editor.insert('1.0', text)
                    self.structured[key] = editor
                    def changed(*_, variable=var, widget=editor):
                        widget.delete('1.0', 'end')
                        widget.insert('1.0', variable.get())
                    var.trace_add('write', changed)
                else:
                    editor = ttk.Entry(self.form, textvariable=var, width=58)
            editor.grid(row=row, column=1, sticky='ew', pady=4)
            self.fields[key] = (include, var, prop)

    def arguments(self):
        args = {}
        for key, (include, var, prop) in self.fields.items():
            if not include.get():
                continue
            value = self.structured[key].get('1.0', 'end-1c') if key in self.structured else var.get()
            if prop.get('type') in ('object', 'array', 'integer', 'number') or key == 'value' or (key == 'owner' and value == 'null'):
                value = json.loads(value)
            args[key] = value
        validate(self.client.contracts['operations'][self.operation.get()], args)
        return args

    def rebase(self):
        self.selected = dict(self.pairs(self.data())).get(self.selected_key)
        self.build_fields()

    def compare(self):
        try:
            self.show({'开始编辑时': self.baseline, '当前样本': dict(self.pairs(self.data(self.baseline_category))).get(self.selected_key), '草稿': self.arguments()})
        except Exception as exc:
            self.say(exc)

    def submit(self):
        if not self.client or not self.client.connected or self.busy or self.category.get() in READONLY:
            return
        if self.unknown:
            self.say('上一命令结果未知，请先查询回执或原封套重发。')
            return
        try:
            args, op = self.arguments(), self.operation.get()
            tokens = {}
            if (op.startswith('entity.') and op != 'entity.create') or op == 'asset.attach':
                key = args.get('id', args.get('entityId'))
                entity = self.baseline_view.get('entities', {}).get(key)
                if not entity:
                    raise APIError('请选中实体并重建编辑基线')
                tokens[key] = entity['viewToken']
            if op.endswith('remove') or op in ('entity.archive', 'rule.activate', 'member.update', 'room.status', 'flow.retry'):
                if not messagebox.askokcancel('确认提交', op + '\n' + pretty(args) + ('\n重试是新尝试，可能重新掷骰。' if op == 'flow.retry' else '')):
                    return
            envelope = self.client.envelope(op, args, tokens)
            client, baseline, category, key = self.client, copy.deepcopy(self.baseline), self.baseline_category, self.selected_key
            def preflight():
                if not tokens and baseline is not None and category not in ('概览', 'artifacts'):
                    admin, view = client.admin(), client.request('view')
                    fresh = dict(self.pairs(admin.get(category, view.get(category, {})))).get(key)
                    if fresh != baseline:
                        raise APIError('选中数据已变化；草稿保留，请比较后重新建立基线', 409)
                return True
            self.job(preflight, lambda _: self.execute(envelope))
        except Exception as exc:
            self.say(exc)

    def execute(self, envelope):
        client = self.client
        self.last_envelope = copy.deepcopy(envelope)
        self.settings.remember(self.context(), envelope)
        self.receipt.set(envelope['payload']['commandId'])
        self.unknown = True
        def done(result):
            self.unknown = result.get('status') not in ('committed', 'rejected')
            self.say(pretty(result))
            self.next_poll = 0
        def send():
            try:
                return client.request('commands', envelope)
            except APIError as exc:
                exc.command_rejected = bool(exc.status)
                raise
        self.job(send, done)

    def query_receipt(self):
        if not self.client or not self.receipt.get().strip():
            self.say('请填写 commandId')
            return
        client, command = self.client, self.receipt.get().strip()
        def done(result):
            if self.last_envelope and command == self.last_envelope['payload']['commandId']:
                self.unknown = result.get('status') not in ('committed', 'rejected')
            self.say(pretty(result))
        self.job(lambda: client.request('receipts/' + urllib.parse.quote(command, safe='')), done)

    def resend(self):
        if self.last_envelope and self.client and self.client.connected and not self.busy and messagebox.askokcancel('原封套重发', '沿用相同 commandId 和参数重发？'):
            self.execute(self.last_envelope)

    def import_rules(self):
        if not self.client:
            return
        paths = filedialog.askopenfilenames(filetypes=[('规则文件', '*.lua *.json')])
        if not paths:
            return
        try:
            sources, data = {}, {}
            for path in map(Path, paths):
                target = sources if path.suffix.lower() == '.lua' else data
                if path.name in target:
                    raise ValueError('同名文件：' + path.name)
                target[path.name] = path.read_text('utf-8-sig') if target is sources else json.loads(path.read_text('utf-8-sig'))
            if not sources:
                raise ValueError('完整规则组至少需要一个 Lua 文件')
            self.category.set('artifacts')
            self.operation.set('rule.stage')
            self.build_fields()
            for key, value in (('sources', sources), ('data', data)):
                self.fields[key][0].set(True)
                self.fields[key][1].set(json.dumps(value, ensure_ascii=False))
            self.say('规则已导入草稿，提交暂存后再明确激活。')
        except Exception as exc:
            self.say(exc)

    def artifact(self):
        if self.client and isinstance(self.selected, str):
            client, revision = self.client, self.selected
            self.job(lambda: client.request('admin/artifacts/' + urllib.parse.quote(revision, safe='')), self.show)

    def backup(self):
        if self.client and self.client.connected:
            client = self.client
            self.job(lambda: client.request('backup', {}), lambda r: self.say('宿主已创建备份（不含身份库）：' + pretty(r)))

    def upload(self):
        if not self.client or not self.client.connected or self.busy:
            return
        path = filedialog.askopenfilename()
        if not path:
            return
        if Path(path).stat().st_size > 10 * 1024 * 1024:
            self.say('素材超过 10 MiB')
            return
        public = messagebox.askyesnocancel('素材可见性', '所有成员可见？否表示仅 KP；取消则不上传。')
        if public is None:
            return
        client = self.client
        self.job(lambda: client.request('assets', raw=Path(path).read_bytes(), headers={'x-asset-name': urllib.parse.quote(Path(path).name), 'x-asset-visibility': 'public' if public else 'kp'}), lambda r: self.say(pretty(r)))

    def download(self):
        if self.client and self.category.get() == 'assets' and self.selected:
            path = filedialog.asksaveasfilename(initialfile=urllib.parse.unquote(self.selected.get('name', 'asset.bin')).replace('/', '_').replace('\\', '_'))
            if path:
                client, key = self.client, self.selected_key
                self.job(lambda: client.request('assets/' + urllib.parse.quote(key, safe=''), binary=True), lambda data: (Path(path).write_bytes(data), self.say('下载完成')))

    def add_watch(self):
        if self.selected is None or self.category.get() in READONLY or not self.client:
            return
        if len(self.settings.data['watches']) >= 100:
            self.say('关注上限 100 项')
            return
        suffix = self.watch_path.get().strip()
        if suffix and not suffix.startswith('/'):
            self.say('字段路径应如 /numbers/hp，留空关注整个对象')
            return
        self.settings.data['watches'].append({**self.context(), 'path': '/' + pointer(self.category.get()) + '/' + pointer(self.selected_key) + suffix, 'enabled': True})
        self.settings.save()
        self.say('关注已保存，不保存观察值。')

    def toggle_watch(self):
        if self.category.get() == '关注' and self.selected:
            self.selected['enabled'] = not self.selected['enabled']
            self.settings.save()
            self.render()

    def delete_watch(self):
        if self.category.get() == '关注' and self.selected:
            self.settings.data['watches'].remove(self.selected)
            self.selected = None
            self.settings.save()
            self.render()

    def tick(self):
        try:
            while True:
                generation, poll, callback, result, error = self.events.get_nowait()
                if generation != self.generation:
                    continue
                if poll:
                    self.polling = False
                else:
                    self.busy = False
                if error:
                    if poll:
                        self.next_poll = time.monotonic() + self.poll_delay
                        self.poll_delay = min(16, self.poll_delay * 2)
                    if isinstance(error, APIError) and error.status in (401, 403):
                        self.disconnect()
                    elif self.client and self.client.stop.is_set():
                        self.disconnect()
                    elif getattr(error, 'command_rejected', False):
                        self.unknown = False
                    self.say(str(error) + ('；写请求失败时可能结果未知，请查询回执，上传/备份不要自动重复。' if not poll else ''))
                else:
                    try:
                        callback(result)
                    except Exception as exc:
                        self.say(exc)
        except queue.Empty:
            pass
        client = self.client
        if client:
            view, segment, error, received = client.snapshot()
            if client.fatal:
                self.disconnect()
                self.say('权限改变，已清理数据；请重新登录。')
            elif view:
                if segment != self.segment:
                    self.segment = segment
                    self.observer.reset()
                    self.admin = {}
                    self.selected = self.baseline = self.last_envelope = None
                    self.unknown = False
                    self.next_poll = 0
                    self.view = view
                    self.build_fields()
                    self.say('新观察段；断线期间的变化无法补齐。')
                if view != self.view:
                    self.observer.sample('view', view)
                    self.view = view
                    self.render()
                else:
                    self.observer.sample('view', view)
                self.status.set('已连接 · 实时样本 ' + time.strftime('%H:%M:%S', time.localtime(received)) + ' · 管理数据 ' + getattr(self, 'admin_time', '等待中'))
                if not self.polling and time.monotonic() >= self.next_poll:
                    self.next_poll = time.monotonic() + 2
                    def got_admin(data):
                        self.admin = data
                        self.admin_time = time.strftime('%H:%M:%S')
                        self.poll_delay = 2
                        self.observer.sample('admin', data)
                        self.render()
                    self.job(client.admin, got_admin, poll=True)
            else:
                self.status.set('断线/等待快照：' + error)
        self.submit_button.configure(state='normal' if self.client and self.client.connected and not self.busy and self.category.get() not in READONLY else 'disabled')
        self.after(200, self.tick)

    def close(self):
        if (self.busy or self.unknown or (self.lan.gateway and self.lan.gateway.running)) and not messagebox.askokcancel('关闭工具', '仍有请求未明确完成或网关正在运行。关闭将停止本工具的网关，宿主继续运行。确认？'):
            return
        self.disconnect()
        self.lan.shutdown()
        self.root.destroy()
