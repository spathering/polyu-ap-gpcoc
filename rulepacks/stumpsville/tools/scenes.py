"""Finite scene recipes and owner-filtered projections; no host implementation imports."""
import copy


DEFAULTS = dict(trapKnown=0, trapState=0, cheese1=1, gateKnown=0, gateTrap=0, gateOpen=0,
    poolKnown=0, moneyRemaining=140, idolRemaining=1, laddersKnown=0, potsKnown=0, potsRemaining=0,
    paintingRead=0, webKnown=0, villagersContacted=0, villagersFreed=0, spidersAlert=0,
    ratsObserved=0, ratsTalked=0, ratsDeal=0, ratsAlert=0, hallDoor=0, fluteRemaining=1,
    factoryKnown=0, paddleRemaining=1, clothRemaining=1, roofKnown=0, ironOpen=0,
    snakeKnown=0, snakeCalmed=0, snakeAlert=0, caveOpen=0,
    agingKnown=0, cheese10=8, ernieKnown=0, ernieAwake=0, ernieSpoken=0, northKnown=0)
STOCKS = [(1, 6, 'cheese1'), (3, 7, 'idolRemaining'), (4, 8, 'potsRemaining'),
          (7, 9, 'fluteRemaining'), (8, 10, 'paddleRemaining'), (8, 11, 'clothRemaining'), (10, 6, 'cheese10')]
DOORS = {'2-3': 'gateOpen', '7-8': 'hallDoor', '8-9': 'ironOpen', '9-10': 'caveOpen'}


def package_numbers(state):
    values = {}
    for location, item, key in STOCKS:
        values[key] = next((x['count'] for x in state['locations'][str(location)]['stock'] if x['item'] == item), 0)
    values['moneyRemaining'] = state['locations']['3'].get('pips', 0)
    values.update({key: int(state['doors'][edge] == 'open') for edge, key in DOORS.items()})
    return values


def apply_numbers(state, numbers):
    state['sceneState'] = copy.deepcopy(numbers)
    for location, item, key in STOCKS:
        stock = state['locations'][str(location)]['stock']
        row = next((x for x in stock if x['item'] == item), None)
        if row is None:
            stock.append({'item': item, 'count': numbers[key]})
        else:
            row['count'] = numbers[key]
    state['locations']['3']['pips'] = numbers['moneyRemaining']


def public_state(state, location, items):
    """Only discovered facts in the current room, never the full private scene state."""
    n = state.get('sceneState', {})
    facts, supplies = [], []
    def fact(condition, label, value):
        if condition:
            facts.append({'label': label, 'value': value})
    if location == 1:
        fact(n.get('trapKnown') or n.get('trapState'), '入口机关', ['已识别，尚未解除', '已解除', '已触发，不会重复触发'][n.get('trapState', 0)])
        known = n.get('trapKnown') or n.get('trapState')
    elif location == 2:
        fact(n.get('gateKnown') or n.get('gateOpen'), '石板门', '已打开' if state['doors']['2-3'] == 'open' else '关闭')
        fact(n.get('gateTrap'), '倾倒机关', '已解除' if n.get('gateTrap') == 1 else '已触发')
        known = False
    elif location == 3:
        fact(n.get('poolKnown'), '池底钱币', str(state['locations']['3'].get('pips', 0)) + 'p')
        fact(n.get('laddersKnown'), '庭院路线', '已辨认并加入地图')
        known = n.get('poolKnown')
    elif location == 4:
        fact(n.get('potsKnown'), '器具', '已整理；数量不会重复生成')
        known = n.get('potsKnown')
    elif location == 5:
        fact(n.get('paintingRead'), '节庆画', '已阅读')
        known = False
    elif location == 6:
        fact(n.get('webKnown'), '屋内危险', '两只蜘蛛')
        fact(n.get('villagersContacted') or n.get('villagersFreed'), '村民', '已撤到庭院' if n.get('villagersFreed') else '已取得联系，仍受束缚')
        fact(n.get('spidersAlert'), '蜘蛛', '警觉')
        known = False
    elif location == 7:
        fact(n.get('ratsObserved'), '鼠帮', '已达成约定' if n.get('ratsDeal') else '保持戒备' if n.get('ratsAlert') else '已观察')
        known = n.get('ratsObserved')
    elif location == 8:
        fact(n.get('factoryKnown'), '工厂设备', '已检查并取得工具许可')
        fact(n.get('roofKnown'), '出口', '门、升降机与屋顶货口已记录')
        known = n.get('factoryKnown')
    elif location == 9:
        fact(n.get('snakeKnown'), '守卫蛇', '平静' if n.get('snakeCalmed') else '警觉' if n.get('snakeAlert') else '守在铁门附近')
        fact(n.get('caveOpen'), '洞窟铁门', '已开放')
        known = False
    elif location == 10:
        fact(n.get('ernieKnown') or n.get('ernieAwake'), 'Ernie', '已交谈并取得许可' if n.get('ernieSpoken') else '醒来' if n.get('ernieAwake') else '熟睡')
        fact(n.get('northKnown'), '后续调查', '北方据点线索已取得')
        known = n.get('agingKnown') or n.get('ernieSpoken')
    else:
        known = False
    if known:
        for row in state['locations'][str(location)]['stock']:
            supplies.append({'name': items[row['item']-1]['name'], 'count': row['count']})
    return {'facts': facts, 'supplies': supplies}
