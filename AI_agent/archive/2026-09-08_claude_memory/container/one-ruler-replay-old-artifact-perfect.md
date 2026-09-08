---
name: one-ruler-replay-old-artifact-perfect
description: 2026-08-02 判决性回放：07-07 老产物用今天的 v3 尺子重判 = 内墙 100%、多画 0m ⇒「正确路径存在」已证实；同轮挖出 mirrored 误杀立面 + 严格档从未执行两条 P0
metadata: 
  node_type: memory
  type: project
  originSessionId: 870845d7-50a9-4bc6-961b-9d882182dd3f
  modified: 2026-08-02T11:21:38.102Z
---

**2026-08-02 主控自跑，零代码改动**。全档 `AI_agent/logs/experiments/2026-08-02_one_ruler_replay/README.md`。

**⭐⭐ 一把尺子的纵向回放（此前一直被判「量纲不可比」）**：把 **07-07 sm24 老产物**（Haiku 4.5 + CV 工具箱）
喂进**今天的 v3 生产判卷层**（同 GT / 同 bindings / 同容差 / 同全卷五张；先用新件复现已落盘的 53.31/57.86 验证姿势）
⇒ **老件内墙 57.86/57.86 = 100 %（20 行全 `complete`）· 外轮廓 60/60 · 多画 0 m**；
今天 Sonnet 全卷 = 92.1 % · 60/60 · 多画 6.77 m（丢分在漏掉右下小房间三面墙 4.55 m，**不在**那 12 段 0.06 m 上）。
**⇒ 用户「正确做法一定存在」从强推断升级为已证实。**

- **做法差别写在 provenance 里**：老件 14 条平面墙 **13 条 `dimension_derived`**（单条最多引 12 个尺寸标注）、38 份 CV 证据；
  今天 10 条墙 **10 条全 `seen`**、引用 ≤2。⇒「量而非看」在产物层面成立，今天这轮没做到。
- **回放前提（也是此前没人能重量老件的原因）**：老件缺 07-31 才立的 `scale_origin` 契约 ⇒ **原样进尺子必然全 0**；
  补值取自产物自己的 `calibration_note`、几何未动。gate① 有 `reading.plan_scale_origin_usable` 在 golden/regression 硬拒，属已知设计。
- **⚠️ 仍不能说「无监督全对」**：该 run 的 `llm.yaml` 逐字写着 prompt 级隔离 + **2 轮 rework**（纪律 1 + schema 1）。

**⛔ P0 断线一 = `mirrored:"unknown"` 误杀整张立面**：`reading_typed_adapter.py:273 _facade_sense` 把 `"unknown"`→`None`，
`:873` 与 binding 的 `false` 不等 ⇒ `_na_components(..., retain_as_miss)`，**在读 strokes 之前就 return**。
**判决性对照：只把这一个词改成 `false`、几何一字节不动 ⇒ 老件与新件双双 existence/along/width/sill/head 各 11/11 全 `complete`、
`window_elevation_geometry` 0/44 → 44/44、墙面不变。** 而 `guide.md:351` 明列 `unknown` 合法、判卷 CLI 注释写着
*"product-provided mirror declarations are not read"*。**⇒ 收回「窗是唯一真缺口」「平面窗连续三轮全崩」。**

**⛔ P0 断线二 = 声明的严格档从未真正执行**：`run_config` 声明 `orthogonal_polygon`+`regression`，
落盘 `checks.json` 头部却是 `rectangular`+`exploratory`；该 run gate① **本来抓到 5 条 fail**
（`dimension_chain_closure` ×4 + `stroke_dimension_consistency` ×1），按档位重算 `blocking()`：
**exploratory ⇒ 0 · regression ⇒ 4** ⇒ 严格档若生效，产物当场被拒。**且它抓的正是「尺寸链不闭合 / 看着画」这同一个病灶。**
另：`view_manifest` 五张全 `dimensioned:false`（图纸带完整尺寸链）⇒ 尺寸类检查大批 N/A。

**⛔ 主控当轮被用户纠正一次（记住这个错法）**：主控把「基准收口（轴线 vs 墙面）」列成要用户拍板的事项，
**用户当场指出通道优先级与出模 `zone_frame` 早就定过了**。核查后主控撤回：
`guide.md §0.2` 明写「plan 粗黑墙在仿真里**就是 centerline**、`thickness_m` 恒 null」，
GT `coordinate_frame` = `building_axis_world_m`（轴线）⇒ **两边契约本来一致、无歧义**；
08-02 那 12 段是 **`position_error` 系统性 0.06 m（=120 内墙半厚）· axis_err 0 · extent_err 0 = 纯平移**
⇒ **契约已写、这一轮没照做**（描了墙的一侧边）；07-07 老件精确命中因为尺寸链标注就打在轴线上。
**⇒ 教训：把「没人执行」误诊成「没有规定」，会平白给用户添一个不该有的决策。先查契约再列拍板项。**
**⇒ 由此「契约写了但零机器消费者」凑满四例**：`self_check` 字段 · `cv_evidence` · `access_log.jsonl` · centerline 规定
⇒ **R3 的真正目标 = 给已有规矩配机器消费者，不是再写规矩。**

⇒ 排工表见 `AI_agent/plan.md` 顶部「2026-08-02 晚」条（R0→R8）。相关 [[controller-must-stay-out-of-product]]
· [[reading-supervision-contamination]] · [[quality-first-descend-from-strong-model]] · [[wall-thickness-dimension-basis-direction]]。
