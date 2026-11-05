return rule('lf.adventure', {'threat:amount', 'intent:amount', 'object:amount', 'consequence:amount'}, function(r, threat, intent, object, consequence)
  local data, choices, result = r.readData('lf.json'), {threat, intent, object, consequence}, {}
  for i, key in ipairs({'threats', 'intents', 'objects', 'consequences'}) do
    local choice = choices[i]
    assert(choice >= 0 and choice <= 6, 'LF_INVALID_TABLE_CHOICE')
    if choice == 0 then choice = r.roll(6) end
    result[key] = {index=choice, text=data[key][choice]}
  end
  return result
end, {kp=true})
