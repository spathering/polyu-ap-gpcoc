return rule('sv.travel.auto', {'actor', 'destination:actor'}, function(r, actor, destination)
  local session = r.call('sv.automation', actor)
  assert(r.number(session, 'phase') == 1, 'SV_SESSION_NOT_STARTED')
  assert(r.number(actor, 'approved') == 1 and r.number(actor, 'ready') == 1, 'SV_NOT_READY')
  assert(r.number(actor, 'incapacitated') == 0 and r.number(actor, 'str') > 0 and r.number(actor, 'dex') > 0 and r.number(actor, 'wil') > 0, 'SV_CANNOT_ACT')
  assert(r.matches(destination, 'sv.location') and r.read(destination).visibility == 'public', 'SV_LOCATION_NOT_PUBLIC')
  local current, target = r.number(actor, 'location'), r.number(destination, 'index')
  local allowed = false
  for _, id in ipairs(r.readData('game.json').locations[current].exits) do if id == target then allowed = true end end
  assert(allowed, 'SV_NOT_ADJACENT')
  local key = 'door' .. math.min(current, target) .. '_' .. math.max(current, target)
  assert(r.read(session).numbers[key] == 1, 'SV_DOOR_CLOSED')
  r.set(actor, 'location', target)
  return {location=target, automatic=true}
end, {dependencies={'sv.automation'}})
