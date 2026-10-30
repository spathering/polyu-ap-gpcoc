# 文档索引

本目录按文档用途与生命周期组织项目知识。

| 目录 | 含义 | 入口 |
| --- | --- | --- |
| `current/` | 当前文档入口，下分设计与工程 | [当前文档索引](current/README.md) |
| `current/design/` | 当前有效的项目目标、设计与约束 | [设计文档索引](current/design/README.md) |
| `current/engineering/` | 与当前代码、配置和文件结构一致的工程说明 | [工程文档索引](current/engineering/README.md) |
| `plans/` | 尚待讨论、验证或实施的需求、调研与方案 | [计划文档索引](plans/README.md) |
| `history/` | 已被替代、取消或完成归档的材料 | [历史文档索引](history/README.md) |
| `standards/` | 跨阶段适用的通用规则和标准 | [通用标准索引](standards/README.md) |

开始使用首测版请阅读 [安装与运行](current/engineering/first-test.md)、[Lua 编写](current/engineering/lua-authoring.md) 和 [验收报告](current/engineering/first-test-acceptance.md)。

聊天室后端已实现的结构、权限及接口见 [聊天室后端](current/engineering/chat-backend.md)。

建议先阅读 [项目概况](current/design/project-overview.md)，再按需要查阅计划或标准。施工前必须检查 [hierarchy 目录与施工登记](current/engineering/hierarchy.md)，登记自己的 ID 与使用或改动范围，结束后释放。

分类取决于内容用途：标准放入 `standards/`，即使它目前正在生效；未落地方案放入 `plans/`，即使它已获确认。历史文档仅用于追溯，不作为当前操作依据。

工程规划中的待解决设计问题见[Issue 索引](<plans/project planning/Issue/README.md>)；Lua 首轮参考样例已归入[工程规划目录](<plans/project planning/lua-script-reference/README.md>)，其编写体验仍需简化。

维护方式见 [文档维护标准](standards/document-maintenance.md)。各分类的 `README.md` 维护本分类的文档清单。

后续更新的问题入口为 [Issues](plans/Issues/README.md)，新增问题使用其中的模板；原规划 Issue 保留正文并通过该索引链接。Windows 快速使用见 [exe 工具说明](current/engineering/desktop-tools.md)。
