return rule('sv.grant', {'actor', 'item:amount', 'slot:amount', 'uses:amount'}, function(r, actor, item, slot, uses)
  assert(r.matches(actor, 'sv.character'), 'SV_NOT_CHARACTER')
  assert(slot >= 1 and slot <= 20, 'SV_SLOT')
  local def = r.readData('game.json').items[item]
  assert(def and uses <= def.uses, 'SV_ITEM')
  assert(r.number(actor, 'item' .. slot) == 0, 'SV_SLOT_OCCUPIED')
  r.set(actor, 'item' .. slot, item)
  r.set(actor, 'uses' .. slot, uses)
  r.set(actor, 'ticks' .. slot, 0)
  local layout = r.call('sv.layout', actor)
  return {item=item, slot=slot, overloaded=layout.overloaded}
end, {kp=true, dependencies={'sv.layout'}})
