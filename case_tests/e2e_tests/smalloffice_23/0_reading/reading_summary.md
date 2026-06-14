# Phase 1 summary — SmallOffice_TwoStep / smalloffice_23

All 5 drawings are clean CAD line-drawings (black background, gray wall poché, cyan
windows/doors, green dimension chains). No photoreal / hand-drawn ambiguity. Units mm → converted
to metres; dimension `text` kept verbatim in mm.

Building: 10000 × 20000 mm footprint, flat roof, single floor.
Total height 4500 mm (z 0–4.50). Confirmed from all four elevation height chains (4500 each side).

Drawing style matches smalloffice_21 conventions exactly.

---

## Per-image confidence

| image | strokes | windows | doors healed/noted | clutter excluded | confidence | reason |
|---|---|---|---|---|---|---|
| 1f_view | 23 (12 wall, 11 window) | 11 | ~7 healed (south wall, east wall, horizontal partitions ×3, vertical partitions ×2) | ~10-12 furniture items | medium | overall layout clear; interior partition y-positions (15.94, 13.00, 8.06) derived from outer dim chain 4060+2940+4940+8060=20000 but inner sub-chains have small discrepancies (~100-200 mm gaps); west wall window y-positions in plan estimated from cyan glazing marks only |
| South_view | 3 (1 wall_fill, 2 window) | 2 | 1 door noted (center, 900mm, z=0.20-2.60) | dim ticks | high | clean chain, symmetrical layout; two windows 2500mm and 2520mm on either side of center door |
| North_view | 2 (1 wall_fill, 1 window) | 1 | 1 door noted (double-leaf, 1600mm, z=0.20-2.60) | dim ticks | high | regular chain; 4800mm wide window and 1600mm double door clearly separated by 2520mm pier |
| East_view | 4 (1 wall_fill, 3 window) | 3 | 1 door noted (double-leaf, 1600mm, z=0.20-2.60) | dim ticks | high | clean 9-segment chain summing to 20000; three windows + one door clearly distinct; z-chains confirm sill/head |
| West_view | 6 (1 wall_fill, 5 window) | 5 | none | dim ticks | high | clean 11-segment chain summing to 20000; 4 smaller windows (1800mm tall) + 1 large window (4800 wide, 2400mm tall); two z-chains confirm different heights for small vs large window groups |

---

## Fields repeatedly null / unknown

- `strokes[*].geometry.thickness_m` = **null on every plan wall** (per guide §0.2 — EP surfaces carry
  no thickness). The "240" callouts are kept only in `ocr_texts`, never as geometry.
