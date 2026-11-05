return rule('lf.library', {'actor', 'operation:text', 'count:amount'}, function(r, actor, operation, count)
  local function require_integer(n, low, high)
    assert(n % 1 == 0 and n >= low and n <= high, 'LF_INVALID_NUMBER')
  end
  if operation == 'context' then
    assert(r.matches(actor, 'lf.participant'), 'LF_NOT_PARTICIPANT')
    local coordinators = r.related(actor, 'references')
    local characters = r.related(actor, 'source')
    assert(#coordinators == 1 and #characters == 1, 'LF_INVALID_BINDING')
    local action, character = coordinators[1], characters[1]
    assert(r.matches(action, 'lf.action') and r.matches(character, 'lf.character'), 'LF_INVALID_BINDING')
    assert(r.read(actor).owner == r.read(character).owner, 'LF_OWNER_CHANGED')
    assert(r.number(actor, 'version') == r.number(action, 'version'), 'LF_STALE_ACTION')
    local found = false
    for _, id in ipairs(r.related(action, 'references')) do
      if id == actor then found = true end
    end
    assert(found, 'LF_NOT_REGISTERED')
    return {action=action, character=character, role=r.number(actor, 'role')}
  elseif operation == 'roll' then
    require_integer(count, 1, 32)
    local n, mode = r.number(actor, 'number'), r.number(actor, 'mode')
    require_integer(n, 2, 5)
    require_integer(mode, 0, 1)
    local dice, successes, insights = {}, 0, 0
    for i = 1, count do
      local d = r.roll(6)
      dice[i] = d
      r.set(actor, 'die' .. i, d)
      if d == n then insights = insights + 1 end
      if d == n or (mode == 0 and d < n) or (mode == 1 and d > n) then
        successes = successes + 1
      end
    end
    r.set(actor, 'dice', count)
    r.set(actor, 'successes', successes)
    r.set(actor, 'insights', insights)
    return {participant=actor, dice=dice, number=n, mode=mode,
            successes=successes, insights=insights, tier=math.min(successes, 3)}
  end
  error('LF_UNKNOWN_OPERATION')
end, {public=false})
