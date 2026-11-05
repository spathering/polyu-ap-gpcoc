return rule('lf.open', {'actor'}, function(r, actor)
  assert(r.matches(actor, 'lf.action'), 'LF_NOT_ACTION')
  assert(r.number(actor, 'phase') == 0, 'LF_NOT_DRAFT')
  local participants, owners, main = r.related(actor, 'references'), {}, 0
  assert(#participants >= 1 and #participants <= 30, 'LF_PARTICIPANT_LIMIT')
  for _, id in ipairs(participants) do
    local c = r.call('lf.library', id, 'context', 0)
    assert(c.action == actor, 'LF_INVALID_BINDING')
    assert(c.role == 1 or c.role == 2, 'LF_INVALID_ROLE')
    if c.role == 1 then main = main + 1 end
    local owner = r.read(id).owner
    assert(owner and not owners[owner], 'LF_DUPLICATE_OWNER')
    owners[owner] = true
    assert(r.number(id, 'state') == 0, 'LF_USED_RECORD')
    local number = r.number(id, 'number')
    assert(number >= 2 and number <= 5 and number % 1 == 0, 'LF_INVALID_NUMBER')
    for _, key in ipairs({'mode', 'prepared', 'expert'}) do
      local value = r.number(id, key)
      assert(value == 0 or value == 1, 'LF_INVALID_CHOICE')
    end
  end
  assert(main == 1, 'LF_ONE_MAIN_REQUIRED')
  r.set(actor, 'phase', 1)
  return {action=actor, participants=participants}
end, {kp=true, dependencies={'lf.library'}})
