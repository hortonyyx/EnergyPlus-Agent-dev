# sm21_anchor 0_reading summary

## Per-image confidence

| Image | Confidence | Notes |
|---|---|---|
| `1f_view` | medium | Plan geometry is clear, but the top chain does not close exactly to 15.00 m as printed and the west entry door / east-side window needed interpreted heals. |
| `2f_view` | medium | Plan geometry is clear, but the printed bottom chain is not a clean closure and the corridor-door heal positions are less certain than the walls. |
| `South_view` | high | Facade bands and window rectangles are straightforward; lower-left door is visible and logged as uncaptured. |
| `North_view` | high | Clear 2-window upper band and 3-window lower band; no door ambiguity. |
| `East_view` | high | Simple 8 m facade with one upper and one lower window. |
| `West_view` | high | Simple 8 m facade with one upper window and one lower door opening. |

## Repeated null / default fields

- `facade_axis_note` is `null` on both plan images by design.
- `scale_origin.world_z_m` is `null` on both plan images by design.
- `ocr_texts` is empty on all six images; the drawings only carry dimension text, which is stored in `dimensions[]`.
- `thickness_m` stays `null` on all plan wall strokes by schema rule.

## Schema friction

- The 1f and 2f plan dimension chains include printed values that do not perfectly sum to the full footprint span; I preserved the chain text as read instead of forcing closure.
- Elevation `outline` is stored separately from `wall_fill` even though the outer silhouette coincides with the facade body edges.
- Door openings on the plans were healed into continuous wall strokes and logged in `uncaptured_visual_elements`; facade doors on elevations were logged only, not traced.
