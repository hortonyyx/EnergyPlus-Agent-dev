# Vacuum Fixes Execution Log — 2026-07-01

## Scope

Implemented the §3 vacuum fixes from
`AI_agent/logs/review/2026-07-01_stage1to5_second_route_audit/RECONCILED_and_vacuum_fixes.md`
in the `validate_case` MEP check path. No GitHub reads. No commit.

## Per-file Changes

- `src/validator/checks/mep.py`
  - Added `mep.placeholder_ban` as an `INVARIANT` fail gate.
  - Added `mep.name_charset` as a `CROSS_CHECK` flag gate.
  - Added `mep.site_matches_testdata` as a `CROSS_CHECK` flag/NA gate.
  - Added optional `testdata: dict | None = None` keyword to `check_mep` for backward-compatible callers.
- `src/agent/execution/validation_run.py`
  - Added `_load_testdata(case_dir)` for `case_data/testdata_prompt.json`.
  - Passed parsed testdata into `check_mep` from `validate_case`.
- `tests/test_checks_mep_assembly.py`
  - Added fixtures for placeholder fail/pass.
  - Added fixtures for name charset flag/pass.
  - Added fixtures for structured site mismatch flag, structured site match pass, and no-structured-site NA.

## SELF-REPORTS

### S4-12 — `mep.placeholder_ban`

- Scan surface: parsed IDF fragment field values from the unified MEP parse, plus structured `building.name` and `site_location.name`.
- Rationale: parsed IDF field values cover object names and authored IDF fields while avoiding raw-format/comment noise; building/site names are LLM-authored MEP strings outside the IDF fragments.
- Banned patterns: `TBD`, `same as above`, `see above`, `etc.`, literal `...`, Unicode `…`, and angle placeholders containing `placeholder`, `tbd`, `todo`, `insert`, or `replace`.
- False-positive guards: case-insensitive token/phrase regexes use non-word boundaries; `etc.` requires the dot and is not matched inside larger tokens/domains; dot-containing names are not flagged unless they contain literal `...`.
- Legacy-golden interaction: explicit sm20/sm21 MEP scan/check showed `mep.placeholder_ban` passes for all checked sm20/sm21 anchor MEP outputs, so no grandfather stop was needed.

### #9 — `mep.name_charset`

- Layer/disposition: `CROSS_CHECK`; offenders are flags, not blockers.
- Allowed charset: ASCII letters, digits, underscore, hyphen, and space; regex `^[A-Za-z0-9_ -]+$`.
- Scanned parsed object types: `CONSTRUCTION`, `SCHEDULE:COMPACT`, `SCHEDULETYPELIMITS`, and material-like objects in `_MATERIAL_TYPES` (`MATERIAL`, `MATERIAL:NOMASS`, `MATERIAL:AIRGAP`, `WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM`, `WINDOWMATERIAL:GLAZING`, `WINDOWMATERIAL:GAS`, `WINDOWMATERIAL:BLIND`, `MATERIAL:INFRAREDTRANSPARENT`).
- Legacy-golden interaction: explicit sm20/sm21 MEP check showed `mep.name_charset` passes for all checked sm20/sm21 anchor MEP outputs.

### #5 — `mep.site_matches_testdata`

- Inspected testdata schema:
  - `case_tests/e2e_tests/sm20_anchor/case_data/testdata_prompt.json`: has `Building location: "Shenzhen"` only; no structured latitude/longitude/time_zone/elevation.
  - `case_tests/e2e_tests/sm21_anchor/case_data/testdata_prompt.json`: has `Building location: "Shenzhen"` only; no structured latitude/longitude/time_zone/elevation.
  - `case_tests/e2e_tests/sm24_anchor/case_data/testdata_prompt.json`: has `Building location: "Shenzhen"` only; no structured latitude/longitude/time_zone/elevation.
- Implemented comparable schema support: numeric fields found either at top level or under nested `site_location`/`Site Location`/`site`/`Site`.
- Compared fields: any structured subset of `latitude`, `longitude`, `time_zone`, `elevation`.
- Tolerances: latitude/longitude `0.01`, time_zone `0.1`, elevation `1.0`.
- Real-vs-NA behavior: current sm20/sm21/sm24 anchor testdata lacks comparable structured fields, so `mep.site_matches_testdata` records `NOT_APPLICABLE` with a clear message. New structured fixtures exercise real comparison pass and mismatch flag.
- Explicit sm20/sm21 anchor check: site gate is `NOT_APPLICABLE` for checked sm20/sm21 anchors; no new blocker. Some sm21 runs still show pre-existing `mep.load_to_schedule` blockers, unrelated to these new gates.

## Test Results

- After S4-12 implementation: `pytest tests/test_checks_mep_assembly.py -q`
  - Result: `17 passed in 3.32s`
- After #9 implementation: `pytest tests/test_checks_mep_assembly.py -q`
  - Result: `19 passed in 2.96s`
- After #5 implementation: `pytest tests/test_checks_mep_assembly.py -q`
  - Result: `22 passed in 3.01s`
- Requested focused selection: `pytest tests/ -k "mep or checks_mep or validation" -q`
  - Result: `42 passed, 347 deselected, 8 xfailed in 19.74s`
- Full suite: `pytest -q`
  - Result: `388 passed, 9 xfailed, 36 warnings in 76.34s`

## Working Tree Note

Pre-existing untracked directories were present and left untouched:

- `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading/EP/`
- `case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading/EP/`
