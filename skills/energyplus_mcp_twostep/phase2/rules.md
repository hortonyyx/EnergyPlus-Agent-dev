> ⚠️ **SUPERSEDED (Step 5, 0–5 refactor).** The single phase2b LLM call this document
> drove is retired. Its content now lives in three homes:
> - **Geometry** (world coords, zone/surface/fenestration derivation, split-pairing,
>   vertex synthesis) → the deterministic kernel: [`../2_modelling/spec.md`](../2_modelling/spec.md)
>   + [`../3_split_pairing/spec.md`](../3_split_pairing/spec.md) (code in `src/agent/geometry/`).
> - **Physics / contract** (building, site, material↔construction, schedules, MEP, naming)
>   → [`../4_mep/authoring.md`](../4_mep/authoring.md).
> - Section→home map: [`AI_agent/architecture/rules_md_split_map.md`](../../../AI_agent/architecture/rules_md_split_map.md).
>
> This file is kept only as the prompt for the **legacy fallback** `run_phase2b`
> (used only on a hard kernel build error) and as history. Do not extend it; edit the
> homes above instead. Scheduled for removal after the Step-8 e2e validates the new flow.

# Phase 2 Rules — vector JSON → IntakeOutput

Phase 2 does not see the image. All visual information has already been vectorized into JSON by
phase 1. This document focuses on the reasoning + output contract for **"vector JSON → IntakeOutput
Pydantic"**. Do not read `skills/energyplus_mcp/*.md` (the old single-step skill) — the "how to read
the drawing" parts there are useless to phase 2, and the key output contract is reproduced here.

---

## 0. Input / Output

### 0.1 Input

Read **every** vector JSON in the directory (do not assume a fixed file set):
- **plan + elevation vector JSONs** (one per image), e.g. `phase1_vector/{1f_view, 2f_view, 3f_view,
  South_view, North_view, East_view, West_view}.json`; output format defined in
  [../phase1/guide.md](../phase1/guide.md) (container) + [../phase1/pen_library.md](../phase1/pen_library.md) (pen meanings)
- **supplementary / section vector JSONs** if present (e.g. `supp_plan`, a section) — consume them
  for stair indexing, local geometry clarification, or anything the main plans/elevations leave
  ambiguous; do not silently ignore a supplement the case provided
- **metadata**: `testdata_prompt.json` (number of floors, floor area, building use, city, facade
  paths — an empty/absent facade path means that facade is blank, i.e. zero windows)

### 0.2 Output

One `IntakeOutput` Pydantic JSON with 11 fields:
- `building`, `site_location`
- `zone_specs`, `material_specs`, `schedule_specs`, `construction_specs`, `surface_specs`,
  `fenestration_specs`, `hvac_specs`, `people_specs`, `lights_specs`

The 9 `*_specs` fields are all natural-language instructions (**not structured data**), read by the
9 downstream subagents; they must be mechanically executable and internally consistent.

### 0.3 Error budget

Phase 2 does not see the image → any "value in the image" error has already been locked by phase 1,
**you can only introduce pure reasoning errors**:
- topology errors: which zone is the corridor / which wall is exterior / which window belongs to which wall
- field-format errors: non-conforming naming / inconsistent cross-field references / template writing / missing enum
- coordinate-translation errors: elevation x_local ↔ world coordinates reversed

A `null` field in the phase 1 JSON means "phase 1 didn't see it", **do not treat null as 0**; if
missing, annotate it accordingly in your output or refuse to model it.

---

## 1. World coordinate system and elevation translation

### 1.1 Global coordinate system

- origin = SW inner corner of the whole-building footprint
- x east, y north, z up (ground z=0)
- units meters, two decimals

### 1.2 Elevation local → world translation formulas (fill per each JSON's `facade_axis_note`)

Phase 1 already gives the 4-facade formulas in `phase1_summary.md` §3 (apply directly, **do not
re-derive**). Example for a 15×8 footprint:

