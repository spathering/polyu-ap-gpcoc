return rule('sv.inventory.core', {'actor', 'operation:text', 'slot:amount', 'value:amount'}, function(r, actor, operation, slot, value)
  assert(r.matches(actor, 'sv.character'), 'SV_NOT_CHARACTER')
  assert(slot >= 1 and slot <= 20, 'SV_SLOT')
  local data = r.readData('game.json')
  local index = r.number(actor, 'item' .. slot)
  assert(index > 0 and data.items[index], 'SV_EMPTY_SLOT')
  local def = data.items[index]
  if operation == 'move' then
    assert(value >= 1 and value <= 20 and value ~= slot, 'SV_TARGET_SLOT')
    assert(r.number(actor, 'item' .. value) == 0, 'SV_SLOT_OCCUPIED')
    local uses = r.number(actor, 'uses' .. slot)
    local ticks = r.number(actor, 'ticks' .. slot)
    r.set(actor, 'item' .. slot, 0)
    r.set(actor, 'uses' .. slot, 0)
    r.set(actor, 'ticks' .. slot, 0)
    r.set(actor, 'item' .. value, index)
    r.set(actor, 'uses' .. value, uses)
    r.set(actor, 'ticks' .. value, ticks)
    if r.number(actor, 'litSlot') == slot then r.set(actor, 'litSlot', value) end
  elseif operation == 'use' then
    assert(def.uses > 0 and def.kind ~= 'condition' and def.kind ~= 'spell', 'SV_ITEM_NO_USES_OR_MANUAL_SPELL')
    local uses = r.number(actor, 'uses' .. slot)
    assert(uses > 0, 'SV_ITEM_EXHAUSTED')
    local consumed = 1
    if def.useDie then consumed = r.roll(6) >= 4 and 1 or 0 end
    r.set(actor, 'uses' .. slot, uses - consumed)
    if uses - consumed == 0 and r.number(actor, 'litSlot') == slot then r.set(actor, 'litSlot', 0) end
  elseif operation == 'light' then
    assert(def.light == true and r.number(actor, 'uses' .. slot) > 0, 'SV_NOT_LIGHT_SOURCE')
    r.set(actor, 'litSlot', slot)
  elseif operation == 'extinguish' then
    assert(r.number(actor, 'litSlot') == slot, 'SV_NOT_LIT')
    r.set(actor, 'litSlot', 0)
  else
    error('SV_INVENTORY_OPERATION')
  end
  local layout = r.call('sv.layout', actor)
  return {operation=operation, slot=slot, target=value, uses=r.number(actor, 'uses' .. slot), overloaded=layout.overloaded}
end, {public=false, dependencies={'sv.layout'}})
