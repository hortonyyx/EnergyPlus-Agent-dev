# Flow cleanup batch plan review (2026-07-03)

结论：**APPROVE-WITH-CHANGES**

整体方向成立，简报对当前源码状态的几条关键判断基本属实。但执行前需要补清楚 5 个容易造成静默错判/漏产物的问题：可配置容差必须进入 sidecar 身份与 criteria 文本；`render_grade` 必须以 `score_vs_gt.json` 为唯一判定源；F1 首-pass 测试要覆盖真实 flow 时序；accepted grade/report 收集要同步改；gt 隔离测试覆盖面要扩大。否则本批会把 F1 修掉，但引入新的“看起来有 grade、实际用旧容差/旧产物”的问题。

## 核实结论

1. `run_stage.py` 的 F1 机制属实。`_judge_gt_artifacts()` 在 `scripts/tool_scripts/run_stage.py:496` 从磁盘 reload manifest，`scripts/tool_scripts/run_stage.py:499` 有 `rec is None or rec.accepted_attempt != attempt` 的 accepted-only 门。当前 `StageRunner.record()` 只在内存 `manifest.accept()`（`src/agent/execution/stage_runner.py:166`），`_post_gate1()` 紧接着在 `src/agent/execution/step_orchestrator.py:321` 调 `packet_fn`，而 `cmd_flow()` 到 `scripts/tool_scripts/run_stage.py:994` 才 save，所以首 pass `rec is None` 的根因成立。
2. 容差现状属实。`reading_score.py` 定义 `DEFAULT_WALL_TOL_M = 0.30` / `DEFAULT_WIN_CENTRE_TOL_M = 0.40`（`src/agent/judge/reading_score.py:33`、`:35`），`score_floor()` 可传 `wall_tol/win_tol`（`:245`），`correction_score.py` import 同一套默认值（`src/agent/judge/correction_score.py:15`）且 `score_correction_geometry()` 也可传参（`:148`）。但 `run_stage.py` 当前调用没有传配置（`scripts/tool_scripts/run_stage.py:450`、`:461`）。
3. baseline.models 漏 reading 属实。`record_baseline._models_from_llm_yaml()` 只读取 `intake_correction/intake_mep/default`（`scripts/tool_scripts/record_baseline.py:58`），baseline 写入处为 `scripts/tool_scripts/record_baseline.py:331`。实际 `run_2026-07-02_sonnet_flow_e2e/_run/baseline.json` 只有 `intake_correction/default`。
4. `render_overlay.py` 现状与简报一致：它直接用 raw `output + gt` 画 overlay（`scripts/tool_scripts/render_overlay.py:143`、`:194`），没有读 `score_vs_gt.json`，也没有 hit/miss/extra、漂移带、立面批卷。
5. correction 侧已能产四 facade window 分表：`_extract_correction_windows()` 初始化 `N/S/E/W`（`src/agent/judge/correction_score.py:136`），score loop 也覆盖四面（`:184`）。但当前只判 along-facade span；`Window.z` 在 schema 有（`src/agent/correction/schema.py:48`），scorer 未用于竖向判分。

## Findings

**MAJOR-1 - 可配置容差必须写入并校验 sidecar 身份，否则会复用旧分数。**  
`scripts/tool_scripts/run_stage.py:473` 的 `_load_valid_score_sidecar()` 只校验 `stage/attempt/output_hash/source`，`scripts/tool_scripts/run_stage.py:518` 写 sidecar 时也没有 tolerance metadata。加 `run_config.grade` 后，同一 attempt 在不同 `wall_tol/window_centre_tol` 下会错误复用旧 `score_vs_gt.json`。  
具体改法：sidecar 增加 `tolerances: {wall_tol_m, window_centre_tol_m}`；`_load_valid_score_sidecar(..., tolerances=...)` 纳入严格匹配；`score_criteria` 也要传入同一 tolerance，因为当前 `score_policy.py` evidence 仍硬写默认值（`src/agent/judge/score_policy.py:93`、`:104`）。

**MAJOR-2 - `render_grade` 接口必须改为 score-sidecar driven，不能沿用 raw output 重算/重画。**  
当前 `render_overlay.render_overlay_to_path(stage, output, gt, out_path)`（`scripts/tool_scripts/render_overlay.py:194`）由 `run_stage.py` 传 raw output 调用（`scripts/tool_scripts/run_stage.py:539`）。这和简报 §1.8 “图↔证据同源”冲突。  
具体改法：`render_grade_to_path(stage, score_sidecar, gt, out_path, ...)` 或传 sidecar path/dict；颜色和 hit/miss/extra 只读 sidecar 的 `scores`，不要在 renderer 里再次 `_match_lines/_match_windows`。如果需要画 product 几何位置，使用 sidecar 里的 `read`/`extra_*` 字段。

**MAJOR-3 - F1 修应先落，并补真正首-pass flow 测试。**  
现有 `tests/test_judge_batch_b.py` 直接调用 `_judge_packet()`，且 fixture manifest 已在磁盘（如 `tests/test_judge_batch_b.py:57`），覆盖不了 `run_one_stage()` 首 pass。  
具体改法：Batch 1 先修 ⑤。可选方案：在 packet 构建前持久化 accepted manifest，或把 in-memory manifest/accepted record 传入 `_grade_artifacts`，避免 reload 磁盘旧态。新增测试要走 `cmd_flow()` 或 `run_one_stage()` 首次 accepted 后立刻断言 packet 中 `score_vs_gt/grade/score_criteria` 非空。

