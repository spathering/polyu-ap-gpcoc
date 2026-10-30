-- 设计参考：故意与 02 使用同一 ID，必须作为显式场次覆盖加载，不能批量安装。
-- 作用域、内容修订与生效时点由宿主激活命令指定，不由该文件自行决定。
return {
  kind = "rule",
  id = "reference.apply-damage",
  title = "本场临时护佑：额外减伤二点",
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
    local damage = math.max(0, input.rawDamage - armor - 2)
    local after = math.max(0, hp - damage)
    return {
      result = { damage = damage, hpLost = hp - after, before = hp,
        after = after, modifier = "session-ward" },
      effects = {
        { kind = "entity.patch", entityId = actor.id, ops = {
          { op = "replace", path = "/components/example.resources/hp/current", value = after }
        } }
      }
    }
  end
}
