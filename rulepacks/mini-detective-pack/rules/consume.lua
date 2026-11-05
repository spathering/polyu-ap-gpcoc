return rule('md.consume', {'actor','item:actor','kind:text'}, function(r,actor,item,kind)
  assert(r.matches(actor,'md.character') and r.matches(item,'md.item'),'MD_INVALID_ITEM')
  assert(r.number(item,'confirmed')==1 and r.number(item,'count')>0,'MD_ITEM_NOT_USABLE')
  assert(r.read(actor).owner==r.read(item).owner,'MD_NOT_HOLDER')
  local holders=r.related(item,'source');assert(#holders==1 and holders[1]==actor,'MD_NOT_HOLDER')
  local index=r.number(item,'itemIndex')
  local data=r.readData('scenario.json');local def=data.items[index]
  assert(def~=nil,'MD_INVALID_ITEM')
  if kind=='medicine' then
    assert(def.id=='item-medkit','MD_NOT_MEDICINE')
    assert(r.number(actor,'slotUsed')==0,'MD_SLOT_USED')
    local heal=3
    if r.number(actor,'talent')~=4 then heal=r.roll(6)<=r.number(actor,'intellect') and 3 or 1 end
    r.set(actor,'hp',math.min(r.number(actor,'hpMax'),r.number(actor,'hp')+heal));r.set(actor,'injury',0);r.set(actor,'slotUsed',1)
  elseif kind=='food' then assert(def.id=='item-food','MD_NOT_FOOD')
  elseif kind=='antidote' then assert(def.id=='item-antidote','MD_NOT_ANTIDOTE');r.set(actor,'poisoned',0)
  else error('MD_UNKNOWN_CONSUMPTION') end
  r.set(item,'count',r.number(item,'count')-1)
  return {character=actor,item=item,count=r.number(item,'count'),hp=r.number(actor,'hp')}
end,{kp=true})
