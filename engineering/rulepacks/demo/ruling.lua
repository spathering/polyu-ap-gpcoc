return flow('demo.ruling', {'actor','skill','amount'}, {
  step('check', function(r, actor, skill) return r.check(actor,skill).passed end,
       {yes='end', no='ruling'}),
  ask('ruling', {role='kp', seconds=60, yes='apply', no='end', timeout='end'}),
  step('apply', function(r, actor, skill, amount) r.damage(actor,amount) end)
})
