# 工程文档

工程文档必须与当前代码、配置及实际文件结构一致，描述已经存在的实现、接口、运行与验证方式。尚未实现的内容放入 [计划目录](../../plans/README.md)。

工程代码目录为 [`engineering/`](../../../engineering/README.md)。已包含 Lua 简化编写的同步内存实验宿主、样例和测试，运行与边界见下表；完整产品后端及联机服务尚未实现。

| 文档 | 说明 |
| --- | --- |
| [Lua 简化编写实验原型](lua-authoring-prototype.md) | 实际实现、运行方式、56 项断言及尚未具备的能力 |
| [hierarchy：工程目录与施工登记](hierarchy.md) | 实际文件清单、Agent 与人员的使用/改动占用记录 |

每次阶段更新（阶段交付、里程碑完成或集中同步工程状态）必须逐项核对工程文档与实际工程，删除失效路径、已移除功能、旧配置、旧命令和其他废弃说明；有追溯价值的内容移入 [历史目录](../../history/README.md)，不得留在当前工程正文中。日常变更也应及时同步，无需等到阶段更新。

所有 Agent 和人员施工前必须先读 hierarchy，检查范围冲突、登记唯一 ID 并确认；施工结束、取消或交接时释放自己的登记。详细要求见 [文档维护标准](../../standards/document-maintenance.md)。

## 版本管理

项目根目录已初始化为 Git 仓库，远端 `origin` 为 [spathering/polyu-ap-gpcoc](https://github.com/spathering/polyu-ap-gpcoc)。初始化时远端为空，使用现有项目文件建立本地 `main` 初始提交，再从 `main` 创建开发分支 `spathering`。

可用 `git status --short --branch` 检查当前工作区和分支，用 `git remote -v` 检查远端配置。分支切换与提交前须遵守 hierarchy 占用规则。初始化与本地分支创建不会自动推送至远端；远端分支及上游关联需在实际推送后确认。
