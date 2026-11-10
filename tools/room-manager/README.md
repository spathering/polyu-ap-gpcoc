# Python 独立桌面房间管理器

当前版本 0.2.0，界面和客户端已改为 Python/Tkinter。工具仍位于 engineering 之外，通过 HTTP/WebSocket 操作主机权威房间；附带独立 LAN 网关面板。

先启动宿主，再双击 [RoomManager.exe](dist/RoomManager/RoomManager.exe) 或 `start.cmd`。发布目录包含 Python/Tk 运行时，复制整个 `dist/RoomManager/` 即可使用。

- [使用说明](docs/usage.md)：数据管理、规则、观察、回执和 LAN 面板。
- [开发与构建](docs/development.md)：Python 源码入口、依赖锁和打包。
- [验收结果](docs/acceptance.md)：真实宿主、WLAN 地址和原生窗口测试。
- [局域网架构](../../docs/current/engineering/network-lan.md)：独立网关及权限边界。
- [WinForms 历史版本](legacy/winforms/README.md)：已被替代，仅供追溯。

局域网页填写真实本机宿主、实际网卡 IPv4 和共享端口，启动后将地址提供给同一可信局域网的成员。独立面板入口为 `RoomManager.exe --lan`。停止网关不会停止宿主；完整变更历史、存档恢复与公网联机仍未实现。
