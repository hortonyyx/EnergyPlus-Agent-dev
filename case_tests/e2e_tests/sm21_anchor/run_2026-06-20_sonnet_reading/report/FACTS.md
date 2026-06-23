# sm21_anchor / run_2026-06-20_sonnet_reading FACTS (2026-06-21, orchestrator=opus-4.8)

**结论**: ❌ STOPPED (human_redraw_required@1_correction) / EP 未跑

**模型**: {'intake_correction': 'deepseek-v4-pro', 'default': 'deepseek-v4-pro'}

## 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 2_modelling | 0 | 0 | 1 | 0 |
| 3_split_pairing | 0 | 0 | 1 | 0 |
| 4_mep | 0 | 0 | 1 | 0 |
| 5_intakeoutput | 0 | 0 | 1 | 0 |
| 0_reading | 52 | 0 | 0 | 8 |
| 1_correction | 6 | 1 | 0 | 1 |

## 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | judge_pass | 1 |
| 1_correction | human_redraw_required | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 1, '1_correction': 1}

**judge② verdicts**: 2 条（1 条 blocking；见各 attempts/NNN/judge.json）

## run_state

- status: `root_stopped`
- root_stop: `human_redraw_required@1_correction`
- root message: judge blocked, root='0_reading' (manual) → human re-trace required
- missing_expected: ['2_modelling', '3_split_pairing', '4_mep', '5_intakeoutput']

## ⛔ blocking
- [2_modelling::2_modelling.build] required artifact missing: 2_modelling/building_geometry.json
- [3_split_pairing::3_split_pairing.build] required artifact missing: 3_split_pairing/geometry_specs.md
- [4_mep::4_mep.build] required artifact missing: 4_mep/mep_output.json
- [5_intakeoutput::5_intakeoutput.build] required artifact missing: 5_intakeoutput/intake_output.json

## ⚠️ flags（不阻塞、供归因）
- [1_correction::correction.zone_count_tripwire] cell count 16 != testdata thermal_zones 14

## 校正审计（看错↔改错归因）

