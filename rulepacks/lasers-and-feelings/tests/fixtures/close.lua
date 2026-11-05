return rule('lf.probe.close', {'actor'}, function(r, actor)
  local p = r.readData('probe.json')
  assert(actor == p.coordinator, 'WRONG_ACTION')
  assert(r.number(actor, 'phase') == 0, 'ALREADY_CLOSED')
  local bonus = 0
  for helper, _ in pairs(p.helpers) do
    assert(r.number(helper, 'submitted') == 1, 'HELP_PENDING')
    if r.number(helper, 'successes') > 0 then bonus = bonus + 1 end
  end
  r.set(actor, 'bonus', bonus)
  r.set(actor, 'phase', 1)
  return {bonus=bonus}
end, {kp=true})
