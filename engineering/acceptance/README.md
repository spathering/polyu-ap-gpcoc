# 首测验收驱动

从项目根执行：

```powershell
engineering/.venv/Scripts/python -m pytest engineering/backend/tests -q --junitxml=engineering/.test-output/acceptance.xml
```

`offline_server.py` 在验收宿主及其 Python 子进程中拒绝非回环 connect/sendto/DNS，并先证明拒绝生效；这是应用进程网络能力限制，不修改系统网络或防火墙。

真实浏览器测试默认使用已安装的 Edge，通过 Playwright 创建隔离上下文。缺少浏览器会失败，不按跳过算成功。`crash_worker.py` 仅对 pytest 提供的临时数据目录执行 os._exit 故障注入。`server_probe.py` 是启动诊断工具，可在启动问题时周期输出线程栈；正式入口不启用它。

聊天室专项为 `test_chat.py` 与 `test_chat_network.py`，包含真实进程提交故障、三浏览器同步/私聊/撤权和 SDK 接入；新增阶段结果见 [聊天验收摘要](chat-results-2026-10-30.json) 与 [聊天室说明](../../docs/current/engineering/chat-backend.md)。

验证范围、实测数字与作者试写待办见 [验收报告](../../docs/current/engineering/first-test-acceptance.md)。测试密码仅用于测试创建的临时账号。正式数据禁止放入 `.test-output/`。
