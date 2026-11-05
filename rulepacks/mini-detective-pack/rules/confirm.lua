return rule('md.confirm', {'actor'}, function(r,actor)
  assert(r.matches(actor,'md.item'),'MD_NOT_ITEM')
  local holders=r.related(actor,'source');assert(#holders==1,'MD_INVALID_HOLDER')
  local holder=holders[1];assert(r.matches(holder,'md.character'),'MD_INVALID_HOLDER')
  assert(r.read(holder).owner==r.read(actor).owner,'MD_NOT_HOLDER')
  local count,found=0,false
  for _,id in ipairs(r.related(holder,'references')) do
    if r.matches(id,'md.item') and r.number(id,'count')>0 then count=count+1;if id==actor then found=true end end
  end
  assert(found and count<=4,'MD_CARD_CAPACITY')
  local data=r.readData('scenario.json');local def=data.items[r.number(actor,'itemIndex')]
  assert(def and r.number(actor,'count')>=1 and r.number(actor,'count')<=def.stackMax,'MD_ITEM_COUNT')
  if r.number(actor,'confirmed')==0 and def.id=='item-shotgun' then r.set(actor,'charges',2) end
  r.set(actor,'confirmed',1);r.set(actor,'star',def.star)
  return {item=actor,holder=holder,confirmed=true}
end,{kp=true})
