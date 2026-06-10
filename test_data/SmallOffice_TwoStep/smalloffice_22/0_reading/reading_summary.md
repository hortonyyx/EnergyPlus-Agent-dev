# Phase 1 Summary

## Confidence

| image | confidence | notes |
| --- | --- | --- |
| `1f_view.json` | high | All walls and all dimension-chain numbers are explicit and orthographic. No plan windows or doors are drawn. |
| `2f_view.json` | high | All walls and all dimension-chain numbers are explicit and orthographic. No plan windows or doors are drawn. |
| `3f_view.json` | high | All walls and all dimension-chain numbers are explicit and orthographic. No plan windows or doors are drawn. |
| `South_view.json` | medium | Window rectangles are clear, but the image has no printed height chain; local y was back-computed from the to-scale raster using the known 15.00 m facade width. |
| `North_view.json` | medium | Second-floor window x positions are dimensioned, but the image still has no printed height chain; local y was back-computed from the to-scale raster using the known 15.00 m facade width. |
| `East_view.json` | medium | Single window is clear, but the image has no printed height chain; local y was back-computed from the to-scale raster using the known 8.00 m facade width. |
| `West_view.json` | medium | Single window is clear, but the image has no printed height chain; local y was back-computed from the to-scale raster using the known 8.00 m facade width. |
| `supp_plan.json` | low | Supplemental image is axonometric only; it was logged as `image_kind=\"other\"` and not orthographically vectorized. |

## Repeated nulls / unknowns

- All plan `wall` strokes keep `thickness_m = null` by phase1 contract.
- None of the four facade renderings carries printed level markers or a vertical dimension chain.
- Facade local y values were therefore derived from image scale, not OCR:
  - South/North facade width = 15.00 m from the plans
  - East/West facade width = 8.00 m from the plans
  - Measured raster scale is consistent at about `86 px/m`, which yields a facade height of about `12.00 m`
  - The two visible storey divider lines land at about `z = 3.60 m` and `z = 7.20 m`
- No door symbols or plan window symbols are visible in `1f_view.png`, `2f_view.png`, or `3f_view.png`.

## Facade Local <-> World

These are the formulas phase2 should apply directly.

- South facade
  - `scale_origin = (world_x, world_y, world_z) = (0.00, 0.00, 0.00)`
  - `x_world = 0.00 + x_local`
  - `y_world = 0.00`
  - `z_world = y_local`

- North facade
  - `scale_origin = (world_x, world_y, world_z) = (15.00, 8.00, 0.00)`
  - `x_world = 15.00 - x_local`
  - `y_world = 8.00`
  - `z_world = y_local`

- East facade
  - `scale_origin = (world_x, world_y, world_z) = (15.00, 0.00, 0.00)`
  - `x_world = 15.00`
  - `y_world = 0.00 + x_local`
  - `z_world = y_local`

- West facade
  - `scale_origin = (world_x, world_y, world_z) = (0.00, 8.00, 0.00)`
  - `x_world = 0.00`
  - `y_world = 8.00 - x_local`
  - `z_world = y_local`

## Phase2-facing cautions

- Treat facade z values as image-derived geometry, not OCR-certified dimensions.
- `North_view.json` has the only explicit horizontal facade dimension chain; other facade window x ranges were proportionally read from the raster.
- `supp_plan.json` is corroborative only. It should not override any orthographic plan/elevation JSON.

## Schema feedback

- `image_kind=\"other\"` works for the axonometric supplement, but `self_check.all_visible_strokes_captured` becomes ambiguous when the whole image is intentionally out of scope.
- When an elevation is clearly to-scale but undimensioned, the schema has no dedicated field for “metric recovered from shared raster scale”; this had to go into notes / unknowns.
- Storey divider lines are semantically important for splitting `wall_fill`, but they currently have no structured home except free-text notes.
