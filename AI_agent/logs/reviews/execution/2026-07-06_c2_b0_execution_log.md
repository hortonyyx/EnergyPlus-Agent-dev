# C2 B0 Execution Log

Date: 2026-07-06
Branch: `6.15_ValidationArchM0toM4`
Batch: B0 (`schema_version` mechanism, profile threading, parent-wall unique attribution, coverage/adjacency helper consolidation)

## Brief Audit

- Read `logs/reviews/request/2026-07-06_c2_b0_batch_brief.md`.
- Read `AI_agent/proposals/c2_orthogonal_polygon_design.md`.
- The requested verdict path `logs/reviews/verdict/2026-07-06_c2_design_review.md` was absent. The matching verdict exists at `AI_agent/logs/reviews/verdict/2026-07-06_c2_design_review.md` and was read.
- No blocking scope contradiction found. The brief matches D1, D4 first-half, D5 helper-only, D8 B0, and D10 #4/#7. The verdict path mismatch is a documentation/location issue, not a change to what B0 builds.

## Changes

### D1: `CorrectedGeometry.schema_version` + schema/profile gate

- Added shared schema constant:
  - `src/agent/correction/constants.py:1`
- Added `CorrectedGeometry.schema_version` defaulting to `"1"`:
  - `src/agent/correction/schema.py:19`
  - `src/agent/correction/schema.py:73`
- Added schema/profile registry and check ids:
  - `src/agent/geometry/capability.py:11`
  - `src/agent/geometry/capability.py:18`
  - `src/agent/geometry/capability.py:21`
  - `src/agent/geometry/capability.py:57`
- Added gate ① check `correction.schema_version_supported` and profile/data-shape check:
  - `src/validator/checks/correction.py:31`
  - `src/validator/checks/correction.py:97`
  - `src/validator/checks/correction.py:108`
- Deterministic core now reads the contract before mutating geometry:
  - `src/agent/correction/deterministic.py:702`
  - `src/agent/correction/deterministic.py:716`
- A0 registry and bump rule added:
  - `skills/intake_pipeline/1_correction/A0_contract.md:213`
  - `skills/intake_pipeline/1_correction/A0_contract.md:229`
  - `skills/intake_pipeline/1_correction/A0_contract.md:233`

### D1/D10 #4: `capability_profile` threaded into kernel and builders

- Geometry builder signatures and calls:
  - `src/agent/geometry/build.py:31`
  - `src/agent/geometry/build.py:37`
  - `src/agent/geometry/build.py:46`
  - `src/agent/geometry/modelling.py:355`
  - `src/agent/geometry/modelling.py:371`
  - `src/agent/geometry/split_pairing.py:46`
  - `src/agent/geometry/split_pairing.py:52`
- Pipeline and validation rebuilds:
  - `src/agent/pipeline.py:678`
  - `src/agent/pipeline.py:702`
  - `src/agent/pipeline.py:891`
  - `src/agent/pipeline.py:946`
  - `src/agent/execution/validation_run.py:177`
- Step runner and CLI:
  - `scripts/tool_scripts/run_stage.py:160`
  - `scripts/tool_scripts/run_stage.py:181`
  - `scripts/tool_scripts/run_stage.py:208`
  - `scripts/tool_scripts/run_stage.py:216`
  - `scripts/tool_scripts/run_stage.py:1041`
  - `scripts/tool_scripts/run_stage.py:1275`
  - `scripts/tool_scripts/run_stage.py:1426`
  - `scripts/tool_scripts/run_stage.py:1631`

### D4 first-half/D10 #7: parent-wall unique attribution

- `_find_parent_wall` now collects same-zone, same-facade-normal exterior wall segment candidates and accepts exactly one strict span containment. Seam hits or multiple matches raise instead of silently taking the last match:
  - `src/agent/geometry/modelling.py:302`
  - `src/agent/geometry/modelling.py:312`
  - `src/agent/geometry/modelling.py:331`
  - `src/agent/geometry/modelling.py:338`
  - `src/agent/geometry/modelling.py:343`

### D5 helper-only: coverage/adjacency consolidation

- Added shared adjacency helper:
  - `src/agent/geometry/adjacency.py:8`
  - `src/agent/geometry/adjacency.py:15`
- Split-pairing by-floor grouping now uses the helper:
  - `src/agent/geometry/split_pairing.py:62`
- Kernel coverage expected-interface area now uses the shared helper:
  - `src/validator/checks/kernel.py:237`

## Tests Added

- `tests/test_c2_b0.py:65`: `schema_version` default `"1"` and unknown version invariant fail.
- `tests/test_c2_b0.py:75`: `orthogonal_polygon` profile accepts v1 data; simulated future polygon-declared schema fails under rectangular profile.
- `tests/test_c2_b0.py:96`: default v1 and explicit v1 produce byte-identical deterministic geometry dictionary.
- `tests/test_c2_b0.py:103`: synthetic seam window raises parent-wall ambiguity.
- `tests/test_c2_b0.py:136`: kernel coverage evidence matches the shared expected-interface helper.
- `tests/test_check_parity.py` was run; the new correction gate checks are in the normal report path and parity remains green.

## Verification

- Baseline from brief: 500 passed, 9 xfailed.
- Targeted run:
  - `python -m pytest -q tests/test_c2_b0.py tests/test_checks_kernel.py tests/test_kernel_guards.py tests/test_pipeline_kernel_wiring.py tests/test_check_parity.py`
  - Result: 34 passed.
- Flow compatibility rerun after CLI default fix:
  - `python -m pytest -q tests/test_run_stage_flow.py tests/test_c2_b0.py tests/test_check_parity.py`
  - Result: 13 passed.
- Full run:
  - `python -m pytest -q`
  - Result: 505 passed, 9 xfailed, 115 warnings.

## Deviations / Notes

- The verdict file was not present at the brief's `logs/...` path; the equivalent verdict was present and read under `AI_agent/logs/...`.
- B0 did not enable schema `"2"` behavior. The profile mismatch test uses a monkeypatched registry entry to exercise the mechanism without adding a B1+ behavior path.
- No golden files were intentionally changed.
- Existing untracked brief file under `logs/reviews/request/` was left untouched.
