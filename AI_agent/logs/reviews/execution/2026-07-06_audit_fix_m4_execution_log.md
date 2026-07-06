# 2026-07-06 Audit Fix M4 Execution Log

Scope: additive tests only for Fable5 audit report C4 items 1, 3, and 4.

## Files touched

- `tests/test_run_pipeline_self_checks.py`
- `tests/test_checks_kernel.py`
- `tests/test_report_assembly.py`

Required backups were written before edits:

- `backup/src_history/2026-07-06_m4_testpatch/test_run_pipeline_self_checks.py`
- `backup/src_history/2026-07-06_m4_testpatch/test_checks_kernel.py`
- `backup/src_history/2026-07-06_m4_testpatch/test_report_assembly.py`

## Tests added

1. `test_run_pipeline_golden_blocks_on_mep_invariant_after_clean_correction`
   - Uses the existing stub MEP path with an incomplete `Schedule:Compact`.
   - Verifies exploratory logs a 4_mep self-check warning and continues.
   - Verifies golden raises `RuntimeError` matching `4_mep self-check blocked under run_profile=golden`.

2. `test_zone_closure_blocks_on_numeric_floor_area_mismatch`
   - Builds a synthetic `BuildingGeometry` where required surface types exist.
   - Deliberately mismatches floor area against the authoritative zone polygon.
   - Verifies `kernel.zone_closure` blocks with numeric offender evidence.

3. Report assembly evidence extractor tests:
   - `test_gate_entries_indexes_blocking_and_flagged_results`
   - `test_judge_entries_indexes_attempt_criteria`
   - `test_correction_entries_indexes_audit_sidecar_rows`
   - `test_ensure_geometry_viewer_smoke_existing`

## Verification

Command:

```bash
/opt/venv/bin/python -m pytest tests/test_run_pipeline_self_checks.py tests/test_checks_kernel.py tests/test_report_assembly.py
```

Result:

```text
collected 26 items

tests/test_run_pipeline_self_checks.py ...........                       [ 42%]
tests/test_checks_kernel.py ..........                                   [ 80%]
tests/test_report_assembly.py .....                                      [100%]

26 passed in 4.46s
```

## Notes

- No production code was changed.
- Existing unrelated/concurrent working-tree changes were present outside this batch scope, including `scripts/tool_scripts/record_baseline.py`, `scripts/tool_scripts/report_assembly.py`, `src/agent/execution/policy.py`, M3 review logs, and `tests/test_provenance_baseline.py`; they were not modified for M4.
