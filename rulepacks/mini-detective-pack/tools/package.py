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


def prepare_presets(client):
    """Create missing account presets; reuse existing actors without resetting gameplay."""
    content=bundle()
    view=client.request('/view')
    if not any(a['id']=='md.check' for a in view['catalog']['actions']):
        install(client)
    scenario=content['data']['scenario.json']
    result=[]
    view=client.request('/view')
    if not any(e['configurationId']=='md.world' for e in view['entities'].values()):
        client.command('entity.create',{'configurationId':'md.world','owner':'kp','visibility':'public','name':'孤岛归航 · 世界时钟'})
    for i,preset in enumerate(scenario['presets']):
        account='player'+str(i+1)
        view=client.request('/view')
        existing=next((e for e in view['entities'].values() if e['configurationId']=='md.character' and e['owner']==account and e['lifecycle']=='active'),None)
        if existing:
            result.append({'account':account,'character':existing['instanceId'],'name':existing['name'],'created':False})
            continue
        actor=client.command('entity.create',{'configurationId':'md.character','owner':account,'visibility':'owner','name':preset['name'],'numbers':{'talent':preset['talentIndex']}})
        client.invoke('md.profile',actor=actor,**preset['attributes'])
        for item_id in preset['startingItemIds']:
            index=next(j+1 for j,item in enumerate(scenario['items']) if item['id']==item_id)
            definition=scenario['items'][index-1]
            item=client.command('entity.create',{'configurationId':'md.item','owner':account,'visibility':'owner','name':definition['name'],'numbers':{'itemIndex':index}})
            client.command('relation.set',{'sourceId':item,'targetId':actor,'relationType':'source'})
            client.command('relation.set',{'sourceId':actor,'targetId':item,'relationType':'references'})
            client.invoke('md.confirm',actor=item)
        result.append({'account':account,'character':actor,'name':preset['name'],'created':True})
    return result

