"""Read-only scene affordances. Never returns answers or undiscovered clues."""


def project_scene(service, actor, view, scenario, knowledge, legacy=None):
    n = actor['numbers']
    locations = {l['id']: l for l in scenario['locations']}
    loc = next((l for l in locations.values() if l['index'] == n['location']), None)
    if not loc:
        return None
    worlds = service.entities(view, 'md.world')
    w = worlds[0]['numbers'] if len(worlds) == 1 else {}
    automation = scenario.get('automation', {})
    searched = loc['id'] in knowledge.get('searched', [])
    held = service.held(view, actor)
    owned = {scenario['items'][i['numbers']['itemIndex'] - 1]['id'] for i in held if 1 <= i['numbers']['itemIndex'] <= len(scenario['items'])}
    age = (n['day'], n['slot'])
    now = (w.get('day', 1), w.get('slot', 1))
    used = n['slotUsed'] and age >= now
    intellect = n['intellect'] if n['day'] < now[0] else n['intellectRemaining']
    base = ('请 KP 建立唯一世界时钟' if not w else '调查已结束' if w.get('closed') else '角色尚未批准' if not n['approved'] else '角色已倒下，请联系 KP' if n['hp'] <= 0 else '角色时间超前，请联系 KP' if age > now else '')
    major = base or ('请先结束遭遇' if n['encounterActive'] else '请先完成待掷骰检定' if n['requestOpen'] else '本轮主要行动已完成，等待同伴或 KP 推进' if used else '')
    attempt_key = str(now[0]) + ':' + loc['id']
    attempts = knowledge.get('attempts', {}).get(attempt_key, 0)
    search_fee = '今日此处前两次侦察免费' if attempts < 2 else '智力额度 1'
    actions = []
    def action(kind, label, cost, reason='', **extra):
        actions.append({'kind': kind, 'label': label, 'cost': cost, 'reason': reason, 'available': not reason, **extra})
    action('explore', '探索当前场景', '主要行动 1 · 体力 1' if n['stamina'] > 0 else '主要行动 1 · 随机疲劳', major or ('追加侦察需要1智力额度' if attempts >= 2 and intellect <= 0 else ''))
    action('sleep', '休息恢复', '主要行动 1 · 恢复体力', major)
    action('wait', '原地等待', '主要行动 1', major)
    if searched:
        action('search', '再次侦察', search_fee, base or ('遭遇中不能侦察' if n['encounterActive'] else '请先完成待掷骰检定' if n['requestOpen'] else '今日智力额度已用完' if attempts >= 2 and intellect <= 0 else ''))
    if loc['index'] in (8, 12, 13):
        action('soothe', '安抚精神', '主要行动 1 · 清除惊扰', major)
    action('hint', '询问现场提示', '智力额度 1', base or ('今日智力额度已用完' if intellect <= 0 else ''))
    if n['requestOpen']:
        action('check', '完成待掷骰检定', '不额外占用主要行动', base)
    if n['encounterActive']:
        action('finish', '结束本人遭遇', '战后状态检查', base)

    known_indices = {x.get('index') if isinstance(x, dict) else x for x in knowledge.get('locations', [])}
    known_indices |= {x.get('index') if isinstance(x, dict) else x for x in (legacy or {}).get('locations', [])}
    explored = set(knowledge.get('searched', [])) & locations.keys()
    revealed = {l['id'] for l in locations.values() if l['index'] in known_indices}
    # Only this member's explored rooms expand the map, exactly one edge.
    # Current position remains an anchor even before the first exploration.
    visible = explored | {loc['id']}
    for source in explored:
        for target in locations[source]['adjacentIds']:
            if target == 'loc-basement' and not w.get('basementOpen') and target not in explored | revealed:
                continue
            visible.add(target)
    exits = []
    for target in locations.values():
        direct = target['id'] in loc['adjacentIds']
        via_hall = not direct and target['id'] != loc['id'] and loc['index'] <= 13 and target['index'] <= 13 and 'loc-hall' in loc['adjacentIds'] and 'loc-hall' in target['adjacentIds']
        if not direct and not via_hall:
            continue
        gate = ''
        if target['id'] == 'loc-basement' and not w.get('basementOpen'):
            if target['id'] not in explored | revealed:
                continue
            gate = '入口尚未开启'
        if {loc['id'], target['id']} == {'loc-west', 'loc-shore'} and not w.get('cliffOpen'):
            gate = '悬崖暗道尚未开启，可经走廊或村落前往海岸'
        reason = major or gate
        exits.append({'index': target['index'], 'id': target['id'], 'name': target['name'], 'via': '' if direct else '经一楼走廊', 'move': direct and not reason, 'explore': not reason, 'reason': reason, 'cost': '主要行动 1', 'exploreCost': '主要行动 1 · 体力 1（耗尽时承受疲劳）'})

    puzzles = []
    if searched:
        for p in scenario['puzzles']:
            route = automation.get('puzzles', {}).get(p['id'], {})
            if route.get('location') == loc['id']:
                solved = p['id'] in knowledge.get('puzzles', [])
                puzzles.append({k: p[k] for k in ('id', 'name', 'prompt')} | {'solved': solved, 'reason': base or ('已经解开' if solved else ''), 'available': not base and not solved})
    pickups = []
    if searched:
        for definition in scenario['items']:
            route = automation.get('items', {}).get(definition['id'])
            if not route or route['location'] != loc['id']:
                continue
            allocated = sum(max(1, int(i['numbers']['count'])) for i in service.entities(view, 'md.item') if i['numbers']['itemIndex'] == definition['index'])
            quota = sum(service.known(view, m['memberId']).get('loot', {}).get(attempt_key, 0) for m in view.get('_members', []))
            reason = base or ('已被领取，场景库存已分配完' if allocated >= definition['quantity'] else '需要先解开对应机关或侦察成功' if route.get('reward') and definition['id'] not in knowledge.get('rewards', []) else '需要' + next((i['name'] for i in scenario['items'] if i['id'] == route['requires']), '对应钥匙') if route.get('requires') and route['requires'] not in owned else '四个卡槽已满' if len(held) >= 4 else '全队今日在此已领取三件物品' if quota >= 3 else '需要 KP 处理剧情条件' if route.get('manual') else '')
            pickups.append({'index': definition['index'], 'name': definition['name'], 'effect': definition['effect'], 'available': not reason, 'reason': reason})
    clue_ids = {c['id'] for c in knowledge.get('clues', [])}
    if loc['id'] == 'loc-steward':
        action('open-maintenance', '拉动维修通道拉杆', '不额外占用主要行动', base or ('请先发现管家工作记录' if 'C4' not in clue_ids else '地下入口已经开放' if w.get('basementOpen') else ''))
        action('boat-key', '出示证据并承诺不再互杀', '本人明确承诺', base or ('请先取得选拔证据' if not clue_ids & {'C1', 'C2', 'C7'} else '船已获得使用权' if w.get('boatReady') else ''), choice='promise')
    if loc['id'] in ('loc-shore', 'loc-basement'):
        action('start-boat', '操作备用启动装置' if loc['id'] == 'loc-shore' else '启动归航船', '主要行动 1', major or ('请先探索当前场景' if not searched else '船已就绪' if w.get('boatReady') else ''))
    if loc['id'] == 'loc-basement':
        action('stop-tracking', '关闭追踪阵法', '主要行动 1', major or ('请先探索控制室' if not searched else '追踪已经关闭' if w.get('trackingOff') else ''))
    endings = []
    if now == (2, 8):
        for value, label in [('1', '归航'), ('2', '携证归航'), ('3', '留守'), ('4', '前往神界'), ('5', '困岛续章')]:
            reason = ('需要到达海岸且船已就绪' if value in ('1', '2') and (loc['id'] != 'loc-shore' or not w.get('boatReady')) else '需要持有选拔证据' if value == '2' and not clue_ids & {'C1', 'C2', 'C7'} else '招募尚未发布' if value == '4' and not w.get('offerMade') else '角色已倒下，请 KP 处理救援' if n['hp'] <= 0 else '')
            endings.append({'choice': value, 'label': label, 'available': not reason, 'reason': reason})
    nodes = [{k: l[k] for k in ('id', 'index', 'name')} | {'explored': l['id'] in explored} for l in locations.values() if l['id'] in visible]
    edges = []
    for l in locations.values():
        if l['id'] not in visible:
            continue
        for target in l['adjacentIds']:
            if target not in visible or l['id'] >= target:
                continue
            if l['id'] not in explored and target not in explored:
                continue
            blocked = ('loc-basement' in (l['id'], target) and not w.get('basementOpen')) or ({l['id'], target} == {'loc-west', 'loc-shore'} and not w.get('cliffOpen'))
            edges.append({'from': l['id'], 'to': target, 'blocked': bool(blocked)})
    return {'actor': actor['instanceId'], 'location': {k: loc[k] for k in ('id', 'index', 'name', 'description')}, 'searched': searched, 'attempts': attempts, 'actions': actions, 'exits': exits, 'puzzles': puzzles, 'items': pickups, 'endings': endings, 'map': {'nodes': nodes, 'edges': edges}}
