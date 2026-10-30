# 首测机器契约

- `models.json`：账号、成员、房间/场次、实体、关系、配置、容器、规则工件、流程/等待、资源及个人记录。
- `messages.json`：命令、登录、回执、错误和授权投影形状。
- `operations.json`：各管理/行动操作的独立输入。保护字段不通过普通玩家 patch 开放。
- `fixtures/`：实体正例、非法字符串数值反例、初始化房间。初始化 fixture 的 activeRuleset 为 null，必须由 Host 加载工件后才是可运行房间。

文件顶层是 schema 名称到 JSON Schema Draft 2020-12 的映射。宿主同时检查语义不变量（权限、引用、循环、数量等），通过形状校验不等于可提交。Lua 短输入声明生成动态动作 schema，客户端表单直接消费该目录。

完整接口与字段生命周期见 [首测工程](../../docs/current/engineering/first-test.md)。版本 1 不支持静默兼容未知字段或未知存档版本。
