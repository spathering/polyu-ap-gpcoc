"""Read-only package composition and documented management operations."""
import json
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent


def bundle():
    manifest = json.loads((PACK / 'manifest.json').read_text(encoding='utf-8'))
    return {'manifest': manifest,
            'sources': {name: (PACK / 'rules' / name).read_text(encoding='utf-8')
                        for name in manifest['rules']},
            'data': {name: json.loads((PACK / 'config' / name).read_text(encoding='utf-8'))
                     for name in manifest['data']},
            'configurations': json.loads((PACK / manifest['configurations']).read_text(encoding='utf-8'))}


def install(client):
    content = bundle()
    revision = client.command('rule.stage', {'sources': content['sources'], 'data': content['data']})
    client.command('rule.activate', {'revision': revision})
    for config in content['configurations']:
        client.command('configuration.put', config)
    return revision


def character(client, owner, name, number=3, style=1, job=1, goal=1):
    entity = client.command('entity.create', {'configurationId': 'lf.character',
                                            'owner': owner, 'name': name, 'visibility': 'public'})
    client.invoke('lf.profile', actor=entity, number=number, style=style, job=job, goal=goal)
    return entity


def action(client, title, slots):
    """Build while draft, then publish atomically with lf.open; no rule revision changes."""
    view = client.request('/view')
    coordinator = client.command('entity.create', {'configurationId': 'lf.action',
                                                  'owner': view['accountId'], 'name': title, 'visibility': 'public'})
    participants = []
    for i, slot in enumerate(slots):
        source = view['entities'][slot['character']]
        participant = client.command('entity.create', {
            'configurationId': 'lf.participant', 'name': source['name'], 'owner': source['owner'],
            'visibility': 'public', 'numbers': {'role': 1 if i == 0 else 2,
                'number': source['numbers']['number'], 'mode': slot.get('mode', 0),
                'prepared': slot.get('prepared', 0), 'expert': slot.get('expert', 0)}})
        for origin, target, kind in [(participant, coordinator, 'references'),
                                     (participant, source['instanceId'], 'source'),
                                     (coordinator, participant, 'references')]:
            client.command('relation.set', {'sourceId': origin, 'targetId': target, 'relationType': kind})
        participants.append(participant)
    client.invoke('lf.open', actor=coordinator)
    return coordinator, participants
