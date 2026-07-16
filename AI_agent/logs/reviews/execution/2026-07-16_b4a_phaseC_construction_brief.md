# B4a Phase C 执行简报（2026-07-16）

## 改动映射

- `gt_extraction.py`：在既有 `PlanExtractionResult` 之后物化公开 Vg boundary segments、surface scope、plan opening 绑定、整 view 最小代价 elevation assignment、nullable z、north refs，以及 build 末的 profile/validate/canonical round-trip 断言。
- `gt_schema.py`：candidate writer 的受保护目录判断也包含运行时 `DEFAULT_GT_DIR`；仍只接受 candidate、拒绝存在目标与 overwrite。
- `gt_from_dxf.py`：替换旧 v2/默认资产路径脚本为显式 `--dxf --manifest --out` 的 build-only candidate CLI。
- `test_gt_from_dxf.py`：tmp L/U DXF round-trip、hidden segment、plan-only z、nonzero north、tie/no-candidate、writer/CLI 与 canonical-order 回归。

## 稿章节→测试映射

| 章节 | 覆盖测试 |
| --- | --- |
| §5.4/§5.5 | `test_reordered_dxf_entity_iteration_has_identical_canonical_candidate`；`test_canonical_hash_changes_for_coordinates_and_write_round_trips`；writer protected-path/overwrite schema tests |
| §10.5 | `test_plan_only_z_and_u_hidden_depth_are_preserved`；schema segment recompute tests |
| §10.6 | `test_opening_no_candidate_and_tie_fail_closed`；schema opening rejection family |
| §10.7 | `test_build_only_cli_round_trips_l_candidate_and_nonzero_north`；plan-only-z test；schema elevation relevance tests |
| §10.8 | CLI L round-trip nonzero north；plan-only U north-null assertions |
| §13 Phase C | CLI inspect→extract→typed-load/hash round-trip；L/U/hidden/plan-only/north/tie/no-candidate/source-isolation/overwrite targeted tests |
| §14.1–§14.4 | `test_gt_schema.py`、`test_gt_extraction.py`、`test_gt_from_dxf.py`、`test_inspect_dxf.py`、`test_gt_discipline.py` |
| §15.1 | No scoreable/claim-status/denominator/completeness fields or scorer changes; typed geometry-only output checked through schema tests |

## 验收与测试

- §14.5 preflight：passed（现有依赖齐备；未改 lockfile）。
- schema/extraction/from-DXF/inspect：66 passed（有既有 Pydantic serializer warnings）。
- render/overlay/discipline regression：14 passed。
- reading/elevation/batch/harness regression：62 passed。
- `git diff --check`：passed。
- full `pytest -q`：1141 passed, 9 xfailed, 127 warnings（325.70s）。

## 预期行为变化

- v3 candidate 只能由显式 manifest-bound DXF 建构并写至一个全新、非受保护路径；没有 baseline 写入、promotion 或覆盖入口。
- extraction 不再复做 Phase B polygonize/zone；开放型 L/U segment、完全 hidden segment、0..N surface key、plan-only z 与 optional north 均保留为 typed v3 数据。
- elevation 是每 view 全局 assignment；tie、缺候选、跨楼层、z 不一致均 fail closed。

## 未决·偏离

- 细稿要求的“不同**序列化 raw DXF** entity 顺序”与 v3 wire 中必含的 `source.content_sha256` / `generator.manifest_sha256`（Phase B 又要求 manifest source hash 精确匹配 raw bytes）不可同时得到相同 canonical bytes/content hash。现已以实际 DXF loader entity iteration 反序的显式测试锁定 extraction-order independence；未改 raw-source provenance 语义。

## review-ask

- 请裁定上述 raw-DXF-order canonical-hash 冲突：保留 raw source hash（则只能保证几何/提取 order 不敏感），或另定义 canonical DXF source hash / 从 v3 content hash 排除 raw source provenance。当前未猜测性修改 Phase B source-hash 合同。

## 本批改动文件

- `src/agent/judge/gt_extraction.py`
- `src/agent/judge/gt_schema.py`
- `scripts/tool_scripts/gt_from_dxf.py`
- `tests/test_gt_from_dxf.py`
- `tests/test_gt_schema.py`
- `AI_agent/logs/reviews/execution/2026-07-16_b4a_phaseC_construction_brief.md`

## 返工 r1

上批的 source-isolation 覆盖**仅为 writer `--out` 写侧**；`--dxf` 读侧由本轮补齐，前版不再将其表述为已验证覆盖。

| 项 | 修法与新增回归 |
| --- | --- |
| F1 | 将实际消费的 tooling profile 深拷贝后贯穿 build；generator 的记录值由独立快照构造，build 末逐字段 dump 比较。`test_build_profile_snapshot_mismatch_fails_closed` 篡改单字段并断言 `gt_build_profile_tolerances_mismatch`。活体反证：临时把断言改为 `if False`，该测试如预期失败为 `DID NOT RAISE`；随后已恢复真实断言。 |
| F2 | `--dxf` 在读前拒 `DEFAULT_GT_DIR`、`gt_sources`、任意 e2e `case_data`，稳定码 `gt_dxf_source_protected_path`；三类参数化负测。 |
| F3 | CLI 恢复必填 `--config`、`--vg-config`，传给 tooling resolver，不再硬编码。 |
| F4 | 新增 elevation 全局 assignment 多最优 tie→`elevation_opening_assignment_ambiguous`，以及双 view z 不一致→`elevation_opening_vertical_disagreement`。 |
| F5 | 新增篡改 `content_sha256` writer 回归：落盘值等于重算值且不等于篡改值。 |
| F6 | 已清：`_bbox_points` 死分支、inspector 异常路径双读、CLI 与 extractor 双 inspect；无 defer。 |

review-ask 已采纳：保留 raw source hash；实体序不敏感仅在 extractor 层保证。代码注释说明不重序列化 DXF，以免改变 provenance hash。

- r1 GT 定向回归：87 passed，13 warnings。
- r1 full `pytest -q`：1148 passed，9 xfailed，134 warnings（291.59s）。

本轮额外改动文件：

- `src/agent/judge/gt_extraction.py`
- `scripts/tool_scripts/gt_from_dxf.py`
- `tests/test_gt_from_dxf.py`
- `tests/test_gt_schema.py`
- `AI_agent/logs/reviews/execution/2026-07-16_b4a_phaseC_construction_brief.md`
