# Plan review request — P0#1 跨层概念墙对齐 (envelope-first)

> **审阅方向（新）**：本项目现以 Claude 主导出方案、Codex 主执行。此 request = **Claude 的方案**，请 Codex **审方案**（不是审已写代码）。请站在「这个设计会不会引入错误/破坏现有不变量/有更简洁正确的做法」的角度 adversarial review，逐条给 agree / disagree / risk / alternative。**不要改任何代码**，只读 + 评。

## 1. 已坐实的根因（已自查 + Codex 侦察双确认）

`apply_deterministic_core` 的轴线图**已经是全楼共享**的（`src/agent/correction/deterministic.py:121-129`：footprint + 所有楼层 cell 的 x/y 汇成一份 `xmap`/`ymap`）。docstring 也宣称目标是 "the same wall on different floors becomes byte-identical"（`:6-8`）。

但合并机制**纯坐标聚类、不分 provenance**：`_build_axis_map`（`:44-87`）只对同一个 `axis_jitter_tol_m=0.05` 聚类。sm21 走廊在 F1 读成 y=[3.1,4.9]、F2 读成 y=[3.2,4.8]（差 0.10m）：

- identity 聚类：3.1 与 3.2 差 0.10 > 0.05 → 两个 cluster（`:61`）。
- snap 到 `structural_snap_grid_m=0.05`：仍是 3.10 / 3.20。
- sliver 合并：严格 `< min_edge_length_m=0.10`（`:73`），0.10 恰好不并 → **两条 canonical 轴线都活下来**。
- 结果：走廊↔房交界两层不共面 → 碎面（GPT 版 112 面 vs 06-16 Opus 对齐版 100 面）。

**核心缺陷**：系统分不清两种 10cm——
- **同层**两条 10cm 轴线 = **两堵真墙**（必须保持区分）；
- **跨层**两条 10cm 轴线 = **同一堵墙读偏了**（应合并；EP 鲁棒的安全默认，几何对错归 judge 层，符合 docstring `:13-16` 哲学）。

## 2. 设计目标 / 必须守住的不变量

1. 同层间距 > `axis_jitter_tol_m` 的两条轴线**绝不**因本次改动被并（不许误伤真墙）。
2. `min_edge_length_m` 保证不破（任意两条 canonical 轴线不近于 min_edge）。
3. **外包优先**：footprint（建筑外包总长宽，schema 里是单一矩形、本就全楼一致）为权威锚；内部墙向其归并，不反向。
4. 确定性 + image-blind（不引入任何"猜"，纯坐标 + provenance 规则）。
5. 全量 pytest 保持绿（现 277）。

## 3. 推荐方案：provenance-aware 跨层归并（两相聚类）

让归并知道每个坐标来自哪层，**跨层用更大的 `cross_floor_align_tol_m`（拟 0.20m），同层仍用 `axis_jitter_tol_m=0.05`**。

算法（每个结构轴 x、y 各跑一次）：
- **Phase A（同层 identity，复用现逻辑）**：对每层**单独**用 `axis_jitter_tol_m` 聚类该层坐标 → 该层候选轴线（reps，各带 floor 标签）。这一步保证「同层 10cm 两墙」各自独立。
- **Phase B（跨层 reconcile）**：汇总所有层 reps + footprint 坐标，按值排序、贪心成组：下一个 rep 并入当前组 **当且仅当** `(value − 组锚) ≤ cross_floor_align_tol_m` **且** 该 rep 的 floor 尚未出现在该组里（**同层互斥**：同层两 rep 永不进同一组，杜绝 3.1@F1 ~ 3.2@F2 ~ 3.3@F1 的传递链把同层真墙并掉）；否则另起新组。
- **组代表（envelope-first 加权）**：组内若含 footprint 坐标 → canonical = 该 footprint 坐标（snap 到 grid），其余向它归；否则 = 组内 reps 的（可加权）均值 snap 到 grid。
- **Phase C（复用现有 grid snap + sliver guard）**：对 Phase B 产出的 canonical 集再跑一次 `structural_snap_grid_m` + `min_edge_length_m` sliver，保证不变量 2。

