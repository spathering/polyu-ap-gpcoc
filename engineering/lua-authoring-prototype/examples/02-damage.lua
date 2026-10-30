return rule('demo.damage', {'actor', 'amount'}, function(r, actor, amount)
  r.damage(actor, amount)
end)
