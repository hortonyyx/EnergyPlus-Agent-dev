# Flow cleanup Batch 2 execution log (2026-07-03)

## Scope

执行 Batch 2: ④ `render_overlay.py` -> `render_grade.py` 视觉重画，③ per-attempt 全渲染 + accepted 升级，外加 §7.4 eyeball 收集。

未提交 git commit。

## Changed files

- `scripts/tool_scripts/render_grade.py`
  - 由旧 `render_overlay.py` 改名并重写。
  - 新接口: `render_grade_to_path(stage, score_sidecar, gt, out_path)`。
  - 判定颜色只读 `score_sidecar["scores"]`: `read` / `delta` / `extra_vwalls` / `extra_hwalls` / `windows` / `extra_windows` / `tolerances`。
  - 不再读取 attempt raw output，不再调用 scorer 的 `_match_lines` / `_match_windows`。
  - gt 只用于 zone 淡灰填充、合并内墙线段 extent、footprint、立面楼层/窗高参考。
  - 合成图包含各 floor plan + N/S/E/W 四个 elevation panel。
  - 画法按 §1.2-1.5: hit 绿实线，miss 红虚线/窗淡红填充，extra 红实线/框，漂移画淡绿 tol band + 灰 gt 中线，窗位错只画 miss ghost + extra，不画 displaced 连线。
  - 外边界、立面 envelope、楼层线改为中性灰参考几何；图例标注 `gray outline = reference geometry (not graded)`。
  - §7.7: 空 facade key 且值为 `[]` 时画空立面；score floor 缺失或 facade key 缺失时画 `no data`。

- `scripts/tool_scripts/_grade_transform.py`
  - 由 `_overlay_transform.py` 改名，供 grade renderer 和测试共用 metric-to-pixel transform。

- `scripts/tool_scripts/run_stage.py`
  - `_judge_gt_artifacts()` 保持 packet 的 accepted-only 门，但内部复用新的 `_grade_attempt_artifacts()`。
  - 新增 `_grade_attempt_artifacts()`:
    - judge-side 读取 `attempts/NNN/output.json`。
    - 用 run_config grade tolerance 打 `score_vs_gt.json`。
    - 用 sidecar 渲 `attempts/NNN/grade.png`。
    - sidecar 复用仍严格校验 `stage/attempt/output_hash/source/tolerances`。
  - 新增 `_render_all_attempt_grades()`:
    - 遍历 `<stage>/attempts/NNN/`，为每个 attempt 生成 `score_vs_gt.json` + `grade.png`。
    - accepted attempt 的 `grade.png` copy/promote 到 `<stage>/grade.png`。
  - 新增 `_render_stage_grade_artifacts()`:
    - 只在 `run_stage.py` tool script judge path 内 lazy-import `src.agent.judge.gt`。
    - `cmd_run()` / `cmd_flow()` 每段 `manifest.save()` 后调用。
  - judge packet 字段从 `overlay` 改为 `grade`。
  - `_print_review_checkpoint()` 从 `overlay.png` 改为 `grade.png`。

- `scripts/tool_scripts/report_assembly.py`
  - `collect_eyeball_assets()` 显式收:
    - `0_reading/grade.png` -> `report/eyeball/0_reading_grade.png`
    - `1_correction/grade.png` -> `report/eyeball/1_correction_grade.png`

- Tests
  - `tests/test_render_grade.py`
    - 覆盖 hit、miss、extra、drift band、wrong-position、no-data、empty-facade。
  - `tests/test_judge_batch_b.py`
    - packet 断言改 `grade`。
    - 新增 per-attempt 落盘测试: 每个 attempt 都有 `score_vs_gt.json` + `grade.png`，accepted promote 到段根。
    - 更新 shared-transform pixel 测试为 sidecar-driven grade。
  - `tests/test_report_assembly.py`
    - 新增 eyeball grade 收集测试。
  - `tests/test_run_stage_flow.py`
    - 首 pass packet 断言改 `grade`，并断言段根 accepted `grade.png` 存在。

## Spec mapping

- §1.1 / ④: `render_overlay.py` 和 `_overlay_transform.py` 已改为 `render_grade.py` / `_grade_transform.py`；产物路径改 `grade.png`。
- §1.2: 颜色轴只表达判定，类别靠线宽/位置/窗口外挂机道或 elevation box。
- §1.3: plan 内墙由 gt zone rect 抽共享边坐标并合并重叠 interval 后画一次。
- §1.4: `abs(delta) > 0.05m` 时画 tol band + gt hairline；tol 取 sidecar `tolerances.wall_tol_m`。
- §1.5 / §7.9: miss window 淡红 ghost + dashed edge；extra/wrong-place 红实框；不做 displaced connector。
- §1.7: reading/correction 两 stage 都支持；单张 grade 合成 plan floors + N/S/E/W elevations。
- §1.8 / §7.2: renderer 不重算命中关系，只读 score sidecar；gt 仅作参考几何。
- §7.4: accepted grade promote 到段根，report eyeball 显式收 reading/correction grade。
- §7.7: empty facade 与 no-data 分开处理。
- §3 gt 隔离: 新增 scoring/rendering loop 全部在 `scripts/tool_scripts/run_stage.py` judge path；未下沉到 `StageRunner`、`step_orchestrator`、correction executor 或 pipeline。

## Validation

- Targeted:
  - `pytest tests/test_render_grade.py tests/test_judge_batch_b.py tests/test_run_stage_flow.py::test_flow_first_pass_packet_has_gt_evidence_before_manifest_save tests/test_report_assembly.py -q`
  - Result: `15 passed`.
- Full:
  - `pytest -q`
  - Result: `426 passed, 9 xfailed, 83 warnings`.
- Optional smoke:
  - `python scripts/tool_scripts/render_grade.py 0_reading case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/0_reading/attempts/001/score_vs_gt.json case_tests/test_baseline/gt/sm21_anchor/gt.json --out /tmp/grade_smoke.png`
  - Result: wrote `/tmp/grade_smoke.png`.

## Claude review points

1. Boundary outline, elevation envelope, and elevation floor lines are neutral gray reference geometry, not judgement color. Current scorer sidecar has no boundary/floor-line hit/miss fields, so they remain non-graded context.
2. Judge packet key changed from `overlay` to `grade`. Tests were updated, but Claude should confirm no external reviewer prompt/parser still expects `overlay`.
3. Extra windows in elevation use the floor's default sill/head band when sidecar has only span data. This follows current scorer data limits; vertical window judgement remains backlog.

## Backlog

- Boundary/envelope judgement in score sidecar -> boundary can use judgement color later. Current neutral color is because the sidecar has no boundary/floor-line hit/miss fields.
