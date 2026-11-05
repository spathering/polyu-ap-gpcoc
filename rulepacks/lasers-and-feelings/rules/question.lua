return rule('lf.question', {'actor', 'question:text'}, function(r, actor, question)
  local c = r.call('lf.library', actor, 'context', 0)
  assert(r.number(c.action, 'phase') ~= 3, 'LF_CANCELLED')
  assert(r.number(actor, 'state') == 1 and r.number(actor, 'insights') > 0, 'LF_NO_INSIGHT')
  assert(r.number(actor, 'questionState') == 0, 'LF_QUESTION_ALREADY_SUBMITTED')
  assert(#question > 0, 'LF_EMPTY_QUESTION')
  r.set(actor, 'questionState', 1)
  return {action=c.action, participant=actor, question=question, kind='insight'}
end, {dependencies={'lf.library'}})
