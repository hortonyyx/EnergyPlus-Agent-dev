<!-- GEN:START model_config -->
# sm21_anchor / run_2026-06-21_sonnet_reading_retry REPORT

## 本次模型配置

- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-06-21`
- orchestrator: `opus-4.8`
- 自动状态: `root_stopped: human_redraw_required@0_reading`
- default: `deepseek-v4-pro`
- intake_correction: `deepseek-v4-pro`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ❌ STOPPED (human_redraw_required@0_reading) / EP 未跑

**数字权威**: [../_run/baseline.json](../_run/baseline.json) + 本 REPORT 的 GEN 区；AGENT 区为主控叙事/建议，citation linter 只约束建议证据 id。

### 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 1_correction | 0 | 0 | 1 | 0 |
| 2_modelling | 0 | 0 | 1 | 0 |
| 3_split_pairing | 0 | 0 | 1 | 0 |
| 4_mep | 0 | 0 | 1 | 0 |
| 5_intakeoutput | 0 | 0 | 1 | 0 |
| 0_reading | 58 | 0 | 0 | 14 |

### 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | human_redraw_required | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 1}

**judge② verdicts**: 1 条（1 条 blocking；见各 attempts/NNN/judge.json）

### run_state

- status: `root_stopped`
- root_stop: `human_redraw_required@0_reading`
- root message: judge blocked, root='0_reading' (manual) → human re-trace required
- missing_expected: ['1_correction', '2_modelling', '3_split_pairing', '4_mep', '5_intakeoutput']

### blocking
- [1_correction::1_correction.build] required artifact missing: 1_correction/correction_geometry_snapped.json
- [2_modelling::2_modelling.build] required artifact missing: 2_modelling/building_geometry.json
- [3_split_pairing::3_split_pairing.build] required artifact missing: 3_split_pairing/geometry_specs.md
- [4_mep::4_mep.build] required artifact missing: 4_mep/mep_output.json
- [5_intakeoutput::5_intakeoutput.build] required artifact missing: 5_intakeoutput/intake_output.json

### 连带缺失下游件

- `1_correction`: required artifact missing: 1_correction/correction_geometry_snapped.json
- `2_modelling`: required artifact missing: 2_modelling/building_geometry.json
- `3_split_pairing`: required artifact missing: 3_split_pairing/geometry_specs.md
- `4_mep`: required artifact missing: 4_mep/mep_output.json
- `5_intakeoutput`: required artifact missing: 5_intakeoutput/intake_output.json

### 校正审计摘要

- sidecar: `1_correction/corrections.json` (missing)
<!-- GEN:END facts_card -->
<!-- AGENT:START conclusion -->
## 一句话结论

- 自动状态: `root_stopped: human_redraw_required@0_reading`
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

1. 2D 肉检 `report/eyeball/0_reading_1f_view_render.png`（from `0_reading/1f_view_render.png` / reading_render）
2. 2D 肉检 `report/eyeball/0_reading_2f_view_render.png`（from `0_reading/2f_view_render.png` / reading_render）
3. 2D 肉检 `report/eyeball/0_reading_East_view_render.png`（from `0_reading/East_view_render.png` / reading_render）
4. 2D 肉检 `report/eyeball/0_reading_North_view_render.png`（from `0_reading/North_view_render.png` / reading_render）
5. 2D 肉检 `report/eyeball/0_reading_South_view_render.png`（from `0_reading/South_view_render.png` / reading_render）
6. 2D 肉检 `report/eyeball/0_reading_West_view_render.png`（from `0_reading/West_view_render.png` / reading_render）
7. 2D 肉检 `report/eyeball/case_data_1f_view.png`（from `../case_data/1f_view.png` / case_data_view）
8. 2D 肉检 `report/eyeball/case_data_2f_view.png`（from `../case_data/2f_view.png` / case_data_view）
9. 2D 肉检 `report/eyeball/case_data_East_view.png`（from `../case_data/East_view.png` / case_data_view）
10. 2D 肉检 `report/eyeball/case_data_North_view.png`（from `../case_data/North_view.png` / case_data_view）
11. 2D 肉检 `report/eyeball/case_data_South_view.png`（from `../case_data/South_view.png` / case_data_view）
12. 2D 肉检 `report/eyeball/case_data_West_view.png`（from `../case_data/West_view.png` / case_data_view）
13. missing eyeball producer `1_correction/zones.png` (correction_zones)
14. missing eyeball producer `1_correction/elev.png` (correction_elev)
15. 3D 几何 viewer unavailable: missing 2_modelling/building_geometry.json

### report/eyeball
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

### missing producers
- `1_correction/zones.png` (correction_zones)
- `1_correction/elev.png` (correction_elev)

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
- `E:gate:1_correction:1_correction.build` (gate; source `1_correction`) — required artifact missing: 1_correction/correction_geometry_snapped.json
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
- `E:stop:human_redraw_required@0_reading` (stop; source `_run/orchestration_state.json`) — _run/orchestration_state.json
- `E:ep:result` (ep; source `EP/EP_run/eplusout.end`) — EP/EP_run/eplusout.end
- `E:geom:digest` (geometry; source `2_modelling/building_geometry.json`) — 2_modelling/building_geometry.json
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
