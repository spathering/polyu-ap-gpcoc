return rule('lf.answer', {'actor'}, function(r, actor)
  local c = r.call('lf.library', actor, 'context', 0)
  assert(r.number(actor, 'questionState') == 1, 'LF_NO_PENDING_QUESTION')
  r.set(actor, 'questionState', 2)
  return {action=c.action, participant=actor, answered=true}
end, {kp=true, dependencies={'lf.library'}})