### conflicts[]
- {"id": "conf_001", "conflict_type": "facade_plan_mismatch", "claim_type": "numeric", "candidates": [{"value": [1.44, 3.44], "source_ids": ["D24_1f_view"], "evidence_grade": "transcribed_dimension", "confidence": "medium"}, {"value": [3.44, 4.64], "source_ids": ["D24_South_view", "S7_South_view"], "evidence_grade": "transcribed_dimension", "confidence": "high"}], "reason_unresolved": "Plan bottom chain D24=2000mm at [1.44,3.44] vs South elevation D24=1200mm at [3.44,4.64]. Two dimension chains give different window width and position for same facade. Elevation chosen as authoritative (shows actual window rectangle with inner z-chain).", "fallback_action": "Adopted elevation chain (1200mm at [3.44,4.64]); plan stroke S15 at [0.90,2.90] treated as inaccurate tracing offset. Logged as corr_009."}
- {"id": "conf_002", "conflict_type": "stroke_vs_dimension", "claim_type": "numeric", "candidates": [{"value": 7.56, "source_ids": ["S10_1f_view"], "evidence_grade": "estimated_stroke", "confidence": "low"}, {"value": 6.3, "source_ids": ["D28_1f_view", "D26_South_view"], "evidence_grade": "transcribed_dimension", "confidence": "high"}], "reason_unresolved": "Reading-stage interior wall S10 at x=7.56 (estimated from cumulative sum) would split south facade window [6.30,8.70] across two rooms. Dimension chain gives window left edge at 6.30. Topology requirement (each window in one room) forces wall to x=6.30.", "fallback_action": "Moved interior wall to x=6.30 (corr_007)."}
- {"id": "conf_003", "conflict_type": "checksum_failure", "claim_type": "numeric", "candidates": [{"value": "Σ=15344mm", "source_ids": ["D19_2f_view", "D20_2f_view", "D21_2f_view", "D22_2f_view", "D23_2f_view", "D24_2f_view", "D25_2f_view", "D26_2f_view", "D27_2f_view", "D28_2f_view", "D29_2f_view", "D30_2f_view"], "evidence_grade": "transcribed_dimension", "confidence": "medium"}, {"value": "15000", "source_ids": ["D1_2f_view", "D30_2f_view"], "evidence_grade": "direct_measurement", "confidence": "high"}], "reason_unresolved": "F2 bottom dimension chain segments do not sum to outer total 15000mm. Individual segment values from reading stage contain internal inconsistency (e.g. D24 2190 from 5.51→7.50 but 5.51+2.19=7.70). Reading-stage transcription error suspected.", "fallback_action": "Used reading-stage wall positions (S8=3.75, S9=5.51, S10=7.50, S11=11.25) as best available topology evidence despite chain inconsistency; noted in corr_011."}
- {"id": "conf_004", "conflict_type": "reference_or_identity_ambiguity", "claim_type": "topology_identity", "candidates": [{"value": "3 interior walls south zone F1", "source_ids": ["S9_1f_view", "S10_1f_view", "S11_1f_view"], "evidence_grade": "estimated_stroke", "confidence": "low"}, {"value": "2 interior walls south zone F1", "source_ids": ["D12_D16_constraint_7_zones"], "evidence_grade": "inferred_topology", "confidence": "medium"}], "reason_unresolved": "Reading stage observed 3 interior walls in F1 south zone creating 4 bays, but metadata says 7 thermal zones total per floor (3N+3S+1 corridor=7, implying 3 south rooms not 4). Leftmost bay (x=0.10-3.44) treated as entrance/lobby cell; may merge with corridor in downstream zoning.", "fallback_action": "Emitted all 4 cells; downstream zonification may merge cell_1_SW with cell_1_C."}
- {"id": "conf_005", "conflict_type": "semantic_size_prior", "claim_type": "semantic", "candidates": [{"value": "cell_2_S2 width=1.76m", "source_ids": ["S8_2f_view", "S9_2f_view"], "evidence_grade": "estimated_stroke", "confidence": "medium"}, {"value": "office min width ~2.4m", "source_ids": ["office_area_pp_A4"], "evidence_grade": "prior", "confidence": "low"}], "reason_unresolved": "F2 cell_2_S2 (x=[3.75,5.51], width=1.76m) is narrow relative to typical office. May be workstation bay or service space rather than full office. Kept as-is; label may change in downstream zoning.", "fallback_action": "Kept cell with role='office'; prior not applied. Width is plausible as a narrow workstation bay in open-plan configuration."}

### unsupported[]
- {"id": "unsup_001", "reason": "West facade F1 entrance door (double-door at local x=[3.40,4.60], y≈[0.00,2.80]) is a door, not a window. No window geometry to emit for west facade F1. The door opening is noted but not modeled as a window per pen library (door → not drawn). Downstream must handle this as a zero-window west F1 wall surface with a door sub-surface if needed.", "regime_assumption_violated": "Door in elevation — correction stage does not model doors; door-healing already done in reading stage for plan walls. Elevation door presence noted."}
- {"id": "unsup_002", "reason": "South facade F1 entrance door (door at x≈[0.40,1.04], y≈[0.00,2.10]) visible in South elevation. Similar to unsup_001: door, not window. South facade F1 leftmost bay (x=0-3.44) contains entrance door rather than window.", "regime_assumption_violated": "Door in elevation — same as unsup_001."}
- {"id": "unsup_003", "reason": "F2 bottom dimension chain checksum failure (Σ≠15000). Individual segment transcription errors in reading stage prevent clean dimension-chain closure. Cell positions for F2 south zone rely on reading-stage stroke estimates rather than closed dimension chain.", "regime_assumption_violated": "Dimension-chain closure required but segments do not sum to outer total within DIMCHAIN_CLOSE_TOL. Cannot auto-close without guessing which segments are wrong."}

