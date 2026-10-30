# 首轮 Lua 样例对照索引

本目录保存首轮显式 schema、效果返回和步骤表样例，供回归对照。普通作者的新编写方向统一见[Lua 宿主 API 与简化编写方案](../lua-authoring-facade.md)，可运行简化样例及当前限制见[工程说明](../../../current/engineering/lua-authoring-prototype.md)。

2026-10-29，原编写协议说明已迁至[历史文档](../../../history/2026-10-29-lua-script-reference.md)，由上述方案替代。旧脚本及数据文件保留原位置，未被重写为新 API，也不表示真实后端已经支持这些能力。

| 对照文件 | 保留用途 |
| --- | --- |
| [01-percentile-check.lua](01-percentile-check.lua) | 百分骰计算与原注册负担 |
| [02-apply-damage.lua](02-apply-damage.lua) | 显式伤害效果提案 |
| [03-transfer-item.lua](03-transfer-item.lua) | 容量与转移的旧协议 |
| [04-check-from-file.lua](04-check-from-file.lua) | 授权数据读取提案 |
| [05-check-with-ruling.lua](05-check-with-ruling.lua) | 原始裁定步骤结构 |
| [06-round-status.lua](06-round-status.lua) | 来源状态与轮次提案 |
| [07-timed-choice.lua](07-timed-choice.lua) | 等待与超时分支提案 |
| [08-grant-item.lua](08-grant-item.lua) | 授予效果与能力提案 |
| [09-session-damage-override.lua](09-session-damage-override.lua) | 同 ID 显式覆盖提案；不能与 02 无差别批量注册 |
| [环境数据](data/environment-modifiers.json) | 04 的配套数据 |

本组曾通过的 43 项模拟断言及其范围保存在历史说明，不能替代当前实验宿主的 56 项验证或未来持久恢复验收。问题与剩余验收统一见[ISSUE-001](../Issue/lua-authoring-simplification.md)。
