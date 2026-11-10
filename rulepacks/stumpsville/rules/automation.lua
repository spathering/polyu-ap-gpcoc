return rule('sv.automation', {'actor'}, function(r, actor)
  assert(r.matches(actor, 'sv.character'), 'SV_NOT_CHARACTER')
  local links = r.related(actor, 'source')
  assert(#links == 1 and r.matches(links[1], 'sv.session'), 'SV_NOT_SESSION')
  assert((r.read(links[1]).numbers.autoResolve or 1) == 1, 'SV_KP_RULING_REQUIRED')
  return links[1]
end, {mode='calculation', public=false})
