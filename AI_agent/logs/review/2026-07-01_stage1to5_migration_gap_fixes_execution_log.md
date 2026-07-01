# Execution Log: Stage 1-5 Migration Gap Fixes

Date: 2026-07-01
Executor: Codex

## Changes

- `src/validator/checks/mep.py`
  - Extended `_load_refs` so `PEOPLE` also validates `Activity_Level_Schedule_Name`.
  - Uses eppy raw field access `Activity_Level_Schedule_Name`; falls back to `obj.fields[9]` only if raw access fails or is absent.
  - Blank/missing and undefined activity schedules now fail under existing check id `mep.load_to_schedule`.
  - Confirmed `mep.schedule_type_refs` remains separate: it only checks `Schedule:Compact` type-limit references.

- `tests/test_checks_mep_assembly.py`
  - Added fixtures for People missing activity schedule, undefined activity schedule, and clean primary+activity schedules.

- `skills/intake_pipeline/1_correction/A3_arbitration.md`
  - Added the corridor/circulation identity arbitration rule with the "never merge on doubt" guard intact.

- `src/validator/checks/correction.py`
  - Added explicit `NOT_APPLICABLE` cross-check placeholders:
    - `correction.facade_area_residuals`
    - `correction.wwr_residuals`
    - `correction.area_residuals`
    - `correction.unsupported_count_by_severity`
  - Message: `deferred until evidence is richer`.

- `tests/test_checks_reading_correction.py`
  - Added a test asserting the residual placeholder slots exist as `NOT_APPLICABLE` cross-checks.

- `src/validator/checks/kernel.py`
  - Added optional `run_profile` metadata to `check_kernel`.
  - `kernel.pairing_gate` remains an invariant; no policy downgrade was added.

- `src/agent/pipeline.py`
  - After `materialize_kernel_geometry(geom, s2)`, `run_pipeline` now calls `check_kernel(bg, interzone_issues=kernel_issues, run_profile=run_profile)`.
  - Writes the normal CheckReport artifact to `2_modelling/kernel_checks.json`.
  - For `run_profile in {"golden", "regression"}`, raises fail-closed when `kernel_issues` is non-empty.
  - Exploratory/dev behavior continues to write artifacts and proceed.
  - Did not overload `run_state`; visibility flows through the existing gate report channel.

- `src/agent/execution/validation_run.py`
  - Passes active `run_profile` into rebuilt kernel CheckReports for consistent report metadata.

- `tests/test_a8_evidence_routing.py`
  - Added exploratory injected-InterZone test proving:
    - `kernel.pairing_gate` is fail/block severity in `kernel_checks.json`.
    - `build_evidence_index()` produces `E:gate:2_modelling:kernel.pairing_gate`.
    - downstream exploratory artifacts still exist.
  - Added golden/regression fail-closed tests.

## Tests

- `pytest tests/ -k "mep or checks_mep or schedule" -q`
  - `30 passed, 356 deselected`

- `pytest tests/test_checks_reading_correction.py -q`
  - `48 passed`

- `pytest tests/test_a8_evidence_routing.py tests/test_pipeline_kernel_wiring.py tests/test_checks_kernel.py -q`
  - `24 passed`

- `pytest -q`
  - `381 passed, 9 xfailed, 36 warnings`
  - Count delta from stated baseline: `+7` passing tests:
    - +3 MEP People activity schedule tests
    - +1 correction residual placeholder test
    - +3 S23 InterZone pipeline/profile tests

## Legacy Anchor Check

Read-only check of existing sm20/sm21 artifacts:

- `sm20_anchor/run_2026-06-15_baseline`
  - `kernel_gate_report.json`: `gate_issues=0`
  - `kernel_checks.json`: `kernel.pairing_gate=pass`

- `sm21_anchor/run_2026-06-16_opus_e2e`
  - `kernel_gate_report.json`: `gate_issues=0`
  - `kernel_checks.json`: `kernel.pairing_gate=pass`

- `sm21_anchor/run_2026-06-20_gpt54_reading`
  - `kernel_gate_report.json`: `gate_issues=0`
  - `kernel_checks.json`: `kernel.pairing_gate=pass`

Golden artifacts touched: none.

## Review-Asks For Claude

- Re-verify People activity schedule locator:
  - Implementation point: `src/validator/checks/mep.py:153-190`.
  - Raw access worked in a direct eppy probe via `obj.raw.Activity_Level_Schedule_Name`.
  - Normal parsed People layout has the fallback value at `obj.fields[9]`.

- Re-verify S23 plumbing point:
  - Implementation point: `src/agent/pipeline.py:862-895`.
  - `run_pipeline` calls `materialize_kernel_geometry()`, then emits `2_modelling/kernel_checks.json` via `check_kernel(..., interzone_issues=kernel_issues, run_profile=run_profile)`.
  - The report surfaces through existing `kernel.pairing_gate` invariant rows; `summarize_gates()` and `build_evidence_index()` consume it as `E:gate:...`.

- Re-verify golden artifact impact:
  - No golden artifact files were modified.
  - Existing sm20/sm21 kernel gate issues are empty and `kernel.pairing_gate` is `pass`.

- Re-verify test count delta:
  - Full suite result is `381 passed, 9 xfailed`.
  - Delta is explained by 7 new passing tests.

