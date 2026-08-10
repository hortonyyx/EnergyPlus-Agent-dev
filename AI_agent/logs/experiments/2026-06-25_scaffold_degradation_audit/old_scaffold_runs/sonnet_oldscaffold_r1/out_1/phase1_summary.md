# Phase 1 Summary — sm21_anchor

## Per-image confidence self-assessment

| Image | Confidence | Reason |
|---|---|---|
| 1f_view.json | Medium | Wall positions for internal dividers estimated from dim-chain cumulative sums + visual symmetry; east window position approximate; corridor notch at west (S11) uncertain |
| 2f_view.json | Medium | South cubicle divider x-positions (~3.75, 7.50, 11.25) estimated from 4-unit symmetric layout + bottom dim chain; north meeting-room divider at x≈7.44–7.50; 360+560 dim-chain segments may indicate wall+reveal rather than pure void |
| South_view.json | High | Dim chains (top + bottom) clearly readable; F2 window positions unambiguous; F1 window positions from bottom chain straightforward; floor divider at y=3.00 clearly drawn; only uncertainty = left-side F1 inner chain (900+600+1500) vs right-side (1000+1600+400) — left likely references door element |
| North_view.json | High | Clear dim chains both top and bottom; F2 windows (2 large landscape) and F1 windows (3 landscape) clearly visible and dimensioned; height dims consistent with other views |
| East_view.json | Medium-high | Clear window positions; F1 east window has unusual 200mm clearance between window top and floor-divider — faithfully recorded; only 1 window per floor, clearly at center |
| West_view.json | Medium-high | Clear F2 window; F1 element clearly a double-door (not a window); no F1 inner sub-dims visible on West elevation; door recorded in uncaptured_visual_elements |

## Repeatedly null / unknown fields

- `thickness_m`: always null on all plan walls (by spec)
- `scale_origin.world_z_m`: null on all plan images (by spec)
- Plan `ocr_texts`: no room-name text labels were visible in the plan images (or text was too small to read from the image); left as empty array
- Elevation `ocr_texts`: no numeric level markers (±0.000 triangle symbols) were visible; heights derived from dimension chains only

## Four-facade x_local ↔ world-axis table

| Facade | facade_axis_note | x_local=0 in world | x_local=15 (or 8) in world |
|---|---|---|---|
| South | local x = world x (eastward) | world x=0 (SW corner) | world x=15.00 (SE corner) |
| North | local x = -world x (westward) | world x=15.00 (NE corner) | world x=0 (NW corner) |
| East | local x = world y (northward) | world y=0 (SE corner) | world y=8.00 (NE corner) |
| West | local x = -world y (southward) | world y=8.00 (NW corner) | world y=0 (SW corner) |

Window x-coordinates in each elevation JSON use **local** coordinates; phase 2 applies the axis mapping to get world x/y.

## Schema feedback

### Where the schema works well
- `wall` / `window` pen distinction for plans is clean and sufficient
- `wall_fill` per-floor convention for elevations is exactly right — one rect per floor cleanly separates F1 and F2
- `dimensions[]` as a separate array (not embedded in strokes) allows dim chains to be read independently of geometry
- `facade_axis_note` + `scale_origin` together give phase 2 everything needed to convert local→world coordinates
- `uncaptured_visual_elements` requirement caught real edge cases (west door, south elevation door symbol)

### Where the schema falls short
- **Elevation door handling**: the pen library has no door pen for elevations. The West F1 double-door and South F1 entrance door are real opening elements visible on the elevation — currently recorded under `window` pen (South) or only in `uncaptured_visual_elements` (West) with notes. A dedicated `door_opening` notation in `uncaptured_visual_elements` with x/y geometry would be more useful than recording zero geometry. Suggestion: allow a non-pen geometry record for door openings in elevation (similar to how plan doors trigger wall-healing with a position note).
- **Plan windows are 1D** (a line segment), not 2D rects — this is correct physically (plan windows have no z), but it means plan and elevation window records have different geometry kinds (`line` vs `rect`). Phase 2 must join them across views to get the full 3D window. This is by design but worth documenting explicitly.
- **Interior dimension labels** (the "240" offset labels inside rooms): the current schema has no clean way to record these — they do not have two endpoints spanning a feature in the usual dimension-chain sense; they are more like "note callouts pointing at a wall edge." Recorded them in `dimensions[]` with approximate endpoints and a note; a dedicated `note_callout` field would be cleaner.
- **Corridor/lobby** spaces: the 1F corridor between y=3.00 and y=5.00 is a distinct thermal zone, but phase 1 only traces wall strokes — the corridor emerges from the topology of the walls, not from any explicit drawn element. This is correct, but it means phase 2 must reliably infer the corridor as a zone from two parallel horizontal walls + the absence of internal divisions. No schema change needed, but noted.
- **Mixed dim chain roles**: the top dim chain on South view locates F2 windows; the bottom chain locates F1 windows and the door. These reference different elements but use the same `dimensions[]` array format. Phase 2 must infer which dim chain refers to which floor level. Adding a `floor_level` hint field to dimension entries would ease this.
