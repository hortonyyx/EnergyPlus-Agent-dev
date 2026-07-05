# Reading Phase A Batch 1 Execution Log

Date: 2026-06-30

Scope implemented: A3, A7, A1, A2, A4 only.

## Summary

- Added `RunPolicy.run_profile` with default `exploratory`; evidence debt flags in `exploratory`/`dev` and blocks in `golden`/`regression`.
- Added machine-readable reading evidence allowlist and report signals:
  - `reading_syntax_valid`
  - `reading_evidence_clean`
  - `j0_semantic_clean`
  - `pipeline_recovered`
- Preserved raw reading field presence as sidecar metadata:
  - `raw_has_dimensions`
  - `raw_has_uncaptured`
  - `legacy_migrated`
- Hardened reading evidence checks:
  - dimension chains close by `(chain_id, axis)`;
  - incomplete chains and missing chain ids are evidence debt;
  - `dimension_derived` strokes must cite resolvable dimensions;
  - dimensioned views must have dimensions;
  - non-legacy dimensions in dimensioned views must carry P1a fields.
- Added sm21 dimensioned-view metadata in `case_data/testdata_prompt.json`.

## Run Profile Threading

- `src/agent/execution/policy.py`: `RunPolicy.run_profile`.
- `src/validator/checks/schema.py`: `CheckReport.run_profile` and disposition mapping.
- `src/agent/execution/validation_run.py`: passes `policy.run_profile` into reading checks and error reports.
- `scripts/tool_scripts/run_stage.py`: added `--run-profile`; passes policy into `0_reading` checks.
- `scripts/tool_scripts/record_baseline.py`: added `--run-profile`; writes signals into `_run/baseline.json`.
- `scripts/tool_scripts/report_assembly.py`: renders signal/status context and prevents a clean status when reading evidence is red.

Default remains `exploratory`.

## Evidence Check Allowlist

Defined in `src/validator/checks/schema.py` as `EVIDENCE_CHECK_IDS`:

- `reading.dimension_chain_closure`
- `reading.dimension_derived_refs`
- `reading.dimensions_present`
- `reading.dimension_p1a_fields`
- `reading.raw_field_presence`
- `reading.stroke_provenance_coverage`

`reading.stroke_provenance_coverage` is allowlisted for machine readability, but A5 behavior was not implemented in this batch.

## Dimensioned Metadata

- Declared in `case_tests/e2e_tests/sm21_anchor/case_data/testdata_prompt.json` via:
  - `Floor plans[].dimensioned`
  - `dimensioned_views`
- Read by `src/agent/execution/case_metadata.py`.
- Passed into validators from `validate_case` and `run_stage.py`.
- No validator imports GT or judge scoring code.

## Test Changes

- `tests/test_checks_reading_correction.py`
  - Added tests for `(chain_id, axis)` closure, incomplete/non-closing chains, dimensioned empty dimensions, P1a fields, `dimension_derived` refs, run-profile gating, legacy grandfathering, and raw-presence sidecar metadata.
  - Updated `test_broken_dimension_chain_flags_not_blocks` to include `axis`; the old fixture relied on the previous loose closure behavior.
- `tests/test_orchestrate_baseline.py`
  - Added signal assertions to gate rollup/report status tests.
  - Added baseline/report signal presence checks.

## Verification

- Targeted:
  - `python -m pytest tests/test_checks_reading_correction.py -q` -> 42 passed
  - `python -m pytest tests/test_orchestrate_baseline.py -q` -> 29 passed, 1 xfailed
  - `python -m pytest tests/test_validation_run_baseline.py -q` -> 10 passed, 8 xfailed
  - `python -m pytest tests/test_execution_foundation.py -q` -> 20 passed
- Full suite:
  - `python -m pytest -q` -> 359 passed, 9 xfailed, 36 warnings

Extra grandfathering check:

- `sm21_anchor/run_2026-06-16_opus_e2e` under `run_profile=regression`: no `0_reading` blocks.
- `sm20_anchor/run_2026-06-15_baseline` under `run_profile=regression`: no `0_reading` blocks.

## Existing Golden/Baseline Impact

No existing golden/baseline test required weakening. The full suite passed with the existing xfail set. New evidence debt may change gate counts and signals in newly recorded baselines, which is intended Phase A behavior.

## Uncertainty

No uncertainty on flag vs block for A1/A2/A4/A7: all new evidence debt uses the evidence allowlist and run-profile policy. `pipeline_recovered` is currently a report signal derived from correction audit sidecars, not a gate.