### corrections[]（显示 20/41，cap=20）
- {"id": "corr_001", "rule_id": "centerline_shift_exterior_south", "source_ids": ["S1_1f_view"], "original_value": 0.0, "resolved_value": 0.1, "delta": 0.1, "changes_topology": false}
- {"id": "corr_002", "rule_id": "centerline_shift_exterior_north", "source_ids": ["S2_1f_view"], "original_value": 8.0, "resolved_value": 7.9, "delta": -0.1, "changes_topology": false}
- {"id": "corr_003", "rule_id": "centerline_shift_exterior_west", "source_ids": ["S3_1f_view"], "original_value": 0.0, "resolved_value": 0.1, "delta": 0.1, "changes_topology": false}
- {"id": "corr_004", "rule_id": "centerline_shift_exterior_east", "source_ids": ["S4_1f_view"], "original_value": 15.0, "resolved_value": 14.9, "delta": -0.1, "changes_topology": false}
- {"id": "corr_005", "rule_id": "centerline_shift_interior_corridor_south", "source_ids": ["S6_1f_view", "D13_1f_view"], "original_value": 3.0, "resolved_value": 3.125, "delta": 0.125, "changes_topology": false}
- {"id": "corr_006", "rule_id": "centerline_shift_interior_corridor_north", "source_ids": ["S5_1f_view", "D15_1f_view"], "original_value": 5.0, "resolved_value": 4.875, "delta": -0.125, "changes_topology": false}
- {"id": "corr_007", "rule_id": "interior_wall_x_S10_adjusted", "source_ids": ["S10_1f_view", "D28_1f_view", "S8_South_view"], "original_value": 7.56, "resolved_value": 6.3, "delta": -1.26, "changes_topology": true}
- {"id": "corr_008", "rule_id": "interior_wall_x_S11_adjusted", "source_ids": ["S11_1f_view", "D31_1f_view", "S9_South_view"], "original_value": 11.56, "resolved_value": 11.36, "delta": -0.2, "changes_topology": true}
- {"id": "corr_009", "rule_id": "south_facade_window_resolution_plan_vs_elevation", "source_ids": ["D24_1f_view", "D24_South_view", "S7_South_view", "S15_1f_view"], "original_value": [1.44, 3.44], "resolved_value": [3.44, 4.64], "delta": null, "changes_topology": false}
- {"id": "corr_010", "rule_id": "snap_window_to_elevation_chain", "source_ids": ["S7_South_view", "D20_South_view", "D21_South_view", "D22_South_view"], "original_value": [3.44, 4.64], "resolved_value": [3.44, 4.64], "delta": 0.0, "changes_topology": false}
- {"id": "corr_011", "rule_id": "dimchain_closure_F2_bottom", "source_ids": ["D19_2f_view", "D20_2f_view", "D21_2f_view", "D22_2f_view", "D23_2f_view", "D24_2f_view", "D25_2f_view", "D26_2f_view", "D27_2f_view", "D28_2f_view", "D29_2f_view", "D30_2f_view"], "original_value": null, "resolved_value": null, "delta": null, "changes_topology": false}
- {"id": "corr_012", "rule_id": "z_stack_reconciliation", "source_ids": ["D5_East_view", "D6_East_view", "D7_East_view", "D11_North_view", "D12_North_view", "D13_North_view"], "original_value": null, "resolved_value": null, "delta": 0.0, "changes_topology": false}
- {"id": "corr_013", "rule_id": "north_facade_F1_window_world_transform", "source_ids": ["S5_North_view", "D18_North_view", "D19_North_view"], "original_value": [1.24, 3.64], "resolved_value": [1.24, 3.64], "delta": 0.0, "changes_topology": false}
- {"id": "corr_014", "rule_id": "F2_south_wall_closure", "source_ids": ["S9_2f_view", "D22_2f_view", "D23_2f_view"], "original_value": 5.51, "resolved_value": 5.51, "delta": 0.0, "changes_topology": false}
- {"rule_id": "deterministic_core.snap", "target": "cell_1_SW.x[1]", "original_value": 3.44, "resolved_value": 3.45, "delta": 0.01}
- {"rule_id": "deterministic_core.snap", "target": "cell_1_SW.y[1]", "original_value": 3.125, "resolved_value": 3.1, "delta": -0.025}
- {"rule_id": "deterministic_core.snap", "target": "cell_1_S1.x[0]", "original_value": 3.44, "resolved_value": 3.45, "delta": 0.01}
- {"rule_id": "deterministic_core.snap", "target": "cell_1_S1.y[1]", "original_value": 3.125, "resolved_value": 3.1, "delta": -0.025}
- {"rule_id": "deterministic_core.snap", "target": "cell_1_S2.x[1]", "original_value": 11.36, "resolved_value": 11.3, "delta": -0.06}
- {"rule_id": "deterministic_core.snap", "target": "cell_1_S2.y[1]", "original_value": 3.125, "resolved_value": 3.1, "delta": -0.025}

