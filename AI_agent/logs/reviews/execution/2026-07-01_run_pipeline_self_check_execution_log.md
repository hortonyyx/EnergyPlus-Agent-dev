# run_pipeline self-check execution log (2026-07-01)

## Files changed

- `src/agent/pipeline.py`
  - Added `capability_profile: str = "rectangular"` to `run_pipeline`.
  - Threaded `capability_profile` into `compute_evidence_debt_from_vector_dir`, `run_correction`, `check_kernel`, `check_correction`, and `check_mep`.
  - Kept the existing A8 pre-core `check_evidence_debt_coverage` sidecar/gate in place.
  - Added post-core inline `check_correction(...)` with `raw_geom=None`, `relied_on_testdata=bool(parsed_testdata)`, and `evidence_debt=evidence_debt`; writes `1_correction/correction_checks.json`.
  - Added post-`run_mep` inline `check_mep(json.loads(mep.model_dump_json()), ...)`; writes `4_mep/mep_checks.json`.
  - Added `_gate_self_check_report(...)` for correction/MEP only. It writes the explicit filename first, raises on blocking checks only for external `run_profile in {"golden", "regression"}`, and logs blocking check ids while continuing for exploratory.
  - Left the kernel gate logic otherwise unchanged; only passed through `capability_profile`.

- `src/agent/execution/case_metadata.py`
  - Added `parse_testdata_text(text) -> dict | None`: blank, invalid JSON, and non-object JSON return `None`; valid JSON objects, including `{}`, return the dict.
  - Added `expected_zone_total_from_testdata(data) -> int | None`: sums `Floor plans[].thermal_zones` integer values, returning `None` when none are present.

- `src/agent/execution/validation_run.py`
  - Reused `expected_zone_total_from_testdata(...)` inside `_expected_zone_total(...)` to remove the duplicated zone-count logic.

- `scripts/tool_scripts/run_stage.py`
  - Reused `expected_zone_total_from_testdata(...)` inside `_expected_zone_total(...)`.
  - No stepwise S4 behavior was changed.

- `tests/test_run_pipeline_self_checks.py`
  - Added inline correction/MEP smoke coverage for exploratory.
  - Added exploratory continue coverage with blocking S1 audit + blocking S4 schedule checks, including artifact and warning assertions.
  - Added strict-profile fail-closed coverage for S1 with report artifact already written.
  - Added run_pipeline vs `validate_case(write_reports=True)` parity coverage for S1/S4 check ids and statuses.
  - Added A8 preservation coverage proving the pre-core evidence coverage sidecar still exists and the full correction report includes `correction.evidence_debt_coverage`.

## Kernel-pairing test decision

I ran:

```bash
python -m pytest tests/test_run_pipeline_self_checks.py tests/test_a8_evidence_routing.py::test_run_pipeline_fail_closed_for_kernel_pairing_gate_profiles -q
```

Result: `7 passed`.

The existing `_minimal_geom()` kernel-pairing fixture was not preempted by S1 after implementing `relied_on_testdata=bool(parsed_testdata)` for testdata `"{}"`. Its structural correction checks passed, so it still reached the kernel InterZone gate. Therefore I did not apply fallback (a) or (b): no fixture change and no assertion change were needed. This is the least invasive outcome and keeps the test focused on the kernel gate.

## Test results

Related sweep:

```bash
python -m pytest tests/test_checks_reading_correction.py tests/test_checks_mep_assembly.py tests/test_a8_evidence_routing.py -q
```

Result: `82 passed`.

Full suite:

```bash
python -m pytest -q
```

Result: `393 passed, 9 xfailed, 36 warnings in 85.99s (0:01:25)`.

The warnings were existing `report_assembly.py` RuntimeWarnings about missing `REPORT.md` AGENT regions in `tests/test_orchestrate_baseline.py`.

## Review-asks / self-report

- No intentional deviation from §9.
- The A8 pre-core sidecar/gate remains in place; the post-core full S1 report is additive.
- The kernel gate was not folded into `_gate_self_check_report`; only correction and MEP use the helper.
- `check_mep` is called with persisted-dict shape via `json.loads(mep.model_dump_json())`.
- `testdata "{}"` parses to `{}` but does not count as reliance because `bool(parsed_testdata)` is false.
- Judgment call: the strict-profile test with both S1 and S4 bad inputs necessarily stops at S1 before MEP. The test asserts S1 report write-before-raise. Exploratory coverage verifies both S1 and S4 blocking artifacts are written and the pipeline still produces `IntakeOutput`.
- Existing untracked files/directories were present before/around this work and were not modified by me except for the new execution log and new test file.
