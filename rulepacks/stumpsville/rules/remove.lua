return rule('sv.remove', {'actor', 'slot:amount'}, function(r, actor, slot)
  assert(r.matches(actor, 'sv.character') and slot >= 1 and slot <= 20, 'SV_SLOT')
  local item = r.number(actor, 'item' .. slot)
  assert(item > 0, 'SV_EMPTY_SLOT')
  for _, prefix in ipairs({'item', 'uses', 'ticks'}) do r.set(actor, prefix .. slot, 0) end
  if r.number(actor, 'litSlot') == slot then r.set(actor, 'litSlot', 0) end
  return {removed=item, slot=slot}
end, {kp=true})
