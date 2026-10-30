return rule('demo.check', {'actor','skill'}, function(r, actor, skill)
  return r.check(actor, skill).passed
end)
