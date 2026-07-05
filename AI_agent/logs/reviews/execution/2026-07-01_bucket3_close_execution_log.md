# Bucket ③ close execution log

Date: 2026-07-01

## Files changed

- `src/agent/pipeline.py`
  - Replaced the S2 manual `kernel_checks.json` write plus InterZone-only strict raise with `_gate_self_check_report(stage_name="2_modelling", report=kernel_report, stage_dir=s2, filename="kernel_checks.json", run_profile=run_profile)`.
  - Kept `check_kernel(..., run_profile=run_profile)` unchanged.
  - Added lazy `check_assembly` import immediately after `assemble_intake_output(...)`.
  - Wrote `5_intakeoutput/assembly_checks.json` before the existing `validate_contract(...)` block, preserving the existing `intake_output.json`, `contract_issues.json`, and all-profile `RuntimeError` behavior.

- `tests/test_a8_evidence_routing.py`
  - Updated `test_run_pipeline_fail_closed_for_kernel_pairing_gate_profiles` to expect the helper error prefix:
    `2_modelling self-check blocked under run_profile=<profile>`.
  - Added `assert "kernel.pairing_gate" in str(exc.value)` so the test still proves the pairing gate is the blocker.

- `tests/test_run_pipeline_self_checks.py`
  - Added `CheckLayer` / `CheckStatus` imports for synthetic `CheckReport` construction.
  - Added a helper that monkeypatches `src.validator.checks.kernel.check_kernel` to return a non-pairing invariant blocker without relying on `kernel_issues`.
  - Added a golden-profile test proving a non-pairing `kernel.coverage_completeness` blocker raises after S2 artifacts are written and before S3 starts.
  - Added an exploratory-profile test proving a non-pairing `kernel.normals` blocker writes `kernel_checks.json`, logs a warning, and continues through S5.
  - Extended the existing inline-vs-`validate_case` parity test to include `5_intakeoutput/assembly_checks.json` check IDs and statuses.

## Non-pairing kernel test construction

The test monkeypatch target is `src.validator.checks.kernel.check_kernel`, matching the lazy import in `run_pipeline`. The fake check:

- receives the same arguments as the real check, including `run_profile`;
- asserts `interzone_issues` is empty, so the blocker is not caused by the InterZone pairing path;
- returns a `CheckReport(stage="2_modelling", run_profile=run_profile)` with:
  - `kernel.pairing_gate` passing;
  - one injected invariant failure such as `kernel.coverage_completeness` or `kernel.normals`.

Golden assertion boundary:

- exists: `2_modelling/building_geometry.json`;
- exists: `2_modelling/kernel_gate_report.json`;
- exists: `2_modelling/kernel_checks.json`;
- absent: `3_split_pairing/geometry_specs.md`.

Exploratory assertion boundary:

- `2_modelling/kernel_checks.json` contains the non-pairing blocker;
- warning log contains `2_modelling self-check` and the injected check ID;
- `3_split_pairing/geometry_specs.md` and `5_intakeoutput/intake_output.json` are produced.

## Pytest

Command:

```bash
python -m pytest -q
```

Result:

```text
395 passed, 9 xfailed, 36 warnings in 72.85s (0:01:12)
```

The warning set was from existing baseline/report-assembly tests about missing AGENT regions.

## Review-asks / self-report

- No deviations from §7 定案.
- No changes to `check_assembly`, `check_kernel`, `validate_contract`, or `_gate_self_check_report` signatures or semantics.
- No `run_profile` was added to `check_assembly`.
- No changes to stepwise execution or `validate_case`.
- No duplicate S2 `kernel_checks.json` writer remains in `run_pipeline`.
- S5 still uses the existing all-profile `validate_contract` hard stop; `assembly_checks.json` is diagnostic-only in `run_pipeline`.
