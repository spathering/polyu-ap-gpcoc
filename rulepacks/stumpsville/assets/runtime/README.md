# 运行插画

2026-11-09 使用内置 image_gen 生成的原创资源。精确提示词记录于 [prompts.json](prompts.json)。

| 文件 | 用途 |
| --- | --- |
| [welcome.png](welcome.png) | 登录页树桩外景，右侧留给HTML表单 |
| [courtyard.png](courtyard.png) | 庭院公开场景，不画隐藏宝物 |
| [mouse.png](mouse.png) | 透明背景的小鼠冒险者立绘 |

只有这三个文件通过 `/art/` 白名单公开；研究图、主持地图、配置源文件不通过此路由提供。图片不含可点击文字，界面导航/按钮/库存均为真实前端元素。节点图由SVG绘制，随授权地点数据变化。

返回[配置包](../../README.md)。
