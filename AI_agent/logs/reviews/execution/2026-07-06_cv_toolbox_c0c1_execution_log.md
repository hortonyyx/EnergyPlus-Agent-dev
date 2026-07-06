# CV Toolbox C0+C1 Execution Log

## Built

- Added `src/agent/reading/cv_toolbox/` with six deterministic tools:
  - `crop_zoom`
  - `wall_line_profiler`
  - `px_m_calibrator`
  - `window_cc_detector`
  - `storey_line_profiler`
  - `overlay_logger`
- Added append-only sidecar support with `cv_schema: "1"`, source image name plus 12-char sha256, crop-chain inverse transforms, reserved Phase B candidate fields, and future integration comments for J0 references, Phase B `anchor_px`, and attempts collection.
- Added `scripts/tool_scripts/cv_probe.py` as a Bash-usable argparse CLI with explicit flags and sidecar plus overlay output.
- Added `skills/intake_pipeline/0_reading/cv_toolbox.md` and a single pointer line in `session_kickoff.md`.
- Extended `tests/test_gt_discipline.py` to scan `src/agent/reading/**/*.py` and `scripts/tool_scripts/cv_probe.py`.
- Added `tests/test_cv_toolbox.py` covering synthetic fixtures, calibrator exact/residual behavior, CC detection and merge, crop round trip, sidecar append-only/schema/crop-chain restore, overlay smoke, sm21 case-data smoke, and CLI end-to-end.

## Verdict API Decisions Applied

- Coordinates are image-local source pixels with top-left origin. Bboxes use half-open `[x0, y0, x1, y1)` convention.
- Cropped tool runs return both crop-local and source-mapped positions, with `crop_chain` recording `local_to_source` and `source_to_local` formulas.
- Line profilers use the clean-vector mask `gray_lo <= mean(rgb) <= gray_hi` and `max(rgb)-min(rgb) <= rgb_tol`, normalized row/column projection, `scipy.signal.find_peaks`, prominence as `strength`, and `peak_widths(..., rel_height=0.5)` for FWHM width.
- `storey_line_profiler` is the same projection kernel as `wall_line_profiler` with `axis="row"` and `candidate_kind="storey_line"`.
- `px_m_calibrator` treats anchors as spans and uses forced-origin least squares: `px_per_m = sum(value_m_i * span_px_i) / sum(value_m_i ** 2)`. Multi-anchor residuals include px and meter residuals; single-anchor residual fields are `null`.
- `window_cc_detector` uses `scipy.ndimage.label` with 8-connectivity, area/shape filters, and fixed-point bbox merging by sorted `(y0,x0,y1,x1)` order using gap/overlap or IoU criteria.
- `overlay_logger` requires `candidate_id`, `status`, and `reason`; it logs accepted, rejected, and undecided decisions and draws green/red/amber overlays.
- Unified tool return structure is `{tool, tool_version, recipe_id, params, results, diagnostics, applicability}`. Results include reserved Phase B fields: `candidate_id`, `candidate_kind`, `coord_space`, `anchor_px`, `visual.*`, `metric.*`, and `provenance`.

## Recipe Constants

`clean_vector_v1` is the single recipe source:

- `gray_lo: 60`, `gray_hi: 230`: seeded directly from the sm21 forensics recipe.
- `rgb_tol: 8`: keeps grayscale CAD strokes while allowing minor export anti-alias variance.
- `prominence: 0.04`: tuned so integer synthetic fixtures pass with exact expected peaks and the full sm21 `case_data/1f_view.png` smoke finds at least five vertical candidates.
- `min_peak_distance_px: 6`: suppresses duplicate peaks for thick synthetic strokes without hiding nearby real wall candidates.
- `min_cc_area_px: 20`: filters small specks while preserving synthetic window rectangles.
- `merge_gap_px: 2`, `merge_overlap_ratio: 0.5`, `merge_iou: 0.2`: deterministic small-gap merge defaults, tuned to merge adjacent synthetic window pieces only when they share substantial overlap on the other axis.
- `calibration_warn_residual_px: 2.0`, `calibration_warn_residual_m: 0.05`: explicit residual warning thresholds used by the calibrator.

## Test Results

Command:

```bash
/opt/venv/bin/python -m pytest tests/test_cv_toolbox.py tests/test_gt_discipline.py
```

Result:

```text
12 passed in 5.97s
```

## Deviations

- No dependency edits were made because the review verdict verified Pillow, NumPy, and SciPy are already direct dependencies.
- No reading/correction schema, gate, judge, pipeline, case, or EnergyPlus behavior was changed.
- `cv_evidence/` is implemented only as a flat-stage audit sidecar. Attempts/report collection is documented and commented as future integration, not current behavior.
