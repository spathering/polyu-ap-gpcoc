return rule('md.advance', {'actor'}, function(r,actor)
  assert(r.matches(actor,'md.world'),'MD_NOT_WORLD')
  assert(r.number(actor,'closed')==0,'MD_CLOSED')
  local day,slot=r.number(actor,'day'),r.number(actor,'slot')
  if slot==8 and day==2 then r.set(actor,'closed',1)
  elseif slot==8 then day=day+1;slot=1
  else slot=slot+1 end
  r.set(actor,'day',day);r.set(actor,'slot',slot)
  return {day=day,slot=slot,closed=r.number(actor,'closed')==1}
end,{kp=true})
