# 独立桌面房间管理工具

首版使用 C# WinForms，通过已有 HTTP/WebSocket 接口管理本机正在运行的房间。源码、构建、测试与发布均位于本目录，不属于 `engineering/`，运行时无需工程源码、Python 或虚拟环境。

先单独启动 OnlineCOC 宿主，再打开 [RoomManager.exe](dist/RoomManager.exe)，输入宿主地址和 KP 账号密码。需要 Windows x64 与 .NET Framework 4.8；工具不会启动或关闭宿主。发布时复制整个 `dist/` 目录。

- [使用说明](docs/usage.md)：连接、表单、规则导入、观察、关注、回执与备份。
- [开发与验证](docs/development.md)：构建、模块职责、测试及接口边界。
- [验收结果](docs/acceptance.md)：本次测试证据和验证范围。
- [发布清单](dist/release.json)：版本、协议与 EXE SHA-256。
- [工程文档入口](../../docs/current/engineering/room-manager.md)。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

完整权威变更历史及存档列表、导出、删除、恢复仍在后续阶段。首版的“观察到的变化”是连接期间收到的样本差异，备份功能仅请求宿主创建备份。
