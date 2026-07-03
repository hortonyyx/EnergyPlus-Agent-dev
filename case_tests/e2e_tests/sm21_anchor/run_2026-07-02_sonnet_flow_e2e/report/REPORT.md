<!-- GEN:START model_config -->
# sm21_anchor / run_2026-07-02_sonnet_flow_e2e REPORT

## 本次模型配置

- llm.yaml: [../llm.yaml](../llm.yaml)
- recorded: `2026-07-02`
- orchestrator: `claude-opus-4-8`
- 自动状态: `reading_evidence_debt`
- default: `deepseek-v4-pro`
- intake_correction: `deepseek-v4-pro`
- reading_syntax_valid: `True`
- reading_evidence_clean: `False`
- j0_semantic_clean: `True`
- pipeline_recovered: `False`
<!-- GEN:END model_config -->
<!-- GEN:START facts_card -->
## 事实卡

**结论**: ⚠️ reading evidence debt / EP Completed, 0 severe, 6 warn / 14区·100面·15窗

**数字权威**: [../_run/baseline.json](../_run/baseline.json) + 本 REPORT 的 GEN 区；AGENT 区为主控叙事/建议，citation linter 只约束建议证据 id。

### 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 0_reading | 79 | 8 | 0 | 21 |
| 1_correction | 8 | 0 | 0 | 5 |
| 2_modelling | 5 | 0 | 0 | 0 |
| 4_mep | 12 | 0 | 0 | 2 |
| 5_intakeoutput | 1 | 0 | 0 | 0 |
| downstream | 3 | 0 | 0 | 1 |

### 证据信号

| signal | value |
|---|---|
| reading_syntax_valid | `True` |
| reading_evidence_clean | `False` |
| j0_semantic_clean | `True` |
| pipeline_recovered | `False` |

### 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | awaiting_human_review | 1 |
| 1_correction | awaiting_human_review | 1 |
| 2_modelling | deterministic_pass | 1 |
| 3_split_pairing | awaiting_geometry_approval | 1 |
| 4_mep | deterministic_pass | 1 |
| 5_intakeoutput | deterministic_pass | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 1, '1_correction': 1, '2_modelling': 1, '3_split_pairing': 1, '4_mep': 1, '5_intakeoutput': 1}

**judge② verdicts**: 2 条（0 条 blocking；见各 attempts/NNN/judge.json）

### run_state

- status: `completed_clean`
- completed_clean: true
- ignored_pending: ['awaiting_geometry_approval@3_split_pairing']

### flags（不阻塞、供归因）
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.stroke_dimension_consistency] 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.stroke_dimension_consistency] 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing
- [0_reading::reading.dimension_chain_closure] dimension chain evidence is missing, incomplete, or non-closing

### 校正审计摘要

- sidecar: `1_correction/corrections.json` (ok)
- counts: corrections=34, conflicts=2, unsupported=0
- by_rule_id: {"centerline_exterior": 1, "deterministic_core.snap": 24, "dimchain_closure_C_right_1F": 1, "dimchain_closure_C_right_2F": 1, "dimchain_closure_C_top_1F": 1, "dimchain_closure_C_top_2F": 1, "north_facade_inversion": 1, "room_role_prior": 1, "stroke_vs_elevation_dimension": 1, "stroke_vs_elevation_dimension_2F": 1, "west_facade_inversion": 1}
- by_stage: {"A1": 3, "A2-detect": 6, "A3-resolve": 3, "core": 24}
<!-- GEN:END facts_card -->
<!-- AGENT:START conclusion -->
## 一句话结论

**CLEAN**——规范跑测流程 P1 落地后**首次在真实 run 上端到端跑通 `flow`**：三层叠加门（gate①→judge②→人工校验）逐段全走通、EP Completed 0 severe（14区/100面/15窗），冷启 Sonnet reading 抽到极佳样本（墙9/9·窗15/15·过度分割0，**超 sm21_pre 地板**）、correction/几何/MEP 零退化承载。**本轮最重要一件事 = 抓到 flow harness 首个真实 bug（F1：judge packet 首 pass gt-evidence 时序空）**——非运行结果错，是工具需修，正是「真跑一遍验 P1」的价值。

> 注：GEN 事实卡的自动状态 `reading_evidence_debt` 是证据门在完美 reading 上的**误报**（见 diagnosis），非真识图债。
<!-- AGENT:END conclusion -->
<!-- AGENT:START focus -->
## 本轮侧重点

这是**规范跑测流程 P1（单一 anchor-aware `flow` 编排）落地后，第一次在真实 run 上驱动它**——工具建好 + 410 单测过，但从没真跑过。测的是 P1 全机器：单一 `flow` verb（manifest-first 可续、退出码 0/10）· judge-in-the-loop（J0/J1 停点 → 看 packet → 写 StageVerdict → `judge` 提交 → 重跑续）· 三个人工校验开关全开（reading/correction/geometry）· gt 权威判卷 evidence（`score_vs_gt` + overlay 注入 judge packet）· durable 人工校验（`approve-review` 绑 accepted `output_hash`）· 几何确认门（`approve-geometry` 绑 digest）· 收尾 `--with-ep --record` 产 baseline + report。

