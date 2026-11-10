return rule('sv.rest', {'actor', 'kind:text', 'attribute:text'}, function(r, actor, kind, attribute)
  assert(r.matches(actor, 'sv.character'), 'SV_NOT_CHARACTER')
  assert(r.number(actor, 'str') > 0, 'SV_DEAD_CANNOT_REST')
  if kind == 'short' then
    local healing = r.roll(6) + 1
    r.set(actor, 'hp', math.min(r.number(actor, 'maxHp'), r.number(actor, 'hp') + healing))
    r.set(actor, 'incapacitated', 0)
  elseif kind == 'long' then
    assert(attribute == 'str' or attribute == 'dex' or attribute == 'wil', 'SV_ATTRIBUTE')
    local full = r.number(actor, 'hp') == r.number(actor, 'maxHp')
    r.set(actor, 'hp', r.number(actor, 'maxHp'))
    if full then
      r.set(actor, attribute, math.min(r.number(actor, attribute .. 'Max'), r.number(actor, attribute) + r.roll(6)))
    end
  elseif kind == 'full' then
    r.set(actor, 'hp', r.number(actor, 'maxHp'))
    for _, key in ipairs({'str', 'dex', 'wil'}) do r.set(actor, key, r.number(actor, key .. 'Max')) end
    r.set(actor, 'incapacitated', 0)
    r.set(actor, 'conditionPending', 0)
  else error('SV_REST_KIND') end
  local items = r.readData('game.json').items
  for slot=1,20 do
    local item = items[r.number(actor, 'item' .. slot)]
    if item and item.kind == 'condition' and (kind == 'full' or item.id == 'frightened' or (kind == 'long' and item.id == 'exhausted')) then
      r.set(actor, 'item' .. slot, 0)
      r.set(actor, 'uses' .. slot, 0)
      r.set(actor, 'ticks' .. slot, 0)
    end
  end
  return {kind=kind, hp=r.number(actor, 'hp')}
end, {kp=true})
