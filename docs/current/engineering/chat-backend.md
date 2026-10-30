# 聊天室后端：数据、权限与接入

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-10-30
- 最后更新：2026-10-30
- 关联文档：[工程说明](first-test.md)、[工程索引](README.md)、[数据契约](../../../engineering/contracts/models.json)、[操作契约](../../../engineering/contracts/operations.json)、[验收摘要](../../../engineering/acceptance/chat-results-2026-10-30.json)

## 1. 能力与边界

已实现聊天室后端、HTTP/进程内接口和浏览器 SDK。支持公共频道、分组频道、双人私聊、文字消息、角色代言、回复引用、公共素材附件、编辑/撤回、禁言/公告频道/归档、已读位置、历史分页，以及将主机已完成的行动回执分享为结果卡片。

聊天室属于长期房间存档，主机验证并排序所有写入；退出、断线和重启不丢弃聊天记录。房间暂停时仍可交流，房间归档后聊天只读，允许更新个人已读位置。聊天文字不解析为 Lua 或骰子命令，不能替代行动日志、数据变更记录或主机计算结果。

本次没有制作聊天页面。现有操作台仍是规则与管理验证工具；前端可用本页 SDK/API 接入。在线状态、正在输入、语音/视频、全文搜索、反应表情、私有附件、Lua 自动播报和流程结果自动推送尚未实现。完整 COC 等游戏规则由配置包实现；逻辑图、地图战斗和 2D/3D 空间能力按游戏需要扩展，暂不作为必要能力纳入实现。

## 2. 模块与事务

`backend/src/onlinecoc/chat.py` 是独立的聊天室领域模块，不导入 FastAPI、不打开文件、不执行 Lua。`Host` 负责可信账号、房间锁、命令去重和提交；网络适配器与 `InProcessTransport` 调用同一主机接口。原 `onlinecoc_data` 文件模块无需认识聊天语义，后续替换存储不改变聊天室权限与操作协议。

每次聊天写入在同一代房间文件中保存频道/消息/已读变更、命令回执和操作审计。`accountId + commandId` 幂等规则沿用现有命令协议；重试保留原始封套，同 ID 不同参数报 `COMMAND_ID_CONFLICT`。聊天没有 Lua 的 T1/随机/T2 阶段：它是一次主机事务。提交前崩溃没有消息和回执；提交后两者同时存在，重试不重复发布。

审计保存操作账号、命令 ID、操作名和时间；正文由聊天记录承载。管理审计可能显示私聊操作发生过，但普通授权投影不包含不可见频道及其序号、修订或未读变化。聊天历史不塞入房间授权快照，也不通过通用 `query` 导出。

## 3. 持久数据结构

房间新增 `chat`，其 `schemaVersion` 为 1。完整机器结构见 `ChatState`、`ChatChannel`、`ChatMessage`、`ChatActionCard`；所有写入和备份恢复均经过结构及跨引用校验。

```text
Room.chat
├─ schemaVersion: 1
├─ channels: {channelId: ChatChannel}
├─ messages: {channelId: [ChatMessage, ...]}  # 按频道序号升序
└─ readPositions: {accountId: {channelId: sequence}}
```

| 结构 | 字段与含义 |
| --- | --- |
| 频道 | `channelId`；`kind` 为 room/group/direct；`name`；`participants`；`posting` 为 all/kp；`muted`；`archived`；`revision`；`lastSequence` |
| 消息身份 | `messageId`、`channelId`、频道内连续 `sequence`、真实 `senderAccountId` |
| 消息版本 | 主机生成 `createdAt`、`updatedAt`、`revision`、`deleted`；时间为 Unix 秒 |
| 普通内容 | `kind: text`、纯文本 `text`、同频道 `replyTo` 或 null、`assetIds` |
| 角色代言 | `speakerId` 与发送时 `speakerName`；未代言时均为 null，真实发送账号仍保留 |
| 行动卡片 | `kind: action`、`card`；主机从回执填入账号/命令/规则/规则修订、结果和骰点轨迹；普通消息为 null |
| 个人已读 | 每账号每频道的最大已读序号，仅本人可读取和推进，不能超过频道最后序号 |

频道 `revision` 在发消息、编辑、撤回或调整频道设置时增加；已读位置单独持久化，不增加共享频道修订。消息序号在编辑和撤回后不变，撤回保留占位，因此历史游标稳定。未读数排除本人发送的消息和撤回消息，不等同于“最后序号减已读序号”。

消息不存角色实例副本；代言名称保留发送时快照，后来角色改名不改写旧记录。回复仅保存同频道既有消息的 ID，不复制其正文；被回复消息撤回后仍可定位占位。

没有频道硬删除或消息硬删除接口。撤回清空当前消息的文字、附件、代言和卡片，保留发送账号、消息身份、版本、回复关系与时间。**撤回不是安全擦除**：原始命令参数、旧文件代和已有备份仍可能保留原内容。

