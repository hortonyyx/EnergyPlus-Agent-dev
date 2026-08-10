# Phase 1 Summary — sm21_anchor (out_2 run)

## Per-image confidence and tally

| image | kind | walls | windows | confidence | main caveats |
|---|---|---|---|---|---|
| 1f_view | plan | 11 wall strokes | 6 window strokes | medium | top dim chain sums to 14760 not 15000; interior vertical wall x positions derived from dim chains; south-west zone vertical wall positions approximate; door positions estimated from swing arc visibility |
| 2f_view | plan | 12 wall strokes | 6 window strokes | medium-low | bottom dim chain center segments (360/560 area) have low-confidence reading; south-side vertical wall positions partially inferred from symmetry; north conference room divider x position derived from top dim chain |
| South_view | elevation | 2 wall_fill strokes | 7 window strokes (incl. small F1 window) | medium | F1 small window (S9) position and size LOW CONFIDENCE; left-side F1 dim chain (1500/600/900) interpretation ambiguous (door height vs sill); door in F1 recorded as window pen with flag |
| North_view | elevation | 2 wall_fill strokes | 5 window strokes | high | top and bottom dim chains both sum to 15000; F2 windows use top chain (1950+3600+3900+3600+1950); F1 windows use bottom chain (1240+2400+2660+2400+2660+2400+1240); consistent heights from both sides |
| East_view | elevation | 2 wall_fill strokes | 2 window strokes | high | simple symmetrical layout with 1 window per floor; both dim chains sum to 8000; height dims unambiguous |
| West_view | elevation | 2 wall_fill strokes | 2 strokes (1 window F2 + 1 door recorded as window F1) | medium | F1 door height NOT explicitly dimensioned; recorded as window pen with LOW CONFIDENCE; door position x same as F2 window (centered); top dim chain 3400+1200+3400=8000 |

---

## Fields repeatedly null or unknown

- `thickness_m` — null for all plan walls (per spec, EP uses no-thickness faces)
- `world_z_m` in `scale_origin` — null for all plan views (z comes from elevation)
- `facade_axis_note` — null for plan views, filled for all 4 elevation views
- `ocr_texts` — empty array for all 6 images (no readable room-name or annotation text found in any of the CAD drawings; dimension numbers are captured in `dimensions[]` instead)
- `scale_origin.world_y_m` — null for elevation views (irrelevant; y is world z for elevations)

---

## Four-facade x_local ↔ world-axis table (filled values)

| facade | local x=0 (world coords) | x_local increases toward | local x=max (world coords) |
|---|---|---|---|
| South | world x=0.00 (SW corner) | east (world x increases) | world x=15.00 (SE corner) |
| North | world x=15.00 (NE corner) | west (world x decreases) | world x=0.00 (NW corner) |
| East | world y=0.00 (SE corner) | north (world y increases) | world y=8.00 (NE corner) |
| West | world y=8.00 (NW corner) | south (world y decreases) | world y=0.00 (SW corner) |

Building coordinate system: origin = SW inner corner of footprint; x = east; y = north; z = up.

---

## Window z heights (authoritative from elevation dim chains)

| floor | facade | sill z (m) | head z (m) | window height (m) | source |
|---|---|---|---|---|---|
| F2 | South | 4.00 | 5.80 | 1.80 | right-side: 1000 sill + 1800 height |
| F2 | North | 4.00 | 5.80 | 1.80 | left-side: 1000 sill + 1800 height |
| F2 | East | 4.00 | 5.80 | 1.80 | left-side: 1000 sill + 1800 height |
| F2 | West | 4.00 | 5.80 | 1.80 | left-side: 1000 sill + 1800 height |
| F1 | South (large) | 1.00 | 2.60 | 1.60 | right-side: 1000 sill + 1600 height |
| F1 | North | 1.00 | 2.60 | 1.60 | left/right: 1000 sill + 1600 height |
| F1 | East | 1.00 | 2.80 | 1.80 | left-side: 1000 sill + 1800 height |
| F1 | West (door) | 0.00 | ~2.10 | ~2.10 | estimated; no explicit dim |
| F1 | South (small) | ~1.40 | ~2.00 | ~0.60 | LOW CONFIDENCE (visual estimate only) |

Note: F1 window heights differ between South/North (1600mm) and East (1800mm). This is as read from the dim chains and reflects genuine differences (East facade dims explicitly show 200|1800|1000 while South/North dims show 400|1600|1000 for F1).

---

## Schema feedback

**Where it falls short:**

1. **Door in elevation**: The pen library has no mechanism for an exterior door visible in elevation (West F1). The only options are wall_fill / window / outline. Recording a floor-height door as a `window` pen is misleading. A `door` pen or a `door_opening` geometry kind would be cleaner. The current workaround (record as window with a note) works but risks phase 2 treating it as a glazed window.

2. **Ambiguous "small window next to door" in South F1**: The 1660mm segment in the South bottom dim chain contains both the pier wall and a small window, but the segment is dimensioned as a single unit. The schema has no way to carry "I think there's a window inside this dim chain segment but I'm not sure where." A `confidence` field per stroke would help.

3. **Plan window y_range**: Plan windows are recorded with a thin strip at the wall edge (y≈0 to 0.20) as a 2D position holder. This is technically correct (phase 1 is not supposed to infer z), but the 2D strip is not a meaningful geometry — it's purely a marker. The schema could explicitly support `"geometry_kind": "wall_x_marker"` for plan windows to avoid the artificial thin rect.

4. **Dimension chain ambiguity at top of 1F**: The top dim chain (north wall of 1F plan) sums to 14760, not 15000. The schema has no way to flag "this chain is probably measuring inner-edge to inner-edge (excluding wall thickness)". A `measurement_reference` field (outer/inner/centerline) would help.

**Where it is redundant:**

- `scale_origin.world_y_m` for elevations is always null (irrelevant field); could be omitted from the elevation schema.
- `facade_axis_note` is required for elevation but the text is formulaic; a structured `{axis, direction, sign}` tuple would be more machine-readable than a freetext string.

**Pen enum values that are insufficient:**

- No `door_opening` pen for elevation views (see above).
- No `dimension_only` or `annotation` stroke kind (for things like the 240mm wall-thickness callout arrows in plan — currently logged in uncaptured, but they carry useful phase-2 data about wall thicknesses that is then thrown away).
