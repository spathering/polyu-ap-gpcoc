return rule('md.request', {'actor','attribute:amount','talent:choice'}, function(r,actor,attribute,talent)
  assert(r.matches(actor,'md.character') and r.number(actor,'approved')==1,'MD_NOT_APPROVED')
  assert(attribute>=1 and attribute<=5,'MD_ATTRIBUTE_RANGE')
  assert(r.number(actor,'requestOpen')==0,'MD_REQUEST_PENDING')
  assert(r.number(actor,'hp')>0,'MD_DOWNED')
  r.set(actor,'requestAttribute',attribute);r.set(actor,'requestTalent',talent and 1 or 0);r.set(actor,'requestOpen',1)
  return {character=actor,attribute=attribute,talent=talent}
end,{kp=true})
