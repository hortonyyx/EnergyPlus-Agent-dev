# Zone Class Tool Usage Guide

## create_zone Tool Usage Guide

This tool has the following required parameters:
1. **name**: The name of the zone
2. **floor_vertices**: A list of floor vertices for the zone. The points in this list must be arranged in counterclockwise order on the xy-plane.
3. **x_origin**: The x-coordinate of the zone's base point
4. **y_origin**: The y-coordinate of the zone's base point
5. **z_origin**: The z-coordinate of the zone's base point
6. **ceiling_height**: The ceiling height of the zone

### floor_vertices Parameter Specification

**CRITICAL: floor_vertices must be ABSOLUTE WORLD COORDINATES, not relative coordinates!**

The `floor_vertices` parameter defines the actual position of each zone's floor in the building's world coordinate system. Each zone must have its own unique floor_vertices based on its actual location in the building.

**Unit**: all coordinates are in **meters** (to match the meter-based dimension chains defined in §D1 of `energyplus_mcp_prompt.md`). Do not pass millimetres.

**Example: Creating multiple zones in a building**

Consider a building with two adjacent zones on the same floor (z=0):
- Zone1: located at x=0 to x=5, y=0 to y=4
- Zone2: located at x=5 to x=10, y=0 to y=4

```json
// Zone1 floor_vertices (absolute world coordinates)
[
  {"X": 0.0, "Y": 0.0, "Z": 0.0},
  {"X": 5.0, "Y": 0.0, "Z": 0.0},
  {"X": 5.0, "Y": 4.0, "Z": 0.0},
  {"X": 0.0, "Y": 4.0, "Z": 0.0}
]

// Zone2 floor_vertices (absolute world coordinates) - NOTE: starts at x=5, not x=0!
[
  {"X": 5.0, "Y": 0.0, "Z": 0.0},
  {"X": 10.0, "Y": 0.0, "Z": 0.0},
  {"X": 10.0, "Y": 4.0, "Z": 0.0},
  {"X": 5.0, "Y": 4.0, "Z": 0.0}
]
```

**For zones on different floors:**
- Floor1 zones: Z coordinate = 0
- Floor2 zones: Z coordinate = floor_height (e.g., 3.0)
- Floor3 zones: Z coordinate = 2 * floor_height (e.g., 6.0)

```json
// Zone1 on Floor2 (z_origin = 3.0)
[
  {"X": 0.0, "Y": 0.0, "Z": 3.0},
  {"X": 5.0, "Y": 0.0, "Z": 3.0},
  {"X": 5.0, "Y": 4.0, "Z": 3.0},
  {"X": 0.0, "Y": 4.0, "Z": 3.0}
]
```

### Relationship between floor_vertices and x_origin/y_origin/z_origin

**IMPORTANT:** The `floor_vertices` and `x_origin/y_origin/z_origin` are INDEPENDENT parameters:

1. **floor_vertices**: Used to create the actual surface geometry (walls, floor, ceiling). These must be absolute world coordinates.

2. **x_origin/y_origin/z_origin**: Metadata for the Zone object in EnergyPlus. Typically set to a reference point of the zone (e.g., the centroid or one corner).

**Example:** For a zone spanning from (5, 10, 0) to (10, 14, 0):
- floor_vertices: `[{"X": 5, "Y": 10, "Z": 0}, {"X": 10, "Y": 10, "Z": 0}, {"X": 10, "Y": 14, "Z": 0}, {"X": 5, "Y": 14, "Z": 0}]`
- x_origin: 7.5 (centroid x)
- y_origin: 12 (centroid y)
- z_origin: 0

**DO NOT** add x_origin/y_origin/z_origin to floor_vertices - the vertices should already be in absolute coordinates!

### How to determine floor_vertices

You must determine each zone's bottom surface vertices based on:
1. The building floor plan diagrams in your generated claude_ep.md file
2. The zone coordinates table in claude_ep.md that shows each zone's position

For example, if claude_ep.md shows:
```
| Zone | x (m) | y (m) | Floor Vertices (CCW) |
|------|-------|-------|---------------------|
| Z1   | 1.25  | 2     | [(0,0), (2.5,0), (2.5,4), (0,4)] |
| Z2   | 3.75  | 2     | [(2.5,0), (5,0), (5,4), (2.5,4)] |
```

Then for Zone1 (on Floor1, z=0):
```json
[
  {"X": 0.0, "Y": 0.0, "Z": 0.0},
  {"X": 2.5, "Y": 0.0, "Z": 0.0},
  {"X": 2.5, "Y": 4.0, "Z": 0.0},
  {"X": 0.0, "Y": 4.0, "Z": 0.0}
]
```

