# B4b Phase C 施工简报（2026-07-17）

## 结果

Phase C judge-only 施工完成，未 commit。未改 `facade_applicability.py`、production 路径、legacy elevation scorer 入口、schema 常量、renderer、CLI 或缓存/原子写路径。

## 返工 r1（执行审 REWORK 闭合）

- **MAJOR-1**：`score_opening_claims_v3` 不再把 reference ledger 中「GT positive 与 completeness negative 同存」的 source 当作 absence 证人。trusted-negative conflict 现必须同时满足：reference source 无 GT positive/无 applicable interval、product ledger 显式声明该 source absence、另一 source 有产品 positive。无 `product_ledger` 时不推断 absence。
- **MAJOR-1 回归**：新增「正确单 plan observation + 冗余 GT-positive complete elevation sources → complete」；原 C3 false-green 已替换为真实 §8.6.1 item-2：添加 complete、negative-capable、但无 GT opening positive 的 elevation source，product-Va ledger 显式无 positive declaration，另一 plan source positive → conflict。
- **Phase B twin**：探针确认共病可达；`score_plan_claims` 采用同一「排除 reference GT-positive/applicable decision」规则。原 `test_b4b_real_trusted_negative_conflict_is_scored_from_va` 锁死错误 `conflict` 预期，已更名并纠正为 `complete`；另加冗余 source 回归。
- **projection 接缝**：前轮「未决·偏离:none」遗漏了 `project_typed_elevation_observation` 与 scorer 尚未被 production normalizer/CLI 串接。补了 typed-local → projection → `score_opening_claims_v3` 的端到端测试，并翻转原始产品 self-report mirror/local-x 断言 claim row 字节相等。production normalizer/CLI 接线属派工单禁止的 Phase D；本测试以 projection 函数作 normalizer stand-in。
- **MINOR-1**：policy 以 `PlanSegment.exterior` 分开 interior wall rows 与 exterior boundary rows，不再共享 segment denominator；新增 pass/fail 分区断言。
- **MINOR-2（主控接受）**：`window_elevation_geometry` 保持可分离的 sill/head-only，代码注释登记 channel-fused along/width 无法在当前 row wire 分离的调和债。
- **MINOR-3（主控接受）**：`no_oversplit` / `negative_evidence_complete` 保持显式 NA，代码注释登记 Phase C 无对应 aggregate scorer 的接缝。

## 改动映射

| 合同面 | 落地 |
|---|---|
| §7.3 / §8.8 受信 elevation frame 投影 | `elevation_score.py` 新增 `TypedElevationObservation`、`project_typed_elevation_observation`；只导入 `facade_applicability.ElevationViewBindingV1`，以 `along_origin + sign * local_x` 投影，不接收产品 mirror/local-x 字段。true/unknown 未经 sidecar resolution 直接 `score_direction_unresolved`。 |
| §8.8 floor lines | 新增 judge-only `score_typed_elevation_floor_lines`，以实际 floor z 比较；z 无 mirror/local-x 变换。 |
| §8.4.1 / §8.5–§8.7 | `opening_claim_score.py` 新增旁路 `score_opening_claims_v3`；沿用 Phase B Va reference ledger、既有 judge-only host resolver、精确 `eligible_units` 和 claim summary。多 source 逐 source 比较、complete-vs-miss conflict、Va trusted-negative conflict、slice 分配与 totality 检查均在此旁路。 |
| §8.5 NA overrides | v3 路径先执行 appearance、door、z-null sill/head override；不由 coverage 抬升分母。 |
| §9.2 | `score_policy.py` 新增 strict `V3Criterion` / `V3PolicyVerdict` 及 `c2_v3_score_policy`。每 criterion 有 eligible、denominator/passing/failing units、NA reasons、machine verdict；identity/totality 直接 machine rejected。legacy `reading_score_criteria` 未动。 |
| Phase C 实测 | 新增 `tests/test_c2_b4b_phase_c.py`；扩 `real_va_context` 以可选择为 elevation 提供真实 completeness，从而 fusion/negative 测试仍通过真实 Va 调用。 |

## 稿章节→测试映射

