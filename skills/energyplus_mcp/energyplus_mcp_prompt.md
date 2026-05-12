# EnergyPlus Intake Geometry Rules

## Scope

This document is loaded in full by the intake prompt together with every other
markdown file in this directory. Treat the whole directory as one mandatory
rule library.

It governs how intake reads building text plus architectural drawings and turns
that evidence into `IntakeOutput` natural-language specs. This is **not** an MCP
execution workflow. Do not rely on tool calls, YAML export steps, or image
annotation scripts here.

## Core Principles

1. Extract only what the text and drawings support. Do not invent geometry.
2. Trust dimension-chain numbers over pixel measurement.
3. Use one building-wide world coordinate system.
4. Preserve per-floor differences in internal partitioning.
5. Unsupported setbacks / cantilevers / atria must not be silently normalized.
6. Make intermediate geometric facts explicit in your internal derivation before
   writing the final specs.

---

## Input Package

### Format A (current standard)

Expect a `testdata_prompt.json` with:
- required per-floor plans under the `Floor plans` array, or legacy single-plan
  fallback via `Top view path of the building`
- optional `South_view.png`, `North_view.png`, `East_view.png`, `West_view.png`
- optional supplementary drawing (`supp_plan.png`, section, axonometric, etc.)

### Image Labels Are Authoritative

If the surrounding prompt labels an image as `Floor <k> plan view`,
`South facade elevation`, etc., trust that label to assign the image's role.
Do **not** re-infer floor number or facade orientation from the picture alone.

---

## Mandatory Internal Derivation Order

Before you write the final `IntakeOutput`, you must internally complete the
following derivation stages in order. Do not jump directly from image impression
to final prose.

1. **Input validation**
   - verify which floor plans exist
   - verify which facades are present vs. blank
   - verify whether a supplementary drawing exists
2. **Shared-footprint check**
   - read each floor's outer `W_f, D_f`
   - verify all floors share the same `W × D`
3. **Dimension extraction**
   - read x/y segment chains per floor
   - read floor-height and window-height chains per facade
   - perform all required checksum tests
4. **Room enumeration**
   - enumerate every enclosed space on every floor before assigning roles
5. **Role assignment**
   - classify each space as office / corridor / stair / lift / WC / lobby /
     storage / service room / other
6. **Coordinate synthesis**
   - derive per-floor `xs_f / ys_f`
   - derive each zone's x-range, y-range, `z_floor`, and ceiling height
7. **Topology synthesis**
   - derive floor-by-floor adjacency and exterior / interior boundaries
8. **Fenestration synthesis**
   - derive every explicit window instance with facade, parent zone, wall side,
     span, sill, and head height
9. **Final output assembly**
   - only now write the 11-field `IntakeOutput`

If any earlier stage is uncertain or fails a checksum, do not compensate by
writing vague final specs.

---

## Zone Granularity

Default rule: **every enclosed room is its own thermal zone** unless the user
explicitly asks for a grouped model.

This includes:
- individual offices
- corridor segments
- staircases
- lift / elevator shafts
- WC / toilets
- storage / service rooms
- lobbies / entrance halls

### Room Enumeration Before Geometry Synthesis

Before assigning coordinates or writing `zone_specs`, first enumerate every
visually enclosed space floor by floor. This replaces the old annotate step's
main function.

Required discipline:
- first list all enclosed spaces you can see on a floor
- then assign semantic roles to those spaces
- only then derive coordinates and adjacency

Do not let coordinate derivation skip room enumeration. Missing rooms early will
propagate into broken surfaces and windows later.

### Corridor Recognition

A corridor is a **long narrow white strip** spanning the full building width or
full building depth between parallel partition lines. This is a geometric rule,
not a color heuristic. Shorter enclosed spaces opening off that strip are rooms.

### Special Spaces

Do not merge stairs, lifts, WC, lobby, or service rooms into generic office
zones when they are visibly distinct in plan.

### Non-Rectangular Room Handling

If a physical room crosses the strip decomposition implied by dimension chains,
model it as **one room** with the combined span. Do not force a false split
just because two chains are easier to read separately.

---

## CAD-Style Drawing Convention

The project's baseline cases use a fixed CAD-style drawing convention. Apply the
following rules whenever the drawings match that style.

### D1. Units

- All dimension-chain numbers are in **meters**.
- Numbers are typically written with two decimal places.
- Do not reinterpret them as millimetres.

