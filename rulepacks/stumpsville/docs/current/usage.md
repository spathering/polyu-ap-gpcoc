# 使用与恢复

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-11-09
- 最后更新：2026-11-10
- 关联文档：[实现](implementation.md)、[验收](../../tests/README.md)、[工程运行](../../../../docs/current/engineering/first-test.md)

## 启动与入场

前提是现有 `engineering/.venv/` 可运行 FastAPI、uvicorn、httpx、websockets 和宿主依赖。包启动不安装或修改工程环境。

1. 双击包内 `start.cmd`，或在项目根目录运行 `powershell -File rulepacks/stumpsville/start.ps1`。默认打开 `http://127.0.0.1:8899`。
2. 全新运行目录先设置8–128位初始密码。宿主建立 `kp`、`player1`、`player2` 三个测试账号，初始共用此密码。随后登录，不自动把准备操作当登录。
3. 同设备、同浏览器可同时打开多个根地址页面，每个页面自动取得独立登录入口；也可点“新开独立登录页”。分别登录 `kp`、`player1`、`player2` 即可共存，不需要无痕窗口。刷新保留该页会话，复制相同完整地址则共享该入口。固定的 `/sessions/kp/`、`/sessions/player1/`、`/sessions/player2/` 仍可使用。
4. 玩家从大厅创建预设或随机草稿。KP 在“控制台→控制与队伍”审核；随机角色背景及起始装备须按 SRD 核定。玩家打开背包检查后标记准备，KP 在控制台开场。

Ctrl+C 结束启动器，同时关闭它启动的宿主。存档位于本包 `runtime/`，测试使用 `tests/output/`，互不混用。不要同时打开两个使用同一存档的启动器。

`start.cmd` 使用 Windows PowerShell。含中文的 `start.ps1` 保存为带 BOM 的 UTF-8，确保 Windows PowerShell 5.1 正确解析；编辑此文件时应保留 BOM。2026-11-09 已修复无 BOM 导致的“字符串缺少终止符”错误，并通过真实 CMD→PowerShell→Python 入口验收。

两个入口均支持 `-Port`、`-Bind`、`-DataDir` 和 `-NoBrowser`；后两项分别指定独立存档目录和关闭自动打开浏览器。例如在项目根目录执行：

```powershell
rulepacks/stumpsville/start.cmd -Port 8900 -DataDir "D:\Studies\Art Programming\OnlineCOC\rulepacks\stumpsville\runtime-other" -NoBrowser
```

## 首次走查

自动裁决默认开启，可在主持控制台关闭。0.2.0/0.3.0存档先重启启动器并刷新页面，再登录KP。页面自动补充缺少的场景规则与状态，保留其他规则和已有角色；控制台也提供“安装场景规则”入口。保持至少一个KP页面登录在线，即可自动执行预设，无需逐项批准；页面关闭或休眠会显示等待自动结算，重开后继续。已有0.1.0存档还需以 KP 登录，在控制台点击“升级自动裁决”，确认安装；无需重新建档或建角。若曾修改规则，先从资料页导出备份。

玩家探索时始终停留在场景桌面。底部“角色状态／背包装备／线索手记／记录消息”打开对应悬浮面板；面板标题旁可折叠或关闭，点击工具栏可将后面的面板置顶，“收起全部”恢复纯场景视野。面板状态按账号和独立登录入口保存。导航与功能组成见[场景桌面与主持控制台](interface.md)。

玩家从01入口开始：“观察地面”会发现机关和02；“检查奶酪”可选择安全检查、DEX解除或直接拿取。到02后检查把手，再用绳索固定开门或冒险直接开门，实际开放03。庭院辨认梯子后继续探索04–10。每个预设的检定与结果见[18个场景行动](scene-actions.md)。未公开、锁住或不相邻的地点不能自动进入。公开描述和主持真相分栏保存；“发布预览”只发布已保存描述及勾选的线索。

