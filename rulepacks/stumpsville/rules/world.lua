return rule('sv.world', {'actor', 'operation:text', 'value:amount'}, function(r, actor, operation, value)
  assert(r.matches(actor, 'sv.session'), 'SV_NOT_SESSION')
  if operation == 'start' then
    r.set(actor, 'phase', 1)
  elseif operation == 'round' then
    assert(r.number(actor, 'phase') == 1, 'SV_SESSION_NOT_STARTED')
    assert(value == r.number(actor, 'round'), 'SV_ROUND_CONFLICT')
    local characters = r.related(actor, 'references')
    local lights = {}
    for _, id in ipairs(characters) do
      if r.matches(id, 'sv.character') then
        local slot = r.number(id, 'litSlot')
        if slot > 0 then
          local ticks = r.number(id, 'ticks' .. slot) + 1
          if ticks >= 6 then
            local uses = math.max(0, r.number(id, 'uses' .. slot) - 1)
            r.set(id, 'uses' .. slot, uses)
            ticks = 0
            if uses == 0 then r.set(id, 'litSlot', 0) end
            lights[#lights + 1] = {actor=id, slot=slot, uses=uses}
          end
          r.set(id, 'ticks' .. slot, ticks)
        end
      end
    end
    r.set(actor, 'round', value + 1)
    return {round=value + 1, lights=lights, encounterDue=(value + 1)%3==0}
  elseif operation == 'finish' then
    r.set(actor, 'phase', 2)
  else error('SV_WORLD_OPERATION') end
  return {phase=r.number(actor, 'phase'), round=r.number(actor, 'round')}
end, {kp=true})
