import copy
import json
import os
import time
import uuid
from collections import deque
from pathlib import Path


def pointer(s):
    return str(s).replace('~', '~0').replace('/', '~1')


class Observer:
    def __init__(self, limit=2000):
        self.limit = limit
        self.reset()

    def reset(self):
        self.baselines = {}
        self.records = deque()
        self.bytes = 0
        self.dropped = 0
        self.segment = uuid.uuid4().hex

    def sample(self, source, value):
        value = {k: v for k, v in value.items() if k not in ('runtime', 'metrics', 'store', 'audit')}
        if source in self.baselines:
            self._diff(source, '', self.baselines[source], True, value, True)
        self.baselines[source] = copy.deepcopy(value)

    def _diff(self, source, path, a, exists_a, b, exists_b):
        if exists_a and exists_b and a == b:
            return
        if exists_a and exists_b and isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(a.keys() | b.keys()):
                if key != 'viewToken':
                    self._diff(source, path + '/' + pointer(key), a.get(key), key in a, b.get(key), key in b)
            return
        row = dict(observationId=uuid.uuid4().hex, sessionId=self.segment, source=source,
                   receivedAt=time.strftime('%Y-%m-%d %H:%M:%S'), path=path,
                   kind='不再可见' if not exists_b else '首次可见' if not exists_a else '变化',
                   beforePresent=exists_a, before=a, afterPresent=exists_b, after=b)
        size = len(json.dumps(row, ensure_ascii=False).encode())
        self.records.append((row, size))
        self.bytes += size
        while len(self.records) > self.limit or self.bytes > 16 * 1024 * 1024:
            self.bytes -= self.records.popleft()[1]
            self.dropped += 1


class Settings:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'python-settings.json'
        try:
            self.data = json.loads(self.path.read_text('utf-8'))
        except (OSError, ValueError):
            self.data = {'watches': [], 'commands': []}
            legacy = self.directory / 'settings.json'
            if legacy.exists() and not self.path.exists():
                try:
                    old = json.loads(legacy.read_text('utf-8-sig'))
                    for watch in old.get('watches', [])[:100]:
                        watch = dict(watch)
                        watch['endpoint'] = watch.get('endpoint', '').rstrip('/')
                        watch['path'] = '/' + pointer(watch.pop('collection', '')) + '/' + pointer(watch.pop('objectId', '')) + watch.get('path', '')
                        self.data['watches'].append(watch)
                    for command in old.get('commands', [])[:200]:
                        command = dict(command)
                        command['endpoint'] = command.get('endpoint', '').rstrip('/')
                        self.data['commands'].append(command)
                except (OSError, ValueError, TypeError):
                    pass
        self.data['watches'] = self.data.get('watches', [])[:100]
        self.data['commands'] = self.data.get('commands', [])[:200]

    def save(self):
        temp = self.path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        temp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, self.path)

    def remember(self, context, envelope):
        self.data['commands'].insert(0, {**context, 'commandId': envelope['payload']['commandId'], 'op': envelope['payload']['op']})
        self.data['commands'] = self.data['commands'][:200]
        self.save()
