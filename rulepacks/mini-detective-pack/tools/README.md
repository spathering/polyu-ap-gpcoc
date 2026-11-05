# 启动与包工具

## 独立服务管理器

双击包根目录的[配置包服务管理.exe](../配置包服务管理.exe)，即可查看服务状态与存档路径，点击“启动服务”“停止服务”或“重启服务”；“打开 KP 页面”用于进入当前服务。默认管理本机8888端口和本包 `runtime/room`。服务停止时可在窗口修改下一次启动的存档目录，重启会沿用实际运行目录。新目录启动后需打开 KP 页面完成首次准备，管理器不设置默认密码。

此程序不要求先登录 KP。关闭管理窗口会保留后台服务；需要停服时点击“停止服务”。已有五个账号 exe 继续适用，与管理器使用相同的启动互斥和监督进程，不会重复启动。

新版服务通过仅限本机当前 Windows 用户的 DPAPI 加密凭据接收停止请求，拒绝网页 Origin／Referer、无凭据和错误凭据的请求。停止后清理该服务关联进程，保留已提交账号和游戏数据。旧版账号入口启动的服务可在核对本工作区、exe 路径、端口及监督进程后通过 Windows Job 关闭整个所属进程树；首次重启后使用新版正常退出接口。旧版前台 PS1 服务缺少控制接口时，仍需在原终端 Ctrl+C 停止一次。

管理器不会按“所有 Python 进程”批量结束任务；端口属于其他程序、其他工作区或伪造的监督 PID 时拒绝关闭。新的 `start.ps1` 前台服务也支持本机控制接口。

构建源为[ServiceManager.cs](ServiceManager.cs)，运行[build-service-manager.ps1](build-service-manager.ps1)生成 exe，[service-manager-build.json](service-manager-build.json)记录构建与摘要。验证见[service-manager-results.json](../tests/service-manager-results.json)。

高级参数：`--port N`、`--data-dir PATH`；可用 `--start`、`--stop`、`--restart`、`--status` 执行指定操作，`--result FILE` 写入操作结果。所有关闭方式都沿用同一实例核对，不依据未经验证的 PID 关闭进程。

## 账号入口

五个原生Windows入口位于包根目录：

| exe | 账号入口 | 新存档预设 |
| --- | --- | --- |
| [KP主持人.exe](../KP主持人.exe) | kp | 主持工作台 |
| [PL1观察员.exe](../PL1观察员.exe) | player1 | 观察员，手电 |
| [PL2护卫.exe](../PL2护卫.exe) | player2 | 护卫，铁棍 |
| [PL3文献员.exe](../PL3文献员.exe) | player3 | 文献员，笔记本 |
| [PL4医护员.exe](../PL4医护员.exe) | player4 | 医护员，急救包 |

直接双击任意一个即可：未启动时隐藏启动本包服务，已启动则复用，打开默认浏览器的对应账号页面。首次需在网页设置密码，初始化账号、规则、时钟和四个角色及初始道具；此后登录使用，exe不保存或绕过密码。不同入口使用不同路径Cookie，不会把同浏览器的PL身份串成KP。

默认地址为本机8888端口，数据位于本包runtime/room。保留完整配置包和工程依赖，不要单独移动exe。退出浏览器不停止后台服务；KP在“日志与设置”或“主持管理→开局与存档”停止本机服务，随后打开任意exe可以继续。原PS1启动方式仍可用。

已有存档不会因为打开exe而改写角色。若是早期未建立四角色的存档，KP登录后点击“主持管理→角色与战斗→建立缺失的4个预设角色”；已有账号角色保留，不重置生命、体力或物品，不强行改成预设。

构建源为[AccountLauncher.cs](AccountLauncher.cs)，运行[build-launchers.ps1](build-launchers.ps1)生成五个PE可执行文件，摘要与编译器记录在[launcher-build.json](launcher-build.json)。无须为运行exe单独安装编译器。