### count summary
- sidecar: `1_correction/corrections.json` (ok)
- counts: corrections=41, conflicts=5, unsupported=3
- by_rule_id: {"F2_south_wall_closure": 1, "centerline_shift_exterior_east": 1, "centerline_shift_exterior_north": 1, "centerline_shift_exterior_south": 1, "centerline_shift_exterior_west": 1, "centerline_shift_interior_corridor_north": 1, "centerline_shift_interior_corridor_south": 1, "deterministic_core.snap": 26, "deterministic_core.window": 1, "dimchain_closure_F2_bottom": 1, "interior_wall_x_S10_adjusted": 1, "interior_wall_x_S11_adjusted": 1, "north_facade_F1_window_world_transform": 1, "snap_window_to_elevation_chain": 1, "south_facade_window_resolution_plan_vs_elevation": 1, "z_stack_reconciliation": 1}
- by_stage: {"A1": 7, "A2-apply": 3, "A3-resolve": 4, "core": 27}

## report/eyeball assets

### copied
- `report/eyeball/1_correction_zones.png` <= `1_correction/zones.png` (correction_zones)
- `report/eyeball/1_correction_elev.png` <= `1_correction/elev.png` (correction_elev)
- `report/eyeball/0_reading_1f_view_render.png` <= `0_reading/1f_view_render.png` (reading_render)
- `report/eyeball/0_reading_2f_view_render.png` <= `0_reading/2f_view_render.png` (reading_render)
- `report/eyeball/0_reading_East_view_render.png` <= `0_reading/East_view_render.png` (reading_render)
- `report/eyeball/0_reading_North_view_render.png` <= `0_reading/North_view_render.png` (reading_render)
- `report/eyeball/0_reading_South_view_render.png` <= `0_reading/South_view_render.png` (reading_render)
- `report/eyeball/0_reading_West_view_render.png` <= `0_reading/West_view_render.png` (reading_render)
- `report/eyeball/case_data_1f_view.png` <= `../case_data/1f_view.png` (case_data_view)
- `report/eyeball/case_data_2f_view.png` <= `../case_data/2f_view.png` (case_data_view)
- `report/eyeball/case_data_East_view.png` <= `../case_data/East_view.png` (case_data_view)
- `report/eyeball/case_data_North_view.png` <= `../case_data/North_view.png` (case_data_view)
- `report/eyeball/case_data_South_view.png` <= `../case_data/South_view.png` (case_data_view)
- `report/eyeball/case_data_West_view.png` <= `../case_data/West_view.png` (case_data_view)

### 3D viewer
- unavailable: missing 2_modelling/building_geometry.json

