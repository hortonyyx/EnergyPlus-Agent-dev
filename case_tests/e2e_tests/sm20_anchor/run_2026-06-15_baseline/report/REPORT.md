<!-- GEN:START model_config -->
# sm20_anchor / run_2026-06-15_baseline REPORT

## 本次模型配置

- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-06-16`
- orchestrator: `opus-4.8`
- 自动状态: `incomplete`
- default: `deepseek-v4-pro`
- intake_correction: `deepseek-v4-pro`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ⚠️ incomplete / EP Completed, 0 severe, 6 warn / 19区·135面·16窗

**数字权威**: [../_run/baseline.json](../_run/baseline.json) + 本 REPORT 的 GEN 区；AGENT 区为主控叙事/建议，citation linter 只约束建议证据 id。

### 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 0_reading | 67 | 0 | 0 | 17 |
| 1_correction | 8 | 0 | 0 | 1 |
| 2_modelling | 5 | 0 | 0 | 0 |
| 4_mep | 10 | 0 | 0 | 1 |
| 5_intakeoutput | 1 | 0 | 0 | 0 |
| downstream | 3 | 0 | 0 | 1 |

### run_state

- status: `incomplete`
- missing_expected: ['0_reading', '1_correction', '2_modelling', '3_split_pairing', '4_mep', '5_intakeoutput']

### 校正审计摘要

- sidecar: `1_correction/corrections.json` (ok)
- counts: corrections=11, conflicts=0, unsupported=0
- by_rule_id: {"A1_facade_local_to_world": 10, "A1_zstack": 1}
- by_stage: {"A1": 11}
<!-- GEN:END facts_card -->
<!-- AGENT:START conclusion -->
## 一句话结论

- 自动状态: `incomplete`
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
3. 2D 肉检 `report/eyeball/0_reading_3f_view_render.png`（from `0_reading/3f_view_render.png` / reading_render）
4. 2D 肉检 `report/eyeball/0_reading_East_view_render.png`（from `0_reading/East_view_render.png` / reading_render）
5. 2D 肉检 `report/eyeball/0_reading_North_view_render.png`（from `0_reading/North_view_render.png` / reading_render）
6. 2D 肉检 `report/eyeball/0_reading_South_view_render.png`（from `0_reading/South_view_render.png` / reading_render）
7. 2D 肉检 `report/eyeball/0_reading_West_view_render.png`（from `0_reading/West_view_render.png` / reading_render）
8. 2D 肉检 `report/eyeball/case_data_1f_view.png`（from `../case_data/1f_view.png` / case_data_view）
9. 2D 肉检 `report/eyeball/case_data_2f_view.png`（from `../case_data/2f_view.png` / case_data_view）
10. 2D 肉检 `report/eyeball/case_data_3f_view.png`（from `../case_data/3f_view.png` / case_data_view）
11. 2D 肉检 `report/eyeball/case_data_East_view.png`（from `../case_data/East_view.png` / case_data_view）
12. 2D 肉检 `report/eyeball/case_data_North_view.png`（from `../case_data/North_view.png` / case_data_view）
13. 2D 肉检 `report/eyeball/case_data_South_view.png`（from `../case_data/South_view.png` / case_data_view）
14. 2D 肉检 `report/eyeball/case_data_West_view.png`（from `../case_data/West_view.png` / case_data_view）
15. missing eyeball producer `1_correction/zones.png` (correction_zones)
16. missing eyeball producer `1_correction/elev.png` (correction_elev)
17. 3D 几何 `manual_review/geometry_viewer.html`（regenerated；浏览器打开 orbit / 半透明 / 截面 / 爆炸 / 量距，确认无误后 `approve-geometry`）

### report/eyeball
- [0_reading_1f_view_render.png](eyeball/0_reading_1f_view_render.png) — reading_render from `0_reading/1f_view_render.png`
- [0_reading_2f_view_render.png](eyeball/0_reading_2f_view_render.png) — reading_render from `0_reading/2f_view_render.png`
- [0_reading_3f_view_render.png](eyeball/0_reading_3f_view_render.png) — reading_render from `0_reading/3f_view_render.png`
- [0_reading_East_view_render.png](eyeball/0_reading_East_view_render.png) — reading_render from `0_reading/East_view_render.png`
- [0_reading_North_view_render.png](eyeball/0_reading_North_view_render.png) — reading_render from `0_reading/North_view_render.png`
- [0_reading_South_view_render.png](eyeball/0_reading_South_view_render.png) — reading_render from `0_reading/South_view_render.png`
- [0_reading_West_view_render.png](eyeball/0_reading_West_view_render.png) — reading_render from `0_reading/West_view_render.png`
- [case_data_1f_view.png](eyeball/case_data_1f_view.png) — case_data_view from `../case_data/1f_view.png`
- [case_data_2f_view.png](eyeball/case_data_2f_view.png) — case_data_view from `../case_data/2f_view.png`
- [case_data_3f_view.png](eyeball/case_data_3f_view.png) — case_data_view from `../case_data/3f_view.png`
- [case_data_East_view.png](eyeball/case_data_East_view.png) — case_data_view from `../case_data/East_view.png`
- [case_data_North_view.png](eyeball/case_data_North_view.png) — case_data_view from `../case_data/North_view.png`
- [case_data_South_view.png](eyeball/case_data_South_view.png) — case_data_view from `../case_data/South_view.png`
- [case_data_West_view.png](eyeball/case_data_West_view.png) — case_data_view from `../case_data/West_view.png`

### missing producers
- `1_correction/zones.png` (correction_zones)
- `1_correction/elev.png` (correction_elev)

### manual_review viewer
- [3D geometry viewer](../manual_review/geometry_viewer.html) — `regenerated`
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
- geometry_digest: `225fb57256b3b2a0546c0cacde68506240c6cf0283d109d8d0be4fd275f3b411`

### evidence_index
- `E:corr:corrections:CORR_ZNSTACK` (correction; source `1_correction/corrections.json`) — CORR_ZNSTACK
- `E:corr:corrections:CORR_NORTH_WIN_F1_1` (correction; source `1_correction/corrections.json`) — CORR_NORTH_WIN_F1_1
- `E:corr:corrections:CORR_NORTH_WIN_F1_2` (correction; source `1_correction/corrections.json`) — CORR_NORTH_WIN_F1_2
- `E:corr:corrections:CORR_NORTH_WIN_F1_3` (correction; source `1_correction/corrections.json`) — CORR_NORTH_WIN_F1_3
- `E:corr:corrections:CORR_NORTH_WIN_F2_1` (correction; source `1_correction/corrections.json`) — CORR_NORTH_WIN_F2_1
- `E:corr:corrections:CORR_NORTH_WIN_F2_2` (correction; source `1_correction/corrections.json`) — CORR_NORTH_WIN_F2_2
- `E:corr:corrections:CORR_NORTH_WIN_F2_3` (correction; source `1_correction/corrections.json`) — CORR_NORTH_WIN_F2_3
- `E:corr:corrections:CORR_NORTH_WIN_F2_4` (correction; source `1_correction/corrections.json`) — CORR_NORTH_WIN_F2_4
- `E:corr:corrections:CORR_NORTH_WIN_F3_1` (correction; source `1_correction/corrections.json`) — CORR_NORTH_WIN_F3_1
- `E:corr:corrections:CORR_EAST_WIN_F3_1` (correction; source `1_correction/corrections.json`) — CORR_EAST_WIN_F3_1
- `E:corr:corrections:CORR_WEST_WIN_F3_1` (correction; source `1_correction/corrections.json`) — CORR_WEST_WIN_F3_1
- `E:ep:result` (ep; source `EP/EP_run/eplusout.end`) — EP/EP_run/eplusout.end
- `E:geom:digest` (geometry; source `2_modelling/building_geometry.json`) — 2_modelling/building_geometry.json
- `E:eyeball:0_reading_1f_view_render.png` (eyeball; source `report/eyeball/0_reading_1f_view_render.png`) — report/eyeball/0_reading_1f_view_render.png
- `E:eyeball:0_reading_2f_view_render.png` (eyeball; source `report/eyeball/0_reading_2f_view_render.png`) — report/eyeball/0_reading_2f_view_render.png
- `E:eyeball:0_reading_3f_view_render.png` (eyeball; source `report/eyeball/0_reading_3f_view_render.png`) — report/eyeball/0_reading_3f_view_render.png
- `E:eyeball:0_reading_East_view_render.png` (eyeball; source `report/eyeball/0_reading_East_view_render.png`) — report/eyeball/0_reading_East_view_render.png
- `E:eyeball:0_reading_North_view_render.png` (eyeball; source `report/eyeball/0_reading_North_view_render.png`) — report/eyeball/0_reading_North_view_render.png
- `E:eyeball:0_reading_South_view_render.png` (eyeball; source `report/eyeball/0_reading_South_view_render.png`) — report/eyeball/0_reading_South_view_render.png
- `E:eyeball:0_reading_West_view_render.png` (eyeball; source `report/eyeball/0_reading_West_view_render.png`) — report/eyeball/0_reading_West_view_render.png
- `E:eyeball:case_data_1f_view.png` (eyeball; source `report/eyeball/case_data_1f_view.png`) — report/eyeball/case_data_1f_view.png
- `E:eyeball:case_data_2f_view.png` (eyeball; source `report/eyeball/case_data_2f_view.png`) — report/eyeball/case_data_2f_view.png
- `E:eyeball:case_data_3f_view.png` (eyeball; source `report/eyeball/case_data_3f_view.png`) — report/eyeball/case_data_3f_view.png
- `E:eyeball:case_data_East_view.png` (eyeball; source `report/eyeball/case_data_East_view.png`) — report/eyeball/case_data_East_view.png
- `E:eyeball:case_data_North_view.png` (eyeball; source `report/eyeball/case_data_North_view.png`) — report/eyeball/case_data_North_view.png
- `E:eyeball:case_data_South_view.png` (eyeball; source `report/eyeball/case_data_South_view.png`) — report/eyeball/case_data_South_view.png
- `E:eyeball:case_data_West_view.png` (eyeball; source `report/eyeball/case_data_West_view.png`) — report/eyeball/case_data_West_view.png
<!-- GEN:END appendix -->
