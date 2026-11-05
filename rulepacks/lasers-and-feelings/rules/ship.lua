return rule('lf.ship', {'actor', 'first:amount', 'second:amount', 'problem:amount'}, function(r, actor, first, second, problem)
  assert(r.matches(actor, 'lf.ship'), 'LF_NOT_SHIP')
  assert(first >= 1 and first <= 7 and second >= 1 and second <= 7 and first ~= second, 'LF_INVALID_STRENGTHS')
  assert(problem >= 1 and problem <= 4, 'LF_INVALID_PROBLEM')
  r.set(actor, 'first', first)
  r.set(actor, 'second', second)
  r.set(actor, 'problem', problem)
  return {ship=actor, first=first, second=second, problem=problem}
end, {kp=true})
