-- 设计参考，宿主 API 尚未实现。自制百分骰，不是完整 COC 规则。
return {
  kind = "rule",
  id = "reference.percentile-check",
  title = "技能百分骰检定",
  inputSchema = {
    type = "object", additionalProperties = false,
    required = { "actorId", "skillId" },
    properties = {
      actorId = { type = "string", minLength = 1 },
      skillId = { type = "string", minLength = 1 }
    }
  },
  run = function(ctx, input)
    local actor = ctx.read(input.actorId)
    local target = actor.components["example.skills"][input.skillId]
    if type(target) ~= "number" or target < 0 or target > 100 then
      return { rejected = { code = "INVALID_SKILL" } }
    end
    local roll = ctx.roll("1d100")
    return {
      result = { target = target, rolled = roll.total, passed = roll.total <= target },
      effects = {}
    }
  end
}
