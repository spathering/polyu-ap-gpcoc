-- 设计参考：无骰管理动作。脚本不能自行赋予执行者授予物品的权限。
return {
  kind = "rule",
  id = "reference.grant-item",
  title = "按模板赐予物品",
  inputSchema = {
    type = "object", additionalProperties = false,
    required = { "templateId", "toContainerId", "quantity", "reason" },
    properties = {
      templateId = { type = "string", minLength = 1 },
      toContainerId = { type = "string", minLength = 1 },
      quantity = { type = "integer", minimum = 1, maximum = 1000 },
      reason = { type = "string", minLength = 1, maxLength = 500 }
    }
  },
  run = function(ctx, input)
    return {
      result = { requestedQuantity = input.quantity, reason = input.reason },
      effects = {
        { kind = "inventory.grant", templateId = input.templateId,
          toContainerId = input.toContainerId,
          quantity = input.quantity, reason = input.reason }
      }
    }
  end
}
