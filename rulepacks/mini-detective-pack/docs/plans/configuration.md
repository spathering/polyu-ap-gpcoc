# 完整配置规格

- 文档类型：计划
- 状态：进行中
- 创建日期：2026-11-02
- 最后更新：2026-11-02
- 关联文档：[来源](../sources.md)、[规则](rules.md)、[主持场景](scenario.md)、[地图与道具图](map-and-items.md)、[界面计划](frontend-design.md)、[界面流程图](interface-flows.md)

## 1. 目标与范围

2026-11-02已建立config/scenario.json、config/configurations.json和13条Lua的本机映射，实情见[实现文档](../implementation.md)。本文仍是目标规格；PendingDecision、MapReveal等领域对象在首版部分通过私密聊天与成员progress表达，不代表同名工程API。在线恢复和组合管理边界已记录ISSUE-004。

将复原规则整理为后续配置作者可逐项填写的规格，覆盖静态定义、会话状态、权限、流程、初始数据与验收。**本文不是现有工程接口或可导入文件格式**；字段名是建议的领域模型，未做工程能力映射。只在包内规划，不改 `engineering/`。规则I/H默认仍待确认；2026-11-02用户确认的桌面单标签、文字卡、页内KP队列、全员前端操作与网络占位素材作为界面方向生效，现已按包级接口实现；实际能力和仍未完成项见[实现与运行](../implementation.md)与[自动行动](../automation-and-ui.md)。规则语义以[规则](rules.md)为唯一正文。

包标识`mini-detective-pack`，内容版本`reconstruction-0.1`，场景`island-return-01`；中文展示名“铃蔓回转录：孤岛归航试跑”。一名主持与2—4名玩家；四张预设卡见场景。系统没有启用的扩展字段不得被解释为已生效能力。

## 2. 参数完整表

除标R/I项外均为H。字符串枚举需严格匹配；数量、次数、资源为整数，不允许负值或小数；时间使用游戏坐标和带时区现实时间两种独立字段。

| 字段 | 默认值 | 约束／含义 |
| --- | --- | --- |
| dice.sides | 6 | I；本版固定d6 |
| check.operator | lte | 采用R4例子，成功≤属性 |
| character.attributes | constitution,strength,speed,observation,spirit,intellect | R4，恰好6项 |
| character.budget | 20 | R4，初始基础值总和 |
| character.min / max | 1 / 5 | R4，初始边界 |
| check.effectiveMin / effectiveMax | 1 / 6 | 临时修正裁剪 |
| talent.rating | 5 | R4；专长范围必须经主持批准 |
| hp.perConstitution | 3 | I；创建时满HP |
| stamina.lowBand | constitution≤3：initial2,max3,sleep1 | R2 |
| stamina.highBand | constitution4—6：initial3,max4,sleep2 | R2；超出1—6拒绝未定义配置 |
| day.slots | morning1,morning2,afternoon1,afternoon2,evening1,evening2,night1,night2 | R2，严格顺序8项 |
| day.initialIndex / slot | 1 / morning1 | 初始在公共会议前 |
| day.max | 2 | 试跑长度；到day2 night2结局收束 |
| clock.timezone | Asia/Shanghai | 异步模式现实日程 |
| clock.mode | manual | manual／asynchronous；manual不等现实钟点 |
| clock.planDeadline / windowOpen | 21:00 / next-day12:00 | R1时间，时区H |
| intellect.dailyBudget | 当前永久智力值 | 每日开始刷新，不扣属性；临时修正不改预算 |
| cost.explore / encounter / escape | 1 / 1 / 1 | 逃跑需有余额，前两者可强行 |
| cost.move / sleep / treat / fixedEvent | 0 / 0 / 0 / 0 | 每项仍占对应时间 |
| cost.hint / extraSearch / reviseIdleSlot | 1智力额度 | 额外主要行动只替换后续空闲轮 |
| team.maxSize | 4 | R6，协作队上限 |
| search.basePerCharacterLocationDay | 2 | R6次数，按日范围H |
| search.itemCapPerTeamLocationDay | 3 | R6上限，按日／防拆队范围H |
| arrival.teamSpeed | min成员当前到达速度 | R6；普通疲劳先攻速度修正可参与 |
| arrival.delay | 1+与最快队速度差 | R6；单位为局部搜索尝试 |
| inventory.cardSlots | 4 | R4，装备占槽，线索不占槽 |
| inventory.stackMax | 3 | 仅标明可堆叠耗材使用 |
| weapon.baseBonus | star | I；无武器0，基础星级1—5 |
| combat.defenseTie | dodgeFails | R3严格大于 |
| combat.resistNegative / resistZero | damage1 / damage0 | R3字面 |
| combat.dodgeDamageFloor | 0 | 失败伤害非负 |
| combat.debuffThreshold | hp*2<hpMax | R3，一场结束时一次 |
| combat.zeroHp | downed | 禁止行动；不自动永久死亡 |
| clue.coreAcquisition | plausibleAction | H参考W1—W3，不要求成功骰 |
| reset.structure | midnight | R6事件栏L32；范围详见场景 |
| reset.items / hp / stamina | false / false / false | 防复原刷物品；不是全局倒带 |
| extension.sanityPoints / magic / parasite / mutation / pvp | false | 后期笔记未构成完整可执行规则 |