## 🔍 请你肉视检验（确定性 + judge 都盖不死的感知项）
1. 2D 肉检 `report/eyeball/1_correction_zones.png`（from `1_correction/zones.png` / correction_zones）
2. 2D 肉检 `report/eyeball/1_correction_elev.png`（from `1_correction/elev.png` / correction_elev）
3. 2D 肉检 `report/eyeball/0_reading_1f_view_render.png`（from `0_reading/1f_view_render.png` / reading_render）
4. 2D 肉检 `report/eyeball/0_reading_2f_view_render.png`（from `0_reading/2f_view_render.png` / reading_render）
5. 2D 肉检 `report/eyeball/0_reading_East_view_render.png`（from `0_reading/East_view_render.png` / reading_render）
6. 2D 肉检 `report/eyeball/0_reading_North_view_render.png`（from `0_reading/North_view_render.png` / reading_render）
7. 2D 肉检 `report/eyeball/0_reading_South_view_render.png`（from `0_reading/South_view_render.png` / reading_render）
8. 2D 肉检 `report/eyeball/0_reading_West_view_render.png`（from `0_reading/West_view_render.png` / reading_render）
9. 2D 肉检 `report/eyeball/case_data_1f_view.png`（from `../case_data/1f_view.png` / case_data_view）
10. 2D 肉检 `report/eyeball/case_data_2f_view.png`（from `../case_data/2f_view.png` / case_data_view）
11. 2D 肉检 `report/eyeball/case_data_East_view.png`（from `../case_data/East_view.png` / case_data_view）
12. 2D 肉检 `report/eyeball/case_data_North_view.png`（from `../case_data/North_view.png` / case_data_view）
13. 2D 肉检 `report/eyeball/case_data_South_view.png`（from `../case_data/South_view.png` / case_data_view）
14. 2D 肉检 `report/eyeball/case_data_West_view.png`（from `../case_data/West_view.png` / case_data_view）
15. 3D 几何 viewer unavailable: missing 2_modelling/building_geometry.json
16. flag [1_correction::correction.zone_count_tripwire] —— cell count 16 != testdata thermal_zones 14（对应渲染件人工核一眼）
17. audit-derived [corrections_summary] —— `corrections.json` 有 5 conflicts / 3 unsupported，人核看错↔改错归因

