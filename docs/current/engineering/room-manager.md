# 独立桌面房间管理工具

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-11-05
- 最后更新：2026-11-05
- 关联文档：[工具与运行入口](../../../tools/room-manager/README.md)、[使用说明](../../../tools/room-manager/docs/usage.md)、[验收结果](../../../tools/room-manager/docs/acceptance.md)、[后续施工计划](../../plans/room-manager-construction-plan.md)

## 当前实现

独立工具位于 `tools/room-manager/`，与 `engineering/` 同级分离。首版 0.1.0 为 Windows x64 原生 WinForms 程序，运行要求 .NET Framework 4.8；只通过协议 1 的 HTTP/WebSocket 接口连接已运行的本机宿主，不依赖宿主源码、Python 或虚拟环境，不启动第二个 Host。

首版支持 KP 查询与现有管理接口写入：配置修订、Lua/JSON 完整规则组暂存与激活、活跃实例编辑及归档、关系、个人进度、成员、房间状态、流程等待/取消/重试、素材上传/下载/挂接/移除，以及宿主侧备份创建。编辑提供独立字段表单、原始结构查看、实体版本冲突比较和命令回执查询。

变化观察分别使用 WS 授权快照与管理轮询，提供对象/字段关注、筛选、观察段和缓存限额。该能力只反映收到的样本，不是完整变更历史；宿主审计独立展示。非实体操作没有统一原子版本保护。备份仅返回宿主 backupId，不包含身份库，也未提供列表、导出、删除和恢复。

操作及限制的唯一正文见[使用说明](../../../tools/room-manager/docs/usage.md)，模块、构建和测试入口见[开发说明](../../../tools/room-manager/docs/development.md)。本轮未修改宿主代码或契约。

## 后续边界

权威历史 H1/H2 和完整存档管理 S1/S2 仍在[施工计划](../../plans/room-manager-construction-plan.md)中。其实现需要新增宿主管理接口，不能以工具直接读写存档替代。原设计中的预期功能与验证项应以本次[验收结果](../../../tools/room-manager/docs/acceptance.md)和实际代码为准。

## 连接地址排错

配置包网页入口与真实宿主可能使用不同端口。当前 mini-detective-pack 网页代理转发 HTTP，但不转发 WebSocket；管理器必须连接宿主的 `serve --port` 地址。登录成功后一直等待快照的排查步骤见[使用说明](../../../tools/room-manager/docs/usage.md#登录成功但一直等待快照)。本次诊断未修改宿主、配置包或运行中的房间数据。
