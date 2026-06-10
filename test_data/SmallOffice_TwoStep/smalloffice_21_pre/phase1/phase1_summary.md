# Phase 1 Summary — smalloffice_21_pre

Generated: 2026-06-09

---

## Per-image confidence

| Image | Confidence | Primary reasons |
|---|---|---|
| `1f_view.json` | **high** | Clear CAD drawing; dim chains fully readable; same layout as sm21 reference provides cross-check; wall/window/door strokes unambiguous; door swing arcs clearly visible for healing decisions |
| `2f_view.json` | **med** | Clear drawing; top dim chain sum = 14880 (120mm short of 15000 — likely small text rounding); bottom double-pier "360\|360" vs "360\|560" reading uncertain; interior bottom-zone partition x positions estimated from equal-office assumption + chain; no ambiguity in perimeter or top windows |
| `South_view.json` | **med** | Facade and windows clearly visible; two height sub-chains (left vs right) give slightly different z readings for F1 windows (left: small window at sill=0.6m, height=0.9m; right: large windows at sill=1.0m, height=1.6m); entry door (SW, x=[0.54,1.44]) not dimensioned in bottom chain — recognized and excluded correctly |
| `North_view.json` | **high** | Clear chains; F2 has two large windows per top chain; F1 has three windows per bottom chain; height sub-chains consistent with south F1 large windows; right height chain shows only overall totals (no F2 sub-divisions) |
| `East_view.json` | **high** | Two windows (one per floor), both centered; top chain 3400\|1200\|3400 unambiguous; F1 sub-chain 200\|1800\|1000 gives slightly taller F1 window than south (1800mm vs 1600mm) — faithfully traced; consistent with plan east corridor window |
| `West_view.json` | **high** | Single F2 window and F1 entry double door clearly visible; door correctly excluded; F2 height chain 1000\|1800\|800 consistent with other facades; F1 has no height sub-chain (door zone, no window to dimension) |

---

## Repeatedly-null fields

| Field | Images affected | Reason |
|---|---|---|
| `strokes[*].geometry.thickness_m` | All plan images (1f, 2f) | Phase 1 rule: plan walls always null; EP surfaces have no thickness |
| `scale_origin.world_z_m` | 1f_view, 2f_view | Plan images: world_z comes from elevation dim chains; always null on plan |
| `facade_axis_note` | 1f_view, 2f_view | Plans: no facade axis; only used for elevations |
| `ocr_texts` | South_view, North_view, East_view, West_view | No visible text labels or room names in elevation images; arrays left empty |

---

## Four-facade x_local ↔ world-axis table

| Facade | Image local origin (world coords) | facade_axis_note | local x → world axis | local x = 0 maps to |
|---|---|---|---|---|
| South | world (0, 0, 0) = SW corner at ground | `local x = world x (increasing eastward)` | world x | West end (world x=0) |
| North | world (15, 8, 0) = NE corner at ground | `local x = -world x (local x increasing = world westward)` | -world x | East end (world x=15) |
| East  | world (15, 0, 0) = SE corner at ground | `local x = world y (increasing northward)` | world y | South end (world y=0) |
| West  | world (0, 8, 0) = NW corner at ground | `local x = -world y (local x increasing = world southward)` | -world y | North end (world y=8) |

**Cross-check**: All four facades agree on floor heights: F1=3000mm (y=0→3.0), F2=3600mm (y=3.0→6.6), total 6600mm. All agree on building width/depth: 15000×8000mm.

---

## Strokes I was unsure about

1. **1f_view bottom-left south window width**: Plan bottom chain shows 1200mm (vs 2400mm for all north windows and the other two south windows). This asymmetry is faithfully traced — the bottom-left office has a narrower south window per the dim chain. Confidence: **med** (the "1200" reading is clear but the asymmetry is unusual).

2. **2f_view bottom dim chain "360|360" or "360|560"**: The two small numbers between the 1200mm window spans read ambiguously. Committed to "360|360" (symmetric pier pattern) as it gives 2×7500=15000mm exactly. If wrong, the pier widths are off but window positions are approximately correct.

3. **South_view left-side F1 height chain**: The left chain shows "600|900|1500" (bottom-up) giving a small window at y=[0.6,1.5], while the right chain shows "1000|1600|400" (bottom-up) for the larger windows y=[1.0,2.6]. The two chains describe DIFFERENT windows (left describes the small 1200mm-wide window at x≈3.44-4.64; right describes the two 2400mm windows at x≈6.3-8.7 and 11.36-13.76). Confidence: **med** — the 600mm sill for the small window is lower than typical but visually the small window appears lower in the wall than the larger ones.

4. **2f_view top dim chain sum ≠ 15000**: Top chain reads 1950+3600+1889+1891+3600+1950=14880mm. Transcribed verbatim; likely rounding in annotation. Endpoints forced to match building total.

5. **East_view F1 window height**: Left chain reads 200|1800|1000 (spandrel|window|sill), giving y=[1.0,2.8] — 1800mm tall vs 1600mm for south/north F1 large windows. Faithfully traced; may indicate a taller east window, or may be a 200mm reading that's actually closer to 400mm (which would give [1.0,2.6] matching south/north). Noted in unknowns.

6. **West_view F1 double door**: Correctly identified as an entry double door (two panels visible, center meeting stile). Position centered at local x=[3.40,4.60] consistent with building corridor midpoint (world y≈[3.40,4.60]). Door excluded from strokes per phase 1 rules.

---

## Healed doors summary

| Image | Healed door location | Evidence |
|---|---|---|
| 1f_view S1 | South wall x≈[0.54,1.44] | Swing arc visible in plan at SW entrance (900mm door per dim chain) |
| 1f_view S4 | West wall y≈[5.0,5.5] | Swing arc visible, upper entry door |
| 1f_view S4 | West wall y≈[2.6,3.5] | Swing arc visible, lower entry door |
| 1f_view S5 | North corridor partition, three openings into top offices | Three swing arcs visible |
| 1f_view S6 | South corridor partition, three openings into bottom offices | Three swing arcs visible |
| 1f_view S9 | Bottom-left/middle vertical partition | One swing arc at ~y1.0-1.9 |
| 2f_view S5 | North corridor partition, two openings into conference rooms | Two swing arcs |
| 2f_view S6 | South corridor partition, four openings into bottom offices | Four swing arcs |

---

## Schema feedback

- The guide §4 specifies `axis` values for dimensions as `x | y | z`; elevation dimension chains along the vertical (z) axis were recorded with `"axis": "z"` per the spec.
- No `outline` pen was needed in any elevation (wall_fill edges define the silhouette; no separate outline stroke drawn).
- No `other` pen used anywhere; all non-keep elements logged in `uncaptured_visual_elements`.
- Scale: all coordinates in meters (two decimals); dimension chain `text` values transcribed verbatim in millimeters as written in the drawings.