## evidence_index
- `E:gate:1_correction:correction.zone_count_tripwire` (gate; source `1_correction`) — cell count 16 != testdata thermal_zones 14
- `E:gate:2_modelling:2_modelling.build` (gate; source `2_modelling`) — required artifact missing: 2_modelling/building_geometry.json
- `E:gate:3_split_pairing:3_split_pairing.build` (gate; source `3_split_pairing`) — required artifact missing: 3_split_pairing/geometry_specs.md
- `E:gate:4_mep:4_mep.build` (gate; source `4_mep`) — required artifact missing: 4_mep/mep_output.json
- `E:gate:5_intakeoutput:5_intakeoutput.build` (gate; source `5_intakeoutput`) — required artifact missing: 5_intakeoutput/intake_output.json
- `E:judge:0_reading:001:c1` (judge; source `0_reading/attempts/001/judge.json`) — missed real element
- `E:judge:0_reading:001:c2` (judge; source `0_reading/attempts/001/judge.json`) — clutter traced as structure
- `E:judge:0_reading:001:c3` (judge; source `0_reading/attempts/001/judge.json`) — pen misclassified
- `E:judge:0_reading:001:c4` (judge; source `0_reading/attempts/001/judge.json`) — number copied wrong
- `E:judge:0_reading:001:c5` (judge; source `0_reading/attempts/001/judge.json`) — image-local orientation self-consistent
- `E:judge:0_reading:001:c6` (judge; source `0_reading/attempts/001/judge.json`) — door healing wrong
- `E:judge:0_reading:001:c7` (judge; source `0_reading/attempts/001/judge.json`) — whole-region missing / misplaced
- `E:judge:1_correction:001:c1` (judge; source `1_correction/attempts/001/judge.json`) — zonification fidelity
- `E:judge:1_correction:001:c2` (judge; source `1_correction/attempts/001/judge.json`) — cross-floor consistency
- `E:judge:1_correction:001:c3` (judge; source `1_correction/attempts/001/judge.json`) — window position fidelity
- `E:judge:1_correction:001:c4` (judge; source `1_correction/attempts/001/judge.json`) — count vs reference
- `E:judge:1_correction:001:c5` (judge; source `1_correction/attempts/001/judge.json`) — overall redraw
- `E:corr:corrections:corr_001` (correction; source `1_correction/corrections.json`) — corr_001
- `E:corr:corrections:corr_002` (correction; source `1_correction/corrections.json`) — corr_002
- `E:corr:corrections:corr_003` (correction; source `1_correction/corrections.json`) — corr_003
- `E:corr:corrections:corr_004` (correction; source `1_correction/corrections.json`) — corr_004
- `E:corr:corrections:corr_005` (correction; source `1_correction/corrections.json`) — corr_005
- `E:corr:corrections:corr_006` (correction; source `1_correction/corrections.json`) — corr_006
- `E:corr:corrections:corr_007` (correction; source `1_correction/corrections.json`) — corr_007
- `E:corr:corrections:corr_008` (correction; source `1_correction/corrections.json`) — corr_008
- `E:corr:corrections:corr_009` (correction; source `1_correction/corrections.json`) — corr_009
- `E:corr:corrections:corr_010` (correction; source `1_correction/corrections.json`) — corr_010
- `E:corr:corrections:corr_011` (correction; source `1_correction/corrections.json`) — corr_011
- `E:corr:corrections:corr_012` (correction; source `1_correction/corrections.json`) — corr_012
- `E:corr:corrections:corr_013` (correction; source `1_correction/corrections.json`) — corr_013
- `E:corr:corrections:corr_014` (correction; source `1_correction/corrections.json`) — corr_014
- `E:corr:corrections:r15` (correction; source `1_correction/corrections.json`) — row 15
- `E:corr:corrections:r16` (correction; source `1_correction/corrections.json`) — row 16
- `E:corr:corrections:r17` (correction; source `1_correction/corrections.json`) — row 17
- `E:corr:corrections:r18` (correction; source `1_correction/corrections.json`) — row 18
- `E:corr:corrections:r19` (correction; source `1_correction/corrections.json`) — row 19
- `E:corr:corrections:r20` (correction; source `1_correction/corrections.json`) — row 20
- `E:corr:corrections:r21` (correction; source `1_correction/corrections.json`) — row 21
- `E:corr:corrections:r22` (correction; source `1_correction/corrections.json`) — row 22
- `E:corr:corrections:r23` (correction; source `1_correction/corrections.json`) — row 23
- `E:corr:corrections:r24` (correction; source `1_correction/corrections.json`) — row 24
- `E:corr:corrections:r25` (correction; source `1_correction/corrections.json`) — row 25
- `E:corr:corrections:r26` (correction; source `1_correction/corrections.json`) — row 26
- `E:corr:corrections:r27` (correction; source `1_correction/corrections.json`) — row 27
- `E:corr:corrections:r28` (correction; source `1_correction/corrections.json`) — row 28
- `E:corr:corrections:r29` (correction; source `1_correction/corrections.json`) — row 29
- `E:corr:corrections:r30` (correction; source `1_correction/corrections.json`) — row 30
- `E:corr:corrections:r31` (correction; source `1_correction/corrections.json`) — row 31
- `E:corr:corrections:r32` (correction; source `1_correction/corrections.json`) — row 32
- `E:corr:corrections:r33` (correction; source `1_correction/corrections.json`) — row 33
- `E:corr:corrections:r34` (correction; source `1_correction/corrections.json`) — row 34
- `E:corr:corrections:r35` (correction; source `1_correction/corrections.json`) — row 35
- `E:corr:corrections:r36` (correction; source `1_correction/corrections.json`) — row 36
- `E:corr:corrections:r37` (correction; source `1_correction/corrections.json`) — row 37
- `E:corr:corrections:r38` (correction; source `1_correction/corrections.json`) — row 38
- `E:corr:corrections:r39` (correction; source `1_correction/corrections.json`) — row 39
- `E:corr:corrections:r40` (correction; source `1_correction/corrections.json`) — row 40
- `E:corr:corrections:r41` (correction; source `1_correction/corrections.json`) — row 41
- `E:corr:conflicts:conf_001` (correction; source `1_correction/corrections.json`) — conf_001
- `E:corr:conflicts:conf_002` (correction; source `1_correction/corrections.json`) — conf_002
- `E:corr:conflicts:conf_003` (correction; source `1_correction/corrections.json`) — conf_003
- `E:corr:conflicts:conf_004` (correction; source `1_correction/corrections.json`) — conf_004
- `E:corr:conflicts:conf_005` (correction; source `1_correction/corrections.json`) — conf_005
- `E:corr:unsupported:unsup_001` (correction; source `1_correction/corrections.json`) — unsup_001
- `E:corr:unsupported:unsup_002` (correction; source `1_correction/corrections.json`) — unsup_002
- `E:corr:unsupported:unsup_003` (correction; source `1_correction/corrections.json`) — unsup_003
- `E:stop:human_redraw_required@1_correction` (stop; source `orchestration_state.json`) — orchestration_state.json
- `E:ep:result` (ep; source `EP/EP_run/eplusout.end`) — EP/EP_run/eplusout.end
- `E:geom:digest` (geometry; source `2_modelling/building_geometry.json`) — 2_modelling/building_geometry.json
- `E:eyeball:1_correction_zones.png` (eyeball; source `report/eyeball/1_correction_zones.png`) — report/eyeball/1_correction_zones.png
- `E:eyeball:1_correction_elev.png` (eyeball; source `report/eyeball/1_correction_elev.png`) — report/eyeball/1_correction_elev.png
- `E:eyeball:0_reading_1f_view_render.png` (eyeball; source `report/eyeball/0_reading_1f_view_render.png`) — report/eyeball/0_reading_1f_view_render.png
- `E:eyeball:0_reading_2f_view_render.png` (eyeball; source `report/eyeball/0_reading_2f_view_render.png`) — report/eyeball/0_reading_2f_view_render.png
- `E:eyeball:0_reading_East_view_render.png` (eyeball; source `report/eyeball/0_reading_East_view_render.png`) — report/eyeball/0_reading_East_view_render.png
- `E:eyeball:0_reading_North_view_render.png` (eyeball; source `report/eyeball/0_reading_North_view_render.png`) — report/eyeball/0_reading_North_view_render.png
- `E:eyeball:0_reading_South_view_render.png` (eyeball; source `report/eyeball/0_reading_South_view_render.png`) — report/eyeball/0_reading_South_view_render.png
- `E:eyeball:0_reading_West_view_render.png` (eyeball; source `report/eyeball/0_reading_West_view_render.png`) — report/eyeball/0_reading_West_view_render.png
- `E:eyeball:case_data_1f_view.png` (eyeball; source `report/eyeball/case_data_1f_view.png`) — report/eyeball/case_data_1f_view.png
- `E:eyeball:case_data_2f_view.png` (eyeball; source `report/eyeball/case_data_2f_view.png`) — report/eyeball/case_data_2f_view.png
- `E:eyeball:case_data_East_view.png` (eyeball; source `report/eyeball/case_data_East_view.png`) — report/eyeball/case_data_East_view.png
- `E:eyeball:case_data_North_view.png` (eyeball; source `report/eyeball/case_data_North_view.png`) — report/eyeball/case_data_North_view.png
- `E:eyeball:case_data_South_view.png` (eyeball; source `report/eyeball/case_data_South_view.png`) — report/eyeball/case_data_South_view.png
- `E:eyeball:case_data_West_view.png` (eyeball; source `report/eyeball/case_data_West_view.png`) — report/eyeball/case_data_West_view.png

_附: baseline.json / 各 <stage>_checks.json / geometry_digest=None_
