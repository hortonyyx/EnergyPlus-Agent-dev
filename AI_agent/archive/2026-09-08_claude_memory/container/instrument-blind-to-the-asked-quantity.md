---
name: instrument-blind-to-the-asked-quantity
description: 模型在同一件事上时对时错，先问「它手里的尺子看得见这个量吗」——F-69 的真因是唯一掩膜对门窗颜色图层的灵敏度为 0，而它照样返回漂亮的候选
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2f8fd7aa-2be5-41c4-8ab8-fa97701b33f1
  modified: 2026-08-22T04:21:35.503Z
---

**2026-08-22，orchestrator 亲自下场跑 sm25 才发现：查了三轮的 F-69 根本不是纪律问题。**

## 事实

sm25 东墙 7 扇窗被读成 7 个墙垛、北墙同一份产物里却全对。
此前的归因是「极性口径可以逐面墙各选一种，全链无门校验一致性」（写进了 plan.md）。

实测（一条命令）：这些 CAD 图**按图层配色**，门窗画在**独立的青色图层**上——
占全图墨迹 sm25 12.3% / sm24 15.6% / sm21 9.7%。
而全仓唯一的掩膜 `clean_vector_v1` 只认 `R≈G≈B`（`rgb_tol=8`）⇒
**它看见的青色像素数 = 0。**

⇒ 读图器**没有任何能直接看见窗的尺子**，只能从灰色墙面线的断口反推。
北墙那次反推对了，东墙那次反推反了。**它不是在选，它是在猜。**

⭐⭐ 更重的一层：**sm21 / sm24 也有这个图层** ⇒ 项目历史上**每一次** reading 都对它是瞎的，
07-07 那两份满分是靠灰线反推挣来的。

## ⭐ 判据（与 [[verify-the-path-works-before-blaming-the-model]] 不同的那一半）

那条讲的是**工具坏了**（调不通、报错）。这条讲的是**工具好好的、返回漂亮结果，
但它对被问的那个量灵敏度为 0**——`wall_line_profiler` 在 sm25 上照样返回 21/18 条候选，
`window_cc_detector` 照样返回一堆 `candidate_kind: "window_rect"` 的框。
**产物长得完全健康**，只是那些框全是墙垛。

> **模型在同一类判断上时对时错、且错法互相矛盾时，第一步不是加纪律、不是改提示词，
> 是问：「它手里的观测手段，物理上看得见这个量吗？」**

补充信号（都在本轮出现过）：
- 工具的**命名**会替你把答案预设掉：`window_cc_detector` 返回的 `candidate_kind` 就叫
  `window_rect`——这个名字本身在引导读图器把连通块当窗。
- 一个 recipe 走天下 + 零旋钮 + 没有任何门在图纸落到窗口外时报红 = 这类缺陷的温床（F-70 同形）。

## 修法形态

**加观测手段，不加纪律。** 把「哪一段是洞口」从推理变成测量：
墙带内有门窗色墨迹 = 洞口，只有灰墨/空白 = 墙垛。
**降级必须显式**：sm20 是 100% 灰度扫描件 ⇒ 工具返回 `mode="monochrome"` 并把每段标
`polarity_ambiguous`，⛔ 绝不给一个自信的错答案（同族 [[absence-conflates-causes-in-observables]]）。

## 顺带：域下限别用浮点严格小于（F-73）

同轮撞到：过程门判 `width < 0.60`，而一扇图纸明写 600 mm 的窗，坐标取自尺寸链后
`10.9 - 10.3 = 0.5999999999999996` ⇒ **一份正确的 reading 被门判红**。
⇒ **域下限要在图纸声明它的那个单位上比**（毫米），不是在浮点米上比。
同族提问：[[silent-default-threshold-behind-otherwise-conclusions]]。

## How to apply

- 排查「模型对这类东西时对时错」：先跑一条**灵敏度**命令——被问的那个特征，
  在现有掩膜/探针下还剩几个像素？为 0 就别再看 prompt 了。
- 造工具时，**输出字段的名字不许预设答案**（`window_rect` → 应叫 `ink_component`）。
- 迁到新图纸前先跑**方言声明**（各墨迹族占比 + 未认领族的比例），⛔ 别默认沿用上一张图的配方。
- 相关：[[proxy-mistaken-for-the-thing]] · [[declare-the-dialect-plus-consumption-ledger]] ·
  [[reading-lever-is-measurement-enforcement]]
