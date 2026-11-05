return rule('md.check', {'actor'}, function(r,actor)
  assert(r.matches(actor,'md.character') and r.number(actor,'approved')==1,'MD_NOT_APPROVED')
  assert(r.number(actor,'hp')>0,'MD_DOWNED')
  assert(r.number(actor,'requestOpen')==1,'MD_NO_REQUEST')
  local i=r.number(actor,'requestAttribute')
  local keys={'strength','speed','observation','spirit','intellect'}
  assert(i>=1 and i<=5,'MD_INVALID_REQUEST')
  local target=r.number(actor,keys[i]);if r.number(actor,'requestTalent')==1 then target=5 end
  local fatigueIndex=({1,2,3,5,4})[i]
  if r.number(actor,'fatigue'..fatigueIndex)==1 or r.number(actor,'fatigue6')==1 then target=target-1 end
  if r.number(actor,'shock')==1 then target=target-1;r.set(actor,'shock',0) end
  local injury=r.number(actor,'injury')
  if (injury==1 and i==1) or (injury==2 and i==2) or (injury==3 and i==3) or (injury==4 and i==4) then target=target-1;r.set(actor,'injury',0) end
  r.set(actor,'fatigue6',0)
  target=math.max(1,math.min(6,target));local die=r.roll(6);local passed=die<=target
  r.set(actor,'requestOpen',0);r.set(actor,'lastDie',die);r.set(actor,'lastPassed',passed and 1 or 0)
  return {character=actor,attribute=keys[i],target=target,die=die,passed=passed}
end)
