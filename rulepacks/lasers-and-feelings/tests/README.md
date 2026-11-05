# 配置包测试与结果

当前验收入口是 `verify_package.py` 和 `verify_ui.py`。通过文档 CLI、公开 HTTP/机器契约与真实浏览器使用现有宿主，禁止修改工程源码、契约或运行存档。

| 验证 | 结果与范围 |
| --- | --- |
| [规则接口摘要](package-results.json) | 52 项；同一修订多次行动、普通玩家主检定与协助、准备／专长、关系绑定、并发消费、取消、洞察状态 |
| [浏览器摘要](ui-results.json) | 25 项；同一浏览器普通标签页三账号并行、默认入口隔离、刷新与退出隔离、Cookie 属性、跨槽位 CSRF 拒绝、Origin 检查、操作日志隔离、网页导入、申请审核、私密冒险、建卡建船、场景、协助、丢回包刷新恢复、主检定、私密问答与移动布局 |
| [exe 启动摘要](launcher-results.json) | 10 项；工作目录独立、缺文件报错、中文与空格路径、首次初始化、账号登录、退出清理及重启 |

从项目根目录运行：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
engineering/.venv/Scripts/python.exe -B rulepacks/lasers-and-feelings/tests/verify_package.py
engineering/.venv/Scripts/python.exe -B rulepacks/lasers-and-feelings/tests/verify_ui.py
engineering/.venv/Scripts/python.exe -B rulepacks/lasers-and-feelings/tests/verify_launcher.py
```

浏览器验证使用现有 Playwright 和 Chromium，缺少默认 Chromium 时尝试系统 Edge；不安装新依赖。每次生成临时密码、全新存档和空闲本机端口，输出留在 `output/` 并排除入库，结束停止自己启动的宿主。若进程异常中止，先确认临时服务停止再重复运行，不使用工程正在游玩的存档。

问答状态测试可能通过明确的 KP 合成夹具设置洞察，用来验证状态与受众，不作为自然随机出现洞察的证据。原骰比较和成功数由真实规则结果独立核算。测试不证明主持人回答在故事意义上真实，也不替代远程部署、断电容灾或长期作者体验。

早期 27 项固定名单实验见[历史说明](../docs/history/2026-10-31-cooperation-validation.md)。`fixtures/`、`verify_cooperation.py` 和 `cooperation-results.json` 只保留该研究的可复现证据，不纳入当前发行包通过项重复计数。
