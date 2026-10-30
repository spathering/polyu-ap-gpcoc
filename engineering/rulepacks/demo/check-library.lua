return rule('demo.lib.check', {'actor','skill'}, function(r, actor, skill)
  r.ownedSkill(actor, skill)
  local target = r.number(skill, 'value')
  local rolled = r.roll(100)
  return {target=target, rolled=rolled, passed=rolled<=target}
end, {public=false})
