# OnlineCOC

本项目试实现一个用于线上多人跑团的通用工具，并探索相关的技术与协作方案。

目前已有可运行的本机首测版：主机权威后端、独立文件数据管理模块、HTTP/WebSocket 联机、Lua 动态规则与可恢复流程、聊天室后端，以及最小浏览器操作台。当前用自制规则验证通用能力，完整 COC 等规则由配置包实现。

从 [安装与运行](docs/current/engineering/first-test.md) 开始；规则制作者阅读 [Lua 编写说明](docs/current/engineering/lua-authoring.md)，验证范围见 [首测验收报告](docs/current/engineering/first-test-acceptance.md)。原 [Lua 同步实验](engineering/lua-authoring-prototype/README.md) 作为独立历史原型保留。

聊天室数据、接口和 SDK 见 [聊天室后端](docs/current/engineering/chat-backend.md)；尚无聊天页面。地图、逻辑图和 2D/3D 空间暂不作为必要实现。

## Windows 快速开始

在工程根目录双击 [安装依赖.exe](安装依赖.exe)，然后双击 [启动OnlineCOC.exe](启动OnlineCOC.exe)。首次启动设置房间初始密码，随后打开本机页面。共享配置为 [launcher-config.json](launcher-config.json)，更新说明见 [桌面工具文档](docs/current/engineering/desktop-tools.md)。

后续更新的问题统一登记到 [Issues](docs/plans/Issues/README.md)，其中保留已有 Lua 设计议题的链接。

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
