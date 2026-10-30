# 首测可执行规则包

这一目录是当前宿主实际加载的完整规则组。运行和语法见 [Lua 编写说明](../../../docs/current/engineering/lua-authoring.md)，不要与保留的同步内存原型或旧 reference 协议混用。

| 文件 | 用途 |
| --- | --- |
| `rules.lua` | 公开百分骰检定 |
| `check-library.lua` | 技能归属、骰面与目标值算法 |
| `damage.lua`、`damage-library.lua` | 一行伤害调用与护甲算法 |
| `transfer.lua`、`transfer-library.lua` | 一行转移与容量算法 |
| `attack.lua` | 只读组合攻击值 |
| `environment.lua`、`environment.json` | 版本化文件数据与只读计算 |
| `ruling.lua` | 检定失败后问 KP，批准后产生后果 |
| `timed.lua` | 发起者限时选择与超时分支 |

导入时选择本目录全部 `.lua` 及 `.json` 文件，不选 README。不同目录使用的同名 Lua API 不代表协议兼容；以当前编写说明和测试为准。这些是自制工程验证规则，不是完整 COC 规则实现。
