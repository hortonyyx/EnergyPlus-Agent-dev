# Run Dir Tidy + Single REPORT.md Execution Log

Date: 2026-06-23
Branch: `6.15_ValidationArchM0toM4`
Executor: Codex
Spec: `AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md`
Review context: `AI_agent/logs/review/review/2026-06-23_rundir_tidy_single_report_review.md`

## Scope

Implemented the approved-with-changes v2 design:

- Moved generated run metadata to `<run>/_run/`.
- Kept `<run>/llm.yaml` at the run root.
- Replaced separate `report/FACTS.md` + protected `report/REPORT.md` with one marker-delimited `report/REPORT.md`.
- Preserved stage artifacts in place, including `2_modelling/building_geometry.json`, `3_split_pairing/geometry_specs.md`, `*_checks.json`, `intake_output.json`, `correction_geometry*.json`, and `verdicts/`.
- Did not read or import `case_tests/test_baseline/gt/`.

## Backups

Before editing `src/` or `scripts/`, copied originals to:

- `backup/src_history/2026-06-23_rundir_tidy/agent_execution/manifest.py`
- `backup/src_history/2026-06-23_rundir_tidy/agent_execution/approval.py`
- `backup/src_history/2026-06-23_rundir_tidy/agent_execution/step_orchestrator.py`
- `backup/src_history/2026-06-23_rundir_tidy/agent_execution/__init__.py`
- `backup/src_history/2026-06-23_rundir_tidy/agent_execution/orchestrate.py`
- `backup/scripts_history/2026-06-23_rundir_tidy/tool_scripts/record_baseline.py`
- `backup/scripts_history/2026-06-23_rundir_tidy/tool_scripts/report_assembly.py`
- `backup/scripts_history/2026-06-23_rundir_tidy/tool_scripts/run_stage.py`

## Implementation

### F1 `_run` metadata helper

- Added `src/agent/execution/run_meta.py` with `RUN_META_DIR = "_run"` and `run_meta_path(run_dir, name, for_write=False)`.
- Routed these through `run_meta_path`:
  - `RunManifest.load/save`, including `filename="validation_manifest.json"`.
  - `GeometryApproval.load/save`.
  - `load_state`, `update_state`, `mark_geometry_approved`.
  - `record_baseline` write of `baseline.json`.
  - report appendix links and evidence sources for moved metadata.
- No root fallback was implemented. Root stale files are ignored when `_run/` exists.

### F2/F4 single marker-delimited REPORT

- `record_baseline.py` now writes `_run/baseline.json` and one `report/REPORT.md`.
- `report_assembly.py` no longer writes `FACTS.md` or `REPORT.template.md`; stale copies are removed after a successful merge/lint.
- `REPORT.md` is composed from:
  - `GEN:model_config` at top with `llm.yaml`, recorded date, orchestrator, run state, and models.
  - `GEN:facts_card` with verdict, gate table, run_state, blocking/flags, correction audit summary, and numeric-authority note.
  - `AGENT:conclusion`, `AGENT:focus`, `AGENT:diagnosis`, `AGENT:recommendations`.
  - `GEN:eyeball_index`.
  - `GEN:appendix` with `_run/` links and evidence index summary.
- GEN blocks are refreshed on every run; AGENT blocks are preserved.
- Missing AGENT regions get placeholders and a `RuntimeWarning`.
- Duplicate, nested, reversed, unknown-key, or unclosed AGENT markers raise `ReportMarkerError` before writing `REPORT.md`.
- Exact full-line marker parsing is used; AGENT-looking marker text inside GEN regions is ignored.

### F3 citation lint scope

- `lint_report_citations` now validates the already-extracted `AGENT:recommendations` block.
- Unknown/stale evidence ids fail with errors prefixed by `AGENT:recommendations`.
- The merged report is linted before write.

### F5 committed run migration

Moved the five generated metadata filenames, where present, into `_run/` using `git mv` for:

- `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline`
- `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e`
- `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading`
- `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading`
- `case_tests/e2e_tests/sm21_anchor/run_2026-06-21_sonnet_reading_retry`