### D2. Dimension Chains

For each axis:
- the **outer chain** is the total length
- the **inner chain** is the segment partition of that same total

Hard checksum:

`sum(inner segments) == outer total`

If the checksum fails, re-read the drawing. Do not continue with guessed values.

### Required Internal Dimension Extraction

Even though intake no longer writes `claude_ep.md`, you must still internally
recover the same class of geometric facts that the old workflow externalized.
Before producing final specs, determine:
- per-floor `W_f`, `D_f`
- per-floor x-segment chain and y-segment chain
- per-floor cumulative boundary arrays `xs_f`, `ys_f`
- corridor strip position on each floor
- per-facade floor-height chain
- per-window facade placement chain, sill height, and head height

The final `zone_specs`, `surface_specs`, and `fenestration_specs` must reflect
these extracted values, not vague visual guesses.

### D3. Per-Floor Plans

For each floor plan:
- thick black lines = walls
- light-gray fill between black lines = wall body
- white enclosed regions = rooms or corridors
- x increases left → right
- y increases bottom → top

The building-wide world origin is the **southwest inner corner** of the shared
footprint.

### D3.1 Shared-Footprint Invariant

Every floor must share the same outer rectangular footprint `W × D`.
Internal segmentation may differ floor by floor, but the outer totals must
satisfy:
- `W_f == W_g`
- `D_f == D_g`
for all floors `f, g` (tolerance ≤ 0.01 m).

If the per-floor outer chains disagree, treat the case as unsupported in the
current revision. Do not silently pick one floor's footprint.

### D4. Facade Elevations

Facade filenames are authoritative:
- `South_view.png` → south facade
- `North_view.png` → north facade
- `East_view.png`  → east facade
- `West_view.png`  → west facade

Do not reinterpret orientation from picture content.

For provided facades:
- left vertical chain = floor heights
- right vertical chain = `top_gap | window_height | sill_height`
- bottom horizontal chain = window placement along the facade

Hard checksum on each floor with windows:

`top_gap + window_height + sill_height == floor_height`

### D4.1 Blank Facade Rule

Treat a facade as blank if either of these is true:
1. the JSON path is empty or the file is missing
2. the facade image exists but has no blue window rectangles

Blank facade means **zero windows on that facade**. Do not invent fenestration.

### D4.2 Per-Floor Window Chain — Read Each Floor Separately

A single facade elevation typically shows **distinct window chains for each
floor**. Different floors on the same facade may have:
- different numbers of windows
- different window widths and gaps
- different `top_gap / window_height / sill_height` decomposition
- one floor blank while another floor on the same facade carries windows

Hard rule: read each floor's horizontal window chain **independently** from
that floor's portion of the facade elevation. Do **not** reuse one floor's
window placement for another floor unless the elevation explicitly shows
identical patterns. Do **not** infer "the facade has windows" from the
presence of windows on any single floor.

For each provided facade, perform per-floor enumeration:
- list each floor's window count separately
- list each floor's window x-spans (or y-spans for east / west) separately
- mark any floor that is locally blank on this facade

This is the explicit replacement for the old workflow's per-floor Fenestration
Table rows.

### D4.3 Upper-Floor Window — Absolute World Z (Hard Rule)

Windows must be expressed in the building-wide world coordinate system, not in
per-floor local coordinates. Use these formulas for every window on floor `f`
with finished-floor level `z_floor`:

```
window_sill_z = z_floor + sill_height
window_head_z = z_floor + sill_height + window_height
```

Worked two-floor example with `floor_height = 3.60`, `sill_h = 1.00`,
`win_h = 1.80`:

- F1 (`z_floor = 0.00`) → `sill_z = 1.00`, `head_z = 2.80`
- F2 (`z_floor = 3.60`) → `sill_z = 4.60`, `head_z = 6.40`
- F3 (`z_floor = 7.20`) → `sill_z = 8.20`, `head_z = 10.00`

