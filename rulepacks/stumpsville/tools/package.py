"""Package composition and resumable public-API workflows. No host internals."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time

from client import HostError
import scenes

PACK = Path(__file__).resolve().parents[1]


def bundle():
    manifest = json.loads((PACK / 'manifest.json').read_text(encoding='utf-8'))
    return {'manifest': manifest,
            'sources': {name: (PACK / 'rules' / name).read_text(encoding='utf-8') for name in manifest['rules']},
            'data': {name: json.loads((PACK / 'config' / name).read_text(encoding='utf-8')) for name in manifest['data']},
            'configurations': json.loads((PACK / manifest['configurations']).read_text(encoding='utf-8'))}


class PackageError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PackageError(message)


class Job:
    def __init__(self, store, client, record):
        self.store, self.client, self.record = store, client, record

    def command(self, key, op, args):
        step = self.record['steps'].get(key)
        if step is None:
            step = {'envelope': self.client.envelope(op, args)}
            self.record['steps'][key] = step
            self.store.save()
        if 'result' not in step:
            command_id = step['envelope']['payload']['commandId']
            receipt = self.client.request('/receipts/' + command_id)
            if receipt['status'] == 'unknown':
                current = self.client.request('/view')
                old = step['envelope']['payload']
                if old['authorityEpoch'] != current['authorityEpoch'] or old['runId'] != current['runId']:
                    require(old['rulesetRevision'] == current['catalog']['rulesetRevision'], '原行动未提交且规则已变更，请主持核查')
                    old.update(authorityEpoch=current['authorityEpoch'], runId=current['runId'], catalogRevision=current['catalog']['revision'])
                    self.store.save()
                receipt = self.client.send(step['envelope'])
            if receipt['status'] != 'committed':
                raise HostError(receipt)
            step['result'] = receipt.get('result')
            self.store.save()
        return step['result']

    def invoke(self, key, rule, **inputs):
        return self.command(key, 'action.invoke', {'actionId': rule, 'input': inputs})


class Package:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        # Heartbeats contain account IDs and times only, never KP credentials.
        self.executor_seen = {}
        self.game = bundle()['data']['game.json']
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding='utf-8'))
            require(self.state.get('format') == 1, '包侧存档格式不支持')
        else:
            self.state = {'format': 1, 'revision': 0, 'jobs': {}, 'drafts': {}, 'requests': {},
                          'notes': {}, 'locations': {str(x['index']): copy.deepcopy(x) for x in self.game['locations']},
                          'published': {}, 'bindings': {}, 'npcs': {}, 'recap': '', 'recapDraft': '',
                          'recapPrivate': '', 'receipts': {}, 'initialized': False}
        self.state.setdefault('doors', {'1-2': 'open', '2-3': 'closed', '3-4': 'open', '3-5': 'open', '3-6': 'open',
                                       '3-7': 'open', '3-8': 'open', '7-8': 'locked', '8-9': 'closed', '9-10': 'closed'})
        self.state.setdefault('roster', {})
        self.state.setdefault('generatedCharacters', {})
        self.state.setdefault('events', {})
        self.state.setdefault('discoveries', {})
        self.state.setdefault('sceneState', {})
        self.state.setdefault('autoSceneQueue', {})
        self.state.setdefault('ruleRevisions', {})
        self.state.setdefault('encounters', self.game['encounters'])
        self.state.setdefault('loot', ['待主持依原版战利品表裁定'] * 20)
        active = self.state.get('activeRevision')
        if active in self.state['ruleRevisions']:
            self.game = self.state['ruleRevisions'][active]['data']['game.json']

    @staticmethod
    def edge(a, b):
        return '-'.join(str(x) for x in sorted((a, b)))

    def passable(self, a, b):
        return self.state['doors'].get(self.edge(a, b), 'closed') == 'open'

    def automation_ready(self, session):
        sources = self.state['ruleRevisions'].get(self.state.get('activeRevision'), {}).get('sources', {})
        return bool(session and 'autoResolve' in session['numbers'] and 'auto-travel.lua' in sources)

    def scene_definitions(self):
        content = self.state['ruleRevisions'].get(self.state.get('activeRevision'), {})
        return content.get('data', {}).get('scene-actions.json', {}).get('actions', [])

    def scene_ready(self):
        content = self.state['ruleRevisions'].get(self.state.get('activeRevision'), {})
        return 'scene.lua' in content.get('sources', {}) and bool(self.state.get('sceneId')) and bool(self.scene_definitions())

    def scene_executor(self, client):
        with self.lock:
            view = client.request('/view')
            require(view['role'] == 'kp', '需要主持权限')
            self.executor_seen[view['accountId']] = time.time()
            session = next(iter(self.entities(view, 'sv.session')), None)
            enabled = session and session['numbers'].get('autoResolve', 1) and view['status'] == 'active'
            tasks = [t for t in self.state['autoSceneQueue'].values() if t['status'] in {'queued', 'running', 'finishing'}
                     and (not t.get('executor') or t['executor'] == view['accountId'])]
            return {'jobs': [{'id': t['id'], 'commandId': t['commandId']} for t in tasks[:1]] if enabled else []}

    def queue_scene(self, view, character, job, definition, choice):
        key = job.record['requestKey']
        require(not any(t['account'] == view['accountId'] and t['status'] in {'queued', 'running', 'finishing'}
                        for t in self.state['autoSceneQueue'].values()), '请等待当前预设行动自动完成')
        task = {'id': key, 'account': view['accountId'], 'actor': character['instanceId'],
                'action': definition['id'], 'choice': choice, 'title': definition['label'], 'status': 'queued',
                'time': time.time(), 'commandId': 'scene-auto-' + hashlib.sha256(key.encode()).hexdigest()[:40]}
        self.state['autoSceneQueue'][key] = task
        return {'status': 'processing', 'jobId': key, 'sceneAction': definition['id'], 'title': definition['label'],
                'message': '行动已接收，等待自动执行端结算；无需主持逐项确认', 'outcome': 'queued',
                'narrative': ['预设行动已排入自动队列。KP 页面在线时会自动处理；尚未投骰或扣减资源。'],
                'checks': [], 'rolls': [], 'stateChanges': [], 'clues': [], 'process': '已提交 → 等待自动执行端'}

    def run_scene_queue(self, job, view, task_id):
        task = self.state['autoSceneQueue'].get(task_id)
        require(task is not None, '自动行动不存在')
        if task['status'] == 'completed':
            return task['result']
        require(not task.get('executor') or task['executor'] == view['accountId'], '请由原自动执行端恢复此行动')
        session = next(iter(self.entities(view, 'sv.session')))
        require(session['numbers'].get('autoResolve', 1) == 1, '自动裁决已关闭，自动队列暂缓执行')
        actor = view['entities'].get(task['actor'])
        task.update(status='running', executor=view['accountId'])
        self.save()
        try:
            require(actor and actor['owner'] == task['account'] and actor['lifecycle'] == 'active', '角色归属或状态已改变')
            result = self.execute_scene(job, view, actor, task['action'], task['choice'])
        except (PackageError, HostError) as error:
            if 'result' in job.record['steps'].get('scene-act', {}):
                raise  # Committed effects must finish publication through the same job.
            if isinstance(error, HostError) and error.response.get('status') != 'rejected':
                raise
            reason = str(error) if isinstance(error, PackageError) else '当前角色或场景条件不允许执行此做法'
            result = {'status': 'completed', 'sceneAction': task['action'], 'title': task['title'], 'outcome': 'blocked',
                'message': '本次自动行动未执行', 'process': '执行前校验未通过，未产生本次行动的掷骰或资源效果',
                'narrative': [reason], 'checks': [], 'rolls': [], 'stateChanges': [], 'clues': []}
            if self.state.get('scenePending') == job.record['requestKey']:
                self.state.pop('scenePending')
        task.update(status='finishing', result=result, completedAt=time.time())
        origin = self.state['jobs'][task_id]
        origin.update(result=result, executed=result)
        receipt_id = task_id.split(':', 1)[1]
        for receipt in self.state['receipts'].get(task['account'], []):
            if receipt['id'] == receipt_id:
                receipt['result'] = result
        return result

    def install_scenes(self, job, view):
        content = copy.deepcopy(self.state['ruleRevisions'][self.state['activeRevision']])
        current = bundle()
        content['sources']['scene.lua'] = current['sources']['scene.lua']
        content['data']['scene-actions.json'] = current['data']['scene-actions.json']
        revision = job.command('scene-stage', 'rule.stage', content)
        job.command('scene-activate', 'rule.activate', {'revision': revision})
        self.state['ruleRevisions'][revision] = content
        self.state['activeRevision'] = revision
        config = next(c for c in current['configurations'] if c['configurationId'] == 'sv.scene')
        job.command('scene-config', 'configuration.put', config)
        existing = next(iter(self.entities(view, 'sv.scene')), None)
        if existing:
            self.state['sceneId'] = existing['instanceId']
            self.state['sceneState'] = existing['numbers']
        else:
            values = {**scenes.DEFAULTS, **scenes.package_numbers(self.state)}
            self.state['sceneId'] = job.command('scene-create', 'entity.create', {'configurationId': 'sv.scene',
                'name': '树桩镇机关与有限库存', 'owner': view['accountId'], 'visibility': 'kp', 'numbers': values})
            self.state['sceneState'] = values
        return {'message': '场景预设规则与状态已安装；保持一个 KP 页面在线即可自动处理'}

    def execute_scene(self, job, view, actor, action, choice):
        require(self.scene_ready(), '场景规则尚未安装，请主持在控制台安装')
        definition = next((x for x in self.scene_definitions() if x['id'] == action), None)
        require(definition and choice in {x['id'] for x in definition['choices']}, '预设行动或做法不存在')
        if 'sceneContext' not in job.record:
            require(actor and actor['numbers']['location'] == definition['location'], '只能执行当前地点的预设行动')
            job.record['sceneContext'] = {'actor': actor['instanceId'], 'action': action, 'choice': choice,
                                        'location': definition['location']}
            self.save()
        context = job.record['sceneContext']
        require(context['action'] == action and context['choice'] == choice, '原行动内容不可更改')
        require(view['role'] == 'kp', '场景结算必须由已经登录的主持执行端运行')
        authority = job.client
        privileged = authority.request('/view')
        require(privileged['role'] == 'kp', '场景执行服务没有主持权限')
        actual = privileged['entities'].get(context['actor'])
        require(actual and (view['role'] == 'kp' or actual['owner'] == view['accountId']), '角色归属已改变')
        self.state['scenePending'] = job.record['requestKey']
        self.save()
        # Shared stock updates and character effects happen in one host transaction.
        # Package publication is resumable through these exact persisted envelopes.
        work = Job(self, authority, job.record)
        if 'scene-act' not in job.record['steps']:
            work.command('scene-sync', 'entity.update', {'id': self.state['sceneId'], 'numbers': scenes.package_numbers(self.state)})
        world = next(iter(self.entities(privileged, 'sv.world')))
        try:
            result = work.invoke('scene-act', 'sv.scene.resolve', actor=context['actor'], scene=self.state['sceneId'],
                                 world=world['instanceId'], action=action, choice=choice)
        except HostError as error:
            if error.response.get('status') == 'rejected':
                self.state.pop('scenePending', None)
                self.save()
            raise
        scenes.apply_numbers(self.state, result['sceneState'])
        for door in result['doors']:
            self.state['doors'][door['edge']] = door['status']
        public = copy.deepcopy(result['public'])
        for field in ('narrative', 'checks', 'rolls', 'stateChanges', 'clues'):
            if public.get(field) == {}:
                public[field] = []
        owner = actual['owner']
        discovery = self.state['discoveries'].setdefault(owner, {})
        for clue in public['clues']:
            discovery[clue['id']] = clue
        for index in result['reveals']:
            key = str(index)
            if key not in self.state['published']:
                place = self.state['locations'][key]
                entity = next(x for x in self.entities(privileged, 'sv.location') if x['numbers']['index'] == index)
                work.command('scene-reveal-' + key, 'entity.update', {'id': entity['instanceId'], 'visibility': 'public'})
                self.state['published'][key] = {k: copy.deepcopy(place[k]) for k in ('index', 'name', 'description', 'exits', 'features')}
                self.state['published'][key]['clues'] = []
                public['stateChanges'].append({'key': 'reveal' + key, 'label': '已知地点', 'before': '尚未揭示', 'after': place['name']})
        session = next(iter(self.entities(privileged, 'sv.session')))
        work.command('scene-doors', 'entity.update', {'id': session['instanceId'], 'numbers': self.public_door_numbers()})
        public['status'] = 'completed'
        public['message'] = public['title'] + '：' + {'success': '已完成', 'failure': '已结算后果', 'blocked': '条件不满足'}[public['outcome']]
        return public

    def public_door_numbers(self, extra=None):
        visible = set(self.state['published'])
        if extra is not None:
            visible.add(str(extra))
        return {'door' + edge.replace('-', '_'): int(status == 'open' and all(x in visible for x in edge.split('-')))
                for edge, status in self.state['doors'].items()}

    def queue_request(self, view, character, request_id, kind, args, text, reason):
        key = view['accountId'] + ':' + request_id
        self.state['requests'][key] = {'id': key, 'account': view['accountId'], 'actor': character['instanceId'],
            'kind': kind, 'args': copy.deepcopy(args), 'text': text, 'status': 'pending', 'reason': reason,
            'location': character['numbers']['location'], 'time': time.time()}
        return {'message': '已请求 KP 裁决；尚未结算', 'requestId': key, 'status': 'pending', 'reason': reason}

    def finish_auto_travel(self, job):
        saved = job.record['autoTravel']
        result = job.invoke('auto-travel', 'sv.travel.auto', actor=saved['actor'], destination=saved['destinationId'])
        self.state['requests'][saved['id']] = {k: copy.deepcopy(v) for k, v in saved.items() if k != 'destinationId'}
        self.state['requests'][saved['id']].update(status='automatic', result=result, reason='已公开相邻地点且通路开启')
        return {'message': '自动裁决完成：已到达地点 ' + str(result['location']), 'requestId': saved['id'], 'status': 'automatic', **result}

    def sync_automation(self, job, session, enabled=None):
        config = next(x for x in bundle()['configurations'] if x['configurationId'] == 'sv.session')
        job.command('auto-config', 'configuration.put', config)
        numbers = {'autoResolve': int(enabled) if enabled is not None else session['numbers'].get('autoResolve', 1)}
        numbers.update(self.public_door_numbers())
        job.command('auto-session', 'entity.update', {'id': session['instanceId'], 'numbers': numbers})

    def validate_bundle(self, content):
        require(isinstance(content, dict) and isinstance(content.get('sources'), dict) and
                isinstance(content.get('data'), dict), '需要 sources 和 data 的配置文件')
        require(1 <= len(content['sources']) <= 64 and all(isinstance(k, str) and isinstance(v, str)
                and len(v) <= 50000 for k, v in content['sources'].items()), '规则源码格式不正确')
        data = content['data'].get('game.json', {})
        # Slot identities are save-game schema. Text/rules may change; migrations are separate work.
        require(isinstance(data, dict) and isinstance(data.get('items'), list), '缺少物品资料')
        identity = lambda items: [(x.get('id'), x.get('kind'), x.get('slots'), x.get('uses')) for x in items]
        require(identity(data['items']) == identity(self.game['items']), '现有存档不支持改变物品编号、槽位或用量上限')
        for key in ('presets', 'rules', 'locations', 'npcs', 'encounters', 'sourceStatus'):
            require(key in data, '缺少资料字段：' + key)
        return copy.deepcopy({'sources': content['sources'], 'data': content['data']})

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state['revision'] += 1
        temporary = self.path.with_suffix('.writing')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(self.state, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows indexers can briefly hold the destination without delete sharing.
        # Retry the same already-fsynced bytes; never fall back to a partial overwrite.
        for attempt in range(20):
            try:
                os.replace(temporary, self.path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(.05)

    def entities(self, view, configuration):
        return [x for x in view['entities'].values() if x['configurationId'] == configuration and x['lifecycle'] == 'active']

    def own_character(self, view):
        return next((x for x in self.entities(view, 'sv.character') if x['owner'] == view['accountId']), None)

    def public_location(self, entity):
        index = str(entity['numbers']['index'])
        location = self.state['published'].get(index)
        if location is None:
            return None
        return {**copy.deepcopy(location), 'entityId': entity['instanceId']}

    def projection(self, client, preview=None):
        with self.lock:
            view = client.request('/view')
            is_kp = view['role'] == 'kp'
            if preview:
                require(is_kp, '需要主持权限')
            account = preview or view['accountId']
            gm = is_kp and not preview
            characters = self.entities(view, 'sv.character')
            mine = next((x for x in characters if x['owner'] == account), None)
            visible = [x for x in self.entities(view, 'sv.location') if x['visibility'] == 'public']
            locations = [self.public_location(x) for x in visible]
            locations = [x for x in locations if x]
            ids = {x['index'] for x in locations}
            for location in locations:
                location['exits'] = [x for x in location['exits'] if x in ids]
                location['doors'] = {str(x): self.state['doors'].get(self.edge(location['index'], x), 'closed') for x in location['exits']}
                known = {c['id'] for c in location['clues']}
                location['clues'].extend(copy.deepcopy(c) for c in self.state['discoveries'].get(account, {}).values()
                                        if c['location'] == location['index'] and c['id'] not in known)
            session = next(iter(self.entities(view, 'sv.session')), None)
            item_ids = set()
            for character in characters if gm else ([mine] if mine else []):
                item_ids.update(character['numbers'].get('item' + str(i), 0) for i in range(1, 21))
            # Item names and scenario secrets are not supplied as a full player catalog.
            items = {str(i): definition for i, definition in enumerate(self.game['items'], 1) if gm or i in item_ids}
            result = {'accountId': account, 'role': 'kp' if gm else 'player', 'roomStatus': view['status'],
                      'revision': self.state['revision'], 'initialized': self.state['initialized'],
                      'automation': {'enabled': bool(session and session['numbers'].get('autoResolve', 1)), 'ready': self.automation_ready(session)},
                      'sceneAutomation': {'ready': self.scene_ready(), 'executorOnline': any(time.time()-t < 20 for t in self.executor_seen.values())},
                      'autoSceneTasks': [{k: t[k] for k in ('id', 'title', 'status', 'time')} for t in self.state['autoSceneQueue'].values()
                                         if t['status'] != 'completed' and (gm or t['account'] == account)],
                      'sceneActions': [copy.deepcopy(x) for x in self.scene_definitions() if mine and x['location'] == mine['numbers']['location']],
                      'sceneStatus': scenes.public_state(self.state, mine['numbers']['location'], self.game['items']) if mine else {},
                      'character': mine, 'session': session, 'locations': locations, 'items': items,
                      'presets': self.game['presets'], 'rules': self.game['rules'],
                      'team': list(self.state['roster'].values()),
                      'generatedCharacter': self.state['generatedCharacters'].get(account),
                      'draft': self.state['drafts'].get(account), 'note': self.state['notes'].get(account, ''),
                      'requests': [x for x in self.state['requests'].values() if gm or x['account'] == account],
                      'recap': self.state['recap'], 'receipts': self.state['receipts'].get(account, [])[-100:],
                      'events': sorted((e for owner, events in self.state['events'].items() if gm or owner == account
                                        for e in events), key=lambda e: e['time'])[-200:],
                      'channels': {} if preview else view['chatChannels'],
                      'preview': bool(preview), 'previewKind': '包侧公开投影' if preview else None}
            if gm:
                result.update(roomId=view['roomId'], characters=characters, drafts=self.state['drafts'],
                              allLocations=self.state['locations'], npcs=self.entities(view, 'sv.npc'),
                              world=next(iter(self.entities(view, 'sv.world')), None),
                              members=client.request('/chat/members')['items'],
                              recapDraft=self.state['recapDraft'], recapPrivate=self.state['recapPrivate'],
                              sourceStatus=self.game['sourceStatus'], encounters=self.state['encounters'], loot=self.state['loot'],
                              npcTemplates=self.game['npcs'], doors=self.state['doors'], catalog=view['catalog'],
                              ruleRevisions=list(self.state['ruleRevisions']), published=self.state['published'])
                result['sceneDefinitions'] = self.scene_definitions()
            return result

    def action(self, client, body):
        require(isinstance(body, dict) and set(body) == {'id', 'operation', 'args'}, '行动格式不正确')
        require(isinstance(body['id'], str) and re.fullmatch(r'[a-zA-Z0-9-]{8,80}', body['id']), '行动编号不正确')
        require(isinstance(body['args'], dict), '行动参数不正确')
        with self.lock:
            view = client.request('/view')
            account = view['accountId']
            key = account + ':' + body['id']
            require(not self.state.get('scenePending') or self.state['scenePending'] == key or
                    body['operation'] in {'chat', 'note', 'draft', 'draft.roll', 'recap', 'share.receipt'},
                    '有场景结算尚待恢复，请发起者恢复原行动后再继续')
            fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            record = self.state['jobs'].get(key)
            if record:
                require(record['fingerprint'] == fingerprint, '同一行动编号不可更改内容')
                if record.get('done'):
                    return record['result']
            else:
                record = {'fingerprint': fingerprint, 'steps': {}, 'created': time.time()}
                self.state['jobs'][key] = record
                self.save()
            job = Job(self, client, record)
            record['requestKey'] = key
            feedback_ops = {'ready', 'check', 'inventory', 'request', 'resolve', 'world', 'actor.update', 'scene.action', 'scene.autorun',
                            'rest', 'grant', 'damage', 'remove', 'stock.take', 'approve',
                            'automation.configure', 'room', 'location.publish'}
            feedback = body['operation'] in feedback_ops
            if feedback and 'before' not in record:
                record['before'] = {x['owner']: {'name': x['name'], 'numbers': x['numbers']}
                                    for x in self.entities(view, 'sv.character')}
                self.save()
            # Once a command reaches the host its envelope remains durable. Pure package
            # changes are only exposed after their action completes under this lock.
            if 'executed' not in record:
                record['executed'] = self.execute(job, view, body['operation'], body['args'], body['id'])
                self.save()
            result = record['executed']
            if feedback:
                self.record_feedback(view, client.request('/view'), body, record, result)
            record.update(done=True, result=result)
            if body['operation'] == 'scene.autorun':
                self.state['autoSceneQueue'][body['args']['jobId']]['status'] = 'completed'
            if self.state.get('scenePending') == key:
                self.state.pop('scenePending')
            command_ids = [step['envelope']['payload']['commandId'] for step in record['steps'].values()]
            self.state['receipts'].setdefault(account, []).append({'id': body['id'], 'operation': body['operation'], 'result': result,
                                                                 'commandIds': command_ids, 'time': time.time()})
            self.save()
            return result

    def record_feedback(self, before_view, after_view, body, record, result):
        """Deliver only a character owner's changes; never copy a KP view into a PL event."""
        op, args, caller = body['operation'], body['args'], before_view['accountId']
        request_id = args.get('requestId') if op == 'resolve' else result.get('requestId') if isinstance(result, dict) else None
        request = self.state['requests'].get(request_id, {})
        if op == 'scene.autorun':
            task = self.state['autoSceneQueue'][args['jobId']]
            request = {'id': task['id'], 'account': task['account'], 'kind': 'scene', 'status': 'automatic',
                       'text': task['title'], 'reason': '按玩家选定的预设做法自动结算', 'result': result, 'time': task['time']}
            request_id = task['id']
        after = {x['owner']: {'name': x['name'], 'numbers': x['numbers']}
                 for x in self.entities(after_view, 'sv.character')}
        before = record['before']
        audience = {caller}
        audience.update(owner for owner in after if after[owner] != before.get(owner))
        if request:
            audience.add(request['account'])
        if op in {'world', 'automation.configure', 'room', 'location.publish'}:
            audience.update(after)
        titles = {'ready': '准备状态', 'check': '属性检定', 'inventory': '物品操作', 'request': '行动申请',
                  'scene.action': '场景行动',
                  'scene.autorun': '场景行动自动结果',
                  'resolve': 'KP 裁决回复', 'world': '探索进度', 'actor.update': '主持调整数值', 'rest': '休息恢复',
                  'grant': '获得物品', 'damage': '伤害结算', 'remove': '移除物品', 'stock.take': '领取物品',
                  'approve': '角色审核', 'automation.configure': '自动裁决设置', 'room': '房间状态', 'location.publish': '地点与线索发布'}
        kind = request.get('kind', op)
        title = titles.get(kind, {'travel': '地点移动', 'transfer': '物品转交', 'review': '事件复核',
                                 'free': '自由行动', 'interact': '场景互动'}.get(kind, titles[op]))
        for owner in audience:
            status = request.get('status', 'completed')
            if status == 'automatic':
                status = 'completed'
            if isinstance(result, dict) and result.get('status') == 'processing':
                status = 'processing'
            own_result = result if owner == caller else request.get('result', {}) if owner == request.get('account') else {}
            if owner != caller and op in {'world', 'automation.configure', 'room', 'location.publish'}:
                session = next(iter(self.entities(after_view, 'sv.session')), None)
                message = {'world': '探索进度已更新 · 第 ' + str(session['numbers']['round']) + ' 回合',
                           'automation.configure': '自动裁决' + ('已开启' if session['numbers'].get('autoResolve', 1) else '已关闭'),
                           'room': '房间' + ('已暂停' if after_view['status'] == 'paused' else '已恢复'),
                           'location.publish': '主持发布了地点与线索，请查看已知地图和线索面板'}[op]
                own_result = {'message': message}
            if isinstance(own_result, dict) and 'result' in own_result and own_result['result']:
                own_result = own_result['result']
            event = {'id': caller + ':' + body['id'], 'account': owner, 'operation': op,
                     'title': title, 'text': request.get('text', '') if owner in {caller, request.get('account')} else '',
                     'status': status, 'mode': 'kp' if request.get('status') == 'pending' or op == 'resolve' or before_view['role'] == 'kp' else 'auto',
                     'requestId': request_id, 'receiptId': body['id'] if owner == caller else None,
                     'reason': request.get('reason', '') if owner in {caller, request.get('account')} else '',
                     'result': own_result, 'changes': self.character_changes(before.get(owner), after.get(owner)),
                     'time': time.time(), 'submittedAt': request.get('time', record['created'])}
            # Narrative approval records an answer; it does not imply a rule was run.
            event['mechanical'] = bool(record['steps']) and (not request or kind in {'check', 'inventory', 'travel', 'transfer'})
            if isinstance(own_result, dict) and own_result.get('sceneAction'):
                event['title'] = own_result['title']
                event['mechanical'] = own_result['outcome'] not in {'blocked', 'queued'}
            if op == 'scene.autorun':
                event['mode'] = 'auto'
                if owner == request['account']:
                    event['id'] = request['id']
                    event['receiptId'] = request['id'].split(':', 1)[1]
            events = self.state['events'].setdefault(owner, [])
            if op == 'scene.autorun' and owner == request['account']:
                # Complete the original submission card instead of leaving a stale
                # "waiting" event alongside its eventual result.
                events[:] = [e for e in events if e['id'] != event['id']]
            if not any(e['id'] == event['id'] for e in events):
                events.append(event)
                del events[:-200]

    def character_changes(self, previous, current):
        if not current:
            return []
        before, after = (previous or {}).get('numbers', {}), current['numbers']
        labels = {'hp': 'HP', 'maxHp': 'HP 上限', 'str': 'STR', 'dex': 'DEX', 'wil': 'WIL',
                  'strMax': 'STR 上限', 'dexMax': 'DEX 上限', 'wilMax': 'WIL 上限', 'armor': '基础护甲',
                  'pips': '钱币', 'xp': 'XP', 'level': '等级', 'grit': 'Grit', 'location': '所在地点',
                  'ready': '准备', 'incapacitated': '失能', 'litSlot': '光源槽位', 'conditionPending': '待整理状态'}
        changes = []
        def add(key, label, old, new):
            if old != new:
                changes.append({'key': key, 'label': label, 'before': old, 'after': new})
        for key, label in labels.items():
            old, new = before.get(key, 0), after.get(key, 0)
            if key == 'location':
                name = lambda value: self.state['published'].get(str(value), {}).get('name', '未公开地点' if value else '尚未入场')
                old, new = name(old), name(new)
            add(key, label, old, new)
        for slot in range(1, 21):
            def item(numbers):
                index = numbers.get('item' + str(slot), 0)
                if not index:
                    return '空'
                definition = self.game['items'][index - 1]
                value = definition['name']
                if definition['uses']:
                    value += ' · 用量 ' + str(numbers.get('uses' + str(slot), 0))
                return value
            add('slot' + str(slot), '槽位 ' + str(slot), item(before), item(after))
        return changes

    def execute(self, job, view, op, args, request_id):
        account = view['accountId']
        gm = view['role'] == 'kp'
        character = self.own_character(view)
        session = next(iter(self.entities(view, 'sv.session')), None)
        world = next(iter(self.entities(view, 'sv.world')), None)
        player_ops = {'draft', 'draft.roll', 'note', 'request', 'ready', 'check', 'inventory', 'chat', 'share.receipt', 'scene.action'}
        require(op in player_ops or gm, '需要主持权限')
        if op == 'initialize':
            return self.initialize(job)
        require(self.state['initialized'], '请主持先安装配置包')
        require(view['status'] != 'archived', '房间已经归档，只能阅读')
        require(view['status'] == 'active' or op in {'note', 'draft', 'draft.roll', 'room', 'recap', 'backup', 'chat', 'automation.configure', 'rules.install', 'scene.install', 'request'}, '房间暂停或已归档')
        if op == 'scene.install':
            return self.install_scenes(job, view)
        if op == 'scene.autorun':
            require(set(args) == {'jobId'}, '自动行动参数不正确')
            task = self.state['autoSceneQueue'].get(args['jobId'])
            require(task and request_id == task['commandId'], '自动行动编号不正确')
            return self.run_scene_queue(job, view, args['jobId'])
        if op == 'scene.action':
            require(set(args) <= {'action', 'choice', 'manual'} and {'action', 'choice'} <= set(args), '场景行动参数不正确')
            require(isinstance(args.get('manual', False), bool), '裁决方式无效')
            definition = next((x for x in self.scene_definitions() if x['id'] == args['action']), None)
            require(definition and args['choice'] in {c['id'] for c in definition['choices']}, '预设行动不存在')
            require(character and character['numbers']['ready'] == 1 and session['numbers']['phase'] == 1, '请先准备并等待主持开场')
            require('sceneContext' in job.record or character['numbers']['location'] == definition['location'], '只能执行当前地点的预设行动')
            if args.get('manual') or session['numbers'].get('autoResolve', 1) == 0:
                return self.queue_request(view, character, request_id, 'scene', {'action': args['action'], 'choice': args['choice']},
                    definition['label'], '玩家主动申请' if args.get('manual') else '主持已关闭自动裁决')
            return self.queue_scene(view, character, job, definition, args['choice'])
        if op == 'automation.configure':
            require(isinstance(args.get('enabled'), bool) and set(args) == {'enabled'}, '自动裁决设置无效')
            require(self.automation_ready(session), '请先安装当前规则以升级此存档')
            self.sync_automation(job, session, args['enabled'])
            return {'message': '自动裁决已开启' if args['enabled'] else '自动裁决已关闭；行动交由 KP 裁决'}
        if op == 'chat':
            require(args.get('operation') in {'chat.direct.open', 'chat.channel.create', 'chat.channel.update', 'chat.message.send',
                'chat.message.share', 'chat.message.edit', 'chat.message.retract', 'chat.read'}, '聊天操作不支持')
            return job.command('chat', args['operation'], args.get('input', {}))
        if op == 'share.receipt':
            receipt = next((x for x in self.state['receipts'].get(account, []) if x['id'] == args.get('receiptId')), None)
            require(receipt and receipt['operation'] in {'check', 'inventory', 'ready'}, '这项回执不可分享')
            result = receipt['result']
            require(result.get('status') != 'pending', '待裁决的行动尚未结算，不能分享结果')
            if receipt['operation'] == 'check':
                summary = f"{result['attribute'].upper()} {result['rolled']}/{result['target']} · " + ('成功' if result['passed'] else '失败')
            elif receipt['operation'] == 'ready':
                summary = '已准备' if result.get('ready') else '取消准备'
            else:
                summary = '物品操作 ' + result['operation'] + ' · 剩余用量 ' + str(result.get('uses', '—'))
            return job.command('share', 'chat.message.send', {'channelId': args['channelId'],
                'text': '【树桩镇回执摘要】' + account + ' · ' + summary + '\n（包侧根据本人回执生成的文字摘要）'})
        if op == 'draft.roll':
            require(not character, '已有角色')
            # A dedicated owner entity provides an authenticated, persisted random draft.
            generated = next((x for x in self.entities(view, 'sv.draft') if x['owner'] == account), None)
            require(generated is not None, '请主持先开放随机建角')
            values = job.invoke('roll', 'sv.create', actor=generated['instanceId'])
            self.state['generatedCharacters'][account] = values
            return values
        if op == 'draft':
            require(not character, '已有角色，请主持修改现有角色')
            name = str(args.get('name', '')).strip()
            require(1 <= len(name) <= 40, '角色名称应为1至40字')
            preset = next((x for x in self.game['presets'] if x['id'] == args.get('preset')), None)
            if args.get('preset') == 'random':
                generated = self.state['generatedCharacters'].get(account)
                require(generated is not None, '请先生成属性')
                preset = {**copy.deepcopy(self.game['presets'][0]), **generated, 'description': '随机建角；背景与起始物品由主持按 HP/钱币表核定'}
                swap = args.get('swap', '')
                require(swap in {'', 'str-dex', 'str-wil', 'dex-wil'}, '交换属性无效')
                if swap:
                    a, b = swap.split('-')
                    preset[a], preset[b] = preset[b], preset[a]
            require(preset is not None, '请选择预设或随机草稿')
            self.state['drafts'][account] = {**copy.deepcopy(preset), 'name': name, 'account': account, 'status': 'submitted', 'requestId': request_id}
            return {'message': '角色草稿已提交主持审核'}
        if op == 'note':
            text = args.get('text', '')
            require(isinstance(text, str) and len(text) <= 8000, '手记最多8000字')
            self.state['notes'][account] = text
            return {'message': '手记已保存'}
        if op == 'approve':
            return self.approve(job, view, args)
        if op == 'request':
            require(character and character['numbers']['approved'] == 1, '请先完成角色审核')
            if 'autoTravel' in job.record:
                return self.finish_auto_travel(job)
            kind = args.get('kind', 'free')
            require(kind in {'travel', 'free', 'transfer', 'interact', 'review', 'check', 'inventory'}, '请求类型不支持')
            if kind != 'review':
                require(view['status'] == 'active', '房间暂停或已归档')
                require(session['numbers']['phase'] == 1 and character['numbers']['ready'] == 1, '请先准备并等待主持开场')
            text = str(args.get('text', '')).strip()
            require(len(text) <= 2000, '请求文字过长')
            manual = args.get('manual', False)
            require(isinstance(manual, bool), '裁决方式无效')
            automatic = self.automation_ready(session) and session['numbers'].get('autoResolve', 1) == 1 and not manual
            if kind == 'review':
                require(bool(text), '请描述需要裁决的事件')
                receipt_id = args.get('receiptId')
                if receipt_id:
                    require(any(x['id'] == receipt_id for x in self.state['receipts'].get(account, [])), '只能复核本人的行动回执')
                return self.queue_request(view, character, request_id, kind, {'receiptId': receipt_id}, text, '玩家主动申请；复核不重复执行原行动')
            if kind in {'check', 'inventory'}:
                params = args.get('input', {})
                allowed = {'check': {'attribute', 'mode'}, 'inventory': {'operation', 'slot', 'value'}}[kind]
                require(isinstance(params, dict) and set(params) == allowed, '行动参数不正确')
                return self.queue_request(view, character, request_id, kind, params, text or ('请求裁决：' + kind), '玩家主动申请')
            if kind == 'travel':
                destination = args.get('destination')
                current = self.state['locations'][str(character['numbers']['location'])]
                visible = {x['numbers']['index'] for x in self.entities(view, 'sv.location')}
                require(destination in current['exits'] and destination in visible and self.passable(current['index'], destination), '该通路尚未开放')
                if automatic:
                    target = next(x for x in self.entities(view, 'sv.location') if x['numbers']['index'] == destination)
                    job.record['autoTravel'] = {'id': account + ':' + request_id, 'account': account, 'actor': character['instanceId'],
                        'kind': kind, 'args': {'destination': destination}, 'text': text or '移动到地点 ' + str(destination),
                        'location': current['index'], 'destinationId': target['instanceId'], 'time': time.time()}
                    self.save()
                    return self.finish_auto_travel(job)
            if kind == 'transfer':
                target = self.state['roster'].get(args.get('targetAccount'))
                require(target and target['account'] != account, '请选择队友')
                args = {**args, 'target': target['id']}
            reason = '玩家主动申请' if manual else '自动裁决已关闭' if not automatic else '事件需要主持判断或涉及其他角色资源'
            return self.queue_request(view, character, request_id, kind, args, text, reason)
        if op in {'ready', 'check', 'inventory'}:
            require(character is not None, '未分配角色')
            allowed = {'ready': {'ready'}, 'check': {'attribute', 'mode'}, 'inventory': {'operation', 'slot', 'value'}}[op]
            require(set(args) == allowed, '参数与行动不符')
            if op in {'check', 'inventory'} and session['numbers'].get('autoResolve', 1) == 0:
                return self.queue_request(view, character, request_id, op, args, '请求裁决：' + op, '自动裁决已关闭')
            return job.invoke('action', 'sv.' + op, actor=character['instanceId'], **args)
        if op == 'resolve':
            request = self.state['requests'].get(args.get('requestId'))
            require(request is not None, '请求不存在')
            if request['status'] != 'pending':
                return {'message': '此请求已经处理', 'status': request['status']}
            reason = str(args.get('reason', '')).strip()
            require(len(reason) <= 2000, '裁定说明过长')
            if args.get('approve'):
                current_actor = view['entities'].get(request['actor'])
                require(current_actor and current_actor['lifecycle'] == 'active' and current_actor['owner'] == request['account'], '角色归属已经改变')
                if request['kind'] == 'scene':
                    request['result'] = self.execute_scene(job, view, current_actor, request['args']['action'], request['args']['choice'])
                if request['kind'] in {'check', 'inventory'}:
                    params = {'attribute': 'dex', 'mode': 'normal', 'operation': 'move', 'slot': 0, 'value': 0, **request['args']}
                    request['result'] = job.invoke('ruling', 'sv.adjudicate', actor=request['actor'], kind=request['kind'], **params)
                if request['kind'] == 'travel':
                    destination = request['args']['destination']
                    current_actor = view['entities'].get(request['actor'])
                    require(current_actor and current_actor['owner'] == request['account'], '角色归属已经改变')
                    allowed = self.state['locations'][str(current_actor['numbers']['location'])]['exits']
                    require(destination in allowed and self.passable(current_actor['numbers']['location'], destination), '角色位置或门状态变化，请重新请求')
                    request['result'] = job.invoke('travel', 'sv.travel', actor=request['actor'], location=destination)
                elif request['kind'] == 'transfer':
                    params = request['args']
                    source, target = view['entities'].get(request['actor']), view['entities'].get(params['target'])
                    require(source and target and source['owner'] == request['account'] and source['numbers']['location'] == target['numbers']['location'], '角色归属或位置变化，请重新请求')
                    request['result'] = job.invoke('transfer', 'sv.transfer', actor=request['actor'], target=params['target'], slot=params['slot'], destination=params['destination'])
                request['status'] = 'approved'
            else:
                request['status'] = 'rejected'
            request['reason'] = reason
            return {'message': '裁定已保存', 'status': request['status'], 'result': request.get('result')}
        if op == 'location.save':
            index = str(args.get('index'))
            require(index in self.state['locations'], '地点不存在')
            require(args.get('revision') == self.state['locations'][index].get('revision', 0), '地点版本冲突，请刷新')
            location = self.state['locations'][index]
            updated = {}
            for field in ('description', 'truth'):
                value = args.get(field, '')
                require(isinstance(value, str) and len(value) <= 6000, '地点文字过长')
                updated[field] = value
            location.update(updated)
            location['revision'] = location.get('revision', 0) + 1
            return {'message': '地点草稿已保存'}
        if op == 'location.publish':
            index = str(args.get('index'))
            require(index in self.state['locations'], '地点不存在')
            location = self.state['locations'][index]
            entity = next(x for x in self.entities(view, 'sv.location') if str(x['numbers']['index']) == index)
            public = {k: copy.deepcopy(location[k]) for k in ('index', 'name', 'description', 'exits', 'features')}
            chosen = args.get('clues', [])
            require(isinstance(chosen, list), '线索选择格式错误')
            public['clues'] = [copy.deepcopy(x) for x in location['clues'] if x['id'] in chosen]
            job.command('publish', 'entity.update', {'id': entity['instanceId'], 'visibility': 'public'})
            if 'autoResolve' in session['numbers']:
                job.command('public-doors', 'entity.update', {'id': session['instanceId'], 'numbers': self.public_door_numbers(index)})
            self.state['published'][index] = public
            return {'message': '地点公开内容已发布'}
        if op == 'door':
            key = args.get('edge')
            require(key in self.state['doors'] and args.get('status') in {'open', 'closed', 'locked'}, '通路设置无效')
            if 'autoResolve' in session['numbers']:
                public_open = args['status'] == 'open' and all(x in self.state['published'] for x in key.split('-'))
                job.command('door', 'entity.update', {'id': session['instanceId'], 'numbers': {'door' + key.replace('-', '_'): int(public_open)}})
            self.state['doors'][key] = args['status']
            return {'message': '通路状态已更新'}
        if op == 'stock.take':
            location = self.state['locations'].get(str(args.get('index')))
            actor = view['entities'].get(args.get('actor'))
            require(location and actor and actor['configurationId'] == 'sv.character' and actor['numbers']['location'] == location['index'], '角色不在此地点')
            stock = next((x for x in location['stock'] if x['item'] == args.get('item')), None)
            require(stock and stock['count'] > 0, '库存不足')
            definition = self.game['items'][stock['item'] - 1]
            job.invoke('grant', 'sv.grant', actor=actor['instanceId'], item=stock['item'], slot=args['slot'], uses=definition['uses'])
            stock['count'] -= 1
            return {'message': '物品已领取，地点库存已扣减', 'remaining': stock['count']}
        if op == 'world':
            operation = args.get('operation')
            return job.invoke('world', 'sv.world', actor=session['instanceId'], operation=operation, value=args.get('round', 0))
        if op == 'generate':
            kind = args['kind']
            result = job.invoke('generate', 'sv.generate', actor=world['instanceId'], kind=kind)
            if kind == 'pots':
                self.state['locations']['4']['stock'] = [{'item': 8, 'count': result['count']}]
            if kind == 'rats':
                for i in range(result['count']):
                    job.command('rat-' + str(i), 'entity.create', {'configurationId': 'sv.npc', 'name': 'Dedratz ' + str(i + 1) + '（待核数值）',
                        'owner': 'kp', 'visibility': 'kp', 'numbers': {'location': 7}})
            if kind == 'encounter':
                result['message'] = '遭遇' if result['rolled'] == 1 else '征兆' if result['rolled'] == 2 else '没有遭遇'
            if kind == 'encounter-table':
                result['entry'] = self.state['encounters'][result['rolled'] - 1]
            if kind == 'loot':
                result['entry'] = self.state['loot'][result['rolled'] - 1]
            return result
        if op == 'tables.save':
            for key, length in [('encounters', 6), ('loot', 20)]:
                rows = args.get(key)
                require(isinstance(rows, list) and len(rows) == length and all(isinstance(x, str) and len(x) <= 2000 for x in rows), '随机表行数或文字无效')
            self.state['encounters'], self.state['loot'] = args['encounters'], args['loot']
            return {'message': '主持随机表已保存'}
        if op in {'damage', 'rest', 'grant', 'remove', 'morale'}:
            target = view['entities'].get(args.get('actor'))
            require(target and target['configurationId'] in {'sv.character', 'sv.npc'}, '目标角色不存在')
            return job.invoke(op, 'sv.' + op, **args)
        if op == 'npc.create':
            name = str(args.get('name', '')).strip()
            require(1 <= len(name) <= 60, '名称应为1至60字')
            numbers = args.get('numbers', {})
            require(set(numbers) == {'str', 'dex', 'wil', 'hp', 'armor', 'location'}, '请填写完整数值')
            require(all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 100 for x in numbers.values()) and 1 <= numbers['location'] <= 10, 'NPC 数值无效')
            numbers = {**numbers, 'strMax': numbers['str'], 'dexMax': numbers['dex'], 'wilMax': numbers['wil'], 'maxHp': numbers['hp']}
            entity = job.command('npc', 'entity.create', {'configurationId': 'sv.npc', 'name': name, 'owner': 'kp', 'visibility': 'kp', 'numbers': numbers})
            return {'message': '主持生物已创建', 'id': entity}
        if op == 'actor.update':
            target = view['entities'].get(args.get('id'))
            require(target and target['configurationId'] in {'sv.character', 'sv.npc'}, '角色不存在')
            allowed = {'armor', 'str', 'dex', 'wil', 'hp', 'strMax', 'dexMax', 'wilMax', 'maxHp', 'xp', 'level', 'grit', 'pips', 'incapacitated'}
            numbers = args.get('numbers', {})
            require(isinstance(numbers, dict) and set(numbers) <= allowed, '数值字段不支持')
            require(all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 100000 for x in numbers.values()), '数值无效')
            merged = {**target['numbers'], **numbers}
            require(all(merged[x] <= merged[x + 'Max'] for x in ('str', 'dex', 'wil')) and merged['hp'] <= merged['maxHp'], '当前值不能超过上限')
            return job.command('update', 'entity.update', {'id': target['instanceId'], 'numbers': numbers})
        if op == 'room':
            require(args.get('status') in {'active', 'paused'}, '房间状态不支持')
            return job.command('room', 'room.status', args)
        if op == 'recap':
            updated = {}
            for field in ('recapDraft', 'recapPrivate'):
                value = args.get(field, '')
                require(isinstance(value, str) and len(value) <= 8000, '回顾文字过长')
                updated[field] = value
            self.state.update(updated)
            if args.get('publish'):
                self.state['recap'] = self.state['recapDraft']
            return {'message': '场次回顾已保存'}
        if op == 'backup':
            backup = job.client.request('/backup', {})
            folder = self.path.parent / 'package-backups'
            folder.mkdir(exist_ok=True)
            destination = folder / (request_id + '.json')
            destination.write_text(json.dumps({'hostBackup': backup, 'package': self.state}, ensure_ascii=False), encoding='utf-8')
            return {'host': backup, 'packageFile': str(destination), 'message': '宿主备份与包侧记录均已保存'}
        if op == 'rules.install':
            content = bundle()
            revision = job.command('stage', 'rule.stage', {'sources': content['sources'], 'data': content['data']})
            job.command('activate', 'rule.activate', {'revision': revision})
            self.sync_automation(job, session)
            self.state['ruleRevisions'][revision] = {'sources': content['sources'], 'data': content['data']}
            self.state['activeRevision'] = revision
            self.game = content['data']['game.json']
            return {'revision': revision}
        if op == 'rules.stage':
            content = self.validate_bundle(args.get('bundle'))
            revision = job.command('stage', 'rule.stage', content)
            self.state['ruleRevisions'][revision] = content
            return {'revision': revision, 'message': '检查通过，尚未激活'}
        if op == 'rules.preview':
            require(args.get('revision') in self.state['ruleRevisions'], '修订不存在')
            return job.client.request('/preview', {'revision': args['revision'], 'rule': args.get('rule', 'sv.layout'), 'input': args.get('input', {})})
        if op == 'rules.activate':
            revision = args.get('revision')
            require(revision in self.state['ruleRevisions'], '修订不存在')
            job.command('activate', 'rule.activate', {'revision': revision})
            self.state['activeRevision'] = revision
            self.game = self.state['ruleRevisions'][revision]['data']['game.json']
            return {'revision': revision, 'message': '规则修订已激活'}
        raise PackageError('未知行动')

    def initialize(self, job):
        if self.state['initialized']:
            return {'message': '配置包已安装'}
        content = bundle()
        revision = job.command('stage', 'rule.stage', {'sources': content['sources'], 'data': content['data']})
        job.command('activate', 'rule.activate', {'revision': revision})
        self.state['ruleRevisions'][revision] = {'sources': content['sources'], 'data': content['data']}
        self.state['activeRevision'] = revision
        for config in content['configurations']:
            job.command(config['configurationId'], 'configuration.put', config)
        job.command('session', 'entity.create', {'configurationId': 'sv.session', 'name': '树桩镇探索', 'owner': 'kp', 'visibility': 'public'})
        job.command('world', 'entity.create', {'configurationId': 'sv.world', 'name': '主持世界记录', 'owner': 'kp', 'visibility': 'kp'})
        values = {**scenes.DEFAULTS, **scenes.package_numbers(self.state)}
        self.state['sceneId'] = job.command('scene', 'entity.create', {'configurationId': 'sv.scene',
            'name': '树桩镇机关与有限库存', 'owner': 'kp', 'visibility': 'kp', 'numbers': values})
        self.state['sceneState'] = values
        for location in self.game['locations']:
            job.command('location-' + str(location['index']), 'entity.create', {'configurationId': 'sv.location',
                'name': location['name'], 'owner': 'kp', 'visibility': 'public' if location['index'] == 1 else 'kp', 'numbers': {'index': location['index']}})
        first = self.state['locations']['1']
        self.state['published']['1'] = {k: copy.deepcopy(first[k]) for k in ('index', 'name', 'description', 'exits', 'features', 'clues')}
        for npc in self.game['npcs']:
            if not npc['verified']:
                continue
            numbers = {k: npc[k] for k in ('str', 'dex', 'wil', 'hp', 'armor', 'location')}
            numbers.update(strMax=npc['str'], dexMax=npc['dex'], wilMax=npc['wil'], maxHp=npc['hp'])
            entity = job.command('npc-' + npc['key'], 'entity.create', {'configurationId': 'sv.npc', 'name': npc['name'], 'owner': 'kp', 'visibility': 'kp', 'numbers': numbers})
            self.state['npcs'][npc['key']] = entity
        for member in job.client.request('/chat/members')['items']:
            if member['role'] == 'player':
                job.command('draft-' + member['accountId'], 'entity.create', {'configurationId': 'sv.draft', 'name': '建角骰盘',
                    'owner': member['accountId'], 'visibility': 'owner'})
        self.state['initialized'] = True
        return {'message': '十地点与规则已安装', 'revision': revision}

    def approve(self, job, view, args):
        account = args.get('account')
        draft = self.state['drafts'].get(account)
        require(draft is not None, '未找到角色草稿')
        if args.get('reject'):
            draft['status'] = 'rejected'
            draft['reason'] = str(args.get('reason', '请修改草稿'))[:2000]
            return {'message': '已退回草稿'}
        existing = next((x for x in self.entities(view, 'sv.character') if x['owner'] == account), None)
        if existing and 'create' not in job.record['steps']:
            raise PackageError('该玩家已有角色')
        entity = job.command('create', 'entity.create', {'configurationId': 'sv.character', 'name': draft['name'], 'owner': account, 'visibility': 'owner'})
        job.invoke('profile', 'sv.profile', actor=entity, strength=draft['str'], dexterity=draft['dex'], will=draft['wil'], hp=draft['hp'], pips=draft['pips'])
        for position, item in enumerate(draft['items']):
            definition = self.game['items'][item['item'] - 1]
            job.invoke('item-' + str(position), 'sv.grant', actor=entity, item=item['item'], slot=item['slot'], uses=definition['uses'])
        session = next(iter(self.entities(view, 'sv.session')))
        job.command('source', 'relation.set', {'sourceId': entity, 'targetId': session['instanceId'], 'relationType': 'source'})
        job.command('reference', 'relation.set', {'sourceId': session['instanceId'], 'targetId': entity, 'relationType': 'references'})
        self.state['bindings'][account] = entity
        self.state['roster'][account] = {'account': account, 'id': entity, 'name': draft['name']}
        draft['status'] = 'approved'
        return {'message': '角色审核通过', 'character': entity}
