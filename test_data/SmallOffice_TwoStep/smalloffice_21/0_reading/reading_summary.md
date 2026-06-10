# Phase 1 summary — SmallOffice_TwoStep / smalloffice_21

All 6 drawings are clean CAD line-drawings (black background, gray wall poché, cyan
windows/doors, green dimension chains). No photoreal / hand-drawn ambiguity. Units mm -> converted
to metres; dimension `text` kept verbatim in mm.

Building: 15000 x 8000 mm footprint, flat roof. F1 = 3.000 m (z 0–3.0), F2 = 3.600 m (z 3.0–6.6),
total 6.600 m. Floor heights confirmed against all four elevation height chains (3000 + 3600 = 6600).

## Per-image confidence

| image | strokes | windows | doors healed/noted | clutter excluded | confidence | reason |
|---|---|---|---|---|---|---|
| 1f_view | 17 (10 wall, 7 window) | 7 | ~6 healed (3 entry, corridor + partition swings) | ~6 furniture groups | medium | layout clear; interior partition x and door-opening extents estimated from dim chains, ticks hard to pin exactly |
| 2f_view | 18 (10 wall, 8 window) | 8 | ~6 healed (corridor swings) | meeting tables + 4 office sets | medium | same as 1f; partition x estimated |
| South_view | 9 (2 wall_fill, 7 window) | 7 | 1 door noted (F1 far-left bay) | dim ticks | medium | F1 short window (S7) z-band and door bay split from the 900/600/1500 chain are the least certain |
| North_view | 7 (2 wall_fill, 5 window) | 5 | none | dim ticks | high | regular window grid, clean chains |
| East_view | 4 (2 wall_fill, 2 window) | 2 | none | dim ticks | high | single centered window per floor |
| West_view | 3 (2 wall_fill, 1 window) | 1 | 1 door noted (F1 glazed double door) | dim ticks | high | F1 element is clearly a door, not a window |

## Fields repeatedly null / unknown

- `strokes[*].geometry.thickness_m` = **null on every plan wall** (per guide §0.2 — EP surfaces carry
  no thickness). The "240" callout is kept only in `ocr_texts`, never as geometry.
- **Plan window z** = absent/unknown on both plans — z comes only from the elevations (phase 2 join).
- `scale_origin.world_z_m` = null on both plans; = 0.00 on all elevations.
- `outline` pen = **never used**: flat-roof building, outline coincides with the wall_fill outer
  edges everywhere, so it is redundant (logged in each elevation's uncaptured list, not traced).
- `facade_axis_note` = null on plans, filled on all 4 elevations.
- Interior partition x-positions on plans are best-estimates from the dimension chains.

## Four-facade x_local <-> world-axis translation table (phase 2 consumes this — signs matter)

Origin convention: world (0,0,0) = SW outer corner of footprint at ground. Plan x = world x (east),
plan y = world y (north). Elevations: local x = horizontal along facade, local y = world z.

| facade | local origin (world) | local x -> world | sign | local y -> world | facade x-span |
|---|---|---|---|---|---|
| South | (x=0,  y=0,  z=0) SW | world x | **+** x_world = x_local | world z | x 0..15 |
| North | (x=15, y=8,  z=0) NE | world x | **-** x_world = 15 - x_local | world z | x 0..15 (15..0 world) |
| East  | (x=15, y=0,  z=0) SE | world y | **+** y_world = x_local | world z | y 0..8 |
| West  | (x=0,  y=8,  z=0) NW | world y | **-** y_world = 8 - x_local | world z | y 8..0 |

(All elevation y_local = world z directly, ground z=0, top z=6.6, floor split z=3.0.)

## Window z-bands by floor (cross-elevation, for phase 2 plan<->elevation join)

- F2 windows: sill z = 4.00, head z = 5.80 (1000 floor-to-sill + 1800 height; consistent S/N/E/W).
- F1 windows (S, N): sill z = 1.00, head z = 2.60 (1000 + 1600).
- F1 windows (E): sill z = 1.00, head z = 2.80 (drawing shows 1800 height on east — noted as-drawn).
- F1 south short window (S7): z ~1.50–2.10 — low-confidence, derived from the 600 chain segment.

## Schema feedback (gaps / redundancy / missing enum values)

- **No gap blocking this case.** The plan `wall`/`window` and elevation `wall_fill`/`window`/`outline`
  pen sets covered everything geometric; everything else fit the recognize-and-log path.
- **Door on an elevation has no first-class home.** A door symbol appears on the South (F1 bay) and
  West (F1 glazed double door) elevations. The pen set correctly forbids tracing it, and the heal
  lives on the plan side — but there is no structured field to carry "elevation saw a door at this
  x-range, z 0..2.1" to phase 2; it currently survives only as free text in
  `uncaptured_visual_elements`. If phase 2 ever needs door z for daylight/opening checks, a small
  optional `noted_openings[]` (non-pen) block would close that gap. Not required for energy sim.
- **`outline` was redundant in all 4 elevations** (flat roof, coincident edges). The "only draw
  outline when it adds z that wall_fill+levels don't" rule worked cleanly — no false outline strokes.
- Minor: plan windows on a perimeter wall are recorded as `line` strokes lying exactly on the wall
  centerline (same coordinate as the wall). That is faithful tracing, but a reviewer rendering
  strokes may see window lines overlapping wall lines — expected, not an error.
