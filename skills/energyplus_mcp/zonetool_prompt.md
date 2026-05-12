# Coordinate And Topology Reference

## Scope

This document provides the coordinate conventions that intake must preserve in
its written specs so downstream geometry agents can reconstruct the building
correctly.

It is loaded together with every other markdown file in this directory.
Treat the whole directory as one rule library.

---

## Absolute World Coordinates

All zone geometry is described in a single building-wide world coordinate system.

- origin = southwest inner corner of the shared building footprint
- x increases west → east
- y increases south → north
- z increases upward by stacking floor finished-floor levels

Zone coordinates must be expressed in **absolute world coordinates**, not local
per-room coordinates.

---

## Per-Floor Boundary Arrays

For each floor `f`, build boundary arrays independently from that floor's own
segment chains:

- `xs_f = [0, ... , W]`
- `ys_f = [0, ... , D]`

The inner partitions may differ floor by floor, but each floor must still end at
the shared totals `W` and `D`.

Do not reuse one floor's room grid for another floor unless the drawings truly
show identical partitions.

---

## Floor Elevation Stacking

Let `h_f` be the floor height for floor `f`, read from the facade left chain.
Then:
- Floor 1 finished floor level: `z_1 = 0`
- Floor 2 finished floor level: `z_2 = h_1`
- Floor 3 finished floor level: `z_3 = h_1 + h_2`
- and so on

Every zone on the same floor shares the same `z_floor` and the same
`ceiling_height = h_f`.

---

## Zone Footprints

For a rectangular room cell on floor `f` bounded by:
- `x_min = xs_f[i]`
- `x_max = xs_f[i+1]`
- `y_min = ys_f[j]`
- `y_max = ys_f[j+1]`

its floor polygon in CCW order is:

1. `(x_min, y_min, z_f)`
2. `(x_max, y_min, z_f)`
3. `(x_max, y_max, z_f)`
4. `(x_min, y_max, z_f)`

Intake does not emit vertices directly, but its zone descriptions must stay
compatible with this reconstruction rule.

### Corridor Collapse Rule

If a corridor spans the full width or full depth across multiple room cells,
treat it as **one corridor zone**, not many tiny corridor fragments.

---

## Coverage Rules

For each floor independently:
- the union of all zone footprints must equal the full shared footprint
- zones must not overlap
- unexplained voids must not appear inside the footprint

If a room crosses a strip boundary, preserve it as one room and adjust the
neighbouring partitions accordingly.

---

## CCW Convention

Whenever a downstream phase reconstructs vertices from your specs, the expected
polygon order is counterclockwise when viewed from above.

Signed-area test:

- positive signed area → CCW (correct)
- negative signed area → CW (must be reversed)

Your written x/y ranges and boundary ordering must remain consistent with this
expectation.

---

## Facade And Parent-Wall Mapping

For the standard rectangular zone whose floor polygon is ordered:
- SW → SE → NE → NW

its four walls map to facades as follows:
- Wall_1 = South
- Wall_2 = East
- Wall_3 = North
- Wall_4 = West

This mapping matters when writing `fenestration_specs`.
A window on the south facade of a rectangular zone must attach to that zone's
south wall, not merely to the correct facade globally.

### Exterior-Wall Rule

Only exterior walls may host windows.
A wall shared between two zones is an interior partition and must not receive
fenestration.

---

## Window Coordinate Rules

For every explicit window instance, your specs must preserve enough information
for downstream geometry to recover:
- facade direction
- parent zone
- parent wall side (Wall_1..Wall_4 per the mapping above)
- facade plane in absolute world coords (`y=0`, `x=W`, `y=D`, `x=0`)
- horizontal span along the facade (axis and absolute range)
- **absolute world z_min and z_max** (i.e. with `z_floor` already added in)

For south / north facades, the horizontal span is along x.
For east / west facades, the horizontal span is along y.

Blank facades must yield zero windows.

### Window Vertex Synthesis Templates (CCW from outside)

A `FenestrationSurface:Detailed` window must be given vertices in
counterclockwise order **when viewed from outside the building**. For a window
that spans axis-range `[a_min, a_max]` along its facade plane and z-range
`[z_min, z_max]` in absolute world coords, use these templates:

| Facade | Facade plane | V1 (bottom near) | V2 (bottom far) | V3 (top far) | V4 (top near) |
|---|---|---|---|---|---|
| South | `y = 0`     | `(a_min, 0,     z_min)` | `(a_max, 0,     z_min)` | `(a_max, 0,     z_max)` | `(a_min, 0,     z_max)` |
| North | `y = D`     | `(a_max, D,     z_min)` | `(a_min, D,     z_min)` | `(a_min, D,     z_max)` | `(a_max, D,     z_max)` |
| East  | `x = W`     | `(W,     a_max, z_min)` | `(W,     a_min, z_min)` | `(W,     a_min, z_max)` | `(W,     a_max, z_max)` |
| West  | `x = 0`     | `(0,     a_min, z_min)` | `(0,     a_max, z_min)` | `(0,     a_max, z_max)` | `(0,     a_min, z_max)` |

Here `W` and `D` are the shared building footprint width and depth, and
`z_min / z_max` are **absolute** world z values, not per-floor offsets.

Worked example. Floor 2 south window on a building with `D = 8`,
`z_floor_F2 = 3.60`, sill `1.00`, head `2.80`, x-span `1.40..3.80`:
- `z_min = 3.60 + 1.00 = 4.60`
- `z_max = 3.60 + 2.80 = 6.40`
- vertices CCW from outside:
  - `(1.40, 0, 4.60)` → `(3.80, 0, 4.60)` → `(3.80, 0, 6.40)` → `(1.40, 0, 6.40)`

If you write the records with sill/head as local offsets and forget to add
`z_floor`, the vertices land at `z ∈ [1.00, 2.80]` but the parent wall lives
at `z ∈ [3.60, 7.20]` — the wall does not surround the sub-surface and
EnergyPlus emits `CHKSBS Partial-Overlap` warnings for every such window.

---

## Final Topology Check

Before finishing intake, confirm that the implied topology is coherent:
1. every zone belongs to exactly one floor
2. every floor's zones close the footprint
3. vertical stacking uses accumulated `z_floor`, not repeated zero elevation
4. every window can be attached to a real exterior wall of a real zone
5. facade direction, wall direction, and coordinate span are mutually consistent
