-- 设计参考：一次失败检定 -> 等待 KP -> 获准才对同一角色应用损伤。
-- ruleStep 结果及效果原子提交；跨等待不持有锁，也不保存协程栈。
return defineFlow({
  id = "reference.check-with-ruling",
  title = "检定失败后由 KP 裁定后果",
  inputSchema = {
    type = "object", additionalProperties = false,
    required = { "actorId", "skillId", "rawDamage" },
    properties = {
      actorId = { type = "string", minLength = 1 },
      skillId = { type = "string", minLength = 1 },
      rawDamage = { type = "integer", minimum = 0, maximum = 10000 }
    }
  },
  start = "check",
  steps = {
    check = ruleStep("reference.percentile-check", {
      input = function(state)
        return { actorId = state.input.actorId, skillId = state.input.skillId }
      end,
      next = function(state)
        if state.steps.check.result.passed then return "done" end
        return "ruling"
      end
    }),
    ruling = approvalStep({
      role = "keeper",
      prompt = "检定失败，是否执行本流程已声明的伤害后果？",
      responseSchema = {
        type = "object", additionalProperties = false,
        required = { "approved", "reason" },
        properties = {
          approved = { type = "boolean" },
          reason = { type = "string", minLength = 1, maxLength = 500 }
        }
      },
      next = function(state)
        if state.steps.ruling.response.approved then return "apply" end
        return "done"
      end
    }),
    apply = ruleStep("reference.apply-damage", {
      input = function(state)
        return { actorId = state.input.actorId, rawDamage = state.input.rawDamage }
      end,
      next = "done"
    }),
    done = endStep()
  }
})
