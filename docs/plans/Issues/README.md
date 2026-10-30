# 更新问题记录

此目录存放后续更新需要讨论、修复或验证的问题，属于计划材料；问题存在不等于已承诺实施。每个问题单独建文档，使用稳定编号和英文文件名，例如 `issue-002-launcher-upgrade.md`。

## 新增问题

复制 [问题模板](issue-template.md)，填写现象、复现方法、影响、相关证据、候选处理方式和验收条件，并在下表登记。未确定的处理方式保留“待讨论”，不要写入当前工程能力说明。完成后把已确认实现同步到 `docs/current/engineering/`，有追溯价值的问题按 [维护标准](../../standards/document-maintenance.md) 归档到历史目录。

| 编号 | 问题 | 问题状态 | 正文 |
| --- | --- | --- | --- |
| ISSUE-001 | Lua 编写体验简化与独立作者试写 | 待独立试写 | [既有设计议题](<../project planning/Issue/lua-authoring-simplification.md>) |
| ISSUE-002 | 桌面工具窗口交互验收 | 待交互验证 | [正文](issue-002-desktop-interaction-validation.md) |

ISSUE-001 的正文仍在原位置，本目录只链接它，不复制成第二份。后续新问题统一从本目录登记；编号从 ISSUE-003 继续。与当前功能、版本和运行相关的事实见 [工程索引](../../current/engineering/README.md)。
