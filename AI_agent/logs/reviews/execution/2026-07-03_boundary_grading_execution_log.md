# Boundary grading execution log (2026-07-03)

## §5 review answers

- a｜reading 边界提取：采用贴边 `wall` 描边提取，符合当前 reading 契约。若同层存在 `wall`/`window` primitive 但四边无贴边 wall，按漏画外墙判 `miss`；若整层无 `wall`/`window` primitive，则 `boundary=None`，sidecar 不写 `boundary`，renderer 保持 no-data 灰。
- b｜correction 边界源：`footprint_x`/`footprint_y` 是 correction 输出里的显式 envelope，优先使用；缺失或不可用时，judge scorer 内部从 cells 外包 bbox 兜底，不改变 correction schema。
- c｜`scorer_schema`：放在 `score_vs_gt.json` 顶层，常量为 `"2"`；`_load_valid_score_sidecar` 将其纳入严格身份匹配，旧 sidecar 会自动重算补齐 boundary。
- d｜score_criteria：新增 advisory-only `boundary_complete`，记录 boundary 命中数、miss 数、no-data 楼层数；不混入现有 interior wall 统计。
- e｜楼板线：本批次不判。gt/scorer 没有独立楼板线元素，renderer 继续把 elevation floor slab 水平线画成中性灰。

## Implementation map

- `src/agent/judge/reading_score.py`
  - `FloorScore.boundary: dict[str, LineMatch] | None`
  - `extract_reading_boundary()` 只从贴边 `wall` strokes 提取 S/N/W/E 坐标。
  - `match_boundary()` 复用 `_match_lines` 的单坐标匹配语义，用 `wall_tol` 判四边。

- `src/agent/judge/correction_score.py`
  - 新增 correction boundary 提取：显式 footprint 优先，cells bbox 兜底。
  - 每个 mapped floor 都写入 `FloorScore.boundary`，容差同 `wall_tol`。

- `src/agent/judge/score_policy.py`
  - 新增 `boundary_complete` criterion，advisory-only。

- `scripts/tool_scripts/run_stage.py`
  - 新增 `SCORER_SCHEMA = "2"`。
  - sidecar 顶层写 `scorer_schema`。
  - `_load_valid_score_sidecar` 严格匹配 schema，旧 sidecar 自动重算。
  - `_floor_score_dict` 在有 boundary 判定时序列化 `scores[*].boundary`。

- `scripts/tool_scripts/render_grade.py`
  - plan footprint 四边：有 `boundary` 判定则 hit 绿 / miss 红虚；无字段保留灰色参考。
  - elevation facade 外框：按每层对应 facade boundary 给左右外框竖边上色；楼板水平线仍灰。
  - renderer 只消费 sidecar 判定字段，不自行判断对错。

## Tests added/updated

- `tests/test_reading_score.py`
  - reading boundary hit/delta、missing boundary miss、empty floor no-data。

- `tests/test_judge_batch_b.py`
  - correction boundary hit/miss/delta。
  - correction footprint missing 时 cells bbox 兜底。
  - sidecar 包含 `scorer_schema`。
  - old schema sidecar 触发重算并补 `boundary`。

- `tests/test_render_grade.py`
  - boundary hit 绿、miss 红虚、无字段灰。
  - elevation boundary 上色，同时 slab 线保持灰。

## Self-review points

- 改动限定在 judge path：`src/agent/judge/`、`scripts/tool_scripts/run_stage.py`、`scripts/tool_scripts/render_grade.py`，未下沉到 execution/correction/pipeline。
- 未修改 reading/correction/IntakeOutput 契约，未重录 golden。
- 旧 sidecar 兼容路径：无 `boundary` 字段的 sidecar 会渲成灰；经 run_stage 重新判分时因 `scorer_schema` 不匹配自动重算。
- 局部验证已跑：`pytest tests/test_reading_score.py tests/test_judge_batch_b.py tests/test_render_grade.py tests/test_gt_discipline.py`，36 passed。
