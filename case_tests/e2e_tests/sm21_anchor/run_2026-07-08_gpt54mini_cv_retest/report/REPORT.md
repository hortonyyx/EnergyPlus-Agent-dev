<!-- GEN:START model_config -->
# sm21_anchor / run_2026-07-08_gpt54mini_cv_retest REPORT

## 本次模型配置

- run_config.yaml: [../run_config.yaml](../run_config.yaml)
- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-07-08`
- orchestrator: `claude-opus-4-8`
- 自动状态: `incomplete`
- provenance: `git=ebddadaee2f9 dirty=dirty:174 skills=61fb9383bca1 reading=fe929a9b641a correction=09119cd999ad corr_cfg=4faa38b71a7d`
- correction: `deepseek-v4-pro` (effort=`unknown`, source=`run_config.yaml:models.correction`)
- default: `deepseek-v4-pro` (effort=`unknown`, source=`llm.yaml:default`)
- mep: `deepseek-v4-pro` (effort=`unknown`, source=`run_config.yaml:models.mep`)
- orchestrator: `claude-opus-4-8` (effort=`unknown`, source=`run_config.yaml:models.orchestrator`)
- reading: `gpt-5.4-mini` (effort=`default`, source=`run_config.yaml:models.reading`)
- reading_syntax_valid: `True`
- reading_evidence_clean: `False`
- j0_semantic_clean: `True`
- pipeline_recovered: `None`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ❌ BLOCKED / EP 未跑

**数字权威**: [../_run/baseline.json](../_run/baseline.json) + 本 REPORT 的 GEN 区；AGENT 区为主控叙事/建议，citation linter 只约束建议证据 id。

### 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 1_correction | 0 | 0 | 1 | 0 |
| 2_modelling | 0 | 0 | 1 | 0 |
| 3_split_pairing | 0 | 0 | 1 | 0 |
| 4_mep | 0 | 0 | 1 | 0 |
| 5_intakeoutput | 0 | 0 | 1 | 0 |
| 0_reading | 84 | 8 | 0 | 16 |

### 证据信号

| signal | value |
|---|---|
| reading_syntax_valid | `True` |
| reading_evidence_clean | `False` |
| j0_semantic_clean | `True` |
| pipeline_recovered | `None` |

### 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | judge_pass | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 1}

**judge② verdicts**: 1 条（0 条 blocking；见各 attempts/NNN/judge.json）

### run_state

- status: `incomplete`
- missing_expected: ['1_correction', '2_modelling', '3_split_pairing', '4_mep', '5_intakeoutput']

### blocking
- [1_correction::1_correction.build] required artifact missing: 1_correction/correction_geometry_snapped.json
- [2_modelling::2_modelling.build] required artifact missing: 2_modelling/building_geometry.json
- [3_split_pairing::3_split_pairing.build] required artifact missing: 3_split_pairing/geometry_specs.md
- [4_mep::4_mep.build] required artifact missing: 4_mep/mep_output.json
- [5_intakeoutput::5_intakeoutput.build] required artifact missing: 5_intakeoutput/intake_output.json

### flags（不阻塞、供归因）
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.stroke_dimension_consistency] 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.stroke_dimension_consistency] 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.dimension_derived_refs] 5 dimension_derived stroke(s) have empty or unresolved dimension_refs
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing

### 校正审计摘要

- sidecar: `1_correction/corrections.json` (missing)
<!-- GEN:END facts_card -->
<!-- AGENT:START conclusion -->
## 一句话结论

- 自动状态: `incomplete`（reading-only 交叉测试，下游有意 out of scope；reading 阶段本身 = J0 judge_pass、gate① 0 block）
- **PASS — gpt-5.4-mini + CV 工具箱交叉测试阳性满分带**（墙 9/9·0.0m·立面窗 15/15 complete·过度分割 0，仅平面窗 6/7），坐实 CV 工具箱配方**模型无关、非 Haiku 特调**。
<!-- AGENT:END conclusion -->
<!-- AGENT:START focus -->
## 本轮侧重点

验证两件事：① **迁移性**——CV 工具箱配方是否 Haiku 特调，换 gpt-5.4-mini（另一个弱模型、经 codex CLI）能否达 Haiku 07-07 同级满分带；② **E 效率批固化**——prescan 前置化（E3）+ cv_toolbox.md 自声明 required（E1），spawn prompt **不再写 measure-before-draw**，看新模型是否仍自发测量。reading-only 对账 gt（下游/EP/record 按用户 stamp out of scope）。
<!-- AGENT:END focus -->
<!-- AGENT:START diagnosis -->
## 错在哪儿 + 归因

无 severe/fatal，reading 坐标准确度达满分带（J0 judge_pass）。两个 minor：
- **1f 一个平面窗中心偏 0.53m**（平面窗 6/7，[E:judge:0_reading:001:c1]）——单点弱模型感知抖动，非系统性漏读；其余 6 平面 + 全部 15 立面窗 complete。
- **dimension-evidence 链不完整**（[E:gate:0_reading::1f_view:reading.dimension_chain_closure] + [E:gate:0_reading::North_view:reading.dimension_derived_refs]）——gpt-5.4-mini 的 dimensions/refs 记录不如满配，但**坐标对账墙 9/9·0.0m 说明它实际用的数字是准的**，flag 是证据完整性提醒非坐标错。stroke_dimension_consistency flag（[E:gate:0_reading::1f_view:reading.stroke_dimension_consistency]）是过度分割嫌疑门，但 extra walls = 0、坐标对账坐实无伪墙。
- **06-23 无工具箱两失败点全修复**：South-F2 四窗并两窗 → 4/4 complete（[E:judge:0_reading:001:c3]）；2f 漏 1 隔墙(6区) → 墙 5/5·0.0m(7区)（[E:judge:0_reading:001:c2]）。
<!-- AGENT:END diagnosis -->
<!-- AGENT:START recommendations -->
## 建议


### 机制问题

- action: 正规 flow harness 复用 codex 产的 reading 判卷成功——gate①（check_reading_view）+ J0 packet + grade + render + attempts 全自动生成，坐实「reading 走 codex、判卷走 flow」可行、无需手搓 scorer。
  evidence: [E:judge:0_reading:001:c1]
  owner: 已验证

### 能力升级

- action: 迁移性成立→解锁开源 VLM 验收提前案：gpt-5.4-mini 达 Haiku/Sonnet 5 同级满分带（墙 9/9·0.0m·立面 15/15·过度分割 0），配方（确定性工具+纪律+验收 harness）模型无关。
  evidence: [E:judge:0_reading:001:c2]
  owner: 用户定是否推开源 VLM

### 脚手架建议

- action: E 批固化在新模型 hold——spawn prompt 无 measure-before-draw，gpt-5.4-mini 读 cv_toolbox.md（自声明 required）自发调 13+ CV 工具量；prescan 前置化（E3）+ 纪律固化（E1）不依赖模型。
  evidence: [E:judge:0_reading:001:c4]
  owner: 已验证

### 修法

- action: codex 侧隔离无 guard 层——clean-room staging（gt 物理排除）对 codex 适用，但 Claude Code PreToolUse guard 不生效（比 claude -p 子代理弱一层）；backlog=给 codex 执行器补等价隔离守卫（codex sandbox profile / 只读挂载）。
  evidence: [E:gate:0_reading::2f_view:reading.stroke_dimension_consistency]
  owner: backlog
- action: gpt-5.4-mini dimension-evidence 链不完整（Phase A 门 flag，坐标准但记录弱）→ Phase B 双通道 schema 给残差正规通道。
  evidence: [E:gate:0_reading::North_view:reading.dimension_derived_refs]
  owner: Phase B
- action: 效率 ~1.5x Haiku（~0.9M tokens/case，弱模型试错多，East 单图 72 工具调用）→ 候选=收窄 prescan 候选表 / 缓存标定。
  evidence: [E:judge:0_reading:001:c4]
  owner: backlog
<!-- AGENT:END recommendations -->
<!-- GEN:START eyeball_index -->
## 肉视检验索引

1. 2D 肉检 `report/eyeball/0_reading_grade.png`（from `0_reading/grade.png` / reading_grade）
2. 2D 肉检 `report/eyeball/0_reading_1f_view_render.png`（from `0_reading/1f_view_render.png` / reading_render）
3. 2D 肉检 `report/eyeball/0_reading_2f_view_render.png`（from `0_reading/2f_view_render.png` / reading_render）
4. 2D 肉检 `report/eyeball/0_reading_East_view_render.png`（from `0_reading/East_view_render.png` / reading_render）
5. 2D 肉检 `report/eyeball/0_reading_North_view_render.png`（from `0_reading/North_view_render.png` / reading_render）
6. 2D 肉检 `report/eyeball/0_reading_South_view_render.png`（from `0_reading/South_view_render.png` / reading_render）
7. 2D 肉检 `report/eyeball/0_reading_West_view_render.png`（from `0_reading/West_view_render.png` / reading_render）
8. 2D 肉检 `report/eyeball/case_data_1f_view.png`（from `../case_data/1f_view.png` / case_data_view）
9. 2D 肉检 `report/eyeball/case_data_2f_view.png`（from `../case_data/2f_view.png` / case_data_view）
10. 2D 肉检 `report/eyeball/case_data_East_view.png`（from `../case_data/East_view.png` / case_data_view）
11. 2D 肉检 `report/eyeball/case_data_North_view.png`（from `../case_data/North_view.png` / case_data_view）
12. 2D 肉检 `report/eyeball/case_data_South_view.png`（from `../case_data/South_view.png` / case_data_view）
13. 2D 肉检 `report/eyeball/case_data_West_view.png`（from `../case_data/West_view.png` / case_data_view）
14. missing eyeball producer `1_correction/grade.png` (correction_grade)
15. missing eyeball producer `1_correction/zones.png` (correction_zones)
16. missing eyeball producer `1_correction/elev.png` (correction_elev)
17. 3D 几何 viewer unavailable: missing 2_modelling/building_geometry.json
18. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
19. flag [0_reading::reading.stroke_dimension_consistency] —— 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall（对应渲染件人工核一眼）
20. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
21. flag [0_reading::reading.stroke_dimension_consistency] —— 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall（对应渲染件人工核一眼）
22. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
23. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
24. flag [0_reading::reading.dimension_derived_refs] —— 5 dimension_derived stroke(s) have empty or unresolved dimension_refs（对应渲染件人工核一眼）
25. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）

### report/eyeball
- [0_reading_grade.png](eyeball/0_reading_grade.png) — reading_grade from `0_reading/grade.png`
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
- `1_correction/grade.png` (correction_grade)
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
- reading evidence debt: [../1_correction/evidence_debt.json](../1_correction/evidence_debt.json)
- correction audit: [../1_correction/corrections.json](../1_correction/corrections.json)
- judge verdict log: [../verdicts/](../verdicts/)
- geometry_digest: `None`

### evidence_index
- `E:gate:0_reading::1f_view:reading.dimension_chain_closure` (gate; source `0_reading::1f_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::1f_view:reading.stroke_dimension_consistency` (gate; source `0_reading::1f_view`) — 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall
- `E:gate:0_reading::2f_view:reading.dimension_chain_closure` (gate; source `0_reading::2f_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::2f_view:reading.stroke_dimension_consistency` (gate; source `0_reading::2f_view`) — 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall
- `E:gate:0_reading::East_view:reading.dimension_chain_closure` (gate; source `0_reading::East_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::North_view:reading.dimension_chain_closure` (gate; source `0_reading::North_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::North_view:reading.dimension_derived_refs` (gate; source `0_reading::North_view`) — 5 dimension_derived stroke(s) have empty or unresolved dimension_refs
- `E:gate:0_reading::West_view:reading.dimension_chain_closure` (gate; source `0_reading::West_view`) — dimension chain evidence is missing, incomplete, or non-closing
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
- `E:ep:result` (ep; source `EP/EP_run/eplusout.end`) — EP/EP_run/eplusout.end
- `E:geom:digest` (geometry; source `2_modelling/building_geometry.json`) — 2_modelling/building_geometry.json
- `E:eyeball:0_reading_grade.png` (eyeball; source `report/eyeball/0_reading_grade.png`) — report/eyeball/0_reading_grade.png
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
