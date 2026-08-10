# Reading Summary — sm21_anchor

## Per-image confidence

| Image | Kind | Walls traced | Windows traced | Confidence | Notes |
|---|---|---|---|---|---|
| 1f_view.png | plan | 12 | 7 | medium-high | Internal vertical wall x-positions estimated from accumulated dimension chain; door heals logged; east corridor window position medium confidence |
| 2f_view.png | plan | 11 | 8 | medium | Bottom section has compressed dimension text "36560" likely two overlapping values; south section partition walls x-positions estimated; south-office-1 may have no window (unclear in image) |
| South_view.png | elevation | 2 (wall_fill) | 9 | high | F1 door on far left recognized/excluded; F2 window pairs position from top chain; F1 window positions from bottom chain; right-side inner y sub-dimensions partially inconsistent (1600+1000=2600 not 3000) |
| North_view.png | elevation | 2 (wall_fill) | 5 | high | F2 two landscape windows; F1 three landscape windows; clean dimension chains; minor uncertainty on F1 window sill bottom |
| East_view.png | elevation | 2 (wall_fill) | 2 | high | Symmetric: one window per floor, centered, portrait; left inner shows 200mm band at floor line |
| West_view.png | elevation | 2 (wall_fill) | 1 | high | F2 one portrait window; F1 has double-leaf entry door (excluded per pen library); cleanest image |

## Repeatedly-null fields

- `thickness_m`: always null for all plan wall strokes (as required — EP does not use wall thickness)
- `scale_origin.world_z_m`: null for plan images (as required)
- `facade_axis_note`: null for plan images, populated for all 4 elevations
- `ocr_texts`: no legible room name or text labels found in any image (CAD drawing has no room labels visible)
- `dimension_refs`: mostly empty for `seen` strokes; populated for `dimension_derived` where applicable

## Schema feedback

- The `wall_fill` per-floor convention (one per floor) worked cleanly for all 4 elevations; 2 floors → 2 wall_fill strokes each.
- Plan images have significant furniture density (desks, chairs, conference tables) requiring active exclusion logging.
- South view contains an elevation door (double-leaf) that the pen library excludes — this correctly produced no window stroke but required careful note.
- West view also has an elevation door (double-leaf entry) at F1 center.
- The `facade_axis_note` sign convention required careful attention: North = -world x, West = -world y.
- Bottom dimension chains in 2f_view have compressed "36560" rendering — two sub-segments (360+560) appear to overlap in the dimension chain text; both sub-values transcribed separately.
- Scale in all images appears to be approximately 1:100 based on 15m building = large drawing, but no explicit scale ratio label found in any image.
