return rule('demo.environment', {'actor'}, function(r, actor)
  return r.number(actor,'attack') + r.readData('environment.json').attackBonus
end, {mode='calculation'})