产物仍是 `{raw_value: canonical}` 映射，下游 `_snap` / `axis_then_reach` 不变。

## 4. 落点 / 签名改动

- 落在 `apply_deterministic_core` 内：现在 `:121-129` 把所有层 pool 进一个 list 再 `_build_axis_map`。改为：按层收集候选轴 → `_reconcile_cross_floor(...)` → 得到 map。
- 倾向**新增** `_reconcile_cross_floor(per_floor_axes: dict, footprint_coords, tol)`，复用现有 cluster/snap/sliver 子步，而非重写 `_build_axis_map`（保护其已有测试）。请评：是改签名 in-place 还是新函数更干净？
- 新配置 `cross_floor_align_tol_m`：加到 `src/configs/correction.yaml` + `config.py`（`CoreTolerances` 字段 + 校验）。排进不变量链：拟 `axis_jitter_tol_m < cross_floor_align_tol_m < gap_close_threshold_m`（0.05 < 0.20 < 0.30），并保持 `min_edge_length_m ≤ cross_floor_align_tol_m`。请评取值与排序。
- docstring（`:1-31`）需补「跨层 reconcile tier」描述。

## 5. 已考虑并否决的替代

- **A. 直接调大 `axis_jitter_tol_m` 到 >0.10**：否决——会把同层真正 10cm 的两墙也并掉（破不变量 1）。
- **B. 把 sliver 合并从 `<` 改 `<=`**：只能恰好治本案的 0.10，治不了 8cm/12cm 跨层 jitter，且会误并同层恰好 min_edge(0.10) 的合法薄构件。否决。

## 6. 验收 / 测试计划

- **单测**：① 两层走廊 3.1/3.2 → 单一 canonical y 轴；② 同层两墙 3.1/3.25（< cross_floor tol 但同层）→ 保持两条（同层互斥生效）；③ 传递链 3.1@F1/3.2@F2/3.3@F1 → 不塌成一条。
- **回归**：现有 kernel/checks 测试全绿（277）。
- **端到端**：用 GPT-5.4 reading 重建 sm21_anchor，走廊跨层 y 轴对齐、面数从 112 降到对齐值；EP 仍 0 severe。

## 7. 请 Codex 重点回答

1. 同层互斥 + 贪心成组：有没有反例会**误并同层真墙**或**漏并应并的跨层墙**？贪心排序窗口的经典缺陷在此算法下会不会触发？
2. envelope-first 加权的具体实现（footprint 坐标做硬锚 vs 高权重均值）哪个更稳？footprint 同时落在两个相邻内部轴附近时怎么裁？
3. `cross_floor_align_tol_m=0.20` 是否安全？有没有真实建筑里「内部墙跨层确实平移 ~0.15m」会被本方案错误对齐的情形（即把真实退台/错位墙当成 jitter 抹平）？这种该不该交给 judge②/unsupported 而非静默对齐？
4. 新函数 vs 改 `_build_axis_map` 签名：哪个对现有测试与可读性更优？
5. 有没有比「两相聚类」更简洁且同样正确的做法（例如基于 footprint 锚 + 单遍约束聚类）？

---

## v2 — Revised after Codex review (REWORK 全部 BLOCKER/MAJOR 已处置)

Claude 裁决：接受 REWORK。§7.1/§7.2/§7.3 三处 DISAGREE 全采纳。贪心 + provenance-blind sliver 改为**约束匹配 + provenance-aware**；footprint 改硬锚；tol 收紧到 0.12 并把安全性从「靠 tol」转移到「靠 mutual-nearest + 冲突即 flag」。设计哲学显式对齐 `correction.yaml:32-33`（歧义升 judge②，不静默合）。

**算法（结构轴 x、y 各跑一次）**

