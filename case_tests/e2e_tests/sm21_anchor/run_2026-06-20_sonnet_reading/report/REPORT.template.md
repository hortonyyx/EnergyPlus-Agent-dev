# sm21_anchor / run_2026-06-20_sonnet_reading REPORT

<!-- GENERATED-SKELETON: deterministic scaffolding; Agent-authored narrative lives in this file. -->

## 一句话结论

- 自动状态: `root_stopped: human_redraw_required@1_correction`
<!-- AGENT-FILL: 用一句话写 pass/blocked + 本 run 最重要的一件事。 -->

## 本轮侧重点

<!-- AGENT-FILL: 说明这轮在测什么、为何重要。 -->

## 事实卡

- [FACTS.md](FACTS.md)
- [baseline.json](../baseline.json)
- evidence_index entries: 83

## 运行状态

- run_state: root_stopped
- 根因停: `human_redraw_required@1_correction`
- stop message: judge blocked, root='0_reading' (manual) → human re-trace required

### 连带缺失下游件

- `2_modelling`: required artifact missing: 2_modelling/building_geometry.json
- `3_split_pairing`: required artifact missing: 3_split_pairing/geometry_specs.md
- `4_mep`: required artifact missing: 4_mep/mep_output.json
- `5_intakeoutput`: required artifact missing: 5_intakeoutput/intake_output.json

## 错在哪儿 + 归因

<!-- AGENT-FILL: 用 evidence_index 把 gate/judge/correction/肉检事实串成因果链。 -->

## 肉视检验

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
- 3D geometry viewer unavailable — missing 2_modelling/building_geometry.json

## 建议


### 机制问题

本 run 无可证据支持的建议

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

本 run 无可证据支持的建议

### 修法

本 run 无可证据支持的建议

## 附录指针

- raw reading outputs: [../0_reading/](../0_reading/)
- correction audit: [../1_correction/corrections.json](../1_correction/corrections.json)
- judge verdict log: [../verdicts/](../verdicts/)
- orchestration ledger: [../orchestration_state.json](../orchestration_state.json)
