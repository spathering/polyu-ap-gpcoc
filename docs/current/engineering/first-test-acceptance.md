# 首测验收报告

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-10-30
- 最后更新：2026-10-30
- 关联文档：[工程运行](first-test.md)、[Lua 编写](lua-authoring.md)、[机器证据](../../../engineering/acceptance/results-2026-10-30.json)、[施工计划](<../../plans/project planning/first-test-construction-plan.md>)

## 1. 结论与证据

聊天室追加后，最终完整回归为 **74 项通过，0 失败/错误/跳过**（其中聊天相关 27 项），用时约 86 秒，包含三个真实隔离浏览器及进程崩溃检查。对应 [机器摘要](../../../engineering/acceptance/chat-results-2026-10-30.json) 保存逐用例结果和源码摘要；下述 47 项及其性能数字保留为原阶段证据，不当作本轮新测数据。首次完整运行遇到一次既有恢复目录发布的 Windows 拒绝访问，单项与最终全套复验均通过，暂未确定瞬时原因。

本机首测基础工程的原阶段自动验收为 **47 个不同 pytest 用例通过，无失败、错误或跳过**。全套运行 46 项，随后新增真实双宿主争用测试通过 1 项；网络部分在禁止宿主外联后复验 2 项通过，不重复计入总数。结果、用例名与耗时保存在机器证据中。

验证环境：Windows x64、CPython 3.14.2、Lupa 2.8 的 Lua 5.4、Edge 156.0.4314.50。使用精确 wheel 锁在新的 `engineering/.test-output/clean-env` 中以 `--no-index --require-hashes` 安装成功，再运行完整测试，不需要数据库、系统 Lua 或本机编译器。具体依赖与许可证见 [依赖清单](../../../engineering/dependency-manifest.json)。

工程 E0—E5 及 E6 自动验证已形成交付；E6-03 独立制作者试写尚未进行，不能据此宣布作者体验验收通过。ISSUE-001 保持开放，计划保留这一待办。首测工程可用不等于完整产品或正式公网发布。

## 2. 可重复命令

从项目根执行：

```powershell
engineering/.venv/Scripts/python -m pytest engineering/backend/tests -q --junitxml=engineering/.test-output/acceptance.xml
```

上述基础阶段原为 47 项；聊天室追加后的当前测试数量及结果见 [聊天验收摘要](../../../engineering/acceptance/chat-results-2026-10-30.json)，其接口与验证范围见 [聊天室后端](chat-backend.md)。真实浏览器测试使用 Edge 隔离上下文，不复用用户浏览器配置或账号；生成数据均位于 pytest 临时目录。测试驱动说明见 [acceptance](../../../engineering/acceptance/README.md)。主机关闭后释放锁，故障注入只对测试目录执行。

离线安装复现需要先备齐锁对应的 wheel：

```powershell
engineering/.venv/Scripts/python -m pip download --require-hashes -r engineering/requirements-dev.lock -d engineering/.test-output/wheels
python -m venv engineering/.test-output/clean-env
engineering/.test-output/clean-env/Scripts/python -m pip install --no-index --find-links engineering/.test-output/wheels --require-hashes -r engineering/requirements-dev.lock
```

联网测试的 `offline_server.py` 在宿主及 Python 子进程拒绝非回环 connect/sendto/DNS，并在启动前证明拒绝生效；三身份与八连接的浏览器测试在此条件下通过。没有更改系统防火墙或声称进行了整机物理断网。

## 3. 施工矩阵对照

