---
name: absence-conflates-causes-in-observables
description: 设计观测量时必须问「取不到值有几种原因、是不是被压成同一个空白」——最该被看见的那一档往往正是那个空白
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 95485813-f489-466d-bdeb-288b7236b5e3
  modified: 2026-08-14T02:44:42.285Z
---

**2026-08-12 发单前实测，当场推翻 plan.md 已写好的解读规则。**

要做的事 = 让「这张图按墙外皮标注还是按轴线标注」可见。plan.md 已写好观测量与解读表：
拿确定性核吸附时逐侧记的 `corrections[].intents` 的 `old_value→new_value`，
**≈半墙厚 ⇒ 外包标注 · ≈0 ⇒ 轴线标注 · 其他 ⇒ 人工判读**。看起来零成本、观测量现成。

**实测 `envelope_transform.py:111-165`，intent 的生成有三处 `continue`**：
位移 `≤ output_precision_m`（0.010）不生成 · 位移 `> envelope_reconcile_tol_m`（0.30）不生成 ·
该轴 `resolution.status != "accepted"` 不生成。

> ⭐ **「没有 intent」这一个状态同时代表三件完全不同的事：
> ① 按轴线标注（位移≈0，好消息）· ② 超出容差（坏消息，最该报警）· ③ 无权威证据（无信息）。**

⇒ **照原表施工，最该被看见的两档恰好是一片空白。** 而空白最容易被读成「没跑到」。

**⭐ 判别问法（设计任何观测量/报表/指标前必问）**：
**「这个量取不到值的时候，有几种不同的原因？它们是不是被压成了同一个空白？」**
⛔ 修法不是「给空白加注释」，是**把每种缺席各自具名**（本例 = 四种状态各一个名字，
且**位移要在 intent 生成之前算**，不能复用那个已经被 `continue` 过滤过的列表）。

**与 [[gate-with-only-negative-assertions-is-unobservable]] 同族、方向相反**：
那条是「门恒红没人发现」，这条是「量恒缺没人发现」——**共同点 = 缺席不是信号，除非你显式把缺席变成信号。**

**⭐ 同批第二条**：同一个 `intents` 字段里 `claim_kind` 有 **`overall_bound`**（外包吸附，能判标注法）
与 **`wing_break_endpoint`**（翼部断点，语义完全不同）两种 ⇒ **一个字段里两种语义，混着算就废了**。
与 [[free-correctness-evaporates-when-representation-changes]] 的「问到【实现】粒度不是【文件/函数名】粒度」
是同一件事的另一面：**问到【语义】粒度，不是【字段名】粒度。**

**⭐⭐ 同日第三次现形（不同子系统，且这次差点写进修法）**：判卷要证「这份产物是修好之后的代码产的」，
自然想法 = 看产物里有没有 `deterministic_core.envelope_atomic_transform` 记录。
**实测 `envelope_transform.py:586` 是 `if not intents: return` 早返回、不留记录**
⇒ 图纸本来就按外皮标注时核什么都不用改，**合法产物同样没记录**
⇒ 「没记录」= 「没跑过核（不可信）」+「跑了但没事干（完全可信）」。
**今天所有 `deterministic_core.*` 记录全是有条件的，一条无条件的都没有。**
⇒ 用户拍板 = 盖一个**无条件**印章。详 [[version-number-is-not-behavior-attestation]]。
**⇒ 一天之内三次 ⇒ 这不是巧合，是「用副作用的痕迹当事件发生的证据」这个习惯本身有问题：
痕迹只在『有事可做』时才留，而你要证的是『来过』。**

**⭐⭐ 2026-08-14 第四次现形，这次是【门】不是【观测量】**：`mep.hvac_schedule_refs` 的
`blank_reference_policy: pass` ⇒ **同一个字段错位缺陷，模型那一格【留空就放行、填了字就炸链】**。
实证：`f18_e2e_verify` / `post_blocker1` 第 3 格是空的 ⇒ 门放行 ⇒ 一路跑到 EP 且 0 Severe；
`accept_C` 第 3 格填了对象类型名 ⇒ 门拦下 ⇒ 链死、退出码 20。
⇒ **决定「这个缺陷今天可不可见」的是模型的偶然选择，不是缺陷本身。**
⇒ ⛔ **别把「门今天没报」读成「那一次是对的」。** 详 [[artifact-severity-depends-on-real-consumer]]。

**⭐ 元教训**：这是「发单前逐处机械核实」**连续第二轮**当场救回范围写错
（上一轮救回 F-22 实为三处不是两处）⇒ 见 [[stop-and-report-catches-dispatcher-errors]]。
**观测量看起来「已经躺在产物里、零成本」时，恰恰最该去读那段生成代码的过滤条件。**
