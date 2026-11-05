return rule('lf.close', {'actor'}, function(r, actor)
  assert(r.matches(actor, 'lf.action'), 'LF_NOT_ACTION')
  assert(r.number(actor, 'phase') == 1, 'LF_HELP_CLOSED')
  local bonus, main = 0, 0
  for _, id in ipairs(r.related(actor, 'references')) do
    local c = r.call('lf.library', id, 'context', 0)
    assert(c.action == actor, 'LF_INVALID_BINDING')
    if c.role == 1 then
      main = main + 1
      assert(r.number(id, 'state') == 0, 'LF_ALREADY_CONSUMED')
    elseif c.role == 2 then
      if r.number(id, 'state') == 1 and r.number(id, 'successes') > 0 then bonus = bonus + 1 end
    else error('LF_INVALID_ROLE') end
  end
  assert(main == 1, 'LF_ONE_MAIN_REQUIRED')
  assert(bonus <= 29, 'LF_PARTICIPANT_LIMIT')
  r.set(actor, 'bonus', bonus)
  r.set(actor, 'phase', 2)
  return {action=actor, bonus=bonus}
end, {kp=true, dependencies={'lf.library'}})
