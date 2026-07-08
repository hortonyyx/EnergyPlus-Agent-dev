# Render Parity and Grading Frame Execution

Date: 2026-07-08

## Scope

Implemented the six requested work items after sm24 manual viewer review.

## W1: Judge-Off Correction Renders

- `scripts/tool_scripts/run_stage.py` now calls `_render_stage()` after every
  stage closeout in both `cmd_run` and `cmd_flow`, independent of judge mode.
- `_judge_packet()` keeps its existing render call; duplicate calls overwrite
  the same files and remain harmless.
- Added a regression test proving `judge=off` still writes correction render PNGs.

## W2: Correction Renders Aligned With Reading

- `render_corrected_geometry.py` now emits per-floor reading-aligned plan renders:
  - `plan_<floor>_render.png`: cell/polygon wall centerlines in dark wall color,
    windows in reading-blue.
  - `roles_<floor>.png`: correction-only role-colored room plan.
- `render_elevation_windows.py` now emits per-facade elevation renders:
  - `elev_<facade>_render.png`: facade outline, floor lines, and window boxes.
- Legacy `zones.png` and `elev.png` are retained for compatibility.
- `run_stage._render_stage()` writes both the new split renders and the legacy
  renders.
- `report_assembly.py`, `new_case_guide.md`, and the J1 rubric now list/copy the
  new correction render artifacts.
- Generated new sm24 correction renders under:
  - `case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/1_correction/`

## W3: Concave Polygon Viewer Triangulation

- `render_geometry_viewer.py` no longer fan-triangulates every polygon from
  vertex 0.
- Added JS-side projection + ear clipping for rings with 5+ vertices; degenerate
  cases fall back to the old fan triangulation so the viewer remains robust.
- Regenerated:
  - `case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/manual_review/geometry_viewer.html`

## W4: Structural Snap Grid

- Changed `src/configs/correction.yaml`:
  - `structural_snap_grid_m: 0.050` -> `0.010`
- Updated comments and the A0 correction contract so clustering owns identity /
  de-jitter while the grid only regularizes output. This preserves 0.12 m /
  0.06 m wall-centerline truths from dimensioned drawings.

## W5: Centerline-To-Outer-Skin Correction Scoring

- Added `wall_thickness_m: 0.24` and a source note to
  `case_tests/test_baseline/gt/sm21_anchor/gt.json`.
- `score_correction_geometry()` now expands correction boundary centerlines
  outward by `wall_thickness_m / 2` when gt declares wall thickness.
- Correction wall segments that touch the outer boundary also expand their span
  endpoints outward by `wall_thickness_m / 2`; interior wall coordinates remain
  axis-to-axis and windows remain unchanged.
- Added tests for boundary and edge-wall span conversion.

## W6: sm21 2026-07-02 Read-Only Audit

Read-only reran correction scoring in memory against:

- Run:
  `case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e`
- Input:
  `1_correction/correction_geometry_snapped.json`
- GT:
  updated sm21 gt with `wall_thickness_m: 0.24`

Results after the new scoring frame:

- Floor map: `Floor 1 -> Floor 1`, `Floor 2 -> Floor 2`.
- Floor 1: walls `4/4`, plan windows `3/3`, boundary `4/4`, max wall offset `0.0 m`.
- Floor 2: walls `5/5`, plan windows `4/4`, boundary `4/4`, max wall offset `0.0 m`.
- Elevation windows: `15/15` matched, `15/15` complete, no z drift, no extras.
- Remaining correction-vs-gt boundary residuals:
  - Floor 1: S/W `-0.02 m`, N/E `+0.02 m`.
  - Floor 2: S/W `-0.02 m`, N/E `+0.02 m`.
- Interpretation: the residual is historical old-run damage from the former
  50 mm grid (`0.12 -> 0.10`, `14.88 -> 14.90`, etc.). New runs with the 10 mm
  grid should preserve these centerline values.
- Existing reading sidecar for the same run remains perfectly aligned to gt
  boundary (`0.0 m` deltas), as expected because reading is outer-skin faithful.

## Tests

- Focused suite:
  - `pytest -q tests/test_run_stage_flow.py tests/test_judge_batch_b.py tests/test_render_grade.py tests/test_deterministic_core.py tests/test_run_config.py tests/test_geometry_viewer.py tests/test_c2_b1_cell_polygon.py tests/test_c2_b1_winding.py`
  - Result: `90 passed, 25 warnings`
- Report/routing suite:
  - `pytest -q tests/test_report_assembly.py tests/test_orchestrate_baseline.py::test_record_baseline_report_lists_eyeball_items tests/test_run_stage_flow.py tests/test_judge_batch_b.py tests/test_render_grade.py`
  - Result: `44 passed, 27 warnings`
- Full suite excluding network-dependent zone-agent test:
  - `pytest -q --ignore=tests/test_zone_agent.py`
  - Result: `559 passed, 9 xfailed, 116 warnings`

The test count increased from the stated `556 passed + 9 xfailed` baseline by
three passing tests: judge-off correction render, boundary centerline expansion,
and edge-wall span expansion.

## Residual

- No git commit was made.
- Existing unrelated dirty/untracked workspace files were left untouched.

## Amendment (Fable 5, 2026-07-08, sm24 resample incident — 4 fixes)

Resampling sm24 1_correction (to pick up the 10mm grid) burned the 3-draw budget and exposed four
defects, all fixed + tested (tests/test_c2_b1_winding.py +3):

1. **Closed-ring polygon is encoding, not geometry** — DeepSeek attempt 3 repeated the first vertex
   at the ring end and the draw was burned on it. `normalized_ccw_polygon()` now canonicalizes both
   winding AND explicit closure (strip duplicate closing vertex); draw-level checks accept closed
   rings (`allow_closed`); gate① post-core stays strict.
2. **Seam rewrite attempted, then REVERTED** — first analysis blamed `_find_parent_wall`'s seam
   band for the win_W03_conf raise ("free ends are not seams") and relaxed it; the B0 contract test
   (`test_window_on_wall_segment_seam_fails_kernel_build`) caught the relaxation as a behavior break.
   Re-diagnosis: the raise was CORRECT — the blocked draw's window really did end on the
   conference|west_office facade seam; the actual defect was item 3 (consuming a blocked draw).
   Original seam semantics restored verbatim; the ±0.05 band already absorbs the observed 1e-6
   float noise. Lesson repeated: don't fix the alarm, fix what set it off.
3. **Stage-root files ≠ accepted attempt (state-consistency defect)** — a blocked resample draw that
   passed draw-checks but failed gate① still overwrote `1_correction/correction_geometry_snapped.json`;
   2_modelling then consumed the BLOCKED draw's geometry (manifest pointer was правильный attempt 1
   throughout). `_load_snapped` + `_render_geometry_viewer` are now manifest-first (read the accepted
   attempt's archived output.json, stage-root fallback for standalone use). Full promote-on-accept
   discipline for stage-root files remains a follow-up.
4. **No human-triage budget affordance** — quarantine counts existing attempt dirs, so a post-fix
   redo was impossible without falsifying history. New explicit `--budget-draws N` global flag
   (provenance-visible; attempt dirs stay append-only).