And for Zone2 (on Floor1, z=0):
```json
[
  {"X": 2.5, "Y": 0.0, "Z": 0.0},
  {"X": 5.0, "Y": 0.0, "Z": 0.0},
  {"X": 5.0, "Y": 4.0, "Z": 0.0},
  {"X": 2.5, "Y": 4.0, "Z": 0.0}
]
```

Notice that Zone2's vertices start at (2.5, 0, 0), NOT (0, 0, 0)!

### ceiling_height Parameter

This parameter represents the height of the zone. It serves as a supplement to the floor_vertices parameter to generate all surface instances corresponding to the zone.

For CAD-style inputs (see §D4 of `energyplus_mcp_prompt.md`), `ceiling_height` equals the per-floor height read from the elevation view's left (vertical) dimension chain. All zones on the same floor share this value.

### Instances Generated After Using create_zone Tool

Using the create_zone tool will generate a zone instance along with all surface instances associated with that zone (including floor and ceiling). Therefore, as long as this zone tool is used correctly, there is no need to separately use create_surface class tools later. However, you still need to use the create_fenestration_surface tool separately to generate corresponding building window instances based on the building images provided by the user.

---

## ⭐ Dimension-to-Vertex Mapping (CAD-style Inputs)

When the input follows the CAD-style convention (meter units, 2-decimal dimension chains — see §D1–D6 of `energyplus_mcp_prompt.md`), use the following direct mapping recipe to go from the `Dimension Extraction` section in `claude_ep.md` to `create_zone` calls. No re-measurement from pixels is allowed.

### M1. Build zone boundary arrays

From the top-view segment chains, compute cumulative arrays:

```
xs = [0, x_seg_1, x_seg_1 + x_seg_2, …]   # length = N_cols + 1
ys = [0, y_seg_1, y_seg_1 + y_seg_2, …]   # length = N_rows + 1
```

Symbolic example: if the top view's x-chain reads `s1 | s2 | s3` and y-chain reads `t1 | t2`, then `xs = [0, s1, s1+s2, s1+s2+s3]` and `ys = [0, t1, t1+t2]`.

### M2. Emit one `create_zone` call per (row, column) cell that is a distinct room

For each floor `f` with FFL `z_f` (F1 → 0; F2 → floor_height; F3 → 2·floor_height; …):

```
for each room cell (i = col index, j = row index):
    x_min, x_max = xs[i], xs[i+1]
    y_min, y_max = ys[j], ys[j+1]
    floor_vertices = [
        {"X": x_min, "Y": y_min, "Z": z_f},
        {"X": x_max, "Y": y_min, "Z": z_f},   # CCW when viewed from above
        {"X": x_max, "Y": y_max, "Z": z_f},
        {"X": x_min, "Y": y_max, "Z": z_f},
    ]
    x_origin = (x_min + x_max) / 2
    y_origin = (y_min + y_max) / 2
    z_origin = z_f
    ceiling_height = floor_height   # from elevation view's left chain
```

### M3. Corridor spanning multiple column cells

When a row (or column) is a corridor that spans **all cells across that direction**, emit **one** `create_zone` call with:

```
x_min = xs[0], x_max = xs[-1]     # full building width
y_min = ys[j],  y_max = ys[j+1]
```

i.e. collapse the partitioning on that row (or column) so the corridor becomes a single zone.

### M4. Symbolic worked example (2×2 grid, F1)

Given `xs = [0, a, W]` and `ys = [0, b, D]` (so `W` and `D` are the total footprint width and depth), and floor height `H`:

| Call # | Zone name | floor_vertices (CCW, Z=0) | x_origin, y_origin, ceiling_height |
|---|---|---|---|
| 1 | Zone_F1_SW | (0,0,0), (a,0,0), (a,b,0), (0,b,0)       | a/2,   b/2,   H |
| 2 | Zone_F1_SE | (a,0,0), (W,0,0), (W,b,0), (a,b,0)       | (a+W)/2, b/2, H |
| 3 | Zone_F1_NW | (0,b,0), (a,b,0), (a,D,0), (0,D,0)       | a/2,   (b+D)/2, H |
| 4 | Zone_F1_NE | (a,b,0), (W,b,0), (W,D,0), (a,D,0)       | (a+W)/2, (b+D)/2, H |

Upper floors mirror these with `Z = (f-1)·H` and `z_origin = (f-1)·H`; everything else identical. Adapt the row/column count to whatever the actual dimension chain in `claude_ep.md` encodes — do NOT hardcode a specific grid shape.

### M5. Self-check before committing

1. **CCW check**: the signed area of `floor_vertices` must be positive:
   ```
   area_signed = 0.5 * sum_i ( x_i * y_{i+1} - x_{i+1} * y_i )   # cyclic
   ```
   Positive → CCW (correct). Negative → CW (wrong, reverse the list).
