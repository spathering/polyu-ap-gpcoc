-- 设计参考：文件读取由宿主授权、校验并固定内容修订；不直接使用 io.open。
return {
  kind = "rule",
  id = "reference.environment-check",
  title = "从数据文件读取环境修正",
  dataFiles = { "data/environment-modifiers.json" },
  inputSchema = {
    type = "object", additionalProperties = false,
    required = { "actorId", "skillId", "environment" },
    properties = {
      actorId = { type = "string", minLength = 1 },
      skillId = { type = "string", minLength = 1 },
      environment = { type = "string", minLength = 1 }
    }
  },
  run = function(ctx, input)
    local data = ctx.files.readJson("data/environment-modifiers.json")
    local entry = data.environments[input.environment]
    if entry == nil then
      return { rejected = { code = "UNKNOWN_ENVIRONMENT" } }
    end
    local actor = ctx.read(input.actorId)
    local base = actor.components["example.skills"][input.skillId]
    if type(base) ~= "number" or base < 0 or base > 100 then
      return { rejected = { code = "INVALID_SKILL" } }
    end
    local target = math.max(0, math.min(100, base - entry.penalty))
    local roll = ctx.roll("1d100")
    return {
      result = { base = base, penalty = entry.penalty, target = target,
        rolled = roll.total, passed = roll.total <= target },
      effects = {}
    }
  end
}
