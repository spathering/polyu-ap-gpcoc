return rule('demo.lib.transfer', {'item','bag','quantity'}, function(r, item, bag, quantity)
  local load = 0
  for _, entry in ipairs(r.items(bag)) do
    load = load + entry.numbers.quantity*entry.numbers.unitMass
  end
  local itemData = r.read(item)
  quantity = quantity or itemData.numbers.quantity
  assert(load + quantity*itemData.numbers.unitMass <= r.number(bag,'capacity'), 'capacity exceeded')
  return r.move(item, bag, quantity)
end, {public=false})
