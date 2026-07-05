# P1 Batch A 执行日志：flow 编排 harness

日期：2026-07-02  
执行范围：仅 Batch A（编排 harness）。未实现 Batch B 的 gt evidence/scorer/overlay，未改 Batch C 文档。

## 逐文件改动摘要

- `scripts/tool_scripts/run_stage.py`
  - 新增 `flow` verb，按 manifest-first resume 逐段调用现有 `run_one_stage`。
  - 新增 `approve-review` verb，写入 `_run/human_review.json` 并清理匹配的 pending state。
  - `flow` 专用退出码：0 完成；10 人/动作 checkpoint；20 终止编排停；30 EP/record 失败。
  - `--judge off` 通过 policy 关闭 enabled judge；`--judge stop` 停在 `AWAITING_JUDGE`。
  - `--geometry auto` 自动重渲 viewer，并以 `actor="flow:auto"`、`policy="auto"` 写 geometry approval。
  - `JUDGE_BLOCK` routable stochastic root 自动 `invalidate(target)` 后 force blind resample；无法自动处理时退 10。
  - `cmd_resample` 补 downstream invalidate。
  - `--with-ep` 调共享 `run_downstream_ep`，固定落 `<run>/EP/EP_run/`，并按 `--llm-config > <run>/llm.yaml > <case>/llm.yaml > src/configs/llm.yaml` 设置 `EP_AGENT_LLM_CONFIG`。
  - Batch B artifact 缺失时在 human review checkpoint 软降级打印 `not generated yet`，不阻断。

- `src/agent/execution/step_orchestrator.py`
  - 新增 `StepStatus.AWAITING_HUMAN_REVIEW`，保持非 terminal、非 advance。
  - `update_state` 将 `AWAITING_HUMAN_REVIEW` 纳入 pending stop_reason。
  - `approve_geometry` 增加 `policy` 参数，保留默认 `required`。
  - 新增 `mark_review_approved`，用于批准 review 后清 matching stop_reason；放行仍以 hash-bound durable review 为权威。
  - 未改 `run_one_stage` 核心判定逻辑。

- `src/agent/execution/review.py`
  - 新增 `HumanReviewApproval`、`load_reviews`、`record_review`、`review_is_current`。
  - 存储位置：`_run/human_review.json`。
  - 审核记录绑定 `manifest.accepted(stage).output_hash`，resample 后 hash 漂移即失效。

- `src/agent/execution/__init__.py`
  - 导出 human review 相关符号、`mark_review_approved`、几何 checkpoint 常量。

- `src/agent/runner.py`
  - 新增共享 `load_intake_from(path)`，内部调用 `ensure_schema_initialized()`。
  - 新增 `run_downstream_ep(...)`，只负责 lazy `build_graph`、`SimContext`、`run_session(auto_approval)` wiring。

- `scripts/run_full_pipeline.py`
  - 移除本地 `_load_intake_from` 和内联 graph/session 代码，改用 `src.agent.runner` 共享函数。
  - 保留原 CLI 的 LLM 配置解析、`--reading-from`/`--intake-from` 布局决策、`--no-simulate` 行为。

- `tests/test_step_orchestrator.py`
  - 覆盖 `AWAITING_HUMAN_REVIEW` 非 terminal/非 advance。
  - 覆盖 `mark_review_approved` 清 pending state。

- `tests/test_execution_foundation.py`
  - 覆盖 human review durable 记录绑定 output hash，hash 漂移失效。

- `tests/test_run_stage_flow.py`
  - 覆盖 `cmd_resample` downstream invalidate。
  - 覆盖 `flow` human review checkpoint、`approve-review` 后 resume、resample 后复核失效重停。
  - 覆盖 `JUDGE_BLOCK` 自动 invalidate + force resample。
  - 覆盖 terminal stop 退 20。
  - 覆盖 geometry auto 写 `actor="flow:auto"` / `policy="auto"`。

- `tests/test_runner_shared.py`
  - 覆盖 `run_downstream_ep` 对 graph、`SimContext`、thread_id、on_event 的 wiring。

- `tests/test_run_full_pipeline_shared.py`
  - 覆盖 `run_full_pipeline --reading-from` 保持 `<case>/EP` + `EP_run` 布局。
  - 覆盖 `run_full_pipeline --intake-from --no-simulate` 保持 flat `<case>/output` 布局与 `run_simulate=False`。

## 新增测试清单

- `tests/test_run_stage_flow.py`
- `tests/test_runner_shared.py`
- `tests/test_run_full_pipeline_shared.py`
- 追加用例：
  - `tests/test_step_orchestrator.py`
  - `tests/test_execution_foundation.py`

## pytest 结果

- 相关测试：
  - `pytest tests/test_step_orchestrator.py tests/test_execution_foundation.py tests/test_run_stage_flow.py tests/test_runner_shared.py -q`
  - 结果：`61 passed`
- 新增 flow/runner/run_full_pipeline 子集：
  - `pytest tests/test_run_full_pipeline_shared.py tests/test_run_stage_flow.py tests/test_runner_shared.py -q`
  - 结果：`8 passed`
- 全量：
  - `pytest -q`
  - 结果：`406 passed, 9 xfailed, 36 warnings in 86.57s`
  - strict xfail 未变 XPASS。

## 环境说明

- 首次全量 pytest 收集 DXF 测试时，`/opt/venv` 缺 `ezdxf`，报 `ModuleNotFoundError: No module named 'ezdxf'`。
- 未修改依赖文件；仅执行 `uv pip install --python /opt/venv/bin/python ezdxf` 补齐当前测试环境后重跑，全量通过。

## 自报审阅需求

- `ezdxf` 似乎未在项目依赖声明中命中（本次未改 `pyproject.toml`，避免扩大 Batch A scope）。请 Claude 判断是否另开依赖声明修复。
- `flow --record` 的 pending 拒绝逻辑在 flow 收尾处实现；由于 flow 遇 pending 会先以 10 返回，record pending 的 30 分支主要防御外部/异常 state。请复核该行为是否符合主控预期。

## 偏离/取舍

- 未做 Batch B 的 `score_vs_gt` sidecar 或 overlay 生成；human review 停靠只做软降级打印 `not generated yet`。
- 未改 gate①/judge/verdict 语义，未改 `run_pipeline`，未改 CorrectedGeometry/契约，未改 golden baseline，未动 reading 子代理协议。
- `run_one_stage` 核心逻辑保持不变；`AWAITING_HUMAN_REVIEW` 仅由 `flow` 外壳自造并写 state。