## 4. 频道与权限

| 频道 | 创建与加入 | 读取与发送 |
| --- | --- | --- |
| 公共 room | 初始 `general`；KP 可创建其他公共频道 | 当前活跃房间成员均可读；发送受 posting/禁言/归档约束 |
| 分组 group | KP 创建，初始成员必须包含创建者；当前可见该频道的 KP 可修改成员 | 只有显式参与者可读，包括 KP；新加入成员可读取该频道全部现有历史 |
| 私聊 direct | 任一成员指定另一个活跃成员；双方顺序不同仍返回同一频道 | 固定双方可读写；不支持改成员、禁言配置或归档，避免把旧私聊变成另一个群组 |

应用层 KP 身份不自动获得其他人的私聊正文。主机运行者仍能访问本机存档和备份；本实现不提供对主机保密的端到端加密。

消息作者可以编辑自己的普通文字、撤回自己的消息；可读该频道的 KP 可以撤回他人的消息，但不能伪装成作者编辑原文。编辑/撤回要求当前消息 `revision`，旧版本报 `VERSION_CONFLICT`。被禁言作者仍可撤回自己的消息，不能继续编辑发言；归档频道禁止所有消息写入。

频道设置更新也要求当前 `revision`；发言可能使该修订变化，冲突时重新读取并确认设置。成员撤销访问后，下一授权快照移除频道，历史接口返回 `NOT_VISIBLE`，旧命令回执不再返回该频道的结果引用。未知频道和无权频道使用相同错误。停用房间成员后不能访问任何聊天接口。

角色代言仅接受本人拥有的公开、活跃角色；KP 可代言公开角色。发送者、时间、类型和结果卡片均由主机生成，客户端不能通过额外字段伪造。

## 5. 素材与行动卡片

消息最多引用 4 个已登记、就绪的**公共素材**。素材仍由现有 Assets 端口读取和备份；私聊中的公共素材不因此变为私有文件。首版拒绝把 KP 私有素材附到任何消息，避免聊天权限与下载权限不一致。玩家可引用已有公共素材，但上传入口仍限 KP。未撤回消息引用的素材禁止 `asset.remove`；撤回解除当前引用，原文件代和备份仍可能保留历史。

`chat.message.share` 接受本人已完成行动的 `commandId`，不接受客户端结果或骰点。主机核验回执已提交、来源是公开且非 KP 专用的普通 action，并检查读取对象当前为公开对象；尚未完成的 flow、只读 calculation、失败回执和他人回执不能分享。结果卡片最大 8 KiB，保存分享当时的主机回执与骰点。

分享是明确发布操作，和执行行动是两个事务：发布失败不撤销已完成行动；客户端用各自 commandId 查询和重试。卡片不可编辑，可以撤回。已发布结果不会随对象权限或规则版本变化追溯删除，因此分享者应选择合适的频道；如需撤销发布，撤回消息。新分享仍重新检查当前可见范围。规则本身的语义与可信性由配置包负责。

## 6. 接口与 SDK

所有路径以前缀 `/api/v1` 开始。账号由 Cookie 或可信进程内绑定提供；不接受请求中的账号身份。HTTP POST 继续检查同源 Origin 和 CSRF。

| 接口 | 输入/输出 |
| --- | --- |
| `GET /chat/members` | 返回活跃房间成员的 accountId/memberId/nickname/role；不返回密码、会话或私有元数据，不代表在线状态 |
| `GET /view` / WS 完整授权快照 | 新增 `chatChannels` 字典；频道设置、`canPost`、本人 `readSequence`、`unreadCount`；普通成员不获禁言名单 |
| `POST /chat/history` | `{channelId, before?, limit?}`；默认最近 50 条，最大 100 条；返回升序 items、channelRevision、lastSequence、nextBefore |
| `POST /commands` | 使用下表 chat.* 操作和既有命令封套 |
| `GET /receipts/{commandId}` | 同账号查结果；撤权后过滤频道引用 |
| `GET /capabilities` / `/contracts` | 聊天版本/限额和完整模型、操作契约 |

`before` 是频道内排他序号，`nextBefore` 为 null 表示没有更早记录。新消息不会改变已取得游标前的顺序；分页响应包含当前内容，编辑和撤回会反映在重新查询的页面上。

| 操作 | 参数 |
| --- | --- |
| `chat.channel.create` | `kind: room/group`、`name`，可选 participants/posting |
| `chat.direct.open` | `accountId` |
| `chat.channel.update` | `channelId`、`revision`，可选 name/participants/posting/muted/archived |
| `chat.message.send` | `channelId`、`text`，可选 replyTo/assetIds/speakerId；文字和附件不能同时为空 |
| `chat.message.share` | `channelId`、本人行动 `commandId`，可选 replyTo |
| `chat.message.edit` | `channelId`、`messageId`、`revision`、`text` |
| `chat.message.retract` | `channelId`、`messageId`、`revision` |
| `chat.read` | `channelId`、`sequence`；只能推进本人位置，倒退请求返回现有值 |

