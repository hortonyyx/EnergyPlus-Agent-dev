# Elevation Grade Batch 2 Execution Log

Date: 2026-07-03  
Executor: Codex  
Repo: `/workspaces/EnergyPlus-Agent-dev` local working tree, not GitHub `main`

## Scope Completed

Implemented Batch 2 renderer only. Batch 1 scorer/policy/config files were present in the working tree and were not edited for this batch.

## Files Changed

- `scripts/tool_scripts/render_grade.py`
  - Replaced the old fake elevation window rendering path with a real `score_sidecar["elevation"]` renderer.
  - Removed the `_window_meta(gt)` gt-window-height dependency.
  - Removed the old plane-score elevation boundary coloring path from elevation panels.
  - Added sidecar-box drawing for `placed_hit`, `matched_with_z_drift`, `miss`, and `extra`.
  - Added `no elevation score` rendering when the top-level `elevation` section is absent or empty.
  - Labeled plan panels as `plan-derived (secondary)`.
  - Added elevation tolerance text and a `vertical drift` legend swatch.
- `tests/test_render_grade.py`
  - Added elevation-sidecar fixtures and renderer coverage for all elevation statuses.
  - Added sidecar-z authority coverage: elevation boxes render at `read.z` from the sidecar, not gt window heights.
  - Added absent-elevation-section coverage: no fake plane-derived fallback.
  - Added plan secondary-label coverage.
  - Preserved zero-window versus no-data behavior with explicit elevation sidecar records.

## Elevation Visual Encoding

- `placed_hit`: green solid box at `record.read.span x record.read.z`.
- `matched_with_z_drift`: orange/tan solid read box at `record.read.span x record.read.z`, gray truth wire at `record.truth.span x record.truth.z`, plus vertical sill/head drift cue lines.
- `miss`: red dashed box with light-red fill at `record.truth.span x record.truth.z`.
- `extra`: red solid box with light-red fill at `record.read.span x record.read.z`.
- Within-tolerance vertical drift on a `placed_hit`: faint green tolerance band around the truth sill/head line plus a gray truth line, using `sill_tol_m` and `head_tol_m` from `score_sidecar["tolerances"]`.

The renderer does not recompute hit/miss/drift and does not look up window z from gt. In elevation panels, gt is used only for the building envelope rectangle and floor reference lines.

## Empty Data Semantics

- Missing or empty top-level `score_sidecar["elevation"]`: each elevation panel draws `no elevation score`; there is no fallback to the old plane-window plus gt-height panel.
- `no_data=true` on a facade/floor record: that floor band draws `no data`.
- Zero-window facade/floor with `gt_count=0`, `read_count=0`, `matches=[]`, `extras=[]`, and `no_data=false`: renders as an empty floor region, not no-data. This preserves `test_render_grade_empty_facade_is_not_no_data`.

## Real Sheet Rendered

The archived sm21 run sidecar predates Batch 1 and lacks `elevation`, so I synthesized a temporary Batch-1-style elevation section from the real `0_reading` JSON files using `src.agent.judge.elevation_score.score_reading_elevation_dir`.

- Real run: `case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e`
- Elevation summary: `gt_total=15`, `matched_total=15`, `placed_hit_total=15`, `z_drift_total=0`, `miss_total=0`, `extra_total=0`, `no_data_floor_facades=0`
- Temporary sidecar used for render: `/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/fd47b002-1329-44c9-bed3-6cb480f205f3/scratchpad/elev_grade_sm21_reading_score_vs_gt_with_elevation.json`
- PNG: `/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/fd47b002-1329-44c9-bed3-6cb480f205f3/scratchpad/elev_grade_sm21_reading.png`

## Verification

- Focused renderer tests: `python -m pytest -q tests/test_render_grade.py` -> `18 passed, 19 warnings`.
- Full suite: `python -m pytest -q` -> `451 passed, 9 xfailed, 91 warnings`.

## REVIEW-ASK

- Please eyeball the orange `matched_with_z_drift` treatment against the desired visual contrast. It is intentionally not green and not a red miss, but the exact color can be tuned.
- Please confirm the within-tolerance vertical drift cue should be two horizontal tolerance bands around truth sill/head, matching the existing wall-drift band idiom as closely as possible in the elevation coordinate system.
- Please confirm that suppressing plane-derived boundary coloring in elevation panels is desired. I removed it because Batch 2 says elevation panels are sidecar-driven and gt is allowed only for envelope/floor reference lines.
