# 跨家族二审裁决 · as-drawn 层设计稿 v2

- **被审对象**：[`design_as_drawn_layer.md`](../../experiments/2026-08-23_as_drawn_reading_prototype/design_as_drawn_layer.md)（v2，Opus 5 主控出稿）
- **审阅方**：**gpt-5.6-sol**（续一审同一线程，effort high，可自行跑命令复核）
- **一审裁决**：[REJECT](2026-08-23_as_drawn_design_crossreview_sol.md)
- **日期**：2026-08-23

## 总裁决：**REJECT（第二次）**

> v2 的**方向明显改善**，但**支撑它的原型仍在执行 v1 语义**；且 G-1、立面结构线反证、
> `ink_coverage` 三处**仍有可复现假绿**，不能据此进入不可逆 gt。

---

## ⭐⭐⭐ 头条：我写了一份自己的代码并没有实现的设计稿

v2 描述的是三层 schema（`observations`/`declarations`/`hypotheses`）、**不跨接**、**无 `class`**、
`admissible_alternatives`、面线级 `ink_coverage`。**代码一样都没实现**：仍是 `wall_bands` +
`class` + `OPENING_MIN_M` 跨接 + `declared_thickness_candidates_mm`。

⇒ **我在 §八 引用的每一个数，都是 v1 形态的产物产出的**，它们**证明不了 v2**。
同族 [[self-report-more-compliant-than-artifact]] —— 只不过这次「更合规的自述」是一份设计稿。

---

## 主控复核：**五条 findings 全部属实，逐条已自行跑过**

| # | sol 的 finding | 主控复核 |
|---|---|---|
| **1** | ⭐⭐⭐ **实证产物不是 v2 schema** ⇒ 三层硬性质、「只拿前两层可重推第三层」**从未被任何真实 JSON 验证过** | ✅ **属实**，见上 |
| **2** | ⭐⭐⭐ **1 个像素可以桥回整段墙**：`_full_extent` 用 `fenestration_px_near > 0` 决定桥接 | ✅ **实测属实**：给 `punch_middle` 后的每个空档伪造 **1 个**门窗像素 ⇒ sm24 **30.0 → 100.0**、sm25 **56.0 → 93.3**。⭐ 这等于把门窗**分类**偷偷放回了反证里 |
| **3** | ⭐⭐ **G-1 可被「重复面线」骗过**：`_best_interior` 只有上界，无**下界**、无**独立源**要求 | ✅ **实测属实**：两条完全重合、相距 **0.2 mm** 的线 ⇒ `span_coverage=1.0`、判为合法 `straddling_pair`；0.002 / 0.02 / 0.12 / 0.26 m 全过。对应真实错误形态：一条粗线被检成双边、或旧表示先塌中线再按线宽生成两条近邻线 |
| **4** | ⭐⭐ **`ink_coverage` 分不开真假面线 —— 那个 0.74 是 v1 跨接的产物** | ✅ **实测属实，且这是我最得意的那条**：B08.b 现状三段 `1.0 / 0.74 / 0.74`；按 v2 主张的**不跨接**拆回极大连续段后变成 **五段全是 1.000** ⇒ 与真墙面**分不开**。⛔ **我在同一份文档里既主张删跨接、又拿只有跨接才存在的数当证据** |
| **5** | ⭐⭐ **立面结构线 24/24 只验了「常坐标附近有候选」**，完全不消费 `runs_m` | ✅ **实测属实**：把全部 `runs_m` 清空 ⇒ **仍 24/24**；`covered_px=1, span_ratio=0.001` ⇒ **仍 24/24**。另：`_targets()` 收了 `view_id` **却没用**；levels 对每个 view 都取全部楼层；depth 跨楼层聚合；没有一对一 assignment；没推 depth-step 的 z 跨度 |
| 6 | `NEAR_WINDOW_M=0.30` 是**承重且不可重算**的有损参数 | ✅ 属实。sol 实测 0.05 / 0.10 / 0.30 ⇒ sm25 **92.0 / 93.3 / 93.3** ⇒ **0.10 之后不再涨分，只多吸 8 个阳性空档**。⭐ 「消费者可以不同意这个窗口」这句站不住 —— 只交两个聚合数，重算不了 |
| 7 | 「三类空档干净分开」表述与实测不符 | ✅ 属实。我那张表量的是**窄窗口**，sol 用 `near` 窗口重量：5–27 px 里**有 2 个带门窗墨**（非 0），穿越墨实际是 `[6,9,10,16,20,20]`（我写「14–23」是跨两个 case 取中位数，**呈现不严谨**）|
| 8 | `crossing_structure_px` **未按空档长度/窗口面积归一** ⇒ 跨方言不可分（sm24 的 5–27px 是 `[36,36,97,103]`，≥28px 从 0 到 906，**严重重叠**）| ✅ 属实 |
| 9 | 可评分 gt 的**正分母仍未定义** | ✅ 属实：`source_primitives` 含 jamb cap、`normalized_runs` 含全部 WALL 原语、`pair_hypotheses` 又宣布不评分 ⇒ **到底哪些是 reading 必须画出的面线，没给机器规则** |
| 10 | README 是 v1/v2 混合证据档 | ✅ 属实 |

