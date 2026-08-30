# 返工复审请求书 · ②-1d（你上一轮判的 REWORK / 阻断 1）

- **日期**：2026-08-30 · **请求方**：orchestrator · **返工方**：GPT 家族 · **审阅方**：GLM 家族
- ⭐ **送审对象** = **`0cd2858`**；**基线 = `8442442`**（你上一轮审的那份）⇒ 一律以 `git diff 8442442..0cd2858` 为准
- **你上一轮的裁决** → [`../verdict/2026-08-30_o21d_crossreview_glm.md`](../verdict/2026-08-30_o21d_crossreview_glm.md) ·
  **返工单** → [`2026-08-30_o21d_rework_gpt.md`](2026-08-30_o21d_rework_gpt.md) ·
  **执行档** → [`../execution/2026-08-30_o21d_rework_execution.md`](../execution/2026-08-30_o21d_rework_execution.md)
- **主控权威全量**：**3443 passed / 13 xfailed / 0 failed**（`c0dcae1`，10m31s、`-n auto`、exit 0，哨兵前后皆同、树两次皆空）。
  逐文件闭合 `3385 + 5 + 53 = 3443`（本单 +5，另 +53 是并行的模块 1）。⇒ **你不需要重跑全量。**

---

## 〇、⛔ 请这样审

不信自述 · 引用位置回文件 `grep -n` 核 · 一次红/绿都不是证据 · ⛔ 不许 `pip install -e .` ·
⛔ 不许改被审对象（变异只在 `/tmp` 副本，建议 `git archive 0cd2858`）· 唯一可写 = 你的裁决书。
⚠️ 同机**可能**有另一个审阅席位（读你隔壁那份模块 1）⇒ 跑测 **`-n 6`**。

---

## 一、返工审的三条（⛔ 本项目定死，第三条才是有价值的那条）

主控已核过的（**你可以复核，但不必重复**）：
- **验收 5「纯门侧」成立** —— `tarch_normalize.py` 与 `as_measured.py` 相对 `8442442` **整文件零 diff**，
  转换器 `basis` 判据锚点**未动** ⇒ 排除了「把某一列改成迎合另一列」这种假修复。
- 五把新锁的**名字**：`..._e3_deleting_one_complete_facts_ring_reddens_only_that_ring` ·
  `..._e4_all_boundary_facts_empty_is_never_zero_comparisons_green` ·
  `..._e2c_converter_zone_fifty_metres_outside_all_facts_is_named` ·
  **`..._real_sm25_two_metre_footprint_vertex_spike_reddens_the_lost_view`**（验收 3，真实数据）·
  **`..._e4_multi_exterior_branch_has_an_explicit_synthetic_lock`**（验收 3b，⭐ 名字里自带 `synthetic`）。

⇒ **归你的三条**：
| # | 要验什么 |
|---|---|
| ① | **旧 commit（`8442442`）上三个静默形态仍复现得出** |
| ② | **新 commit（`0cd2858`）上三个都红，且「只红该红的」** |
| ③ | ⭐⭐⭐ **换同形输入仍走不通** —— ⛔ **请再找一个它没想到的**（下方 A1 是我点名的方向，但⛔ 别被我限住）|

---

## 二、⭐ 五个攻击面

### A1 · ⭐⭐⭐ 施工方自报的最薄弱处：**完整性复算与生产者共用同一段代码**

**它的原话**：正常 sm25 那 **4 个具名 exclusion**，「完整性复算与生产者**共用 `derive_boundary_edges`**，
存在**同因漏判**风险」。它点名要你打：**有效 footprint 下 owner/junction 整 ring 同因消失**、
在 `F1-z4/z5` 共用非 logical cavity 中追加幻觉 zone、**同 floor 多 plan view 的归属唯一性**。

⇒ ⭐ **这正是本项目的老病族**：[[self-consistent-gates-anchor-on-product-chosen-apertures]] ——
**用生产者自己的定义去复算生产者，只能验证「它没算错自己的谎」**。
请判：那道非空/全集断言，**在生产者与复算者同因失效时还剩什么分辨力**？

### A2 · ⭐⭐ 验收 3 那条「真实路径」锁，量到的是不是它声称的量

`..._real_sm25_two_metre_footprint_vertex_spike_reddens_the_lost_view`：
改前 `passed=True, paired=56`（整层静默丢边仍绿）· 改后 `passed=False, paired=56`。

⇒ 请查：① **`paired` 前后都是 56** —— 那红是**新断言**红的，还是别的原因红的？
② 把顶点挪 **0.5 m / 5 m** 呢，是不是也红、红在同一条断言上？
③ ⭐ **它红的是「丢了边」还是「footprint 变了」** —— 若是后者，这条锁量的是另一个东西。

### A3 · ⭐⭐ N4「零生产接线」它顺手办了 —— 接对地方了吗

你上一轮指出 `reconcile_boundary_basis` **全仓仅测试调用**（门只活在测试里）。
它报「staging producer 已接门，实跑 `paired=100 zones=29/29`」。

⇒ 请查：① 接在**哪一步**、**谁在什么时候会真的触发它** ② **失败时会不会响亮**（还是只记一条 diagnostic）
③ ⭐ 走查/签字那条链上**人真的会看到它**吗（本项目刚栽过 F-148：补偿闸看不见它该看的量）。

### A4 · ⭐ 验收 3b 的诚实度

`exterior ring ≠ 1` 分支**零真实存货**（主控普查：sm24 / sm25 签字件 / sm25 as-received 五个 view 全是单 ring；
sm21 结构上走不了）。它把这件事登记进了层契约、锁名里带 `synthetic`。

⇒ 请核：① 层契约里那段话**有没有把合成说成真实覆盖** ② 除了这一处，**还有没有别的分支也是零存货却没被登记**。

### A5 · ⭐ 禁令核对（⛔ 别信我，独立验）

`git show --name-only 0cd2858` ⇒ ① 答案根 `case_tests/test_baseline/gt/` **零条目**
② **没有扫走并行席位的东西**（唯一的 `as_drawn` 命中是层契约 **markdown**，不是模块 1 的代码面）。

---

## 三、⛔ 范围之外（显式对账）

- **模块 1**（as-drawn 生产者类型）—— **另一份请求书**，同样交给你，⛔ 不在本单
- **F-149 外部锚** · **F-152**（`string-path` 假边，今天新登记）· correction 侧 ·
  重签答案 · 改 `promote_gt_v3` · 全量（归主控，已跑）

⚠️ 两份请求书拆开送审 ⇒ **并集要显式对账**；缝里若有一块两份都没覆盖的，请点名。

---

## 四、裁决形式

`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` / `REJECT`；findings 分**阻断**/**不阻断**两栏，
每条带**可复现命令 + 实测数字**。裁决书落
`AI_agent/logs/reviews/verdict/2026-08-30_o21d_rework_crossreview_glm.md`。
⭐ 若某个攻击面本身问错了，直接说并给出正确的问法（今天你已正确纠正我三次）。
