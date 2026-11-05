return rule('md.combat', {'attacker:actor','defender:actor','dodge:choice'}, function(r,attacker,defender,dodge)
  assert(attacker~=defender,'MD_SAME_TARGET')
  assert(r.matches(attacker,'md.character') and r.matches(defender,'md.character'),'MD_NOT_CHARACTER')
  assert(r.number(attacker,'hp')>0 and r.number(defender,'hp')>0,'MD_DOWNED')
  local attackWeapon=r.number(attacker,'weapon')
  for _,id in ipairs(r.related(attacker,'references')) do
    if r.matches(id,'md.item') and r.number(id,'equipped')==1 then
      local def=r.readData('scenario.json').items[r.number(id,'itemIndex')]
      if def.id=='item-shotgun' then
        assert(r.number(id,'charges')>0,'MD_NO_AMMO')
        r.set(id,'charges',r.number(id,'charges')-1)
        if r.number(id,'charges')==0 then r.set(attacker,'weapon',0);r.set(id,'equipped',0) end
      end
    end
  end
  -- KP records the defender choice before invocation; all dice are host-generated.
  local ds,dv,dd=r.roll(6),r.roll(6),r.roll(6)
  -- The captured bonus applies to this shot; zero ammo unequips subsequent attacks.
  local power=r.number(attacker,'strength')-ds+attackWeapon
  local speed=r.number(attacker,'speed')-dv
  local damage=0;local avoided=false
  if dodge then
    avoided=r.number(defender,'speed')-dd>speed
    if not avoided then damage=math.max(0,power+speed) end
  else
    damage=power-(r.number(defender,'strength')-dd+r.number(defender,'weapon'))
    if damage<0 then damage=1 end
  end
  r.set(defender,'hp',math.max(0,r.number(defender,'hp')-damage))
  return {attacker=attacker,defender=defender,dodge=dodge,dice={ds,dv,dd},damage=damage,avoided=avoided,hp=r.number(defender,'hp')}
end,{kp=true})
