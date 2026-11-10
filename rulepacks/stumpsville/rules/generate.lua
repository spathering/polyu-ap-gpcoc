return rule('sv.generate', {'actor', 'kind:text'}, function(r, actor, kind)
  assert(r.matches(actor, 'sv.world'), 'SV_NOT_WORLD')
  local results = {}
  if kind == 'character' then
    for _, key in ipairs({'str', 'dex', 'wil'}) do
      local a, b, c = r.roll(6), r.roll(6), r.roll(6)
      results[key] = a + b + c - math.min(a, math.min(b, c))
    end
    results.hp = r.roll(6)
    results.pips = r.roll(6)
  elseif kind == 'pots' then
    assert(r.number(actor, 'generated4') == 0, 'SV_ALREADY_GENERATED')
    results.count = r.roll(6)
    r.set(actor, 'pots', results.count)
    r.set(actor, 'generated4', 1)
  elseif kind == 'rats' then
    assert(r.number(actor, 'generated7') == 0, 'SV_ALREADY_GENERATED')
    results.count = r.roll(6) + r.roll(6)
    r.set(actor, 'rats', results.count)
    r.set(actor, 'generated7', 1)
  elseif kind == 'encounter' or kind == 'encounter-table' then
    results.rolled = r.roll(6)
  elseif kind == 'reaction' then
    results.first = r.roll(6)
    results.second = r.roll(6)
    results.total = results.first + results.second
  elseif kind == 'loot' then
    results.rolled = r.roll(20)
  else error('SV_GENERATE_KIND') end
  return results
end, {kp=true})
