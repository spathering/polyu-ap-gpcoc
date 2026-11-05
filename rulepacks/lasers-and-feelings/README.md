# 激光与情感 · 配置包与跑团桌面

基于 John Harper 的 **Lasers & Feelings v1.4** 制作的独立配置包。当前版本 **1.0.0**，已实现规则、对象配置、浏览器前端、独立启动与导出工具；只使用现有工程能力，未修改 `engineering/`。

Windows 用户直接双击本目录的 **[启动激光与情感.exe](启动激光与情感.exe)**。它使用项目已有 Python 环境启动服务并打开浏览器；请保留完整配置包，不要单独移动 exe。

也可以从项目根目录使用原脚本启动：

```powershell
.\rulepacks\lasers-and-feelings\start.ps1
```

默认打开 `http://127.0.0.1:8877`。首次启动设置密码，点击页面上的“KP / 玩家1 / 玩家2 测试窗口”，在同一浏览器的三个普通标签页分别登录 `kp`、`player1`、`player2`。KP 点击“导入并激活本包”，再创建角色、飞船和场景，即可组织跑团。

| 入口 | 内容 |
| --- | --- |
| [使用说明](docs/usage.md) | 安装、完整流程、恢复、自定义和导出 |
| [游戏规则](docs/rules.md) | 完整中文整理及本包裁定 |
| [原始规则与来源](sources/README.md) | 完整一页 PDF、全文及来源校验 |
| [数据与规则设计](docs/package-preparation.md) | 角色与机械记录、关系绑定、权限和事务 |
| [前端设计](ui/frontend-design.md) | 已实现界面、命令恢复与接入方式 |
| [测试与结果](tests/README.md) | 当前规则接口和真实浏览器验证 |
| [许可与改动](LICENSE.md) | 原作署名、CC BY 4.0、翻译与改编范围 |

```text
lasers-and-feelings/
├─ manifest.json：版本与资源清单
├─ config/：静态资料与五种配置
├─ rules/：可复用的 lf.* Lua 规则
├─ flows/：普通 action 与主持操作的流程说明
├─ ui/：跑团桌面
├─ tools/：启动、导出、公开协议客户端
├─ sources/：完整原书与来源
├─ assets/：展示资源约定
├─ docs/：使用、规则、设计、历史记录
└─ tests/：包级与浏览器验收
```

`runtime/`、`exports/`、`tests/output/` 是独立生成目录，不入库。每次行动创建新记录并用现有关系绑定参与者，不重新发布规则组。地图、数值 HP 和背包重量不属于原书必要玩法。

当前沿用宿主本机访问范围；未新增公网、LAN、P2P 或语音。开发遵循[协作边界](../AGENTS.md)。[ISSUE-003](../../docs/plans/Issues/issue-003-rulepack-cooperative-ruling.md)的固定绑定问题已由包侧可复用规则处理，结果已反馈工程责任者；没有必须修改工程才能继续的阻塞项。
