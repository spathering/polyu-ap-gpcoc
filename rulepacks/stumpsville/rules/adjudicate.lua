return rule('sv.adjudicate', {'actor', 'kind:text', 'attribute:text', 'mode:text', 'operation:text', 'slot:amount', 'value:amount'}, function(r, actor, kind, attribute, mode, operation, slot, value)
  if kind == 'check' then return r.call('sv.check.core', actor, attribute, mode) end
  if kind == 'inventory' then return r.call('sv.inventory.core', actor, operation, slot, value) end
  error('SV_RULING_KIND')
end, {kp=true, dependencies={'sv.check.core', 'sv.inventory.core'}})
