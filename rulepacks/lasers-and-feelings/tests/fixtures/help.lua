return rule('lf.probe.help', {'actor'}, function(r, actor)
  local p = r.readData('probe.json')
  assert(p.helpers[actor], 'NOT_PARTICIPANT')
  assert(r.number(p.coordinator, 'phase') == 0, 'HELP_CLOSED')
  assert(r.number(p.coordinator, 'version') == 1, 'STALE_ACTION')
  assert(r.number(actor, 'submitted') == 0, 'ALREADY_SUBMITTED')
  -- Also checks control of this participant record before requesting randomness.
  r.set(actor, 'submitted', 1)
  local result = r.call('lf.probe.roll', actor)
  r.set(actor, 'successes', result.successes)
  r.set(actor, 'insights', result.insights)
  return result
end, {dependencies={'lf.probe.roll'}})
