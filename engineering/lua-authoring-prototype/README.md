# Lua 简化编写实验原型

用于 ISSUE-001 的 A0/A1 验证，采用 Lua 5.4 语言能力，无第三方 Lua 包。生产后端语言、Lua 嵌入实现及版本依赖仍待选择。

- `host.lua`：同步内存宿主、效果收集、暂存视图和回执。
- `examples/01-check.lua`、`02-damage.lua`、`03-transfer.lua`：短输入声明加普通回调；常用操作一条调用，不返回底层效果表。
- `examples/05-check-with-ruling.md`：A0 流程稿，尚不可执行。
- `tests.lua`：行为和失败用例。旧参考文件保持不变。

`r` 是每次执行注入的 Lua 宿主 API 参数；三个样例的输入、返回、效果和现有函数统一见[工程说明](../../docs/current/engineering/lua-authoring-prototype.md#宿主-api-与三个样例)。目标分层与规则包边界见[主方案](<../../docs/plans/project planning/lua-authoring-facade.md#3-lua-宿主-api-与分层职责>)。

在此目录使用 Lua 5.4 执行：

```text
lua tests.lua
```

本轮通过临时 Python/Lupa 2.8 的 Lua 5.4 引擎运行同一 `tests.lua`，无需将该临时环境加入项目依赖。具体验证与限制见[当前工程说明](../../docs/current/engineering/lua-authoring-prototype.md)。

接口只用于受信作者实验。实体模型是扁平夹具，持有关系为物品到容器的映射；不是正式数据容器实现。宿主仅有对象允许集和 canWrite，未实现细粒度动作能力、网络认证、字段投影和持久化。不应用于公开服务或陌生脚本。
