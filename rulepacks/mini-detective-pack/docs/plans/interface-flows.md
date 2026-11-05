# KP与PL界面逻辑图

- 文档类型：计划
- 状态：草案
- 创建日期：2026-11-02
- 最后更新：2026-11-02
- 关联文档：[界面计划](frontend-design.md)、[配置规格](configuration.md)、[地图与道具（剧透）](map-and-items.md)、[规则](rules.md)

## 1. 范围与约定

本文件表达界面导航、待办流转和信息边界，这是目标流程图，部分已由本机包实现；防守方选择已接入，停靠及在线恢复等仍待实施；当前导航与自动流程见[自动行动与界面](../automation-and-ui.md)。2026-11-02用户已确认桌面单标签、页内独立KP队列、文字替代手绘与全员前端操作。下图的“分页／窗口”均在同一标签页内；不要求新浏览器窗口、终端、手改文件或外部群聊。规则与参数不在图内重新定义，详见规则／配置；页面ID与界面计划一致。图中动作箭头不表示API已经存在。KP完整地图含剧透，PL只接收按受众过滤的投影。

## 2. 入口与建卡

```mermaid
flowchart TD
  entry["进入房间"] --> auth{"核验房间身份"}
  auth -->|"未获授权"| denied["显示无权进入或申请入口"]
  auth -->|"KP"| kp["KP-DESK 工作台"]
  auth -->|"PL"| role{"已有审核通过的角色？"}
  role -->|"是"| desk["PL-DESK 主桌面"]
  role -->|"否"| create["选择预设或自定义建卡"]
  create --> check{"六维20点、单项1至5<br/>才能与初始物合法？"}
  check -->|"否"| errors["显示字段错误，保留草稿"]
  errors --> create
  check -->|"是"| review["提交KP审核"]
  review --> result{"KP决定"}
  result -->|"退回及原因"| create
  result -->|"通过"| ready["PL确认准备好了"]
  ready --> desk
```

选择KP只来自授权核验结果，PL没有自行切换身份的路径；刷新页面不跳过审核。准备与KP开始场次是独立动作。

## 3. PL页面导航与行动

```mermaid
flowchart LR
  desk["PL-DESK<br/>左叙事 右待办"] --> plan["PL-PLAN<br/>每日8轮草稿"]
  desk --> map["PL-MAP<br/>已知地点与边"]
  desk --> bag["PL-BAG<br/>人物与4槽卡"]
  desk --> cards["PL-CARDS<br/>私有回执 / 共享卡"]
  desk --> team["PL-TEAM<br/>协作邀请"]
  desk --> chat["PL-CHAT<br/>明确受众"]
  map -->|"加入计划，不立即移动"| plan
  plan --> submit["提交本人计划"]
  submit --> waiting["等待KP锁轮与裁定"]
  waiting --> task["收到本人待办"]
  task --> choice{"待办类型"}
  choice -->|"调查或谜题"| method["选择方法 / 输入答案"]
  choice -->|"掷骰"| dice["按指定请求掷一次"]
  choice -->|"领取"| loot["领取与制卡流程"]
  choice -->|"战斗"| combat["攻击 / 锁定防御 / 逃跑"]
  choice -->|"结局"| ending["本人明确选择"]
  method --> feedback["收到授权反馈与状态更新"]
  dice --> feedback
  loot --> feedback
  combat --> feedback
  ending --> feedback
  feedback --> desk
```

背包、卡册和聊天都是可随时查看的工具；能否执行具体操作由当前动作和授权决定。待办优先于普通行动菜单，但不会替玩家选择。各页面关闭后回到原日志位置和未提交计划。

## 4. KP工作区与一轮裁定

