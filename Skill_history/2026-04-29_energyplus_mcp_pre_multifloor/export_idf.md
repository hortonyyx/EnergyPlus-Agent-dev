# Export IDF File Skill

## Overview

This skill describes the YAML → IDF export step. The actual conversion is performed by an external script — **do not write inline Python in chat**.

## Usage

After `validate_config()` and `export_yaml(...)` have written `<case_dir>/output/<case_name>.yaml`, run:

```bash
python Tool_scripts/export_idf.py <case_dir>
```

The script writes `<case_dir>/output/<case_name>.idf` and prints the path. Run from the repository root so the IDD relative path resolves.

## What the script does

The script applies five idempotent patches around `ConverterManager.convert_all()`:

| # | Patch | Why |
|---|---|---|
| 0 | Pre-inject placeholder `Material:NoMass` + 3 stub `Construction` (`Default_Ext_Wall`, `Default_Int_Wall`, `Default_Window`) **before** `convert_all`. | `FenestrationConverter` strictly requires the referenced `Construction` to exist; without this, every window in geometry-phase YAML is silently dropped. The MEP phase overwrites these stubs with real layered constructions. |
| 1 | Set `RunPeriod` defaults (Day_of_Week_for_Start_Day, weather-file flags, Begin/End_Year). | YAML schema emits a default `RunPeriod` with `None` fields that break `save_idf`. **Required even in geometry phase.** |
| 2 | `Building.Minimum_Number_of_Warmup_Days = 1`. | Default 0 makes EnergyPlus refuse to run. **Required even in geometry phase.** |
| 3 | Rewrite any `BuildingSurface:Detailed` with `Outside_Boundary_Condition == 'Surface'` to `Adiabatic + Default_Int_Wall`. | Geometry phase already writes `Adiabatic` directly on shared walls (per `energyplus_mcp_prompt.md` IDF Step 3 table); this is a no-op safety net for any leftover surface-matched walls. Idempotent. |
| 4 | Drop trailing `None` fields from `Schedule:Compact` objects. | No-op in geometry phase (no `Schedule:Compact` exists). Required once MEP phase introduces them. |

## When you (the LLM) should NOT touch this

- Do **not** open `Tool_scripts/export_idf.py` to inline its body into the chat.
- Do **not** ask `Bash` to `cat` the script and then re-execute its contents.
- Do **not** rewrite the patches inside chat — call the script.

If the script fails, report the failure verbatim and stop. The script is the single source of truth for the patch set; modifying behaviour means editing the script in a separate change.

## Running the simulation

After exporting:

```bash
energyplus -w data/weather/Shenzhen.epw -d <case_dir>/output -r <case_dir>/output/<case_name>.idf
```

Note: full simulation requires the MEP phase to have authored Materials / Constructions / Schedules / People / Lights / HVAC. The geometry-phase IDF passes IDF parse + OpenStudio 3D-viewer geometry checks but is **not** simulation-ready.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `YAML not found` | Script run before `export_yaml` produced the YAML, or wrong `<case_dir>` | Run `export_yaml(...)` first; pass the case directory (parent of `output/`) |
| `IDD not found` | Script run from a directory that is not the repo root | `cd` to repo root before running |
| `Construction X does not exist in IDF` | Patch 0 was disabled or YAML references a non-default Construction not pre-injected | Either add the Construction in MEP phase, or extend `PLACEHOLDER_CONSTRUCTIONS` in the script |