Removed obsolete tracked human/generated report files:

- root `RUN_REPORT.md` from sm20 baseline, sm21 opus, and sm21 sonnet retry.
- `report/FACTS.md` and `report/REPORT.template.md` from gpt54 and sonnet reading runs.

Generated single `report/REPORT.md` for all five active runs. The gpt54 and sonnet reading run roots now have only `llm.yaml` as a root file, with metadata under `_run/`.

### F6 docs

Updated:

- `AI_agent/guides/new_case_guide.md`
- `AI_agent/architecture/pipeline_stage_contracts.md`
- `case_tests/test_baseline/README.md`
- `case_tests/test_baseline/index.md`
- runtime comments in `src/agent/execution/orchestrate.py`
- `scripts/tool_scripts/run_stage.py`

The docs now describe `<run>/llm.yaml`, `<run>/_run/`, and one `report/REPORT.md`. `scripts/run_full_pipeline.py` legacy per-case config behavior was not changed.

## Validation

Commands run:

- `python -m py_compile src/agent/execution/run_meta.py src/agent/execution/manifest.py src/agent/execution/approval.py src/agent/execution/step_orchestrator.py src/agent/execution/orchestrate.py src/agent/execution/__init__.py scripts/tool_scripts/report_assembly.py scripts/tool_scripts/record_baseline.py scripts/tool_scripts/run_stage.py`
- `python -m pytest tests/test_execution_foundation.py tests/test_validation_run_baseline.py tests/test_orchestrate_baseline.py -q`
  - Result: `65 passed, 52 warnings`
- Regenerated reports/baselines:
  - `python scripts/tool_scripts/record_baseline.py sm20_anchor run_2026-06-15_baseline --base-dir case_tests/e2e_tests --date 2026-06-16 --orchestrator opus-4.8`
  - `python scripts/tool_scripts/record_baseline.py sm21_anchor run_2026-06-16_opus_e2e --base-dir case_tests/e2e_tests --date 2026-06-16 --orchestrator opus-4.8`
  - `python scripts/tool_scripts/record_baseline.py sm21_anchor run_2026-06-20_gpt54_reading --base-dir case_tests/e2e_tests --date 2026-06-21 --orchestrator opus-4.8`
  - `python scripts/tool_scripts/record_baseline.py sm21_anchor run_2026-06-20_sonnet_reading --base-dir case_tests/e2e_tests --date 2026-06-21 --orchestrator opus-4.8`
  - `python scripts/tool_scripts/record_baseline.py sm21_anchor run_2026-06-21_sonnet_reading_retry --base-dir case_tests/e2e_tests --date 2026-06-21 --orchestrator opus-4.8`
- Checked gpt54/sonnet roots:
  - `find ... -maxdepth 1 -type f` shows only `llm.yaml`.
  - `find .../report -maxdepth 1 -type f` shows only `REPORT.md`.
- Marker merge smoke test on a temporary sm21 copy:
  - edited `AGENT:focus` to `HAND_EDITED_FOCUS_SMOKE`
  - reran `record_baseline` twice
  - edit survived and second rerun was byte-idempotent (`cmp` exit `0`)
- Full suite:
  - `python -m pytest -q`
  - Result: `328 passed, 36 warnings in 64.86s`

Warnings are expected `RuntimeWarning`s for missing AGENT regions in synthetic/first-run reports; this is the specified missing-key placeholder behavior.

## Review Ask

- I removed root `RUN_REPORT.md` and generated new single `report/REPORT.md` for sm20 baseline, sm21 opus, and sm21 sonnet retry to keep the active run contract consistent, although the explicit end-to-end regeneration callout named only gpt54 and sonnet reading.
- sm20 baseline and sm21 opus do not have historical `_run/orchestration_state.json`, so their generated REPORT run_state is `incomplete` even though gate/EP facts remain clean. I did not fabricate orchestration state.
- Regenerated sm20 and sm21 opus `_run/baseline.json` gained additive `evidence_index` data while preserving their geometry counts.
- `force_template=True` still resets AGENT content after validating any existing marker structure; malformed markers fail before any write.
