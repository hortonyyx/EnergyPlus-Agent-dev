# Report Organization Execution Log

Date: 2026-06-23
Executor: Codex

## Summary

Implemented the approved run-report organization design:

- `record_baseline.py` now writes `baseline.json` plus `report/FACTS.md`, protected `report/REPORT.md`, `report/REPORT.template.md`, and `report/eyeball/`.
- `baseline.json` gets an additive `evidence_index` field.
- `report/REPORT.md` is create-if-absent and is linted for structured evidence citations.
- `report/FACTS.md` is deterministic and includes raw facts, correction audit, run state, report assets, viewer availability, and evidence ids.
- `record_baseline.py` no longer writes top-level `RUN_REPORT.md`.
- `record_baseline.py` calls `validate_case(..., write_reports=False)` so it does not rewrite load-bearing `*_checks.json` artifacts.

## Backup

Before editing `scripts/tool_scripts/record_baseline.py`, copied it to:

- `backup/scripts_history/2026-06-23_report_org/record_baseline.py`

That backup path is gitignored by the repository's broad backup ignore rule.

## Files Changed

- `scripts/tool_scripts/report_assembly.py`
  - New deterministic report assembly support.
  - Explicit 2D eyeball collector from real producers:
    `1_correction/zones.png`, `1_correction/elev.png`, `0_reading/*_render.png`, and parent `case_data/*_view.png`.
  - Collision-safe report filenames.
  - Missing producer reporting.
  - `manual_review/geometry_viewer.html` verification/regeneration from `2_modelling/building_geometry.json`.
  - `run_state` derivation from `STAGE_ORDER`, `TERMINAL_STOP`, `ADVANCE_OK`, and explicit pending set.
  - Geometry approval supersedes only `3_split_pairing:awaiting_geometry_approval`.
  - Raw-artifact `evidence_index` construction for gate, judge, correction, stop, EP, geometry, and eyeball evidence.
  - Duplicate evidence id assertion.
  - Lexical citation linter for the four recommendation buckets.
  - REPORT skeleton rendering and protected write behavior.

- `scripts/tool_scripts/record_baseline.py`
  - Migrated output from top-level `RUN_REPORT.md` to `report/`.
  - Adds `evidence_index` to `baseline.json`.
  - Stops rewriting stage check artifacts by using `write_reports=False`.
  - Writes deterministic `FACTS.md`.
  - Creates/preserves authored `REPORT.md`; writes `REPORT.template.md`; supports `--force-template`.
  - Runs citation lint after REPORT creation/preservation.

- `tests/test_orchestrate_baseline.py`
  - Migrated assertions to `report/FACTS.md` / `report/REPORT.md`.
  - Added report preservation and `--force-template` regression.
  - Added 6+ `run_state` cases including real geometry-gated clean shape, all 4 pending states, and non-human terminal precedence.
  - Added evidence duplicate id test.
  - Added citation linter pass/fail tests.
  - Added full correction evidence indexing check beyond FACTS display cap.
  - Added state-aware stopped-run report test with no dead viewer link.

- `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/baseline.json`
  - Preserved existing score-card values.
  - Added only `evidence_index`.

- `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/baseline.json`
  - Preserved existing score-card values.
  - Added only `evidence_index`.

- `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/report/`
  - Added `FACTS.md`, `REPORT.md`, `REPORT.template.md`, and `eyeball/` assets.

- `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/report/`
  - Added `FACTS.md`, `REPORT.md`, `REPORT.template.md`, and `eyeball/` assets.

- `AI_agent/guides/new_case_guide.md`
  - Migrated to `report/`.
  - Fixed `record_baseline.py <case> <run>` command.
  - Fixed viewer path to `manual_review/geometry_viewer.html`.
  - Added final REPORT authoring and citation discipline step.

- `case_tests/test_baseline/README.md`
  - Migrated baseline layout and command to `report/`.

- `case_tests/test_baseline/index.md`
  - Migrated registry wording to `report/`.

- `AI_agent/architecture/pipeline_stage_contracts.md`
  - Migrated run layout and correction audit report path to `report/FACTS.md`.

- `AI_agent/CLAUDE.md`
  - Migrated the active audit report path mention to `report/FACTS.md`.

- `scripts/tool_scripts/run_stage.py`
  - Updated aggregate report comment.

- `src/agent/execution/orchestrate.py`
  - Updated comments from `RUN_REPORT` to `report/FACTS.md`.

## Real Run Validation

Regenerated report assembly for:

- `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/`
  - `run_state`: `completed_clean`.
  - Real geometry-gated stale `3_split_pairing:awaiting_geometry_approval` was correctly superseded by `geometry_approved=true`.
  - `manual_review/geometry_viewer.html` was regenerated from `2_modelling/building_geometry.json` and linked from REPORT.
  - `report/eyeball/` contains 14 copied 2D assets.

- `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/`
  - `run_state`: `root_stopped`.
  - Root stop is separated from consequential missing downstream artifacts.
  - No dead 3D viewer link is emitted because geometry is unavailable.
  - `report/eyeball/` contains 14 copied 2D assets.

## Validation Commands

- `python -m py_compile scripts/tool_scripts/report_assembly.py scripts/tool_scripts/record_baseline.py`
  - passed
- `python -m pytest tests/test_orchestrate_baseline.py -q`
  - `22 passed`
- `python -m pytest tests/test_validation_run_baseline.py tests/test_step_orchestrator.py -q`
  - `50 passed`
- `git diff --check`
  - passed
- `python -m pytest -q`
  - `320 passed in 63.02s`

## Invariants Checked

- No new code imports or reads `case_tests/test_baseline/gt/`.
- `record_baseline.py` no longer writes top-level `RUN_REPORT.md`.
- `record_baseline.py` does not call `validate_case(write_reports=True)`.
- The two real run baselines keep existing score-card values and only add `evidence_index`.
- Existing top-level historical `RUN_REPORT.md` files were not deleted or edited.
- `manual_review/geometry_viewer.html` remains outside `report/`; generated viewer HTML is gitignored.

## Judgment Calls / Deviations / Risk Points

- `baseline.json` persists only the approved additive enforcement field `evidence_index`. `run_state`, viewer status, and report asset metadata are used in `FACTS.md` / `REPORT.md` but not persisted to baseline. This keeps the real baselines aligned with the hard instruction to keep baseline values stable and add evidence indexing only.
- When regenerating the two real runs, current validation recomputed stale 0_reading pass/NA counts as `58/14` instead of the checked-in `52/8`. I restored the checked-in score-card values and kept only the new `evidence_index` in committed `baseline.json` files. `FACTS.md` was regenerated from the restored score-card plus fresh report context.
- Gate duplicate ids use the first occurrence unsuffixed and subsequent within-report duplicates as `#2`, `#3`, etc.
- REPORT preservation is implemented as create-if-absent plus explicit `--force-template`; it does not attempt marker-region merging inside an already authored file.
- Citation enforcement is called by `record_baseline.py` after REPORT creation/preservation. I did not add a separate standalone linter CLI.
- Existing top-level `RUN_REPORT.md` artifacts in older checked-in runs remain untouched as historical generated files; the generator and active docs no longer produce or point to them.
- The user-provided spec/review files under `AI_agent/logs/review/{request,review}/` were untracked at start and were left untouched.
