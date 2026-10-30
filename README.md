# OnlineCOC

本项目试实现一个用于线上多人跑团的通用工具，并探索相关的技术与协作方案。

目前处于原型验证阶段，已建立 [Lua 简化编写实验原型](engineering/lua-authoring-prototype/README.md)，尚未实现完整线上跑团功能。自定义规则与流程已选用 Lua，房间长期存档、主机权威与共享剧情进度等设计已确认；后端实现语言及具体架构仍待确定，见[项目概况](docs/current/design/project-overview.md)。

## 工程代码

[`engineering/`](engineering/README.md) 用于存放工程代码及相关构建、测试配置。

## 文档入口

从 [文档索引](docs/README.md) 开始阅读。

| 类型 | 入口 | 内容 |
| --- | --- | --- |
| 当前 | [当前文档](docs/current/README.md) | 分为设计文档与工程文档，工程内容与当前代码对齐 |
| 计划 | [计划文档](docs/plans/README.md) | 待讨论、待验证或待实施的需求与方案 |
| 历史 | [历史文档](docs/history/README.md) | 已被替代、取消或完成归档的记录 |
| 通用标准 | [通用标准](docs/standards/README.md) | 跨阶段适用的约定、规范与维护规则 |

工程规划中待解决的设计问题见[Issue 索引](<docs/plans/project planning/Issue/README.md>)。

新增或修改文档前，请阅读 [文档维护标准](docs/standards/document-maintenance.md)。

Agent 或人员施工前，必须检查 [hierarchy 目录与施工登记](docs/current/engineering/hierarchy.md)，用唯一 ID 登记使用或改动范围，确认无冲突后施工，结束后释放标记。
