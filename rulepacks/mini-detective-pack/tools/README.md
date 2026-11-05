# 启动与包工具

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
