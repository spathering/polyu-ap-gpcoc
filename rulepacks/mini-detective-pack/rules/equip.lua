return rule('md.equip', {'actor','item:actor'}, function(r,actor,item)
  assert(r.matches(actor,'md.character') and r.matches(item,'md.item'),'MD_INVALID_ITEM')
  assert(r.number(item,'confirmed')==1 and r.number(item,'count')>0,'MD_ITEM_NOT_USABLE')
  local holders=r.related(item,'source');assert(#holders==1 and holders[1]==actor,'MD_NOT_HOLDER')
  assert(r.read(actor).owner==r.read(item).owner,'MD_NOT_HOLDER')
  local def=r.readData('scenario.json').items[r.number(item,'itemIndex')]
  assert(def and def.star>0,'MD_NOT_WEAPON')
  if def.id=='item-shotgun' then assert(r.number(item,'charges')>0,'MD_NO_AMMO') end
  for _,id in ipairs(r.related(actor,'references')) do
    if r.matches(id,'md.item') then r.set(id,'equipped',id==item and 1 or 0) end
  end
  r.set(actor,'weapon',def.star)
  return {character=actor,item=item,weapon=def.star}
end,{kp=true})
