# `flow` P1 执行简报审阅报告

审阅对象：`AI_agent/logs/review/request/2026-07-02_flow_p1_execution_brief.md`  
权威基线：`AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md` §8，尤其 §8.6/§8.10/§8.11。  
结论：**APPROVE-WITH-CHANGES**

总体判断：P1 切分成立，Batch A/B/C 的大方向可执行；A3 durable review、A4/A7 invalidate、A6 option A、B1/B2 scorer evidence 的基本机制都落在当前真实代码接口上。需要在动工前补几条硬约束，否则会出现 evidence 与 accepted attempt 不绑定、`--from auto` 被 stale state 误导、flow 下游 EP 使用错误 LLM 配置等问题。

## Findings

### MAJOR-1：B1/B4 的 scorer sidecar / overlay 必须从 accepted attempt 读产物，不能读 mutable stage 目录

简报 B1 写的是 `_judge_packet` 对 0 段调用 `score_reading_dir(run_dir/'0_reading', case)`，1 段吃 `1_correction/correction_geometry_snapped.json`（简报 167-168、188-190）。但当前 `_judge_packet` 在 `_post_gate1` resume 已接受 attempt 时仍会重新生成 packet（`step_orchestrator.py:232-238`, `293-324`），而当前 packet/render 也从 stage flat 目录读（`run_stage.py:387-411`）。`StageRecord.output_hash` 的权威绑定对象是 `attempts/NNN/output.json`（`stage_runner.py:140-172`）。

如果用户在 judge 前改动 flat `0_reading/*_view.json` 或 `1_correction/correction_geometry_snapped.json`，sidecar 会落在旧 attempt 目录里，但内容对应新 flat 文件。这会破坏“gt 权威 evidence”作为 accepted attempt 证据的语义，也会让 A3 的人工复核记录绑错对象。

必须改执行简报：`score_vs_gt.json`、`score_criteria`、overlay 都从 `attempt_dir/output.json` 或与 `manifest.accepted(stage).output_hash` 校验一致的 artifact 生成；sidecar 内写入 `stage`、`attempt`、`output_hash`、`source="attempt_output"`。已有 sidecar 可复用，但必须校验 hash。补测试：resume 后篡改 flat stage 文件，packet sidecar 仍等于 accepted attempt。

### MAJOR-2：`--from auto` 必须 manifest-first，不能依赖 stale `orchestration_state`

`invalidate(manifest, stage)` 只删除下游 accepted 指针，不改 `orchestration_state.json`（`invalidation.py:50-62`）。简报说 `--from auto` 由 manifest/state 决定（简报 73、251），但未定义优先级。若实现按 state 判断“已 advance”，下游被 invalidate 后 state 里仍可能保留旧的 `deterministic_pass`/`judge_pass`，flow 会错误跳过需要重跑的 2/3/4/5。

必须改执行简报：`--from auto` 判定以 manifest 为权威。某阶段只有在以下条件同时满足时才算 advance：有 accepted record；若该阶段有 enabled judge，则 accepted attempt 旁存在非 blocking verdict；若该阶段开人工 review，则 durable review hash 当前；若是几何门，则 approval digest 当前；且下游没有因上游 invalidate 缺 accepted pointer。state 只用于提示 pending 原因，不用于证明完成。补 A7/F 测试：已判 1 段后 invalidate 1，auto 从 2 而非跳到 5。

### MAJOR-3：A6/flow 的 EP 共享函数需要写清 run-scoped LLM 配置与 intake loader

`run_full_pipeline.py` 在 graph run 前设置 `EP_AGENT_LLM_CONFIG`，优先 `--llm-config`，其次 `<case>/llm.yaml`，再全局默认（`run_full_pipeline.py:195-220`）；`src.agent.llm` 依赖该环境变量加载所有下游模型（`llm.py:14-36`）。权威流程要求新 run 目录落模型配置（权威 §8.1 第 2 步），但简报 A6 的 flow 侧只构造 `AgentState`，没有说明 `<run>/llm.yaml` 如何进入环境（简报 133-142）。

必须改执行简报：`flow --with-ep` 在调用 `run_downstream_ep` 前解析并设置 LLM 配置，建议优先 `<run>/llm.yaml`，允许 `--llm-config` 覆盖，再退到 `<case>/llm.yaml`/全局；记录实际配置路径。`_load_intake_from` 的 `ensure_schema_initialized()` 逻辑应抽共享，不能在 flow 里裸 `IntakeOutput.model_validate_json`。`--epw` 也应暴露或复用 `run_full_pipeline.py` 的默认 `data/weather/Shenzhen.epw`。

`run_downstream_ep` 落 `src/agent/runner.py` 可行，但应 lazy import `build_graph`，接收已构造的 `AgentState`/`SimContext` 参数，避免把 CLI config 解析塞进 runner。`run_full_pipeline` 的 `--reading-from`、`--intake-from`、`--no-simulate`、prebuilt-intake short-circuit、flat-vs-EP 布局必须通过回归测试保真（`run_full_pipeline.py:241-343`）。