- South: `X_world = x_local`, `Y_world = 0`, `Z_world = y_local`
- North: `X_world = 15 - x_local`, `Y_world = 8`, `Z_world = y_local`
- East:  `X_world = 15`, `Y_world = x_local`, `Z_world = y_local`
- West:  `X_world = 0`, `Y_world = 8 - x_local`, `Z_world = y_local`

15 / 8 are that footprint's outer dimensions; for other cases read the corresponding elevation
JSON's `scale_origin`.

---

## 2. Extract key quantities from the vector JSON

### 2.1 Footprint dimensions

From any plan's `dimensions` take the total-length chains: `text="15.00", axis="x"` is W,
`text="8.00", axis="y"` is D.

**Shared-footprint invariant**: the current regime assumes every floor shares the same outer
rectangular footprint `W × D` (internal partitioning may differ floor by floor). Verify
`W_f == W_g` and `D_f == D_g` across all floors (tolerance ≤ 0.01 m). If the per-floor outer chains
disagree, **report the conflict — do not silently pick one floor's footprint** (see §2.6).

### 2.2 Floor heights and per-floor z ranges

Derive from any elevation's left/right total-height chain + segment chains (values are per case —
do not reuse another case's heights). Example only, not reusable:

- F1: z_floor = 0.00, ceiling_height = 3.60, z_top = 3.60
- F2: z_floor = 3.60, ceiling_height = 3.60, z_top = 7.20
- F3: z_floor = 7.20, ceiling_height = 4.80, z_top = 12.00

Or equivalently: read directly from some elevation's `strokes[pen=wall_fill]` `y_range_m` (already
split per floor). The two paths must agree; if they disagree, report the conflict, do not silently
split the difference.

### 2.3 Per-floor plan zone topology

Each plan JSON's `strokes[pen=wall]` gives all wall centerlines (2D segments). **A zone = the
smallest closed polygon enclosed by these segments.** Phase 2 must judge by geometric enclosure, not
by ID order.

Example: 10 wall strokes enclosing 6 rooms + 1 corridor = 7 zones (consistent with testdata
`thermal_zones=7`).

### 2.4 Window positions

Each elevation JSON's `strokes[pen=window]` gives this facade's window local rects. Translate back to
world coordinates via §1.2, then judge which exterior wall they belong to by `Y_world` (North/South:
Y=0 or Y=8; East/West: X=0 or X=15).

`y_local` directly = `z_world`, no translation needed.

### 2.5 Two-way use of dimensions

A dimension chain both gives coordinates and provides cross-checks:

- direct use: read the number as a distance
- check use: stroke endpoint coordinates should match the accumulated dim chain (e.g. South_view F1
  second window x_range=[6.30,8.70] should equal dim chain 1.40+2.40+2.50=6.30 start, width 2.40).
  If they disagree **trust the dim**; the stroke coordinate may be a phase 1 tracing offset

**Dimension-chain checksum**: per axis, the inner segment chain must sum to the outer total chain
(`sum(inner segments) == outer total`, tolerance ≤ 0.01 m). For an elevation, each floor's
right-side chain must sum to that floor's height. If a checksum fails, report it — do not continue
with guessed values (see §2.6).

### 2.6 Coverage and unsupported-geometry handling

**Coverage (per floor, independently)**: the union of all zone footprints must equal the full shared
footprint; zones must not overlap; there must be no unexplained voids inside the footprint. If a room
crosses a strip boundary, keep it as one room and adjust the neighboring partitions accordingly.

**Do not silently fabricate**: the current regime assumes a shared rectangular footprint across
floors. If the vector JSON / dimensions reveal a feature outside this regime — setback, cantilever,
multiple exterior footprints across floors, atrium / void that breaks the shared footprint — or a
global conflict (per-floor footprints disagree, conflicting facade orientation, facade height chains
that change the floor stacking) — **do not fabricate a clean rectangular building from it**. Write
the inconsistency explicitly into the affected `zone_specs` / `surface_specs` / `fenestration_specs`
prose and mark those floors as unsupported. Never normalize the case into a single clean `W × D` to
make the output look tidy.

---

## 3. IntakeOutput field derivation order

Produce in the following order to avoid naming drift when later fields reference earlier ones:

