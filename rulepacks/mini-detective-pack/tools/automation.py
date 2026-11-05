"""Pack-side, authenticated deterministic workflows over the public host API.

No engine privileges are given to a browser. A separate KP session executes a
closed action vocabulary; SQLite journals command envelopes before dispatch.
"""
import ctypes
import http.cookiejar
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.request
import uuid

from client import Client, HostError
from package import PACK
from scene import project_scene


class ActionError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ActionError(message)


def protect(data, decrypt=False):
    """Windows user-bound DPAPI. Never fall back to plaintext on other hosts."""
    if os.name != 'nt':
        raise OSError('DPAPI unavailable')
    class Blob(ctypes.Structure):
        _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buf = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    fn = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise OSError('DPAPI failed')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(target.data)


class Automation:
    def __init__(self, backend, directory):
        self.backend = backend
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.session_path = directory / 'automation-session.bin'
        self.db = sqlite3.connect(directory / 'automation.sqlite', check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, account TEXT, body TEXT, snapshot TEXT, result TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS steps (request TEXT, step INTEGER, envelope TEXT, result TEXT, PRIMARY KEY(request,step))')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, account TEXT, text TEXT, created REAL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS needs (id TEXT PRIMARY KEY, account TEXT, actor TEXT, title TEXT, text TEXT, state TEXT, reply TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS choices (id TEXT PRIMARY KEY, payload TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS knowledge (member TEXT PRIMARY KEY, value TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        self.db.commit()
        self.lock = threading.RLock()
        self.client = None
        try:
            cookie = protect(self.session_path.read_bytes(), True).decode()
            c = Client.__new__(Client)
            c.base, c.csrf = backend, None
            c.opener = urllib.request.build_opener()
            c.opener.addheaders = [('Cookie', cookie)]
            c.csrf = c.request('/me')['csrf']
            self.attach(c, save=False)
        except (OSError, ValueError, HostError):
            pass

    def attach(self, client, save=True):
        with self.lock:
            require(client.request('/view')['role'] == 'kp', '需要主持人会话')
            self.client = client
            if save:
                cookies = [h.cookiejar for h in client.opener.handlers if isinstance(h, urllib.request.HTTPCookieProcessor)]
                if cookies:
                    cookie = '; '.join(c.name + '=' + c.value for c in cookies[0])
                    try:
                        encrypted = protect(cookie.encode())
                        temporary = self.session_path.with_suffix('.tmp')
                        temporary.write_bytes(encrypted)
                        temporary.replace(self.session_path)
                    except OSError:
                        pass  # Memory-only operation remains available.

    def authority(self):
        require(self.client is not None, '自动处理尚未启用，请 KP 登录一次')
        try:
            view = self.client.request('/view')
        except HostError as exc:
            if exc.response.get('httpStatus') in (401, 403):
                self.client = None
                raise ActionError('自动处理会话已到期，请 KP 重新登录') from exc
            raise
        require(view['role'] == 'kp', '自动处理需要主持人会话')
        return view

    def enabled(self):
        row = self.db.execute('SELECT value FROM settings WHERE key="enabled"').fetchone()
        return bool(row and row[0] == 'true')

    def set_enabled(self, caller, enabled):
        with self.lock:
            require(caller['role'] == 'kp', '只有 KP 可以切换自动处理')
            require(type(enabled) is bool, '开关值必须为布尔值')
            require(not self.db.execute('SELECT 1 FROM requests WHERE result IS NULL').fetchone(), '请先恢复结果待确认的行动，再切换处理方式')
            if enabled:
                view = self.authority()
                artifact = self.client.request('/admin/artifacts/' + view['catalog']['rulesetRevision'])['artifact']
                scenario = artifact['data'].get('scenario.json', {})
                if 'automation' not in scenario:
                    # Upgrade only this known pack. Keep active scenario edits,
                    # sources, entities and inventory; add the missing defaults.
                    local = json.loads((PACK / 'config/scenario.json').read_text(encoding='utf-8'))
                    require(scenario.get('id') == local['id'] and all([x['id'] for x in scenario.get(k, [])] == [x['id'] for x in local[k]] for k in ('locations', 'items', 'puzzles')), '当前场景结构不兼容，请 KP 检查配置')
                    data = {**artifact['data'], 'scenario.json': {**scenario, 'automation': local['automation']}}
                    revision = self.client.command('rule.stage', {'sources': artifact['sources'], 'data': data})
                    self.client.command('rule.activate', {'revision': revision})
            changed = self.enabled() != enabled
            self.db.execute('INSERT OR REPLACE INTO settings VALUES ("enabled",?)', ('true' if enabled else 'false',))
            if changed:
                self.db.execute('INSERT INTO events VALUES (?,?,?,?)', ('switch:' + str(uuid.uuid4()), '*', 'KP 已' + ('开启自动处理。' if enabled else '关闭自动处理，后续行动交由 KP 裁定。'), time.time()))
            self.db.commit()
            return {'enabled': enabled, 'message': '自动处理已开启' if enabled else '自动处理已关闭，后续行动提交给 KP'}

    @staticmethod
    def entities(view, config):
        return [e for e in view['entities'].values() if e['configurationId'] == config and e['lifecycle'] == 'active']

    def known(self, view, member):
        row = self.db.execute('SELECT value FROM knowledge WHERE member=?', (member,)).fetchone()
        if row:
            return json.loads(row[0])
        # Legacy manual reveals can render in the browser, but cannot grant an
        # automated reward without a corresponding validated workflow.
        return {'locations': [], 'descriptions': {}, 'clues': [], 'puzzles': [], 'searched': [], 'loot': {}}

    def active_scenario(self, view):
        revision = view.get('catalog', {}).get('rulesetRevision')
        if self.client and revision:
            if getattr(self, '_scenario_revision', None) != revision:
                artifact = self.client.request('/admin/artifacts/' + revision)['artifact']
                self._scenario = artifact['data']['scenario.json']
                self._scenario_revision = revision
            return self._scenario
        return json.loads((PACK / 'config/scenario.json').read_text(encoding='utf-8'))

    def status(self, caller):
        with self.lock:
            account = caller['accountId']
            is_kp = caller['role'] == 'kp'
            logs = self.db.execute('SELECT account,text,created FROM events ' + ('' if is_kp else 'WHERE account=? OR account="*" ') + 'ORDER BY created DESC LIMIT 60', () if is_kp else (account,)).fetchall()
            needs = self.db.execute('SELECT id,account,actor,title,text,state,reply FROM needs ' + ('WHERE title NOT IN ("确认接收道具","选择防御") ' if is_kp else 'WHERE account=? ') + 'ORDER BY rowid DESC LIMIT 40', () if is_kp else (account,)).fetchall()
            # The host member ID is authoritative, including nonstandard account IDs.
            own_members = caller.get('_members', [])
            member = next((m['memberId'] for m in own_members if m['accountId'] == account), 'member-' + account)
            knowledge = self.known(caller, member)
            full = caller
            if self.client:
                try:
                    full = self.authority()
                except ActionError:
                    pass
            scenario = self.active_scenario(full)
            local = json.loads((PACK / 'config/scenario.json').read_text(encoding='utf-8'))
            # Older compatible packs need no reset to render scene affordances.
            scene_data = {**scenario, 'automation': scenario.get('automation', local['automation'])}
            discovered = set(knowledge.get('searched', []))
            availability = []
            for item in scenario['items']:
                route = scene_data['automation']['items'].get(item['id'])
                if route and route['location'] in discovered:
                    availability.append({'index': item['index'], 'name': item['name'], 'effect': item['effect'], 'location': route['location']})
            pending = self.db.execute('SELECT body FROM requests WHERE account=? AND result IS NULL LIMIT 1', (account,)).fetchone()
            party = []
            if self.client:
                party = [{'id': e['instanceId'], 'name': e['name']} for e in self.entities(full, 'md.character') if e['owner'] != 'kp' and e['numbers']['approved']]
            full['_members'] = own_members
            scenes = {}
            for character in self.entities(caller, 'md.character'):
                if not is_kp and character['owner'] != account:
                    continue
                owner_member = next((m['memberId'] for m in own_members if m['accountId'] == character['owner']), 'member-' + character['owner'])
                owner_known = self.known(full, owner_member)
                legacy = next((p['value'] for p in caller.get('progress', {}).values() if p['ownerId'] == owner_member and p['eventKey'] == 'md.known'), {})
                scene = project_scene(self, character, full, scene_data, owner_known, legacy)
                if scene:
                    scene['features'] = scene_data['automation'].get('scenes', local['automation'].get('scenes', {})).get(scene['location']['id'], {}).get('features', [])
                    scenes[character['instanceId']] = scene
            return {'ready': self.client is not None, 'enabled': self.enabled(), 'party': party, 'logs': [dict(zip(('account', 'text', 'created'), r)) for r in logs],
                    'needs': [dict(zip(('id', 'account', 'actor', 'title', 'text', 'state', 'reply'), r)) for r in needs],
                    'knowledge': knowledge, 'items': availability, 'scenes': scenes,
                    'puzzles': [{k: p[k] for k in ('id', 'name', 'prompt')} for p in scenario['puzzles'] if scene_data['automation']['puzzles'][p['id']]['location'] in discovered],
                    'pending': json.loads(pending[0]) if pending else None}

    def action(self, caller, body):
        with self.lock:
            require(isinstance(body, dict), '行动格式不正确')
            require(set(body) <= {'id', 'kind', 'actor', 'destination', 'item', 'answer', 'puzzle', 'text', 'target', 'choice'}, '包含不支持的行动字段')
            for field in ('id', 'kind', 'actor', 'answer', 'puzzle', 'text', 'target', 'choice'):
                require(field not in body or isinstance(body[field], str), '行动文字字段格式不正确')
            for field in ('destination',):
                require(field not in body or type(body[field]) is int, '行动数值字段格式不正确')
            require('item' not in body or type(body['item']) in (int, str), '道具字段格式不正确')
            try:
                ident = str(uuid.UUID(body.get('id', '')))
            except (ValueError, TypeError, AttributeError):
                raise ActionError('行动缺少有效编号')
            require(len(json.dumps(body, ensure_ascii=False)) <= 5000, '行动内容过长')
            account = caller['accountId']
            key = account + ':' + ident
            encoded = json.dumps(body, ensure_ascii=False, sort_keys=True)
            row = self.db.execute('SELECT account,body,snapshot,result FROM requests WHERE id=?', (key,)).fetchone()
            if row:
                require(row[0] == account and row[1] == encoded, '同一行动编号不能修改内容')
                if row[3]:
                    return json.loads(row[3])
                snapshot = json.loads(row[2])
                self.authority()
            else:
                require(not self.db.execute('SELECT 1 FROM requests WHERE result IS NULL').fetchone(), '有行动结果待恢复，请原提交者先恢复行动')
                if not self.enabled() and body.get('kind') not in ('ruling', 'respond', 'advance'):
                    return self.queue_manual(caller, body, key, encoded)
                view = self.authority()
                # Use active host data, so KP scenario edits apply to automation too.
                artifact = self.client.request('/admin/artifacts/' + view['catalog']['rulesetRevision'])['artifact']
                scenario = artifact['data']['scenario.json']
                require('automation' in scenario or body.get('kind') in ('advance', 'ruling', 'respond'), '请 KP 打开自动处理开关，以补齐当前配置')
                members = self.client.request('/chat/members')['items']
                snapshot = {'view': view, 'scenario': scenario, 'members': members, 'role': caller['role'], 'time': time.time(), 'knowledge': {m['memberId']: self.known(view, m['memberId']) for m in members}}
                if body.get('kind') in ('respond', 'ruling'):
                    snapshot['decision'] = self.db.execute('SELECT account,actor,state FROM needs WHERE id=?', (body.get('target'),)).fetchone()
                    choice = self.db.execute('SELECT payload FROM choices WHERE id=?', (body.get('target'),)).fetchone()
                    snapshot['choice'] = choice[0] if choice else None
                self.db.execute('INSERT INTO requests VALUES (?,?,?,?,NULL)', (key, account, encoded, json.dumps(snapshot, ensure_ascii=False)))
                self.db.commit()
            self.current, self.step = key, 0
            try:
                message = self.execute(account, body, snapshot)
                result = {'message': message}
            except ActionError as exc:
                result = {'message': str(exc), 'rejected': True}
            except HostError as exc:
                # Deterministic host rejection can be surfaced; uncertain transport
                # failures deliberately keep the workflow resumable.
                if exc.response.get('status') == 'rejected':
                    code = exc.response.get('code')
                    reason = {'MD_NOT_SOOTHING_LOCATION': '此处不能安抚，请前往音乐室、浴场或桑拿房', 'MD_NO_INTELLECT': '今日智力额度已用完', 'MD_NO_AMMO': '武器弹药已经耗尽', 'MD_NOT_WEAPON': '此道具不能作为武器装备', 'MD_SLOT_USED': '本轮主要行动已完成', 'MD_ITEM_NOT_USABLE': '道具尚未确认或已经耗尽'}.get(code, '操作未通过规则检查，请核对当前角色状态')
                    result = {'message': reason, 'rejected': True}
                else:
                    raise
            self.db.execute('UPDATE requests SET result=? WHERE id=?', (json.dumps(result, ensure_ascii=False), key))
            self.db.commit()
            return result

    def queue_manual(self, caller, body, key, encoded):
        names = {'move': '移动', 'explore': '探索', 'sleep': '休息', 'soothe': '安抚', 'wait': '等待', 'search': '追加侦察', 'check': '检定', 'puzzle': '解谜', 'take': '领取道具', 'equip': '装备', 'consume': '使用道具', 'discard': '丢弃', 'offer': '转交', 'attack': '攻击', 'finish': '结束遭遇', 'hint': '询问提示', 'start-boat': '启动船', 'stop-tracking': '停止追踪', 'open-maintenance': '开启维修通道', 'boat-key': '出示证据并承诺不再互杀', 'ending': '选择结局', 'special': '特殊行动'}
        require(body.get('kind') in names, '不支持此行动')
        actor = caller['entities'].get(body.get('actor'))
        require(actor and actor['configurationId'] == 'md.character' and actor['lifecycle'] == 'active', '角色不存在')
        require(actor['owner'] == caller['accountId'] or caller['role'] == 'kp', '只能操作自己的角色')
        scenario = json.loads((PACK / 'config/scenario.json').read_text(encoding='utf-8'))
        visible_entities = caller['entities']
        if 'target' in body and self.client:
            try:
                visible_entities = self.authority()['entities']
            except ActionError:
                pass
        lines = ['角色：' + actor['name'], '行动：' + names[body['kind']]]
        if 'destination' in body:
            destination = next((l['name'] for l in scenario['locations'] if l['index'] == body['destination']), '未指定有效地点')
            lines.append('目的地：' + destination)
        for field, label in [('item', '道具'), ('target', '对象'), ('puzzle', '机关'), ('answer', '回答'), ('choice', '选择'), ('text', '说明')]:
            if field in body:
                value = body[field]
                if field in ('item', 'target'):
                    entity = visible_entities.get(str(value))
                    definition = next((i for i in scenario['items'] if i['index'] == value), None) if field == 'item' else None
                    value = entity['name'] if entity else definition['name'] if definition else '已指定对象'
                if field == 'choice':
                    choices = {'1': '归航', '2': '携证归航', '3': '留守', '4': '前往神界', '5': '困岛续章', 'promise': '承诺不再互杀', 'accept': '接收', 'decline': '拒绝', 'counter': '对抗', 'dodge': '闪避'}
                    value = choices.get(value, value)
                lines.append(label + '：' + str(value))
        result = {'message': '自动处理已关闭，行动已提交给 KP。', 'queued': True}
        self.db.execute('INSERT INTO requests VALUES (?,?,?,?,?)', (key, caller['accountId'], encoded, '{}', json.dumps(result, ensure_ascii=False)))
        self.db.execute('INSERT INTO needs VALUES (?,?,?,?,?,"open","")', (key, actor['owner'], actor['instanceId'], '人工处理 · ' + names[body['kind']], '\n'.join(lines)))
        self.db.commit()
        return result

    def command(self, op, args):
        step = self.step
        self.step += 1
        row = self.db.execute('SELECT envelope,result FROM steps WHERE request=? AND step=?', (self.current, step)).fetchone()
        if row:
            envelope = json.loads(row[0])
            require(envelope['payload']['op'] == op and envelope['payload']['args'] == args, '恢复步骤发生变化，请联系 KP')
            if row[1] is not None:
                return json.loads(row[1])
        else:
            envelope = self.client.envelope(op, args)
            self.db.execute('INSERT INTO steps VALUES (?,?,?,NULL)', (self.current, step, json.dumps(envelope)))
            self.db.commit()
        receipt = self.client.request('/receipts/' + envelope['payload']['commandId'])
        if receipt['status'] == 'unknown':
            receipt = self.client.send(envelope)
        if receipt['status'] == 'pending':
            raise RuntimeError('Host command is still pending')
        if receipt['status'] != 'committed':
            raise HostError(receipt)
        result = receipt['result']
        self.db.execute('UPDATE steps SET result=? WHERE request=? AND step=?', (json.dumps(result), self.current, step))
        self.db.commit()
        return result

    def invoke(self, rule, **inputs):
        return self.command('action.invoke', {'actionId': rule, 'input': inputs})

    def log(self, account, text, suffix=''):
        self.db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?,?)', (self.current + suffix, account, text, time.time()))
        self.db.commit()

    def need(self, account, actor, title, text, suffix='', payload=None):
        self.db.execute('INSERT OR IGNORE INTO needs VALUES (?,?,?,?,?,"open","")', (self.current + suffix, account, actor, title, text))
        if payload:
            self.db.execute('INSERT OR IGNORE INTO choices VALUES (?,?)', (self.current + suffix, json.dumps(payload)))
        self.db.commit()
        return '已交给接收者确认。' if payload else '已提交给 KP，等待裁决。'

    def execute(self, account, body, snapshot):
        view, data = snapshot['view'], snapshot['scenario']
        kind = body.get('kind')
        if kind == 'advance':
            require(snapshot['role'] == 'kp', '只有 KP 可以推进轮次')
            worlds = self.entities(view, 'md.world')
            require(len(worlds) == 1, '需要唯一的世界时钟，请检查开局准备')
            world = worlds[0]
            require(not world['numbers']['closed'], '调查时钟已经结束')
            result = self.invoke('md.advance', actor=world['instanceId'])
            if not result['closed']:
                for character in self.entities(view, 'md.character'):
                    n = character['numbers']
                    if (n['day'], n['slot']) < (result['day'], result['slot']):
                        self.invoke('md.sync', actor=character['instanceId'], day=result['day'], slot=result['slot'])
            labels = data['slots']
            message = 'KP 已结束最终轮次，请玩家选择结局。' if result['closed'] else f"KP 已推进至第{result['day']}日 · {labels[result['slot']-1]}，角色轮次已同步。"
            self.log('*', message)
            return message
        if kind == 'respond':
            row = snapshot.get('decision')
            choice = snapshot.get('choice')
            require(row and choice and row[0] == account and row[2] == 'open', '没有可以处理的本人选择')
            payload = json.loads(choice)
            target = view['entities'].get(row[1])
            source = view['entities'].get(payload['source'])
            require(target and source and target['lifecycle'] == source['lifecycle'] == 'active', '参与角色已失效')
            require(target['numbers']['location'] == source['numbers']['location'], '双方已经离开同一地点')
            worlds = self.entities(view, 'md.world')
            require(len(worlds) == 1 and not worlds[0]['numbers']['closed'], '调查已经收束')
            if payload['kind'] == 'transfer':
                require(body.get('choice') in ('accept', 'decline'), '请选择接收或拒绝')
                if body['choice'] == 'accept':
                    item = next((i for i in self.held(view, source) if i['instanceId'] == payload['item']), None)
                    require(item and len(self.held(view, target)) < 4, '道具已失效或接收者卡槽已满')
                    if item['numbers']['equipped']:
                        self.command('entity.update', {'id': source['instanceId'], 'numbers': {'weapon': 0}})
                    self.command('entity.update', {'id': item['instanceId'], 'owner': target['owner'], 'numbers': {'equipped': 0}})
                    for relation in view['relations'].values():
                        if (relation['sourceId'] == item['instanceId'] and relation['relationType'] == 'source') or (relation['sourceId'] == source['instanceId'] and relation['targetId'] == item['instanceId'] and relation['relationType'] == 'references'):
                            self.command('relation.remove', {'id': relation['relationId']})
                    self.command('relation.set', {'sourceId': item['instanceId'], 'targetId': target['instanceId'], 'relationType': 'source'})
                    self.command('relation.set', {'sourceId': target['instanceId'], 'targetId': item['instanceId'], 'relationType': 'references'})
                message = '已接收道具。' if body['choice'] == 'accept' else '已拒绝此次转交。'
            else:
                require(body.get('choice') in ('counter', 'dodge'), '请选择对抗或闪避')
                require(target['numbers']['hp'] > 0 and source['numbers']['hp'] > 0, '倒下的角色不能攻击或防御')
                for entity in (source, target):
                    if not entity['numbers']['encounterActive']:
                        self.invoke('md.enter', actor=entity['instanceId'])
                roll = self.invoke('md.combat', attacker=source['instanceId'], defender=target['instanceId'], dodge=body['choice'] == 'dodge')
                message = f"攻击已结算：伤害 {roll['damage']}，防守方剩余 HP {roll['hp']}。"
            self.db.execute('UPDATE needs SET state="done",reply=? WHERE id=?', (message, body['target']))
            self.log(source['owner'], source['name'] + ' → ' + target['name'] + '：' + message, ':source')
            self.log(account, message)
            return message
        if kind == 'ruling':
            require(snapshot['role'] == 'kp', '只有 KP 可以处理裁决')
            row = snapshot.get('decision')
            require(row and row[2] == 'open', '裁决已处理或不存在')
            text = str(body.get('text', '')).strip()
            require(text, '请填写裁决反馈')
            self.db.execute('UPDATE needs SET state="done",reply=? WHERE id=?', (text[:2000], body['target']))
            self.log(row[0], 'KP 裁决：' + text[:2000])
            players = [p for p in self.entities(view, 'md.character') if p['owner'] != 'kp' and p['numbers']['hp'] > 0 and p['numbers']['approved'] and not p['numbers']['ending']]
            worlds = self.entities(view, 'md.world')
            if players and len(worlds) == 1 and not worlds[0]['numbers']['closed'] and all(p['numbers']['slotUsed'] for p in players):
                self.advance_if_ready(view, players[0], worlds[0])
            return '已记录裁决，接收者可在行动记录中查看。'
        actor = view['entities'].get(body.get('actor'))
        require(actor and actor['configurationId'] == 'md.character' and actor['lifecycle'] == 'active', '角色不存在')
        require(actor['owner'] == account or snapshot['role'] == 'kp', '只能操作自己的角色')
        owner, aid, n = actor['owner'], actor['instanceId'], actor['numbers']
        member = next((m['memberId'] for m in snapshot['members'] if m['accountId'] == owner), None)
        require(member, '角色没有对应玩家')
        worlds = self.entities(view, 'md.world')
        require(len(worlds) == 1, '需要唯一的世界时钟，请联系 KP')
        world, w = worlds[0], worlds[0]['numbers']
        require(not w['closed'] or kind == 'ending', '本场调查已收束')
        require(n['approved'] == 1 and n['hp'] > 0, '角色未批准或已倒下，请联系 KP')
        require((n['day'], n['slot']) <= (w['day'], w['slot']), '角色时钟超前，请联系 KP')
        if (n['day'], n['slot']) < (w['day'], w['slot']):
            self.invoke('md.sync', actor=aid, day=w['day'], slot=w['slot'])
            n = {**n, 'day': w['day'], 'slot': w['slot'], 'slotUsed': 0}
        loc = data['locations'][n['location'] - 1]
        knowledge = json.loads(json.dumps(snapshot['knowledge'].get(member, {})))
        for key, default in [('locations', []), ('descriptions', {}), ('clues', []), ('puzzles', []), ('searched', []), ('loot', {})]:
            knowledge.setdefault(key, default)
        items = self.held(view, actor)
        owned = {data['items'][i['numbers']['itemIndex'] - 1]['id'] for i in items}
        message = ''
        used = False
        if kind in ('move', 'explore', 'sleep', 'soothe', 'wait'):
            require(n['slotUsed'] == 0 and not n['encounterActive'], '本轮已行动或仍在遭遇中')
            require(not n['requestOpen'], '请先完成当前待掷骰检定')
            destination = body.get('destination', n['location'])
            require(isinstance(destination, int) and 1 <= destination <= len(data['locations']), '目的地无效')
            target = data['locations'][destination - 1]
            attempt_key = str(w['day']) + ':' + target['id']
            if kind == 'explore' and knowledge.get('attempts', {}).get(attempt_key, 0) >= 2:
                require(n['intellectRemaining'] > 0, '今日此地点基础侦察已用完，追加侦察需要1智力额度')
            if kind in ('move', 'explore'):
                require(target['id'] != 'loc-basement' or w['basementOpen'], '地下入口尚未开放')
                require(not ({loc['id'], target['id']} == {'loc-west', 'loc-shore'}) or w['cliffOpen'], '悬崖暗道尚未开放')
                direct = target['id'] == loc['id'] or target['id'] in loc['adjacentIds']
                indoor = kind == 'explore' and destination <= 13 and n['location'] <= 13 and 'loc-hall' in target['adjacentIds'] and 'loc-hall' in loc['adjacentIds']
                require(direct or indoor, '目的地不相邻，请先移动到入口')
            if kind == 'explore' and knowledge.get('attempts', {}).get(attempt_key, 0) >= 2:
                self.invoke('md.resolve', actor=aid, kind='hint', destination=n['location'])
            self.invoke('md.resolve', actor=aid, kind=kind, destination=destination)
            used = True
            if kind in ('move', 'explore'):
                loc = target
            reveals = [loc] + [l for l in data['locations'] if l['id'] in loc['adjacentIds'] and (l['id'] != 'loc-basement' or w['basementOpen'])]
            for reveal in reveals:
                if not any((x.get('index') if isinstance(x, dict) else x) == reveal['index'] for x in knowledge['locations']):
                    knowledge['locations'].append({k: reveal[k] for k in ('id', 'index', 'name')})
            knowledge['descriptions'][str(loc['index'])] = loc['description']
            labels = {'move': '移动到', 'explore': '探索了', 'sleep': '休息于', 'soothe': '安抚自己于', 'wait': '等待于'}
            message = labels[kind] + loc['name'] + '。'
            if kind == 'explore':
                if loc['id'] not in knowledge['searched']:
                    knowledge['searched'].append(loc['id'])
                clues = [c for c in data['clues'] if c['locationId'] == loc['id'] and (c['id'] != 'C7' or 'item-film' in owned)]
                for clue in clues:
                    if not any(c['id'] == clue['id'] for c in knowledge['clues']):
                        knowledge['clues'].append({k: clue[k] for k in ('id', 'text')})
                knowledge.setdefault('attempts', {})[attempt_key] = knowledge.get('attempts', {}).get(attempt_key, 0) + 1
                attribute = data['automation'].get('checks', {}).get(loc['id'], 3)
                self.invoke('md.request', actor=aid, attribute=attribute, talent=False)
                roll = self.invoke('md.check', actor=aid)
                message += '核心线索已记入卡册。' if clues else '已记录现场，可以查看物品与机关。'
                message += f"检定 {roll['die']} / {roll['target']}，" + ('成功。' if roll['passed'] else '未成功；核心线索仍保留。')
                if roll['passed']:
                    for itemid in data['automation'].get('exploreRewards', {}).get(loc['id'], []):
                        if itemid not in knowledge.setdefault('rewards', []):
                            knowledge['rewards'].append(itemid)
                if loc['id'] == 'loc-projector' and clues and not roll['passed']:
                    self.command('entity.update', {'id': aid, 'numbers': {'shock': 1}})
        elif kind == 'search':
            require(loc['id'] in knowledge['searched'] and not n['encounterActive'] and not n['requestOpen'], '请先探索此处并完成现有遭遇或检定')
            attempt_key = str(w['day']) + ':' + loc['id']
            count = knowledge.get('attempts', {}).get(attempt_key, 0)
            if count >= 2:
                self.invoke('md.resolve', actor=aid, kind='hint', destination=n['location'])
            self.invoke('md.request', actor=aid, attribute=data['automation'].get('checks', {}).get(loc['id'], 3), talent=False)
            roll = self.invoke('md.check', actor=aid)
            knowledge.setdefault('attempts', {})[attempt_key] = count + 1
            if roll['passed']:
                for itemid in data['automation'].get('exploreRewards', {}).get(loc['id'], []):
                    if itemid not in knowledge.setdefault('rewards', []):
                        knowledge['rewards'].append(itemid)
            message = f"追加侦察 {roll['die']} / {roll['target']}，" + ('成功。' if roll['passed'] else '未成功。') + ('消耗1智力额度。' if count >= 2 else '使用今日此地点的基础侦察次数。')
        elif kind == 'check':
            require(n['requestOpen'] == 1, '当前没有待完成的检定')
            roll = self.invoke('md.check', actor=aid)
            message = f"检定 {roll['die']} / {roll['target']}，" + ('成功。' if roll['passed'] else '未成功。')
        elif kind == 'puzzle':
            pid = body.get('puzzle')
            route = data['automation']['puzzles'].get(pid)
            require(route and route['location'] == loc['id'] and loc['id'] in knowledge['searched'], '请先探索机关所在地点')
            require(pid not in knowledge['puzzles'], '该机关已经解开')
            # P5 accepts a written code or its physical key.
            if pid == 'P5' and body.get('answer') == '使用档案钥匙' and 'item-record-key' in owned:
                body = {**body, 'answer': '0712'}
            answer = re.sub(r'[\s，、,。；;（）()·\-／/“”"：:]', '', str(body.get('answer', ''))).upper()
            if pid == 'P4' and answer not in route['answers']:
                return self.need(owner, aid, '画像问答的语义判断', str(body.get('answer', '')))
            require(answer in route['answers'], '机关没有打开，可以重新观察提示后再试')
            knowledge['puzzles'].append(pid)
            if route.get('reward'):
                knowledge.setdefault('rewards', []).append(route['reward'])
            if route.get('flag'):
                self.command('entity.update', {'id': world['instanceId'], 'numbers': {route['flag']: 1}})
            for cid in route.get('clues', []):
                clue = next(c for c in data['clues'] if c['id'] == cid)
                if not any(c['id'] == cid for c in knowledge['clues']):
                    knowledge['clues'].append({k: clue[k] for k in ('id', 'text')})
            message = '机关已解开，线索和领取资格已更新。'
        elif kind == 'take':
            require(loc['id'] in knowledge['searched'], '请先探索当前地点')
            definition = next((i for i in data['items'] if i['index'] == body.get('item')), None)
            require(definition, '道具不存在')
            route = data['automation']['items'].get(definition['id'])
            require(route and route['location'] == loc['id'], '此处不能领取该道具')
            require(not route.get('requires') or route['requires'] in owned, '缺少开柜钥匙')
            require(not route.get('reward') or definition['id'] in knowledge.get('rewards', []), '尚未取得该道具的领取资格')
            require(not route.get('manual'), '该物品需要角色对话或剧情选择，请在特殊行动中联系 KP')
            allocated = sum(max(1, int(i['numbers']['count'])) for i in self.entities(view, 'md.item') if i['numbers']['itemIndex'] == definition['index'])
            require(allocated < definition['quantity'], '场景库存已分配完毕')
            require(len(items) < 4, '四个卡槽已满，请先转交或丢弃')
            daykey = str(w['day']) + ':' + loc['id']
            # Team quota counts everyone, including private inventories.
            team = sum(snapshot['knowledge'].get(m['memberId'], {}).get('loot', {}).get(daykey, 0) for m in snapshot['members'])
            require(team < 3, '全队今日在此地点已取得三件道具')
            iid = self.command('entity.create', {'configurationId': 'md.item', 'owner': owner, 'visibility': 'owner', 'name': definition['name'], 'numbers': {'itemIndex': definition['index']}})
            self.command('relation.set', {'sourceId': iid, 'targetId': aid, 'relationType': 'source'})
            self.command('relation.set', {'sourceId': aid, 'targetId': iid, 'relationType': 'references'})
            self.invoke('md.confirm', actor=iid)
            knowledge['loot'][daykey] = knowledge['loot'].get(daykey, 0) + 1
            message = '已领取并生成可用卡片：' + definition['name'] + '。'
        elif kind in ('equip', 'consume', 'discard', 'offer'):
            item = next((i for i in items if i['instanceId'] == body.get('item')), None)
            require(item and item['numbers']['confirmed'], '道具不属于该角色或尚未确认')
            definition = data['items'][item['numbers']['itemIndex'] - 1]
            if kind == 'equip':
                self.invoke('md.equip', actor=aid, item=item['instanceId'])
                message = '已装备：' + item['name'] + '。'
            elif kind == 'consume':
                purpose = {'item-medkit': 'medicine', 'item-food': 'food', 'item-antidote': 'antidote'}.get(definition['id'])
                if definition['id'] == 'item-mask':
                    self.invoke('md.resolve', actor=aid, kind='hint', destination=n['location'])
                    self.command('entity.update', {'id': item['instanceId'], 'numbers': {'count': item['numbers']['count'] - 1}})
                    knowledge['sheltered'] = True
                else:
                    require(purpose, '此物品的特殊用途请通过特殊行动说明')
                    self.invoke('md.consume', actor=aid, item=item['instanceId'], kind=purpose)
                used = purpose == 'medicine'
                message = '已使用：' + item['name'] + '，效果和数量已更新。'
            elif kind == 'discard':
                if item['numbers']['equipped']:
                    self.command('entity.update', {'id': aid, 'numbers': {'weapon': 0}})
                self.command('entity.update', {'id': item['instanceId'], 'numbers': {'count': 0, 'equipped': 0}})
                message = '已丢弃：' + item['name'] + '，卡槽已释放。'
            else:
                target = view['entities'].get(body.get('target'))
                require(target and target['configurationId'] == 'md.character' and target['lifecycle'] == 'active' and target['owner'] != owner, '请选择另一名玩家的角色')
                require(target['numbers']['location'] == n['location'], '转交双方必须同地')
                return self.need(target['owner'], target['instanceId'], '确认接收道具', actor['name'] + ' 希望交给你：' + item['name'], ':transfer', {'kind': 'transfer', 'item': item['instanceId'], 'source': aid})
        elif kind == 'attack':
            target = view['entities'].get(body.get('target'))
            require(target and target['configurationId'] == 'md.character' and target['lifecycle'] == 'active' and target['instanceId'] != aid, '攻击目标无效')
            require(target['numbers']['location'] == n['location'] and target['numbers']['hp'] > 0, '目标必须同地且未倒下')
            require(not self.db.execute('SELECT 1 FROM needs WHERE actor=? AND title="选择防御" AND state="open"', (target['instanceId'],)).fetchone(), '该角色已有待回应的攻击')
            return self.need(target['owner'], target['instanceId'], '选择防御', actor['name'] + ' 发起攻击，请选择对抗或闪避。', ':defense', {'kind': 'attack', 'source': aid})
        elif kind == 'finish':
            require(n['encounterActive'], '当前没有进行中的遭遇')
            require(not self.db.execute('SELECT 1 FROM needs WHERE title="选择防御" AND state="open"').fetchone(), '请先完成待回应的攻击')
            self.invoke('md.finish', actor=aid)
            message = '已结束本人的遭遇。'
        elif kind in ('start-boat', 'stop-tracking', 'open-maintenance', 'boat-key', 'ending', 'hint'):
            if kind == 'hint':
                self.invoke('md.resolve', actor=aid, kind='hint', destination=n['location'])
                prompts = [p['prompt'] for p in data['puzzles'] if data['automation']['puzzles'][p['id']]['location'] == loc['id']]
                message = '提示：' + ('；'.join(prompts) if prompts else '试着查看现场的文字、容器与相邻入口，重要线索不依赖一次掷骰成功。')
            elif kind == 'start-boat':
                require(loc['id'] in ('loc-shore', 'loc-basement') and loc['id'] in knowledge['searched'], '请先探索船舱或地下控制室')
                require(not w['boatReady'] and not n['slotUsed'] and not n['encounterActive'], '船已就绪或本轮不能再操作')
                self.invoke('md.resolve', actor=aid, kind='wait', destination=n['location'])
                self.command('entity.update', {'id': world['instanceId'], 'numbers': {'boatReady': 1}})
                used, message = True, '已启动归航船。'
            elif kind == 'stop-tracking':
                require(loc['id'] == 'loc-basement' and loc['id'] in knowledge['searched'], '请先探索地下控制室')
                require(not w['trackingOff'] and not n['slotUsed'] and not n['encounterActive'], '追踪已关闭或本轮不能再操作')
                self.invoke('md.resolve', actor=aid, kind='wait', destination=n['location'])
                self.command('entity.update', {'id': world['instanceId'], 'numbers': {'trackingOff': 1}})
                used, message = True, '已关闭追踪阵法；归航船仍可使用。'
            elif kind == 'open-maintenance':
                require(loc['id'] == 'loc-steward' and any(c['id'] == 'C4' for c in knowledge['clues']), '请先调查管家工作记录')
                self.command('entity.update', {'id': world['instanceId'], 'numbers': {'basementOpen': 1}})
                message = '维修拉杆已开启地下入口。'
            elif kind == 'boat-key':
                require(loc['id'] == 'loc-steward' and any(c['id'] in ('C1', 'C2', 'C7') for c in knowledge['clues']), '需要在管家房出示选拔证据')
                require(body.get('choice') == 'promise', '需要本人承诺不继续互杀')
                self.command('entity.update', {'id': world['instanceId'], 'numbers': {'boatReady': 1}})
                message = '管家接受证据与承诺，交出船的使用权。'
            else:
                ending = body.get('choice')
                require(ending in ('1', '2', '3', '4', '5'), '请选择自己的结局')
                require(w['day'] == 2 and w['slot'] == 8, '尚未到最终选择时刻')
                if ending in ('1', '2'):
                    require(loc['id'] == 'loc-shore' and w['boatReady'], '需要到达海岸且船已就绪')
                    if ending == '2':
                        require(any(c['id'] in ('C1', 'C2', 'C7') for c in knowledge['clues']), '尚未持有选拔证据')
                if ending == '4':
                    require(w['offerMade'], '招募尚未发布')
                self.command('entity.update', {'id': aid, 'numbers': {'ending': int(ending)}})
                message = '已记录本人选择的结局：' + {'1': '归航', '2': '携证归航', '3': '留守', '4': '前往神界', '5': '困岛续章'}[ending] + '。'
        elif kind == 'special':
            text = str(body.get('text', '')).strip()
            require(text, '请说明特殊行动的方法与目标')
            return self.need(owner, aid, '特殊行动需要裁决', text[:2000])
        else:
            raise ActionError('不支持此行动')
        self.command('progress.set', {'ownerKind': 'member', 'ownerId': member, 'eventKey': 'md.known', 'value': knowledge})
        self.db.execute('INSERT OR REPLACE INTO knowledge VALUES (?,?)', (member, json.dumps(knowledge, ensure_ascii=False)))
        key_cards = {'item-chess-key', 'item-clock-key', 'item-record-key', 'item-sword-key', 'item-gun-key'}
        if kind in ('move', 'explore') and loc['id'] == 'loc-shore' and w['day'] == 2 and w['slot'] >= 7 and owned & key_cards and not w['trackingOff'] and not knowledge.get('sheltered') and not knowledge.get('pursuerMet'):
            knowledge['pursuerMet'] = True
            self.db.execute('INSERT OR REPLACE INTO knowledge VALUES (?,?)', (member, json.dumps(knowledge, ensure_ascii=False)))
            self.need(owner, aid, '海岸阻拦', actor['name'] + ' 携带尚未解除追踪的钥匙牌抵达海岸。请处理追踪者交涉或遭遇；玩家可以选择放弃钥匙牌或寻求庇护。', ':pursuer')
            message += '海岸出现追踪者，已通知 KP 处理交涉或遭遇。'
        self.log(owner, actor['name'] + '：' + message)
        if used:
            self.advance_if_ready(view, actor, world)
        return message

    @staticmethod
    def held(view, actor):
        relations = list(view['relations'].values())
        result = []
        for item in Automation.entities(view, 'md.item'):
            if item['owner'] != actor['owner'] or item['numbers']['count'] <= 0:
                continue
            source = [r for r in relations if r['sourceId'] == item['instanceId'] and r['relationType'] == 'source']
            ref = any(r['sourceId'] == actor['instanceId'] and r['targetId'] == item['instanceId'] and r['relationType'] == 'references' for r in relations)
            if len(source) == 1 and source[0]['targetId'] == actor['instanceId'] and ref:
                result.append(item)
        return result

    def advance_if_ready(self, view, actor, world):
        if not self.enabled():
            return
        players = [p for p in self.entities(view, 'md.character') if p['owner'] != 'kp' and p['numbers']['approved'] and p['numbers']['hp'] > 0 and not p['numbers']['ending']]
        if not players or any(p['numbers']['encounterActive'] or (p['instanceId'] != actor['instanceId'] and (not p['numbers']['slotUsed'] or (p['numbers']['day'], p['numbers']['slot']) != (world['numbers']['day'], world['numbers']['slot']))) for p in players):
            return
        if self.db.execute('SELECT 1 FROM needs WHERE state="open" AND title!="确认接收道具"').fetchone():
            return
        result = self.invoke('md.advance', actor=world['instanceId'])
        if not result['closed']:
            for player in players:
                self.invoke('md.sync', actor=player['instanceId'], day=result['day'], slot=result['slot'])
            if result['day'] == 2 and result['slot'] == 6:
                self.command('entity.update', {'id': world['instanceId'], 'numbers': {'offerMade': 1}})
                self.log('*', '招募已发布：可以选择前往神界，也可以继续调查并归航。', ':offer')
            if result['day'] == 2 and result['slot'] == 1:
                self.log('*', '午夜后，宅邸的普通家具恢复原位。道具、证据和已经打开的关键通路仍然保留。归航窗口在今日凌晨2。', ':midnight')
        labels = ['上午1', '上午2', '下午1', '下午2', '晚上1', '晚上2', '凌晨1', '凌晨2']
        self.log('*', '本轮全员行动完成。' + ('调查时钟已结束，请选择结局。' if result['closed'] else f"进入第{result['day']}日 {labels[result['slot']-1]}。"), ':clock')
