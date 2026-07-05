# 审阅：AI_agent 管理文档重构（2026-06-20，Codex MCP 直审）

**Reviewer**：Codex（gpt-5.x，`mcp__codex__codex` danger-full-access，自主读文件 + 跑 pytest）
**Request**：[../request/2026-06-20_management_docs_restructure_request.md](../request/2026-06-20_management_docs_restructure_request.md)

## Verdict：CHANGES REQUESTED → **逐条处置后 CLOSEABLE**

无 High。Codex 跑 `python -m pytest -q` = **274 passed**；分支/commit 与 CLAUDE.md 一致（`6.15_ValidationArchM0toM4` / `41558e1`）；
decision_log.md 完整承接旧 CLAUDE.md §5.1–5.13 + 两份 changelog（diff 仅为预期的移动路径改写）；281 个活文档相对链接扫描，
非豁免缺失仅下列 Low；gt / LLM-vs-code / IntakeOutput 不变量与代码一致。

## Findings + 处置

| # | 级别 | 问题 | 处置 |
|---|---|---|---|
| M1 | Medium | CLAUDE.md 关键路径表把 `intakeoutput.py` 列在 `src/agent/geometry/` 下，实际在 `src/agent/intakeoutput.py` | ✅ 已修：geometry 行去掉 `intakeoutput.py`，单列一行 `../src/agent/intakeoutput.py`（5_intakeoutput 装配+契约）|
| L1 | Low | floorplan_redraw_strategy.md:240 链到不存在的 `skills/intake_pipeline/phase1_prompt_template.md` | ✅ 已修：retarget 到 `0_reading/guide.md` |
| L2 | Low | decision_log.md §B 引言重复两行，第二行用 stale `test_baseline/runs/` 措辞 | ✅ 已修：删重复行，保留 `backup/tests_history/test_baseline_runs/` 版 |

**有意保留**（Codex 认可）：floorplan_redraw_strategy.md 中 2 处对已退役 `skills/energyplus_mcp/` 的引用 = POC 史叙述，非当前指针，保留作历史语境。

## 结论
3 条全修，pytest 274 绿不受影响（纯文档）。restructure CLOSEABLE。