Upper floors **must** add the accumulated `z_floor`. Forgetting it drops the
window onto the ground floor and makes its absolute z range fall outside the
parent wall's z range, which causes EnergyPlus `Base surface does not surround
subsurface (CHKSBS)` partial-overlap warnings on every upper-floor window.

When writing `fenestration_specs`, the **absolute** `z_min..z_max` for each
window is mandatory. Per-floor `sill_height / head_height` numbers may
accompany it as auxiliary scratch, but world-z is the authoritative value the
downstream geometry agent must consume.

Note: the formulas above assume a single window per floor per facade
(`N = 1`). When a floor has two or more windows stacked on the same facade
(`N >= 2`, e.g. high window + low window on one wall), the right-side chain
becomes `top_gap | win_h_N | inter_gap_{N-1} | win_h_{N-1} | ... | inter_gap_1
| win_h_1 | sill_h_1`. For the general N-window case, including the
`inter_gap` term and the per-window subscripted formulas, follow the
authoritative version in
[intake_output_contract.md](intake_output_contract.md) under
`fenestration_specs > Right-side chain pattern (general)`. Self-check rule is
the same in both files: `z_max_i - z_min_i` must equal that specific window's
`win_h_i`, never `top_gap` or `inter_gap`.

### D5. Out-of-Scope for the Current Shared-Footprint Regime

The current intake regime assumes **shared exterior footprint across floors**.
The following are therefore out of scope for the current production intake path:
- setbacks
- cantilevers
- multiple exterior footprints across floors
- atrium / void cases that require breaking the shared-footprint assumption

If such a case is visible, do not silently flatten it into an ordinary
shared-footprint building.

Unified handling rule (both manual Step 4 and structured-output runtime path):

1. Detect the unsupported feature explicitly during dimension extraction.
2. Refuse to fabricate a clean rectangular building from it. Never silently
   normalize a setback / cantilever / multi-footprint case into a single
   shared `W × D`.
3. Surface the inconsistency to the consumer:
   - in the **manual Step 4 workflow**, stop and tell the user the case is
     outside the current shared-footprint regime; do not produce an
     `IntakeOutput`
   - in the **structured-output runtime path**, since the contract still
     requires returning an `IntakeOutput`, write the inconsistency explicitly
     into `zone_specs` / `surface_specs` / `fenestration_specs`. Mark the
     affected floors as unsupported in prose. Do **not** invent geometry to
     make the output look clean.

In both contexts, "do not silently fabricate" is the load-bearing rule. The
only difference is what the consumer hears at the end (a human in the manual
path, a downstream agent in the runtime path).

### D6. Ambiguity Handling

When evidence is incomplete or conflicting, do not handle all ambiguity the same
way. Use this policy:

- **Fail fast** when the ambiguity breaks global geometry under the current
  shared-footprint regime:
  - conflicting floor footprint totals
  - conflicting floor-count evidence
  - conflicting facade orientation labels
  - inconsistent facade height chains that change floor stacking
- **Conservative default allowed** when the ambiguity is local and does not
  change topology:
  - missing non-critical material detail
  - missing non-critical office defaults outside geometry
- **Must call out uncertainty explicitly** when a local geometric detail is
  plausible but not provable from the drawings:
  - ambiguous room role between two service categories
  - unclear supplementary detail that does not override the main plan

Do not silently normalize a globally ambiguous case into a clean rectangular
building.

---

## Topology Sketch Requirement

Before writing `surface_specs`, internally form a floor-by-floor topology sketch.
This replaces the old workflow's floor-plan diagram and adjacency-matrix role.
At minimum, you must know:
- which zones occupy each strip or cell on each floor
- which boundaries are exterior
- which zone pairs are adjacent
- which floors stack above which lower-floor zones

If you cannot form a coherent topology sketch, your `surface_specs` will be too
weak for downstream geometry agents.

---

## Geometry Self-Check Before Writing Specs

Before finalizing `IntakeOutput`, verify:
1. every used dimension chain closes against its total
2. every floor respects the shared `W × D` footprint
3. every zone belongs to the correct floor and role
4. corridors / stair / WC / lift are not dropped
5. no blank facade receives windows
6. for every window, the absolute z range is computed as
   `z_floor + sill_height` to `z_floor + sill_height + window_height` and lies
   inside the parent wall's z range `[z_floor, z_floor + ceiling_height]`
7. each facade was read per-floor (different floors on the same facade may have
   different window chains, including some floors being locally blank)
8. unsupported geometry is not silently normalized
9. you have completed room enumeration before coordinate synthesis
10. you have completed dimension extraction before final prose generation
11. you can internally map every window to a real parent zone and exterior wall
12. for vertically stacked zones with **misaligned partitions** between floors,
    every InterZone floor / ceiling surface is split at the union of break
    points and each piece is paired explicitly with the correct upper / lower
    zone — see `intake_output_contract.md` `surface_specs` for the required
    enumeration density
