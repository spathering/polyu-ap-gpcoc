return rule('sv.layout', {'actor'}, function(r, actor)
  local data = r.readData('game.json')
  local occupied, cards = {}, {}
  local overloaded, armor, injured = false, 0, false
  for slot = 1, 20 do
    local index = r.number(actor, 'item' .. slot)
    if index > 0 then
      local def = data.items[index]
      assert(def, 'SV_UNKNOWN_ITEM')
      local cells = {slot}
      if def.id == 'injured' then injured = true end
      if slot > 10 then
        overloaded = true
      elseif def.slots == 2 then
        if def.shape == 'offhand-body' and slot <= 4 then
          assert(slot == 2, 'SV_LIGHT_ARMOR_OFFHAND_BODY')
          cells = {2, 3}
        elseif slot <= 4 then
          assert(slot == 1 or slot == 3, 'SV_ITEM_NEEDS_TWO_SLOTS')
          cells = {slot, slot + 1}
        else
          assert(slot == 5 or slot == 6 or slot == 8 or slot == 9, 'SV_ITEM_NEEDS_TWO_SLOTS')
          cells = {slot, slot + 1}
        end
      elseif def.slots == 4 then
        assert(slot == 5 or slot == 6, 'SV_ITEM_NEEDS_FOUR_SLOTS')
        cells = {slot, slot + 1, slot + 3, slot + 4}
      end
      if def.kind == 'armor' and slot <= 4 and r.number(actor, 'uses' .. slot) > 0 then armor = math.max(armor, def.armor or 0) end
      for _, cell in ipairs(cells) do
        assert(not occupied[tostring(cell)], 'SV_SLOT_OCCUPIED')
        occupied[tostring(cell)] = slot
      end
      cards[#cards + 1] = {slot=slot, item=index, uses=r.number(actor, 'uses' .. slot), cells=cells}
    end
  end
  local coins = math.ceil(math.max(0, r.number(actor, 'pips') - 250) / 250)
  local coinSlots = {}
  for slot=10,1,-1 do
    if coins > 0 and not occupied[tostring(slot)] then
      occupied[tostring(slot)] = -1
      coinSlots[#coinSlots+1] = slot
      coins = coins - 1
    end
  end
  if coins > 0 then overloaded = true end
  return {occupied=occupied, cards=cards, overloaded=overloaded, armor=armor, injured=injured, coinSlots=coinSlots}
end, {mode='calculation', public=false})