隐藏服务由独立监督进程持有Windows Job；服务结束或监督进程退出时清理所属子进程树。启动互斥锁避免五入口同时重复启动；校验端口上的包ID及工作区摘要，遇到其他服务占用时拒绝打开错误页面。日志在runtime/launcher.log，不记录设置密码。

测试可给exe传`--port`、`--data-dir`覆盖隔离端口和存档，`--capture`把将打开的URL写入指定测试文件而不启动浏览器；正式使用无需参数。不同存档请使用不同端口。同一工作区同端口复用当前服务。

原生与五账号验收见[launcher-results.json](../tests/launcher-results.json)，运行步骤见[测试索引](../tests/README.md)。

自动行动由 [automation.py](automation.py) 通过现有宿主接口处理；会话加密、独立存储及旧存档更新见[自动行动与界面](../docs/automation-and-ui.md)。五个 exe 无需因本次 Python／界面更新重新编译，完整包中的新文件随服务重启加载。

## HostAccounts 实例发现

本包使用工程公开 CLI 的 `serve` 启动实际房间宿主，新版宿主会自动向同一 Windows 用户的 `%LOCALAPPDATA%/OnlineCOC/HostControl/` 发布实例记录。因此可直接用[HostAccounts.exe](../../../tools/host-accounts/HostAccounts.exe)扫描并查看本包账号，不需要额外为网页8888端口配置管理权限。

若工具安装／宿主功能更新之前已经启动本包服务，旧进程不会自动加载新增接口。需要停止旧服务，再从原账号 exe 启动同一存档，然后在 HostAccounts 点击“扫描本机实例”。关闭浏览器不会停止旧服务，单纯再次双击账号 exe 也会复用旧服务。

选择实例时核对存档路径为本包 `runtime/room`（或启动时指定的目录）。工具中的地址是内部宿主的本机端口，可能不同于网页8888端口。首次准备尚未完成时只有网页服务，还没有实际房间宿主，也就没有可管理的账号实例。

2026-11-05 已用真实原生工具只读验证本包实例发现和五账号列表。该次检测不到的原因是12:01启动的旧宿主尚无后来新增的管理接口，重启后恢复。账号与游戏进度保留。

## 新设备登录与 AUTH_FAILED

本包没有固定默认密码；`12345678` 只有在本机首次准备时明确设置过才有效。`kp` 是小写账号。Git 不同步被忽略的 `runtime/`，安装依赖也不创建本包账号；工程根启动器的默认存档与本包 `runtime/room/` 是两份独立存档。

首次打开应显示“首次准备”，设置密码后再登录。不存在的目录和已有空目录均进入首次准备；非空目录不会被自动覆盖或重设密码。已有存档需要使用其原密码。

无法确认曾设置的密码、且只是想验证新设备能否正常运行时，可在项目根目录启动另一份独立测试存档，使用一个尚不存在的路径：

```powershell
.\rulepacks\mini-detective-pack\start.ps1 --port 8890 --data-dir .\rulepacks\mini-detective-pack\runtime\new-device-room
```

浏览器打开 http://127.0.0.1:8890/sessions/kp/ ，在“首次准备”中设置密码，再用 `kp` 和刚设置的密码登录。此方式保留原 `runtime/room/`；8890 已占用时需换空闲端口。

需要继续原存档而忘记密码时，可先用上述 HostAccounts 工具选中本包实例并在线重设 `kp` 密码；无需旧 KP 密码，工具不提供原密码查询。也可停止持有该存档的规则包服务后，使用工程公开的离线密码命令：

```powershell
.\engineering\.venv\Scripts\python.exe -B .\engineering\backend\scripts\run.py --data-dir .\rulepacks\mini-detective-pack\runtime\room password kp
```

命令会交互输入新密码，修改指定账号密码；不要删除原存档来解决认证问题。宿主离线管理及排他锁说明见[首测工程](../../../docs/current/engineering/first-test.md#5-管理和恢复)。
