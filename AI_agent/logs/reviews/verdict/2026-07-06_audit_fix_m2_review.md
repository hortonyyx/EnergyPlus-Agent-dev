# Review: M2 audit-fix gates proposal

Verdict: **APPROVE-WITH-CHANGES**.

I verified against the local working tree only. The brief's paths are shorthand in a few places: the actual files are `src/validator/checks/reading.py`, `src/validator/checks/mep.py`, and `skills/intake_pipeline/4_mep/authoring.md`.

## Findings

1. **MAJOR - HVAC schedule check scope can retro-fail anchors unless explicitly scoped or grandfathered.**  
   `src/validator/checks/mep.py:40` limits `_LOAD_TYPES` to `("PEOPLE", "LIGHTS", "ELECTRICEQUIPMENT")`, and `_load_refs` only scans those at `src/validator/checks/mep.py:404-441`, so the brief is right that thermostat/ideal-load schedules are currently missed. But the local IDD makes `ZoneControl:Thermostat` field A3 `Control Type Schedule Name` required (`data/dependencies/Energy+.idd:35193-35199`), and local anchors leave it blank, e.g. `case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r1/4_mep/mep_output.json:22` and `case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading/4_mep/mep_output.json:22`. If M2 enforces that required field as part of schedule checking, it is not golden-neutral. Concrete fix: either limit M2 to the three checklist schedules plus non-empty optional references, or add an explicit legacy/grandfather path and pre-scan output before making `ZoneControl:Thermostat` A3 blocking.

2. **MAJOR - Cover both `ZoneHVAC:IdealLoadsAirSystem` and `HVACTemplate:Zone:IdealLoadsAirSystem`, and use parsed raw field names, not guessed indexes.**  
   Current anchors often use `ZoneHVAC:IdealLoadsAirSystem` (`case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r1/4_mep/mep_output.json:22`), while repo schemas/tools still expose `HVACTemplate:Zone:IdealLoadsAirSystem` (`src/validator/data_model.py:1383-1397`, `src/agent/tools/hvac_tools.py:35-52`). `idf_fragments.py` keeps `fields` plus `raw` (`src/validator/idf_fragments.py:76-80`, `:100`), so use `raw.Availability_Schedule_Name`, `raw.Heating_Availability_Schedule_Name`, etc. Concrete fix: create a small schedule-ref table by object type and raw attribute. Also include `HVACTemplate:Thermostat` because its heating/cooling schedule fields are the template equivalent (`data/dependencies/Energy+.idd:27404-27428`).

3. **MAJOR - Existing malformed HVAC fragments will be newly exposed.**  
   A literal non-empty reference check finds anchor impacts: `sm21_anchor/run_2026-06-23_gpt54mini_reading` misorders `HVACTemplate:Zone:IdealLoadsAirSystem` so `Office_Thermostat` lands in `System Availability Schedule Name` (`.../mep_output.json:22`); `sm21_anchor/run_2026-07-01_sonnet_e2e_r1` and `run_2026-07-02_sonnet_flow_e2e` have malformed `ZoneHVAC:IdealLoadsAirSystem` layouts where `NoLimit`/`None` is parsed into heating availability schedule fields (`.../run_2026-07-02_sonnet_flow_e2e/4_mep/mep_output.json:22`). Concrete fix: before execution, define whether these are expected new invariant failures, or only validate the primary system availability field for M2 and defer heating/cooling availability fields.

4. **MINOR - Thermal-mass definition should explicitly skip only fenestration constructions and not `Construction:AirBoundary`.**  
   The brief's opaque definition is mostly right: iterate only `CONSTRUCTION`; skip if any layer resolves to a `WINDOWMATERIAL:*`; require at least one layer resolving to object type exactly `MATERIAL`. `Material:NoMass`, `Material:AirGap`, and `Material:InfraredTransparent` are not mass-bearing (`src/validator/checks/mep.py:34-39`). `Construction:AirBoundary` is a separate IDD object (`data/dependencies/Energy+.idd:9097-9124`), so it will not be reached by `idx.of_type("CONSTRUCTION")`. Concrete fix: name this in the helper/test to prevent future overreach.

5. **MINOR - Dependency brief is basically right, but `attrs` is imported as `attr`.**  
   Direct imports are local and real: `from dotenv import load_dotenv` at `src/agent/llm.py:5`, `from openai import OpenAI` at `src/agent/pipeline.py:41`, and `from attr import dataclass` at `src/rag/vector.py:5`. `pyproject.toml:7-31` currently lacks `ezdxf`, `python-dotenv`, `openai`, and `attrs`; `uv.lock` already contains `openai` (`uv.lock:1948-1964`), `python-dotenv` (`uv.lock:2554-2560`), and `attrs` (`uv.lock:195-201`), but not `ezdxf`.

## Review Questions

