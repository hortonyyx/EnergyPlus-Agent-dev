# Reading Summary — sm20_anchor

## §1 Per-image confidence self-assessment

| Image | Kind | Confidence | Reason |
|---|---|---|---|
| 1f_view.png | plan | **high** | Clean CAD drawing; clear dimension chains; all wall strokes unambiguous; no furniture, doors, or clutter |
| 2f_view.png | plan | **high** | Clean CAD; top zone has 4 columns at 3.75m (chain confirmed); bottom has 3 columns at 5.00m; no ambiguity |
| 3f_view.png | plan | **high** | Clean CAD; simplest layout; top north zone has no interior walls; 1 interior wall at x=7.50 in south zone |
| South_view.png | elevation | **high** | Clear gray wall fills; 6 blue windows (3×F1, 3×F2) with explicit dimension chains; F3 has no windows; all chains sum correctly |
| North_view.png | elevation | **high** | Clear; 3 floors; F1=3 windows, F2=4 windows, F3=1 large strip window; all horizontal chains verified to sum to 15.00 |
| East_view.png | elevation | **high** | Simple; 3 floor fills; 1 window on F3 only; chains verified (3.50+1.00+3.50=8.00; 1.40+2.40+1.00=4.80) |
| West_view.png | elevation | **high** | Visually identical to East — same dimensions, same single F3 window; high confidence by comparison |

**supp_plan.png**: This is a 3D perspective render of the building. It was examined for context (confirms 3-story rectangular massing with windows on south/north/east/west) but **no supp_plan.json was emitted** — the image is non-orthographic and cannot be read as plan or elevation per guide.md rules.

---

## §2 Fields repeatedly null / unknown

- `strokes[*].geometry.thickness_m` — null throughout all plan files (guide.md §0.2: EP walls have no thickness)
- `scale_origin.world_z_m` — null throughout all plan files (z comes from elevation dimension chains)
- `facade_axis_note` — null in all plan files (only required for elevations)
- `ocr_texts` — empty in all 7 images; no text labels, room names, or drawing titles were present in any drawing
- No level markers (▽ symbols) were present; z values were read entirely from dimension chains

---

## §3 Four-facade local-x ↔ world-axis table and translation formulas

### Established footprint from plans
- Building footprint: **15.00 m (east–west, world x) × 8.00 m (north–south, world y)**
- SW inner corner of footprint = world origin (0, 0, 0)

### Floor z-stack (from elevation dimension chains, all four elevations agree)
| Floor | z_floor (m) | z_top (m) | height (m) |
|---|---|---|---|
| F1 | 0.00 | 3.60 | 3.60 |
| F2 | 3.60 | 7.20 | 3.60 |
| F3 | 7.20 | 12.00 | 4.80 |

### Facade local-x ↔ world-axis mapping

| Facade | scale_origin (world) | local x maps to | facade_axis_note |
|---|---|---|---|
| South | (0.00, 0.00, 0.00) | world x, increasing eastward | `South facade: local x = world x (increasing eastward); local y = world z` |
| North | (15.00, 8.00, 0.00) | −world x, increasing westward | `North facade: local x = -world x (local x increasing = world westward); local y = world z` |
| East | (15.00, 0.00, 0.00) | world y, increasing northward | `East facade: local x = world y (increasing northward); local y = world z` |
| West | (0.00, 8.00, 0.00) | −world y, increasing southward | `West facade: local x = -world y (local x increasing = world southward); local y = world z` |

### Per-facade world-coordinate translation formulas

These formulas convert a local (x_local, y_local) coordinate from an elevation JSON into world (X, Y, Z):

**South facade** (`scale_origin` = world (0, 0, 0)):
```
X_world = 0.00 + x_local          [= x_local, eastward]
Y_world = 0.00                     [fixed: south face at y=0]
Z_world = 0.00 + y_local          [= y_local, upward]
```

**North facade** (`scale_origin` = world (15, 8, 0)):
```
X_world = 15.00 - x_local         [local x increases westward = world x decreases]
Y_world = 8.00                     [fixed: north face at y=8]
Z_world = 0.00 + y_local          [= y_local, upward]
```

**East facade** (`scale_origin` = world (15, 0, 0)):
```
X_world = 15.00                    [fixed: east face at x=15]
Y_world = 0.00 + x_local          [local x increases northward = world y increases]
Z_world = 0.00 + y_local          [= y_local, upward]
```

**West facade** (`scale_origin` = world (0, 8, 0)):
```
X_world = 0.00                     [fixed: west face at x=0]
Y_world = 8.00 - x_local          [local x increases southward = world y decreases]
Z_world = 0.00 + y_local          [= y_local, upward]
```

### Window world-coordinate cross-check (spot checks)

**South F1 window 1** (S4 in South_view.json):
- local x∈[1.40, 3.80], local y∈[1.00, 2.80]
- World: X∈[1.40, 3.80], Y=0.00, Z∈[1.00, 2.80] ✓

**North F3 large window** (S11 in North_view.json):
- local x∈[1.40, 13.60], local y∈[8.40, 11.00]
- World: X∈[15.00−13.60, 15.00−1.40] = [1.40, 13.60], Y=8.00, Z∈[8.40, 11.00] ✓

**East F3 window** (S4 in East_view.json):
- local x∈[3.50, 4.50], local y∈[8.60, 11.00]
- World: X=15.00, Y∈[3.50, 4.50], Z∈[8.60, 11.00] ✓

**West F3 window** (S4 in West_view.json):
- local x∈[3.50, 4.50], local y∈[8.60, 11.00]
- World: X=0.00, Y∈[8.00−4.50, 8.00−3.50] = [3.50, 4.50], Z∈[8.60, 11.00] ✓
- East and West F3 windows are symmetric about the building centerline (y=4.00): [3.50,4.50] ✓

---

## §4 Schema feedback

**Where the schema works well:**
- The `wall` / `wall_fill` / `window` / `outline` split cleanly covers this building — no ambiguous elements required `outline` pen (the storey lines are embedded in wall_fill boundaries, not separate strokes)
- The `dimensions[]` array with verbatim text + from/to + axis is sufficient to reconstruct all z-bands and x/y positions
- The per-floor `wall_fill` rule (pen_library §3) is unambiguous for this building's regular 3-floor stack

**Where it is slightly redundant:**
- Duplicate dimension chains (top+bottom on plans, left+right on elevations) produce many near-identical dimension entries; a "duplicate_of" flag would reduce noise, but verbatim capture is correct per the error budget
- The `from`/`to` coordinates on dimension entries within elevation JSONs use a placeholder `y=0.00` on both ends (the actual y/z value is in the text) — the schema would benefit from a clearer elevation-dimension convention distinguishing x-axis and z-axis dimension endpoint coordinates

**Pen-enum gaps observed:**
- No gaps encountered for this building — it has no balconies, cornices, railings, or structural columns that would stress the ignore-set
- No `outline` pen was needed — all facades have explicit wall_fill rects and the outline adds nothing beyond their edges

**supp_plan.png decision (as noted in §1):**
- The supplementary image is a 3D perspective/axonometric render, not an orthographic plan or elevation. Per guide.md and reading_guide.md, only orthographic views are in scope. No `supp_plan.json` was emitted. The render was used for context only (confirms massing, window placement on south and north faces visible, single small windows on east/west faces visible).
