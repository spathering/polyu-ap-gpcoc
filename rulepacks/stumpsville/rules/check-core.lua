return rule('sv.check.core', {'actor', 'attribute:text', 'mode:text'}, function(r, actor, attribute, mode)
  assert(r.matches(actor, 'sv.character'), 'SV_NOT_CHARACTER')
  assert(r.number(actor, 'approved') == 1, 'SV_NOT_APPROVED')
  assert(r.number(actor, 'ready') == 1, 'SV_NOT_READY')
  assert(r.number(actor, 'incapacitated') == 0 and r.number(actor, 'str') > 0 and r.number(actor, 'dex') > 0 and r.number(actor, 'wil') > 0, 'SV_CANNOT_ACT')
  assert(attribute == 'str' or attribute == 'dex' or attribute == 'wil', 'SV_ATTRIBUTE')
  assert(mode == 'normal' or mode == 'advantage' or mode == 'disadvantage', 'SV_CHECK_MODE')
  local links = r.related(actor, 'source')
  assert(#links == 1 and r.number(links[1], 'phase') == 1, 'SV_SESSION_NOT_STARTED')
  local layout = r.call('sv.layout', actor)
  if layout.overloaded or (layout.injured and (attribute == 'str' or attribute == 'dex')) then mode = 'disadvantage' end
  local first, second = r.roll(20), 0
  local rolled = first
  if mode ~= 'normal' then
    second = r.roll(20)
    if mode == 'advantage' then rolled = math.min(first, second) else rolled = math.max(first, second) end
  end
  local target = r.number(actor, attribute)
  local passed = rolled <= target
  r.set(actor, 'lastRoll', rolled)
  r.set(actor, 'checks', r.number(actor, 'checks') + 1)
  return {attribute=attribute, first=first, second=second, rolled=rolled, target=target, passed=passed, mode=mode}
end, {public=false, dependencies={'sv.layout'}})
