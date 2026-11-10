# Python 独立桌面房间管理器

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-11-05
- 最后更新：2026-11-09
- 关联文档：[工具入口](../../../tools/room-manager/README.md)、[使用说明](../../../tools/room-manager/docs/usage.md)、[LAN 模块](network-lan.md)、[验收](../../../tools/room-manager/docs/acceptance.md)

## 当前实现

0.2.0 已将原 C# WinForms 前端迁移为 Python/Tkinter，源码、构建、依赖锁、测试和发布位于 `tools/room-manager/`。Windows x64 发布目录内置 Python 运行时；开发环境验证为 CPython 3.14.2、Tk 8.6。管理器不导入宿主实现、不打开存档文件，所有业务写入均通过现有协议 1 接口。

原配置、规则暂存/激活、实例/关系/进度、成员与房间状态、流程、素材、备份创建、观察和关注、版本冲突比较及命令回执功能均有 Python 入口。原始结构只读，已知操作采用字段表单，结构字段为多行 JSON。旧 WinForms 代码、文档和发布物保留于 `legacy/winforms/`，不再作为现行启动方式。

新增“局域网联机”页，可启动/停止独立 LAN 网关、选择本机网卡和端口、复制地址与查看连接数量；也可通过 `--lan` 单独打开面板。网关代码位于 `engineering/network-lan/`，不依赖后端或数据模块。具体边界见[LAN 架构](network-lan.md)。

## 现行限制

首版 LAN 为可信网络内 HTTP/WebSocket，未实现公网穿透、TLS 和 UDP 自动发现。网页配置包代理与真实宿主可能不同端口，管理器须连接真实宿主或本次 LAN 网关。

观察仅是收到样本的差异，不是完整历史。非实体操作没有统一原子版本保护，备份只创建而不提供列表/导出/删除/恢复。未来工作仍见[后续施工计划](../../plans/room-manager-construction-plan.md)。本轮未修改宿主业务、存储或账号控制代码。
