return rule('lf.probe.roll', {'actor'}, function(r, actor)
  local n = r.number(actor, 'number')
  local mode = r.number(actor, 'mode')
  local count = r.number(actor, 'dice')
  assert(n >= 2 and n <= 5 and n % 1 == 0, 'INVALID_NUMBER')
  assert(mode == 0 or mode == 1, 'INVALID_MODE')
  assert(count >= 1 and count <= 5 and count % 1 == 0, 'INVALID_DICE')
  local dice, successes, insights = {}, 0, 0
  for i = 1, count do
    local d = r.roll(6)
    dice[i] = d
    if d == n then insights = insights + 1 end
    if d == n or (mode == 0 and d < n) or (mode == 1 and d > n) then
      successes = successes + 1
    end
  end
  return {dice=dice, successes=successes, insights=insights}
end, {public=false})
