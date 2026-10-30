# 工程代码

首测工程使用 Python 3.14、Lua 5.4、独立文件数据管理模块和本机 HTTP/WebSocket。业务计算由主机执行，网页提供最小操作台。

- [Windows 安装 / 启动 exe 与配置](../docs/current/engineering/desktop-tools.md)
- [后续更新 Issues](../docs/plans/Issues/README.md)
- [安装、启动、备份与恢复](../docs/current/engineering/first-test.md)
- [聊天室后端与 SDK](../docs/current/engineering/chat-backend.md)
- [Lua 规则与流程编写](../docs/current/engineering/lua-authoring.md)
- [验收报告与限制](../docs/current/engineering/first-test-acceptance.md)
- [实际目录和施工登记](../docs/current/engineering/hierarchy.md)

| 路径 | 职责 |
| --- | --- |
| `desktop/` | Windows 两个 exe 的源码、共享配置对接、构建与验收 |
| `backend/src/onlinecoc/` | 领域约束、命令、身份、聊天室、Lua 子进程、持久流程；`server.py` 为本机联网适配器 |
| `data-management/onlinecoc_data/` | 无业务/网络依赖的文件快照、排他锁、CAS、查询、导出与恢复 |
| `contracts/` | 共用模型、命令、操作 JSON Schema 与正反 fixtures |
| `rulepacks/demo/` | 可执行首测 Lua 规则与数据文件 |
| `client-sdk/` | 可替换 Transport 的浏览器客户端 |
| `test-console/` | 三身份操作、规则导入、管理和回执查询 |
| `backend/tests/`、`acceptance/` | 单元、模块、真实进程故障及真实浏览器验收 |
| `requirements-*.lock`、`dependency-manifest.json` | Windows x64 / CPython 3.14 的依赖版本、wheel 摘要及许可证 |
| `lua-authoring-prototype/` | 保留的 A1 同步内存原型，运行协议与首测宿主不同 |

`.venv/` 为开发依赖，`.runtime/` 为建议的手工游玩数据，`.test-output/` 为可重建的测试/离线 wheel/截图产物。它们被 Git 忽略，不能把正式存档放入测试目录。
