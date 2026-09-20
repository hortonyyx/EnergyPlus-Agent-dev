# Second Rework — Calibration Correction Complete

## Critical Fix: Coordinate Transformation Error

**Previous Error**: Origin reported as y=1595 px, which exceeds image height (1111 px). Root cause: measured crop-local coordinates without transforming back to source image using crop transform metadata.

**Fix Applied**: 
- Loaded crop_zoom metadata JSON to extract crop bbox and scale
- Applied proper inverse transformation: `source_x = bbox_x0 + crop_local_x / scale`
- Verified all coordinates fall within [0, 790] × [0, 1111] px image bounds

## Corrected Calibration

| Property | Value | Evidence |
|----------|-------|----------|
| **Origin (SW corner)** | (246.0, 879.5) px | Tick endpoints from cropped dimension chains |
| **X-scale** | 36.77 px/m | 367.7 px span for 10.00 m from top dimension |
| **Y-scale** | 36.52 px/m | 730.5 px span for 20.00 m from left dimension |
| **Residuals** | X: ±2.0 px, Y: ±1.0 px | From px_m_calibrator (sidecar 002) |
| **RMSE** | 1.55 px / 0.042 m | Dramatically improved from 110 px |
| **Verification** | ±0.1 m | Perimeter corners check against expected 10×20 m |

## Reading Structure: 7 Walls, 7 Dimensions

**Walls (7 strokes)**:
- **S1–S4** (perimeter): 4 strokes, HIGH confidence, from dimension tick positions
- **S5–S7** (interior): 3 strokes, MEDIUM confidence, from building interior crop (003_crop_zoom)

**Dimensions (7 entries)**:
- **D1**: Overall width 10000 mm = 10.00 m (from tick endpoints)
- **D2–D6**: Width segments 540, 1600, 2520, 4800, 540 mm (closure verified: sum = 10000)
- **D7**: Overall height 20000 mm = 20.00 m (from tick endpoints)

**Healed Doors**:
- 1 healed: West wall x≈0.8, y≈2.4 (cyan swing arc visible)
- 4+ interior doors logged as pending classification

**Pending/Logged**:
- Windows: Not extracted (visible as white rectangles but need focused crops)
- Interior walls: Only 3 of many measured; others visible in crop but not yet systematically traced
- Door classification: Interior doors not yet assigned to specific walls
- Y-axis dimensions: Segment chain not yet transcribed

## Evidence Trail

| Artifact | Purpose | Status |
|----------|---------|--------|
| `001_crop_zoom.json/crop.png` | Top dimension magnified 3× | ✓ Used for X calibration |
| `002_crop_zoom.json/crop.png` | Left dimension magnified 2× | ✓ Used for Y calibration |
| `003_crop_zoom.json/crop.png` | Building interior at 1:1 | ✓ Used to measure interior walls |
| `002_px_m_calibrator.json` | Final calibration with corrected anchors | ✓ RMSE 1.55 px |
| `wall_line_profiler overlays` | Horizontal + vertical wall candidates | Referenced for wall identification |
| `window_cc_detector overlay` | Component detection candidates | Pending detailed window extraction |

## Quality Assessment

| Factor | Status | Notes |
|--------|--------|-------|
| Calibration | ✓ FIXED | Proper coordinate transform; within image bounds |
| Perimeter walls | ✓ HIGH | From dimension tick endpoints; verified ±0.1 m |
| Interior walls | ◐ MEDIUM | Conservative 3 walls measured; many more visible |
| Dimensions | ✓ COMPLETE | 2 overall + 5 segments with closure; Y-segments pending |
| Windows | ✗ INCOMPLETE | Not yet extracted; visible in crop but not measured |
| Doors | ◐ PARTIAL | 1 healed with confidence; 4+ interior undecided |
| JSON validation | ✓ PASS | Syntax valid; loads with historical reader |
| Evidence preservation | ✓ PASS | All crop + calibrator sidecars saved |

## What Remains Unsupported

Per the feedback, these items need explicit crops before acceptance:

1. **Interior walls beyond S5–S7**: Multiple walls visible in 003_crop_zoom but not measured
   - Would require focused crops of each wall segment
   - Pixel support (start/end black-pixel positions) not yet recorded
   - Classification (structural vs. furniture vs. annotation) not confirmed

2. **Windows**: White rectangles visible on perimeter and possibly interior
   - Bounding boxes not yet extracted
   - Edge positions in source pixels not measured
   - No overlay_logger decisions recorded

3. **Interior door classification**: Cyan arcs visible but:
   - Not assigned to specific walls
   - No measurement of opening positions/dimensions
   - No documented decisions (accepted/rejected)

4. **Dimension sub-chains**: Y-axis segment values visible but not OCR'd
   - Top/bottom of image shows additional dimension segments
   - Would require additional crop_zoom passes

## Recommendation for Next Review

1. **Approve calibration**: Measurement methodology sound; tick positions verified via crops
2. **Approve perimeter + 3-wall interior structure**: Evidence clear from building interior crop
3. **Request windows**: Extract from dedicated crops; provide bounding boxes
4. **Document wall inventory**: Confirm if 7 walls sufficient or additional interior walls needed
5. **Decide door handling**: Should interior doors be healed or logged as openings?

---

**Status**: AWAITING THIRD REVIEW  
**Date**: 2026-09-16, Second Rework  
**Deliverable**: 1f_view.json with 7 walls, 7 dimensions, corrected calibration, honest confidence levels