```mermaid
flowchart TD
  desk["KP-DESK 总览"] --> plans["KP-PLAN<br/>收计划与缺席处理"]
  desk --> queue["W-KP-QUEUE<br/>跨分页独立浮窗"]
  queue -->|"点击待办：定位但不执行"| ruling
  desk --> map["KP-MAP<br/>完整地图与按人揭露"]
  desk --> loot["KP-LOOT<br/>库存、分配与卡面审核"]
  desk --> events["KP-EVENTS<br/>公告、触发器与结局"]
  desk --> log["KP-LOG<br/>记录、暂停与改判"]
  plans --> verify["核对轮次、成本、协作确认<br/>固定事件是否占轮"]
  verify --> lock["锁定当前轮"]
  lock --> arrival["按最慢队速安排到达<br/>累计局部搜索动作"]
  arrival --> ruling["KP-RULING<br/>环境、方法、骰子与结果"]
  ruling --> audience["选择受众并预览投送"]
  audience --> delivery["发公开公告或私密反馈<br/>记录证据、资源与归属"]
  delivery --> pending{"影响本轮的待办完成？"}
  pending -->|"否"| detail["处理掷骰、领取、遭遇等<br/>其他队伍可继续"]
  detail --> ruling
  pending -->|"是"| finish["结束本轮"]
  finish --> next{"是否第8轮或最终轮？"}
  next -->|"普通轮"| plans
  next -->|"第1日第8轮"| midnight["午夜结构复原<br/>刷新日额度，不复制库存"]
  midnight --> plans
  next -->|"最终轮"| endings["收集各PL结局选择<br/>确认后关闭场次"]
```

被退回修改卡面的物品保持已领取归属；只要该轮领取已完成，可留作跨轮审核。新道具未确认前不可使用。KP推进时不通过“一键完成”绕过尚未作出的防御、容量或结局选择。

## 5. 道具、回执与线索卡的不同路径

```mermaid
flowchart TD
  result["KP完成探索裁定"] --> receipt["私密原始回执<br/>EvidenceReceipt"]
  result --> offer["本次可领取物列表"]
  receipt --> rewrite["PL填写文字标题与正文<br/>图片或手绘可选"]
  rewrite --> audience["选择公共或指定受众"]
  audience --> publish["发布线索卡<br/>PublishedCard 可含虚假叙述"]
  offer --> apply["PL申请实例与数量"]
  apply --> validate{"库存、上限、容量合法？"}
  validate -->|"否"| fix["提示原因或打开必要整理"]
  fix --> apply
  validate -->|"是"| own["登记唯一归属与已用额度<br/>卡片待确认，占槽"]
  own --> draft["PL以文字制作道具卡面<br/>图像可选"]
  draft --> check{"KP核验真实实例"}
  check -->|"退回"| draft
  check -->|"通过"| item["确认道具卡<br/>可用但不可伪造实例"]
```

PL-CARDS可看到本人回执和有权限的共享卡，但二者不能合成一个“全部线索”接口。公开卡不向其他PL暴露原始clueId、真假比对结果、未公开地点或作者未授权的私聊内容。

## 6. 战斗界面时序

```mermaid
sequenceDiagram
  participant K as KP战斗台
  participant X as 受信任裁定层（待适配）
  participant A as 攻方PL
  participant D as 守方PL
  K->>X: 创建遭遇、确定先攻和当前攻击
  X-->>D: 仅发送本次防御选择请求
  D->>X: 锁定对抗或闪避
  X-->>A: 发力量骰与速度骰请求
  A->>X: 提交掷骰动作（非自定点数）
  X->>X: 生成并持久化攻击骰
  X-->>D: 显示已锁选择与对应防御骰请求
  D->>X: 提交一次防御骰动作
  X->>X: 持久化骰子、按规则计算伤害
  X-->>K: 展示公式、HP变化及待确认结果
  K->>X: 确认裁定或附理由改判
  X-->>A: 发送授权的本次结果
  X-->>D: 发送授权的本次结果
  K->>X: 进入下一攻击或结束遭遇
```

防御锁定前不显示攻击骰；NPC由KP操作对应请求。网络失败后查询原请求结果，不另开一组骰。逃跑与追击也先分别锁定地点、再揭示比较；不将对手秘密路线放在按钮提示中。战斗图的“裁定层”是职责名称，不表示工程已有该接口。

## 7. 地图与秘密信息投影

