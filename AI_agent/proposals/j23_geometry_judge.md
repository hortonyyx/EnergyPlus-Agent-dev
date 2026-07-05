# J23 几何 judge + `score_geometry_vs_gt`（DEFERRED · P2）

> **状态：DEFERRED / P2（用户 2026-07-02 定 defer、"后面再想怎么做"）。** 理由=几何本就人工看 3D HTML
> viewer 过一遍；J0/J1 过后 J23 多半判"形态像不像"、主观、参考意义小。规范跑测流程 **P1 已落地**
> （`7.02_FlowP1BatchA/B/C`），本文 = 其中 **P2 部分的活设计**（当时随 P1 一起提、被 defer）。
>
> **溯源**：本设计原稿在 `logs/reviews/request/2026-07-02_standardize_test_flow_proposal.md` §8.5/§8.8/§8.11#5 +
> `logs/reviews/verdict/2026-07-02_standardize_test_flow_review_final.md`。2026-07-05 从 logs 抽出归位 proposals/
> （logs 那份留作 P1 落地的冻结审轨）。**一旦动工，按本文补落码执行简报 → Codex 独立 review → 执行。**

## 1. 补的空洞

当前几何一层（stage 2/3）只有 **gate① 确定性 + 人工 3D 确认门**，**没有 per-run judge**（J23 未落地）——
过度分区 / 欠合并这类**内核能力缺陷**（sm24 非方形已暴露：L 走廊拆 2 区、阶梯 office 拆 3 区）在 judge 层是空洞。
J23 = 判 **built 几何**，补这个空洞（S1）。

## 2. J23 rubric（判 built 几何）
① **热区分解保真**（过度分区 / 欠合并 vs gt——sm24 类）
② 空气耦合 / 邻接语义（导热对但缺 AirBoundary/ZoneMixing？）
③ 3D 体量 vs 图
④ 窗落 built 面
⑤ 计数 vs gt（内核合法碎裂要有解释）

判卷口径同 J0/J1：**`score_geometry_vs_gt` 数据对账权威 + 看图辅助**（[[judge-gt-authoritative-images-auxiliary]]）。

## 3. `score_geometry_vs_gt`（新，照 `score_reading_vs_gt` 路子）
built zone/window ↔ gt 逐元素对账 + 热区数。judge-side（经 `load_gt` 读 gt，不破 gt 隔离铁律）。

## 4. 3 开关几何格
- **review on** → 人工看既有 `manual_review/geometry_viewer.html`（**不新渲 overlay**）。
- **review off + judge on** → **J23**（数据层 `score_geometry_vs_gt` 权威 + 感知辅助可用 viewer 静态 PNG 导出 /
  `render_building_3d`）。
- 都关 → continue。

## 5. 内核能力缺陷路由（关键）
J23 判出的过度分区 / 欠合并**根因是内核能力缺陷、非随机 draw** → 路由 **JUDGE_BLOCK_HUMAN + backlog**
（**不**盲重抽——重抽同一确定性内核不会变），交人 + 记 C2 能力升级。**红利**：J23 判多了可把不吃 gt 的启发式沉成
gate① 几何检查（如"相邻同 role 矩形区共享整边 + 仅导热 → 疑过度分区 / 该 air-boundary"），把判据机械化。

## 6. 动工前提（比 P1 侵入，故 defer）
1. **reorder / wrap stage-3 几何门**（§8.11#5）：现 `_post_gate1` 几何 approval 门在 judge dispatch **之前** →
   J23 跑不到；要改成"**J23 先判、人工 3D 后审**"。这是结构改动、值得独立 review/test pass。
2. **`score_geometry_vs_gt`** 实现。
3. **sm24 gt**（量化过度分区需要；sm24 非方形首跑已收口但**无 gt**，见 [[sm24-nonsquare-first-run-2026-06-24]] +
   plan.md N3）。
4. 测试：J23 deterministic-root 路由 / geometry auto 审计字段 / post-judge 人工校验 resume。

## 7. 关联
- 补几何 judge 空洞 = 三层叠加门的 geometry↔J23 那一格（guide `new_case_guide.md` §0）。
- 与 C2 非方形能力升级同源（过度分区→区合并/air-boundary，见 plan.md 中期 + `capability/pipeline_0-5_capability_upgrade_suggestions.md`）。
