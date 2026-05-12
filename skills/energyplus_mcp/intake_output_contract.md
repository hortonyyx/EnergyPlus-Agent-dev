# Intake Output Contract

## Scope

This document defines how the intake stage must write `IntakeOutput`.
It is loaded together with every other markdown file in this directory.
Follow the whole directory as one rule library.

The intake stage returns exactly one structured `IntakeOutput` object with:
- `building`
- `site_location`
- `zone_specs`
- `material_specs`
- `schedule_specs`
- `construction_specs`
- `surface_specs`
- `fenestration_specs`
- `hvac_specs`
- `people_specs`
- `lights_specs`

The nine `*_specs` fields are natural-language instructions for downstream
agents, so they must be explicit, mechanically usable, and internally
consistent.

---

## Naming Rules

### Allowed Format

Every name must use only:
- letters
- digits
- `_`

Forbidden everywhere in names:
- spaces
- commas
- semicolons
- hyphens
- slashes
- parentheses

Examples:
- valid: `Shenzhen_CN`, `Zone_F2_C`, `Window_Office_South_1`
- invalid: `Shenzhen, China`, `Zone F2 C`, `Wall-01`

### Exact Reuse Across Fields

Names referenced across subsystems must match **exactly**.
No synonyms, no pluralization, no case drift.

Specifically:
- constructions named in `surface_specs` or `fenestration_specs` must be
  defined in `construction_specs`
- schedules named in `hvac_specs`, `people_specs`, or `lights_specs` must be
  defined in `schedule_specs`
- zones named in `surface_specs`, `fenestration_specs`, `hvac_specs`,
  `people_specs`, or `lights_specs` must be defined in `zone_specs`

---

## No Compression, No Placeholders

Do **not** use placeholders such as:
- `TBD`
- `same as above`
- `see above`
- `etc.`
- `...`

Do **not** use template notation or compressed multi-instance shorthand such as:
- `Floor_N_*`
- `for N in 2..5`
- `typical floors`
- `repeat for upper floors`

Every concrete zone, surface relationship, and window instance that matters to
later agents must be explicitly enumerated.

---

## Field-by-Field Writing Contract

### `building`

Use reasonable office defaults when a parameter is missing, but keep the name
concrete and properly formatted.

### `site_location`

If latitude / longitude are not given, infer them from the city or region.
Use a formatted site name such as `Shenzhen_CN`.

### `zone_specs`

`zone_specs` is the geometric contract for the downstream phases.
It must explicitly enumerate **every zone**, floor by floor.

For every zone, specify at least:
- exact zone name
- floor number
- semantic role (office / corridor / stair / lift / WC / lobby / storage / etc.)
- x-range in meters
- y-range in meters
- floor elevation `z_floor`
- ceiling height
- any important adjacency fact needed later

Do not collapse multiple floors into one template description.

#### Preferred zone-specs structure

Write `zone_specs` in a way that approximates the old workflow's zone
coordinates table, even though the final carrier is prose rather than markdown
tables.

Recommended structure:
1. state the shared building footprint `W × D`
2. group the description by floor
3. for each floor, list every zone one by one
4. for each zone, state:
   - name
   - role
   - x-range
   - y-range
   - area or equivalent span information
   - `z_floor`
   - ceiling height
   - major adjacent zones or exterior sides

This should be dense enough that a downstream agent could reconstruct a zone
coordinates table mechanically.

#### Coverage requirements

For every floor, `zone_specs` must make it possible to verify that:
- all zones together cover the shared footprint
- there are no unexplained voids
- there are no overlaps
- corridors remain explicit zones
- stairs / lift / WC / service rooms are not dropped

### `material_specs`

List the actual material types needed by the case. If a parameter is unknown,
use a reasonable office default instead of leaving a placeholder.

### `construction_specs`

Define every construction referenced later in `surface_specs` or
`fenestration_specs`.

### `schedule_specs`

This field must be complete because the schedule agent runs first and will not
be re-invoked later.

Whenever the downstream phases need schedules, define them here with:
- exact schedule name
- schedule type limits
- value profile

The downstream schedule checklist is:
- thermostat heating setpoint schedule
- thermostat cooling setpoint schedule
- ideal loads availability schedule
- people number-of-people schedule
- people activity-level schedule
- lights schedule

Do not forget the activity-level schedule.

### `surface_specs`

Describe surfaces in a way that can be derived mechanically from zone geometry.
Make explicit:
- which boundaries are exterior vs interior
- which zones are adjacent across each shared boundary
- which construction name each surface type uses
- how floors / ceilings pair between vertically stacked zones

The described zone layout on each floor must cover the shared footprint with no
unexplained gaps or overlaps.

#### Required surface-specs density (not optional)

