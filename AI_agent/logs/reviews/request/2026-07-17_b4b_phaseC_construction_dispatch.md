# B4b Phase C 施工派发（terra 执行档，2026-07-17）

**任务**：按 [AI_agent/proposals/c2_b4b_detail_spec.md](../../proposals/c2_b4b_detail_spec.md) **v2 定稿**施工 **Phase C（Elevation、fusion、policy 与 capability 完整面）**（稿 §13 Phase C）。该稿是唯一施工合同（累计式自包含）；本单**只放行 Phase C**。Phase A（identity/score inputs/sidecar v8 skeleton）+ Phase B（plan segment/opening matching/denominator）已 CLOSED 收录。

## 前置门（全部已满足，可开工）
- **B4b Phase A/B 已合并**（score_schema/config/inputs + segment_score.py + opening_claim_score.py 的 plan 面 + 精确 partial denominator + 三 ledger Va 调用骨架 CLOSED）。
- **B4a A–D 全 CLOSED**：elevation z 配对 + render seam（`gt_to_render_model`）+ GT schema v3 + source refs 全 typed 落地。
- **B4B-REC-C 逐字对账门已 PASS**（主控 Opus 先行，[verdict/2026-07-17_b4b_rec_c.md](../verdict/2026-07-17_b4b_rec_c.md)）：四项全一致 + 30/30 行为探针——① elevation source refs/view kind/floor/facade identity；② render/source-view binding seam（`gt_to_render_model` via `projection_surface_key`、plural keys、`source_view_id`）；③ verified overlay 独立性口径（`visible_intervals` 是 Vg 派生量、**非独立观察真值**，证据独立性只由人工 overlay 签收提供）；④ Va 唯一 applicability 引擎公开面（四类型 + `derive_opening_claim_applicability` + 四行 status/reason + 七 CLAIM_ORDER + 双 GeometrySourceKind）。
- **基座 = HEAD `04d293d`（1194 绿 + 9 xfail，树干净）**。

## Phase C 范围（稿 §13 Phase C 施工 + §7.3–7.5 / §8.4.1 / §8.5–8.8 / §9.2 / §4.2，以稿为准）

在 Phase B 的 plan 计分之上，**扩** `opening_claim_score.py` + **加** `score_policy.py` 的 v3 policy：

1. **elevation actual-segment projection**（§7.3 步骤 2 / §8.8）：用 §6.3 已验真的该 view frame，forward map `world_along = along_origin + sign*local_x`；逆映射 target 两端 → Va 标准通道 local→world→升序→∩target→∩visible_intervals。**mirror/local-x 只按 bindings 变换**，不再额外翻转或套产品 mirror。
2. **mirror / local x / direction frame**（§8.8）：`true`/`unknown` direction 无外部 resolution → **整 view REJECTED**。
3. **sill/head/floor-line score**（§8.8 elevation 可评分 existence/along/width/sill/head）。
4. **plan/elevation 多 source fusion / conflict**（§8.7）：两个独立可观察 source 冲突 = conflict（入 denominator、按 fail units）；**禁用多个弱 partial 自动拼成 full**，除非 applicable interval union 经 Va totality 明确覆盖 T；拼接 denominator 上限仍为 1。
5. **host judge-only 关系评分**（§8.4.1 / §8.6）：host 只按 plan 的唯一 segment+zone 关系评分，**judge-only、不写回 canonical host、不抢 B5 resolver 所有权**；host 只对 unobserved residual 记 NA。
6. **appearance / z-null NA**（§8.5 capability/reference-value override）：appearance 逐 claim = 0 + reason `reference_value_unavailable`；door 及未支持 opening kind 的 row = NA reason `unsupported_target_kind`；GT value 为 null 的 sill/head = 0 NA——**这些 override 先于 Va coverage 执行，不得被 Va 可观察 coverage 抬成可计分**。
7. **v3 criteria / verdict**（§9.2，`score_policy.py` 新增 denominator-aware v3 policy）：每 criterion wire 含 `eligible`/`denominator_units`/`passing_units`/`failing_units`/`na_reasons`/machine verdict；identity/totality 非法 → 顶层 REJECTED，不进 StageVerdict 聚合。
8. **unsupported combination 顶层 NA**（§4.2 冻结矩阵 / §2.3 不变量 7）：correction v1/v2 → `unsupported_product_schema`；未知 GT profile → `unsupported_gt_profile`；**机器可读 NA/REJECTED，禁空对象/零分/legacy fallback**。
9. **trusted negative conflict**（§8.6.1）：产品某 source 无 positive 而该 source trusted negative interval 覆盖 target 可评分 slice + 另一 source 有产品 positive → 该 slice conflict；negative 只覆盖部分时按 §8.5 endpoints 切开只给覆盖部分 units；无 completeness/遮挡/裁切/区间外缺失**不产生** conflict。
10. **逐 target/claim totality**（§6.6 / §6.7）：criterion passing+failing=denominator；eligible=false 当且仅当 denominator=0 且 verdict=not_applicable。

