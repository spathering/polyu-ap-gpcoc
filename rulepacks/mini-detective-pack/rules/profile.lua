return rule('md.profile', {'actor','constitution:amount','strength:amount','speed:amount','observation:amount','spirit:amount','intellect:amount'}, function(r, actor, constitution,strength,speed,observation,spirit,intellect)
  assert(r.matches(actor,'md.character'),'MD_NOT_CHARACTER')
  assert(r.number(actor,'approved')==0,'MD_PROFILE_LOCKED')
  local values={constitution,strength,speed,observation,spirit,intellect}
  local keys={'constitution','strength','speed','observation','spirit','intellect'}
  local total=0
  for i,v in ipairs(values) do assert(v>=1 and v<=5 and v%1==0,'MD_ATTRIBUTE_RANGE'); total=total+v; r.set(actor,keys[i],v) end
  assert(total==20,'MD_ATTRIBUTE_BUDGET')
  r.set(actor,'maxHp',constitution*3); r.set(actor,'hpMax',constitution*3); r.set(actor,'hp',constitution*3)
  r.set(actor,'staminaMax',constitution>=4 and 4 or 3)
  r.set(actor,'stamina',constitution>=4 and 3 or 2)
  r.set(actor,'intellectRemaining',intellect); r.set(actor,'approved',1)
  return {character=actor,approved=true}
end,{kp=true})
