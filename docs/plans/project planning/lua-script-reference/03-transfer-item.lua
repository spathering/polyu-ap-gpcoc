-- 设计参考：内核维护数量守恒、唯一持有、读集版本及原子提交。
return {
  kind = "rule",
  id = "reference.transfer-item",
  title = "带容量校验的物品转移",
  inputSchema = {
    type = "object", additionalProperties = false,
    required = { "itemId", "fromContainerId", "toContainerId", "quantity" },
    properties = {
      itemId = { type = "string", minLength = 1 },
      fromContainerId = { type = "string", minLength = 1 },
      toContainerId = { type = "string", minLength = 1 },
      quantity = { type = "integer", minimum = 1, maximum = 1000 }
    }
  },
  run = function(ctx, input)
    local summary = ctx.inventory.summaryAfterTransfer(input)
    local bag = ctx.read(input.toContainerId)
    if summary.targetMassG > bag.components["demo.inventory"].capacityMassG then
      return { rejected = { code = "CAPACITY_EXCEEDED" } }
    end
    return {
      result = { transferredQuantity = input.quantity },
      effects = {
        { kind = "inventory.transferQuantity", itemId = input.itemId,
          fromContainerId = input.fromContainerId,
          toContainerId = input.toContainerId, quantity = input.quantity }
      }
    }
  end
}