2. **No gap / overlap**: the union of all zone rectangles on a floor must equal the full footprint `[0, xs[-1]] × [0, ys[-1]]` with zero overlap.
3. **Area sum**: sum of per-zone areas equals `xs[-1] * ys[-1]`.
4. **Ceiling height consistency**: every zone on the same floor must have the same `ceiling_height`.

### M6. Window vertices (for `create_fenestration_surface`)

For a south-facade window at `x ∈ [x_win_min, x_win_max]`, `z ∈ [z_sill, z_head]`, the vertices (CCW **when viewed from outside**, i.e. from y < 0 looking north) are:

```
[
  {"X": x_win_min, "Y": 0.0, "Z": z_sill},
  {"X": x_win_max, "Y": 0.0, "Z": z_sill},
  {"X": x_win_max, "Y": 0.0, "Z": z_head},
  {"X": x_win_min, "Y": 0.0, "Z": z_head}
]
```

For a north-facade (y = y_max) window, swap the first two and last two to keep CCW-from-outside (observer at y > y_max). The east (x = x_max) and west (x = 0) facades follow the same principle, with the observer placed outside the footprint on the corresponding axis.

**CCW-from-outside vertex templates for all four facades** (window spans axis-range `[a_min, a_max]` at `z ∈ [z_sill, z_head]`):

| Facade | Plane | Vertex 1 | Vertex 2 | Vertex 3 | Vertex 4 |
|---|---|---|---|---|---|
| South | `y = 0`      | `(a_min, 0,     z_sill)`     | `(a_max, 0,     z_sill)`     | `(a_max, 0,     z_head)`     | `(a_min, 0,     z_head)`     |
| North | `y = y_max`  | `(a_max, y_max, z_sill)`     | `(a_min, y_max, z_sill)`     | `(a_min, y_max, z_head)`     | `(a_max, y_max, z_head)`     |
| East  | `x = x_max`  | `(x_max, a_max, z_sill)`     | `(x_max, a_min, z_sill)`     | `(x_max, a_min, z_head)`     | `(x_max, a_max, z_head)`     |
| West  | `x = 0`      | `(0,     a_min, z_sill)`     | `(0,     a_max, z_sill)`     | `(0,     a_max, z_head)`     | `(0,     a_min, z_head)`     |

For South / North facades, `a_*` are x-coordinates; for East / West facades, `a_*` are y-coordinates.

Only emit `create_fenestration_surface` calls for facades that actually carry windows. Facades marked blank in the Fenestration Table (either because their elevation image has no blue rectangles, or because no elevation image was provided for that direction) must have no window entities.

### M7. Wall-index → Facade mapping (critical for `building_surface_name`)

`create_zone` automatically generates walls named `{zone_name}_Wall_1 … _Wall_N`, where N = number of floor vertices. Each wall is built from consecutive floor-vertex pairs `(v_i → v_{i+1})`. **For the standard rectangular room whose `floor_vertices` are ordered CCW as `[SW, SE, NE, NW]`** (the ordering produced by §M2), the resulting four walls map to compass directions as follows:

| Wall name | Built from vertices | Faces | Parent plane |
|---|---|---|---|
| `{zone}_Wall_1` | SW → SE | **South** | `y = y_min` of the zone |
| `{zone}_Wall_2` | SE → NE | **East**  | `x = x_max` of the zone |
| `{zone}_Wall_3` | NE → NW | **North** | `y = y_max` of the zone |
| `{zone}_Wall_4` | NW → SW | **West**  | `x = x_min` of the zone |

**Use this mapping directly** when filling `building_surface_name` in `create_fenestration_surface` — do NOT call `list_surfaces` and manually compare vertex coordinates each time. Examples:

- South-facing window in `Zone_F1_SW` → `building_surface_name = "Zone_F1_SW_Wall_1"`.
- North-facing window in `Zone_F2_NE` → `building_surface_name = "Zone_F2_NE_Wall_3"`.
- East-facing window in `Zone_F1_NE` → `building_surface_name = "Zone_F1_NE_Wall_2"`.
- West-facing window in `Zone_F2_NW` → `building_surface_name = "Zone_F2_NW_Wall_4"`.

**Only exterior walls get windows.** A wall between two zones (e.g. `Zone_F1_SW_Wall_2` if SE zone is adjacent) is an interior partition and must never host a `FenestrationSurface:Detailed`. Check the Zone Coordinates Table to see which sides of a zone are on the footprint boundary (exterior) vs. shared with another zone (interior).

If a zone's floor polygon is non-rectangular or its vertices are ordered differently from `[SW, SE, NE, NW]`, the mapping shifts: Wall_i always corresponds to the edge `v_i → v_{i+1}` in CCW order. Re-derive per zone in that case and record the mapping in `claude_ep.md` beside the Zone Coordinates Table.
