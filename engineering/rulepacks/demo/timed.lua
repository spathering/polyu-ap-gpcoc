return flow('demo.timed', {'actor','amount'}, {
  ask('choice', {role='initiator', seconds=30, yes='apply', no='end', timeout='end'}),
  step('apply', function(r, actor, amount) r.damage(actor,amount) end)
})