### MAJOR-4：B3 correction scorer 需要显式 floor-name 映射

`CorrectedGeometry` 支持 `Floor.name` 任意字符串（`correction/schema.py:59-74`），当前真实样本同时存在 `"Floor 1"`/`"Floor 2"` 和 `"F1"`/`"F2"`。gt 则用 `"Floor 1"`/`"Floor 2"`。简报 B3 只说抽 cell rect 与 window span，未说明 floor 对齐策略（简报 188-192）。

必须改执行简报：correction scorer 不能只按字符串相等匹配 floor。应按以下顺序映射：精确名称、数字序号（F1/1F/Floor 1）、必要时按 `z_floor`/列表顺序兜底；未匹配 floor 要写进 sidecar evidence，而不是静默空分。否则 J1 scorer 在现有 sm21 `F1/F2` run 上会假阴性或无 evidence。

### MINOR-1：A8 退出码表应保留未自动处理 `JUDGE_BLOCK` 的 10 码兜底

权威 §8.6 把“未处理 JUDGE_BLOCK”列入 10 码动作检查点。简报 A8 只列 AWAITING_* 为 10（简报 151-155），而 A4 假设所有 `JUDGE_BLOCK` 都会自动重抽。当前 `_verdict_outcome` 正常会给 stochastic root 填 `route_target`（`step_orchestrator.py:440-443`），所以主路径没问题；但实现仍应防御 route target 缺失、target 超出 `--to` 策略、或自动动作被配置关闭的情况。

处置：退出码表补 `JUDGE_BLOCK` defensive mapping：能自动处理就不返回；无法自动处理时退 10，并打印人工动作。

### MINOR-2：Batch A 不能硬依赖 Batch B 的 overlay/score sidecar 已存在

简报 A3 要在人工 review 停靠时打印 overlay + score sidecar 路径（简报 103），但 Batch B 才产这些 artifact（简报 161-201）。A 先 B 后的切分合理，不过 A 实现必须对缺失 artifact 软降级：打印“not generated yet / Batch B unavailable”，不能阻塞 durable review 测试。

### MINOR-3：`approve-review` 后的 state 语义要与 geometry approval 对齐或明确差异

几何 approval 记录后会 `mark_geometry_approved` 清 pending stop_reason（`step_orchestrator.py:531-544`）。A3 的 `approve-review` 只写 durable record（简报 111），未说明是否清 `awaiting_human_review@stage`。可接受“必须重跑 flow 后清”，但这会让 `status` 在批准后、重跑前仍显示 pending。

处置：二选一写清楚。推荐新增 `mark_review_approved`：若 stop_reason 正是该 stage 的 `awaiting_human_review`，记录 `human_review_approved` 元数据并清 pending；重跑 flow 仍以 output_hash 复核为准。

## 审阅重点逐条结论

1. **A3 durable 人工校验 checkpoint**：机制正确，建议采用 flow 外壳自造 `AWAITING_HUMAN_REVIEW`，不把 review 开关传进 `run_one_stage`。`output_hash` 绑定足够稳，因为它是 accepted attempt 的内容 hash。需补 MAJOR-1 的 attempt-bound evidence 和 MINOR-3 的 state 处置。
2. **A6 EP 布局修 option A**：方向正确。共享函数应只承载 graph/session/SimContext，不吞 CLI 布局决策；`run_full_pipeline` 仍按当前逻辑算 `output_dir`/`ep_run_subdir`，flow 固定传 `<run>/EP` + `EP_run`。需补 MAJOR-3。
3. **A4 JUDGE_BLOCK 自动重抽 + A7 invalidate**：正确复用 `_verdict_outcome` 分流；manual/deterministic root 已不会进入自动重抽。`cmd_resample` 补 invalidate 不破坏语义，属于修复旧缺口；要在 force 前 `manifest.save` 并测试下游指针清理。
4. **A8 退出码**：0/10/20/30 自洽，但需补 `JUDGE_BLOCK` defensive 10 码兜底。
5. **B1/B2 scorer 接入 judge_packet**：不写入 `StageVerdict`、不替代 checklist 的边界正确；`score_criteria` 只能是 advisory evidence。阈值复用 `DEFAULT_WALL_TOL_M=0.30`、`DEFAULT_WIN_CENTRE_TOL_M=0.40`，放宽口径合理。需补 MAJOR-1。
6. **B3/B4**：技术路径可行。Correction scorer 可复用 `reading_score` 的 gt derivation/matcher，但要补 floor 映射。Overlay 必须用共享 metric transform 直接同图绘制，不能 raster 合成；centerline-vs-clear-space caveat 已有，但实现要在图例/evidence 中标成容差说明。
7. **gt 隔离铁律**：简报边界正确。新增 `score_*_vs_gt`、overlay、score_policy 只能在 `src/agent/judge/` 或 `scripts/tool_scripts/`，`run_stage.py` 也只能在 `_judge_packet`/tooling path 内 lazy import gt。不得让 `src/validator/checks`、`src/agent/pipeline.py`、`src/agent/execution/validation_run.py` import gt。
8. **§8.11 build 必办覆盖**：P1 覆盖 #1/#2/#3/#4/#6/#7 及 P1 测试；#5 J23 和对应 deterministic-root 测试明确 P2 deferred，符合权威 §8.11 分期建议；#8 需增加 MAJOR-1/2 的测试。
9. **批次切分**：A 先 B 后合理。条件是 Batch A 对 Batch B artifact 软依赖，不改 golden，不改 `run_pipeline`、契约、gate①、`StageVerdict` 语义。
10. **当前 395 绿 + 9 strict xfail / golden 风险**：主要风险来自 `StepStatus` 新枚举影响 state 测试、`cmd_resample` invalidate 改变旧断言、`run_full_pipeline` 重构行为漂移。简报测试清单方向正确，但需补上述回归。