- **Phase A — 同层 identity（复用现逻辑，保留全部 raw 成员）**：每层**单独**用 `axis_jitter_tol_m=0.05` 聚类该层 cell 坐标 → 每层候选轴 reps；**保留 raw→rep 全映射**（修 §7.4/§MAJOR：最终 map 必须覆盖每个 raw 值，否则 `_snap`(`:90-91`) 漏掉非精确等于 rep 的值）。
- **Phase B0 — footprint 硬锚**：footprint_x/y snap 到 grid → **固定** canonical 轴，永不被平均移动（修 §7.2）。
- **Phase B — 约束跨层匹配（mutual-nearest + 冲突即 flag）**：
  - 候选边：**不同层** reps 间、距离 ≤ `cross_floor_align_tol_m`。
  - 接受规则：**每层每组至多一个 rep**；仅并 **mutual-nearest** 对；若某 rep 有竞争候选（另一层 tol 内有 ≥2 个 rep，或两 rep 争同一伙伴）→ **歧义 → 不并**、保留各自、写 `cross_floor_ambiguous` flag 供 judge②（对齐 `correction.yaml:32-33`）。
  - rep 落在某 footprint 硬锚 tol 内 → 归到 footprint（footprint 不动）、每层至多最近一个、且不得使 cell 塌陷；竞争 → flag（修 §7.2 magnet 风险）。
  - 组 canonical = 成员 reps 均值 snap 到 grid（含 footprint 的组取 footprint 值）。
- **Phase C — provenance-aware sliver guard**：跑 min_edge sliver，但**绝不**合并「各自支撑里含 ≥min_edge 的不同同层轴」的两条 canonical；这类残余 sliver → flag，不静默合（修 BLOCKER#1 / §7.5.5）。
- **map 产物**：`{raw_value: canonical}`，覆盖所有 raw（Phase A 已保留）。

**容差** `cross_floor_align_tol_m = 0.12`：需 >0.10 才吃得下 sm21 的 0.10 jitter；<0.15 才保住真实错位。排序 `axis_jitter_tol_m(0.05) < cross_floor_align_tol_m(0.12) < gap_close_threshold_m(0.30)`。**不**设 `min_edge ≤ cross_floor_align` 为语义不变量（修 §7.3/§MAJOR）。安全性主要靠 mutual-nearest + flag，不靠 tol 数值。

**实现约束**：新增 `_reconcile_cross_floor(...)`，不改 `_build_axis_map` 签名（保留为兼容包装；抽小 helper 复用 identity-cluster 与 snap/sliver）；新增 `cross_floor_align_tol_m` 到 yaml+config（验证链 + 测试构造器同步，修 MINOR）；audit 用新 rule_id `deterministic_core.cross_floor_align` 命名新容差、歧义用 `cross_floor_ambiguous`（修 MINOR audit label）。

**策略变更（显式记录）**：跨层超 jitter 的**无歧义 mutual-nearest** jitter → 对齐 + 审计；**有歧义/竞争/可能真实错位** → flag 给 judge②，不静默对齐。这是对 `correction.yaml:32-33` 哲学的遵守而非违反。

**v2 待 Codex 二审**：(a) Phase B 的 mutual-nearest + 冲突即 flag 是否还有漏并/误并反例？(b) 0.12 取值是否同意？(c) Phase C provenance-aware sliver 的「同层冲突」判定是否完备？(d) 还有无遗漏的 BLOCKER/MAJOR？

---

## v2.1 — Implementation spec（APPROVED, dispatch-ready）

二审结论 APPROVE-WITH-CHANGES、无 BLOCKER。Claude 裁决并固化 4 处修订，以下为执行器唯一权威实现规范（实现这一节即可，前文为推导背景）。

**裁决的 4 处修订**
1. `cross_floor_align_tol_m = **0.11**`（非 0.12；0.12 会抹 0.10–0.12m 真错位）。
2. 冲突判定上升到**组件/图级**（非仅 pairwise）：杜绝 3 层传递链误并。
3. Phase C 同层冲突判定引用**原始 Phase A 每层 reps**；残余不安全 sliver → block/flag、不静默合。
4. flag 路由：歧义/竞争/疑似真错位 → **轴线保持分离 + 写 advisory `corrections` 条目**（rule_id `deterministic_core.cross_floor_ambiguous`）；**严禁写 `unsupported`**（不可硬拒 build）。

