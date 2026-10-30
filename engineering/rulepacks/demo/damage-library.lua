return rule('demo.lib.damage', {'actor','amount'}, function(r, actor, amount)
  local lost = math.max(0, amount-r.number(actor,'armor'))
  r.set(actor, 'hp', math.max(0,r.number(actor,'hp')-lost))
end, {public=false})
