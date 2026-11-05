# 包级验收

所有输出位于本包`tests/output/`，已忽略；不使用工程默认游玩存档，不运行工程回归测试。

```powershell
& '.\engineering\.venv\Scripts\python.exe' -B '.\rulepacks\mini-detective-pack\tests\verify_automation.py'
& '.\engineering\.venv\Scripts\python.exe' -B '.\rulepacks\mini-detective-pack\tests\verify_package.py'
& '.\engineering\.venv\Scripts\python.exe' -B '.\rulepacks\mini-detective-pack\tests\run_ui.py'
& '.\engineering\.venv\Scripts\python.exe' -B '.\rulepacks\mini-detective-pack\tests\verify_account_launchers.py'
```

自动化专项创建真实隔离宿主，检验固定行动、权限、私密知识、费用、产出、转交、防御及提交后响应丢失恢复，并运行桌面浏览器检查。其余命令分别回归原规则、三身份界面和五个原生入口；均会停止自己启动的进程，临时口令不写入报告。每次测试均创建新输出目录，不覆盖既有游戏数据。

| 结果 | 入口 |
| --- | --- |
| 自动行动与场景界面109项（包含逐PL探索地图、KP手动推进、场景交互、总开关及请求恢复） | [automation-results.json](automation-results.json) |
| 真实HTTP权限、规则、幂等、两日路线与重启保持25项 | [results.json](results.json) |
| 三身份浏览器分页、私密地图、队列及管理表单17项 | [ui-results.json](ui-results.json) |
| 五个真实exe、服务复用、四预设／初始道具、五账号浏览器与停止服务40项 | [launcher-results.json](launcher-results.json) |

`verify_ui.py URL PASSWORD_FILE`供已有隔离服务联调使用，不是普通玩家入口。截图在忽略的output目录。合计191项检查。暂无物理断电、LAN／公网、4人完整跑团、在线恢复、NPC自主决策和多队速度调度验收。
