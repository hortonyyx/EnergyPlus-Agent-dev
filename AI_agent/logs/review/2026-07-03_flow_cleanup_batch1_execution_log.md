# Flow cleanup Batch 1 execution log (2026-07-03)

## Scope

只执行 Batch 1：⑤ F1 修、② `baseline.models` 结构化、① `<run>/run_config.yaml` 接线、§7.1 sidecar 容差身份骨架、§7.5 gt 隔离测试扩面。未做 Batch 2 的 `render_grade` 视觉重画、per-attempt 全渲染、accepted grade promote、eyeball grade 收集。

## Changes

- `scripts/tool_scripts/run_stage.py`
  - §7.3 F1：`_judge_packet()` 现在接收当前 in-memory `RunManifest`，并传给 `_judge_gt_artifacts()`；不再依赖 packet 构建时从磁盘 reload 的旧 manifest。
  - §7.10/§7.1：接入 `RunConfig.grade_for(stage)`，将 `wall_tol_m/window_centre_tol_m` 线程化到 `_score_attempt_output()`、`score_floor()`、`score_correction_geometry()`、`reading_score_criteria()` 和 `score_vs_gt.json.tolerances`。
  - §7.1：`_load_valid_score_sidecar()` 严格匹配 `stage/attempt/output_hash/source/tolerances`，容差不同则重算 sidecar。
  - ①：`cmd_flow()` 读取 `<run>/run_config.yaml`，配置存在时用其中 `scope.stages`、`judge.mode`、`review.*`；缺文件时软降级为原 CLI 默认并 warning。`cmd_run()` 也读取配置以供 judge packet grade 容差使用。

- `src/agent/execution/run_config.py`
  - ①/§7.10：新增 `RunConfig`/`GradeConfig` loader。字段覆盖 `scope/judge/review/models/grade`，默认容差为 reading/correction 均 `0.30/0.40`。
  - 缺失/坏形状/坏容差均 `warnings.warn(..., RuntimeWarning)` 后使用历史默认；不 hard fail。
  - YAML `judge.mode: off` 兼容 PyYAML 将 `off` 解析为 `False` 的行为。

- `src/agent/judge/score_policy.py`
  - §7.1：`reading_score_criteria()` 接收真实 `wall_tol_m/window_centre_tol_m`，criteria evidence 不再硬写默认常量。

- `scripts/tool_scripts/record_baseline.py`
  - §7.6/②：`baseline.models` 改为结构化 `{reading, correction, mep, default, orchestrator}: {model_id, effort, source}`。
  - `run_config.yaml` 优先；legacy `llm.yaml` 作为 correction/mep/default fallback；缺 `run_config.yaml` 时 reading/orchestrator 等缺口显式 `unknown` + warning。
  - `mep` 若无 `intake_mep`，按现有 pipeline 语义记录 `intake_correction` fallback source。

- `scripts/tool_scripts/report_assembly.py`
  - ②：报告模型配置段兼容新的结构化 `baseline.models`，显示 `model_id/effort/source`，并列出 `run_config.yaml` 链接。

- `tests/test_gt_discipline.py`
  - §7.5：gt 隔离扫描从单文件扩到整个 `src/agent/execution/` + `src/agent/correction/`，并保留 `src/agent/pipeline.py` 覆盖。

- Tests
  - `tests/test_run_stage_flow.py`：新增真实 `cmd_flow()` 首 pass packet 时序测试，断言首次 accepted 后 packet 立即拥有非空 `score_vs_gt`、`overlay`、`score_criteria`；新增 run_config 控制 judge/review 默认测试。
  - `tests/test_judge_batch_b.py`：新增 sidecar `tolerances` 断言和容差不匹配重算断言。
  - `tests/test_run_config.py`：新增 run_config 缺失软默认和字段解析测试。
  - `tests/test_orchestrate_baseline.py`：新增结构化 `baseline.models` 与缺 run_config unknown+warn 测试。

## F1 fix choice

采用“把 in-memory manifest 传进 `_judge_gt_artifacts()`”方案，而不是在 packet 构建前强制 `manifest.save()`。

理由：副作用更小。`run_one_stage()`/`StageRunner.record()` 的既有语义是先更新内存 manifest，外层 verb 再统一保存；packet 是同一调用栈里的 judge-side 产物，只需要看到刚 accepted 的内存记录即可。这样不改变 `run_one_stage` 的持久化边界，也避免在 packet 回调里引入额外磁盘写入时机。

## Test result

- Focused: `pytest tests/test_run_config.py tests/test_run_stage_flow.py tests/test_judge_batch_b.py tests/test_orchestrate_baseline.py::test_record_baseline_models_structured_from_run_config_and_llm tests/test_orchestrate_baseline.py::test_record_baseline_models_missing_run_config_uses_unknown_and_warns tests/test_gt_discipline.py`
  - `19 passed`
- Full: `pytest`
  - `416 passed, 9 xfailed`
  - 新增通过数：`+6`（从既有 410 到 416）

## Claude review points

- Config loader shape：当前 `RunConfig` 放在 `src/agent/execution/run_config.py`，`flow` 使用 `scope/judge/review/grade`；`models` 主要供 `record_baseline` provenance 使用，未改 LLM factory/`llm.yaml` 生产配置路径。
- F1 timing fix：请复核“传 in-memory manifest”是否符合你希望的持久化边界；我没有在 packet 回调前提前保存 manifest。
- Tolerance threading：当前路径为 `run_config.yaml -> RunConfig.grade_for(stage) -> _judge_packet -> _judge_gt_artifacts -> _score_attempt_output -> score_floor/score_correction_geometry -> reading_score_criteria -> sidecar.tolerances`。Batch 2 的 renderer 仍待改为 sidecar-driven `render_grade`。
- Warnings：缺 `run_config.yaml` 会按规格软降级并 warning；全量测试因此有新增 RuntimeWarning 噪声，但不影响通过。
