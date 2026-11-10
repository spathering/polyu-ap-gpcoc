return rule('sv.create', {'actor'}, function(r, actor)
  assert(r.matches(actor, 'sv.draft'), 'SV_NOT_DRAFT')
  local values = {}
  for _, key in ipairs({'str', 'dex', 'wil'}) do
    local a, b, c = r.roll(6), r.roll(6), r.roll(6)
    values[key] = a + b + c - math.min(a, math.min(b, c))
    r.set(actor, key, values[key])
  end
  values.hp, values.pips = r.roll(6), r.roll(6)
  r.set(actor, 'hp', values.hp)
  r.set(actor, 'pips', values.pips)
  r.set(actor, 'generation', r.number(actor, 'generation') + 1)
  return values
end)