### Step 1 — `building`

Derive every field from `testdata_prompt.json`, never copy a previous case's values:
- name from `TestName` (no spaces; snake/camel mix ok)
- type from `Building type`
- num_floors from `Number of floors` (must equal the `Floor plans` length)
- total_floor_area_m2 from `Floor area`

Use office defaults only where a field is genuinely missing.
(Example only, not reusable: `Smalloffice_20` / `Office` / 3 / 360.)

### Step 2 — `site_location`

Derive from testdata `Building location`: `city = "<Location>_CN"` (naming rule see §5),
weather_file = `<Location>.epw` (must match an EPW under `data/weather/`); climate_zone by geographic
common sense or leave blank. If lat/long are absent, infer from the city/region.
(Example only, not reusable: `Shenzhen` → `Shenzhen_CN` / `Shenzhen.epw`.)

### Step 3 — `zone_specs`

List explicitly per floor per zone, **strictly forbid** `Floor_N_*` template writing.

Naming convention (example): `F{1|2|3}_{orientation|function}` such as `F1_S1` / `F1_Corridor` /
`F2_S1` / `F3_North_Office`. Every zone name is later referenced by `surface_specs` /
`fenestration_specs` / `hvac_specs` / `people_specs` / `lights_specs` and must be **literally
identical** (no case drift, no same/different spelling with a `Zone_` prefix).

Each zone must explicitly give:
- `x_range`, `y_range` (world system, meters)
- `z_floor`, `ceiling_height`
- semantic role (office / corridor / stair / lift / WC / lobby / storage / service / etc.)

**Granularity**: default rule = **every enclosed room is its own thermal zone**, unless the case
explicitly asks for a grouped model. Do **not** merge stairs / lifts / WC / lobby / storage / service
rooms into generic office zones when they are distinct enclosures. (Thermal re-zoning such as
perimeter/core or merge-by-use is a future, rule-driven step, not this baseline.)

**Corridor recognition**: a corridor is a long narrow strip spanning the full building width or full
depth between parallel partition lines — a geometric rule, not a color heuristic. A corridor is a
zone, not a surface. If it spans multiple room cells, collapse it into **one** corridor zone, not
many fragments. Shorter enclosed spaces opening off the strip are rooms.

**Non-rectangular room**: if a room crosses the strip decomposition implied by the dimension chains,
model it as **one** room with the combined span; do not force a false split just because two chains
read more easily separately.

Assign roles from the `ocr_texts` labels phase 1 transcribed (do not invent roles the labels and
geometry do not support).

### Step 4 — `surface_specs`