1. **Opaque construction edge cases:** use `CONSTRUCTION` only; skip constructions with any `WINDOWMATERIAL:*` layer; require at least one exact `MATERIAL` layer otherwise. This includes `Cons_InterFloor` and other interior opaque constructions. Pure window constructions and multi-layer glazing/gas fenestration constructions skip. `Construction:AirBoundary` needs a separate check if emitted.

2. **Exact schedule fields and optionality:**  
   `ZoneControl:Thermostat`: `Control_Type_Schedule_Name` / A3 / parsed `fields[2]`, IDD required.  
   `ThermostatSetpoint:DualSetpoint`: `Heating_Setpoint_Temperature_Schedule_Name` A2 and `Cooling_Setpoint_Temperature_Schedule_Name` A3, not marked required in IDD (`data/dependencies/Energy+.idd:35471-35483`). Non-empty refs must exist; blank is IDD-allowed but conflicts with the authoring checklist if you choose to enforce authoring policy.  
   `ZoneHVAC:IdealLoadsAirSystem`: `Availability_Schedule_Name` A2, `Heating_Availability_Schedule_Name` A8, `Cooling_Availability_Schedule_Name` A9; all blank-optional (`data/dependencies/Energy+.idd:35726-35730`, `:35805-35812`).  
   `HVACTemplate:Zone:IdealLoadsAirSystem`: `System_Availability_Schedule_Name` A3, `Heating_Availability_Schedule_Name` A6, `Cooling_Availability_Schedule_Name` A7; blank-optional (`data/dependencies/Energy+.idd:27446-27449`, `:27505-27512`).  
   Also cover `ThermostatSetpoint:SingleHeating`, `SingleCooling`, and `SingleHeatingOrCooling` if present (`data/dependencies/Energy+.idd:35438-35469`).

3. **Grandfathering path for closure tolerance:** `reading.dimension_chain_closure` is in `EVIDENCE_CHECK_IDS` (`src/validator/checks/schema.py:41-49`). Evidence failures block only under `golden`/`regression` unless `legacy_migrated` is true (`src/validator/checks/schema.py:137-142`). The legacy flag is propagated into evidence (`src/validator/checks/reading.py:171-177`; `src/agent/reading/legacy.py:118-123`). So legacy migrated goldens are shielded; non-legacy golden/regression runs can block.

4. **Minimal `uv.lock` route:** edit `pyproject.toml`, run plain `uv lock` without any upgrade flags, then inspect the diff. Expected minimal diff: root `energyplus-agent` dependency/metadata changes, one new `ezdxf` package block, direct refs for existing locked `openai`/`python-dotenv`/`attrs`, removal of root direct `click`/`aiohttp`. `click` should stay locked through `typer` and `uvicorn` (`uv.lock:3351-3357`, `:3427-3433`); `aiohttp` appears root-only in lock refs (`uv.lock:594`, `:628`) and should disappear with its unused aio dependencies if no other resolver edge remains.

5. **`click`/`aiohttp` removal safety:** focused import and entry-point scans found no `from/import click` or `from/import aiohttp` in `src`, `tests`, or non-vendor scripts. The only project script is `energyplus-mcp = "src.mcp.server:mcp.run"` (`pyproject.toml:33-34`). Removing direct deps is safe; `click` remains transitive via `typer`/`uvicorn`.

## Empirical Scans

Dimension-chain pre-scan over `case_tests/**/0_reading/*_view.json`: 97 files; 24 had chain tags; 73 had none. With the exact current validator grouping `(chain_id, axis)`, there were 10 complete comparable chains, 126 incomplete exact groups, 8 residuals `<=0.010`, **0 residuals in `(0.010, 0.05]`**, and 2 residuals `>0.05` already failing the old 50 mm rule (`sm21_anchor/run_2026-07-02_sonnet_flow_e2e/0_reading/1f_view.json` residual 0.24 m; `2f_view.json` residual 0.12 m). A heuristic normalization of `_overall/_detail/_seg` chain names still found 0 in `(0.010, 0.05]`. Tightening is free for the newly affected band.

Thermal-mass pre-scan over 13 `4_mep/mep_output.json` files: all 8 anchor MEP outputs parsed for this check and passed the proposed opaque thermal-mass rule. `case_tests/e2e_tests/smalloffice_23/4_mep/mep_output.json` would newly fail because all opaque layers are `Material:NoMass` (`:19-20`). One non-anchor audit output has an existing parse error.

The A0 tolerance claim is local and valid: `DIMCHAIN_CLOSE_TOL` is 10 mm at `skills/intake_pipeline/1_correction/A0_contract.md:176-179`; `reading.py` currently has `_OUTPUT_PRECISION_M = 0.01` with a misleading DIMCHAIN comment at `src/validator/checks/reading.py:45` and the closure check literal `> 0.05` at `src/validator/checks/reading.py:669`.
