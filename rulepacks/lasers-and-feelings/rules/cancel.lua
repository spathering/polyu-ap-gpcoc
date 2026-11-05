return rule('lf.cancel', {'actor'}, function(r, actor)
  assert(r.matches(actor, 'lf.action'), 'LF_NOT_ACTION')
  assert(r.number(actor, 'phase') ~= 3, 'LF_ALREADY_CANCELLED')
  for _, id in ipairs(r.related(actor, 'references')) do
    if r.number(id, 'role') == 1 then
      assert(r.number(id, 'state') == 0, 'LF_ALREADY_CONSUMED')
    end
  end
  r.set(actor, 'phase', 3)
  return {action=actor, cancelled=true}
end, {kp=true})
