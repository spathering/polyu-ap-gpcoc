# 首测 Lua 规则与流程编写

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-10-30
- 最后更新：2026-10-30
- 关联文档：[首测运行](first-test.md)、[可执行样例](../../../engineering/rulepacks/demo/README.md)、[原简化方案](<../../plans/project planning/lua-authoring-facade.md>)、[ISSUE-001](<../../plans/project planning/Issue/lua-authoring-simplification.md>)

## 1. 一条操作写一行业务调用

每个 `.lua` 文件返回一个规则或流程定义。文件名不作规则 ID，顶层 `return` 不能遗漏；规则函数无需返回复杂效果结构。

```lua
return rule('my.damage', {'actor', 'amount'}, function(r, actor, amount)
  r.damage(actor, amount)
end)
```

传入的是实例 ID，使用配置判断同类物品，用标签判断类别：

```lua
assert(r.matches(item, 'demo.item'))
assert(r.hasTag(item, 'melee'))
r.transfer(item, bag, quantity)
```

`{'actor','amount'}` 同时决定函数参数顺序、后端输入校验、目录说明和前端表单。可用类型为 actor、skill、item、bag、amount（非负整数）、quantity（正整数）、text、choice（布尔）。同类多个参数使用 `{'attacker:actor','target:actor','amount'}`，冒号左侧为参数名，右侧为类型；顺序严格按数组。首测不接受无序 map 作为输入声明。

## 2. 常用接口

| 调用 | 语义 |
| --- | --- |
| `r.check(actor, skill)` | 返回 `{rolled,target,passed}`；技能必须归属该角色，操作者须控制该角色 |
| `r.damage(actor, amount)` | demo 算法扣除护甲后减 HP，最低 0 |
| `r.transfer(item, bag, quantity)` | demo 容量校验后原子转移，整叠保留 ID，部分转移创建新实例 ID |
| `r.number(id, key)`、`r.read(id)` | 读取当前拟状态，注册实际读集；read 返回授权数据副本 |
| `r.set(id, key, value)` | 修改已有普通数值；不能直接改 quantity/unitMass/capacity，仍检查控制权及模型范围 |
| `r.hasTag(id, tag)`、`r.matches(id, configurationId)` | 标签/配置判断，不以名称判断身份 |
| `r.related(id, relationType)`、`r.items(bag)` | 关系目标 ID 列表或容器内容副本，跟踪关系集合读版本 |
| `r.roll(sides)` | 主机随机服务，先持久记录再返回，不可在只读计算中使用 |
| `r.call(ruleId, ...)` | 调用同修订规则；检查调用成环/深度和模式 |
| `r.readData(filename)` | 读取已导入并固定到修订的 JSON 数据副本，不是任意文件读取 |
| `r.result(nodeId)` | 流程后续阶段读取已提交节点结果；不存在返回 nil |

便捷 check/damage/transfer 在当前 demo 包中绑定 `demo.lib.*`；业务算法在这些 Lua 文件中，不在通用数据模块。自定义算法可调用自己的规则 ID。`r.move` 是 transfer 使用的内核搬移原语，仍检查数量、持有和目标类型；容量业务由 demo Lua 负责。

规则中的改动先写拟视图，后续调用能读到它；任何规则错误、非法原语、超时、超限、提交前冲突都会使当前阶段整体失败。即使用 `pcall` 吃掉宿主错误，也不能把已污染阶段提交。已提交的前序流程阶段不因后序失败回滚。

## 3. 只读组合值和数据文件

```lua
return rule('my.attack', {'actor'}, function(r, actor)
  return r.number(actor, 'attack') + r.readData('environment.json').attackBonus
end, {mode='calculation'})
```

同时导入 `environment.json`：`{"attackBonus":2}`。刷新计算不会写存档、触发随机或调用 action。计算结果不必作为冗余属性持久化。返回值可为 nil、布尔、文本、安全范围内有限数字或 JSON 形状的表；拒绝函数、userdata、循环表、混合键、NaN/Infinity。空表作为对象，非空连续整数键表作为数组。

## 4. 等待、分支与重启

```lua
return flow('my.ruling', {'actor','skill','amount'}, {
  step('check', function(r, actor, skill)
    return r.check(actor, skill).passed
  end, {yes='end', no='ruling'}),
  ask('ruling', {role='kp', seconds=60,
                 yes='apply', no='end', timeout='end'}),
  step('apply', function(r, actor, skill, amount)
    r.damage(actor, amount)
  end)
})
```

这是已运行的阶段式流程。每个 step 单独原子提交；无显式分支时进入下一节点，最后进入 end。分支应返回布尔；存在分支时必须同时写 yes/no。等待节点必须提供 role、seconds、yes/no/timeout，role 可为 kp 或 initiator。节点 ID 在同一流程中唯一，整张图无环。不能跨等待保存 Lua 局部变量、闭包或协程；需要跨阶段的数据用输入、`r.result` 或已经提交的实体状态表达。

KP 同意只解决待办，不把 KP 权限授予发起者。后续阶段重新按发起者当前权限及当前实体状态执行；目标被转走、资源耗尽或撤权时可以进入 needs_attention。管理者可取消，或修正问题后执行 flow.retry 产生新的阶段尝试；重试会重新检查当前状态并生成该新尝试的随机记录。它与断线重发原 commandId 的幂等恢复不同。

## 5. 导入、预览和回退

在操作台选择完整 Lua 文件组及需要的 JSON 数据文件，点击检查并暂存，得到不可变修订 ID。规则 ID 重复、输入声明错误、流程环或显式依赖环会拒绝整组。声明依赖使用 `{dependencies={'my.other'}}`；动态 `r.call` 还会做运行时环检测。内部库标记 `{public=false}`，KP 专用入口用 `{kp=true}`。

`GET /api/v1/admin/artifacts/{revision}` 可查看与当前修订的源码/数据差异。KP 可调用 `/api/v1/preview`，提交 `{revision,rule,input}`；预览在隔离快照执行，固定测试骰面，不提交业务状态。随后用 `rule.activate` 激活指定修订；回退也是激活已有旧修订。激活不会自动迁移现有实体数值。

每条新行动固定当前修订，每个进行中流程固定其启动修订；源码和 JSON 都保存在工件中。因此改写/删除原文件、发布新版便捷库或重启不会替换旧流程。首测手动导入，不监听磁盘变化自动激活。

只允许 KP 导入可信规则。运行器限制 Lua 全局能力、Python 属性桥、文件/网络访问及资源用量，但不是供陌生人任意执行恶意代码的安全托管平台。此版本 API 的可用性与独立制作者的低门槛体验是两项不同验收；后者仍需实际试写，ISSUE-001 保持开放。
