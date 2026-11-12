# 树桩镇 Stumpsville

0.4.2新增局域网连接／启动诊断，KP控制台显示房间地址、连线玩家和最近访问；同时修复普通HTTP局域网页面的行动提交兼容性。双击启动窗口可自动识别网卡IP、选择端口、复制玩家地址，支持首次准备与停止／重启。十地点18个预设可自动检定并结算机关、物品、通路和发现，展示骰点、叙述与状态变化。保持一个已登录KP页面在线即可自动执行，无需逐项批准。玩家以场景为底，通过可开关折叠的悬浮面板管理角色、背包、线索和记录；KP在统一控制台处理现场控制、消息与裁决。支持多页面独立登录。

局域网游玩双击 **[start-lan.cmd](start-lan.cmd)**；本机游玩双击 [start.cmd](start.cmd)。首次在本机设置初始密码，再以 `kp`、`player1`、`player2` 登录；两个入口共用本包 `runtime/`，切换时先停止原入口。详细步骤见[使用与恢复](docs/current/usage.md)。

0.2.0/0.3.0存档重启启动器、刷新页面并登录KP，页面会补充场景规则；角色、资源和其他自定义规则保留。0.1.0 存档还需在 KP“控制台”升级自动裁决规则。每次打开根地址或点击“新开独立登录页”，均可登录另一个账号。

冒险专属遭遇表、Jack/Ernie 数值等仍待原版正文终校。首版提供主持填写及裁定入口，不能把待核模板视为完整原版内容。

| 入口 | 内容 |
| --- | --- |
| [场景预设行动](docs/current/scene-actions.md) | 18个行动、检定与实际结果、自动队列和恢复 |
| [当前实现](docs/current/implementation.md) | 实际页面、规则、数据边界及人工裁定事项 |
| [场景桌面与主持控制台](docs/current/interface.md) | 当前导航 Mermaid、功能组成树及反馈语义 |
| [使用与恢复](docs/current/usage.md) | 启动、玩家入场、局域网连接诊断、备份与恢复 |
| [来源与许可](docs/current/sources.md) | SRD、冒险资料的核对范围、原创资源 |
| [验证记录](tests/README.md) | 真实宿主与浏览器验收、可重跑脚本 |
| [设计计划](docs/plans/README.md) | 页面、导航、界面组成与验收范围 |
| [界面图集](assets/ui-design/README.md) | 页面效果图、子 UI、状态与组件图 |
| [原版参考来源](assets/references/README.md) | 原版纸面表单、场景预览与使用说明 |
| [场景依据](../investigation-vtt-reference/docs/plans/stumpsville-foundry-plan.md) | 十地点对照和原 Foundry 方案 |

设计图作为美术参考，实际功能以当前实现及测试记录为准。运行插画独立放在 [assets/runtime](assets/runtime/README.md)，参考原图不通过游戏服务公开。
