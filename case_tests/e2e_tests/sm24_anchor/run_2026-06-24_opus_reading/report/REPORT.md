<!-- GEN:START model_config -->
# sm24_anchor / run_2026-06-24_opus_reading REPORT

## 本次模型配置

- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-06-24`
- orchestrator: `opus-4.8`
- 自动状态: `completed_clean`
- default: `deepseek-v4-pro`
- intake_correction: `deepseek-v4-pro`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ✅ clean / EP Completed, 0 severe, 6 warn / 11区·76面·11窗

**数字权威**: [../_run/baseline.json](../_run/baseline.json) + 本 REPORT 的 GEN 区；AGENT 区为主控叙事/建议，citation linter 只约束建议证据 id。

### 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 0_reading | 49 | 0 | 0 | 11 |
| 1_correction | 5 | 1 | 0 | 1 |
| 2_modelling | 5 | 0 | 0 | 0 |
| 4_mep | 10 | 0 | 0 | 1 |
| 5_intakeoutput | 1 | 0 | 0 | 0 |
| downstream | 3 | 0 | 0 | 1 |

### 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | judge_pass | 1 |
| 1_correction | judge_pass | 2 |
| 2_modelling | deterministic_pass | 1 |
| 3_split_pairing | awaiting_geometry_approval | 1 |
| 4_mep | deterministic_pass | 1 |
| 5_intakeoutput | deterministic_pass | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 1, '1_correction': 2, '2_modelling': 1, '3_split_pairing': 1, '4_mep': 1, '5_intakeoutput': 1}

**judge② verdicts**: 2 条（0 条 blocking；见各 attempts/NNN/judge.json）

### run_state

- status: `completed_clean`
- completed_clean: true
- ignored_pending: ['awaiting_geometry_approval@3_split_pairing']

### flags（不阻塞、供归因）
- [1_correction::correction.zone_count_tripwire] cell count 11 != testdata thermal_zones 8

### 校正审计摘要

- sidecar: `1_correction/corrections.json` (ok)
- counts: corrections=24, conflicts=1, unsupported=0
- by_rule_id: {"A1_centerline_exterior": 4, "A3_gap_close_north_divider": 1, "A3_inferred_wall_extension": 1, "deterministic_core.snap": 17, "deterministic_core.window": 1}
- by_stage: {"A1": 4, "A3": 3, "core": 18}
<!-- GEN:END facts_card -->
<!-- AGENT:START conclusion -->
## 一句话结论

- 自动状态: `completed_clean`
- **非方形 case 全链路跑通（EP Completed, 0 severe）**：识图干净、几何内核封闭、InterZone 配对零缺陷；唯一信号是确定性内核把两个**非矩形房间**按矩形分解 → cell 数 8→11（tripwire flag，非 bug）。本 run **无 gt**（有意为之），区数正确性待补 gt 后定量。
<!-- AGENT:END conclusion -->
<!-- AGENT:START focus -->
## 本轮侧重点

- 这是**首个非方形 case** 的端到端探针：footprint 10×20m 规整，但**内部走廊是 L 形（非矩形）**、右下 office 有阶梯西墙。目的=看现有确定性几何框架在非矩形几何下的行为，**不求"干净金标准"、不做 judge 阻塞**。
- 识图由 **Opus 冷启子代理**完成（顺带是 reading-honest schema 的一个强模型对照点）；correction/mep/下游走 DeepSeek；几何门由 orchestrator 自评放行（actor=opus_agent）。
- **本 run 无 gt**（有意为之，后续补）——所以区划/窗位的"对不对"只有定性观察，没有定量评分。
<!-- AGENT:END focus -->
<!-- AGENT:START diagnosis -->
## 错在哪儿 + 归因

本 run **没有"错"**——是一个干净跑通的非方形探针。因果链如下：

1. **识图干净（无回归显形）**：Opus 7 条 J0 准则全 pass，仅 `lstep_coordinates` 一条 minor/correction_recoverable（L 拐 x 从像素估、有尺寸链兜底）[E:judge:0_reading:001:c1]…[E:judge:0_reading:001:c7]。无家具误当墙、无尺寸链误当墙——**reading-honest 的 provenance 字段在 Opus 上没有诱发过度分割**（子代理 schema feedback 明确：`dimension_derived` 仅用于周边墙、内墙用 `seen`）。
2. **校正忠实但触发区数 tripwire（11≠8）**：唯一 flag [E:gate:1_correction:correction.zone_count_tripwire]。J1 判为 minor/recoverable [E:judge:1_correction:002:c2]——**非校正错**，是确定性内核把两个非矩形房间按矩形分解：**L 形走廊 → Z06_Corridor_N + Z10_Corridor_SE**，**阶梯西墙右下 office → Z07/Z08/Z11**。
3. **几何内核 + InterZone 配对零缺陷**：11 区/76 面/11 窗，kernel gate 0 issue；76 面边界 = 40 内部相邻(Surface) + 25 室外 + 11 接地，**全互逆**。关键：`Z06_W1 ↔ Z10_W5` 互为匹配面 [E:geom:digest]——L 形走廊两段**导热连通、未被热隔离**（拆区没切断物理连接）。
4. **EP 成功**：0 severe / 6 warn（全样板告警）[E:ep:result]。
<!-- AGENT:END diagnosis -->
<!-- AGENT:START recommendations -->
## 建议


### 机制问题

- action: 区数 tripwire 在非矩形分解下**正确触发并被 judge 正确归类为 recoverable**，judge-in-the-loop 机制工作正常，无需改。
  evidence: [E:gate:1_correction:correction.zone_count_tripwire], [E:judge:1_correction:002:c2]
  owner: 无（机制确认）

### 能力升级

- action: **非矩形开敞空间过度分区**——L 形走廊被拆成两个独立 EP 热区（Z06/Z10），它们导热耦合但**无空气耦合**（无 AirBoundary / ZoneMixing），EP 视为中间隔导热墙的两个区，而物理上是一个连通开敞空间。需在内核分解后加一步**区合并 / air-boundary**：把同一开敞空间的矩形碎片标记为 air-coupled（`Construction:AirBoundary`）或合并为单热区。这是非方形(C2)能力升级的核心一环。
  evidence: [E:judge:1_correction:002:c2], [E:gate:1_correction:correction.zone_count_tripwire], [E:geom:digest]
  owner: capability / C2 非方形

### 脚手架建议

- action: `run_full_pipeline` 把 EP 产物写到 `<case>/output/` 而非 `<run>/EP/EP_run/`，导致 record_baseline --require-ep 找不到、需手动归位。anchor（run 子目录）布局下应让下游 EP 输出直接落 run 目录。
  evidence: [E:ep:result]
  owner: scaffold

### 修法

- action: **本 case 补 gt（精确区划/每立面窗数/尺寸），尤其约定非矩形房间的"期望热区数"口径**（L 走廊算 1 还是 2），区数正确性才能定量、本 run 才能升为 golden anchor。补 gt 前 sm24 不入册 golden。
  evidence: [E:judge:1_correction:002:c2]
  owner: gt / N3
<!-- AGENT:END recommendations -->
<!-- GEN:START eyeball_index -->
## 肉视检验索引

1. 2D 肉检 `report/eyeball/1_correction_zones.png`（from `1_correction/zones.png` / correction_zones）
2. 2D 肉检 `report/eyeball/1_correction_elev.png`（from `1_correction/elev.png` / correction_elev）
3. 2D 肉检 `report/eyeball/0_reading_1f_view_render.png`（from `0_reading/1f_view_render.png` / reading_render）
4. 2D 肉检 `report/eyeball/0_reading_East_view_render.png`（from `0_reading/East_view_render.png` / reading_render）
5. 2D 肉检 `report/eyeball/0_reading_North_view_render.png`（from `0_reading/North_view_render.png` / reading_render）
6. 2D 肉检 `report/eyeball/0_reading_South_view_render.png`（from `0_reading/South_view_render.png` / reading_render）
7. 2D 肉检 `report/eyeball/0_reading_West_view_render.png`（from `0_reading/West_view_render.png` / reading_render）
8. 2D 肉检 `report/eyeball/case_data_1f_view.png`（from `../case_data/1f_view.png` / case_data_view）
9. 2D 肉检 `report/eyeball/case_data_East_view.png`（from `../case_data/East_view.png` / case_data_view）
10. 2D 肉检 `report/eyeball/case_data_North_view.png`（from `../case_data/North_view.png` / case_data_view）
11. 2D 肉检 `report/eyeball/case_data_South_view.png`（from `../case_data/South_view.png` / case_data_view）
12. 2D 肉检 `report/eyeball/case_data_West_view.png`（from `../case_data/West_view.png` / case_data_view）
13. 3D 几何 `manual_review/geometry_viewer.html`（existing；浏览器打开 orbit / 半透明 / 截面 / 爆炸 / 量距，确认无误后 `approve-geometry`）
14. flag [1_correction::correction.zone_count_tripwire] —— cell count 11 != testdata thermal_zones 8（对应渲染件人工核一眼）
15. audit-derived [corrections_summary] —— `corrections.json` 有 1 conflicts / 0 unsupported，人核看错↔改错归因

### report/eyeball
- [1_correction_zones.png](eyeball/1_correction_zones.png) — correction_zones from `1_correction/zones.png`
- [1_correction_elev.png](eyeball/1_correction_elev.png) — correction_elev from `1_correction/elev.png`
- [0_reading_1f_view_render.png](eyeball/0_reading_1f_view_render.png) — reading_render from `0_reading/1f_view_render.png`
- [0_reading_East_view_render.png](eyeball/0_reading_East_view_render.png) — reading_render from `0_reading/East_view_render.png`
- [0_reading_North_view_render.png](eyeball/0_reading_North_view_render.png) — reading_render from `0_reading/North_view_render.png`
- [0_reading_South_view_render.png](eyeball/0_reading_South_view_render.png) — reading_render from `0_reading/South_view_render.png`
- [0_reading_West_view_render.png](eyeball/0_reading_West_view_render.png) — reading_render from `0_reading/West_view_render.png`
- [case_data_1f_view.png](eyeball/case_data_1f_view.png) — case_data_view from `../case_data/1f_view.png`
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
- geometry_digest: `92b70adb282f0c560b866dc6b0857e9829d453b5a5194f4b04203f7744760176`

### evidence_index
- `E:gate:1_correction:correction.zone_count_tripwire` (gate; source `1_correction`) — cell count 11 != testdata thermal_zones 8
- `E:judge:0_reading:001:c1` (judge; source `0_reading/attempts/001/judge.json`) — wall_completeness
- `E:judge:0_reading:001:c2` (judge; source `0_reading/attempts/001/judge.json`) — no_furniture_as_wall
- `E:judge:0_reading:001:c3` (judge; source `0_reading/attempts/001/judge.json`) — no_dimension_as_wall
- `E:judge:0_reading:001:c4` (judge; source `0_reading/attempts/001/judge.json`) — door_healing
- `E:judge:0_reading:001:c5` (judge; source `0_reading/attempts/001/judge.json`) — window_recognition
- `E:judge:0_reading:001:c6` (judge; source `0_reading/attempts/001/judge.json`) — elevation_axes
- `E:judge:0_reading:001:c7` (judge; source `0_reading/attempts/001/judge.json`) — lstep_coordinates
- `E:judge:1_correction:002:c1` (judge; source `1_correction/attempts/002/judge.json`) — zonation_layout
- `E:judge:1_correction:002:c2` (judge; source `1_correction/attempts/002/judge.json`) — zone_count
- `E:judge:1_correction:002:c3` (judge; source `1_correction/attempts/002/judge.json`) — window_placement
- `E:judge:1_correction:002:c4` (judge; source `1_correction/attempts/002/judge.json`) — cross_floor
- `E:judge:1_correction:002:c5` (judge; source `1_correction/attempts/002/judge.json`) — overall_redraw
- `E:corr:corrections:corr_1` (correction; source `1_correction/corrections.json`) — corr_1
- `E:corr:corrections:corr_2` (correction; source `1_correction/corrections.json`) — corr_2
- `E:corr:corrections:corr_3` (correction; source `1_correction/corrections.json`) — corr_3
- `E:corr:corrections:corr_4` (correction; source `1_correction/corrections.json`) — corr_4
- `E:corr:corrections:corr_5` (correction; source `1_correction/corrections.json`) — corr_5
- `E:corr:corrections:corr_6` (correction; source `1_correction/corrections.json`) — corr_6
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
- `E:corr:conflicts:conf_1` (correction; source `1_correction/corrections.json`) — conf_1
- `E:ep:result` (ep; source `EP/EP_run/eplusout.end`) — EP/EP_run/eplusout.end
- `E:geom:digest` (geometry; source `2_modelling/building_geometry.json`) — 2_modelling/building_geometry.json
- `E:eyeball:1_correction_zones.png` (eyeball; source `report/eyeball/1_correction_zones.png`) — report/eyeball/1_correction_zones.png
- `E:eyeball:1_correction_elev.png` (eyeball; source `report/eyeball/1_correction_elev.png`) — report/eyeball/1_correction_elev.png
- `E:eyeball:0_reading_1f_view_render.png` (eyeball; source `report/eyeball/0_reading_1f_view_render.png`) — report/eyeball/0_reading_1f_view_render.png
- `E:eyeball:0_reading_East_view_render.png` (eyeball; source `report/eyeball/0_reading_East_view_render.png`) — report/eyeball/0_reading_East_view_render.png
- `E:eyeball:0_reading_North_view_render.png` (eyeball; source `report/eyeball/0_reading_North_view_render.png`) — report/eyeball/0_reading_North_view_render.png
- `E:eyeball:0_reading_South_view_render.png` (eyeball; source `report/eyeball/0_reading_South_view_render.png`) — report/eyeball/0_reading_South_view_render.png
- `E:eyeball:0_reading_West_view_render.png` (eyeball; source `report/eyeball/0_reading_West_view_render.png`) — report/eyeball/0_reading_West_view_render.png
- `E:eyeball:case_data_1f_view.png` (eyeball; source `report/eyeball/case_data_1f_view.png`) — report/eyeball/case_data_1f_view.png
- `E:eyeball:case_data_East_view.png` (eyeball; source `report/eyeball/case_data_East_view.png`) — report/eyeball/case_data_East_view.png
- `E:eyeball:case_data_North_view.png` (eyeball; source `report/eyeball/case_data_North_view.png`) — report/eyeball/case_data_North_view.png
- `E:eyeball:case_data_South_view.png` (eyeball; source `report/eyeball/case_data_South_view.png`) — report/eyeball/case_data_South_view.png
- `E:eyeball:case_data_West_view.png` (eyeball; source `report/eyeball/case_data_West_view.png`) — report/eyeball/case_data_West_view.png
<!-- GEN:END appendix -->
