# Facade Frame Cross-Check Execution Log

Date: 2026-07-06
Branch: `6.15_ValidationArchM0toM4`

## Brief Audit

- `derive_facade_frame` API matches the brief: it takes `view_facade`, `footprint_x`, `footprint_y`, `mirrored`, and `local_x_positive`, then returns a single-plane frame with `to_world_along()`.
- Reading elevation artifacts have the required local data with a minor adaptation: windows are `pen == "window"` strokes whose local along-facade span is `geometry.x_range_m`. There is no separate `along_x` field.
- Authoritative envelope/footprint bounds are available at correction-check time from accepted `CorrectedGeometry.footprint_x/y`.
- No blocker found; proceeded without schema changes, prompt changes, gt reads, or `facade.py` edits.

## Changes

- Added `correction.facade_frame_cross_check` to `check_correction` as a CROSS_CHECK-only result:
  - Entry point and parameter: `src/validator/checks/correction.py:83`
  - Reading elevation window extraction: `src/validator/checks/correction.py:226`
  - Honest `NOT_APPLICABLE` degradation: `src/validator/checks/correction.py:293`
  - `derive_facade_frame` projection and greedy nearest-along matching: `src/validator/checks/correction.py:331`
  - Per-window flag evidence: `src/validator/checks/correction.py:406`
- Wired reading-stage artifacts into both correction-check consumers:
  - `validate_case`: `src/agent/execution/validation_run.py:127`, `src/agent/execution/validation_run.py:157`
  - `run_pipeline`: `src/agent/pipeline.py:825`, `src/agent/pipeline.py:927`
- Added named tolerance:
  - Loader field/validation: `src/agent/correction/config.py:58`, `src/agent/correction/config.py:104`
  - YAML config: `src/configs/correction.yaml:102`
  - A0 registry: `skills/intake_pipeline/1_correction/A0_contract.md:187`
- Added tests for PASS, FLAG evidence, NOT_APPLICABLE, and West E/W sign consistency:
  - `tests/test_checks_reading_correction.py:786`
  - `tests/test_checks_reading_correction.py:796`
  - `tests/test_checks_reading_correction.py:813`
  - `tests/test_checks_reading_correction.py:820`

## Tolerance Rationale

`facade_frame_cross_check_tol_m = 0.300`.

This check compares two artifacts across the reading/correction boundary: deterministic elevation local-x placement against the correction LLM's world window placement. It is a flag-only placement sanity check, not a snap/grid operation. I aligned it with `ENVELOPE_RECONCILE_TOL` because the expected harmless disagreement is wall-thickness/envelope-basis scale; window geometry itself still uses the finer `window_snap_grid_m`.

## Real-Data Probe

Run directory:
`case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e`

Read-only probe command loaded `1_correction/correction_geometry_snapped.json` plus all `0_reading/*_view.json` files and ran `check_correction(..., reading_views=views)`.

Result:

- Status: `PASS`
- Flag count: 0
- Blocking count: 0
- Matches checked: 15
- Unusable inputs: 0
- Unmatched reading windows: 0
- Unmatched correction windows: 0
- Sample flag: none; no facade-frame mismatches were produced.

## Verification

- Focused: `python -m pytest tests/test_checks_reading_correction.py tests/test_check_parity.py -q`
  - `54 passed`
- Affected core/kernel compatibility rerun:
  - `python -m pytest tests/test_deterministic_core.py tests/test_kernel_guards.py tests/test_checks_reading_correction.py tests/test_check_parity.py -q`
  - `91 passed`
- Full: `python -m pytest -q`
  - `509 passed, 9 xfailed, 115 warnings`

No golden files were changed.

## Deviations

- Minor adaptation from brief wording: elevation windows do not expose a field literally named `along-x`; the existing artifact shape uses `geometry.x_range_m` on window rect strokes.
- Existing direct `CoreTolerances(...)` tests construct the dataclass manually, so the new validator-only tolerance has a default (`0.30`) while the YAML loader still reads the named config value.
- The request brief file is untracked in this worktree and was read only; it was not modified.
