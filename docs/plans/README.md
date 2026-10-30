# 计划文档

收录待讨论、待验证或待实施的需求、调研、设计提案及实施计划。计划被接受不代表功能已经实现。

新增计划时，在下表登记，并在正文写清目标、范围、待确认问题、实施步骤与验收条件。

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| [轻量跑团规则与前端方案](games/lasers-and-feelings/README.md) | 草案 | Lasers & Feelings v1.4 完整官方规则书、中文整理、配置包准备及基于首测工程的叙事前端方案；讨论后再实现 |
| [更新问题 Issues](Issues/README.md) | 进行中 | 后续问题统一索引、模板，并链接已有设计议题 |
| [首测版工程设计](<project planning/first-test-engineering-design.md>) | 进行中 | 首测技术基线、独立文件数据管理模块、房间与实例结构、事务/恢复、动态 Lua 及本机 HTTP/WS；已有本机首测实现，实际状态见当前工程 |
| [首测版施工计划](<project planning/first-test-construction-plan.md>) | 进行中 | E0—E6 工作包、依赖、退出条件与故障验收矩阵；首测施工顺序的统一入口；工程自动验收已落地，独立作者试写待验收 |
| [Lua 简化编写接口与可恢复流程方案](<project planning/lua-authoring-facade.md>) | 进行中 | 已有 A0 同题稿与 A1 同步内存简化层，56 项断言通过；正式首测已实现持久流程与短声明，独立作者试写待验收 |
| [工程规划 Issue](<project planning/Issue/README.md>) | 进行中 | Lua 编写简化方案获准分期推进，同步原型已有验证，完整验收待完成 |
| [Lua 规则与流程脚本设计参考](<project planning/lua-script-reference/README.md>) | 草案 | 旧样例对照索引：9 个脚本与数据保留，原协议正文已归档；现行编写方向见宿主 API 与简化方案 |
| [前后端对接与同步契约设计](<project planning/frontend-backend-contract.md>) | 草案 | 逻辑协议与 SDK、HTTP/实时映射、授权投影、快照恢复、Lua 动态动作目录及资源接口 |
| [系统模块分层与职责设计](<project planning/module-responsibilities.md>) | 草案 | 从原分析第 2 节拆出：模块层级、职责、协作关系及业务场景映射 |
| [抽象数据结构与容器设计](<project planning/data-container-model.md>) | 草案 | 长期房间与主机权威、个人事件记录、统一实例、原始/组合数值、类型化引用与事件规则入口，以及 CRUD 和内核约束 |
| [后端、自定义能力与联机方案分析](<project planning/backend-network-analysis.md>) | 草案 | 基于跑团与联机调研，分析数据模型、容器、Lua 规则与流程、运行中新增规则与版本管理、持久流程、授权、联机适配及资源管理；Lua 语言已选定，首测已验证 Python/Lua/文件/本机 HTTP/WS，更广范围仍待验证 |
| [COC 与线上跑团的工程构成调研](coc-online-trpg-research.md) | 进行中 | 从图谱分支、规则元素与对象、内容类型及格式用途三条主线开展调研；已整理首轮公开资料，完整规则核查与平台实测待开展 |

计划落地后，将有效结论整理到 [当前文档](../current/README.md) 或 [通用标准](../standards/README.md)，再将原计划归档到 [历史目录](../history/README.md)，补充结果和后续文档链接。部分落地的计划应明确已完成与剩余内容。

维护规则见 [文档维护标准](../standards/document-maintenance.md)。
