# A8 correction evidence routing proposal review

结论：APPROVE-WITH-CHANGES

本审只核方案与代码接缝，不改业务代码。A8 的主方向成立：Phase A 已把 reading 证据债变成机器可读事实，golden/regression 应 fail-closed 或进入既有 reread 路由，exploratory/dev 可以继续但 correction 必须看到确定性 debt manifest，避免 image-blind LLM 为弱证据补造坐标。需要修改的是若干接缝事实与落地强度，尤其 run_profile 的实际传播和事后核。

## Findings

### BLOCKER

无。

### MAJOR

1. **run_profile 的实际入口/默认值会削弱 A8.2，方案需补齐而不是只假定 golden/regression 已在路径上。**  
   `run_pipeline()` 目前没有 `run_profile` 参数，直接在 correction 前调用 `run_correction()`，没有读取/消费 reading checks：`src/agent/pipeline.py:689-731`。`intake_node` 与 standalone wrapper 也都用默认 `run_pipeline(...)`：`src/agent/nodes/intake.py:64-66`、`scripts/run_pipeline_deepseek.py:59-60`。另一方面，`record_baseline()` 与 `run_stage.py` 虽已有 `--run-profile`，默认仍是 `exploratory`：`scripts/tool_scripts/record_baseline.py:292-308`、`:666-670`，`scripts/tool_scripts/run_stage.py:399-410`、`:569-573`。现有 sm21 “golden” 单测也用 `RunPolicy(require_ep=True)` 默认 exploratory：`tests/test_validation_run_baseline.py:217-220`。  
   结论：Q3 的答案是“当前 correction 前确实无证据债拦截；但 recorded golden baseline 的常规验证路径不是 `run_pipeline()`，而是已产物 + `validate_case/record_baseline`。A8.2 对 `run_pipeline` 是真实缺口补丁，但不是当前 golden baseline 测试的主路径。”落地时必须给 `run_pipeline`/CLI/调用方一个显式 `run_profile`，并把 golden/regression 调用口径写进指南/测试，否则 fail-closed 分支不会被触发。

2. **方案里的 orchestrator/correction 入口事实需要修正。**  
   当前仓库没有 `src/agent/execution/run_stage.py`；逐段 runner 是 `scripts/tool_scripts/run_stage.py`。stepwise correction 入口在 `_draw_correction()` 调 `run_correction()`：`scripts/tool_scripts/run_stage.py:119-136`。`src` 内 `run_correction()` 只有定义和 `run_pipeline()` 调用；脚本层还有 stepwise 调用。  
   同时，`route_stage_failure()` 对 manual stage 只返回 `HUMAN_REDRAW_REQUIRED`：`src/agent/execution/routing.py:38-48`；真正转成 `AWAITING_REREAD` 是 `step_orchestrator.run_one_stage()` 在 `policy.reading_runner_available=True` 且 0_reading gate① blocking 时做的：`src/agent/execution/step_orchestrator.py:264-274`。方案“golden/regression BLOCK → reread 已通”的结论基本成立，但表述应改成“经 step_orchestrator + runner flag 转换”，不是 routing.py 单独触发。

3. **preflight 必须按“当前请求的 run_profile”重判 disposition，不能盲用落盘 CheckReport 自带 profile。**  
   evidence check 本身是事实，disposition 由 `disposition(result, run_profile=...)` 决定：`src/validator/checks/schema.py:105-137`。但已接受 attempt 会直接加载旧 report 再走 post-gate：`src/agent/execution/step_orchestrator.py:232-238`，不会因为本次命令从 exploratory 改成 golden 而重算。`record_baseline()` 会重新 validate，所以它不受这个问题影响；A8 preflight 若读取落盘 checks，则必须显式传入当前 `RunPolicy.run_profile` 并重新调用 disposition，测试覆盖“report.run_profile=exploratory，但 preflight run_profile=regression 仍 fail-closed”。

4. **A8.3b 不应只是可选项；应作为 exploratory/dev 的确定性可见兜底，disposition 可保持 FLAG。**  
   Q1 裁决我接受“不在 exploratory 纯确定性强制 unsupported”：证据债不等于一定不可修，尤其 `stroke_provenance_coverage`、`dimension_chain_closure`、`dimensions_present` 是 view/global 或链级弱证据，不总能一一映射到某个 corrected cell/window。强制 LLM 不碰会与 Phase B 的双通道/算术下沉重叠，也会误杀可由独立证据修复的情况。  
   但仅有 manifest + prompt 纪律仍不足以回应原 MAJOR5 的“确定性路由非 prompt 指令”。建议把 CROSS_CHECK 作为 A8 的必需轻量门：对 element-local debt（如 `dimension_derived_refs.offenders`）要求输出落 `unsupported`/`conflicts` 或有明确独立证据说明；对 view/global debt 至少要求 correction audit 中引用 debt，若仍静默产出完整坐标则 flag。exploratory/dev 不 block，golden/regression 已在 preflight fail-closed/reread。

