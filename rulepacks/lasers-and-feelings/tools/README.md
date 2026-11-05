# 配置包工具

| 文件 | 用途 |
| --- | --- |
| `launch.py` | 独立桌面、同源转发、三个隔离会话入口及现有宿主启动 |
| `PackLauncher.cs` | Windows 控制台 exe 启动器源码 |
| `build-launcher.ps1` | 使用 Windows 自带 .NET Framework C# 编译器生成包根目录 exe |
| `launcher-build.json` | 源码、exe 的 SHA-256 与编译器版本 |
| `package.py` / `client.py` | 源组装与公开协议操作 |
| `export.py` | 导出包含 exe、完整源文件与规则书的 ZIP |

从项目根目录重新生成 exe：

```powershell
.\rulepacks\lasers-and-feelings\tools\build-launcher.ps1
```

生成文件为包根目录的 `启动激光与情感.exe`。运行已有 exe 不需要重新编译，不安装额外 Python 依赖，不修改工程文件。它查找项目已有的 `engineering/.venv/Scripts/python.exe`，调用本包 `tools/launch.py`；参数逐项传递，支持路径中的空格和中文。

exe 是控制台入口，支持首次密码交互和 Ctrl+C。进程清理采用 [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) 的退出关闭机制，只约束此启动器及其子进程。验证覆盖强制终止启动器后前端、宿主均停止，以及同一存档重新启动；不依赖枚举、结束其他人的 Python 进程。

运行与数据说明见[使用说明](../docs/usage.md)，exe 专项验证见[测试入口](../tests/README.md)。

前端更新后需停止旧服务再启动；exe 会读取当前 `launch.py` 和 `ui/`，仅修改这些文件无需重新编译 exe。同机测试入口见[使用说明](../docs/usage.md#同一浏览器测试多个账号)。
