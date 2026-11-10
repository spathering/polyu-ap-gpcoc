return rule('sv.inventory', {'actor', 'operation:text', 'slot:amount', 'value:amount'}, function(r, actor, operation, slot, value)
  r.call('sv.automation', actor)
  return r.call('sv.inventory.core', actor, operation, slot, value)
end, {dependencies={'sv.automation', 'sv.inventory.core'}})