```mermaid
flowchart LR
  source["KP场景定义<br/>全地图、库存、谜底、触发器"] --> secure["受信任授权层<br/>核验身份与揭露记录"]
  reveal["KP选择按人揭露<br/>MapReveal"] --> secure
  state["会话状态与事件记录"] --> secure
  secure --> kp["KP全量工作台"]
  secure --> one["PL甲获准的地点、边、描述<br/>及本人私密回执"]
  secure --> two["PL乙获准的地点、边、描述<br/>及本人私密回执"]
  one --> mapone["PL甲地图与行动选项"]
  two --> maptwo["PL乙地图与行动选项"]
  public["显式发布的共享卡与公共公告"] --> both["其授权受众的公共卡册"]
```

PL甲知道一条隐藏边不自动使PL乙知道；只有明确的共享或KP揭露才改变乙的可见范围。玩家自绘地图可作为不保真的共享线索卡，不自动写入官方可达边。KP预览某PL只查看该投影，不改变PL权限。

## 8. 实施与验收

阶段与页面验收以界面计划§8为准。先核对图中每条提交是否有待办来源，再以建卡→探索→获取卡→发布线索→KP推进的最小闭环制作静态样稿；后续才接服务和多人恢复。

KP裁定队列独立页内窗口已确认，不再待定；手机不在当前范围。其余待确认：多人协作是否增加明确授权的队长代填（默认只代填草稿、不代提交）、公共展示的最终样式。验收须检查越权、并行领取、满包整理、指定受众、断线重放和防御选择先后，并确保全流程从前端完成。交付文档不等于这些行为已通过工程验证。

已检查本地引用和Mermaid代码块的围栏与图类型声明，并人工核对状态先后；本地没有Mermaid渲染器，未完成渲染级语法或视觉验证。多人权限和恢复测试留待对应实现阶段。

## 9. 单标签分页与可折叠窗口

```mermaid
flowchart TD
  browser["一个桌面浏览器标签页"] --> shell["房间工作区<br/>顶栏、内部分页、窗口管理器"]
  shell --> main["主分页：一次激活一个<br/>桌面 / 计划 / 地图 / 卡册<br/>KP另有世界、房间管理、日志存档"]
  shell --> tools["并存的页内工具窗<br/>聊天 / 角色 / 背包 / 详情 / 文字卡编辑器"]
  shell --> kp{"是KP身份？"}
  kp -->|"是"| queue["W-KP-QUEUE<br/>默认展开，可停靠、折叠"]
  kp -->|"否"| pl["PL个人待办角标"]
  queue --> select["点击待办定位裁定分页<br/>保留队列筛选与当前对象"]
  select --> main
  main --> navigate["切换内部分页"]
  navigate --> preserve["保留滚动位置、草稿及工具窗<br/>不触发游戏动作"]
  preserve --> main
  tools --> fold["折叠为标题条<br/>保留未读与处理状态"]
  fold --> restore["点击恢复原位置与草稿"]
  restore --> tools
  shell --> reset["整理窗口 / 恢复默认布局<br/>不重发请求、不改变游戏状态"]
```

```mermaid
stateDiagram-v2
  [*] --> Closed
  Closed --> Floating: 打开或聚焦工具
  Floating --> Docked: 停靠侧边
  Docked --> Floating: 取消停靠
  Floating --> Collapsed: 折叠
  Docked --> Collapsed: 折叠
  Collapsed --> Floating: 恢复到浮动位置
  Collapsed --> Docked: 恢复到原停靠位
  Floating --> Closed: 关闭工具
  Docked --> Closed: 关闭工具
  Collapsed --> Closed: 关闭工具
  note right of Closed
    关闭只影响显示
    草稿保留，已提交待办继续存在
  end note
```

窗口状态独立于`PendingDecision.status`。恢复时根据保存的原停靠模式二选一，不同时走两条路径；同一个工具只保留一个实例，多次点击聚焦已有窗口。跨分页未读只更新角标，不抢焦点；游戏请求的提交、确认与资源消费仍按原业务流程执行。
