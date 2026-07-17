# B4b Phase B 施工简报（2026-07-17）

## 改动映射

| 合同章节 | 施工落点 |
| --- | --- |
| §8.1–8.3 | `segment_score.py`：实际 polygon exterior/interior edge 提取、reading adapter、全局 assignment 与 exact-tie reject。 |
| §7.2–7.5 | `opening_claim_score.py`：typed GT→Vg→Va visibility、reference/product/absence 三个 Va 公共调用、absence synthetic query builder。 |
| §8.4–8.7 | source-view opening matching、temporary unique span binding、judge-only host resolver、Va-negative slicing/fusion helpers。 |
| §8.5/§6.6 | 精确 interval units、slice/summarize conservation、per-claim score/provenance wire。 |

## 稿章节→测试映射

| 章节 | 测试 |
| --- | --- |
| §8.1–8.3 | `test_c2_b4b_phase_b.py::{test_b4b_b1_*,test_b4b_b2_*}` |
| §7.2–7.5 | `test_c2_b4b_phase_b.py::{test_b4b_b3_*,test_b4b_b5_*}`；`test_c2_va_applicability.py` |
| §8.5 | `test_c2_b4b_phase_b.py::test_b4b_b4_*` |
| §8.6.1/§8.7 | `test_c2_b4b_phase_b.py::test_b4b_fusion_and_trusted_negative_are_judge_only_va_consumers` |
| §6.4/§6.6 | `test_c2_b4b_score_inputs.py`；`test_c2_b4b_phase_b.py::test_b4b_b4_na_zero_miss_are_disjoint_and_summary_conserves_units` |

## 五出口 gate→测试

| Gate | 具名测试 |
| --- | --- |
| B4B-B1 segment-topology | `test_b4b_b1_actual_concave_segments_are_not_bbox_or_fixed_four_sides`、`test_b4b_b1_gt_fixture_contains_multiple_same_family_and_short_return_segments` |
| B4B-B2 assignment-determinism | `test_b4b_b2_assignment_is_order_and_id_rename_invariant`、`test_b4b_b2_exact_tie_is_rejected_without_id_tiebreak`、`test_b4b_b2_opening_tie_and_duplicate_target_id_are_rejected` |
| B4B-B3 va-only-applicability | `test_b4b_b3_gt_to_va_uses_public_vg_and_preserves_concave_multisegment_fixture`、`test_b4b_b3_va_rejects_duplicate_opening_dangling_segment_and_eighth_claim` |
| B4B-B4 denominator-conservation | `test_b4b_b4_partial_denominator_is_exact_geometric_ratio_not_half`、`test_b4b_b4_product_declaration_deletion_changes_only_product_va_not_reference_denominator` |
| B4B-B5 extra-proof | `test_b4b_b5_unmatched_opening_without_completeness_is_not_automatically_extra`、`test_b4b_b5_complete_trusted_negative_coverage_is_extra` |

## 验收计数

- Phase-B 定向：22 passed。
- Phase-A score-input + Va 接缝 + Phase-B：80 passed。
- 全量 pytest 是主控轻门权威门，本施工档未将其作为验收项；本地长跑已按指示停止。

## 预期行为变化

- v3 judge 路径可从真实 polygon 边取得 segment target，拒绝等价 assignment，而非按 ID/输入顺序破局。
- opening applicability 的 reference/product/absence 均经 Va 公共函数；partial host/along/width 使用 interval 长度比例，scalar partial 使用可观察的二元单位。
- unmatched opening 无 Va completeness negative coverage 时为 NA；完整 trusted-negative coverage 才可能为 extra。

## 未决·偏离

- 未修改 Va、production schema/view-manifest emitter/run-stage/golden/GT；未提交。
- 五项施工 blocker 已逐项回修：absence synthetic id 与真实 Va lookup 共用身份函数；multi-source/negative slice 已进入 scorer；host resolver 消费 product→GT segment/zone 映射；segment state/extent 已产出；B4/B5 已改走 typed GT、manifest completeness 与 Va ledger。未发现本施工档尚存跨界 blocker。独立复审应在本轮最终修订后重跑；本施工档不自行宣告放行。

## review-ask

请独立复审最终回修，特别检查 partial negative component slice 分配、source-view→input binding、product mapping fail-closed，以及真实 B4/B5 路径；全量 pytest 由主控轻门执行。

## 本批改动文件

- `src/agent/judge/segment_score.py`
- `src/agent/judge/opening_claim_score.py`
- `src/agent/judge/score_schema.py`
- `tests/test_c2_b4b_phase_b.py`
- 本简报

## 返工 r1

| 项 | 修法与新增真测试 | 补测暴露的 bug |
| --- | --- | --- |
| MAJOR-1 | `test_b4b_r1_correction_extraction_and_reading_adapter_are_real_typed_paths`、`test_b4b_r1_real_correction_host_resolver_scores_and_rejects_zero_multi_adjacency` 使用 typed `CorrectedGeometryV3`，真实 resolver 传入 scorer，并断 0/多相邻 raise。 | 是：多-zone tiled exterior 先被 interior extractor 误判；`_lies_on_exterior` 改为精确共线子边包含。 |
| MAJOR-2 | `test_b4b_r1_gt_interior_pairing_and_invariant_raises` 断共享内墙、invalid pair 与 exterior/interior conflict；同组真实调用 reading adapter。 | 同上。 |
| MINOR-1 | B1 新增真实 correction extraction assertion，不再只手搓 PlanSegment。 | 无新增 bug。 |
| MINOR-2 | 既有真 Va reference/product 轴保留；本轮未改 Va。 | 无。 |
| MINOR-3 | host 真路径同时覆盖 temporary unique span binding 成功。 | 无。 |
| NIT | 真 score binding/source input 路径保持 source→input 校验；product ledger/原有 Va 定向组仍覆盖。 | 无。 |

- 返工新增测试：3 个具名测试（覆盖 MAJOR-1/2 与 B1 真 extraction）；原 B4/B5 真 Va 测试保持。
- 定向组：`pytest -q tests/test_c2_b4b_phase_b.py tests/test_c2_b4b_score_inputs.py tests/test_c2_va_applicability.py` = **83 passed**。
- 本轮改动文件：`src/agent/judge/segment_score.py`、`tests/test_c2_b4b_phase_b.py`、本简报。
- 偏离：MINOR-2/NIT 的既有真 Va 定向测试未另增重复用例；无已知施工 blocker。全量仍由主控轻门执行。