**要改的文件**
- `src/agent/correction/deterministic.py`：新增 `_reconcile_cross_floor(...)` + 接进 `apply_deterministic_core`（替换 `:121-129` 的「全 pool → `_build_axis_map`」）；`_build_axis_map(values, tol)` **签名不变**，保留为兼容包装，可抽 `_identity_clusters` / `_snap_sliver` 小 helper 复用。docstring(`:1-31`) 补「cross-floor reconcile tier」。
- `src/agent/correction/config.py`：`CoreTolerances` 加 `cross_floor_align_tol_m` 字段 + 加载 + 验证（链：`axis_jitter_tol_m < cross_floor_align_tol_m < gap_close_threshold_m`；**不**断言 `min_edge ≤ cross_floor_align`）。
- `src/configs/correction.yaml`：加 `cross_floor_align_tol_m: 0.11` + 注释（跨层同墙 reading jitter 对齐上限；安全靠 mutual-nearest+flag 非 tol）。
- 测试：新增单测 + 更新构造器 `tests/test_deterministic_core.py:13-27`、`tests/test_kernel_guards.py:15-29`（新必填字段）。

**算法（结构轴 x、y 各一次）**
- **Phase A 同层 identity（复用现逻辑 + 保留全部 raw 成员）**：每层单独用 `axis_jitter_tol_m` 聚类该层 cell 坐标 → 每层 reps，**保留 raw→该层 rep 全映射**（终 map 必须覆盖每个 raw，否则 `_snap`(`:90-91`) 漏值）。
- **Phase B0 footprint 硬锚**：footprint_x/y snap 到 grid → 固定 canonical，永不被平均移动。
- **Phase B 约束跨层匹配（component-level、mutual-nearest、冲突即 flag）**：
  - 候选边：**不同层** reps 间距 ≤ `cross_floor_align_tol_m`。
  - 用 mutual-nearest 边构连通分量；**合法分量 = 每层至多 1 个节点 且 直径 ≤ tol 且 无竞争**；任一节点在 tol 内有 ≥2 个跨层候选、或分量违反每层≤1/直径约束 → 该处**不并、保留分离**、写 `cross_floor_ambiguous` advisory。
  - rep 落在某 footprint 硬锚 tol 内 → 归 footprint（footprint 不动）、每层至多最近 1 个、且不得使 cell 塌陷；竞争 → flag。
  - 合法分量 canonical = 成员 reps 均值 snap 到 grid（含 footprint 者取 footprint 值）。
- **Phase C provenance-aware sliver**：跑 min_edge sliver，但比较时引用**原始 Phase A 每层 reps**：两条 canonical 若各自支撑含「≥min_edge 的不同同层轴」→ **绝不合并**，残余 sliver 写 advisory flag；仅当无同层冲突时才按原 sliver 合。
- **map 产物**：`{raw_value: canonical}` 覆盖所有 raw。下游 `_snap`/`axis_then_reach` 不变。

**审计**：跨层对齐移动写 `corrections`，rule_id `deterministic_core.cross_floor_align`、tolerance_name 含 `CROSS_FLOOR_ALIGN_TOL`；歧义写 `deterministic_core.cross_floor_ambiguous`。

**不变量（必守）**：①同层 >jitter 两轴绝不被本改动并；②任意两 canonical 不近于 min_edge；③footprint 不被移动；④确定性 + image-blind；⑤全量 pytest 绿。

**单测（必加）**：① 两层走廊 3.10/3.20 → 单一 canonical；② 同层 3.10/3.21 + 另层 3.19 → F1 两轴不被 Phase C 并、且 3.19 正确匹配 3.21 一侧（或 flag）；③ 3 层链 3.10@F1/3.18@F2/3.26@F3（tol=0.11，相邻 0.08<tol 但端到端 0.16>tol）→ 不塌成一条（component 直径约束生效）；④ 竞争：3.10@F1 + 3.17@F2 + 3.29@F2 → 不静默抢、写 ambiguous flag。

**验收**：全量 pytest 绿（现 277 + 新增）。sm21 端到端面数回归由 Claude 另跑。