**结论 = P1 主干全部按设计工作**：三层叠加门逐段停对了（J0 过→reading 人工校验停→J1 过→correction 人工校验停→几何门停→EP），人工校验签名 durable、几何门绑 digest、EP 落 `<run>/EP/EP_run/`、report 自动生成。**但真跑一遍暴露了一个单测没覆盖的端到端首 pass 时序 bug（F1）**——这正是为什么工具建好还得真跑。
<!-- AGENT:END focus -->
<!-- AGENT:START diagnosis -->
## 错在哪儿 + 归因

**⚠️ 归因混杂（关键）：reading 用的是 Sonnet 5（`claude-sonnet-5`），非 Sonnet 4.6。** 子代理经 Agent tool `model="sonnet"` 别名 spawn，解析到最新 Sonnet = Sonnet 5（~2026-06/07 上线）。而**所有历史 sm21 reading 实验（窗 4–11/15、退化调查、强/弱 prompt A/B、脚手架恢复验证）都是 Sonnet 4.6**（llm.yaml 显式 `claude-sonnet-4-6`）。∴ 本轮窗 **15/15**（历史 Sonnet 4.6 高方差从没到过）**很可能主要来自 4.6→5 的模型升级，不能干净归功于脚手架恢复**——两个变量同时变了。要隔离需补一轮 Sonnet 4.6（显式配）同图对照。

**管线侧：无错，全链路 CLEAN。** 因果链：冷启 Sonnet 5 reading 干净（J0 全 7 项 PASS，gt 对账墙9/9·窗15/15·过度分割0·0.0m 偏移，[E:judge:0_reading:001:c1] … [E:judge:0_reading:001:c7]）→ correction 零退化（J1 全 5 项 PASS，correction↔gt 同样 9/9·15/15·0.0m，[E:judge:1_correction:001:c1] … [E:judge:1_correction:001:c5]）→ 几何内核 0 issues（14区/100面/15窗，[E:geom:digest]）→ MEP/装配 gate① 0 block/flag → EP Completed 0 severe / 6 warn（[E:ep:result]）。走廊 y=3–5 两层跨层对齐（cross_floor reconcile 无需修）。

**8 个 0_reading flag 是良性诚实残差、非缺陷。** `dimension_chain_closure`（[E:gate:0_reading::1f_view:reading.dimension_chain_closure]）来自 C_top 总尺寸 15.0 vs 分段和 14.76（差 0.24m = 内隔墙厚未标注）+ C_bottom/C_right 无 overall 只有分段；`stroke_dimension_consistency`（[E:gate:0_reading::1f_view:reading.stroke_dimension_consistency]）来自 6 条墙坐标恰在尺寸链累加点。gt 对账证实这 9 条墙全是真实房间边界墙、0.0m 偏移，转录忠实（[E:judge:0_reading:001:c4] number-copied-wrong=PASS）→ 两 flag 在此为**假阳性**。**但它们把 run 自动状态判成 `reading_evidence_debt`**（reading_evidence_clean=False）——证据门无法区分「诚实的无-overall / 墙厚残差」与「真识图债」，在完美 reading 上误报（子代理已在 self_check 诚实标注，未编造尺寸文本）。

**工具侧：F1 flow harness 时序 bug（本轮真实发现，单测未覆盖）。** `_judge_gt_artifacts`（run_stage.py:496）从磁盘重 load manifest，但 `cmd_flow` 中当前段的 accept 只在 `run_one_stage` 返回后 `manifest.save`（run_stage.py:994）才落盘、**晚于 packet 构建** → 首 pass `rec is None`（or accepted_attempt 不匹配）→ judge packet 的 `score_vs_gt`/`overlay`/`score_criteria` **全空** → judge 首轮（正是判卷那轮）拿不到 Batch B 的 gt 对账主判据，静默架空「gt 权威判卷 evidence」设计。J0/J1 双复现；删 sidecar 后二 pass 因 accept 已落盘而自愈。本 run 靠二 pass 拿正确 packet 完成判卷，结论未受影响，但工具须修（见修法）。
<!-- AGENT:END diagnosis -->
<!-- AGENT:START recommendations -->
## 建议


### 机制问题

本 run 无可证据支持的建议

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

- action: 证据门 dimension_chain_closure 在「无 overall 只有分段」或「分段和 vs overall 差 ≈ 内隔墙厚(0.24m)」两情形应结合 stroke 内部自洽降权，避免把完美 reading(本 run 实为墙9/9·窗15/15·0.0m 偏移)误判成 reading_evidence_debt 自动状态
  evidence: [E:gate:0_reading::1f_view:reading.dimension_chain_closure] [E:judge:0_reading:001:c4]
  owner: reading/validator（宜并 Phase B 双通道 schema 一起解，届时 overall 缺失/墙厚残差有正规通道）

