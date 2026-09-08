---
name: observation-named-as-fact-travels-as-fact
description: 把带噪声的观测量命名成事实性的名字（如 thickness），它就以事实身份往下游走并被当缺陷追查
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ddd696dd-10d9-48a7-98d5-1f2ffbe95d55
  modified: 2026-08-23T07:30:20.221Z
---

2026-08-22 我登记了 F-78：「sm25 二层量出 0.131 / 0.146 两个图纸上不存在的墙厚」，
当成缺陷追了两轮。2026-08-23 实测推翻：**1 px = 21.81 mm，全部 22 条墙带的面线间距
离图纸声明值都在 1.00 px 以内**，0.131 离 120 mm 只有 **0.49 px** —— 亚像素噪声。

**Why:** 字段叫 `thickness_m`（厚度）时，读它的人（包括我自己）默认它是**图纸的属性**，
于是 0.131 就成了「图纸上有一种 131 mm 的墙」这种不可能的事实。
同一个数字叫 `spacing_m`（两条面线的实测间距）时，它显然是**观测量**，
带噪声天经地义，吸附与残差记账是下游的事。**缺陷是命名造出来的，不是测出来的。**

**How to apply:**
- 给字段命名前问：**「这个值是我量到的，还是世界本来就有的？」**量到的就用观测性名字
  （`measured_*` / `*_px` / `spacing` / `observed_*`），⛔ 别用领域事实词。
- 追一个"不可能的值"之前，**先把它换算回原始单位**（像素、计数、原始刻度）看它有多大。
  亚像素的偏差不是缺陷。
- 吸附 / 归一化 / 分类这类换算，放在**给它起事实性名字的那一层**，不要在观测层就做掉。

相关：[[representation-collapse-manufactures-unrelated-errors]] ·
[[proxy-mistaken-for-the-thing]] · [[instrument-blind-to-the-asked-quantity]]