### MINOR

1. **已核实的接缝事实。**  
   `EVIDENCE_CHECK_IDS` 确为 6 个：`src/validator/checks/schema.py:41-49`；golden/regression block 且 legacy_migrated 祖父化为 flag：`:52`、`:129-134`。`summarize_gates()` 的四信号存在：`reading_syntax_valid`、`reading_evidence_clean`、`j0_semantic_clean`、`pipeline_recovered`：`src/agent/execution/orchestrate.py:77-119`。`CorrectedGeometry.unsupported` 已是既有字段：`src/agent/correction/schema.py:67-79`。`_build_correction_messages()` 已有 room_labels 与 feedback 两个结构化注入模式：`src/agent/pipeline.py:330-348`。

2. **Q2：preflight 放 `src/agent/execution/` 是正确层次。**  
   validator 层应继续只产事实；A8 preflight 是消费 `CheckReport`、按 run_profile 作执行路由和下游 prompt/audit 注入，属于 execution/orchestration。可以在 validator 暴露纯 helper（例如 evidence id 判定已存在），但不要让 validator 知道 correction 或 `unsupported`。

3. **“不新增 needs_reread 字段，复用 AWAITING_REREAD + unsupported”判断成立。**  
   对 stepwise/orchestrator 路径，reading 证据债在 golden/regression 下可以通过既有 0_reading gate blocking 进入 `AWAITING_REREAD`（runner 可用）或 human redraw/quarantine（runner 不可用/预算耗尽）；这不需要改 `CorrectedGeometry`。对 `run_pipeline` 便捷路径，正确行为是 correction 前 fail-closed 并提示 reread，而不是把 reread 意图塞进 correction schema。对 exploratory/dev，已有 `unsupported` 字段足够承载“不可安全修复”的结果。

4. **Q5：A8 范围限 correction 前是合适的，但 evidence_debt 应留痕给报告/归因。**  
   4_mep 不直接消费 0_reading；它吃 3_split_pairing 的 geometry specs 和 testdata：`src/agent/pipeline.py:767-809`。证据债的实际风险是在 correction 把弱 reading 固化为 geometry 后传递下游。因此 A8 不必扩到 4_mep 的 prompt，但应把 `1_correction/evidence_debt.json` 纳入 correction audit/report evidence index，便于后续判断 downstream 错误是否源自 reading debt。

## Q1-Q5 Answers

- **Q1**：接受 exploratory/dev 保留 prompt 纪律，但必须有确定性 manifest 和必需的事后 CROSS_CHECK（FLAG）。不建议纯确定性强制全部 unsupported。
- **Q2**：放 `src/agent/execution/`；validator 保持事实层。
- **Q3**：`run_pipeline` 当前 correction 前无证据债拦截；但 golden baseline 的 recorded-run 验证主要走 `validate_case/record_baseline`，不是 `run_pipeline`。A8.2 是真实缺口但优先级低于 stepwise/profile 口径补齐；若团队把 standalone/intake_node 用作 golden 录制路径，则需同步升优先级。
- **Q4**：CROSS_CHECK 必要，不是过度工程；但 exploratory/dev 应 flag，不应 block。
- **Q5**：不扩 prompt 到 4_mep；把 debt manifest 留痕并进报告/归因即可。

## Required Changes Before Implementation

1. 修正文档中的路径和路由事实：`scripts/tool_scripts/run_stage.py`，以及 `route_stage_failure` vs `step_orchestrator` 的责任边界。
2. 给 A8 preflight 明确一个 `run_profile` 输入，并用该 profile 重判 disposition；不要依赖落盘 report 的旧 profile。
3. 给 `run_pipeline` 增可选 `run_profile="exploratory"`，并给 CLI/intake_node 是否传 golden/regression 作明确策略；新增 golden/regression fail-closed 测试。
4. 将 A8.3b 作为必需的 deterministic CROSS_CHECK（exploratory/dev flag），并定义 element-local 与 view/global debt 的不同核查粒度。
