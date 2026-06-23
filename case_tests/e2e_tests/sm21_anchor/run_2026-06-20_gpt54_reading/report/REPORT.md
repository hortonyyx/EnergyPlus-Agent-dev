<!-- GEN:START model_config -->
# sm21_anchor / run_2026-06-20_gpt54_reading REPORT

## 本次模型配置

- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-06-21`
- orchestrator: `opus-4.8`
- 自动状态: `completed_clean`
- default: `deepseek-v4-pro`
- intake_correction: `deepseek-v4-pro`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ✅ clean / EP Completed, 0 severe, 6 warn / 14区·112面·15窗

**数字权威**: [../_run/baseline.json](../_run/baseline.json) + 本 REPORT 的 GEN 区；AGENT 区为主控叙事/建议，citation linter 只约束建议证据 id。

### 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 0_reading | 58 | 0 | 0 | 14 |
| 1_correction | 7 | 0 | 0 | 1 |
| 2_modelling | 5 | 0 | 0 | 0 |
| 4_mep | 10 | 0 | 0 | 1 |
| 5_intakeoutput | 1 | 0 | 0 | 0 |
| downstream | 3 | 0 | 0 | 1 |

### 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | judge_pass | 2 |
| 1_correction | judge_pass | 1 |
| 2_modelling | deterministic_pass | 1 |
| 3_split_pairing | awaiting_geometry_approval | 1 |
| 4_mep | deterministic_pass | 1 |
| 5_intakeoutput | deterministic_pass | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 2, '1_correction': 1, '2_modelling': 1, '3_split_pairing': 1, '4_mep': 1, '5_intakeoutput': 1}

**judge② verdicts**: 2 条（0 条 blocking；见各 attempts/NNN/judge.json）

### run_state

- status: `completed_clean`
- completed_clean: true
- ignored_pending: ['awaiting_geometry_approval@3_split_pairing']

### 校正审计摘要

- sidecar: `1_correction/corrections.json` (ok)
- counts: corrections=36, conflicts=2, unsupported=0
- by_rule_id: {"A1_centerline": 1, "A1_coordinate_normalization": 1, "A3_stroke_vs_dimension": 2, "deterministic_core.snap": 32}
- by_stage: {"A1_coordinate_normalization": 1, "A2-detect": 1, "A3-resolve": 4, "core": 32}
<!-- GEN:END facts_card -->
<!-- AGENT:START conclusion -->
## 一句话结论

- 自动状态: `completed_clean`
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
15. 3D 几何 `manual_review/geometry_viewer.html`（existing；浏览器打开 orbit / 半透明 / 截面 / 爆炸 / 量距，确认无误后 `approve-geometry`）
16. audit-derived [corrections_summary] —— `corrections.json` 有 2 conflicts / 0 unsupported，人核看错↔改错归因

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
- [3D geometry viewer](../manual_review/geometry_viewer.html) — `existing`
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
- geometry_digest: `6d7a44f4caae4e92ddc750a70361a7c8c37a8c150c4e17951d65aed9be5aaa2c`

### evidence_index
- `E:judge:0_reading:002:c1` (judge; source `0_reading/attempts/002/judge.json`) — missed real element
- `E:judge:0_reading:002:c2` (judge; source `0_reading/attempts/002/judge.json`) — clutter traced as structure
- `E:judge:0_reading:002:c3` (judge; source `0_reading/attempts/002/judge.json`) — pen misclassified
- `E:judge:0_reading:002:c4` (judge; source `0_reading/attempts/002/judge.json`) — number copied wrong
- `E:judge:0_reading:002:c5` (judge; source `0_reading/attempts/002/judge.json`) — image-local orientation self-consistent
- `E:judge:0_reading:002:c6` (judge; source `0_reading/attempts/002/judge.json`) — door healing wrong
- `E:judge:0_reading:002:c7` (judge; source `0_reading/attempts/002/judge.json`) — whole-region missing / misplaced
- `E:judge:1_correction:001:c1` (judge; source `1_correction/attempts/001/judge.json`) — zonification fidelity
- `E:judge:1_correction:001:c2` (judge; source `1_correction/attempts/001/judge.json`) — cross-floor consistency
- `E:judge:1_correction:001:c3` (judge; source `1_correction/attempts/001/judge.json`) — window position fidelity
- `E:judge:1_correction:001:c4` (judge; source `1_correction/attempts/001/judge.json`) — count vs reference
- `E:judge:1_correction:001:c5` (judge; source `1_correction/attempts/001/judge.json`) — overall redraw
- `E:corr:corrections:corr_1F_S_spans` (correction; source `1_correction/corrections.json`) — corr_1F_S_spans
- `E:corr:corrections:corr_2F_S_spans` (correction; source `1_correction/corrections.json`) — corr_2F_S_spans
- `E:corr:corrections:corr_z_values` (correction; source `1_correction/corrections.json`) — corr_z_values
- `E:corr:corrections:corr_central_centerlines` (correction; source `1_correction/corrections.json`) — corr_central_centerlines
- `E:corr:corrections:r5` (correction; source `1_correction/corrections.json`) — row 5
- `E:corr:corrections:r6` (correction; source `1_correction/corrections.json`) — row 6
- `E:corr:corrections:r7` (correction; source `1_correction/corrections.json`) — row 7
- `E:corr:corrections:r8` (correction; source `1_correction/corrections.json`) — row 8
- `E:corr:corrections:r9` (correction; source `1_correction/corrections.json`) — row 9
- `E:corr:corrections:r10` (correction; source `1_correction/corrections.json`) — row 10
- `E:corr:corrections:r11` (correction; source `1_correction/corrections.json`) — row 11
- `E:corr:corrections:r12` (correction; source `1_correction/corrections.json`) — row 12
- `E:corr:corrections:r13` (correction; source `1_correction/corrections.json`) — row 13
- `E:corr:corrections:r14` (correction; source `1_correction/corrections.json`) — row 14
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
- `E:corr:conflicts:conflict_cross_floor_corridor` (correction; source `1_correction/corrections.json`) — conflict_cross_floor_corridor
- `E:corr:conflicts:conflict_1F_south_extra_window` (correction; source `1_correction/corrections.json`) — conflict_1F_south_extra_window
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
