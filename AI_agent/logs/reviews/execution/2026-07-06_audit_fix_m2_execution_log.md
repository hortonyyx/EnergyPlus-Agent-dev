# M2 audit-fix gates execution log

Date: 2026-07-06
Executor: Codex
Workspace: `/workspaces/EnergyPlus-Agent-dev`

## Scope executed

- Backed up all existing files edited in this batch under `backup/src_history/2026-07-06_m2_gates/` with relative paths preserved.
- Did not touch `src/agent/pipeline.py`, `src/agent/execution/`, or `src/validator/checks/assembly.py`.
- Did not modify any `case_tests/` anchor or case data.
- Did not run the pipeline or EnergyPlus.

## Changes

- `src/validator/checks/reading.py`
  - Line 45: fixed the misleading `_OUTPUT_PRECISION_M` comment so it only claims A0 output precision scale.
  - Line 46: added `DIMCHAIN_CLOSE_TOL_M = 0.010`.
  - Line 670: replaced the 0.05 m chain-closure literal with `DIMCHAIN_CLOSE_TOL_M`.

- `src/validator/checks/mep.py`
  - Lines 40-57: added `_WINDOW_MATERIAL_TYPES` and table-driven HVAC schedule-reference fields.
  - Lines 117 and 121: wired `mep.construction_thermal_mass` and `mep.hvac_schedule_refs` into `check_mep`.
  - Lines 133-145: added material-type and construction-layer helpers.
  - Lines 410-458: added `mep.construction_thermal_mass` as an INVARIANT check. It iterates only `CONSTRUCTION`, skips constructions with any resolved `WINDOWMATERIAL:*` layer, and requires at least one layer resolving exactly to `MATERIAL`. `Material:NoMass`, `Material:AirGap`, and `Material:InfraredTransparent` are reported as non-mass layer types. `CONSTRUCTION:AIRBOUNDARY` is named as out of scope.
  - Lines 526-574: added `mep.hvac_schedule_refs` as an INVARIANT check. It uses raw eppy field names, checks only non-empty references against `SCHEDULE:COMPACT`, and treats blank references as pass. Heating/cooling availability fields are explicitly deferred in evidence.

- `tests/test_checks_reading_correction.py`
  - Lines 383-387: added the 49 mm non-closing dimension-chain regression.

- `tests/test_checks_mep_assembly.py`
  - Lines 74-160: added positive/negative thermal-mass coverage, including fenestration skip and `Construction:AirBoundary` out-of-scope coverage.
  - Lines 347-479: added positive/negative HVAC schedule-reference coverage across the adjudicated object table, blank optional fields, and deferred heating/cooling availability fields.

- `pyproject.toml`
  - Lines 8, 10, 21, and 24: added direct dependencies `attrs`, `ezdxf`, `openai`, and `python-dotenv`.
  - Removed direct dependencies `aiohttp` and `click`.

- `uv.lock`
  - Regenerated with plain `UV_PROJECT_ENVIRONMENT=/opt/venv uv lock`.

## Informational pre-scan

MEP scan target: every `case_tests/**/4_mep/mep_output.json`.

New-check impacts:

- `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading`
  - Would fail `mep.hvac_schedule_refs`.
  - Cause: 14 `HVACTemplate:Zone:IdealLoadsAirSystem.System_Availability_Schedule_Name` values parse as `Office_Thermostat`, which is not a `Schedule:Compact`.

- `case_tests/e2e_tests/smalloffice_23`
  - Would fail `mep.construction_thermal_mass`.
  - Cause: four opaque constructions have only `Material:NoMass` layers and no layer resolving exactly to `MATERIAL`: `Default_Ext_Wall`, `Default_Int_Wall`, `Default_GroundFloor`, `Default_Roof`.

Parse-limited existing output:

- `case_tests/e2e_tests/smalloffice_21/output_fable_audit/pipeline_out`
  - Existing MEP parse failure prevents the new checks from running, so this was not counted as a new-check failure.

Reading scan target: every `case_tests/**/0_reading/*_view.json`.

- Files scanned: 97.
- Complete comparable chains: 10.
- Residuals in the newly affected `(0.010, 0.050]` m band: 0.
- Existing old-rule failures over 0.050 m: 2, both in `case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e`:
  - `0_reading/1f_view.json`, chain `C_top`, axis `x`, residual 0.24 m.
  - `0_reading/2f_view.json`, chain `C_top`, axis `x`, residual 0.12 m.

`smalloffice_23` test dependency check:

- `rg "smalloffice_23" tests -n` returned no hits.
- No test in `tests/` depends on `smalloffice_23` MEP passing.

Deferred scope recorded:

- Heating/cooling availability schedule fields remain deferred for both `ZoneHVAC:IdealLoadsAirSystem` and `HVACTemplate:Zone:IdealLoadsAirSystem`.

## uv.lock diff summary

Command run:

```bash
UV_PROJECT_ENVIRONMENT=/opt/venv uv lock
```

Package/version comparison against the backed-up lock:

- Added packages: `ezdxf`, `fonttools`.
- Removed packages: `aiohappyeyeballs`, `aiohttp`, `aiosignal`, `frozenlist`, `multidict`, `propcache`, `yarl`.
- Changed package versions: none.

This matches the requested direct dependency changes plus the expected `ezdxf` transitive dependency and removal of the unused `aiohttp` branch. No unrelated version bump appeared.

Import verification:

```bash
/opt/venv/bin/python -c "import ezdxf, dotenv, openai, attr"
```

Result: passed.

## Targeted tests

Command run:

```bash
/opt/venv/bin/python -m pytest tests/test_checks_mep_assembly.py tests/test_checks_reading_correction.py
```

Result: 77 passed.

Also run:

```bash
git diff --check -- src/validator/checks/reading.py src/validator/checks/mep.py tests/test_checks_reading_correction.py tests/test_checks_mep_assembly.py pyproject.toml uv.lock
```

Result: passed.

## Deviations and notes

- `tests/test_checks_mep.py` does not exist in this working tree, so the targeted MEP check file run was `tests/test_checks_mep_assembly.py`.
- Full suite was not run, per M2 instruction to run only targeted tests.
- No commit was made.
