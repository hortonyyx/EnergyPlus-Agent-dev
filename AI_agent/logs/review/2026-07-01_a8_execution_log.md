# 2026-07-01 A8 Correction Evidence Routing Execution Log

## Scope Implemented

- Added deterministic A8 preflight in `src/agent/execution/evidence_preflight.py`.
  - Projects only the 0_reading evidence-check subset from `CheckReport`.
  - Recomputes disposition with the current `run_profile`; it does not trust the report's stored profile.
  - Writes lightweight `EvidenceDebt` with `schema_version` and `producer` extension slots.
- Wired `run_correction()` as the correction prompt injection point.
  - `evidence_debt=None` remains backward-compatible: it computes preflight from reading vectors.
  - Empty debt does not inject a prompt block.
  - Non-empty debt is injected as a structured JSON block with conflict/unsupported discipline.
- Wired `run_pipeline(..., run_profile="exploratory")`.
  - Always computes and writes `1_correction/evidence_debt.json` before correction.
  - Fails closed only when the current profile makes evidence debt blocking (`golden`/`regression`).
- Added A8.3b post-correction deterministic coverage check.
  - `correction.evidence_debt_coverage` is profile-sensitive in `disposition()`.
  - Element-local missing coverage blocks in `golden`/`regression`.
  - View/global missing coverage remains advisory/flag in all profiles.
  - Coverage checks `conflicts`/`corrections` only; `unsupported` is not counted as LLM coverage.
- Added report/evidence-index trace for `1_correction/evidence_debt.json`.
- Did not add `needs_reread`.
  - Stepwise strict-profile reread still depends on the existing 0_reading gate routing to `AWAITING_REREAD` when `reading_runner_available=True`.
  - If the runner is unavailable, existing stepwise behavior remains human/hard-stop.

## Files Changed

- `src/agent/execution/evidence_preflight.py` (new)
- `src/agent/pipeline.py`
- `src/validator/checks/schema.py`
- `src/validator/checks/correction.py`
- `src/agent/execution/validation_run.py`
- `scripts/tool_scripts/run_stage.py`
- `scripts/tool_scripts/report_assembly.py`
- `scripts/tool_scripts/record_baseline.py`
- `tests/test_a8_evidence_routing.py` (new)

## Backup

Backed up existing modified `src` files before editing:

- `backup/src_history/2026-07-01_a8_evidence_routing/pipeline.py`
- `backup/src_history/2026-07-01_a8_evidence_routing/schema.py`
- `backup/src_history/2026-07-01_a8_evidence_routing/correction.py`
- `backup/src_history/2026-07-01_a8_evidence_routing/validation_run.py`

## Tests

- `pytest tests/test_a8_evidence_routing.py -q`
  - `9 passed`
- `pytest tests/test_checks_reading_correction.py tests/test_orchestrate_baseline.py tests/test_intake_pipeline.py -q`
  - `79 passed, 1 xfailed`
- `pytest -q`
  - `374 passed, 9 xfailed`
  - Existing golden xfail count stayed at 9; total passed increased from the stated 365 baseline by the 9 new A8 tests.
- `python -m compileall -q src/agent/execution/evidence_preflight.py src/agent/pipeline.py src/validator/checks/correction.py src/validator/checks/schema.py src/agent/execution/validation_run.py scripts/tool_scripts/run_stage.py scripts/tool_scripts/report_assembly.py scripts/tool_scripts/record_baseline.py`
  - passed
- `rg -n "needs_reread" ...`
  - no new `needs_reread` field found.

## NEEDS-REVIEW

1. A8.3b element-local coverage currently requires offender ids (for example `S1`) to be mentioned in `conflicts` or `corrections`. It does not prove a geometric cell/window mapping; this was chosen because §6 says coverage-only, not coordinate correctness, but the phrase "strong core to cell/window" may deserve a stricter future mapping once a deterministic stroke→cell/window bridge exists.
2. View/global debt coverage is accepted if `conflicts`/`corrections` mention the view or check id. This is intentionally advisory and lexical, not semantic.
3. `run_pipeline()` derives dimensioned-view metadata from `testdata_text`. `run_stage.py` passes case metadata explicitly. Standalone `run_correction()` callers with empty testdata text and no `dimensioned_views` argument will still compute evidence debt, but may miss dimensioned-view-only debt such as `dimensions_present`.
4. Strict stepwise preflight does not hard-raise inside `run_correction()`. It relies on the existing 0_reading gate to produce `AWAITING_REREAD` when `reading_runner_available=True`; direct manual invocation of `1_correction` can still proceed with debt injected unless the post-coverage gate blocks.
