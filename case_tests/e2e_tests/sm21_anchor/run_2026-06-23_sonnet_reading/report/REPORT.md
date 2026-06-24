<!-- GEN:START model_config -->
# sm21_anchor / run_2026-06-23_sonnet_reading REPORT

## 本次模型配置

- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-06-23`
- orchestrator: `opus-4.8`
- 自动状态: `root_stopped: quarantined@0_reading`
- default: `deepseek-v4-pro`
- intake_correction: `deepseek-v4-pro`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ❌ STOPPED (quarantined@0_reading) / EP 未跑

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
| 0_reading | quarantined | 3 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 3}

**judge② verdicts**: 3 条（3 条 blocking；见各 attempts/NNN/judge.json）

### run_state

- status: `root_stopped`
- root_stop: `quarantined@0_reading`
- root message: judge blocked, root='0_reading' (manual) but re-read budget (3) is spent — quarantine for human triage
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

- 自动状态: `root_stopped: quarantined@0_reading`
**❌ BLOCKED — Sonnet 的 sm21 识图在 3/3 盲重读后 quarantine**：1f 南带把家具/尺寸链 tick/窗洞边误当隔墙（过度分割），att3 经"存在性纪律"已从 16 墙砍到 10 墙、2f 全对，但 1f 仍残留 1 道窗边伪隔墙（x=3.44）→ floor1 8 区 vs gt 7，不达干净标准、不入 baseline。**机制侧（gate①→J0→判不可恢复→auto-reread→预算用尽 quarantine）全程按设计正确运转。**
<!-- AGENT:END conclusion -->
<!-- AGENT:START focus -->
## 本轮侧重点

本轮 = sm21 批次重跑（攒齐新命名+外包优先+reading-honest+judge 两轴+auto-reread+report/ 一次性验证），先只 sm21、Sonnet + gpt-5.4-mini 两条 reading 并行。**本 run = Sonnet 那条，目的是压测 reading-honest + auto-reread 恢复链**（Sonnet 在 sm21 上历来过度分割，正好拿来验证"弱识图能不能被 judge 抓住 + 盲重读救回"）。配套问题：用户质疑"识图为何单拎出来更差"——本 run 的三次 ladder 是该诊断的一手证据（详 [plan.md N1d](../../../../../AI_agent/plan.md)）。
<!-- AGENT:END focus -->
<!-- AGENT:START diagnosis -->
## 错在哪儿 + 归因

因果链：**每次 attempt 的结构 linter（gate①）都过**（0_reading pass=58/flag=0/block=0）——结构合法掩盖不了语义错，这正是 J0 存在的理由。**J0（主控多模态）三次都抓到 1f 南带过度分割**：att1 `[E:judge:0_reading:001:c2]` + att2 `[E:judge:0_reading:002:c1]` 均 16 墙 / 10 内隔墙，且 stroke provenance 多为 `dimension_derived`（Sonnet 把尺寸链段界当墙的铁证）；att3 `[E:judge:0_reading:003:c1]` 加"存在性来自画出的墙线、不在尺寸段界造墙"通用纪律后骤降到 10 墙、2f 全对，但 1f 残留 x=3.44（南立面小窗左边）一道伪隔墙 → floor1 8 区。预算 3/3 用尽 → `[E:stop:quarantined@0_reading]`。**归因 = root_stage 0_reading（识图感知错），非 correction/内核**。**非回归非模型弱**：Sonnet 读干净过更复杂的 sm20（无家具平面），sm21 翻车是 case×model 杂物陷阱（家具+密尺寸链 × 弱 VLM），06-07 三模型实验即有记录。肉检对照见 `[E:eyeball:case_data_1f_view.png]`（原图满平面家具）vs `[E:eyeball:0_reading_1f_view_render.png]`（多切的南带）。
<!-- AGENT:END diagnosis -->
<!-- AGENT:START recommendations -->
## 建议


### 机制问题

- action: 机制侧无需修——auto-reread + reading-honest + judge 两轴 recoverability 全程正确：gate① 结构过、J0 抓存在性错并判 unrecoverable、盲重读启动、预算用尽如实 quarantine 而非放行假绿。reading-honest 的 `provenance` 字段把"dimension_derived"病因显形，是这轮能精确归因的关键。
  evidence: [E:judge:0_reading:001:c2] [E:judge:0_reading:003:c1] [E:stop:quarantined@0_reading]
  owner: 本项目（机制保持）

### 能力升级

- action: 弱 VLM 在密集 CAD（家具+尺寸链满布）平面上的识图能力是真瓶颈——同一 Sonnet 读无家具的 sm20 干净、读满家具的 sm21 过度分割。能力升级方向 = 让识图段对"杂物 vs 结构"鲁棒（训练/提示/预处理三选），列入识图→建模质量主线。
  evidence: [E:judge:0_reading:003:c1] [E:eyeball:case_data_1f_view.png]
  owner: 本项目（识图能力主线）

### 脚手架建议

- action: 加一条 gate① 或 J0 的确定性"过度分割 smell"预警——当 wall stroke 的 `provenance=dimension_derived` 比例过高、或平面 cell 数 > testdata thermal_zones 时自动 flag，把 J0 现在靠人眼抓的东西前移成廉价信号。
  evidence: [E:judge:0_reading:001:c2] [E:judge:0_reading:002:c1]
  owner: 本项目（src/validator + judge harness）

### 修法

- action: 喂图前做杂物/尺寸链图层掩膜或分区裁图（降低家具/tick 对弱模型的干扰），并把"存在性来自画出的墙线、绝不在尺寸段界造墙"写进 0_reading skill 的密集 CAD 负例（sm21 当教材）。att3 实证该纪律把 Sonnet 从 16 墙→10 墙、2f 全修对，方向已验证有效，仅差最后一道窗边混淆。
  evidence: [E:judge:0_reading:003:c1] [E:eyeball:0_reading_1f_view_render.png] [E:eyeball:case_data_1f_view.png]
  owner: 本项目（skills/intake_pipeline/0_reading + N1d）
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
- `E:judge:0_reading:002:c1` (judge; source `0_reading/attempts/002/judge.json`) — clutter traced as structure
- `E:judge:0_reading:002:c2` (judge; source `0_reading/attempts/002/judge.json`) — missed real element
- `E:judge:0_reading:002:c3` (judge; source `0_reading/attempts/002/judge.json`) — pen misclassified
- `E:judge:0_reading:002:c4` (judge; source `0_reading/attempts/002/judge.json`) — number copied wrong
- `E:judge:0_reading:002:c5` (judge; source `0_reading/attempts/002/judge.json`) — image-local orientation self-consistent
- `E:judge:0_reading:002:c6` (judge; source `0_reading/attempts/002/judge.json`) — door healing wrong
- `E:judge:0_reading:002:c7` (judge; source `0_reading/attempts/002/judge.json`) — whole-region missing / misplaced
- `E:judge:0_reading:003:c1` (judge; source `0_reading/attempts/003/judge.json`) — clutter traced as structure
- `E:judge:0_reading:003:c2` (judge; source `0_reading/attempts/003/judge.json`) — missed real element
- `E:judge:0_reading:003:c3` (judge; source `0_reading/attempts/003/judge.json`) — pen misclassified
- `E:judge:0_reading:003:c4` (judge; source `0_reading/attempts/003/judge.json`) — number copied wrong
- `E:judge:0_reading:003:c5` (judge; source `0_reading/attempts/003/judge.json`) — image-local orientation self-consistent
- `E:judge:0_reading:003:c6` (judge; source `0_reading/attempts/003/judge.json`) — door healing wrong
- `E:judge:0_reading:003:c7` (judge; source `0_reading/attempts/003/judge.json`) — whole-region missing / misplaced
- `E:stop:quarantined@0_reading` (stop; source `_run/orchestration_state.json`) — _run/orchestration_state.json
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
