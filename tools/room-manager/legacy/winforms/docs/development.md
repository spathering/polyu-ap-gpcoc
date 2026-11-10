> 2026-11-09：WinForms 版本已由 [Python 管理器](../../../README.md) 替代。本目录保留历史实现和验收，旧测试脚本不作为当前施工入口。

# 独立房间管理器开发与验证

- 文档类型：历史
- 文档子类：工程
- 状态：已归档
- 创建日期：2026-11-05
- 最后更新：2026-11-05
- 关联文档：[工具入口](../../../README.md)、[使用说明](usage.md)、[验收结果](acceptance.md)、[工程设计](../../../../../docs/plans/room-manager-design.md)

## 1. 构建

使用系统 .NET Framework x64 C# 编译器，源码兼容 C# 5，无第三方运行库。构建入口为 `build.ps1`，生成 `dist/RoomManager.exe`、框架/DPI 配置、工具配置、依赖清单与发布摘要。无需 npm、Python、宿主源码或网络安装步骤。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/room-manager/build.ps1
```

构建脚本每次记录当前 EXE SHA-256；编译器会写入构建时间等信息，不承诺重复构建字节完全相同。程序请求普通用户权限，以 .NET Framework 4.8、Windows x64 为运行基线。

## 2. 代码职责

| 路径 | 职责 |
| --- | --- |
| `src/Program.cs` | 读取配置、启动桌面窗体 |
| `src/UI/MainForm.cs` | 登录、列表、表单、冲突比较、导入/上传/下载、备份、回执及用例协调 |
| `src/Protocol/ApiClient.cs` | HTTP/WS、Cookie/CSRF、禁止跳转、KP 检查、封套与重连 |
| `src/Protocol/Json.cs` | JSON、规范比较及 begin/part/end 快照装配 |
| `src/Protocol/Validate.cs` | 已知操作的字段类型、必填、枚举、范围和结构校验 |
| `src/Observation/Observer.cs` | 分来源基线、字段差异、观察段、记录和字节限额 |
| `src/LocalSettings/` | 工具配置、本地关注与最小命令元信息 |

首版用例协调仍在 MainForm 中，没有单独 Application 程序集或空占位目录。接口层和观察层可独立被测试程序引用。实际表单来自服务器已知操作 schema 的属性，操作白名单固定；未知操作不自动获得写入口。服务器保留最终业务校验责任。

## 3. 并发与边界

HTTP 使用异步调用，WS 只有一个接收/退避循环，管理轮询单任务执行；普通管理按钮共用忙状态。界面轮询 500 ms，管理数据默认 2 s，失败后以 2—16 s 退避重试；数据变化的比较放在后台并加锁，返回结果通过会话代号检查，退出后旧任务不能写入新会话。每次重连和 authority 改变重建观察基线，降权直接结束管理会话。

协议 1，命令上限 64 KiB，WS 完整快照上限 2 MiB，单条 WS 消息上限 256 KiB；普通 HTTP JSON 响应最多 16 MiB，素材最多 10 MiB。连接超时 10 s，HTTP 请求/响应读取各有 15 s 限制，重连退避 0.5—5 s。列表每页 500 项，只呈现已经收到的授权投影，不调用虚构的分页接口。

来源时间是本机观察时间，未收到的中间态不补造。命令最小记录在请求前写入本地，原封套只在内存；重试沿用原 commandId。配置等非实体写入仅有前置比较，存在检查/提交间竞争。当前保存本地设置采用临时文件替换；不同进程共享同一设置目录会有最后写入者覆盖，需用 `--settings-dir` 隔离。

## 4. 测试

从项目根目录运行以下命令，测试需要已有宿主测试环境；这是测试依赖，不是工具运行依赖。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -X utf8 tools/room-manager/tests/run.py
```

测试驱动创建 `.test-output/<时间>/host`，用随机空闲回环端口启动真实宿主，运行 C# 单元/协议/两会话集成与 WinForms 窗口测试，再真实重启宿主并从复制后的发布目录启动原生 EXE。结束时关闭测试宿主，生产房间不参与测试。每次输出有 JSON 报告、日志、截图和隔离存档；该目录已忽略，不作为发布物。

`Integration.cs` 覆盖分片、差异、限额和现行管理操作；`ProtocolEdges.cs` 覆盖 CSRF、Origin、退出、跳转、服务不可达；`GuiSmoke.cs` 打开真实窗口并通过控件事件提交、比较冲突、维护关注、通过本进程窗口消息取消原生确认框及验证大列表；`Reconnect.cs` 与驱动协作验证宿主重启。验收报告应记录真实运行结果，不能把源码中的断言数量当作通过数量。

首版不改宿主契约，不实现 H1/H2 权威历史与 S1/S2 完整存档管理。扩展前仍按工程占用规范登记，后端问题通过独立 Issue 协调。