编辑只修改普通消息正文，不修改附件、回复或代言身份。正文必须有非空白字符；附件独立发送时使用空 text。文本原样存储，前端必须按纯文本展示，不能直接写入 innerHTML 或执行其中代码。

以下示例中的 `client` 是已登录并收到完整快照的 `Client` 实例：

```javascript
await client.sendChat('general', '大家准备好了吗？');
await client.sendChat('general', '我检查门锁。', {speakerId: 'actor-player1'});
const dm = (await client.openDirect('player2')).result.channelId;
await client.sendChat(dm, '我们先讨论一下调查顺序。');
const page = await client.chatHistory(dm, {limit: 20});
await client.markChatRead(dm, page.lastSequence);
const people = (await client.chatMembers()).items;
// 通用命令也支持全部聊天室操作。
await client.command('chat.message.share', {channelId: 'general', commandId: 'my-check-command'});
```

命令成功回执仅含必要引用：channelId、messageId/sequence/revision 或 readSequence，不复制消息正文。调用方需要检查 `status`，不能把收到 HTTP 200 当作业务成功。`NOT_VISIBLE`、`CHANNEL_READ_ONLY`、`ROOM_ARCHIVED`、`MESSAGE_RETRACTED`、`RATE_LIMITED`、`LIMIT_EXCEEDED` 均为明确错误；失败不会部分更新消息。

## 7. 实时同步与缓存

沿用本机适配器约 250ms 检查一次授权投影、完整分片快照替换的机制，没有另起聊天服务。只同步频道元信息，不逐条推送历史正文；频道 `revision` 变化后前端主动调用历史接口。私有频道的活动不会改变非参与者的普通授权投影。

SDK 提供上述调用，但不建立历史消息缓存。前端若缓存页面，应遵守：

1. 完整快照中频道消失、登出、断线或身份重置时，清空相关缓存，并丢弃该身份/频道旧请求的迟到响应。
2. 频道 revision 变化时，使该频道所有历史页面失效；变化可能来自旧消息编辑/撤回，不能只刷新最后一页后保留其他页为有效。
3. 分页结果与当前授权频道、身份及修订核对后再显示；请求与快照先后交错时重新查询。重连后重新取得授权快照和所需历史。
4. 纯文本与可信 action 卡片分开展示，卡片的“主机结果”标识来自 kind/card，而不是文字中的称呼或骰点描述。

## 8. 存档升级、限额与验证

原房间业务版本仍为 1。缺少 chat 的旧房间在启动时先验证原数据，再以一个新文件代初始化公共频道；已有 chat 不重建，连续重启不重复升级。存在不兼容或损坏 chat 时拒绝打开，不静默清空历史。旧房间备份可恢复并执行同样升级。

备份包含频道、全部消息、个人已读、权限和引用素材；恢复后身份绑定和聊天访问约束保持一致。文件仍采用不可变全量代：每条消息会增加新的完整状态文件，首版适合小规模测试，不把逻辑条数上限等同于保证可用容量。

| 项目 | 当前限制 |
| --- | --- |
| 频道 | 每房间 128 个；参与者/禁言列表各最多 64 个 |
| 消息 | 每房间累计 10,000 条，撤回占位仍计数，无自动删除 |
| 文本 | 每条 4,000 个字符；公共附件最多 4 个 |
| 发言频率 | 每账号跨频道每 10 秒最多 30 条新消息/卡片；重复命令不重复计数 |
| 分页 | 每页 1—100 条，默认 50 条 |
| 结果卡片 | 规范 JSON 序列化后不超过 8 KiB |
| 文件累计配额 | 沿用 512 MiB，可能早于消息数上限达到；备份/恢复新目录可重建文件链，不删除消息 |

本轮完整后端回归 74 项通过，其中聊天室 27 项；具体耗时、源码摘要和逐用例结果保存在机器摘要。专项测试位于 `test_chat.py`，真实浏览器接入测试位于 `test_chat_network.py`，机器摘要见本页关联文档。覆盖权限/私聊隔离、频道修改、分页/已读、编辑/撤回/引用、主机结果防伪、旧存档升级、备份恢复、限额、进程强制退出、HTTP 边界、SDK 重连和实时撤权。可重复运行：

```powershell
engineering/.venv/Scripts/python -m pytest engineering/backend/tests/test_chat.py engineering/backend/tests/test_chat_network.py -q
```

生产级高并发聊天、大型聊天历史、断电与硬盘损坏容灾未在本阶段验收；现有文件存储的故障与配额边界继续适用。本次未新增运行依赖，安装/启动 exe 和共享依赖配置无需调整。
