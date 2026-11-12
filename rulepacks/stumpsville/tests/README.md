# 配置包验收

测试通过公开 CLI/HTTP/WebSocket 操作真实宿主；数据全部写入本包被忽略的 `tests/output/`，不使用工程存档。测试自动结束自己的服务进程，不写入正式 `runtime/`。

2026-11-12：0.4.1局域网启动新增10组专项验收通过。使用实际 `pythonw.exe` 和Tk窗口，在本机真实WLAN IPv4验证网卡名称、端口与密码校验、首次准备、KP及两PL登录、Origin／本机账号控制边界、地址复制与主持页链接、占用冲突、停止释放端口、重启保留账号／存档、关闭窗口清理，以及实际 `start-lan.cmd` 的中文／空格路径。测试客户端仍在同一物理电脑；不声称已完成跨设备或防火墙环境验收。窗口截图位于 `output/screenshots/lan-running.png`。

2026-11-10 0.4.0通过55组验收：15组已有业务、6组通用自动裁决、7组行动反馈、10组已有浏览器交互、8组场景预设、5组场景恢复及4组场景浏览器闭环。浏览器未捕获 JavaScript 异常；包含旧地址兼容、单页面板开关/折叠/状态恢复、内嵌 KP 裁决、玩家原页结果更新、编辑手记时保留草稿、实时消息、390px窄屏及同浏览器账号隔离。

场景专项遍历全部18个预设，验证成功和失败的真实骰点、叙述、机关／库存／门／线索效果，重复领取与两玩家竞争最后一件物品，旧规则补充安装、背包已满阻止，以及主事务提交后和反馈发布时中断的恢复。自动执行使用现有已登录KP页面，不新增账号、不持久化KP凭据。浏览器覆盖离线等待、重开KP页面自动继续、主动人工申请与真实结果返回；自动队列不会显示为待KP人工批准。截图见 `output/screenshots/scene-action-*.png` 和 `scene-kp-console.png`。

反馈专项验证自动骰点、物品与位置前后值、人工申请等待/批准/拒绝、转交双方资源通知、账号可见性、重启持久化，以及“宿主已提交但反馈阶段中断”后恢复同一行动不重掷。反馈与场景恢复专项显式注入 ConnectionError，预期产生503日志，随后恢复验证通过；不是正常运行故障。业务验收同时包含配对备份恢复到第二个空目录。

2026-11-09 启动修复补验通过5项：Windows PowerShell 5.1 文件解析、真实 `start.cmd` 启动、中文/空格路径与参数透传、独立未初始化存档页面，以及测试进程清理。此前业务和浏览器脚本直接使用 Python，未覆盖 CMD/PowerShell 入口；新增测试补上这一缺口。

从项目根目录运行：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tests/verify_package.py
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tests/verify_ui.py
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tests/verify_automation.py
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tests/verify_feedback.py
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tests/verify_scenes.py
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tests/verify_scene_recovery.py
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tests/verify_scene_ui.py
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tests/verify_launcher.py
engineering/.venv/Scripts/pythonw.exe -B rulepacks/stumpsville/tests/verify_lan.py
```

| 证据 | 内容 |
| --- | --- |
| [lan-results.json](lan-results.json) · [脚本](verify_lan.py) | 10组真实Tk窗口、LAN包入口、多账号、冲突和生命周期验收；pythonw无控制台，完成情况查看结果文件，失败信息在output/lan-error.log |
| [scene-results.json](scene-results.json) · [脚本](verify_scenes.py) | 全部18个预设的8组真实宿主结果、有限库存、失败后果与权限验收 |
| [scene-recovery-results.json](scene-recovery-results.json) · [脚本](verify_scene_recovery.py) | 5组旧规则迁移、中断恢复、容量及手动开关验收 |
| [scene-ui-results.json](scene-ui-results.json) · [脚本](verify_scene_ui.py) | 4组已有KP页面自动执行、玩家过程／结果、断线继续及主动人工裁决 |
| [package-results.json](package-results.json) | 真实宿主业务、权限、幂等、回合/光源、物品碰撞、有限库存、公开/私密、聊天、版本、备份和重启/恢复 |
| [ui-results.json](ui-results.json) | Edge/Playwright，规范页面及旧地址、浮层、控制台裁决、即时反馈、消息、独立会话、1440px与390px布局及JS错误 |
| [feedback-results.json](feedback-results.json) | 7组持久行动通知、变化、隐私、人工回复及中断/重启恢复 |
| [verify_feedback.py](verify_feedback.py) | 隔离真实宿主的反馈专项及包侧故障注入 |
| [automation-results.json](automation-results.json) | 6组自动/人工裁决、宿主权限、复核、重启、规则升级结果 |
| [verify_automation.py](verify_automation.py) | 独立真实宿主的自动裁决专项脚本 |
| [launcher-results.json](launcher-results.json) | Windows PowerShell 5.1 解析及真实 CMD 启动入口的5项验证 |
| [verify_launcher.py](verify_launcher.py) | 独立临时目录、随机端口、不打开浏览器的启动回归脚本 |
| `output/screenshots/` | 场景悬浮面板、主持控制台及消息、地点、窄屏实际截图，可重建 |
| [harness.py](harness.py) | 隔离宿主/适配器生命周期与API账号夹具 |
| [probe_host.py](probe_host.py) | 前期核对 progress 个人记录写入权限的独立探针 |

验收记录包含检查时间和具体断言分组，不能把分组数量等同全部规则覆盖。跨设备LAN、防火墙、完整原版冒险内容、长时间多人压力场景未验收。目录中的运行账号和随机口令不入库；结果JSON与截图不包含口令。

返回[当前实现](../docs/current/implementation.md)。
