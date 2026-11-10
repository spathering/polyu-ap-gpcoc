return rule('sv.check', {'actor', 'attribute:text', 'mode:text'}, function(r, actor, attribute, mode)
  r.call('sv.automation', actor)
  return r.call('sv.check.core', actor, attribute, mode)
end, {dependencies={'sv.automation', 'sv.check.core'}})