参数改动须产生新内容版本并在场次开始时确认。运行中不能通过直接改参数重算已发生的骰子与伤害。

## 3. 静态配置对象

所有对象包含`id`（稳定ASCII标识）、`name`、`provenance`（R/I/H及具体原件位置）、`visibility`。引用用ID，显示名变更不影响存档。可选字段省略时按下面缺省处理，不能把空白数字默认为0。

| 对象 | 必填内容 | 可选与缺省 |
| --- | --- | --- |
| PackDefinition | id,contentVersion,ruleProfile,scenarioId,sourceIndex | licenseStatus=unconfirmed，implementationStatus=documentOnly |
| AttributeDefinition | id,name,min,max | 无隐含派生技能 |
| TalentDefinition | id,name,scope,rating5 | excludesCombat=true；必须列出可用场景 |
| CharacterTemplate | id,name,六维,talentId,startingItemIds | 简介空；HP/体力由公式生成；不能导入历史后期值 |
| LocationDefinition | id,name,description,adjacentIds,searchTargets,visibility | locked=false,danger=false,resetPolicy=none |
| SearchTarget | id,locationId,method,attribute,coreClueIds,successEffects,failureEffects | oncePerSession=false；剩余库存由实例维护 |
| ItemDefinition | id,name,kind,slots,effect,consumable,unique,obtainCondition | weaponStar=0,stackMax=1；kind为weapon/tool/medicine/key/food/story |
| ClueDefinition | id,title,factText,conclusionIds,leadLocationIds,core,delivery | 无实体库存、无槽位；factText只给授权获得者 |
| PuzzleDefinition | id,prompt,availableEvidence,answer,alternatives,success,failure | attemptsUnlimited=true，但同方法失败需改条件 |
| NpcDefinition | id,name,motive,knownClueIds,disclosureConditions,combatProfile | 非参战NPC可无数值，不能因此自动无敌 |
| EncounterDefinition | id,locationIds,trigger,participants,choices,endConditions | repeatable=false,visibility=participants |
| FixedEvent | id,gameTime,participants,publicText,effects | once=true；不允许倒地角色被移动到危险处 |
| StatusDefinition | id,trigger,effect,duration,removeCondition,stackPolicy | 无自动跨类型清除 |
| EndingDefinition | id,condition,priority,text | 同轮满足多个时需玩家选择，不能只按登记顺序 |

场景文件内表格提供实体定义；本节定义字段形状。`effect`建议为类型化动作集合，例如grantClue、transferItem、modifyHp、addStatus、unlockEdge、setFlag。不得执行来自玩家线索文本的脚本或把文本推论当指令。

