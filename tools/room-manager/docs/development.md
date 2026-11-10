# Python 管理器构建与模块

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-11-09
- 最后更新：2026-11-09
- 关联文档：[使用说明](usage.md)、[验收](acceptance.md)、[LAN 架构](../../../docs/current/engineering/network-lan.md)

## 源码与构建

已验证 Windows x64、CPython 3.14.2、Tk 8.6。运行依赖固定于 `requirements-runtime.lock`，打包/测试依赖固定于 `requirements-build.lock`。旧 C# 源码、发布物、文档与测试保留在 `legacy/winforms/`，不再作为当前入口。

从工具目录执行：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-build.lock
.venv/Scripts/python manager.py
.venv/Scripts/python build.py
```

`build.ps1` 为相同 Python 构建入口；`start.cmd` 优先启动已打包 EXE，否则使用本工具的 Python 环境。PyInstaller 将管理器、Tk 与独立 LAN 包一同收集到 `dist/RoomManager/`，没有引用宿主 Python 环境、backend 模块或房间存档。发布清单记录版本、EXE 及源文件摘要。

| 模块 | 职责 |
| --- | --- |
| manager.py | 命令行、设置目录和两个窗口入口 |
| python/room_manager/gui.py | Tk 窗口、字段表单、用例与界面线程调度 |
| python/room_manager/protocol.py | HTTP Cookie/CSRF、WS 完整快照、权限、重连及封套 |
| python/room_manager/state.py | 本地最小设置、观察基线与限额 |
| engineering/network-lan/src/onlinecoc_lan/ | 独立 LAN 网关及可嵌入/独立运行的 GUI；不依赖管理器或后端实现 |

HTTP/WS 工作位于后台线程，Tk 控件只在主线程访问；后台结果携带会话代号，断开或切换后旧结果被丢弃。管理操作和 admin 轮询各限一个任务，结果队列上限 16，WS 分片在接收线程验证后才发布。列表按 500 项呈现，原始 JSON 保留未识别字段只读，不进行整对象写回。

## 验证入口

从项目根目录运行：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
# 可选：填当前机器实际 LAN IPv4；省略则使用回环进行可复现验证。
$env:ONLINECOC_TEST_LAN_IP='本机局域网IP'
tools/room-manager/.venv/Scripts/python tools/room-manager/tests/verify_python.py
tools/room-manager/.venv/Scripts/python tools/room-manager/tests/verify_distribution.py
```

集成测试借用已有 `engineering/.venv` 启动隔离宿主，将房间、主机发现记录和截图全部放入 `.test-output/`。这属于开发测试依赖，打包程序不依赖它。分发测试复制整个发布目录，再分别打开管理器和独立 LAN 面板，确认原生窗口存在并正常关闭。测试不更改防火墙，不读取真实房间凭据。

当前选型参考：[aiohttp 服务端接口](https://docs.aiohttp.org/en/stable/web_reference.html)、[websockets 同步客户端接口](https://websockets.readthedocs.io/en/stable/reference/sync/client.html)，2026-11-09 核对；实际版本以锁文件为准。
