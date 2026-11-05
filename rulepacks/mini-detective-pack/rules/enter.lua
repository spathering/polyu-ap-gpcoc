return rule('md.enter', {'actor'}, function(r,actor)
  assert(r.matches(actor,'md.character') and r.number(actor,'hp')>0,'MD_DOWNED')
  assert(r.number(actor,'encounterActive')==0,'MD_ENCOUNTER_ACTIVE')
  local stamina=r.number(actor,'stamina')
  if stamina>0 then r.set(actor,'stamina',stamina-1) else r.set(actor,'fatigue'..r.roll(6),1) end
  r.set(actor,'encounterActive',1)
  return {character=actor,stamina=r.number(actor,'stamina')}
end,{kp=true})
