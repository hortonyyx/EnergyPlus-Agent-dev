---
name: review-scope-complement-must-be-reconciled
description: "把一批改动拆成两份复审请求书送出去,两份范围的并集要显式对账——否则落在缝里的那半没人审,而每份请求书自己看都是完整的"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d8fe0051-7002-4586-92bc-937faf7f6a52
  modified: 2026-08-17T14:26:46.535Z
---

一批改动拆成多份复审请求书（不同审阅方 / 不同家族 / 「谁写谁不批」要求换人）时，
**必须把各份请求书声明的范围求并集，再与本批实际改动面逐文件对账**。

2026-08-17 实证：F-51 那条线有上下游两半 —— 上游 `src/agent/reading/cv_toolbox/sidecar.py`（GLM 写的，
侧车报告源图 `width_px`/`height_px`）+ 下游 `vision_resize.py` + staging 预缩（Claude 侧写的）。
两份请求书**各自都自称完整**：一份审「基座修法批 + grid_A」，另一份审「707 前置三件」，
`sidecar.py` **两份都没列** ⇒ 落在缝里，零复审。**是我事后逐份对账才发现的，不是我知道欠、排在后面的。**

**Why**：每份请求书的作者（就是我）都在写「这份要审什么」，没人在写「加起来还差什么」。
排除条款（「⛔ 不在范围：X，另找非 GLM 席位」）会给人一种范围已经想清楚的错觉 ——
它证明的只是「我想到了 X」，不证明「我把补集想全了」。
同族形状 = [[absence-conflates-causes-in-observables]]：**没被任何一份请求书提到的文件，
和「已审过」在盘面上长得一模一样**（都不出现在待审清单里）。

**How to apply**：发第二份及以后的复审请求书之前，跑一次 `git show --stat <本批全部提交>`，
把文件清单与各请求书 §「被审范围」逐行划掉；划不掉的就是缝。
把这个并集对账**写进请求书**（「本批共 N 个文件，本单覆盖 M 个，另 N−M 个在 XX 单」），
让审阅方也能替我查这一步。相关：[[whoever-writes-cannot-review-blind-spot]] ·
[[stop-and-report-catches-dispatcher-errors]]