## 硬不变量与禁区（违即偏差）
- **Va 是唯一 applicability 引擎**（§2.3）：elevation applicability 同样一律走 Va 公开函数，**禁在 scorer 里重实现「看起来可见」的 extra 判据**（§8.6：Va `negative_evidence_intervals` 只进 absence/conflict，**不能从 GT target 相减、不能充当第二份观察真值**）。
- **visible_intervals 非独立真值**（REC-C ③ / 稿 §... / B4a §9.6）：可见性类 claim 判分政策**不得**把 `visible_intervals` 当独立证据源；证据独立性只由 verified 门人工 overlay 签收。
- **精确 partial 分母守恒**（§8.5，接 Phase B 的 gate B4B-B4）：host/along/width 分母 = 精确几何比例；existence/sill/head 可见即 binary；**禁固定 0.5 / 硬编码分母**；NA/0/miss/conflict 守恒必须成立。
- **frame 只从受信 bindings**（§6.3.8 / gate C1）：`mirrored`/`local_x_positive`/frame-transform 只来自受信 `view_projection_binding_v1`；产品输出同名字段**只可作一致性审计、不能驱动 denominator**。
- **judge-only**（§2.2 / §12.3）：本批全落 `src/agent/judge/`；**生产路径（executor/correction/reading/pipeline）零 import 本批模块**；`facade_applicability.py`（Va production 侧）**只有 source scan 发现 no-op 回归才改**，否则一行不动。
- **明确不改**（§12.3）：production output schema、`view_manifest.py` base emitter、`RunManifestV2` artifact key union、任何 `case_tests/.../gt`/golden/verified overlay、B5/B5b/B6。
- **legacy 锁定**（§9.1 / §12.2）：legacy v2 wall/window/boundary/elevation counter/criteria/verdict/renderer 语义、legacy policy 一律不动；typed dispatch adapter 加旁路，不在旧函数塞 v3 分支；`elevation_score.py` legacy overlap 行为锁定。
- **⚠️ import footgun（REC-C 观察 O2，必守）**：`ElevationViewBindingV1` **同名两型**——`gt_manifest.ElevationViewBindingV1`（DXF 提取 binding，15 字段）与 `facade_applicability.ElevationViewBindingV1`（Va 方向/frame binding，13 字段 input_id/world_axis/sign/mirrored/frame_transform_sha256/…）**字段集不相交、是两个不同类型**。本批**必须** `from src.agent.correction.facade_applicability import ElevationViewBindingV1`（稿 §16 L766 已定 import 源），不得误引 gt_manifest 那个。
- **不越界 Phase D 领地**（§13 Phase D）：**不做** `SCORER_SCHEMA "7"→"8"`、full identity cache validator、sidecar/PNG 原子 pair、typed polygon renderer/gray hatch PNG、CLI service dispatch、legacy v2 regression 封口、VA-C7 六项最终债务扫描、最终 import boundary/static scan。sidecar v8 保持 Phase A skeleton 的 wire（Phase C 填几何/policy 结果字段，但 schema 常量仍 "7"→"8" 的 bump 归 Phase D）。
- **不越界 Phase A/B 稳定件**：score schema/config canonical hash、sidecar v8 identity、A0 frame preimage、segment/opening assignment determinism 已 CLOSED，不 revert 不重构。
- 若必须跨界或改 Va 才能过验收 → **停止报 blocker**，不擅改。

## 测试纪律（稿 §13 Phase C 测试矩阵，全数落地、真断言）
逐条落地，**负轴不得 shipped-untested**（升一档审专抓此型）：
- **mirrored/non-mirrored 相同世界结果**（§7.3 性质测试：sign±1、mirror 两态、local-x 两态逆映射经同一 forward map 精确恢复 T；切短 visible intervals 只收窄 Va output）；
- **true/unknown 缺 resolver 拒绝**（整 view REJECTED）；
- multi-facade same family；
- plan-only z-null；
- sill/head partial binary eligibility；
- source conflict 进入 conflict units；
- **host 三面**（正确 / 错误 / 歧义）；**appearance 明确 NA 且不入 denominator**；
- correction v1/v2 + GT v3 → 顶层 NA；
- door row `unsupported_target_kind`；
- 全核心 criterion NA 的顶层 verdict。
- 稿章节→测试映射表 + 五出口 gate 逐一具名落测。
- 定向组逐组记 passed 数；**全量 pytest 归主控轻门**（codex exec ~30s 杀长前台进程，执行器全量自验不可得——targeted suite 自验即可，别指望跑全量）。

## 出口 gate（§13 Phase C，逐一具名落测）
- `B4B-C1-frame-trust`（frame 只从受信 bindings，产品同名字段不驱动 denominator）
- `B4B-C2-elevation-claims`（elevation existence/along/width/sill/head 计分 + appearance NA + true/unknown REJECTED）
- `B4B-C3-fusion-totality`（多 source fusion + conflict + 弱 partial 不自动拼 full + denominator≤1）
- `B4B-C4-na-machine-surface`（unsupported combination 机器可读 NA/REJECTED，无空对象/零分/legacy fallback）
- `B4B-C5-policy-conservation`（criterion passing+failing=denominator；miss/conflict>阈值→fail；identity/totality 非法→顶层 REJECTED 不进聚合）

## 交付
1. 工作树内代码+测试（**不 commit**）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-17_b4b_phaseC_construction_brief.md`（改动映射 / 稿章节→测试映射表 / 五 gate→测试 / 验收各组 passed 数 / 预期行为变化 / 未决·偏离 / review-ask〔无则注明 none〕 / 本批改动文件清单）。**如实披露未竟项**（"未做说成留给审查"属披露偏差，会记档）。
3. terse report（各组 passed / 改动文件 / 关键结论 / 偏差 / review-ask 摘要），不贴 diff。

审向：**Opus 子代理执行审（升一档·独立上下文·活体探针）→ 主控轻门（独立全量 + 抽查 + 裁决）**。重点探：① frame 信任根（产品 mirror/local-x 能否篡改穿透进 denominator）；② Va 是否真被调用非重实现 elevation applicability（信任根）；③ 弱 partial 是否会被自动拼成 full（totality 假绿）；④ appearance/door/z-null NA 是否真不入 denominator（恒真式/override 被 coverage 抬起）；⑤ 负轴测试矩阵是否全落真断言（shipped-untested）；⑥ 是否误碰 Phase D 领地（schema 8 / PNG / CLI）。