Each zone has 4 walls + 1 floor + 1 ceiling (top floor's is a roof). **List per surface
explicitly**, no template writing.

Exterior / interior wall judgment:
- exterior = this surface sits on the building footprint boundary (on plan it is one of the
  perimeter wall strokes) → `outside_boundary_condition = Outdoors`
- interior = this surface is between two zones → `outside_boundary_condition = Surface`, with
  `outside_boundary_condition_object` set to the **exact partner surface name** in the adjacent zone
  (also state the adjacent zone). Name **both** sides and point them at each other reciprocally, e.g.
  `Wall_East_F1_R1` (in F1_R1) ↔ `Wall_West_F1_R2` (in F1_R2).

> **EnergyPlus has no `Zone` boundary condition.** Every interzone surface — interior walls **and**
> interfloor floor/ceilings alike — uses `outside_boundary_condition = Surface` + a reciprocal
> `outside_boundary_condition_object`. Writing `outside_boundary_condition = Zone` is an EnergyPlus
> input error (`invalid Outside Boundary Condition="ZONE"` severe). The two paired faces must
> reference each other and use the same (or reverse-stacked) construction (§5.1).

Floor / ceiling:
- F1 floor → Ground (`outside_boundary_condition = Ground`), construction = `Default_GroundFloor`
- F2 floor = F1 ceiling → InterZone, paired (split-pairing must list each pair explicitly, no
  "foreach"), **both faces' construction = `Cons_InterFloor`** (see §5.1)
- F3 floor = F2 ceiling → same, **both faces' construction = `Cons_InterFloor`**
- F3 ceiling = Roof (top floor) → `outside_boundary_condition = Outdoors`, surface type = `Roof`,
  construction = `Default_Roof`

**Cross-floor split-pairing must be explicitly enumerated.** When the two stacked floors share the
same partition layout (aligned), pair zone-to-zone, e.g.:

```
- F2_S1.floor pairs with F1_S1.ceiling  [zone (F2_S1) <-> zone (F1_S1)]
- F2_S2.floor pairs with F1_S2.ceiling
- ...
```

**Misaligned partitions (load-bearing)**: when adjacent floors have different internal partitions, a
single upper-floor zone's footprint may span multiple lower-floor zones (and vice versa). The
InterZone floor / ceiling surface must then be **split at the union of x-break and y-break points of
both stacks**, and **each split piece paired with exactly one zone on the other side**. Write one
line per piece, stating: source zone (this floor) / surface type (floor or ceiling) / split sub-range
(absolute world x-range and/or y-range) / paired zone (adjacent floor) / construction. Example:

```
- Zone_F1_NW ceiling, x 0.00 to 3.75, pairs with Zone_F2_N1 floor, Cons_InterFloor
- Zone_F1_NW ceiling, x 3.75 to 5.00, pairs with Zone_F2_N2 floor, Cons_InterFloor
```

Do not write "each F2 zone floor maps to the same-named F1 zone ceiling", "split at the combined
breaks where needed", or name a split piece without naming its exact paired counterpart — these are
templates, and missing per-piece pairings produced `RoofCeiling:Detailed references an outside
boundary surface that cannot be found` fatals in real runs.

Each surface must explicitly give:
- 4 vertices CCW from outside (zonetool_prompt rule; §4 gives the wall vertex synthesis formulas)
- construction name (see Step 6 placeholders)

### Step 5 — `material_specs` / `construction_specs`

Materials + placeholder constructions:
- `Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window` / `Default_GroundFloor` /
  `Default_Roof` / `Cons_InterFloor`
- glazing uses `WindowMaterial:SimpleGlazingSystem` (**must be a standalone Construction**, not
  stacked with an air gap / a second glass pane, otherwise EP NaN fatal)
- opaque surfaces use a simple stack (e.g. stucco + insulation + gypsum)

**material ↔ construction split (hard).** Materials and constructions are produced by two separate
downstream agents: the material agent creates every material object, the construction agent only
references materials **by name, verbatim**. So a `construction_specs` layer that names a material not
present in `material_specs` is dropped — the construction agent finds no such material and silently
skips that whole Construction (→ missing construction → its surfaces/windows cannot attach → EP fatal).
Therefore:
- **every** Construction layer (opaque and glazing alike) must name a material that is explicitly
  declared in `material_specs`.
- the **glazing material must be declared in `material_specs`** as a named
  `WindowMaterial:SimpleGlazingSystem` (explicit `Name` + U-Factor + SHGC; the material agent creates
  it via `create_glazing_material`). `Default_Window`'s single layer then references that material
  name. Do **not** write the glazing properties only inline under `construction_specs` — an inline
  `WindowMaterial:SimpleGlazingSystem` block that adds no named entry to `material_specs` leaves the
  window Construction with no resolvable layer, so it is dropped and the model ends up with 0 windows.

#### Step 5.1 — InterZone surface single-construction hard constraint

EP hard constraint: **for an InterZone-paired pair of surfaces (the upper zone's floor / the lower
zone's ceiling), the construction layer stacks must be the reverse of each other** (or share one
construction, which satisfies it trivially). Otherwise EnergyPlus fatals with:

```
GetSurfaceData: Construction DEFAULT_CEILING of interzone surface CEILING_F1_S1
does not have the same materials in the reverse order as the construction
DEFAULT_FLOOR of adjacent surface FLOOR_F2_S1
```

**Mandatory rules**:

1. **Do not define two independent constructions for the upper/lower InterZone faces** (e.g.
   `Default_Floor` + `Default_Ceiling`). Even if physically reasonable (carpet on the floor top,
   gypsum on the ceiling bottom), two independent stacks are usually **not mutual reverses** → EP fatal
2. **Correct approach**: define a **single `Cons_InterFloor`**, applied to both the upper zone's
   floor surface and the lower zone's ceiling surface. Example:
   ```
   Cons_InterFloor: layers = [Mat_Floor_Concrete, Mat_IntWall_Gypsum]
   - used for all F1 ceiling / F2 floor InterZone pairs
   - used for all F2 ceiling / F3 floor InterZone pairs
   - both surfaces reference the same Cons_InterFloor -> reverse symmetry holds trivially
   ```
3. In construction_specs, **only the ground floor (F1 floor → Ground) and the roof (F3 ceiling →
   Outdoors)** use independent constructions (`Default_GroundFloor` / `Default_Roof`); they do not
   participate in InterZone pairing

**Counter-example (not allowed)**:
```
❌ Default_Floor: [Carpet, Concrete]
❌ Default_Ceiling: [Concrete, Gypsum]
   -> reverse(Default_Floor) = [Concrete, Carpet] != Default_Ceiling
   -> EP GetSurfaceData fatal
```

**Allowed but not recommended (only if forced to split into two constructions)**:
- the two independent stacks are **strictly mutual reverses** (explicitly enumerate both layer lists
  in the spec and annotate the reverse relationship)
- each independent stack is **itself a palindrome** (e.g. `[Gypsum, Insul, Gypsum]`)

**Link with surface_specs Step 4**: when surface_specs writes the construction field for each
InterZone surface, **both sides must use the same construction name** (e.g. `Cons_InterFloor`); do
not give the upper/lower faces different construction names.

### Step 6 — `fenestration_specs`

**One record per window**, each carrying all of these fields (vertices alone are not enough — the
semantic fields make review / diffing catch facade-axis flips, parent-wall mismatches, and wrong z
before IDF export):
- window name
- floor + parent zone
- facade direction (South / North / East / West)
- parent_surface_name (the exterior wall surface) + parent wall side (Wall_1=South / Wall_2=East / Wall_3=North / Wall_4=West)
- facade plane in absolute world coords (`y=0` south / `x=W` east / `y=D` north / `x=0` west)
- horizontal span axis + absolute range (x-range for south/north, y-range for east/west)
- **absolute world `z_min` / `z_max`** (the authoritative z statement)
- 4 vertices CCW from outside (§4.1)
- referenced construction name

**parent surface mapping** uses the §2.4 formula: from the elevation window stroke local rect →
world rect → which exterior wall it lands on → parent_surface_name = that exterior wall's surface name.
Only exterior walls may host windows; for a blank or missing facade (no window strokes / empty or
absent image path) **explicitly state zero windows on that facade** — never invent fenestration.

**vertices**: synthesize the 4 window vertices CCW from outside per the §4.1 table, using the
window's absolute world `z_min / z_max` (elevation `y_local` is already world z, see §2.4).

**per-window self-check** (before writing each record):
- `z_max - z_min == that window's height` (reconciled against the elevation right-side dim chain)
- `z_min >= z_floor` and `z_max <= z_floor + ceiling_height` — the window must sit inside its parent
  wall's z range, otherwise EnergyPlus emits `Base surface does not surround subsurface (CHKSBS),
  Overlap Status=Partial-Overlap`
- the facade plane matches the parent wall side per the §4.1 mapping

### Step 7 — `schedule_specs` / `people_specs` / `lights_specs` / `hvac_specs`

The input carries geometry, not loads/schedules, so these are assigned from the
default MEP priors. **Default load / schedule / HVAC values: [`priors/mep.md`](priors/mep.md)**
(by testdata `Building type`; office is seeded). Explicit input data overrides the defaults.
This step then enforces the structural completeness contract below.

**`schedule_specs` must be complete**: the schedule subagent runs first and is not re-invoked later,
so every schedule any downstream field references must be defined here, each with an exact name,
schedule type limits, and value profile. Required checklist:
- thermostat heating setpoint schedule
- thermostat cooling setpoint schedule
- ideal loads availability schedule
- people number-of-people schedule
- **people activity-level schedule** (easy to forget — do not omit)
- lights schedule

All naming follows §5.

---

## 4. zone enclosure → polygon → vertex synthesis

Each zone's 4 walls are 4 wall centerlines on plan. Synthesize 4 vertices CCW from outside (top view,
each wall seen clockwise is from the outside):

| face | vertex 1 | vertex 2 | vertex 3 | vertex 4 |
|---|---|---|---|---|
| South wall (y=y_floor) | (x_min, y_min, z_top) | (x_max, y_min, z_top) | (x_max, y_min, z_floor) | (x_min, y_min, z_floor) |
| East wall (x=x_max) | (x_max, y_min, z_top) | (x_max, y_max, z_top) | (x_max, y_max, z_floor) | (x_max, y_min, z_floor) |
| North wall (y=y_max) | (x_max, y_max, z_top) | (x_min, y_max, z_top) | (x_min, y_max, z_floor) | (x_max, y_max, z_floor) |
| West wall (x=x_min) | (x_min, y_max, z_top) | (x_min, y_min, z_top) | (x_min, y_min, z_floor) | (x_min, y_max, z_floor) |
| Floor | (x_min, y_min, z_floor) | (x_max, y_min, z_floor) | (x_max, y_max, z_floor) | (x_min, y_max, z_floor) |
| Ceiling/Roof | (x_min, y_max, z_top) | (x_max, y_max, z_top) | (x_max, y_min, z_top) | (x_min, y_min, z_top) |

Non-rectangular zones use the same CCW principle but need more than 4 polygon vertices; for an
all-rectangular case, 4 vertices suffice.

For a rectangular zone whose floor polygon is ordered SW → SE → NE → NW, the four walls map to
facades as: Wall_1 = South, Wall_2 = East, Wall_3 = North, Wall_4 = West. A window on a facade must
attach to that zone's wall on the same side, not merely the correct facade globally.

### 4.1 Window (fenestration) vertex synthesis

A `FenestrationSurface:Detailed` window must be given vertices CCW **when viewed from outside the
building**. For a window spanning axis-range `[a_min, a_max]` along its facade plane and z-range
`[z_min, z_max]` in absolute world coords:

| Facade | Facade plane | V1 (bottom near) | V2 (bottom far) | V3 (top far) | V4 (top near) |
|---|---|---|---|---|---|
| South | `y = 0` | `(a_min, 0, z_min)` | `(a_max, 0, z_min)` | `(a_max, 0, z_max)` | `(a_min, 0, z_max)` |
| North | `y = D` | `(a_max, D, z_min)` | `(a_min, D, z_min)` | `(a_min, D, z_max)` | `(a_max, D, z_max)` |
| East | `x = W` | `(W, a_max, z_min)` | `(W, a_min, z_min)` | `(W, a_min, z_max)` | `(W, a_max, z_max)` |
| West | `x = 0` | `(0, a_min, z_min)` | `(0, a_max, z_min)` | `(0, a_max, z_max)` | `(0, a_min, z_max)` |

`W` / `D` are the shared footprint width / depth; for South/North the horizontal span is along x, for
East/West along y. `z_min / z_max` are **absolute** world z (elevation `y_local` already = world z,
so no per-floor offset is added on top).

Worked example — F2 south window, `D = 8`, `z_floor_F2 = 3.60`, sill 1.00, head 2.80, x-span 1.40..3.80:
- `z_min = 3.60 + 1.00 = 4.60`, `z_max = 3.60 + 2.80 = 6.40`
- vertices CCW from outside: `(1.40, 0, 4.60)` → `(3.80, 0, 4.60)` → `(3.80, 0, 6.40)` → `(1.40, 0, 6.40)`

If the parent wall lives at `z ∈ [3.60, 7.20]` but the window vertices land at `z ∈ [1.00, 2.80]`
(per-floor offset forgotten), the wall does not surround the sub-surface and EnergyPlus emits
`CHKSBS Partial-Overlap` for every such window.

---

## 5. Naming rules (mandatory)

Character set: letters / digits / `_` only. **Forbidden**: spaces, commas, semicolons, hyphens,
slashes, parentheses.

Cross-field references must be **literally identical**:
- a construction in `surface_specs` / `fenestration_specs` must appear in `construction_specs`
- a schedule in `hvac_specs` / `people_specs` / `lights_specs` must appear in `schedule_specs`
- a zone in `surface_specs` / `fenestration_specs` / `hvac_specs` / `people_specs` / `lights_specs`
  must appear in `zone_specs`

Legal: `Shenzhen_CN` / `Zone_F2_C` / `Window_Office_South_1`
Illegal: `Shenzhen, China` / `Zone F2 C` / `Wall-01`

---

## 6. Disallowed writing

- ❌ `Floor_N_*` template / `for N in 2..5` / `typical floors` / `repeat for upper floors`
- ❌ `TBD` / `same as above` / `see above` / `etc.` / `...`
- ❌ cross-field naming drift (`Zone_F1_S1` vs `F1_S1` vs `zone_f1_s1`)
- ❌ surface_specs writing "each F2 zone floor maps to F1 ceiling" — must enumerate each pair
- ❌ fenestration_specs missing parent_surface_name or missing CCW vertices
- ❌ SimpleGlazingSystem stacked with an air gap / second glass pane in one Construction (EP will fatal)

---

## 7. Self-check list

After producing IntakeOutput, go through each item:

- [ ] all 11 fields present
- [ ] all zones explicitly enumerated (no template writing), per-floor zone count consistent with testdata `thermal_zones` (e.g. 7+8+4 = 19)
- [ ] all surfaces explicitly enumerated per zone (each zone 4 walls + floor + ceiling/roof)
- [ ] cross-floor split-pairing enumerated per pair
- [ ] every fenestration gives parent_surface_name mapping back to a valid exterior wall surface name
- [ ] every window's `[z_min, z_max]` lies inside its parent wall's `[z_floor, z_floor + ceiling_height]` (CHKSBS prevention, §3 Step 6)
- [ ] cross-field references literally identical (construction / schedule / zone)
- [ ] naming character set legal
- [ ] shared-footprint invariant holds (all floors same `W × D`, ≤ 0.01 m) and dimension chains pass `sum(inner) == outer` (§2.1 / §2.5)
- [ ] per-floor coverage: union of zone footprints = shared footprint, no overlaps, no unexplained voids (§2.6)
- [ ] special spaces (corridor / stair / lift / WC / lobby / storage) are not dropped or merged into office zones; a full-span corridor is one zone (§3 Step 3)
- [ ] `schedule_specs` defines all 6 checklist schedules, including the people activity-level schedule (§3 Step 7)
- [ ] no unsupported geometry (setback / cantilever / multi-footprint / atrium) silently normalized into a clean box (§2.6)
- [ ] WWR self-check: total window area per facade (from the fenestration records) is consistent with that facade's exterior wall area and the elevation; counts are per case (example only: sm_20 south 3 windows × 2 floors × 2.40×1.80)
- [ ] z values continuous with no gap: F1 ceiling top = F2 floor bottom = 3.60, F2 ceiling top = F3 floor bottom = 7.20
- [ ] **InterZone single-construction** (§5.1): every F2 floor / F1 ceiling pair's construction field equals `Cons_InterFloor` (**not Default_Floor / Default_Ceiling**); F3 floor / F2 ceiling same; the construction names `Default_Floor` / `Default_Ceiling` do not exist

---

## 8. Relationship to the existing skill docs

This document replaces the phase 2 task's dependence on `skills/energyplus_mcp/*.md`. With vectorized
JSON in hand, all "image-reading" parts of those docs are void; the essence of their "output
contract" parts is consolidated here in §3–§7, and the zonetool vertex synthesis table is in §4.

If while running phase 2 you find a strong constraint from the old skill that this document does not
cover, append a `phase2_followup_notes` record at the end of your output so this document can be
extended later.
