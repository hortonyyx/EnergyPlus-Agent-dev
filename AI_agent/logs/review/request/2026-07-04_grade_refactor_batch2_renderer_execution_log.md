# Grade Refactor Batch 2 Renderer Execution Log

Date: 2026-07-04

Scope: Batch 2 renderer rewrite for the schema-6 grade sidecar. Batch 1 scorer/config files were already dirty in the local tree and were not refactored here except for one legacy renderer fixture in `tests/test_judge_batch_b.py`.

## Files Changed By This Batch

- `scripts/tool_scripts/render_grade.py`
- `tests/test_render_grade.py`
- `tests/test_judge_batch_b.py`
- `case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/0_reading/attempts/001/score_vs_gt.json`
- `AI_agent/logs/review/renders/2026-07-03_elevation_grade/05_real_sm21_v6.png`
- `AI_agent/logs/review/renders/2026-07-03_elevation_grade/06_all_states_v6.png`
- `AI_agent/logs/review/request/2026-07-04_grade_refactor_batch2_renderer_execution_log.md`

## Renderer Encoding

Plan walls:

- Gray GT base is drawn from `gt` / `gt_intervals`.
- Product overlays are drawn only from `product` / `product_intervals`.
- `complete` draws all product intervals green.
- Piece-level rendering:
  - `matched`: green solid at product coordinates.
  - `missing`: dashed miss annotation at GT coordinates, orange when `within_tol`, otherwise red.
  - `extra`: solid product segment at product coordinates, orange when `within_tol`, otherwise red.
- The active renderer no longer uses `_interior_coords` or derives product wall length from GT zones.

Plan windows:

- Gray GT lane base is drawn from `gt` / `gt_intervals`.
- Product overlays are drawn only from `product` / `product_intervals`.
- Piece semantics match plan walls: matched green, missing dashed, extra solid, orange for within tolerance.

Plan footprint boundary:

- Existing sidecar-driven `_draw_plan_boundary` remains: green thick hit, red dashed miss, gray truth boundary when absent.

Elevation windows:

- Gray GT boxes are drawn as the truth base.
- Product boxes are drawn only from `product_box`.
- `complete`: green product outline.
- `within_tol`: orange product box with orange tolerance fill.
- `miss`: red dashed GT annotation only.
- `extra`: red solid product box.
- The renderer no longer recognizes legacy `placed_hit` / `matched_with_z_drift` as elevation status names.
- Facade `orientation=flipped` or `ambiguous` shows a small cue in the elevation panel.

Elevation vertical boundary:

- Drawn from serialized `elevation.boundary[facade].floors[floor].side_left/side_right`.
- No W/E/S/N facade-side mapping is re-derived in the renderer.
- `complete`: green thick product coordinate.
- `within_tol`: orange thick product coordinate.
- `miss`: red dashed GT coordinate.
- `no_data`: gray reference line.

Elevation floor/ground/roof lines:

- Drawn from `elevation.floor_lines[facade]`.
- GT lines are gray.
- Matched product lines are green, orange when `within_tol`.
- GT-line miss is red dashed.
- Product-line extra is red solid.
- `no_data` is gray text/line treatment, distinct from a red miss.

Legend/header:

- Updated to green=complete, orange=within-tol, red dashed=miss, red solid=extra, gray=GT truth/no-data.
- Plan panels remain labeled `plan-derived (secondary)`.
- Absent elevation sidecar still reports `no elevation score` rather than manufacturing score fallbacks.

## Red-Line Renderer Tests

`tests/test_render_grade.py` now uses schema-6-shaped sidecars and includes product-vs-GT coordinate tests:

- `test_render_grade_red_line_plan_wall_uses_product_extent_not_gt_extent` creates a wall where product is half the GT extent. It asserts the green product overlay appears on the product half and not on the uncovered GT half; the uncovered half is checked for dashed red miss pixels.
- `test_render_grade_red_line_plan_window_uses_product_span_not_gt_span` creates a plan window whose product span is offset from GT. It asserts green appears at the product lane coordinates and not at the GT lane coordinates.
- `test_render_grade_red_line_elevation_window_uses_product_box_not_gt_box` creates an elevation window with a product box far below/right of the GT box. It asserts the green product outline is at `product_box` and not at `gt_box`.

Preserved coverage:

- `test_render_grade_empty_facade_is_not_no_data` remains and verifies a zero-window facade is not rendered as no-data.
- `tests/test_gt_discipline.py` remains green.
- A legacy transform test in `tests/test_judge_batch_b.py` was updated to carry schema-6 product geometry instead of relying on scalar wall records.

## Demo Renders

Fresh real SM21 schema-6 sidecar regenerated from:

- `reading_score.score_reading_dir`
- `elevation_score.score_reading_elevation_dir`
- `GradeConfig()` defaults

Written sidecar:

- `case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/0_reading/attempts/001/score_vs_gt.json`

PNG outputs:

- `AI_agent/logs/review/renders/2026-07-03_elevation_grade/05_real_sm21_v6.png`
  - dimensions: `1774x1629`
  - bytes: `26475`
- `AI_agent/logs/review/renders/2026-07-03_elevation_grade/06_all_states_v6.png`
  - dimensions: `1224x1069`
  - bytes: `20689`

Both files exist and are non-trivial size.

## Tests

- Targeted: `python -m pytest tests/test_render_grade.py tests/test_gt_discipline.py -q` -> `22 passed`.
- Targeted after legacy fixture update: `python -m pytest tests/test_judge_batch_b.py::test_grade_uses_shared_metric_transform_for_gt_and_sidecar_pixels tests/test_render_grade.py tests/test_gt_discipline.py -q` -> `23 passed`.
- Full final: `python -m pytest -q` -> `465 passed, 9 xfailed, 89 warnings in 86.65s`.

## REVIEW-ASK

- Confirm the small textual `flip` / `ambig` cue is sufficient, or specify a preferred icon/marker style for orientation normalization.
- Confirm whether ignored review-render PNGs should stay as local artifacts only; they exist at the requested paths but are ignored by the repository `.gitignore` pattern.
- Review the no-data visual treatment: it is gray/subtle rather than red to preserve the miss vs no-data distinction.
