# 2026-07-02 Flow P1 Batch B 执行日志

## 执行范围

只执行 Batch B（gt 权威 judge evidence）：judge_packet 的 gt 对账 sidecar、score_criteria、attempt overlay，以及对应测试。不做 Batch C 文档重写。

## 逐文件改动

- `src/agent/judge/score_policy.py`
  - 新增 `reading_score_criteria`，将 `FloorScore`/correction 同构 score 转成机读 `score_criteria` evidence。
  - 不写入、不扩展 `StageVerdict`；`StageVerdict` 仍由 judge 主控裁决。
  - 复用 scorer 容差常量：`DEFAULT_WALL_TOL_M=0.30`、`DEFAULT_WIN_CENTRE_TOL_M=0.40`。

- `src/agent/judge/correction_score.py`
  - 新增 correction accepted attempt output scorer。
  - 输入为 `CorrectedGeometry` dump 或对象；不读 flat `1_correction/correction_geometry_snapped.json`。
  - 抽取 correction cells 的 interior partition lines、windows facade spans，复用 `reading_score` 的 gt derivation 和 matcher。
  - floor-name 映射顺序：精确名 > 数字序号（`F1`/`1F`/`Floor 1`）> `z_floor`/顺序兜底。
  - 未匹配 floor/window floor 写入 evidence；窗口 floor alias 也按同套 gt floor 映射归并。

- `scripts/tool_scripts/_overlay_transform.py`
  - 新增纯坐标 `MetricTransform` 和 `plan_transform`。
  - gt 与产物使用同一个 metric→pixel transform。

- `scripts/tool_scripts/render_overlay.py`
  - 新增 judge/tooling overlay 渲染。
  - 从 accepted attempt output 对象渲染，不读 flat stage 目录。
  - gt zone/window 底图为灰/蓝，reading strokes 或 correction cells 为红，写同一 canvas。
  - 图例说明 `clear-space bbox` vs correction centerline 的容差语义，不把系统偏移标成硬错。

- `scripts/tool_scripts/run_stage.py`
  - `_judge_packet` 内懒加载 `load_gt`，仅在 judge path 读 gt。
  - 对 `0_reading`/`1_correction`：
    - 读取 `attempts/NNN/output.json`。
    - 校验 `hash_text(output.json)` 等于 `manifest.accepted(stage).output_hash`。
    - 写 `attempts/NNN/score_vs_gt.json`，字段含 `stage`/`attempt`/`output_hash`/`source="attempt_output"`。
    - 已有 sidecar 复用前校验 hash/stage/attempt/source；不一致则重算。
    - 写 `attempts/NNN/overlay.png`。
    - packet 增加 `score_vs_gt`、`score_criteria`、`overlay`。
  - 无 gt 或非 0/1 stage 时，packet 字段诚实置空：`score_vs_gt=null`、`overlay=null`、`score_criteria=[]`。

- `tests/test_judge_batch_b.py`
  - 新增 Batch B 覆盖。

## 新增测试覆盖

- `test_judge_packet_scores_accepted_reading_attempt_not_mutable_flat`
  - 篡改 mutable flat `0_reading/1f_view.json` 后生成 packet。
  - 断言 sidecar 绑定 manifest accepted attempt hash，且从 `attempts/002/output.json` 生成。
  - 断言 `score_criteria` 只在 packet/sidecar，`StageVerdict(extra="forbid")` 拒绝 `suggested_status`。
  - 断言 sidecar hash 被篡改后会重算。

- `test_correction_scorer_maps_f1_f2_to_gt_floors`
  - 使用 sm21 `F1/F2` correction attempt。
  - 断言映射到 gt `Floor 1/Floor 2`，interior walls 和 windows 命中合理。

- `test_judge_packet_scores_correction_attempt_and_records_floor_map`
  - 断言 correction packet 产 `score_vs_gt`、`overlay`、`score_criteria`，sidecar 记录 floor_map。

- `test_overlay_uses_shared_metric_transform_for_gt_and_product_pixels`
  - 构造小 gt/correction，断言 shared transform 下同一 metric split line 的像素为产物红色，gt cell fill 为灰色。

## pytest 结果

- 聚焦测试：`pytest tests/test_judge_batch_b.py tests/test_gt_discipline.py -q`
  - 结果：`8 passed in 3.79s`

- 邻近回归：`pytest tests/test_run_stage_flow.py tests/test_gt_render.py tests/test_gt_overlay.py -q`
  - 结果：`13 passed in 4.05s`

- 全量回归：`pytest -q`
  - 结果：`410 passed, 9 xfailed, 36 warnings in 111.84s`
  - strict xfail 未 XPASS。
  - `tests/test_gt_discipline.py` 绿。

## gt 隔离检查

- 新增 gt 读取只在：
  - `src/agent/judge/*`
  - `scripts/tool_scripts/run_stage.py` 的 `_judge_packet` judge path lazy import
  - `scripts/tool_scripts/render_overlay.py`
  - 测试
- 未让 `src/validator/checks`、`src/agent/pipeline.py`、`src/agent/execution/*`、`src/agent/correction/*` import gt。

## 自报审阅需求

- `score_policy.py` 中 minor/severe 分级采用：
  - `extra_vwalls+extra_hwalls <= 2` 为 minor，否则 severe。
  - window hit ratio `< 1.0` 但 `>= 0.80` 为 minor，否则 severe。
  brief 规定三类 criterion 和 pass/minor/severe，但未给精确数量阈值；请审阅该分级口径是否需要调整。

- overlay 当前对 `0_reading` 渲染 plan views（用于与现有 `reading_score` 的 floor wall/window 对账一致），跳过 elevation views。若后续要把 elevation gt/window 视觉也并入同一 artifact，可作为后续批次扩展；本批未扩 scope。

## 偏离与取舍

- 无 Batch C 改动。
- 无 golden 文件改动。
- 无 gate①/judge verdict 语义、`run_pipeline`、`CorrectedGeometry` schema/契约改动。
