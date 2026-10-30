# 工程目录与施工登记

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-10-29
- 最后更新：2026-10-30
- 最近目录核对：2026-10-30
- 关联文档：[工程文档索引](README.md)、[文档维护标准](../../standards/document-maintenance.md)

## 工程实际目录

以下清单只记录实际存在的项目文件。`engineering/` 已包含 Lua 简化编写的同步内存实验宿主、三份规则样例与测试；完整产品后端和联机尚未实现。新增、移动、重命名、删除文件时，必须在同一施工任务内同步本清单。

路径均相对项目根目录。清单覆盖项目维护的文件（含文档与配置）；版本控制内部数据（如 `.git/`）、依赖安装目录、缓存及生成产物不逐文件登记，出现这些目录时应补充目录用途与施工影响范围，不能因此忽略写入冲突。

`.git/` 已用于本地 Git 仓库的版本记录、分支、索引和远端配置，不作为项目文件入库。切换分支、更新索引或提交等操作会影响整个工作区的协作状态，施工前应登记相应范围；初始化与全局分支切换使用整个工程范围 `.`。

| 实际文件 | 用途 |
| --- | --- |
| `AGENTS.md` | Agent 协作与施工要求 |
| `README.md` | 项目入口 |
| `engineering/README.md` | 工程代码目录用途与相关入口 |
| `engineering/lua-authoring-prototype/README.md` | 同步原型用途、运行和边界 |
| `engineering/lua-authoring-prototype/host.lua` | Lua 简化编写同步内存实验宿主 |
| `engineering/lua-authoring-prototype/tests.lua` | 原型行为与失败条件验证套件 |
| `engineering/lua-authoring-prototype/examples/01-check.lua` | 简化检定规则 |
| `engineering/lua-authoring-prototype/examples/02-damage.lua` | 简化伤害规则 |
| `engineering/lua-authoring-prototype/examples/03-transfer.lua` | 简化物品转移规则 |
| `engineering/lua-authoring-prototype/examples/05-check-with-ruling.md` | A0 裁定流程稿，尚不可执行 |
| `docs/current/engineering/lua-authoring-prototype.md` | 原型实际能力、运行与验证限制 |
| `docs/README.md` | 全部文档索引 |
| `docs/current/README.md` | 当前文档分类入口 |
| `docs/current/design/README.md` | 设计文档索引 |
| `docs/current/design/project-overview.md` | 项目目标与阶段概况 |
| `docs/current/engineering/README.md` | 工程文档索引与同步要求 |
| `docs/current/engineering/hierarchy.md` | 实际目录清单与施工登记（本文件） |
| `docs/history/README.md` | 历史文档索引与归档说明 |
| `docs/history/2026-10-29-lua-script-reference.md` | 首轮 Lua 编写协议正文及验证背景归档 |
| `docs/plans/README.md` | 计划文档索引 |
| `docs/plans/project planning/first-test-engineering-design.md` | 首测工程设计：候选技术栈、模块/数据/事务与本机联机基线，待施工 |
| `docs/plans/project planning/first-test-construction-plan.md` | 首测施工计划：E0—E6 工作包、依赖与故障验收矩阵，待施工 |
| `docs/plans/project planning/Issue/README.md` | 工程规划待解决问题索引 |
| `docs/plans/project planning/Issue/lua-authoring-simplification.md` | ISSUE-001：Lua 规则与流程编写体验简化议题 |
| `docs/plans/project planning/lua-authoring-facade.md` | Lua 简化编写接口与可恢复流程候选方案 |
| `docs/plans/project planning/lua-script-reference/README.md` | 旧 Lua 样例对照索引及替代关系 |
| `docs/plans/project planning/lua-script-reference/01-percentile-check.lua` | 百分骰检定规则参考 |
| `docs/plans/project planning/lua-script-reference/02-apply-damage.lua` | 护甲减伤与 HP 效果参考 |
| `docs/plans/project planning/lua-script-reference/03-transfer-item.lua` | 容量校验与物品转移参考 |
| `docs/plans/project planning/lua-script-reference/04-check-from-file.lua` | 读取配置文件的环境检定参考 |
| `docs/plans/project planning/lua-script-reference/05-check-with-ruling.lua` | 检定分支与 KP 裁定流程参考 |
| `docs/plans/project planning/lua-script-reference/06-round-status.lua` | 逻辑轮次状态规则参考 |
| `docs/plans/project planning/lua-script-reference/07-timed-choice.lua` | 限时输入与超时流程参考 |
| `docs/plans/project planning/lua-script-reference/08-grant-item.lua` | 无骰物品授予规则参考 |
| `docs/plans/project planning/lua-script-reference/09-session-damage-override.lua` | 场次临时伤害覆盖参考 |
| `docs/plans/project planning/lua-script-reference/data/environment-modifiers.json` | 环境检定的数据配置参考 |
| `docs/plans/project planning/backend-network-analysis.md` | 后端、自定义能力与联机方案分析草案 |
| `docs/plans/project planning/module-responsibilities.md` | 系统模块分层与职责设计草案 |
| `docs/plans/project planning/data-container-model.md` | 抽象数据结构与容器设计草案 |
| `docs/plans/project planning/frontend-backend-contract.md` | 前后端接口、SDK、授权投影与同步契约草案 |
| `docs/plans/coc-online-trpg-research.md` | COC 与线上跑团的图谱、规则构成及内容类型调研 |
| `docs/standards/README.md` | 通用标准索引 |
| `docs/standards/document-maintenance.md` | 文档维护及施工协调标准 |

## 施工登记

本表是 Agent 和人员共同使用的占用登记表。所有施工开始前必须先读取本文件，按路径范围检查冲突，登记自己的唯一 ID、使用方式与任务。登记后重新读取确认记录仍在且无冲突，才可开始工作。详细规则见 [施工占用与冲突处理](../../standards/document-maintenance.md#8-施工占用与冲突处理)。

<!-- occupancy:start -->
| ID | 路径范围（相对项目根目录） | 方式 | 任务 | 开始时间（含时区） | 最后确认时间（含时区） |
| --- | --- | --- | --- | --- | --- |
<!-- occupancy:end -->

施工结束、取消或交接时必须释放自己的记录；无活动记录表示当前没有已登记的占用，不代表不存在未遵守约定的并发工作。
