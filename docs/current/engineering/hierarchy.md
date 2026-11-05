# 工程目录与施工登记

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-10-29
- 最后更新：2026-11-02
- 最近目录核对：2026-11-02（本次核对 mini-detective-pack 含自动行动服务、分区界面、五个账号入口及验收；全工程核对仍为 2026-11-01）
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
| `rulepacks/AGENTS.md` | 配置包作者只使用工程、不修改工程的施工边界 |
| `rulepacks/lasers-and-feelings/.gitignore` | 独立 L&F 配置包文件 |
| `rulepacks/lasers-and-feelings/assets/README.md` | 独立 L&F 配置包文件 |
| `rulepacks/lasers-and-feelings/config/configurations.json` | 对象配置或原规则静态资料 |
| `rulepacks/lasers-and-feelings/config/lf.json` | 对象配置或原规则静态资料 |
| `rulepacks/lasers-and-feelings/config/README.md` | 对象配置或原规则静态资料 |
| `rulepacks/lasers-and-feelings/docs/history/2026-10-31-cooperation-validation.md` | 当前包文档或历史验证记录 |
| `rulepacks/lasers-and-feelings/docs/history/README.md` | 当前包文档或历史验证记录 |
| `rulepacks/lasers-and-feelings/docs/package-preparation.md` | 当前包文档或历史验证记录 |
| `rulepacks/lasers-and-feelings/docs/README.md` | 当前包文档或历史验证记录 |
| `rulepacks/lasers-and-feelings/docs/rules.md` | 当前包文档或历史验证记录 |
| `rulepacks/lasers-and-feelings/docs/usage.md` | 当前包文档或历史验证记录 |
| `rulepacks/lasers-and-feelings/flows/README.md` | 独立 L&F 配置包文件 |
| `rulepacks/lasers-and-feelings/LICENSE.md` | 独立 L&F 配置包文件 |
| `rulepacks/lasers-and-feelings/manifest.json` | 独立 L&F 配置包文件 |
| `rulepacks/lasers-and-feelings/README.md` | 独立 L&F 配置包文件 |
| `rulepacks/lasers-and-feelings/rules/adventure.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/answer.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/cancel.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/close.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/help.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/library.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/main.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/open.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/profile.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/question.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/README.md` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/rules/ship.lua` | 当前可复用 Lua 规则或规则索引 |
| `rulepacks/lasers-and-feelings/sources/lasers-and-feelings-original.pdf` | 完整原始规则、来源、许可与摘要 |
| `rulepacks/lasers-and-feelings/sources/lasers-and-feelings-original.txt` | 完整原始规则、来源、许可与摘要 |
| `rulepacks/lasers-and-feelings/sources/README.md` | 完整原始规则、来源、许可与摘要 |
| `rulepacks/lasers-and-feelings/sources/source-checksums.txt` | 完整原始规则、来源、许可与摘要 |
| `rulepacks/lasers-and-feelings/start.ps1` | 独立 L&F 配置包文件 |
| `rulepacks/lasers-and-feelings/启动激光与情感.exe` | Windows 原生控制台启动入口 |
| `rulepacks/lasers-and-feelings/tools/PackLauncher.cs` | 配置包 exe 源码及退出进程清理 |
| `rulepacks/lasers-and-feelings/tools/build-launcher.ps1` | 仅在包内生成 exe 与摘要的编译脚本 |
| `rulepacks/lasers-and-feelings/tools/launcher-build.json` | 源码、exe 摘要和编译环境记录 |
| `rulepacks/lasers-and-feelings/tools/README.md` | 包工具、exe 构建和启动清理说明 |
| `rulepacks/lasers-and-feelings/tests/verify_launcher.py` | 原生 exe 的真实启动、退出清理及重启验证 |
| `rulepacks/lasers-and-feelings/tests/launcher-results.json` | 10 项原生启动验证机器结果 |
| `rulepacks/lasers-and-feelings/tests/.gitignore` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/cooperation-results.json` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/fixtures/close.lua` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/fixtures/help.lua` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/fixtures/main.lua` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/fixtures/roll.lua` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/package-results.json` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/README.md` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/ui-results.json` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/verify_cooperation.py` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/verify_package.py` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tests/verify_ui.py` | 包级验证、浏览器验证、机器证据或历史夹具 |
| `rulepacks/lasers-and-feelings/tools/client.py` | 仅使用现有 CLI/HTTP 的独立启动、导出或包工具 |
| `rulepacks/lasers-and-feelings/tools/export.py` | 仅使用现有 CLI/HTTP 的独立启动、导出或包工具 |
| `rulepacks/lasers-and-feelings/tools/launch.py` | 独立启动、同源适配及同机多账号会话槽位 |
| `rulepacks/lasers-and-feelings/tools/package.py` | 仅使用现有 CLI/HTTP 的独立启动、导出或包工具 |
| `rulepacks/lasers-and-feelings/ui/app.js` | 跑团桌面界面、样式或设计 |
| `rulepacks/lasers-and-feelings/ui/frontend-design.md` | 跑团桌面界面、样式或设计 |
| `rulepacks/lasers-and-feelings/ui/index.html` | 跑团桌面界面、样式或设计 |
| `rulepacks/lasers-and-feelings/ui/README.md` | 跑团桌面界面、样式或设计 |
| `rulepacks/lasers-and-feelings/ui/styles.css` | 跑团桌面界面、样式或设计 |
| `rulepacks/README.md` | 独立配置包分类、资料或待实施方案 |
| `rulepacks/mini-detective-pack/README.md` | 铃蔓回转录资料、规则复原、本机实现与自动行动入口 |
| `rulepacks/mini-detective-pack/docs/README.md` | 铃蔓资料与计划文档索引 |
| `rulepacks/mini-detective-pack/docs/sources.md` | 五张规则图、七张工作表、三张UI参考、网络检索及原料冲突证据 |
| `rulepacks/mini-detective-pack/docs/plans/README.md` | 铃蔓规则与配置补全计划索引 |
| `rulepacks/mini-detective-pack/docs/plans/rules.md` | 六维、探索、体力、卡片与战斗的复原及试跑规则草案 |
| `rulepacks/mini-detective-pack/docs/plans/configuration.md` | 参数、对象、权限、状态机与验收规格草案 |
| `rulepacks/mini-detective-pack/docs/plans/scenario.md` | 两日主持场景、地图、库存、线索、谜题及结局补全草案 |
| `rulepacks/mini-detective-pack/docs/plans/map-and-items.md` | 宅邸与岛屿地图、22种道具分布及获取依赖的Mermaid草案 |
| `rulepacks/mini-detective-pack/docs/plans/frontend-design.md` | 新增UI参考适配、KP与PL界面和前端实施计划 |
| `rulepacks/mini-detective-pack/docs/plans/interface-flows.md` | 建卡、KP与PL操作、战斗时序和秘密信息投影Mermaid草案 |
| `rulepacks/mini-detective-pack/raw/12EC99D144C79211680B3CB83DDFDE55.png` | 用户提供的企划玩法原图 |
| `rulepacks/mini-detective-pack/raw/5576AAC5876167733B85FAEE1A978AA5.png` | 用户提供的行动轮、体力与探索原图 |
| `rulepacks/mini-detective-pack/raw/85AD675A5E3B80BE55A62EAB58577AEB.png` | 用户提供的战斗机制原图 |
| `rulepacks/mini-detective-pack/raw/99B0B7DE1C3110F18003D2D0D7A502FF.png` | 用户提供的六维与卡片机制原图 |
| `rulepacks/mini-detective-pack/raw/B1D563E533F8B0012B91AB2A2AE3B32A.png` | 用户提供的战斗示例原图 |
| `rulepacks/mini-detective-pack/raw/铃蔓回转录.xlsx` | 用户提供的场景、角色、日程与后期战斗工作簿 |
| `rulepacks/mini-detective-pack/raw/UI/65cb0a21-b583-4261-8f15-22084de2ffc9.png` | 用户新增的建角界面参考图 |
| `rulepacks/mini-detective-pack/raw/UI/9ea93a5d-5705-4b90-9591-88b7970d3507.png` | 用户新增的背包弹层参考图 |
| `rulepacks/mini-detective-pack/raw/UI/c80d39dd-b28b-4260-9866-3c028e4133a4.png` | 用户新增的叙事与选择主界面参考图 |
| `rulepacks/mini-detective-pack/assets/README.md` | 已下载网络占位素材的用途、许可与绑定索引 |
| `rulepacks/mini-detective-pack/assets/placeholders/manifest.json` | 20份占位素材的来源、作者、许可、摘要与22道具及23地点绑定 |
| `rulepacks/mini-detective-pack/assets/placeholders/CREDITS.md` | 网络占位素材逐件署名、来源与许可 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-lantern.svg` | 网络占位素材：Lantern，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-key.svg` | 网络占位素材：Key，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-hammer-drop.svg` | 网络占位素材：Hammer Drop，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-broadsword.svg` | 网络占位素材：Broadsword，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-candle-light.svg` | 网络占位素材：Candle Light，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-scroll-unfurled.svg` | 网络占位素材：Scroll Unfurled，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-hood.svg` | 网络占位素材：Hood，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-pine-tree.svg` | 网络占位素材：Pine Tree，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-castle.svg` | 网络占位素材：Castle，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/delapouite-film-strip.svg` | 网络占位素材：Film Strip，Delapouite，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/delapouite-rope-coil.svg` | 网络占位素材：Rope Coil，Delapouite，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/delapouite-island.svg` | 网络占位素材：Island，Delapouite，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/delapouite-village.svg` | 网络占位素材：Village，Delapouite，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/delapouite-sailboat.svg` | 网络占位素材：Sailboat，Delapouite，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-meat.svg` | 网络占位素材：Meat，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-round-bottom-flask.svg` | 网络占位素材：Round Bottom Flask，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/sbed-health-normal.svg` | 网络占位素材：Health Normal，sbed，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/skoll-winchester-rifle.svg` | 网络占位素材：Winchester Rifle，Skoll，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/icons/lorc-umbrella.svg` | 网络占位素材：Umbrella，Lorc，CC-BY-3.0 |
| `rulepacks/mini-detective-pack/assets/placeholders/textures/parchment.png` | 网络占位素材：Parchment，Mattias Lejbrink，CC0-1.0 |
| `docs/plans/Issues/issue-003-rulepack-cooperative-ruling.md` | 配置包协作问题：包侧已解决并验证，待工程责任者复核记录 |
| `docs/plans/games/README.md` | 轻量跑团资料与适配计划索引 |
| `docs/plans/games/lasers-and-feelings/README.md` | 已迁入独立配置包的兼容入口 |
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

本次配置包实际新增文件：

| 实际文件 | 用途 |
| --- | --- |
| `rulepacks/mini-detective-pack/.gitignore` | 配置包清单／启动或忽略配置 |
| `rulepacks/mini-detective-pack/config/configurations.json` | 本包场景／对象配置 |
| `rulepacks/mini-detective-pack/config/scenario.json` | 本包场景／对象配置 |
| `rulepacks/mini-detective-pack/docs/implementation.md` | 本包当前实现与运行说明 |
| `rulepacks/mini-detective-pack/manifest.json` | 配置包清单／启动或忽略配置 |
| `rulepacks/mini-detective-pack/rules/advance.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/check.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/combat.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/confirm.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/consume.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/damage.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/enter.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/equip.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/finish.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/profile.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/request.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/resolve.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/rules/sync.lua` | 本包Lua权威规则 |
| `rulepacks/mini-detective-pack/start.ps1` | 配置包清单／启动或忽略配置 |
| `rulepacks/mini-detective-pack/tests/README.md` | 包级验收驱动／机器结果 |
| `rulepacks/mini-detective-pack/tests/results.json` | 包级验收驱动／机器结果 |
| `rulepacks/mini-detective-pack/tests/run_ui.py` | 包级验收驱动／机器结果 |
| `rulepacks/mini-detective-pack/tests/ui-results.json` | 包级验收驱动／机器结果 |
| `rulepacks/mini-detective-pack/tests/verify_package.py` | 包级验收驱动／机器结果 |
| `rulepacks/mini-detective-pack/tests/verify_ui.py` | 包级验收驱动／机器结果 |
| `rulepacks/mini-detective-pack/tools/client.py` | 包侧公开CLI／HTTP启动与适配工具 |
| `rulepacks/mini-detective-pack/tools/launch.py` | 包侧公开CLI／HTTP启动与适配工具 |
| `rulepacks/mini-detective-pack/tools/package.py` | 包侧公开CLI／HTTP启动与适配工具 |
| `rulepacks/mini-detective-pack/ui/app.js` | 本机单标签KP／PL前端 |
| `rulepacks/mini-detective-pack/ui/index.html` | 本机单标签KP／PL前端 |
| `rulepacks/mini-detective-pack/ui/styles.css` | 本机单标签KP／PL前端 |
| `docs/plans/Issues/issue-004-mini-pack-management.md` | 配置包在线恢复与组合管理接口边界 |

账号原生入口新增文件：

| 实际文件 | 用途 |
| --- | --- |
| `rulepacks/mini-detective-pack/KP主持人.exe` | 预设账号Windows原生入口 |
| `rulepacks/mini-detective-pack/PL1观察员.exe` | 预设账号Windows原生入口 |
| `rulepacks/mini-detective-pack/PL2护卫.exe` | 预设账号Windows原生入口 |
| `rulepacks/mini-detective-pack/PL3文献员.exe` | 预设账号Windows原生入口 |
| `rulepacks/mini-detective-pack/PL4医护员.exe` | 预设账号Windows原生入口 |
| `rulepacks/mini-detective-pack/tests/launcher-results.json` | 账号启动器源码、构建、说明或验收 |
| `rulepacks/mini-detective-pack/tests/verify_account_launchers.py` | 账号启动器源码、构建、说明或验收 |
| `rulepacks/mini-detective-pack/tools/AccountLauncher.cs` | 账号启动器源码、构建、说明或验收 |
| `rulepacks/mini-detective-pack/tools/build-launchers.ps1` | 账号启动器源码、构建、说明或验收 |
| `rulepacks/mini-detective-pack/tools/launcher-build.json` | 账号启动器源码、构建、说明或验收 |
| `rulepacks/mini-detective-pack/tools/README.md` | 账号启动器源码、构建、说明或验收 |

生成目录：`rulepacks/mini-detective-pack/runtime/` 为独立游玩数据，含 `room/` 宿主存档、`room-automation/` 自动化队列与凭据及停服备份，`rulepacks/mini-detective-pack/tests/output/` 为隔离测试存档、日志和截图，均忽略且不逐文件登记，仍受对应施工范围约束。`rulepacks/lasers-and-feelings/runtime/` 为独立游玩存档，`rulepacks/lasers-and-feelings/exports/` 为导出 ZIP；均不入库且不逐文件登记。`rulepacks/lasers-and-feelings/tests/output/` 存放配置包的独立实验存档、日志与接口发现结果，不入库、不逐文件登记，仍受对应施工范围约束。`engineering/.venv/` 是依赖环境；`engineering/.runtime/` 存放游玩数据、桌面工具的独立 Python/环境、缓存及日志；`engineering/.test-output/` 存放隔离测试、离线 wheel、截图与报告；Python/pytest 缓存不登记逐文件清单。生成目录仍受其父目录施工占用约束。

本次自动化与界面新增文件：

| 实际文件 | 用途 |
| --- | --- |
| `rulepacks/mini-detective-pack/tools/scene.py` | 当前场景、可达出口及逐PL已探索／一跳周边地图投影 |
| `rulepacks/mini-detective-pack/tools/automation.py` | KP自动处理总开关、固定行动验证、恢复及人工裁决 |
| `rulepacks/mini-detective-pack/ui/workflow.js` | KP／PL分区导航、顶部自动开关和中文结果呈现 |
| `rulepacks/mini-detective-pack/docs/automation-and-ui.md` | 当前自动化、导航、Mermaid、权限及升级说明 |
| `rulepacks/mini-detective-pack/tests/verify_automation.py` | 真实宿主与桌面浏览器自动化专项 |
| `rulepacks/mini-detective-pack/tests/automation-results.json` | 自动化专项机器结果 |

## 施工登记

本表是 Agent 和人员共同使用的占用登记表。所有施工开始前必须先读取本文件，按路径范围检查冲突，登记自己的唯一 ID、使用方式与任务。登记后重新读取确认记录仍在且无冲突，才可开始工作。详细规则见 [施工占用与冲突处理](../../standards/document-maintenance.md#8-施工占用与冲突处理)。

<!-- occupancy:start -->
| ID | 路径范围（相对项目根目录） | 方式 | 任务 | 开始时间（含时区） | 最后确认时间（含时区） |
| --- | --- | --- | --- | --- | --- |
<!-- occupancy:end -->

施工结束、取消或交接时必须释放自己的记录；无活动记录表示当前没有已登记的占用，不代表不存在未遵守约定的并发工作。
