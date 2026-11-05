return rule('md.damage', {'actor','amount'}, function(r,actor,amount)
  assert(r.matches(actor,'md.character'),'MD_NOT_CHARACTER')
  assert(amount<=100,'MD_DAMAGE_RANGE')
  r.set(actor,'hp',math.max(0,r.number(actor,'hp')-amount))
  return {character=actor,hp=r.number(actor,'hp'),downed=r.number(actor,'hp')==0}
end,{kp=true})
