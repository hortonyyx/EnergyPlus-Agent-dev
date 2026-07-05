# Review request — 逐段 judge-in-the-loop 编排（backlog #1）

- **Date**: 2026-06-19
- **Branch**: 6.15_ValidationArchM0toM4
- **Reviewer**: Codex (gpt-5.2-codex), via MCP direct call (read-only/self-driven) — 试点新 §6.14
- **Author**: Opus 4.8 (主开发 Agent)

## 背景
之前的 baseline 是「整链 run_full_pipeline 跑完 → 事后 validate_case + 统一 judge」（务实 v1）。
用户要的是 new_case_guide §2 的**理想态**：逐子环节都有 judge 的一份报告，反复不过就停（按
§1.3 失败分类），judge 过才继续；几何步骤要人工确认后才继续；全跑完或中途停后出总报告。
本次把它落地。

## 改动范围（只审这批，diff 已清成只剩本次）
- **新增** `src/agent/execution/step_orchestrator.py` — 逐段编排状态机核心：
  `run_one_stage`（draw + gate① + 段内盲重抽 ≤ 预算 → 停在某状态）/ `submit_verdict`（收 Agent 的
  StageVerdict → 分类）/ `approve_geometry`/`geometry_is_approved` / `update_state`+`orchestration_state.json`。
- **新增** `scripts/tool_scripts/run_stage.py` — 逐段 CLI（verbs run/judge/resample/approve-geometry/
  status），接真执行器（run_correction/materialize_kernel_geometry/run_mep/assemble）+ gate① checks +
  渲染 + judge packet + 几何阻塞门。
- **改** `src/agent/execution/__init__.py` — 导出新原语。
- **改** `scripts/tool_scripts/record_baseline.py` — 总报告纳入 stop_reason + 逐段编排状态 + verdict 计数。
- **改** `AI_agent/guides/new_case_guide.md §2` — 重写为逐段驱动流程。
- **新增** `tests/test_step_orchestrator.py` — 18 条（全假 draw/judge）。

## 关注点（请重点审）
1. **失败分类正确性**（contracts §0.3 / guide §1.3）：deterministic gate①-block 必须 fail-closed
   不重抽（不弹上游）；manual(0_reading) 阻塞 = human_redraw；stochastic 盲重抽 ≤ 预算耗尽 quarantine；
   judge blocking 可路由→resample / 不可归因→交人。有没有错配？
2. **盲重抽铁律**（invariant 6）：重抽 loop 是否真的从不把 judge 评语/feedback 注入 draw prompt？
3. **预算磁盘派生**：per-stage ≤3 是否在跨 CLI 调用（gate①-block 重抽 + judge-block 重抽）下共用同一井、
   不会被绕过或重复计数？边界（正好 3）对不对？
4. **几何阻塞门**：ConfirmationPolicy.REQUIRED 下 `run 4_mep` 是否在**画之前**就拒；approval 绑 digest，
   几何漂移后是否自动失效（fail-closed）？approve_geometry 经 validate_case 取 digest 是否会误绑陈旧/不一致字节？
5. **不污染 / 不越界**：是否动了 `IntakeOutput` 契约 / `run_pipeline` / 下游 9 subagent？（应零改动）
   gt 是否仅在 judge packet 路径出现、gate①/执行器未 import？
6. **CLI 真执行器接线**：run_stage 各 stage 的 executor + gate① 接线是否与 run_pipeline 语义一致
   （snapped geom 路径、used_constructions、zone_names、契约 backstop）？有没有会静默吞错/伪 PASS 的地方？
7. 一般 correctness / 资源 / 边界 bug。

## 验收标准
- High/Medium/Low 分级 findings + 证据（文件:行）+ 建议修复。
- 全套测试：`python -m pytest -q`（作者侧已 234 绿）。
- verdict：CLOSEABLE / CHANGES REQUESTED。
