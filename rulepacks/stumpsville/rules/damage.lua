return rule('sv.damage', {'actor', 'amount:amount', 'attribute:text'}, function(r, actor, amount, attribute)
  assert(r.matches(actor, 'sv.character') or r.matches(actor, 'sv.npc'), 'SV_DAMAGE_TARGET')
  assert(attribute == 'str' or attribute == 'dex', 'SV_DAMAGE_ATTRIBUTE')
  assert(amount <= 1000, 'SV_DAMAGE_RANGE')
  local layout = nil
  if r.matches(actor, 'sv.character') then layout = r.call('sv.layout', actor) end
  local armor = math.max(r.number(actor, 'armor'), layout and layout.armor or 0)
  local damage = math.max(0, amount - armor)
  local oldHp = r.number(actor, 'hp')
  local hp = math.max(0, oldHp - damage)
  local overflow = math.max(0, damage - oldHp)
  r.set(actor, 'hp', hp)
  local target = r.number(actor, attribute)
  local rolled, critical = 0, false
  if overflow > 0 then
    target = math.max(0, target - overflow)
    r.set(actor, attribute, target)
    rolled = r.roll(20)
    critical = rolled > target
    if critical then
      r.set(actor, 'incapacitated', 1)
      if layout then
        local placed = false
        for slot=1,20 do
          if not placed and not layout.occupied[tostring(slot)] then
            r.set(actor, 'item' .. slot, 12)
            r.set(actor, 'uses' .. slot, 0)
            r.set(actor, 'ticks' .. slot, 0)
            placed = true
          end
        end
        if not placed then r.set(actor, 'conditionPending', r.number(actor, 'conditionPending') + 1) end
      end
    end
  end
  return {damage=damage, hp=hp, overflow=overflow, attribute=attribute, remaining=target, save=rolled, critical=critical, dead=attribute=='str' and target==0}
end, {kp=true, dependencies={'sv.layout'}})
