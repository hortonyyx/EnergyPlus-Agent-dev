---
name: dont-touch-the-tree-while-a-review-runs
description: 送审之后到裁决之前不许动被审对象，否则审阅方审的和你交的不是同一个东西
metadata:
  type: feedback
---

**送审 → 裁决之间，被审对象必须冻结。**

**2026-08-24 实犯**：把分母与判分器送 GLM 审之后，我继续在同一棵树上做下一件事（门窗身份外置）。
审阅方复验基线时发现树被连续改写（9 文件、6000+ 行），只好**自己 `git archive` 出一份冻结副本**
再审，并把这件事写进裁决的「程序性事件」。⇒ 它的每条 finding 我都得先确认「这条在我现在的树上还成立吗」。

**How to apply**：送审时**写明 commit**，然后要么等裁决、要么去做**不碰被审对象**的事
（管理文档、memory、另一条线）。并行开发就开新分支/worktree。

**Why**：同族 [[green-suite-is-a-property-of-tree-and-launcher]]（⛔ 全量在跑时不许动树）——
审阅和跑测一样，是**对某一棵树**的测量。
