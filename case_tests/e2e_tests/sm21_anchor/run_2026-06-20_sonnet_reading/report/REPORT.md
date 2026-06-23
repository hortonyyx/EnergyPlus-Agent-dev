<!-- GEN:START model_config -->
# sm21_anchor / run_2026-06-20_sonnet_reading REPORT

## 本次模型配置

- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-06-21`
- orchestrator: `opus-4.8`
- 自动状态: `root_stopped: human_redraw_required@1_correction`
- default: `deepseek-v4-pro`
- intake_correction: `deepseek-v4-pro`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ❌ STOPPED (human_redraw_required@1_correction) / EP 未跑

**数字权威**: [../_run/baseline.json](../_run/baseline.json) + 本 REPORT 的 GEN 区；AGENT 区为主控叙事/建议，citation linter 只约束建议证据 id。

### 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 2_modelling | 0 | 0 | 1 | 0 |
| 3_split_pairing | 0 | 0 | 1 | 0 |
| 4_mep | 0 | 0 | 1 | 0 |
| 5_intakeoutput | 0 | 0 | 1 | 0 |
| 0_reading | 58 | 0 | 0 | 14 |
| 1_correction | 6 | 1 | 0 | 1 |

### 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | judge_pass | 1 |
| 1_correction | human_redraw_required | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 1, '1_correction': 1}

**judge② verdicts**: 2 条（1 条 blocking；见各 attempts/NNN/judge.json）

### run_state

- status: `root_stopped`
- root_stop: `human_redraw_required@1_correction`
- root message: judge blocked, root='0_reading' (manual) → human re-trace required
- missing_expected: ['2_modelling', '3_split_pairing', '4_mep', '5_intakeoutput']

### blocking
- [2_modelling::2_modelling.build] required artifact missing: 2_modelling/building_geometry.json
- [3_split_pairing::3_split_pairing.build] required artifact missing: 3_split_pairing/geometry_specs.md
- [4_mep::4_mep.build] required artifact missing: 4_mep/mep_output.json
- [5_intakeoutput::5_intakeoutput.build] required artifact missing: 5_intakeoutput/intake_output.json

### flags（不阻塞、供归因）
- [1_correction::correction.zone_count_tripwire] cell count 16 != testdata thermal_zones 14

### 连带缺失下游件

- `2_modelling`: required artifact missing: 2_modelling/building_geometry.json
- `3_split_pairing`: required artifact missing: 3_split_pairing/geometry_specs.md
- `4_mep`: required artifact missing: 4_mep/mep_output.json
- `5_intakeoutput`: required artifact missing: 5_intakeoutput/intake_output.json

### 校正审计摘要

- sidecar: `1_correction/corrections.json` (ok)
- counts: corrections=41, conflicts=5, unsupported=3
- by_rule_id: {"F2_south_wall_closure": 1, "centerline_shift_exterior_east": 1, "centerline_shift_exterior_north": 1, "centerline_shift_exterior_south": 1, "centerline_shift_exterior_west": 1, "centerline_shift_interior_corridor_north": 1, "centerline_shift_interior_corridor_south": 1, "deterministic_core.snap": 26, "deterministic_core.window": 1, "dimchain_closure_F2_bottom": 1, "interior_wall_x_S10_adjusted": 1, "interior_wall_x_S11_adjusted": 1, "north_facade_F1_window_world_transform": 1, "snap_window_to_elevation_chain": 1, "south_facade_window_resolution_plan_vs_elevation": 1, "z_stack_reconciliation": 1}
- by_stage: {"A1": 7, "A2-apply": 3, "A3-resolve": 4, "core": 27}
<!-- GEN:END facts_card -->
<!-- AGENT:START conclusion -->
## 一句话结论

- 自动状态: `root_stopped: human_redraw_required@1_correction`
<!-- AGENT-FILL: 用一句话写 pass/blocked + 本 run 最重要的一件事。 -->
<!-- AGENT:END conclusion -->
<!-- AGENT:START focus -->
## 本轮侧重点

<!-- AGENT-FILL: 说明这轮在测什么、为何重要。 -->
<!-- AGENT:END focus -->
<!-- AGENT:START diagnosis -->
## 错在哪儿 + 归因

<!-- AGENT-FILL: 用 evidence_index 把 gate/judge/correction/肉检事实串成因果链。 -->
<!-- AGENT:END diagnosis -->
<!-- AGENT:START recommendations -->
## 建议


### 机制问题

本 run 无可证据支持的建议

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

本 run 无可证据支持的建议

### 修法

本 run 无可证据支持的建议
<!-- AGENT:END recommendations -->
<!-- GEN:START eyeball_index -->
## 肉视检验索引

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

### report/eyeball
- [1_correction_zones.png](eyeball/1_correction_zones.png) — correction_zones from `1_correction/zones.png`
- [1_correction_elev.png](eyeball/1_correction_elev.png) — correction_elev from `1_correction/elev.png`
- [0_reading_1f_view_render.png](eyeball/0_reading_1f_view_render.png) — reading_render from `0_reading/1f_view_render.png`
- [0_reading_2f_view_render.png](eyeball/0_reading_2f_view_render.png) — reading_render from `0_reading/2f_view_render.png`
- [0_reading_East_view_render.png](eyeball/0_reading_East_view_render.png) — reading_render from `0_reading/East_view_render.png`
- [0_reading_North_view_render.png](eyeball/0_reading_North_view_render.png) — reading_render from `0_reading/North_view_render.png`
- [0_reading_South_view_render.png](eyeball/0_reading_South_view_render.png) — reading_render from `0_reading/South_view_render.png`
- [0_reading_West_view_render.png](eyeball/0_reading_West_view_render.png) — reading_render from `0_reading/West_view_render.png`
- [case_data_1f_view.png](eyeball/case_data_1f_view.png) — case_data_view from `../case_data/1f_view.png`
- [case_data_2f_view.png](eyeball/case_data_2f_view.png) — case_data_view from `../case_data/2f_view.png`
- [case_data_East_view.png](eyeball/case_data_East_view.png) — case_data_view from `../case_data/East_view.png`
- [case_data_North_view.png](eyeball/case_data_North_view.png) — case_data_view from `../case_data/North_view.png`
- [case_data_South_view.png](eyeball/case_data_South_view.png) — case_data_view from `../case_data/South_view.png`
- [case_data_West_view.png](eyeball/case_data_West_view.png) — case_data_view from `../case_data/West_view.png`

### manual_review viewer
- 3D geometry viewer unavailable — missing 2_modelling/building_geometry.json
<!-- GEN:END eyeball_index -->
<!-- GEN:START appendix -->
## 附录指针

- numeric authority: [../_run/baseline.json](../_run/baseline.json)
- run manifest: [../_run/run_manifest.json](../_run/run_manifest.json)
- validation summary: [../_run/validation_manifest.json](../_run/validation_manifest.json)
- geometry approval: [../_run/geometry_approval.json](../_run/geometry_approval.json)
- orchestration ledger: [../_run/orchestration_state.json](../_run/orchestration_state.json)
- raw reading outputs: [../0_reading/](../0_reading/)
- correction audit: [../1_correction/corrections.json](../1_correction/corrections.json)
- judge verdict log: [../verdicts/](../verdicts/)
- geometry_digest: `None`

### evidence_index
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
- `E:stop:human_redraw_required@1_correction` (stop; source `_run/orchestration_state.json`) — _run/orchestration_state.json
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
<!-- GEN:END appendix -->
