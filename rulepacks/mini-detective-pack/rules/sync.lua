return rule('md.sync', {'actor','day:amount','slot:amount'}, function(r,actor,day,slot)
  assert(r.matches(actor,'md.character'),'MD_NOT_CHARACTER')
  assert(day>=1 and day<=2 and slot>=1 and slot<=8,'MD_INVALID_TIME')
  assert(day>r.number(actor,'day') or (day==r.number(actor,'day') and slot>r.number(actor,'slot')),'MD_TIME_NOT_FORWARD')
  if day>r.number(actor,'day') then r.set(actor,'intellectRemaining',r.number(actor,'intellect')) end
  r.set(actor,'day',day);r.set(actor,'slot',slot);r.set(actor,'slotUsed',0)
  return {character=actor,day=day,slot=slot}
end,{kp=true})
