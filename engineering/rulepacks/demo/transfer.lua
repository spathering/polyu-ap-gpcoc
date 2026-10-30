return rule('demo.transfer', {'item','bag','quantity'}, function(r, item, bag, quantity)
  return r.transfer(item, bag, quantity)
end)
