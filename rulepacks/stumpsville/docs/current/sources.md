# 来源、核查范围与许可

- 文档类型：当前
- 文档子类：工程
- 状态：有效
- 创建日期：2026-11-09
- 最后更新：2026-11-10
- 关联文档：[实现](implementation.md)、[原版参考](../../assets/references/README.md)、[原场景计划](../../../investigation-vtt-reference/docs/plans/stumpsville-foundry-plan.md)

## 已核查规则

查阅日期2026-11-09。Mausritter 由 Isaac Williams / Losing Games 创作。SRD 采用 CC BY 4.0；本包将规则改写为中文短提示、JSON 和 Lua，未复制完整规则书。许可与原始作品见[官方 SRD](https://mausritter.com/srd/)、[中文授权 SRD 说明](https://maplewhisper.com/mausritter/srd/)、[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。

| 来源 | 核查用途 |
| --- | --- |
| [Make a mouse](https://mausritter.com/srd/make-a-mouse/) | 三属性3d6取高两骰、HP/钱币、交换、背景装备与低属性补偿 |
| [Inventory](https://mausritter.com/srd/inventory/) | 2/2/6槽、状态、超载、用量、轻甲和钱币占槽 |
| [How to play](https://mausritter.com/srd/how-to-play/) | 豁免、伤害、重伤与休息 |
| [Running Mausritter](https://mausritter.com/srd/running-mausritter/) | 遭遇检查、反应和士气 |
| [Magic](https://mausritter.com/srd/magic/) | 法术力量、用量、WIL损伤；本版仍由KP裁定 |
| [中文 SRD 生物](https://maplewhisper.com/mausritter/srd/creatures/) | 通用小鼠、大鼠、蜘蛛、蛇的数值与能力 |
| [官方状态卡](https://mausritter.com/assets/static/mausritter-item-condition-sheets.0f6x257L.pdf) | 状态卡效果和解除条件 |

通用蜘蛛采用HP6、STR8、DEX15、WIL10、护甲1、毒咬d6；HP后伤害作用于DEX。通用蛇采用HP12、STR12、DEX10、WIL10、护甲2、咬击d8。两者的场景专属描述仍需原版对照。原始第三方导出中存在的数值冲突不作为本版自动规则依据。

## 冒险内容边界

[官方作者发布页](https://losing-games.itch.io/mausritter)确认核心规则书收录 Stumpsville。本次尚未取得可逐页核验的第40–41页正文。十地点拓扑、两机关、池底宝物、2d6鼠帮、Jack/Ernie所在地等沿用项目既有计划，明确标为待原版终校。地点文字为简短改写，不冒充原文译本。

尚缺：原冒险六条遭遇内容、战利品表引用、Jack/Ernie专属数值、蛇笛细节、北方据点线索准确措辞、部分道具槽位。页面保留主持填写入口。`verified:false` 的NPC候选不会自动以占位数值创建；可由KP明确核定后新建。

SRD 的 d6 **遭遇检查**不是冒险的六条**遭遇内容表**。本包将两个动作分开。官方书籍正文和插画不自动纳入 SRD 许可，第三方发布须遵循[官方第三方许可](https://mausritter.com/third-party-licence/)。本包不是官方产品，也未获得官方背书。

## 自动预设的适配声明

0.4.0的18个固定行动沿用现有十地点资料。潜水DEX与失败磕碰、割网救援、WIL交涉或口粮交换、Jack工具许可、蛇笛确定安抚、Ernie交谈许可等分支为本包自动游玩适配，不宣称来自已逐页核验的原版。具体条件与实际效果统一见[场景预设行动](scene-actions.md)。仍未自动创建未核定的Jack/Ernie或村民专属数值，完整战斗和原版专属表仍待终校。

## 美术与测试内容

运行插画 `welcome.png`、`courtyard.png`、`mouse.png` 由内置 image_gen 原创生成；精确提示词见[运行资源](../../assets/runtime/README.md)。十张设计图为生成式界面参考，按钮文字与数字不作为规则来源。原官方预览仅留在研究参考目录，不由运行静态路由提供。

两张预设木栗、豆叶为自制测试角色；示例手记、回顾和测试数据不属于原版故事内容。生成图片与代码不改变任何被引用作品的权利范围。