| 章节 | 测试 |
|---|---|
| §7.3 frame inverse / Va-only shrink / scorer seam | `test_b4b_c1_frame_trust_forward_inverse_restores_world_target`；`test_b4b_c1_frame_trust_shorter_visible_intervals_only_shrink_va_output`；`test_b4b_c1_projection_to_v3_scorer_ignores_product_frame_self_report` |
| §8.4.1 / §8.5 / §8.8 elevation、host、z-null、floor line | `test_b4b_c2_elevation_claims_score_actual_projection_and_na_overrides`；`test_b4b_c2_elevation_partial_scalars_are_binary_and_floor_lines_use_actual_z`；`test_b4b_c2_multiple_same_family_elevation_sources_fuse_without_id_shortcut`；`test_b4b_c2_host_correct_wrong_and_ambiguous_stay_judge_only` |
| §8.6.1 / §8.7 fusion | `test_b4b_c3_fusion_totality_conflict_and_exact_partial_denominator`；`test_b4b_c3_correct_single_plan_observation_is_not_reference_negative_conflict`；`test_b4b_c3_explicit_product_absence_in_non_gt_source_conflicts_with_positive`；Phase-B twin 两个 named regressions |
| §4.2 | `test_b4b_c4_na_machine_surface_unsupported_combination_and_door` |
| §9.2 / §6.6–6.7 | `test_b4b_c5_policy_conservation_and_top_level_na_or_rejected` |

## 五出口 gate→测试与计数

| Gate | 具名测试 | passed |
|---|---|---:|
| B4B-C1-frame-trust | frame tests（sign ±1、mirror 两态、local-x 两态、true/unknown reject、Va visible shrink、projection→scorer E2E） | 12 |
| B4B-C2-elevation-claims | 四个 elevation/NA/floor-line/multi-source/host tests | 4 |
| B4B-C3-fusion-totality | positive conflict、correct single-plan regression、explicit product-absence item-2 conflict | 3 |
| B4B-C4-na-machine-surface | unsupported product schema + door NA test | 1 |
| B4B-C5-policy-conservation | conservation / all-NA / rejected test | 1 |

Phase C 定向组：**21 passed**。

补充 targeted 自验：

- `python -m pytest tests/test_c2_b4b_*.py -q`：**66 passed**。
- `python -m pytest tests/test_elevation_score.py -q`：**16 passed**。
- `python -m pytest tests/test_c2_b4b_*.py tests/test_elevation_score.py -q`：**82 passed**。
- `git diff --check`：通过。
- production import scan（correction/reading/pipeline → 本批 judge 模块）：无命中。

## 预期行为变化

- typed elevation product geometry 可通过受审 binding 投到 world-along 后进入 v3 claim scorer；同名产品 frame 字段无法影响分母。
- independent positive disagreement，以及“一个 source 有产品 positive、另一 source 的 Va trusted-negative 覆盖该可评分 slice”均产生 conflict fail units。
- 后一种 conflict 只在 product-Va ledger 明确 absence 时发生；缺失 observation 或 reference GT-positive source 均不等于 absence。
- appearance、door 和 z-null sill/head 产机器 NA，不是零分；全核心 criterion NA 时顶层为 not_applicable。
- v3 policy 的 miss/conflict 进入 failing units，并在 conservation/identity 非法时 fail closed。

## 未决·偏离

前轮写作 `none` 是披露偏差：遗漏了 projection→production normalizer/CLI 未接线。该生产接线属于本派工单明确禁止的 Phase D；本轮已补 Phase C pure-function E2E，未越界接入 CLI/normalizer。MINOR-2/3 的 channel-fused elevation geometry 与 inert criteria 均按主控裁决登记为后续 phase/细稿调和债。

## Review ask

none。

## 本批改动文件

- `src/agent/judge/elevation_score.py`
- `src/agent/judge/opening_claim_score.py`
- `src/agent/judge/score_policy.py`
- `tests/test_c2_b4b_phase_b.py`
- `tests/test_c2_b4b_phase_c.py`
- `AI_agent/logs/reviews/execution/2026-07-17_b4b_phaseC_construction_brief.md`
