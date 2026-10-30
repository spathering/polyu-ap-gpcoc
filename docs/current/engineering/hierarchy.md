# 工程目录与施工登记

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-10-29
- 最后更新：2026-10-30
- 最近目录核对：2026-10-30
- 关联文档：[工程文档索引](README.md)、[文档维护标准](../../standards/document-maintenance.md)

## 工程实际目录

以下清单只记录实际存在的项目文件。`engineering/` 已包含本机首测后端、独立文件数据管理、Lua/流程执行器、SDK、操作台、规则包及验收驱动；原同步内存实验保留。新增、移动、重命名、删除文件时，必须在同一施工任务内同步本清单。

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
| `docs/plans/games/README.md` | 轻量跑团资料与适配计划索引 |
| `docs/plans/games/lasers-and-feelings/frontend-design.md` | 角色、协助检定、叙事和主持工作台前端方案 |
| `docs/plans/games/lasers-and-feelings/package-preparation.md` | 规则包准备、对象映射与实际后端能力边界 |
| `docs/plans/games/lasers-and-feelings/README.md` | 轻量科幻跑团规则资料与前端方案入口 |
| `docs/plans/games/lasers-and-feelings/rules.md` | 完整规则中文整理、选项表与待裁定事项 |
| `docs/plans/games/lasers-and-feelings/sources/lasers-and-feelings-original.pdf` | 官方 Lasers & Feelings v1.4 完整一页规则书 |
| `docs/plans/games/lasers-and-feelings/sources/lasers-and-feelings-original.txt` | 官方规则书全页提取正文 |
| `docs/plans/games/lasers-and-feelings/sources/README.md` | 官方规则来源、版本、许可与完整性核验 |
| `docs/plans/games/lasers-and-feelings/sources/source-checksums.txt` | 原始 PDF 与提取正文的 SHA-256 摘要 |
| `docs/plans/project planning/first-test-engineering-design.md` | 首测工程设计与实施对照，保留设计基线 |
| `docs/plans/project planning/first-test-construction-plan.md` | 首测 E0—E6 任务与验收基线，独立作者试写待验收 |
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
| `.gitignore` | 首测实现 / 测试 / 配置 |
| `docs/current/engineering/first-test.md` | 工程运行与验收文档 |
| `docs/current/engineering/lua-authoring.md` | 工程运行与验收文档 |
| `engineering/acceptance/crash_worker.py` | 首测实现 / 测试 / 配置 |
| `engineering/acceptance/README.md` | 工程运行与验收文档 |
| `engineering/acceptance/server_probe.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/pyproject.toml` | 首测实现 / 测试 / 配置 |
| `engineering/backend/scripts/run.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/__init__.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/assets.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/cli.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/contracts.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/errors.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/execution.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/gateway.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/host.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/identity.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/lua_runtime.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/model.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/registry.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/src/onlinecoc/server.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/tests/conftest.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/tests/test_adapters.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/tests/test_faults.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/tests/test_foundation.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/tests/test_host.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/tests/test_model_contracts.py` | 首测实现 / 测试 / 配置 |
| `engineering/backend/tests/test_network.py` | 首测实现 / 测试 / 配置 |
| `engineering/client-sdk/client.js` | 首测实现 / 测试 / 配置 |
| `engineering/contracts/fixtures/entity-invalid-number.json` | 机器契约 / 样例 / 依赖证据 |
| `engineering/contracts/fixtures/entity-valid.json` | 机器契约 / 样例 / 依赖证据 |
| `engineering/contracts/fixtures/room-initial.json` | 机器契约 / 样例 / 依赖证据 |
| `engineering/contracts/messages.json` | 机器契约 / 样例 / 依赖证据 |
| `engineering/contracts/models.json` | 机器契约 / 样例 / 依赖证据 |
| `engineering/contracts/operations.json` | 机器契约 / 样例 / 依赖证据 |
| `engineering/contracts/README.md` | 工程运行与验收文档 |
| `engineering/data-management/onlinecoc_data/__init__.py` | 首测实现 / 测试 / 配置 |
| `engineering/data-management/onlinecoc_data/ports.py` | 首测实现 / 测试 / 配置 |
| `engineering/data-management/onlinecoc_data/store.py` | 首测实现 / 测试 / 配置 |
| `engineering/data-management/pyproject.toml` | 首测实现 / 测试 / 配置 |
| `engineering/dependency-manifest.json` | 机器契约 / 样例 / 依赖证据 |
| `engineering/requirements-dev.lock` | 依赖精确版本及安装包摘要 |
| `engineering/requirements-runtime.lock` | 依赖精确版本及安装包摘要 |
| `engineering/rulepacks/demo/attack.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/check-library.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/damage-library.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/damage.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/environment.json` | 机器契约 / 样例 / 依赖证据 |
| `engineering/rulepacks/demo/environment.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/README.md` | 工程运行与验收文档 |
| `engineering/rulepacks/demo/rules.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/ruling.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/timed.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/transfer-library.lua` | 首测实现 / 测试 / 配置 |
| `engineering/rulepacks/demo/transfer.lua` | 首测实现 / 测试 / 配置 |
| `engineering/test-console/app.js` | 首测实现 / 测试 / 配置 |
| `engineering/test-console/index.html` | 首测实现 / 测试 / 配置 |
| `engineering/test-console/style.css` | 首测实现 / 测试 / 配置 |
| `docs/current/engineering/first-test-acceptance.md` | 首测验收文档 / 证据 / 驱动 |
| `engineering/acceptance/offline_server.py` | 首测验收文档 / 证据 / 驱动 |
| `engineering/acceptance/results-2026-10-30.json` | 首测验收文档 / 证据 / 驱动 |
| `docs/current/engineering/desktop-tools.md` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `docs/plans/Issues/issue-template.md` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `docs/plans/Issues/README.md` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `engineering/desktop/build-info.json` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `engineering/desktop/build.ps1` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `engineering/desktop/desktop_host.py` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `engineering/desktop/DesktopTools.cs` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `engineering/desktop/README.md` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `engineering/desktop/tests/test_desktop.py` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `engineering/desktop/verify_environment.py` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `launcher-config.json` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `启动OnlineCOC.exe` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `安装依赖.exe` | Windows 安装/启动工具、配置、测试或更新问题文档 |
| `docs/plans/Issues/issue-002-desktop-interaction-validation.md` | 桌面工具验收记录或后续问题 |
| `engineering/desktop/acceptance-results.json` | 桌面工具验收记录或后续问题 |

