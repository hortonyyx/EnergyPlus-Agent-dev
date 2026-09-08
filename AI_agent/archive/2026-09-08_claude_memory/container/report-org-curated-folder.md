---
name: report-org-curated-folder
description: "每 run 产单一策展 report/ 文件夹(用户只看这里);事实层(代码 FACTS.md)/叙事层(主控撰写 REPORT.md 含四桶建议)分离;主控跑完每 case 要填 REPORT.md 的 AGENT-FILL 槽+四桶、建议必挂 evidence_index 的 [E:..] 证据"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3db7ea1d-2b89-4365-91ff-7f8c9463d1a3
---

2026-06-23 `6.23_ReportOrgCuratedFolder`（commit a750eff，五审闭环 8→4→2→1→0）。主控汇报优化落地，**这是主控跑完每个 case 后的操作事实**：

- **`<run>/report/` = 用户唯一要看的地方**：`FACTS.md`(确定性事实卡，代码产) + `REPORT.md`(主控+judge 动态撰写) + `eyeball/`(2D 肉检图，代码汇拢)。3D viewer 留 `manual_review/`、REPORT 给指针。
- **record_baseline 只产骨架**：`REPORT.md` create-if-absent（不覆写主控已写的叙事，`--force-template` 才重置）。主控跑完要**填 REPORT.md 的 AGENT-FILL 槽**（一句话结论/本轮侧重点/错在哪+归因）+ **四桶建议**（机制问题/能力升级/脚手架建议/修法）。
- **建议有纪律**：每桶或写精确哨兵 `本 run 无可证据支持的建议`，或写 `- action: … / evidence: [E:..] / owner: …` 记录；**evidence 必引 `baseline.json.evidence_index` 里真实存在的 id**（坐标式：`E:gate:<view-key>:<check>` / `E:judge:<stage>:<attempt>:c<n>` / `E:corr:<kind>:<slug>` / `E:stop/ep/geom/eyeball`）。citation linter 纯词法卡，散文凑数会失败。
- **run_state 状态感知**：completed_clean / root_stopped / pending（复用 step_orchestrator 的 TERMINAL_STOP/ADVANCE_OK + PENDING + 几何 supersede）；stopped run 不发死链、不叫开不存在的 viewer。
- 代码在 `scripts/tool_scripts/report_assembly.py`（evidence_index/run_state/linter/collector/write_report_files）+ `record_baseline.py` 接线。RUN_REPORT.md 已原子迁移弃用。
- **坑**：committed sm21 baseline 的 gates 是旧检查套（reading-honest 06-22 加了 ~12 检查后未重录），evidence_index 来自 fresh——cosmetic 不一致，下次批次重录自愈。

**2026-06-23 续 `6.23_RunDirTidySingleReport`（commit 38a817a，Codex 审 APPROVE-WITH-CHANGES 6 findings 全采纳，测试→328）**——根目录收拾 + 单一报告：
- **机器记账迁 `<run>/_run/`**：orchestration_state/baseline/run_manifest/validation_manifest/geometry_approval 五件经新 `src/agent/execution/run_meta.py:run_meta_path()` 统一路由。**llm.yaml 留根**（输入配置）。根目录 = 纯文件夹 + llm.yaml。读这些机器件路径变了（`_run/baseline.json` 等）。
- **单一 `report/REPORT.md`**（FACTS.md 已删并入）：模型配置置顶 + GEN 生成区（事实卡/run_state/eyeball 索引/evidence_index）+ AGENT 撰写区（conclusion/focus/diagnosis/recommendations）。**marker 围栏 `<!-- GEN:START k -->`/`<!-- AGENT:START k -->`**：GEN 每跑刷新、AGENT 跨跑保留；畸形 marker（重复/嵌套/反序/未闭合）**fail-before-write**（`ReportMarkerError`）。主控只填 4 个 AGENT 区。
- citation linter 改吃**抽出的 AGENT:recommendations 区**（非扫整文档）；GEN 刷新后陈旧 evidence id → 失败点名。
- **wart**：2 个 legacy golden（sm20/run_2026-06-15、sm21/run_2026-06-16_opus）无编排账本→run_state=incomplete（未编造，待批次重录自愈）；run_state 纯从 orchestration_state.json 推、空账本=incomplete。

关联 [[pipeline-0-5-refactor-status]]、[[per-stage-validation-judge-architecture]]、[[reading-honest-judge-routing-architecture]]。操作手册见 AI_agent/guides/new_case_guide.md（已加 REPORT 撰写步）。
