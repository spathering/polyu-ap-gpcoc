return rule('sv.ready', {'actor', 'ready:choice'}, function(r, actor, ready)
  assert(r.matches(actor, 'sv.character') and r.number(actor, 'approved') == 1, 'SV_NOT_APPROVED')
  r.set(actor, 'ready', ready and 1 or 0)
  return {ready=ready}
end)