| `engineering/backend/src/onlinecoc/chat.py` | 聊天室领域模型、权限、分页及操作 |
| `engineering/backend/tests/test_chat.py` | 聊天室数据/权限/恢复/故障测试 |
| `engineering/backend/tests/test_chat_network.py` | 聊天室 SDK 与真实浏览器联机验收 |
| `docs/current/engineering/chat-backend.md` | 当前聊天室后端、模型、接口及约束 |
| `engineering/acceptance/chat-results-2026-10-30.json` | 聊天室追加与完整回归的机器验收摘要 |

生成目录：`engineering/.venv/` 是依赖环境；`engineering/.runtime/` 存放游玩数据、桌面工具的独立 Python/环境、缓存及日志；`engineering/.test-output/` 存放隔离测试、离线 wheel、截图与报告；Python/pytest 缓存不登记逐文件清单。生成目录仍受其父目录施工占用约束。

## 施工登记

本表是 Agent 和人员共同使用的占用登记表。所有施工开始前必须先读取本文件，按路径范围检查冲突，登记自己的唯一 ID、使用方式与任务。登记后重新读取确认记录仍在且无冲突，才可开始工作。详细规则见 [施工占用与冲突处理](../../standards/document-maintenance.md#8-施工占用与冲突处理)。

<!-- occupancy:start -->
| ID | 路径范围（相对项目根目录） | 方式 | 任务 | 开始时间（含时区） | 最后确认时间（含时区） |
| --- | --- | --- | --- | --- | --- |
<!-- occupancy:end -->

施工结束、取消或交接时必须释放自己的记录；无活动记录表示当前没有已登记的占用，不代表不存在未遵守约定的并发工作。