## 4. 会话状态

| 对象 | 必需状态字段 | 读取范围 |
| --- | --- | --- |
| Session | id,contentVersion,phase,day,slot,revision,mode,gmId,playerIds,worldFlags | 公共时间公开；worldFlags逐项决定 |
| Character | id,ownerId,baseAttributes,permanentModifiers,talentId,hpMax,hp,staminaMax,stamina,intellectBudget,intellectRemaining,locationId,statusIds,lifeState,inventoryIds | 主持全量；本人全量；其他人只获已公开描述 |
| Plan | id,ownerId,day,8个slot/action,target,teamId,priority,state | 主持、本人、同意协作成员；未定秘密目的不公开 |
| TeamVisit | id,day,locationId,memberIds,cohortKey,arrivalOrder,localActionCount,claimedItemIds | 主持及该队；cohortKey保持同一来源队拆分后的累计 |
| SearchUsage | characterId,day,locationId,baseUsed,extraUsed | 主持和本人，baseUsed≤2 |
| ItemInstance | id,definitionId,quantity,holderId或locationId,cardState,createdBy,revision | 主持与持有人；未发现库存保密 |
| EvidenceReceipt | id,clueId,recipientIds,sourceEventId,privateText | 主持与列明接收者 |
| PublishedCard | id,authorId,title,body,attachments,audience,revision | 发布受众；与EvidenceReceipt不自动反向关联展示 |
| Encounter | id,participantIds,order,index,attackId,phase,defenseChoice,rollIds,escapeChoice,ended,postDebuffApplied | 主持与参与者；逃跑选择在锁定后公开 |
| ResourceLedger | operationId,actorId,resource,delta,before,after,causeId | 主持与本人，不携带别人的私密叙事 |
| EventLog | id,operationId,gameTime,visibility,rolls,effects,beforeRevision,afterRevision | 按授权投影；回放不能扩大读权限 |

必要不变量：0≤HP≤HP上限，0≤体力≤上限，0≤智力余额≤预算；倒地=HP0；库存槽位≤4；唯一物实例仅一持有人／地点；动作重复提交只生效一次；不可通过客户端指定骰点改结果。初始模板不能复制历史人物的寄生或人外状态。

## 5. 权限与消息

| 操作 | 主持 | 角色本人 | 其他玩家 |
| --- | --- | --- | --- |
| 创建角色、改初始六维 | 审核 | 提交候选 | 无 |
| 提交／修改未来计划 | 可协助且留痕 | 可在锁定前修改 | 需本人同意协作 |
| 骰子、HP、库存结算 | 发起裁定并确认 | 发起合法行动 | 无任意写权限 |
| 查看原始私聊线索 | 全部 | 仅被投送部分 | 仅明确获准者 |
| 发布线索卡 | 可 | 可自由表述 | 可阅读自己受众内卡片 |
| 制作道具卡 | 校验实例并批准 | 申请制卡 | 无伪造入口 |
| 物品转移 | 裁定／登记 | 提出或确认接收 | 仅作为同意接收者 |
| 地图未揭露边、谜底、NPC动机 | 可 | 不可 | 不可 |

原料“不可转发文字”在产品中表现为不提供直接分享原始回执的功能；不能声称能阻止截图或玩家私下复述。玩家可造假的只有公开卡叙述，不能改主持的事实对象、真实物品和战斗日志。

最小消息：publicAnnouncement、privateNarration、rollRequest、rollResult、itemOffer、itemAccepted、cluePublished、ruling、phaseChanged。每条都有id、时间、发送者、受众、关联动作；公开消息不得附上私密字段的隐藏副本。

## 6. 流程状态机

### 场次

`draft→characterReview→planning→slotLocked→resolving→slotComplete`，其后进入下一轮planning；第8轮完成后午夜清理与新日刷新，再进入planning。最终固定事件后进入`endingChoice→closed`。可在任一处理中暂停为paused，恢复后回原步骤；paused不推进时钟、不自动扣资源。

### 探索

