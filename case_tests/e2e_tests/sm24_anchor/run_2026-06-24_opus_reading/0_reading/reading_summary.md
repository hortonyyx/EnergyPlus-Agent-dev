# sm24_anchor — 0_reading summary (opus, 2026-06-24)

Single-floor office, Shenzhen, ~200 m². Outer footprint **10.00 m (E-W) × 20.00 m (N-S)**
(10000 / 20000 mm overall chains). Walls 240 mm (annotated, not applied to strokes). The footprint
outline is rectangular, but the **interior corridor is non-rectangular (T/L-shaped)** — the point of
this case.

## Per-image stroke counts + confidence

| image | kind | wall / wall_fill | window | confidence |
|---|---|---|---|---|
| 1f_view | plan | 13 wall strokes | (windows recorded via elevations; plan cyan cross-checked) | high (S1–S12); **medium on S13** L-step coordinates |
| South_view | elevation | 1 wall_fill | 2 windows | high |
| North_view | elevation | 1 wall_fill | 1 window (4800) | high |
| East_view | elevation | 1 wall_fill | 3 windows (1×4800 + 1200 + 1500) | high |
| West_view | elevation | 1 wall_fill | 5 windows (4×1800-tall + 1×4800/2400-tall) | high |

Total elevation windows = 2 (S) + 1 (N) + 3 (E) + 5 (W) = **11 windows**. Doors (healed / not traced):
N double-door 1600, S double-door 900, E double-door 1600 = 3 exterior doors + several interior swing doors.

## Layout read (topology is the correction stage's job — recorded here only as context)

8 thermal zones expected. As traced, the wall network implies:
- **North reception room** — full width, y 16.10–20.00 (L-sofa). Corridor mouth + double door at its south edge.
- **Left column** (x 0–4.10): upper-left office (y 13.00–16.10), middle-left office (y 8.10–13.00),
  bottom-left conference room (y 0–8.10, oval table).
- **Right column** (x 5.90–10.00): small north-right room (y 15.05–16.10, credenza), middle-right
  office (y 8.10–15.05, two 4-seat tables), bottom-right office (y 0–4.95, stepped west wall).
- **Corridor** (8th zone): N–S spine x 4.10–5.90 between the columns, then an **L-step at y≈4.95**
  (S13) where it turns east toward the bottom-right office door and widens toward the south entrance.
  This is the non-rectangular boundary.

## Honesty / discipline notes (this run probes a suspected over-segmentation issue)

- **No dimension chain / tick / extension line was emitted as a wall.** Every wall stroke is a DRAWN
  line confirmed in the plan raster; dimensions live in `dimensions[]` only. The 240 mm thickness
  annotation is in `dimensions[]`, never a stroke.
- Walls are traced as **one stroke per continuous wall** (perimeter = 4 healed strokes, not segmented
  at door/window openings). The plan was NOT over-segmented despite heavy furniture.
- **Doors healed**, not traced; the corridor mouth (open span at y=16.10) was deliberately left as a
  gap (not welded) per the doorless-open-span guardrail.
- All furniture (sofa, desks, conference table, credenza, monitors, chairs) recognized and logged in
  `uncaptured_visual_elements`, never traced.

## Repeatedly-null fields
- `ocr_texts`: empty on every image (the drawing prints no room names / labels, only dimensions).
- plan `thickness_m`: null everywhere (per simulation; 240 mm kept only as a dimension).
- plan `scale_origin.world_z_m`: null.

## Lowest-confidence items (flag for judge / eyeball)
1. **S13 L-step coordinates** (corridor turn + bottom-right office door x) — derived from pixels, medium confidence.
2. Exact corridor-mouth width at y=16.10 (S7/S8 gap) — approximate.
3. Elevation↔plan window x-positions reconciled across the facade-axis sign flips (N and W run opposite world axes) — sign deferred to correction as designed.

## Schema feedback
The optional `provenance` / `confidence` / `dimension_refs` fields were natural to fill and did NOT
push me toward over-segmentation; I used `dimension_derived` only for perimeter strokes whose extent
comes straight from the overall chains, and `seen` for the interior walls I traced directly off the
raster. No pressure to instantiate walls I did not see drawn.