For each floor, the topology must be **recoverable as if** an adjacency matrix
and a floor-topology sketch had been written first. The downstream agent must
be able to read off, without guesswork:
- which sides of each zone are exterior
- which neighboring zone, if any, touches each interior side
- which zone above / below pairs with each floor / ceiling surface
- which surfaces are roof vs ground-contact vs interzone

#### Same-floor adjacency: enumerate every zone explicitly

For every floor, enumerate every zone one at a time and list, per zone:
- which of its four wall sides are exterior
- which neighboring zone touches each interior side

No template or grouped shorthand. If a wall faces another zone, name that
zone. Vague phrasing like "interior walls are adjacent to other zones" is
forbidden.

#### Cross-floor split-pairing: required enumeration (load-bearing)

When two adjacent floors have **different internal partitions**, a single
upper-floor zone's footprint may span multiple lower-floor zones (and vice
versa). The InterZone floor / ceiling surface must then be **split** at the
union of x-break and y-break points of both stacks, and each split piece must
be paired with exactly one zone on the other side.

For every zone whose ceiling or floor sits on a misaligned partition, write a
per-piece pairing line. Each line must state:
- the source zone (this floor)
- the surface type (ceiling or floor)
- the split sub-range (x-range and / or y-range in absolute world coords)
- the paired zone (the adjacent floor)

Example pattern (one zone, one piece per line):

```
Zone_F1_NW ceiling x 0.00 to 3.75 pairs with Zone_F2_N1 floor
Zone_F1_NW ceiling x 3.75 to 5.00 pairs with Zone_F2_N2 floor
```

Forbidden under this rule:
- "split at the combined x-breaks where needed" without per-piece enumeration
- naming a `*_CEILING_E` or `*_FLOOR_W` split piece without naming its exact
  paired counterpart
- letting the downstream agent guess which upper-floor zone sits over a given
  sub-range of a lower-floor ceiling

Reason this is load-bearing: missing per-piece pairings produced
`RoofCeiling:Detailed references an outside boundary surface that cannot be
found` fatal errors in EnergyPlus during real runs.

### `fenestration_specs`

Explicitly enumerate every window instance.

Rules:
- windows only belong on real exterior walls
- blank facades must receive zero windows
- if all facades are blank, state that explicitly
- every window's z range must be expressed in **absolute world coordinates**,
  with the floor's `z_floor` already added in

#### Required fenestration-specs density (one record per window)

For every window, write one record. Each record must include all of:
- window name
- floor
- parent zone
- facade direction (South / North / East / West)
- parent wall side (Wall_1=South / Wall_2=East / Wall_3=North / Wall_4=West)
- facade plane (e.g. `y = 0` for south, `x = W` for east, `y = D` for north,
  `x = 0` for west, in absolute world coords)
- horizontal span axis and absolute range (x-range for south / north;
  y-range for east / west)
- **absolute z_min and z_max** in world coords — this is the authoritative
  z statement
- referenced construction name

Per-floor `sill_height` and `window_height` (as read off the elevation right
chain) may accompany the record as auxiliary scratch values, but they are
**not** the z statement. Downstream geometry must consume the absolute z
range; if a record gives only sill / head numbers without the absolute z
range, the record is incomplete.

#### Right-side chain pattern (general)

A facade right-side chain alternates **gaps** and **windows**, read top-to-bottom:

```
top_gap | win_h_N | inter_gap_{N-1} | win_h_{N-1} | ... | inter_gap_1 | win_h_1 | sill_h_1
```

where `N` is the number of windows stacked on that floor (counted bottom-up,
so `win_h_1` is the lowest window). Cases:

- `N = 0`: chain is just `floor_height` itself (no windows on this floor for
  this facade — locally blank, write nothing).
- `N = 1` (most common): chain has 3 segments — `top_gap | win_h_1 | sill_h_1`.
- `N >= 2`: chain has `2N + 1` segments — gaps and windows alternate.

Checksum (every floor with windows): the entire chain must sum to the
`floor_height` (= `ceiling_height` of zones on that floor).

#### Per-window world-z formula (mandatory, generalizes to N windows)

For window `i` on floor `f` (counted bottom-up, `i = 1` = lowest):

```
z_min_i = z_floor + sill_h_1 + sum over k in [1..i-1] of (win_h_k + inter_gap_k)
z_max_i = z_min_i + win_h_i
```

Self-check per window:

```
z_max_i - z_min_i  must equal  win_h_i
```

That is — only the chain segment **labelled as that specific window's
height** sets `z_max - z_min`. `top_gap`, `inter_gap_*`, and `sill_h_*` are
**different** chain segments and never participate in `z_max - z_min`.

Worked example A (single window per floor, `N = 1`, all three floors
same dimensions): `top_gap = 0.80, win_h_1 = 1.80, sill_h_1 = 1.00`,
`floor_height = 3.60`. Chain sum 0.80 + 1.80 + 1.00 = 3.60 ✓.

