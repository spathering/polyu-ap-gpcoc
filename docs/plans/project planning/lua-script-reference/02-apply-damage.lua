-- 设计参考：只计算提案，不直接改角色或数据库。
return {
  kind = "rule",
  id = "reference.apply-damage",
  title = "护甲减伤并扣除 HP",
  inputSchema = {
    type = "object", additionalProperties = false,
    required = { "actorId", "rawDamage" },
    properties = {
      actorId = { type = "string", minLength = 1 },
      rawDamage = { type = "integer", minimum = 0, maximum = 10000 }
    }
  },
  run = function(ctx, input)
    local actor = ctx.read(input.actorId)
    local hp = actor.components["example.resources"].hp.current
    local armor = actor.components["example.defense"].armor
    local damage = math.max(0, input.rawDamage - armor)
    local after = math.max(0, hp - damage)
    return {
      result = { damage = damage, hpLost = hp - after, before = hp, after = after },
      effects = {
        { kind = "entity.patch", entityId = actor.id, ops = {
          { op = "replace", path = "/components/example.resources/hp/current", value = after }
        } }
      }
    }
  end
}