## ✅ sol 同意的两条

- **§七 对一审配对器诊断的修正成立**：sol 自己重跑候选图 —— sm24 最大 degree=1、边互不相交
  ⇒ 遍历顺序不影响结果，**贪心确实不是 B08 错配的原因**，真因是合法性判据太弱
  （`spacing_m=0.2761`，cfg 只声明 240 而 30% 容差让 276 mm 仍合法）。
- **立面目标推导确实独立于被测产物**：`_targets()` 只读 gt 与 binding，⛔ 不存在拿产物反推目标的循环。
  四个 depth step 由 gt 独立产生（East 6.0 / North 15.0 / South 5.0 / West 14.0）。
  ⚠️ 但只能裁成「**24 个目标的常坐标与产物一致**」，⛔ 不能裁成「立面结构线全面验证」。

## ⏭ 进 gt 之前必须解决（sol 列，主控接受）

1. ⭐ **真产出一份 v2 三层 JSON 夹具**，证明不含 `class`、不跨 gap、pairing 只在 hypotheses ——
   **用这份夹具重跑全部数字**。⛔ 在此之前 v2 的所有实证都不作数。
2. `NEAR_WINDOW_M` 改为**可重算证据**（门窗色连通域 / 最近距离 / 多尺度距离直方图），
   ⛔ 不得用单像素 `>0` 桥整段。
3. G-1 加 **distinct-source + 最小可分辨间距**，补 `duplicate_face` / `collapse_to_midline_then_double` /
   错误配对 / 单像素门窗噪声 四种坏夹具。
4. 立面线反证必须**比较完整 runs/span** + **一对一 assignment** + 按 view 的楼层范围推目标；
   depth-step 至少再验一栋形态不同的建筑。
5. ⛔ **放弃「0.74 可分真假线」**，在 no-bridge 形态下重新找独立证据；找不到就把该配对**明确保持 ambiguous**。
6. 定义 **gt 的可评分分母**：哪些 primitive/run 可评分、哪些仅审计；
   「有 source_primitive 支撑 ⇒ unscored」的跨模态匹配规则是什么。
7. README 清理为**只陈述 v2 当前有效形态与数字**。

## 流程注记

⭐⭐ **两轮下来同一个形状**：一审我挑的三种变异恰好是尺子看得见的；二审我写的设计稿超出了代码实现的范围。
**两次都是「我产出的叙述比我产出的东西更合规」，且两次都要换人才看得见。**
⇒ [[whoever-writes-cannot-review-blind-spot]] · [[self-report-more-compliant-than-artifact]]
