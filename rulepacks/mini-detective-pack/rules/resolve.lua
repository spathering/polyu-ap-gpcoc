return rule('md.resolve', {'actor','kind:text','destination:amount'}, function(r,actor,kind,destination)
  assert(r.matches(actor,'md.character') and r.number(actor,'approved')==1,'MD_NOT_APPROVED')
  assert(r.number(actor,'hp')>0,'MD_DOWNED')
  if kind=='hint' then
    assert(r.number(actor,'intellectRemaining')>0,'MD_NO_INTELLECT')
    r.set(actor,'intellectRemaining',r.number(actor,'intellectRemaining')-1)
    return {character=actor,kind=kind}
  end
  assert(r.number(actor,'slotUsed')==0,'MD_SLOT_USED')
  assert(kind=='explore' or kind=='move' or kind=='sleep' or kind=='soothe' or kind=='wait','MD_UNKNOWN_ACTION')
  local scenario=r.readData('scenario.json');local current=r.number(actor,'location')
  if kind=='move' or kind=='explore' then
    assert(destination>=1 and destination<=#scenario.locations,'MD_UNKNOWN_LOCATION')
    local reachable=destination==current
    local from,to=scenario.locations[current],scenario.locations[destination]
    for _,next in ipairs(from.adjacentIds) do if next==to.id then reachable=true end end
    -- A single indoor exploration may pass through hall, without searching hall.
    if kind=='explore' and current<=13 and destination<=13 then
      local fromHall,toHall=false,false
      for _,next in ipairs(from.adjacentIds) do if next=='loc-hall' then fromHall=true end end
      for _,next in ipairs(to.adjacentIds) do if next=='loc-hall' then toHall=true end end
      if fromHall and toHall then reachable=true end
    end
    assert(reachable,'MD_NOT_ADJACENT')
    -- Hidden edge authorization is confirmed by KP before invoking this KP-only rule.
    r.set(actor,'location',destination)
  end
  if kind=='explore' then
    local stamina=r.number(actor,'stamina')
    if stamina==0 then r.set(actor,'fatigue'..r.roll(6),1) else r.set(actor,'stamina',stamina-1) end
  elseif kind=='sleep' then
    local gain=r.number(actor,'constitution')>=4 and 2 or 1
    r.set(actor,'stamina',math.min(r.number(actor,'staminaMax'),r.number(actor,'stamina')+gain))
    for i=1,6 do r.set(actor,'fatigue'..i,0) end
    r.set(actor,'shock',0)
  elseif kind=='soothe' then
    assert(current==8 or current==12 or current==13,'MD_NOT_SOOTHING_LOCATION')
    r.set(actor,'shock',0)
  end
  r.set(actor,'slotUsed',1)
  return {character=actor,kind=kind,location=r.number(actor,'location'),stamina=r.number(actor,'stamina')}
end,{kp=true})