## §7 审阅需求裁决

| 项 | 裁决 |
|---|---|
| A-R1 | 选 **flow 外壳自造** `AWAITING_HUMAN_REVIEW`。核只产 gate①/judge/geometry fact，review 开关是调用策略。必须把新枚举加入 `StepStatus`，并让 `update_state` 记录非 terminal stop。 |
| A-R2 | golden + `--geometry auto` 选 **告警不硬阻**。默认仍为 `required`；显式 `auto` 要有 actor=`flow:auto`、policy=`auto`、viewer 重渲和 baseline/report 可见审计。 |
| A-R3 | 共享函数落 `src/agent/runner.py` 可行；`build_graph` lazy import。`_load_intake_from`/schema init 抽共享。flow 侧必须补 run-scoped LLM config、`--epw` 默认和 thread_id 建议 `case/run`。 |
| A-R4 | `cmd_resample` 补 invalidate **应做**。这会改变“旧下游 accepted 指针保留”的错误行为；如现有测试依赖旧行为，应更新测试。 |
| A-R5 | 老 verb 不升级新退出码。保留 `0/2` 兼容；新码表只给 `flow`。 |
| B-R1 | 建议新建纯坐标 transform util，例如 `scripts/tool_scripts/_overlay_transform.py`。gt 与产物共用同一 `metric_to_pixel`，直接绘制到同一 canvas；不要叠两张 PNG。 |
| F-额外 | `output_hash` 绑定 durable review 足够稳。`--from auto` 必须按 MAJOR-2 manifest-first；被 invalidate 的下游即使 state 显示 pass，也必须重跑。 |

## Build 必办处置

| §8.11 必办 | 简报处置 | 审阅结论 |
|---|---|---|
| #1 scorer sidecar + 阈值→criterion | B1/B2 已覆盖 | **需改**：sidecar/overlay 必须绑定 accepted attempt 与 output_hash。 |
| #2 StageVerdict 权威、不塞 raw 分 | B2 已覆盖 | **通过**：保持 advisory evidence，不自动 verdict。 |
| #3 J1 correction scorer | B3 已覆盖 | **需改**：补 floor-name mapping 与未匹配 evidence。 |
| #4 overlay 共享 transform | B4 已覆盖 | **通过但需测试**：共享 metric transform、非 raster 合成、标注 centerline caveat。 |
| #5 J23 reorder/wrap | 简报明确 P2 deferred | **通过**：P1 不应动 stage-3 judge 顺序；P2 单独审。 |
| #6 durable 人工 review | A3 已覆盖 | **通过但需补**：approve-review state 清理策略写清。 |
| #7 force 前 invalidate | A4/A7 已覆盖 | **通过**：flow 与 `cmd_resample` 都要做。 |
| #8 测试 | §5 已覆盖大部 | **需补**：attempt-bound evidence、manifest-first auto、run-scoped LLM config；J23 测试 P2。 |

## 最终必办清单

1. 修改简报 B1/B4：所有 scorer/overlay evidence 从 accepted attempt output 生成，并写 `output_hash`。
2. 修改简报 A1/F：定义 `--from auto` 的 manifest-first advance 判定，state 只作提示。
3. 修改简报 A6：flow 的 `<run>/llm.yaml` / `--llm-config` / `--epw` / shared intake loader 明确化。
4. 修改简报 B3：加入 correction floor-name 映射和未匹配 floor evidence。
5. 修改简报 A8：补未自动处理 `JUDGE_BLOCK` 的 10 码兜底。
6. 修改简报 A3/Batch A：Batch B artifact 缺失时软降级；`approve-review` 后 state 清理策略明确。

完成以上改动后，本简报可作为 P1 build 指令进入 Batch A/B 执行。
