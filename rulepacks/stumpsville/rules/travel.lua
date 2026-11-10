return rule('sv.travel', {'actor', 'location:amount'}, function(r, actor, location)
  assert(r.matches(actor, 'sv.character') and r.number(actor, 'approved') == 1, 'SV_NOT_APPROVED')
  assert(location >= 1 and location <= 10, 'SV_LOCATION')
  r.set(actor, 'location', location)
  return {location=location}
end, {kp=true})