- F1 (`z_floor = 0.00`) → `z_min_1 = 1.00, z_max_1 = 2.80`, height 1.80
- F2 (`z_floor = 3.60`) → `z_min_1 = 4.60, z_max_1 = 6.40`, height 1.80
- F3 (`z_floor = 7.20`) → `z_min_1 = 8.20, z_max_1 = 10.00`, height 1.80

Worked example B (single window, F3 corridor on a tall floor): `top_gap = 1.40,
win_h_1 = 2.40, sill_h_1 = 1.00`, `floor_height = 4.80`. Chain sum 1.40 + 2.40
+ 1.00 = 4.80 ✓.

- F3 (`z_floor = 7.20`) → `z_min_1 = 7.20 + 1.00 = 8.20`,
  `z_max_1 = 8.20 + 2.40 = 10.60`, height 2.40

**Common mistake to avoid (example B is exactly where this trips up)**:
writing `z_max_1 = z_min_1 + top_gap = 8.20 + 1.40 = 9.60`. Wrong — `top_gap`
is the segment between the top of the window and the ceiling, not the
window's own height. The result is a window 1.40 m tall instead of 2.40 m
tall, which downstream propagates into a too-short window in the IDF even
though all other geometry is correct.

Worked example C (two windows stacked on one floor, `N = 2`, demonstrates the
inter_gap term): `top_gap = 0.50, win_h_2 = 1.20, inter_gap_1 = 0.40,
win_h_1 = 1.20, sill_h_1 = 0.30`, `floor_height = 3.60`. Chain sum
0.50 + 1.20 + 0.40 + 1.20 + 0.30 = 3.60 ✓.

- F1 lower window (`i = 1`): `z_min_1 = 0 + 0.30 = 0.30`,
  `z_max_1 = 0.30 + 1.20 = 1.50`, height 1.20
- F1 upper window (`i = 2`): `z_min_2 = 0 + 0.30 + 1.20 + 0.40 = 1.90`,
  `z_max_2 = 1.90 + 1.20 = 3.10`, height 1.20

Both windows pass `z_max_i - z_min_i == win_h_i == 1.20`. Note how the upper
window's `z_min_2` includes the lower window's height **and** the inter_gap
between them; mixing inter_gap into `z_max_2 - z_min_2` would be the same
class of mistake as the top_gap confusion in example B.

#### Per-window self-check before writing the record

Before writing each window record, verify in your head:
- `z_max_i - z_min_i == win_h_i` (the right chain segment, identified by the
  inventory you wrote earlier — see Right-side chain pattern above)
- `z_min_i >= z_floor` (window doesn't sit below its floor)
- `z_max_i <= z_floor + ceiling_height` (window doesn't poke above its ceiling)
- the parent wall named is exterior (not shared with another zone)
- the facade plane matches the parent wall side per the Wall_1..Wall_4 mapping
- for floors with `N >= 2` windows on the facade, every `z_min_i` correctly
  includes the cumulative `win_h_k + inter_gap_k` for all `k < i`

If any of these fails, the record is wrong; fix it before writing.

Reason this is load-bearing: forgetting the `z_floor` offset, or confusing
`top_gap / inter_gap / window_height` chain segments in the `z_max - z_min`
calculation, both produce window vertices that fall outside the parent wall
or have the wrong height in IDF. Real-case observations:

- forgetting `z_floor` → `Base surface does not surround subsurface (CHKSBS),
  Overlap Status=Partial-Overlap` warnings for every upper-floor window
- confusing `top_gap` for `window_height` → windows in IDF appear at the
  correct sill but ~half the intended height (silently — EnergyPlus accepts
  it as a valid smaller window, OpenStudio reveals the geometric error on
  visual inspection)

### `hvac_specs`, `people_specs`, `lights_specs`

These must reference explicit zone names and explicit schedule names already
introduced elsewhere. Do not use templates or grouped placeholders.

---

## Final Consistency Check Before Returning

Before returning `IntakeOutput`, verify all of the following:
1. every concrete zone referenced anywhere exists in `zone_specs`
2. every construction referenced anywhere exists in `construction_specs`
3. every schedule referenced anywhere exists in `schedule_specs`
4. every zone is explicitly enumerated with no compressed shorthand
5. every window belongs to a real non-blank facade and a real exterior wall
6. no forbidden punctuation appears in any name field
7. no placeholder or deferred wording remains in any `*_specs` field
8. `zone_specs` is detailed enough to recover per-floor coordinates and coverage
9. `surface_specs` is detailed enough to recover adjacency and exterior/interior boundaries
10. `fenestration_specs` is detailed enough to recover one explicit record per window
11. for every pair of vertically stacked floors with **misaligned partitions**,
    every InterZone ceiling / floor split piece is named with its paired
    counterpart on the other floor — no piece is left dangling
12. every window record carries **absolute world z_min / z_max**, and each
    window's `[z_min, z_max]` lies inside its parent wall's
    `[z_floor, z_floor + ceiling_height]`
