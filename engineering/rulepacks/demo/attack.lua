return rule('demo.attack', {'actor'}, function(r, actor)
  return r.number(actor,'attack') + r.number(actor,'armor')
end, {mode='calculation'})
