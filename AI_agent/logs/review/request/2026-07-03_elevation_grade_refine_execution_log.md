# Elevation Grade Refinement Execution Log

Date: 2026-07-04
Executor: Codex
Workspace: `/workspaces/EnergyPlus-Agent-dev`

## Files Changed

- `src/agent/judge/elevation_score.py`
- `src/agent/judge/correction_score.py`
- `src/agent/judge/score_policy.py`
- `src/agent/execution/run_config.py`
- `scripts/tool_scripts/run_stage.py`
- `scripts/tool_scripts/render_grade.py`
- `tests/test_elevation_score.py`
- `tests/test_render_grade.py`
- `tests/test_run_config.py`
- `tests/test_judge_batch_b.py`

Note: the working tree already contained dirty Batch 1/Batch 2 files before this refinement began; those were preserved and edited in place.

## Scoring Algorithm

Association is now 2D overlap-based per facade and per orientation:

- Build gt and read boxes in `(along span) x (z span)` metric space.
- For each read/gt pair, compute:
  `overlap_fraction = intersection_area / min(read_area, gt_area)`.
- A pair is an association candidate only when `overlap_fraction >= elevation_overlap_min`.
- Default `elevation_overlap_min` is `0.25`.
- Reading keeps per-facade orientation selection. Both aligned and interval-reflected flipped orientations are scored using this same overlap test.
- Assignment remains one-to-one and maximizes:
  1. placed hits,
  2. associated pairs,
  3. minimum normalized cost.
- A gt with no associated read is a `miss`.
- A read with no associated gt is an `extra`.
- Therefore a same-along but wrong-floor read with zero vertical overlap is `miss + extra`, not drift.

Accuracy after association:

- `placed_hit` iff all are within tolerance:
  - along-center delta <= `elevation_along_tol_m`
  - sill delta <= `sill_tol_m`
  - head delta <= `head_tol_m`
  - width delta <= `width_tol_m`
- Otherwise the associated pair is `matched_with_z_drift`.
- `width_tol_m` is now a real accuracy gate.
- `overlap_fraction` is emitted on associated elevation match records.

Correction elevation scoring uses the same overlap association while keeping aligned scoring authoritative and flipped scoring as mirror evidence only.

## Config And Schema

- Added `GradeConfig.elevation_overlap_min` with default `0.25`.
- Added `elevation_overlap_min` to `GradeConfig.as_tolerances()`.
- Threaded `elevation_overlap_min` through reading/correction elevation scoring.
- Updated policy evidence to report `width_tol_m` and `overlap_min`.
- Bumped `SCORER_SCHEMA` from `3` to `4`.

## Renderer Changes

- Restored elevation envelope boundary grading from plan/correction `score.boundary`.
- Elevation panels draw the two vertical envelope edges for each floor/facade:
  - green when the corresponding boundary side has a read match,
  - red dashed when that boundary side is missing.
- Elevation windows are sidecar-driven only:
  - gt truth target: faint gray wire,
  - `placed_hit`: green outline on read box, no heavy green fill,
  - `matched_with_z_drift`: orange outline on read box, gray truth underlay, thin center connector,
  - `miss`: red dashed box plus light-red fill on gt truth,
  - `extra`: red solid box plus light-red fill on read box.
- Header legend now includes gray gt truth and outline-only hit encoding.

## Tests

Before changes:

- `python -m pytest -q`
- Result: `451 passed, 9 xfailed, 91 warnings`

After changes:

- Focused: `python -m pytest -q tests/test_elevation_score.py tests/test_render_grade.py tests/test_run_config.py tests/test_gt_discipline.py`
- Result: `36 passed, 18 warnings`
- Full: `python -m pytest -q`
- Result: `454 passed, 9 xfailed, 90 warnings`

Coverage added/updated:

- Partial 2D overlap associates as drift even when along-center is outside tolerance.
- Zero-overlap wrong-floor same-along read is miss + extra.
- Width delta is now an accuracy gate.
- Correction wrong-z/wrong-floor behavior follows overlap semantics.
- Elevation boundary edges render green/red from `score.boundary`.
- Gray truth underlay renders.
- Hit renders as outline-only, not heavy fill.
- Schema/tolerance tests include `elevation_overlap_min`.
- `tests/test_gt_discipline.py` stayed green.

## Demo Renders

Generated in repo:

- `AI_agent/logs/review/renders/2026-07-03_elevation_grade/03_real_sm21_new_visual.png`
  - Size: `24627` bytes
  - Image: `1774x1629 RGB`
- `AI_agent/logs/review/renders/2026-07-03_elevation_grade/04_four_states_new_visual.png`
  - Size: `25426` bytes
  - Image: `1774x1629 RGB`

Trace sidecars also generated:

- `AI_agent/logs/review/renders/2026-07-03_elevation_grade/03_real_sm21_new_visual.score_vs_gt.json`
- `AI_agent/logs/review/renders/2026-07-03_elevation_grade/04_four_states_new_visual.score_vs_gt.json`

## REVIEW-ASK

- Confirm the restored elevation envelope semantics should remain exactly the pre-Batch-2 mapping: elevation panel `N/S/E/W` uses `score.boundary[N/S/E/W]` and draws both vertical envelope edges for that floor band.
- Review whether the status name `matched_with_z_drift` should be renamed later, since it now covers any associated-but-inaccurate axis including along and width.
- Review the synthetic sheet visually for the preferred orange connector strength; it is intentionally thin and sidecar-driven.
- Confirm that saving trace sidecars next to the requested PNGs is acceptable for future render audits.