| 编号 | 已执行的验证与证据范围 |
| --- | --- |
| V01 | 同名、同配置、不同耐久实例分别修改；配置引用阻止删除 |
| V02 | 拆分转移数量守恒、去重与重开；阶段第二操作失败整段回滚 |
| V03 | 重复持有、悬空/跨房间引用、包含循环、被引用实体归档均拒绝 |
| V04 | 同 ID 重发返回原回执、改参数冲突、两线程争同一数量不透支、旧 viewToken 拒绝 |
| V05 | T1 前/后、随机记录后、T2 前/后 os._exit 真实退出，重开不重复扣血且不更换骰面 |
| V06 | 浏览器连接中断后相同封套重发，快照已更新时回执仍幂等；提交后退出再查原回执 |
| V07 | 三身份隔离、权限/CSRF/Origin/Host 校验、隐藏对象/秘密素材拒绝、撤权后查询拒绝 |
| V08 | 连续提交在 3/8 个真实 WS 页面同步，撤权清空缓存；ASGI 受控发送阻塞在约 2 秒关闭，其他主机调用仍可用 |
| V09 | 组合计算不提交；只读掷骰、无效结果、非法宿主调用和捕获后的污染阶段均拒绝 |
| V10 | 不合法导入、显式依赖环、死循环硬终止、内存增长/桥接属性访问/循环表与 NaN 边界 |
| V11 | 等待时更换 Lua 便捷库及 JSON 数据、重开；原流程仍用原源码/数据修订 |
| V12 | 流程节点 T2 前/后真实退出，恢复单一 wait/原骰面；期限不重置，超时后回应拒绝 |
| V13 | 等待期间转移控制权，后果按原发起者复查并进入 needs_attention，未被 KP/回应接口提权 |
| V14 | 房间重开、身份重新登录、成员/角色个人记录和回执恢复；不存在独立世界进度副本 |
| V15 | 完整账号/房间/规则/素材备份到新目录恢复、清空会话；损坏素材拒绝且不创建成功目标 |
| V16 | 直接调用与 HTTP 适配器在固定骰面下处理同一序列，结果、状态、拒绝和回执一致 |
| V17 | 真正第二宿主进程被 STORE_LOCKED 拒绝；执行超时、队列配额拒绝；限制 WAN 的冷启动及本机游玩 |
| V18 | 暂存半写、fsync 前、发布前/后真实退出；同步异常与容量耗尽注入；最终代损坏停止打开 |
| V19 | 内存/文件实现运行相同 snapshot/CAS/query/receipt 契约；Host 可注入内存实现，文件重开结果一致 |

V08 的慢发送故障是在 ASGI 发送边界注入背压，不冒称真实拥塞公网测试。V18 的磁盘满通过存储配额及写入/同步异常验证，没有填满用户系统磁盘或做物理断电。并发等待回应与超时由同一房间锁串行裁决，测试覆盖已过期回应与阶段恢复，不等于高并发压力竞态穷举。公开/自有/KP 投影是首测权限模型，不代表已实现所有未来字段级权限策略。

对应测试集中在 [foundation](../../../engineering/backend/tests/test_foundation.py)、[host](../../../engineering/backend/tests/test_host.py)、[faults](../../../engineering/backend/tests/test_faults.py)、[model contracts](../../../engineering/backend/tests/test_model_contracts.py)、[adapters](../../../engineering/backend/tests/test_adapters.py)、[network](../../../engineering/backend/tests/test_network.py)。

## 4. 本机测量

每档 5 轮、每轮提交一次改名并等待所有页面显示。统计为小样本中位数及最近秩 p95（5 样本时等于最大值），仅记录本机表现。提交列为同一宿主观察窗口的文件提交样本，包含校验与序列化；内存为宿主进程工作集，不包含所有浏览器或 Lua 子进程。

| 连接数 | 操作到全部页面更新 p50 / p95 | 授权快照 UTF-8 大小 | 文件提交中位 / 最大 | 当前 / 峰值工作集 |
| --- | --- | --- | --- | --- |
| 3 | 261.9 / 269.2 ms | 7880–8238 B | 7.36 / 8.09 ms | 62.3 / 125.1 MiB |
| 8 | 277.5 / 283.6 ms | 7881–8239 B | 7.69 / 10.08 ms | 64.9 / 128.5 MiB |

观察窗口的 Lua 工作进程启动、加载、执行及 IPC 合计样本为 396.7 ms（仅 1 次，不能当作充分的分位数估计）。请求进入房间锁的排队中位 0.0005 ms、最大 0.0010 ms；驱动每轮仅一条命令，并发请求峰值为 1，未测饱和吞吐。八连接是同时订阅的浏览器数量，不是八个并行 Lua 执行器。

已配置每连接单个在途完整投影、2 秒发送期限和命令准入配额，避免无限历史增量积压。实测约一个轮询周期完成状态同步，不据此承诺公网同延迟或生产并发规模。全量 JSON 存储与全量快照适合当前小规模首测；增长后的容量、压缩/裁剪与数据库需求仍需实际负载评估。

## 5. 保留项

- 独立制作者试写：按 [Issue](<../../plans/project planning/Issue/lua-authoring-simplification.md>) 的五道任务记录耗时、错误和求助；本次没有虚构参与者或结论。
- 首测默认单房间、回环联网；没有 LAN/公网部署、P2P、正式用户面板或数据库适配器。聊天室后端已追加实现，聊天页面仍待制作；完整游戏规则归配置包，地图/逻辑图/空间能力暂不作为必要实现。
- Windows 文件发布的物理断电边界、恶意脚本安全托管、长时间饱和负载均未验收。
- FastAPI/Starlette 的测试客户端对现用 httpx 发出 1 条弃用提醒；本轮适配器测试通过，运行服务路径不使用 TestClient。依赖升级应在后续重新锁定和验证，不在交付末尾盲目升级。
