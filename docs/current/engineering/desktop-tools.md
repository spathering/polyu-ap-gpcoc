# Windows 依赖安装与一键启动

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-10-30
- 最后更新：2026-10-30
- 关联文档：[首测工程](first-test.md)、[工程索引](README.md)、[桌面工具源码](../../../engineering/desktop/README.md)、[更新问题](../../plans/Issues/README.md)

## 使用

在完整工程根目录双击 [安装依赖.exe](../../../安装依赖.exe)，完成后双击 [启动OnlineCOC.exe](../../../启动OnlineCOC.exe)。exe 必须与工程目录及 [launcher-config.json](../../../launcher-config.json) 一起保留，不是可单独搬走的应用包。

安装程序校验并展开官方 Python 3.14.2 x64 完整运行时，创建项目内虚拟环境，依据共享 `engineering/requirements-runtime.lock` 安装 26 项运行依赖，检查版本、模块导入和 `pip check` 后才标记完成。不需要系统 Python、不注册 Python、不修改 PATH 或系统 Python 环境，不需要管理员安装。

启动程序检查环境，尚未安装或依赖锁变化时自动完成必要安装；环境就绪后启动本机服务并打开浏览器。首次启动询问初始密码，初始化 `kp`、`player1`、`player2` 三个首测账号。密码不写入配置或启动日志。后续使用同一存档目录会恢复进度。

启动窗口保持运行，可点击“打开页面”和“取消 / 停止”。停止或关闭窗口时先通知主机正常退出并释放文件锁；超过 30 秒时结束本次子进程树，下次按存档恢复。它不会停止占用相同端口的其他程序。浏览器标签页关闭不等于停止主机。

## 配置的唯一来源

| 配置 | 用途与更新方式 |
| --- | --- |
| `python.version`、`archiveUrl`、`sha256` | 固定运行时版本、完整 zip 和摘要；三项须成组更新并验证 ABI |
| `python.directory`、`cacheFile` | 项目内运行时目录与下载缓存；升级 Python 时使用新的版本目录 |
| `dependencies.lockFile` | 唯一运行依赖版本与 wheel 摘要清单，安装器不另硬编码包版本 |
| `dependencies.environmentRoot` | 虚拟环境根目录；项目位置、Python 摘要或 lock 内容变化会生成新环境 |
| `dependencies.indexUrl`、`wheelDirectory`、`offline` | HTTPS 软件源、本地 wheel 来源与离线模式 |
| `dependencies.probeModules` | 安装后必须可导入的模块，新增关键依赖时同步添加 |
| `application.entryPoint` | 当前桌面宿主入口脚本 |
| `application.dataDirectory` | 房间/账号数据目录，默认与原 CLI 的 `.runtime/demo` 相同 |
| `application.port`、`openBrowser`、`startupTimeoutSeconds` | 回环端口、是否自动打开页面、就绪等待时间 |
| `logsDirectory` | 安装/启动日志目录 |

配置路径均相对 exe 所在工程根目录，拒绝绝对路径与越出工程目录的路径。配置文件不能存放密码、令牌或带账号密码的软件源 URL。更改存档目录表示打开另一份房间，不会自动迁移旧数据。

Python 来源和摘要使用 [官方 Windows 发布清单](https://www.python.org/ftp/python/3.14.2/windows-3.14.2.json) 的标准 x64 完整包；沿用本工程已经验证的 3.14.2，未在本次更换后端 Python 基线。

## 依赖更新与失败恢复

更新包版本时先同步运行 lock、开发 lock 和依赖清单，再运行安装 exe 与相关回归。修改现有配置内容和 lock 不需要重新编译 exe；修改 C# 程序时运行 [构建脚本](../../../engineering/desktop/build.ps1)，同步两个二进制及 `build-info.json`。

新依赖组合使用新的环境目录，保留旧环境，避免失败时破坏上一组合；不移动或覆盖存档。安装中断的环境不会有完成标记，重试会按 lock 重装。已标记环境若检测到依赖损坏，安装 exe 会尝试按原 lock 修复。启动时校验失败会显示错误，可运行安装 exe 修复。旧环境和下载暂存不自动删除。

默认数据与环境在 `engineering/.runtime/`，已被 Git 忽略。项目搬移后重新运行安装程序；Python 可重新验证使用，虚拟环境因绝对路径变化重新建立。同步代码时不要用空存档覆盖已有 `.runtime/demo`。

离线安装需先备好 `python.cacheFile` 对应的官方 zip 和锁对应的 wheel，将 `wheelDirectory` 指向它们并设 `offline: true`；缺包或摘要错误时明确失败。下载内容通过 SHA-256 后才展开，pip 安装使用 `--require-hashes --only-binary=:all:`。

## 自动化和故障定位

窗口下方显示进度，详细日志位于 `logsDirectory`。两个工具通过项目级锁避免同时安装/启动；原 CLI 主机仍由文件数据模块排他锁保护。

测试支持 `--headless`、`--config <文件>`、`--check`；启动额外支持 `--no-browser` 和 `--run-seconds N`。自定义配置只覆盖设置，工程根仍为 exe 所在目录。无人值守首次初始化可使用 `ONLINECOC_BOOTSTRAP_PASSWORD` 环境变量；宿主使用后立即从自身环境移除，避免传给 Lua 子进程。

常见处理：端口占用时修改配置或停止旧服务；依赖损坏时重跑安装器；Python 缓存摘要错误时检查配置和缓存来源；下载/安装失败时查看日志并重试。正式备份恢复仍使用 [首测运维步骤](first-test.md#5-管理和恢复)。

## 本次验证

默认配置的在线下载与安装也已成功执行，项目内默认运行环境已准备好；没有初始化或覆盖默认游玩存档。

8 项真实 exe 自动测试全部通过，无跳过，耗时约 115 秒，见 [机器记录](../../../engineering/desktop/acceptance-results.json)。覆盖全新 Python/虚拟环境安装、重复检查、锁文件变更生成新环境、损坏包修复、启动后执行 Lua 行动、正常停止和重开保持进度、重复工具拒绝、越界路径/错误摘要/缺少离线缓存及端口占用。

验证机器为 Windows x64，构建使用系统 .NET Framework 4.8 编译器。Windows 窗口自动化内核因资源路径缺失未能初始化，重置重试后仍失败；本次没有声称完成窗口视觉、密码弹窗或鼠标操作验收。后续交互核对记录为 [ISSUE-002](../../plans/Issues/issue-002-desktop-interaction-validation.md)。
