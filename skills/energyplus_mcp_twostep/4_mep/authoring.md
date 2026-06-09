# 4_MEP — physical-information authoring (LLM)

Stage **物理信息挂载** of the pipeline. The geometry is already fully built and
serialized deterministically (zones / surfaces / windows) by the kernel; this stage
authors **only the non-geometry** specs and attaches them by name. You do **not** see
drawings and you do **not** author any geometry (no zones, no surfaces, no windows).

Use the default values in [`mep.md`](mep.md) (by building type) unless explicit input
data overrides them.

## What you output (8 of the 11 IntakeOutput fields)

`building`, `site_location`, `material_specs`, `construction_specs`, `schedule_specs`,
`hvac_specs`, `people_specs`, `lights_specs`. The three geometry fields
(`zone_specs` / `surface_specs` / `fenestration_specs`) are supplied by the kernel —
do not produce them.

## Inputs given to you at runtime

- `testdata_prompt.json` — building name / type / floors / area / location / facades.
- The serialized **zone list** (names + role per zone) — author per-zone `people_specs`
  / `lights_specs` / `hvac_specs` against these exact zone names, literally.
- The **required construction set** — the geometry references these construction names;
  you MUST define every one of them in `construction_specs` (with materials in
  `material_specs`). Defining a construction the geometry uses but you omit drops its
  surfaces at EnergyPlus.

## Rules

### building (from testdata)
name from `TestName` (no spaces), type from `Building type`, num_floors from `Number of
floors`, total_floor_area_m2 from `Floor area`. Office defaults only where genuinely
missing.

### site_location (from testdata `Building location`)
`city = "<Location>_CN"`, `weather_file = "<Location>.epw"` (must match an EPW under
`data/weather/`), climate_zone by geographic sense or blank; infer lat/long if absent.

### material_specs / construction_specs (the construction contract)
- Define **every** construction in the required construction set. Typical layer stacks:
  - `Default_Ext_Wall`: [Mat_Stucco, Mat_Insulation, Mat_Gypsum] (outside→inside)
  - `Default_Int_Wall`: [Mat_Gypsum, Mat_Insulation, Mat_Gypsum] (symmetric)
  - `Default_GroundFloor`: [Mat_Floor_Concrete, Mat_Insulation, Mat_Gypsum]
  - `Default_Roof`: [Mat_Roof_Membrane, Mat_Insulation, Mat_Gypsum]
  - `Cons_InterFloor`: **single** construction used by every interzone floor/ceiling
    pair (monolithic, e.g. [Mat_Floor_Concrete]) — both paired faces share it, so the
    EnergyPlus reverse-layer symmetry holds trivially. Do **not** define separate
    `Default_Floor` / `Default_Ceiling`.
  - `Default_ExtFloor` (only if in the required set): exposed floor underside.
  - `Default_Window`: a single layer referencing a named
    `WindowMaterial:SimpleGlazingSystem` (do NOT stack two panes / an air gap → EP NaN).
- **material ↔ construction split (hard).** The material agent creates every material;
  the construction agent references materials by name only. So **every** Construction
  layer (opaque and glazing) must name a material explicitly declared in `material_specs`.
  The glazing material must be a named `WindowMaterial:SimpleGlazingSystem` in
  `material_specs` (Name + U-Factor + SHGC); `Default_Window` references it by name. Never
  inline glazing properties only under `construction_specs`.

### schedule_specs (must be complete)
The schedule subagent runs first and is not re-invoked, so every schedule any field
references must be defined here with an exact name, type limits, and value profile.
Required checklist:
- thermostat heating setpoint schedule
- thermostat cooling setpoint schedule
- ideal loads availability schedule
- people number-of-people schedule
- **people activity-level schedule** (easy to forget — do not omit)
- lights schedule

### people_specs / lights_specs / hvac_specs (per zone)
Assign from `mep.md` defaults, per zone, by the zone's role. Reference each zone by its
exact name from the zone list. HVAC = `IdealLoadsAirSystem` with the setpoints from
`mep.md`.

## Naming (mandatory)
Letters / digits / `_` only — no spaces, commas, hyphens, slashes, parentheses.
Cross-field references literally identical: a construction in the geometry specs must
appear verbatim in `construction_specs`; a schedule in `hvac/people/lights_specs` must
appear in `schedule_specs`.