### 修法

> note: F1（flow harness bug，本轮真跑发现，无 pipeline evidence id 故不入 action）：judge packet 首 pass 的 gt-evidence（score_vs_gt/overlay/score_criteria）全空——`_judge_gt_artifacts`(run_stage.py:496) 从磁盘重 load manifest，但 cmd_flow 中当前段 accept 在 run_one_stage 返回后 manifest.save(run_stage.py:994) 才落盘、晚于 packet 构建 → 首 pass rec is None。J0/J1 双复现、二 pass 自愈。修向：run_one_stage 内 accept 后即持久化 / 或把 in-memory manifest 传进 _judge_gt_artifacts 不重 load；补「端到端首-pass judge packet 内容」测试。走 Codex 执行。已带进 plan.md N2b backlog + memory。
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
16. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
17. flag [0_reading::reading.stroke_dimension_consistency] —— 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall（对应渲染件人工核一眼）
18. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
19. flag [0_reading::reading.stroke_dimension_consistency] —— 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall（对应渲染件人工核一眼）
20. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
21. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
22. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
23. flag [0_reading::reading.dimension_chain_closure] —— dimension chain evidence is missing, incomplete, or non-closing（对应渲染件人工核一眼）
24. audit-derived [corrections_summary] —— `corrections.json` 有 2 conflicts / 0 unsupported，人核看错↔改错归因

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
- reading evidence debt: [../1_correction/evidence_debt.json](../1_correction/evidence_debt.json)
- correction audit: [../1_correction/corrections.json](../1_correction/corrections.json)
- judge verdict log: [../verdicts/](../verdicts/)
- geometry_digest: `f683752da9ddf2e4ae11666d81ed91e35ccd0bf6e2dfd073736f736adff4e34c`

### evidence_index
- `E:gate:0_reading::1f_view:reading.dimension_chain_closure` (gate; source `0_reading::1f_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::1f_view:reading.stroke_dimension_consistency` (gate; source `0_reading::1f_view`) — 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall
- `E:gate:0_reading::2f_view:reading.dimension_chain_closure` (gate; source `0_reading::2f_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::2f_view:reading.stroke_dimension_consistency` (gate; source `0_reading::2f_view`) — 6 plan wall stroke coordinate(s) coincide with dimension-chain cumulative positions; verify each is a real room-bounding wall
- `E:gate:0_reading::East_view:reading.dimension_chain_closure` (gate; source `0_reading::East_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::North_view:reading.dimension_chain_closure` (gate; source `0_reading::North_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::South_view:reading.dimension_chain_closure` (gate; source `0_reading::South_view`) — dimension chain evidence is missing, incomplete, or non-closing
- `E:gate:0_reading::West_view:reading.dimension_chain_closure` (gate; source `0_reading::West_view`) — dimension chain evidence is missing, incomplete, or non-closing
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
- `E:debt:1f_view_reading.dimension_chain_closure_1` (evidence_debt; source `1_correction/evidence_debt.json`) — 1f_view.reading.dimension_chain_closure
- `E:debt:2f_view_reading.dimension_chain_closure_2` (evidence_debt; source `1_correction/evidence_debt.json`) — 2f_view.reading.dimension_chain_closure
- `E:debt:East_view_reading.dimension_chain_closure_3` (evidence_debt; source `1_correction/evidence_debt.json`) — East_view.reading.dimension_chain_closure
- `E:debt:North_view_reading.dimension_chain_closure_4` (evidence_debt; source `1_correction/evidence_debt.json`) — North_view.reading.dimension_chain_closure
- `E:debt:South_view_reading.dimension_chain_closure_5` (evidence_debt; source `1_correction/evidence_debt.json`) — South_view.reading.dimension_chain_closure
- `E:debt:West_view_reading.dimension_chain_closure_6` (evidence_debt; source `1_correction/evidence_debt.json`) — West_view.reading.dimension_chain_closure
- `E:corr:corrections:C1` (correction; source `1_correction/corrections.json`) — C1
- `E:corr:corrections:C2` (correction; source `1_correction/corrections.json`) — C2
- `E:corr:corrections:C3` (correction; source `1_correction/corrections.json`) — C3
- `E:corr:corrections:C4` (correction; source `1_correction/corrections.json`) — C4
- `E:corr:corrections:C5` (correction; source `1_correction/corrections.json`) — C5
- `E:corr:corrections:C6` (correction; source `1_correction/corrections.json`) — C6
- `E:corr:corrections:C7` (correction; source `1_correction/corrections.json`) — C7
- `E:corr:corrections:C8` (correction; source `1_correction/corrections.json`) — C8
- `E:corr:corrections:C9` (correction; source `1_correction/corrections.json`) — C9
- `E:corr:corrections:C10` (correction; source `1_correction/corrections.json`) — C10
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
- `E:corr:conflicts:CONF1` (correction; source `1_correction/corrections.json`) — CONF1
- `E:corr:conflicts:CONF2` (correction; source `1_correction/corrections.json`) — CONF2
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
