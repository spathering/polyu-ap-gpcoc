return rule('lf.main', {'actor'}, function(r, actor)
  local c = r.call('lf.library', actor, 'context', 0)
  assert(c.role == 1, 'LF_NOT_MAIN')
  assert(r.number(c.action, 'phase') == 2, 'LF_NOT_CLOSED')
  assert(r.number(actor, 'state') == 0, 'LF_ALREADY_CONSUMED')
  local main = 0
  for _, id in ipairs(r.related(c.action, 'references')) do
    if r.number(id, 'role') == 1 then
      assert(id == actor, 'LF_INVALID_BINDING')
      main = main + 1
    end
  end
  assert(main == 1, 'LF_ONE_MAIN_REQUIRED')
  r.set(actor, 'state', 1)
  return r.call('lf.library', actor, 'roll', 1 + r.number(actor, 'prepared')
                + r.number(actor, 'expert') + r.number(c.action, 'bonus'))
end, {dependencies={'lf.library'}})