玩家可点属性检定、物品详情使用/换槽/点亮，转交则进入主持请求队列。主持“推进回合”每次仅推进一次；六轮消耗已点亮的光源一格。04铜锅盘和07鼠帮人数只生成一次，生成后保留结果。地点库存领取在接收角色实际位于该地点时执行。

需要主持判断时，预设行动、检定、移动、使用/换槽弹窗可选择“主动请求 KP 裁决”；场景或记录面板的“请求 KP 裁决”可描述具体事件，已有回执也可点“请求复核”。KP 在“控制台→待处理与裁决”查看上下文、批准或拒绝并填写回复。复核已完成行动不会重复掷骰或扣减资源。关闭自动裁决后，新预设行动、检定、物品操作和移动默认等待主持；已有申请不会在重新开启时自动批准。

场景顶部的“最近行动”显示提交、等待、结算结果及资源变化；“记录消息”保留完整行动过程、原始骰点、前后值和主持说明。等待KP批准的申请和尚未开始的自动任务不提前掷骰或扣资源；自动任务由KP页面自动执行，人工申请在批准后执行，拒绝有明确回复。预设结果显示叙述、检定阈值与原始骰、伤害／数量骰、机关和库存变化，新线索进入本人线索面板。自动结算中断时继续原任务，已提交的效果不会重放。旧申请仍可在“我的裁决申请”查看，升级前的原始回执也保留，但无法补建当时未保存的资源前后值。记录面板与 KP“消息与记录”均可收发消息、切换频道、查看未读并标记已读。

“控制台→控制与队伍”分别提供遭遇检查、冒险表抽取、反应、士气和伤害。未终校表项在“资料→编辑随机表”填写。通用蜘蛛/蛇已预建；其他NPC可按原版输入数值新建，不能把默认小鼠数值当专属数值。

连接中断后保留原行动，使用顶部“恢复原行动”。不要为同一次掷骰或领取换一个新请求。规则版本冲突时刷新并检查来源；主机已明确拒绝才重新发起修正后的行动。

## 局域网

先在本机完成准备，再关闭启动器，以明确的私有 IPv4 重新启动，例如：

```powershell
powershell -File rulepacks/stumpsville/start.ps1 -Port 8899 -Bind 192.168.1.23
```

参与者访问相同地址，具体地址以本机实际网卡为准。服务限定 Host/Origin，不能使用 `0.0.0.0` 作为访问地址。首次初始化仅允许回环来源。包不会添加防火墙规则或映射公网端口；此 HTTP 适配器用于本机/可信局域网。实际跨设备与防火墙环境尚未验收。

## 备份与恢复

“场次→创建完整备份”先创建宿主房间备份，再保存包侧快照。返回两个配对对象：

- `runtime/host/backups/<backupId>/`：宿主房间/规则/素材。
- `runtime/package-backups/<行动ID>.json`：`hostBackup.backupId` 和配对的 `package` 快照。

网页备份不包含账号密码散列。恢复需要停止原服务并使用原来的 `runtime/host/identity/`。移动到其他电脑应另用宿主离线 `backup --include-identity`，同时保留对应包侧快照；不要仅拷贝单独的包 JSON。

恢复到一个全新目录，不覆盖原存档。以下路径用实际备份 ID 替换：

```powershell
engineering/.venv/Scripts/python.exe -B engineering/backend/scripts/run.py --data-dir rulepacks/stumpsville/runtime-restored/host restore --bundle rulepacks/stumpsville/runtime/host/backups/<backupId> --identity-dir rulepacks/stumpsville/runtime/host/identity
```

将配对 JSON 的 `package` 对象以 UTF-8 JSON 写入 `runtime-restored/package.json`，然后启动：

```powershell
engineering/.venv/Scripts/python.exe -B rulepacks/stumpsville/tools/launch.py --data-dir rulepacks/stumpsville/runtime-restored --port 8899
```

完整复现程序在 `tests/verify_package.py`，使用独立新目录验证恢复后的角色、手记和回顾。备份不是只导出配置；“资料→导出配置包”只导出可检查的规则/资料，不包含私人场次存档。
