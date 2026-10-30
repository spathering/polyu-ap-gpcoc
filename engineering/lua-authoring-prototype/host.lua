-- A1 trusted-author experiment. In-memory, synchronous, not a security sandbox.
local M = {}
local function copy(v)
  if type(v) ~= 'table' then return v end
  local r = {}; for k, x in pairs(v) do r[k] = copy(x) end; return r
end
local function finite(v) return type(v) == 'number' and v == v and math.abs(v) < math.huge end
local function integer(v) return finite(v) and v % 1 == 0 end
local function canonical(v)
  if type(v) == 'string' then return 'string:' .. #v .. ':' .. v end
  if type(v) ~= 'table' then return type(v) .. ':' .. tostring(v) end
  local keys = {}; for k in pairs(v) do keys[#keys+1] = k end
  table.sort(keys)
  local out = {}; for _, k in ipairs(keys) do out[#out+1] = canonical(k) .. '=' .. canonical(v[k]) end
  return '{' .. table.concat(out, ';') .. '}'
end
function M.rule(id, inputs, run)
  assert(type(id) == 'string' and id ~= '' and type(run) == 'function')
  local known = {actor=true, item=true, bag=true, amount=true, quantity=true, skill=true}
  for _, kind in ipairs(inputs) do assert(known[kind], 'unknown input kind') end
  return {id=id, inputs=copy(inputs), run=run}
end
function M.load(path)
  local f = assert(io.open(path, 'rb')); local source = f:read('*a'); f:close()
  local env = {rule=M.rule, pcall=pcall, error=error, type=type}
  local chunk = assert(load(source, '@' .. path, 't', env))
  local def = chunk()
  assert(type(def) == 'table' and type(def.run) == 'function', 'invalid rule definition')
  def.source = source
  return def
end
local function validate(s)
  for id, e in pairs(s.entities) do
    assert(id == e.id and type(e.scope) == 'string' and integer(e.revision) and e.revision > 0, 'invalid identity')
    if e.kind == 'actor' then
      assert(integer(e.hp) and integer(e.maxHp) and e.maxHp >= 0 and e.hp >= 0 and e.hp <= e.maxHp, 'invalid hp')
      assert(integer(e.armor) and e.armor >= 0, 'invalid armor')
      for _, skill in pairs(e.skills) do assert(integer(skill) and skill >= 0 and skill <= 100, 'invalid skill') end
    elseif e.kind == 'bag' then
      assert(integer(e.capacity) and e.capacity >= 0, 'invalid capacity')
    elseif e.kind == 'item' then
      assert(integer(e.quantity) and e.quantity > 0 and integer(e.unitMass) and e.unitMass >= 0, 'invalid item')
      local bag = s.entities[s.holding[id]]
      assert(bag and bag.kind == 'bag' and bag.scope == e.scope, 'invalid holding')
    else error('unknown entity kind') end
  end
  for item, bag in pairs(s.holding) do
    assert(s.entities[item] and s.entities[item].kind == 'item' and s.entities[bag], 'dangling holding')
  end
end
function M.new(initial, options)
  options = options or {}
  local state = copy(initial); validate(state)
  local receipts, active = {}, false
  local host = {}
  function host.snapshot() return copy(state) end
  function host.execute(def, principal, command)
    if active then return {status='rejected', code='REENTRANT_EXECUTION'} end
    if type(command.id) ~= 'string' or command.id == '' or type(principal.id) ~= 'string' then
      return {status='rejected', code='INVALID_COMMAND'}
    end
    if type(command.args) ~= 'table' or type(command.expected or {}) ~= 'table' then
      return {status='rejected', code='INVALID_COMMAND'}
    end
    for k, v in pairs(command.args) do
      if not integer(k) or k < 1 or k > #def.inputs or (type(v) ~= 'string' and type(v) ~= 'number') then
        return {status='rejected', code='INVALID_INPUT'}
      end
    end
    for id, revision in pairs(command.expected or {}) do
      if type(id) ~= 'string' or not integer(revision) or revision < 1 then
        return {status='rejected', code='INVALID_COMMAND'}
      end
    end
    local signature = canonical({def.id, def.source or tostring(def.run), command.args, command.expected or {}})
    local key = canonical({principal.id, principal.scope, command.id})
    if not command.preview and receipts[key] then
      if receipts[key].signature ~= signature then return {status='rejected', code='IDEMPOTENCY_CONFLICT'} end
      -- Recheck visibility before returning cached business data.
      for id in pairs(receipts[key].readSet) do
        if not principal.allowed[id] then return {status='rejected', code='NOT_FOUND_OR_FORBIDDEN'} end
      end
      local replay = copy(receipts[key].receipt); replay.replayed = true; return replay
    end
    active = true
    local baseline, draft = copy(state), copy(state)
    local reads, touched, created, effects, dice = {}, {}, {}, {}, {}
    local poisoned, operationCount = nil, 0
    local function reject(code)
      poisoned = poisoned or code
      error(code, 0)
    end
    local function tick()
      operationCount = operationCount + 1
      if operationCount > (options.maxOperations or 100) then reject('OPERATION_LIMIT') end
    end
    local function read(id, kind)
      local e = draft.entities[id]
      if not e or e.scope ~= principal.scope or not (created[id] or principal.allowed[id]) then reject('NOT_FOUND_OR_FORBIDDEN') end
      if kind and e.kind ~= kind then reject('TYPE_MISMATCH') end
      if not created[id] then reads[id] = baseline.entities[id].revision end
      return e
    end
    local function write(id)
      if not principal.canWrite then reject('FORBIDDEN') end
      touched[id] = true
    end
    local api = {}
    function api.read(id) tick(); return copy(read(id)) end
    function api.check(id, skill)
      tick(); local actor = read(id, 'actor'); local target = actor.skills[skill]
      if not target then reject('INVALID_SKILL') end
      -- Dependency-injected RNG for experiments; only committed calls keep records.
      local rolled = (options.roll or function() return math.random(1,100) end)(command.preview == true)
      if not integer(rolled) or rolled < 1 or rolled > 100 then reject('INVALID_ROLL') end
      local result = {passed=rolled <= target, target=target, rolled=rolled}
      dice[#dice+1] = copy(result); return result
    end
    function api.damage(id, amount)
      tick(); local actor = read(id, 'actor')
      if not integer(amount) or amount < 0 then reject('INVALID_AMOUNT') end
      write(id)
      local effective = options.damagePolicy and options.damagePolicy(copy(actor), amount) or math.max(0, amount-actor.armor)
      if not integer(effective) or effective < 0 then reject('INVALID_DAMAGE_POLICY') end
      local before = actor.hp; actor.hp = math.max(0, before-effective)
      effects[#effects+1] = {kind='damage', target=id, lost=before-actor.hp}
      return {before=before, after=actor.hp, lost=before-actor.hp}
    end
    function api.transfer(itemId, destination, quantity)
      tick(); local item = read(itemId, 'item'); local target = read(destination, 'bag')
      local sourceId = draft.holding[itemId]; local source = read(sourceId, 'bag')
      if sourceId == destination then reject('SAME_CONTAINER') end
      quantity = quantity or item.quantity
      if not integer(quantity) or quantity <= 0 or quantity > item.quantity then reject('INVALID_QUANTITY') end
      write(itemId); write(sourceId); write(destination)
      local mass = 0
      for id, bagId in pairs(draft.holding) do
        if bagId == destination then
          local member = read(id, 'item'); mass = mass + member.quantity * member.unitMass
        end
      end
      local afterMass = mass + quantity * item.unitMass
      local capacityOK = options.capacityPolicy and options.capacityPolicy(copy(target), afterMass)
      if capacityOK == nil then capacityOK = afterMass <= target.capacity end
      if capacityOK ~= true then reject('CAPACITY_EXCEEDED') end
      local resultId = itemId
      if quantity == item.quantity then
        draft.holding[itemId] = destination
      else
        local serial = draft.nextId
        repeat resultId = 'split-' .. serial; serial = serial+1 until not draft.entities[resultId]
        draft.nextId = serial
        local part = copy(item); part.id = resultId; part.quantity = quantity; part.revision = 1
        draft.entities[resultId] = part; draft.holding[resultId] = destination
        created[resultId] = true; touched[resultId] = true
        item.quantity = item.quantity - quantity
      end
      effects[#effects+1] = {kind='transfer', source=sourceId, target=destination, item=resultId, quantity=quantity}
      return resultId
    end
    local ok, result = pcall(function()
      local args = command.args
      if type(args) ~= 'table' or #args ~= #def.inputs then reject('INVALID_INPUT') end
      for i, kind in ipairs(def.inputs) do
        if kind == 'actor' or kind == 'item' or kind == 'bag' then read(args[i], kind)
        elseif kind == 'amount' or kind == 'quantity' then
          if not integer(args[i]) or args[i] < (kind == 'quantity' and 1 or 0) then reject('INVALID_INPUT') end
        elseif type(args[i]) ~= 'string' or args[i] == '' then reject('INVALID_INPUT') end
      end
      return def.run(api, table.unpack(args))
    end)
    local receipt
    if not ok or poisoned then
      receipt = {status='rejected', code=poisoned or 'SCRIPT_ERROR', diagnostic=not ok and tostring(result) or nil}
    else
      -- Results are intentionally limited to scalars for this A1 experiment.
      if type(result) == 'table' or (type(result)=='number' and not finite(result)) or
         (type(result) ~= 'nil' and type(result) ~= 'boolean' and type(result) ~= 'number' and type(result) ~= 'string') then
        receipt = {status='rejected', code='INVALID_RESULT'}
      else
        local conflict
        for id, revision in pairs(command.expected or {}) do
          if not reads[id] or reads[id] ~= revision then conflict = true end
        end
        -- Synchronous host disallows reentrant writers; compare actual tracked reads too.
        for id, revision in pairs(reads) do
          if not state.entities[id] or state.entities[id].revision ~= revision then conflict = true end
        end
        if conflict then receipt = {status='rejected', code='REVISION_CONFLICT'}
        else
          for id in pairs(touched) do
            if not created[id] then draft.entities[id].revision = draft.entities[id].revision+1 end
          end
          local valid = pcall(validate, draft)
          if not valid then receipt = {status='rejected', code='INVARIANT_FAILED'}
          else
            receipt = {status=command.preview and 'preview' or 'committed', result=result, effects=copy(effects), dice=copy(dice), replayed=false}
            if not command.preview then state = draft end
          end
        end
      end
    end
    if not command.preview then receipts[key] = {signature=signature, readSet=copy(reads), receipt=copy(receipt)} end
    active = false
    return copy(receipt)
  end
  return host
end
return M
