# Review — 逐段 judge-in-the-loop 编排（backlog #1）

- **Date**: 2026-06-19
- **Reviewer**: Codex (default model, ChatGPT account), via MCP direct call — `sandbox=danger-full-access`,
  自主读文件 + 跑 pytest（试点新 §6.14：MCP 直连 + 落盘）
- **Request**: [2026-06-19_stepwise_judge_in_the_loop_request.md](../request/2026-06-19_stepwise_judge_in_the_loop_request.md)
- **Tests**: Codex 跑 `python -m pytest -q` → `234 passed in 45.63s`
- **环境注记**: Codex 自带 bwrap 沙箱（read-only/workspace-write）在 dev container 内无法嵌套命名空间，
  只有 `danger-full-access` 能让它真正执行命令；该模式经用户显式授权后调用。Codex 全程只读未改源码（git 核验）。

---

## VERDICT: CHANGES REQUESTED

Tests run: `python -m pytest -q` passed, `234 passed in 45.63s`.

**High**
- `src/agent/execution/step_orchestrator.py:302`, `scripts/tool_scripts/run_stage.py:408`: judge routing ignores
  `verdict.root_stage` and always resamples the judged stage. The contract says the 打回 target is the
  judge-attributed root stage, not mechanically the current stage. A J1 verdict with `root_stage="0_reading"`
  currently becomes `JUDGE_BLOCK` for `1_correction`, and the CLI prints `resample ... 1_correction`. That
  misclassifies manual-root failures that should be `human_redraw_required`, and would also mishandle
  deterministic-root failures. Suggested fix: classify routable verdicts by `root_stage`, validate it against the
  stage registry, apply that stage's capability, and have the CLI resample/report the routed target stage, not
  always `stage`.

- `scripts/tool_scripts/run_stage.py:115`, `scripts/tool_scripts/run_stage.py:197`, `src/agent/pipeline.py:446`,
  `src/agent/pipeline.py:543`: the per-stage draw budget is only enforced around outer `run_one_stage` attempts,
  but the real stochastic executors still perform up to 3 internal LLM retries per outer draw. That means a
  nominal budget of 3 can spend up to 9 correction or MEP samples, and the internally rejected draws are not
  persisted under `attempts/NNN`. Suggested fix: add draw-once executor entry points for stepwise mode, or plumb
  the orchestrator budget/attempt filing into the internal retry loop so every stochastic draw is counted and
  archived.

**Medium**
- `scripts/tool_scripts/run_stage.py:420`, `src/agent/execution/step_orchestrator.py:386`: `approve-geometry`
  records the approval but never updates or clears the orchestration ledger. The normal documented flow is approve
  geometry, then run `4_mep`; however `update_state` only clears a stale stop reason when the advancing outcome is
  for the same stage, so `awaiting_geometry_approval@3_split_pairing` can remain in `orchestration_state.json`
  after the run has successfully advanced. `record_baseline.py` will then report a stopped run incorrectly.
  Suggested fix: on successful approval, update the state for the geometry checkpoint, or make the next successful
  `4_mep` run clear prior geometry-approval stop reasons.

**Low**
- `src/agent/execution/step_orchestrator.py:254`: `RunPolicy.judge_enabled` is ignored; enabled rubrics always
  produce `AWAITING_JUDGE`. That makes the exported orchestrator surprising outside this CLI. Suggested fix: gate
  the judge branch on `policy.judge_enabled and reg is not None and reg[1]`.

- `scripts/tool_scripts/run_stage.py:51`: `gt_path` / `has_gt` are imported at module load, even though the
  discipline says gt should only be reachable from the judge path. The current use is only in `_judge_packet`, but
  the import is broader than necessary. Suggested fix: move the gt import inside `_judge_packet`.

- `scripts/tool_scripts/run_stage.py:115`, `src/agent/pipeline.py:676`: stepwise correction does not write the
  `corrections.json` audit artifact that `run_pipeline` writes after deterministic core. The information is present
  inside the snapped geometry, but the stage directory shape no longer matches the full pipeline. Suggested fix:
  mirror the `corrections/conflicts/unsupported` write in `_draw_correction`.

---

## 主开发 Agent 处置（2026-06-19，Opus 4.8）

- **High-1（root_stage 路由）— 已修**：`_verdict_outcome` 改为按 `verdict.root_stage` 路由（校验 ∈ STAGE_REGISTRY，
  按该 stage 的 capability 判 manual→human_redraw / deterministic→交人 / stochastic→resample），`StageOutcome` 加
  `route_target`，CLI 用 route_target 提示重抽哪一段。
- **High-2（预算 vs 内层重试）— 已真修（re-verify 后升级处置）**：Codex re-verify 指出我初判有误——
  `_make_correction_validator` 拒的 0窗/重复id/z断裂是**语义坏 draw**（非纯 transport/格式），在内层被静默重试 ≤3×，
  绕过外层预算 + append-only attempts。**修法（语义/格式分层）**：① pipeline.py 抽出 `correction_draw_issues()`
  （语义检查，返回 list 不 raise）+ `_schema_only_correction_validator`（内层只判 schema/格式）+ `run_correction`
  加 `draw_validate` 参数（legacy run_pipeline 默认全量校验、字节不变）。② 步进 `_draw_correction` 用 schema-only 内层
  校验 + 在 PRE-core 跑 `correction_draw_issues` 作 gate①——**语义坏 draw 现在会被落 attempt + 计入 ≤3 预算 +
  盲重抽**。transport/JSON 格式重试仍在内层（Codex 认同 defensible）。+7 单测（test_correction_stability）。
- **Medium（approve-geometry 残留 stop_reason）— 已修**：`update_state` 改为 stop_reason 由**最新 outcome** 派生
  （advance→None），且 `approve-geometry` 成功后清几何门 stop_reason + 记 `geometry_approved`。
- **Low-1（judge_enabled 被忽略）— 已修**：judge 分支加 `policy.judge_enabled` 闸；CLI 仍 judge_enabled=True 行为不变。
- **Low-2（gt import 范围）— 已修**：gt import 移进 `_judge_packet`。
- **Low-3（corrections.json 缺失）— 已修**：`_draw_correction` 补写 corrections/conflicts/unsupported。

修后全套测试 **247 passed**（+新增 root 路由 / 几何门 stop_reason 清除 / 语义-格式分层 的回归）。

**Re-verify 状态（已闭环）**：Codex 第一轮判 High-1/Medium/Low-1/2/3 = **PASS**，High-2 = FAIL/must-fix（指出
语义坏 draw 绕过预算+审计）。我据此把 High-2 从"文档化"升级为真修（语义/格式分层，正是 Codex 开的药方
"semantic draw rejection should be counted/filed or exposed to the outer gate"）。额度恢复后 Codex 终审（新会话
019edfc0，自主读文件+跑 pytest）判 **High-2 = PASS（无 findings，247 passed），整个 #1 改动集 VERDICT: CLOSEABLE**。

**新 §6.14 试点小结（MCP 直连 + 落盘）**：可行且高效（Codex 自主 grep/读文件/跑 pytest、findings 内联回我、
我落盘审计轨迹）。两个环境约束：① Codex 自带 bwrap 沙箱在 dev container 内无法嵌套 → 只能 `danger-full-access`
（经 Claude Code 安全门，需用户显式授权）；② ChatGPT 账户有用量上限，长/多轮审会被打断。结论：适合**单轮深审**，
多轮 re-verify 受额度限制。