`submitted→validated→costPaid→arrival→narrated→methodChosen→resolved→lootPending→complete`。前置不合法退回submitted，不收费。玩家可在costPaid前取消；已经投骰或获核心信息后取消不返还费用。发放第5张卡停在lootPending，先由玩家腾出槽位再原子转移；不会阻塞其他队私密流程。

### 战斗

`created→entryCost→initiative→defenseLocked→attackRolls→defenseRoll→damage→nextAttack`，出现逃跑走`escapeLocked→pursuitLocked→reveal→escaped或initiative`，结束统一进入`postCombat→complete`。先选防御再显示攻击骰；仅防御方式提交者有权决定；同一attackId不得重复计算HP。多人按规则§6的顺序执行。

### 修改与恢复

每个请求带operationId及预期revision；重复请求返回原结果，版本过期要求重新读取。骰子一经生成存档，重连不能重掷。资源、次数、库存与日志必须同时成功；如果失败则不留下半扣款。主持改判需一条带原因的补偿事件和新revision，不删旧证据。上述均为未来实现要求，尚未验证后端具备。

## 7. 开局配置清单

| 项目 | 试跑默认 |
| --- | --- |
| 公开说明 | 角色来孤岛参加学校活动，需调查失联并寻找归航方式；不公布幕后真相 |
| 游戏内年代 | 当前年份未指定；1926、1932、1943、1951、1960仅为档案年份，不将系统日期当剧情年代 |
| 初始地点 | loc-hall |
| 初始角色 | pc-observer、pc-guard、pc-scholar、pc-medic，2—4人取用 |
| 体力／血量／智力 | 按规则建卡计算；状态空、已用次数0、智力满 |
| 初始团队 | 一队，包含当前所有参玩角色；允许合法拆分 |
| 地点 | 场景表列出的核心地点全部存在，隐藏边需发现，未补齐的原料地点为旁支 |
| 道具 | 场景目录唯一物各1；地点库存急救包2份，加预设医护员初始1份，共3份；厨房口粮4份；按份计产出、按堆叠卡计槽位 |
| 开放／锁定 | 公共宅邸开放；管家柜、地下门、船只按谜题锁定 |
| 已知线索 | 仅公共入场说明；其余未获得 |
| 世界标记 | intro=false,clockKnown=false,recordsKnown=false,entranceKnown=false,routeKnown=false,boatReady=false,offerMade=false |
| 中途存档 | 保存角色、计划、队伍次数、世界标记、物品、事件和原始骰子，不只存聊天 |

## 8. 待确认、实施和验收

待确认事项继承规则§9；另需确认角色属性可见性、跨队累计规则和现实日程。线上两类卡片已允许纯文字、图片可选，不再等待绘图形式确认。先人工核对场景各ID与引用，再在后续独立任务映射现有工程入口；遇能力缺口按包边界提Issue，而不是在本文写成已支持。

| 验收场景 | 预期 |
| --- | --- |
| 六维和19／21、单项0／6建卡 | 拒绝；20且各1—5接受 |
| 体质3／4 | 初始HP9／12，体力2／3，上限3／4 |
| 属性3骰3／4 | 成功／失败 |
| 同一请求重放、重连战斗 | 不重扣资源、不重掷骰、不重复发唯一物 |
| 两队同时拿同一钥匙 | 恰好一人获实例，其余取得明确已领取反馈 |
| 4张卡后取新物 | 等待玩家选择去向；不允许超槽或删除旧物 |
| 线索造假发布 | 公开卡可与事实不符，其他玩家看不到后台真假标签 |
| 错误方法／失败骰 | 不直接给谜底；主线仍有替代入口 |
| 体力0强行探索／逃跑 | 前者加疲劳继续，后者拒绝 |
| 对抗差−1／0／1 | 伤害1／0／1，防止不慎改公式 |
| 闪避平手、攻击差值为负 | 平手中招，最终伤害仍≥0 |
| 半血、低于半血结束 | 前者不抽，后者仅抽一次 |
| 午夜复原后搜同一柜子 | 建筑恢复，无唯一物复制，无HP自动回满 |
| 非授权玩家读取私密回执／主持配置 | 拒绝；不仅在界面隐藏 |
| 任一主线节点未访问 | 仍能从其他证据路径达成解释及归航 |
| 结局关闭后新动作 | 拒绝推进，可读已授权记录 |