**MAJOR-4 - report/eyeball 收集与 accepted 升级件需要同步改。**  
`report_assembly.collect_eyeball_assets()` 目前只收 `1_correction/zones.png`、`1_correction/elev.png`、`0_reading/*_render.png` 和 case_data 图（`scripts/tool_scripts/report_assembly.py:100` 到 `:155`），不收 `overlay.png`，更不会收新 `grade.png`。  
具体改法：accepted attempt 的 `<stage>/grade.png` 必须 copy/promote 到 `<stage>/grade.png`，并由 `collect_eyeball_assets()` 显式收进 `report/eyeball/0_reading_grade.png`、`1_correction_grade.png`。`_print_review_checkpoint()` 也要从 `overlay.png` 改到 `grade.png`（`scripts/tool_scripts/run_stage.py:703`）。

**MAJOR-5 - gt 隔离测试覆盖面不足，本批应顺手加宽。**  
当前 `test_gt_discipline` 只扫 `src/validator/checks/*.py`、`src/agent/pipeline.py`、`src/agent/correction/deterministic.py`、`src/agent/execution/validation_run.py`（`tests/test_gt_discipline.py:50`、`:57`）。简报铁律说 `validator/`、`pipeline`、`execution`、`correction` 都不得 import/read gt；当前测试没有递归覆盖整个 `src/agent/execution/` 和 `src/agent/correction/`。  
具体改法：扩大扫描范围，保留 judge/tool scripts 白名单。per-attempt score/render 只能留在 `scripts/tool_scripts/run_stage.py` 的 judge path 或 `src/agent/judge/`，不要下沉进 `StageRunner`、`step_orchestrator` 或 correction executor。

**MINOR-1 - baseline.models 建议用结构化 provenance，而不是只补一个 reading 字符串。**  
当前 `_models_from_llm_yaml()` 返回 `{section: model_name}` 字符串（`scripts/tool_scripts/record_baseline.py:57`）。简报要求“每段 model_id + effort + 主控标识”。  
具体改法：`baseline.models` 建议按 stage/role 结构化，例如 `reading/correction/mep/default/orchestrator`，每项含 `model_id`、`effort`、`source`。旧 run 缺 `run_config.yaml` 时不要 hard fail；用 `unknown` + warning，符合 §3 向后兼容。

**MINOR-2 - displaced connector 先不要做进正式版。**  
`_match_windows()` 只产独立 miss/extra（`src/agent/judge/reading_score.py:230`），没有 pair id。renderer 端最近邻连线会新增一套非 scorer 证据，和 §1.8 冲突。  
具体改法：正式版只画 gt miss ghost + product extra；需要 connector 时由 scorer 输出 `displaced_pairs` 后再画。

**MINOR-3 - correction 立面“无数据”要区分空真值与缺数据。**  
Floor 1 West 没窗时 sidecar 合法表现为 `"W": []`，这不是缺数据。缺数据应只指 score floor 缺失、facade key 缺失、或 correction floor/window floor unmapped evidence。  
具体改法：grade 立面 panel 对空 facade 画空立面；对 missing score/evidence 画 `no data` 占位。

## §4 review-ask 答复

a. 两把独立判卷尺的推理成立；默认值先相等是正确选择。不要默认设成 correction 更紧，因为 correction 是 gt/image 盲，若 reading 放过而 correction 才卡住，补救点被后移。若要不等，应该是 reading 更紧或相等，即 `reading_tol <= correction_tol`。配置放独立 `run_config.yaml` 副作用小于扩 `llm.yaml`，因为 scope/judge/review/grade 不是 LLM factory 配置。

b. displaced 连线同意先不做，留 backlog。没有 scorer pair id 前，render-only 最近邻配对会制造第二套证据。

c. 最干净路径：`run_config.yaml` -> `RunConfig.grade_for(stage)` -> `_judge_packet()` -> `_grade_artifacts()` -> `_score_attempt_output(... wall_tol, win_tol)` -> `score_floor()` / `score_correction_geometry()` -> `reading_score_criteria(... wall_tol, win_tol)` -> sidecar metadata -> `render_grade_to_path(sidecar, gt, ...)`。

d. 认同执行顺序 ⑤ -> ③。先修 manifest/packet 首-pass 时序，再做每 attempt 全渲染；否则容易在 per-attempt 扩面时把空 evidence 问题扩散。

e. correction_score 已产四立面 window 分表，但只判横向 span；竖向 sill/head 可按简报用 gt 做参考底。缺数据画占位，空 facade 不画成缺数据。

## 其他风险

1. per-attempt grade 的磁盘/性能成本当前可接受：J0/J1 每 stage 通常最多 3 attempts，一张合成 PNG 成本不大。但要用 `output_hash + tolerances` 跳过重绘，避免 resume 每次重画。
2. 盲重抽污染风险可控，前提是 grade/score 只留在 attempts/judge/report 面，不进入 correction prompt 的顶层 `*.json` glob。当前 pipeline 只读 `0_reading/*.json` 顶层（`src/agent/pipeline.py:84`、`:367`），attempts 子目录不会被读到；继续保持。
3. Batch 拆分合理，但 Batch 1 必须包含 sidecar tolerance/schema 变更的最小骨架；Batch 2 再做视觉重画和 per-attempt promotion。

未运行测试；本次按要求只读源码并写审阅意见。