- **Plan window z** = absent/unknown on plan — z comes only from elevations (phase 2 join).
- `scale_origin.world_z_m` = null on plan; = 0.00 on all 4 elevations.
- `outline` pen = **never used**: flat-roof single-floor building; outline coincides with the wall_fill
  outer edges on all 4 elevations (logged in each elevation's uncaptured list, not traced).
- `facade_axis_note` = null on plan, filled on all 4 elevations.
- Interior partition y-positions: medium confidence (see plan note above).

---

## Four-facade x_local ↔ world-axis translation table

Origin convention: world (0,0,0) = SW outer corner of footprint at ground.
Plan x = world x (east), plan y = world y (north).
Elevations: local x = horizontal along facade, local y = world z.

| facade | local origin (world) | local x direction | formula: world from local | local y | facade x-span |
|---|---|---|---|---|---|
| South | (x=0,  y=0,  z=0) SW | world x, increasing eastward | **x_world = x_local** | world z | x 0..10 |
| North | (x=10, y=20, z=0) NE | -world x, increasing westward | **x_world = 10 − x_local** | world z | x 0..10 (world 10..0) |
| East  | (x=10, y=0,  z=0) SE | world y, increasing northward | **y_world = x_local** | world z | x 0..20 (world y 0..20) |
| West  | (x=0,  y=20, z=0) NW | -world y, increasing southward | **y_world = 20 − x_local** | world z | x 0..20 (world y 20..0) |

(All elevation y_local = world z directly; ground z=0.00, building top z=4.50.)

---

## Window z-bands by facade (for phase 2 plan ↔ elevation join)

All windows share sill z=1.00 unless noted:

| facade | window | sill z (m) | head z (m) | height (mm) | notes |
|---|---|---|---|---|---|
| South | west window (x=2.04-4.54) | 1.00 | 2.80 | 1800 | from left/right chains 1000+1800 |
| South | east window (x=5.44-7.96) | 1.00 | 2.80 | 1800 | same chain |
| North | large window (x=0.54-5.34) | 1.00 | 3.40 | 2400 | from left chain 1000+2400 |
| East  | large window (x=8.84-13.64) | 1.00 | 2.80 | 1800 | from right chain 1000+1800 |
| East  | window (x=14.38-15.58) | 1.00 | 2.80 | 1800 | same |
| East  | window (x=17.96-19.46) | 1.00 | 2.80 | 1800 | same |
| West  | windows 1-4 (x=0.54-11.58) | 1.00 | 2.80 | 1800 | from left chain 1000+1800 |
| West  | large window (x=14.66-19.46) | 1.00 | 3.40 | 2400 | from right chain 1000+2400 |

Note: north large window and west large window both have height=2400 (head z=3.40). South and east
windows and west win1-4 have height=1800 (head z=2.80).

---

## Door locations by facade

| facade | x_local range | door type | z range | notes |
|---|---|---|---|---|
| South | x=4.54-5.44 | single-leaf glazed + transom | z=0.20-2.60 (threshold 200mm) | healed on plan S1 |
| North | x=7.86-9.46 | double-leaf glazed + transom | z=0.20-2.60 (threshold 200mm) | healed on plan S3 |
| East  | x=5.70-7.30 | double-leaf glazed + transom | z=0.20-2.60 (threshold 200mm) | healed on plan S2 |
| West  | none visible | — | — | no door symbols on west elevation |

---

## Schema feedback (gaps / redundancy / missing enum values)

- **No gap blocking this case.** Plan `wall`/`window` and elevation `wall_fill`/`window` pen sets
  covered all geometry; everything else fit the recognize-and-log path.
- **Door transom windows:** The central door on the south facade and the double doors on north and
  east all appear to have a small transom light above the door leaf. Per discipline, the door
  assembly is not traced (no `door` pen; heal on plan side). The transom is logged in
  `uncaptured_visual_elements` but not traced separately, since its z-extent is ambiguous and it is
  physically part of the door frame assembly. If phase 2 needs daylight/opening z for the transom, a
  small `noted_openings[]` block would help.
- **`outline` redundant in all 4 elevations** (flat roof, coincident edges): the "only draw outline
  when it adds z that wall_fill+levels don't" rule worked cleanly — no false outline strokes.
- **Interior partition discrepancy:** The inner fine sub-chain values on the left side of the plan
  (1500+2380, 1200+1740, 1500+1220, 3080+4800) do not sum exactly to the outer coarse chain values
  (4060, 2940, 4940, 8060). Differences are ~80-180 mm, likely attributable to wall thicknesses
  (240mm walls) being counted partially in one chain but not the other, or annotation offset. The
  outer chain values (4060+2940+4940+8060=20000) are used as authoritative partition y-positions.
  The correction stage should cross-check partition y positions against the 8-zone zone list from
  testdata_prompt.json.
- **West wall large window axis:** The west elevation places the large 4800mm window at local
  x=14.66-19.46 (world y = 20−19.46 to 20−14.66 = y≈0.54-5.34, i.e. near the south end of the west
  wall). In the plan image the large cyan window on the west wall also appears in the northern
  portion of the plan (high y). There may be an axis convention question. The plan stroke S20 note
  flags this; the elevation JSON (West_view.json S6) is the authoritative source for x_local
  coordinates; phase 2 should use the elevation's dimension chain, not the plan's visual estimate.
- Minor: plan windows on perimeter walls are recorded as `line` strokes on the wall centerline
  (same coordinate as the wall). Visually they overlap — expected and correct per discipline.