当前已生成JSON／Lua并完成真实HTTP与浏览器专项检查，覆盖25项接口与17项界面检查；全量计划对象和在线恢复未实现，实际范围见实现文档。

## 9. 前端适配补充（待实现）

新增界面依据为sources中的U1—U3，KP／PL页面和分期以[界面计划](frontend-design.md)为唯一正文。以下为建议数据补充，不表示现有工程具备相应接口：

| 对象／字段 | 计划定义 | 权限与不变量 |
| --- | --- | --- |
| PendingDecision | id,kind,assigneeIds,allowedActions,causeId,status,revision | 只投送KP与被指派人；合法动作仍由规则和当前状态校验，不由前端自定 |
| MapReveal | subjectIds,locationId或edgeKey,revealedFields,eventId | 地点、边和字段分别揭露，默认不公开；不会因队伍不同成员看见就自动全员已知 |
| ItemInstance.cardState | pending／confirmed | 领取即登记归属并占槽与产出；审核确认卡面，不能创建第二实例；待确认不能使用 |
| PL地图投影 | revealedLocations,revealedEdges,authorizedDescriptions,knownPosition | 不传未揭露真实节点、边、库存、谜底与隐藏事件；路径计算仅用投影 |
| 发布卡输入 | title,body,attachments,audience | 不透传EvidenceReceipt私密正文或后台真假关联；共享地图草图不直接改官方通路 |

满包领取时必须允许相关整理；战斗已锁定攻击期间不允许切换其武器。待确认卡占有状态可跨轮，领取容量等本轮待办未完成则不能强制跳过。强制倒数和自动跟随多数均未启用。前端操作图见界面流程图，全部数值规则沿用原版本。

### 已确认的工作区规格

| 配置／对象 | 值或字段 | 边界 |
| --- | --- | --- |
| ui.platform / navigation | desktop / singleBrowserTab | 内部分页，不以新浏览器标签或系统窗口承载正常流程；手机不在验收范围 |
| ui.kpQueue | floatingWorkspaceWindow | 页内独立窗W-KP-QUEUE，可移动、折叠、停靠，跨分页存在 |
| ui.cardInput | text，attachment可选 | 线索卡与道具卡均可纯文字，原有真假和审核规则保持 |
| ui.operationEntry | frontendOnly | 房间准备、角色审核、配置表单、裁定、揭露、库存、战斗、存读档和改判均有前端入口；不是取消后端权威 |
| WorkspacePreference | accountId,roomId,roleId,activePage,windows,scrollPositions | 个人UI偏好；不得包含完整私密回执，不能复用为游戏存档 |
| WindowState | windowId,mode,previousMode,x,y,width,height,zIndex,filter,selectedId | mode为closed/floating/docked/collapsed；恢复时裁剪到桌面可见区；关闭不取消业务 |
| CardDraft | ownerId,roomId,kind,title,body,optionalAttachments,audience,itemInstanceId可选 | 文本不作为可执行脚本；道具卡绑定既有实例，不能改真实属性；按角色隔离草稿 |
| AssetReference | assetId,localPath,roleBindings,sourcePage,author,license,sha256 | 当前资源见[素材清单](../../assets/placeholders/manifest.json)；已配图不表示该对象对PL可见 |

加载包使用前端文件选择器或已装包列表，表单先校验再创建场次；存档恢复先暂停并预览差异，明确确认后执行。任何业务失败均在前端给出下一步，不要求操作者到终端补调用；无法满足时记录缺口，不通过客户端自改权威状态绕行。窗口折叠、切页和素材替换都不增加operationId、不重新结算。
