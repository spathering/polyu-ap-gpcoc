-- 设计参考：按指定逻辑时钟的 round.start 边界到期，不用真实时间 sleep。
return {
  kind = "rule",
  id = "reference.apply-slow",
  title = "施加一个有来源的限轮状态",
  inputSchema = {
    type = "object", additionalProperties = false,
    required = { "actorId", "clockId", "sourceKey", "rounds" },
    properties = {
      actorId = { type = "string", minLength = 1 },
      clockId = { type = "string", minLength = 1 },
      sourceKey = { type = "string", minLength = 1 },
      rounds = { type = "integer", minimum = 1, maximum = 100 }
    }
  },
  run = function(ctx, input)
    local clock = ctx.clocks.read(input.clockId)
    local expiresRound = clock.round + input.rounds
    return {
      result = { expiresRound = expiresRound, expiresPhase = "round.start" },
      effects = {
        { kind = "status.apply", bearerId = input.actorId,
          statusType = "reference.slow", sourceKey = input.sourceKey,
          stacking = "refreshBySource",
          duration = { clockId = input.clockId,
            expiresAt = { round = expiresRound, phase = "round.start" } } }
      }
    }
  end
}
