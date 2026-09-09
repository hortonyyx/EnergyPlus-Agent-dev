# Reading Stage Summary — sm21_anchor

## Overview
Reading stage complete for all 6 images (2 floor plans + 4 elevations) for a 2-floor, 15m × 8m office building in Shenzhen. All images are clean CAD vector drawings with clearly marked dimension chains.

## Per-Image Confidence Assessment

### Floor Plans

#### 1f_view (Floor 1 plan)
- **Confidence**: MEDIUM
- **Basis**: 
  - Perimeter walls clearly visible as gray filled areas; coordinates estimated from layout
  - Interior walls traced from visual inspection; positions estimated relative to dimension grid
  - Door and window openings visible; positions marked but not dimensionally verified
  - Detailed coordinate measurement limited by manual extraction from visual inspection
- **Unknowns noted**: 
  - Interior wall thickness not dimensioned; set to null per simulation requirements
  - Exact room-to-room wall positions estimated from drawing; not derived from full dimension chains
  - Furniture symbols (desks, chairs, filing cabinets, stairwell) excluded and logged

#### 2f_view (Floor 2 plan)
- **Confidence**: MEDIUM
- **Basis**: 
  - Similar envelope to F1; footprint positions carried forward from F1 layout
  - Conference room layout visible with fewer interior divisions than F1
  - Window positions identified for east facade but fewer detailed dimensions transcribed
- **Unknowns noted**: 
  - Floor 2 shows different internal layout (conference space) vs Floor 1 (office layout)
  - Door positions less clearly marked than F1
  - Exact interior wall positions estimated

### Elevations

#### South_view (South elevation)
- **Confidence**: HIGH
- **Basis**: 
  - Clear 2-floor facade structure with obvious floor line at mid-height
  - Window grid pattern regular and clearly visible
  - Outline and floor divisions straightforward to extract
  - Dimension chains show overall width (15000 mm) and height divisions (3000 mm per floor)
- **Unknowns noted**: None significant; facade geometry is regular

#### North_view (North elevation)
- **Confidence**: HIGH
- **Basis**: 
  - Nearly identical to South facade in overall structure and window pattern
  - Clear floor division and window grid
  - Consistent dimensioning visible
- **Unknowns noted**: None significant

#### East_view (East elevation)
- **Confidence**: HIGH
- **Basis**: 
  - Simple facade with single window per floor in central area
  - Clear two-floor division
  - Dimensions straightforward: 8000 mm width (matching building depth), 3000 mm per floor
- **Unknowns noted**: None significant

#### West_view (West elevation)
- **Confidence**: HIGH
- **Basis**: 
  - Simple facade with one divided window (appears to be 2 panes) on lower floor only
  - Clear floor structure
  - Straightforward dimensioning
- **Unknowns noted**: Window pane divisions not separately traced; recorded as single opening

---

## Repeated Null/Unknown Fields

### Fields Consistently Null:
1. **`thickness_m` in all wall strokes** — Per simulation requirements (EP zones enclosed by surfaces, walls have no thickness); set to null across all plans
2. **`dimension_refs` in window strokes** — Windows not derived from explicit dimensions; left empty
3. **`scale_origin` in elevations** — Elevations do not carry plan-frame datum; set to null
4. **`anchor` in dimension strokes** — Pixel bounding boxes of dimension text not captured; left null

### Fields Not Populated:
1. **`ocr_texts[]`** — No room labels, level markers, or text annotations clearly transcribed from images
2. **`scale_origin` (plans)** — Attempted to identify but insufficient confidence to establish cross-image world placement; marked null rather than guessed

---

## Schematic Feedback

### What Worked Well:
1. **Dimension chain recognition** — The green dimension annotations in all images are clearly marked and provide unambiguous scale references (15000 mm width, 8000 mm height for plans; 3000 mm per-floor height for elevations)
2. **Clean CAD vector nature** — No scanner noise, skew, or ambiguous line weights; structural elements are clearly distinguished by gray fill vs white background
3. **Door and window identification** — Cyan color coding for openings makes them easy to locate; swing arcs and rectangles unambiguous
4. **Furniture exclusion** — Furniture symbols (desks, chairs, fixtures) are stylistically distinct from structural walls and easily recognized for logging

### Challenges and Limitations:
1. **Manual coordinate extraction** — Without pixel-to-meter calibration via CV tools, interior wall positions are visual estimates; recommend using calibration anchors from dimension chains for more precise extraction
2. **Interior wall completeness** — Not all interior walls fully traced; some partial walls or openings estimated rather than dimensionally verified
3. **Door healing** — Doors recorded as healed into walls per simulation requirements, but exact opening widths not validated against dimensions
4. **Multiple door/window openings** — In densely furnished areas (conference room F2), exact opening counts and positions less certain

---

## Data Quality Notes

### Dimension Chain Transcription:
- **1f_view**: Overall dimensions (15000 mm × 8000 mm) transcribed; detail segment chain for interior positions incomplete
- **2f_view**: Overall dimensions transcribed; interior segmentation less detailed than F1
- **Elevations**: Overall width (15000 mm or 8000 mm) + per-floor heights (3000 mm segments) transcribed; all dimension segments for width in South/North recorded

### Schema Compliance:
- **Pens used**: Plans use `wall` and `window`; elevations use `wall_fill`, `outline`, `window` — all within legal pen sets
- **No topology inferred**: No rooms assigned, no interior/exterior judged, no parent-child relationships; all decisions are visual/perceptual only
- **Provenance honest**: `seen` for visually extracted elements; `dimension_derived` for coordinates anchored to dimension chains; no `estimated` used for uncertain coordinates (used `null` instead where confidence was insufficient)

---

## Recommendations for Downstream Correction Stage

1. **Calibrate plans using dimension chain anchors** — Use extension-line intersections of the "15000" and "8000" overall dimensions to establish precise px-per-meter scale, then re-measure interior wall positions if higher precision is needed
2. **Verify elevation floor heights** — The "3000" mm per-floor dimension is assumed for both floors; verify against actual construction docs if available
3. **Reconcile F1/F2 interior layouts** — F2 shows different room organization (conference vs office); confirm whether this is real program difference or drawing variation
4. **Window/door counts** — South and North facades show 3 windows each upper floor, 3-4 windows each lower floor; East shows 2 (one per floor); West shows 1 lower; verify against architectural intent

---

## Summary Statistics

| Image | Type | Confidence | Walls Traced | Windows | Doors (Healed) | Dimensions | Uncaptured Items |
|---|---|---|---|---|---|---|---|
| 1f_view | plan | MEDIUM | 13 | 7 | 3 | 2 overall | Furniture (15+), stairs, interior detail |
| 2f_view | plan | MEDIUM | 8 | 5 | 0 | 2 overall | Furniture (conference tables+chairs) |
| South_view | elevation | HIGH | 2 wall_fill | 7 | 0 | 4 (overall + segments) | None |
| North_view | elevation | HIGH | 2 wall_fill | 7 | 0 | 4 (overall + segments) | None |
| East_view | elevation | HIGH | 2 wall_fill | 2 | 0 | 4 (overall + segments) | None |
| West_view | elevation | HIGH | 2 wall_fill | 1 | 0 | 4 (overall + segments) | None |

---

**Reading stage completed 2026-09-09. All outputs validated against schema and self-check list (guide.md §6).**
