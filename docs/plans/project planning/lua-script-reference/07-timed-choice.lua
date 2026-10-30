-- 设计参考：宿主持久化待办与截止时间；玩家回应和到期只允许一次胜出。
return defineFlow({
  id = "reference.timed-choice",
  title = "三十秒内选择是否开门",
  inputSchema = {
    type = "object", additionalProperties = false,
    required = { "playerId" },
    properties = { playerId = { type = "string", minLength = 1 } }
  },
  start = "decision",
  steps = {
    decision = inputStep({
      assignee = function(state) return { participantId = state.input.playerId } end,
      prompt = "是否打开门？三十秒后视为未选择。",
      responseSchema = {
        type = "object", additionalProperties = false,
        required = { "answer" },
        properties = { answer = { type = "string", enum = { "open", "leave" } } }
      },
      timeout = { seconds = 30, next = "expired", overdue = "executeOnce" },
      next = function(state)
        if state.steps.decision.response.answer == "open" then return "opened" end
        return "left"
      end
    }),
    opened = endStep({ result = function(state) return { choice = "open" } end }),
    left = endStep({ result = function(state) return { choice = "leave" } end }),
    expired = endStep({ result = function(state) return { choice = "timeout" } end })
  }
})
