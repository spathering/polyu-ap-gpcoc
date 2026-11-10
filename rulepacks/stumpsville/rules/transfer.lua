return rule('sv.transfer', {'actor', 'target:actor', 'slot:amount', 'destination:amount'}, function(r, actor, target, slot, destination)
  assert(actor ~= target and r.matches(actor, 'sv.character') and r.matches(target, 'sv.character'), 'SV_TRANSFER_TARGET')
  assert(slot >= 1 and slot <= 20 and destination >= 1 and destination <= 20, 'SV_SLOT')
  local item = r.number(actor, 'item' .. slot)
  assert(item > 0 and r.number(target, 'item' .. destination) == 0, 'SV_SLOT_OCCUPIED')
  for _, prefix in ipairs({'item', 'uses', 'ticks'}) do
    r.set(target, prefix .. destination, r.number(actor, prefix .. slot))
    r.set(actor, prefix .. slot, 0)
  end
  if r.number(actor, 'litSlot') == slot then r.set(actor, 'litSlot', 0) end
  r.call('sv.layout', actor)
  local layout = r.call('sv.layout', target)
  return {item=item, recipient=target, slot=destination, overloaded=layout.overloaded}
end, {kp=true, dependencies={'sv.layout'}})
