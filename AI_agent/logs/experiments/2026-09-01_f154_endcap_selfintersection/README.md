# 2026-09-01 · F-154 端头修法撞上**自交环** —— ⛔ 线索，**非证据**

> ⛔⛔ **本目录的一切都是【线索】，⛔ 不是证据。** 里面的实现**未过任何审、未跑全量、已从工作树撤下**。
> 将来若要复用，必须**重新实现 + 自己重新论证 + 补锁**，⛔ 不许直接把 diff 贴回去。

## 一、这是什么
GPT 家族席位按 [F-154 重发单](../../reviews/request/2026-09-01_f154_reissue_wall_endcap_unowned.md)
施工，在**正式落库门**前按 §五 必停触发器中止。它的实现留在 `endcap_attempt.diff`（`as_measured.py` +167/-34）。
主控已按纪律**把树撤回 `58bb59f`**，只保全线索。

## 二、⭐⭐⭐ 撞出来的东西（比停报本身重要）

**端头修法在【条数】上完全达标，在【环有效性】上不成立。**

| | 派工单钉的读数 | 实际 |
|---|---|---|
| plan-F1 | `44/2 → 88/1` ✅ | 救回的那个腔 **44 条边、自交** |
| plan-F2 | `56/1 → 91/0` ✅ | 救回的那个腔 **35 条边、自交** |

⭐ **形态极说明问题**（主控独立探针，见 `orchestrator_ring_validity_probe.txt`）：
```
plan-F1  健康的 11 个腔  各 4 条边  全部 valid
         救回来的那个     44 条边   Self-intersection
plan-F2  健康的 14 个腔  各 4 条边  全部 valid
         救回来的那个     35 条边   Self-intersection
```
⚠️ 主控的环重建方式与生产者不同，F1 自交点位略有出入（`151600` vs 席位报的 `159400`），
**F2 逐字一致** ⇒ **结论对重建方式不敏感**。

## 三、⭐⭐⭐ 病根：这撞上的是**用户已经签过字的那条口径**

[指南 §十.6c](../../../guides/reading_correction_split_guide.md)（2026-08-29 用户签字）：
> **接头处传播【线】，⛔ 不传播端点；端点由相邻两条线求交算出。**
> ⭐ gt 侧 `s7_expand_zones` **已经是这么做的**，⛔ 但 pipeline 侧没有这一步，
> 且**事实层存逐边端点后它会【从已解变成未解】**。

**那句预言应验了。** `s7_expand_zones` 的 docstring 逐字：
「rebuild the zone polygon from **offset support-line corners**」+
「**L/T/cross/re-entrant joints need no special-case code**」。
而 `derive_boundary_edges` 是**把 span 的端点首尾接起来** ⇒ 走廊形状（几十个 T 接头）必然拼不拢。

⇒ **F-154「让端头可被认领」是在治症状。** 真病灶 = **环的构造方式**：
[[representation-collapse-manufactures-unrelated-errors]] —— **换表示 > 加容差 > 加分支**。

## 四、⚠️ 也证明了上一轮那个读数是【代理量】
上一轮施工方给的 `44/2 → 88/1` 被主控写进重发单**验收 1 的承重位置**当成「修法有效」。
**它量的是边的条数与 loss 条数，不是环成不成立。**
⇒ [[proxy-mistaken-for-the-thing]] + [[citing-someone-elses-fact-does-not-transfer-responsibility]]
⇒ **题错 #57**，裁决见重发单 §八。

⭐ **为什么上一轮没撞到**：那轮被「哈希不许变」挡在正式落库门**之前**就停了，
自交环在门后 ⇒ [[probe-past-the-blocker-to-find-hidden-walls]]「卡在 X」≠「X 之后没问题」。

## 五、文件
| 文件 | 是什么 |
|---|---|
| `endcap_attempt.diff` | 席位的端头实现（⛔ 线索非证据）|
| `seat_execution_doc.md` | 席位执行档副本 |
| `orchestrator_ring_validity_probe.txt` | **主控独立复现**的环有效性读数 |
