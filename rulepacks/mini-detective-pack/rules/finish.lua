return rule('md.finish', {'actor'}, function(r,actor)
  assert(r.matches(actor,'md.character'),'MD_NOT_CHARACTER')
  assert(r.number(actor,'encounterActive')==1,'MD_NO_ENCOUNTER')
  r.set(actor,'encounterActive',0)
  local injury=0
  if r.number(actor,'hp')*2<r.number(actor,'hpMax') then injury=r.roll(6);r.set(actor,'injury',injury) end
  return {character=actor,injury=injury}
end,{kp=true})
