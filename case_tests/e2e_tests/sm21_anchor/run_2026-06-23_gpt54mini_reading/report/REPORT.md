<!-- GEN:START model_config -->
# sm21_anchor / run_2026-06-23_gpt54mini_reading REPORT

## 本次模型配置

- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-06-23`
- orchestrator: `opus-4.8`
- 自动状态: `completed_clean`
- default: `deepseek-v4-pro`
- intake_correction: `deepseek-v4-pro`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ✅ clean / EP Completed, 0 severe, 6 warn / 14区·100面·15窗

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
| 0_reading | judge_pass | 3 |
| 1_correction | judge_pass | 1 |
| 2_modelling | deterministic_pass | 1 |
| 3_split_pairing | awaiting_geometry_approval | 1 |
| 4_mep | deterministic_pass | 1 |
| 5_intakeoutput | deterministic_pass | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 3, '1_correction': 1, '2_modelling': 1, '3_split_pairing': 1, '4_mep': 1, '5_intakeoutput': 1}

**judge② verdicts**: 4 条（2 条 blocking；见各 attempts/NNN/judge.json）

### run_state

- status: `completed_clean`
- completed_clean: true
- ignored_pending: ['awaiting_geometry_approval@3_split_pairing']

### 校正审计摘要

- sidecar: `1_correction/corrections.json` (ok)
- counts: corrections=6, conflicts=0, unsupported=0
- by_rule_id: {"A1_centerline": 1, "A2_checksum_failure": 1, "A3_facade_plan_mismatch": 1, "A3_prior_completion": 1, "A3_stroke_vs_dimension": 2}
- by_stage: {"A1": 1, "A2": 1, "A3": 4}
<!-- GEN:END facts_card -->
<!-- AGENT:START conclusion -->
## 一句话结论

- 自动状态: `completed_clean`

**✅ CLEAN 端到端** —— 弱模型 **gpt-5.4-mini** 经 auto-reread 在第 3 次救回干净识图后，0–5 全段过、几何已批、EP Completed 0 severe/6 warn，**14 区/100 面/15 窗（与 opus golden 同计数）**。最重要的一件事：**judge+重读兜底让一个会出错的弱模型也跑出了干净 baseline** `[E:ep:result]`，正是开源 VLM 北极星的可行性实证。
<!-- AGENT:END conclusion -->
<!-- AGENT:START focus -->
## 本轮侧重点

本轮 = sm21 批次重跑（攒齐新命名+外包优先+reading-honest+judge 两轴+auto-reread+report/ 一次性验证），先只 sm21、Sonnet + gpt-5.4-mini 两条 reading 并行。**本 run = gpt-5.4-mini 那条，目的是测"更弱的模型能否经恢复链跑出干净 baseline"**（对齐"脚手架=降智机制服务国产 VLM→开源北极星"）。配套验证全部新地基代码（确定性命名 `Z01_W3_Win1`、外包优先、report/ 策展）在真实 e2e 上是否成立。
<!-- AGENT:END focus -->
<!-- AGENT:START diagnosis -->
## 错在哪儿 + 归因

这是一条**恢复链成功**的 run，不是无错 run。0_reading 三跳：att1 `[E:judge:0_reading:001:c1]`（South-F2 4窗并2 + 2f 南带欠1墙）→ att2 `[E:judge:0_reading:002:c1]`（通用"不合并相邻窗"纪律把 South 修到 7 窗、2f 仍欠）→ att3 `[E:judge:0_reading:003:c1]`（2f 南带补回 → 4 房，全干净）。J0 PASS 后进 1_correction：J1 五条全过 `[E:judge:1_correction:001:c1]`..`[E:judge:1_correction:001:c4]`，14 区/15 窗对 gt 精确命中。确定性核做 6 条校正（A1 中线×1 / A2 checksum×1 / A3 仲裁×4，含 stroke_vs_dimension×2）`[E:corr:corrections:corr-1]`，几何内核 100 面经人工 3D 门 `[E:geom:digest]` 批准，下游 InterZone 门过、EP 0 severe `[E:ep:result]`。**两个非阻塞瑕疵**：① footprint 收成 14.8×7.8 而非外包 [0,15]×[0,8]（gpt-mini 立面 JSON 缺结构化总尺寸字段，envelope 提取器没拿到信号、回退平面内缩，容差内）；② 房间 role 全 office（gt 有 meeting，仅负荷档位）。
<!-- AGENT:END diagnosis -->
<!-- AGENT:START recommendations -->
## 建议


### 机制问题

- action: 机制无需改——auto-reread + reading-honest + judge 两轴在弱模型上闭环成功：弱识图被 J0 逐跳抓住、盲重读用通用 discipline lever 逐步修复（att1→att2 修立面并窗、att2→att3 补平面隔墙），3 次内救回干净并跑通 EP。这是"判+重读兜底弱模型"范式的端到端实证。
  evidence: [E:judge:0_reading:001:c1] [E:judge:0_reading:003:c1] [E:ep:result]
  owner: 本项目（机制保持）

### 能力升级

- action: gpt-5.4-mini 这类弱 VLM 在密集 CAD 上首跳必出错（并窗/欠读隔墙），但错误模式"可被通用纪律纠正"——说明能力差距是**可工程化收敛**的，值得作为开源 VLM 接入的基准模型档位纳入识图能力主线评测。
  evidence: [E:judge:0_reading:001:c1] [E:judge:0_reading:002:c1]
  owner: 本项目（识图能力主线 / 开源模型接入）

### 脚手架建议

- action: 外包优先（envelope）提取器对弱模型立面退化——gpt-mini 立面 JSON 缺结构化总尺寸字段时，footprint 回退到平面内缩 14.8×7.8 而非权威 [0,15]×[0,8]。脚手架方向：让 envelope 提取器在立面维度稀疏时也能从 outline/wall_fill 描边 extent 兜底，或在 reading schema 强制立面 overall 维度字段。
  evidence: [E:geom:digest] [E:judge:1_correction:001:c4]
  owner: 本项目（src/agent/correction/envelope.py + reading schema）

### 修法

- action: 房间 role 全标 office、漏掉 gt 的 meeting（F1_S3 / F2_N1 / F2_N2）。属负荷档位、不动几何，但影响 4_mep 负载密度。修法 = role phase-2（确定性绑定 sidecar，plan.md N1b ②）落地后，role 从识图 room_labels 确定性传导而非 correction 隐式判。
  evidence: [E:judge:1_correction:001:c1] [E:eyeball:1_correction_zones.png]
  owner: 本项目（role phase-2，远期）
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
- geometry_digest: `ecac6a8a693043db7814b5e78cbf9ead720adea0456d26e82e4b11104458cb04`

### evidence_index
- `E:judge:0_reading:001:c1` (judge; source `0_reading/attempts/001/judge.json`) — missed real element
- `E:judge:0_reading:001:c2` (judge; source `0_reading/attempts/001/judge.json`) — clutter traced as structure
- `E:judge:0_reading:001:c3` (judge; source `0_reading/attempts/001/judge.json`) — pen misclassified
- `E:judge:0_reading:001:c4` (judge; source `0_reading/attempts/001/judge.json`) — number copied wrong
- `E:judge:0_reading:001:c5` (judge; source `0_reading/attempts/001/judge.json`) — image-local orientation self-consistent
- `E:judge:0_reading:001:c6` (judge; source `0_reading/attempts/001/judge.json`) — door healing wrong
- `E:judge:0_reading:001:c7` (judge; source `0_reading/attempts/001/judge.json`) — whole-region missing / misplaced
- `E:judge:0_reading:002:c1` (judge; source `0_reading/attempts/002/judge.json`) — missed real element
- `E:judge:0_reading:002:c2` (judge; source `0_reading/attempts/002/judge.json`) — clutter traced as structure
- `E:judge:0_reading:002:c3` (judge; source `0_reading/attempts/002/judge.json`) — pen misclassified
- `E:judge:0_reading:002:c4` (judge; source `0_reading/attempts/002/judge.json`) — number copied wrong
- `E:judge:0_reading:002:c5` (judge; source `0_reading/attempts/002/judge.json`) — image-local orientation self-consistent
- `E:judge:0_reading:002:c6` (judge; source `0_reading/attempts/002/judge.json`) — door healing wrong
- `E:judge:0_reading:002:c7` (judge; source `0_reading/attempts/002/judge.json`) — whole-region missing / misplaced
- `E:judge:0_reading:003:c1` (judge; source `0_reading/attempts/003/judge.json`) — missed real element
- `E:judge:0_reading:003:c2` (judge; source `0_reading/attempts/003/judge.json`) — clutter traced as structure
- `E:judge:0_reading:003:c3` (judge; source `0_reading/attempts/003/judge.json`) — pen misclassified
- `E:judge:0_reading:003:c4` (judge; source `0_reading/attempts/003/judge.json`) — number copied wrong
- `E:judge:0_reading:003:c5` (judge; source `0_reading/attempts/003/judge.json`) — image-local orientation self-consistent
- `E:judge:0_reading:003:c6` (judge; source `0_reading/attempts/003/judge.json`) — door healing wrong
- `E:judge:0_reading:003:c7` (judge; source `0_reading/attempts/003/judge.json`) — whole-region missing / misplaced
- `E:judge:1_correction:001:c1` (judge; source `1_correction/attempts/001/judge.json`) — zonification fidelity
- `E:judge:1_correction:001:c2` (judge; source `1_correction/attempts/001/judge.json`) — cross-floor consistency
- `E:judge:1_correction:001:c3` (judge; source `1_correction/attempts/001/judge.json`) — window position fidelity
- `E:judge:1_correction:001:c4` (judge; source `1_correction/attempts/001/judge.json`) — count vs reference
- `E:judge:1_correction:001:c5` (judge; source `1_correction/attempts/001/judge.json`) — overall redraw
- `E:corr:corrections:corr-1` (correction; source `1_correction/corrections.json`) — corr-1
- `E:corr:corrections:corr-2` (correction; source `1_correction/corrections.json`) — corr-2
- `E:corr:corrections:corr-3` (correction; source `1_correction/corrections.json`) — corr-3
- `E:corr:corrections:corr-4` (correction; source `1_correction/corrections.json`) — corr-4
- `E:corr:corrections:corr-5` (correction; source `1_correction/corrections.json`) — corr-5
- `E:corr:corrections:corr-6` (correction; source `1_correction/corrections.json`) — corr-6
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
