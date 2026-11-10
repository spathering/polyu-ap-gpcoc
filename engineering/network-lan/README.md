# OnlineCOC 局域网联网模块

独立 HTTP/WebSocket 网关，连接已运行的本机宿主。模块不导入后端、不读写存档、不执行游戏规则。设计、权限边界及限制见[工程文档](../../docs/current/engineering/network-lan.md)。

常用 GUI 在[Python 房间管理器](../../tools/room-manager/README.md)的“局域网联机”页；打包 EXE 支持 `--lan` 单独打开面板。

独立安装与启动（项目根目录）：

```powershell
python -m pip install -r engineering/network-lan/requirements.lock
python -m pip install --no-deps -e engineering/network-lan
python -m onlinecoc_lan --gui
# 或独立命令行运行，按实际宿主与网卡填写地址：
python -m onlinecoc_lan --upstream http://127.0.0.1:8765 --bind 192.168.1.20 --port 8877
```

其他电脑连接 `http://192.168.1.20:8877`。此地址仅为示例，必须替换为当前机器实际 IP。HTTP 仅用于可信局域网；Windows 防火墙端口放行由操作者处理。Ctrl+C 停止网关，原宿主继续运行。默认 CLI 只绑定回环，需明确指定 LAN 地址才会开放局域网。
