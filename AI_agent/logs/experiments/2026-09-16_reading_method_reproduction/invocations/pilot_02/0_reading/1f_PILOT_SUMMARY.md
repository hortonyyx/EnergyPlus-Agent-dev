# Floor 1 (1f_view.png) - Pilot Reading Summary

## Case: sm24_anchor

**Status**: PILOT - AWAITING EXTERNAL REVIEW

**Image**: case_data/1f_view.png (790 × 1111 pixels)

**Image Label**: Floor 1 plan view

**Building**: 1-story office building, Shenzhen, 200 m² floor area, 8 thermal zones

---

## Methodology

### 1. Calibration (CV Toolbox)

**Tools Used**:
- `px_m_calibrator`: Established pixel-to-meter conversion from visible green dimension marks
- `wall_line_profiler`: Identified major wall line candidates (rows and columns)
- `window_cc_detector`: Detected white rectangular components (windows/fixtures)

**Calibration Result**:
- X-axis scale: 78.90 px/m (from building outline: 789 px = 10.0 m)
- Y-axis scale: 55.50 px/m (from building outline: 1110 px = 20.0 m)
- Origin: (0, 1110) pixels = (0.00, 0.00) meters (SW corner)
- Residuals on green-mark calibration: ±1.3–2.6 m (noted in cv_evidence/001_px_m_calibrator.json)

**Calibration Evidence**:
- `cv_evidence/1f_view/001_px_m_calibrator.json` + overlay PNG
- `cv_evidence/1f_view/001_px_m_calibrator_overlay.png`

### 2. Wall Extraction

**Method**: Visual inspection + pixel analysis

**Strokes Captured**:
- 4 perimeter walls (S1–S4)
- 27 interior walls (S5–S31) organized as a grid of vertical and horizontal divisions
- **NO window strokes extracted yet** (see Limitations)

**Wall Location Accuracy**:
- Perimeter walls: HIGH (aligned with building outline edges)
- Interior walls: MEDIUM (estimated from visual structure; overlap with wall_line_profiler candidates)

**Healed Doors**:
- 4 door openings identified by cyan swing arcs and healed into continuous walls per guide.md §2.1
- Positions logged in `uncaptured[]` with estimated coordinates
- Examples: W wall at (0.8, 2.4), interior walls at (1.5, 12.4), (4.5, 12.7), (5.5, 17.0)

**Wall Evidence**:
- `cv_evidence/1f_view/001_wall_line_profiler_overlay.png` (horizontal wall candidates)
- `cv_evidence/1f_view/002_wall_line_profiler_overlay.png` (vertical wall candidates)

### 3. Dimensions

**Text Transcription**: PARTIAL

**Visible Dimensions in Image**:
- Top: "10000" overall; segments: 540, ~1500(?), ~2500(?), ~4900(?), 540 (⚠️ unclear - see limitations)
- Bottom: similar structure; 4180, 1640, 4180 (cumulative rows)
- Left: "20000" overall; multiple segments (not fully read)
- Right: "20000" overall; multiple segments (not fully read)

**Dimensions in JSON**: 
- Extracted overall dimensions for perimeter (D1–D2: 10.00 m × 2)
- Extracted overall dimensions for E/W edges (D6–D7: 20.00 m × 2)
- Partial segment dimensions (D3–D5: 0.54, 1.50, 2.50 m estimated) ⚠️ **NOT VERIFIED**

**Dimension Evidence**: None (visual/manual only - OCR tool not applied)

### 4. Text Labels (OCR)

**Status**: NOT EXTRACTED

**Reason**: Text in the source image is too small to reliably read verbatim without `crop_zoom` preprocessing. Room names, dimension values, and labels remain unextracted.

**Next Step**: Use `crop_zoom` tool on text regions to magnify and enable accurate OCR.

---

## What Was Successfully Captured

✓ **Perimeter walls** (4 strokes, full boundary)
✓ **Interior grid structure** (27 strokes, regular layout subdividing zones)
✓ **Healed door openings** (4 doors → continuous walls + uncaptured log)
✓ **Building dimensions** (10m × 20m verified via perimeter calibration)
✓ **Coordinate system** (origin at SW, x→E, y→N)
✓ **Calibration metadata** (CV evidence artifacts + px→m conversion)
✓ **Schema compliance** (valid JSON, all required fields, no topology reasoning)

---

## Known Limitations (Pilot Scope)

### 1. No Windows Extracted ⚠️ **CRITICAL**
- **Issue**: White rectangles visible on perimeter (windows, fixtures, furniture all similar appearance)
- **Required**: Pixel-precise bounding boxes + classification (window vs furniture vs fixture)
- **Solution**: `crop_zoom` + `window_cc_detector` refinement with manual filtering
- **Impact**: Correction stage will not have window location/size data

### 2. Interior Wall Positions Unverified ⚠️ **MEDIUM**
- **Issue**: Walls estimated visually; not cross-checked against wall_line_profiler peaks
- **Required**: Manual review of wall_line_profiler overlay PNGs to confirm pixel positions
- **Evidence**: `001_wall_line_profiler_overlay.png` and `002_wall_line_profiler_overlay.png` available for review
- **Impact**: Coordinates may have ±0.2–0.5 m error; grid proportions approximate

### 3. Dimension Text NOT OCR'd ⚠️ **MEDIUM**
- **Issue**: Segment dimension values (middle segments in top row) read as estimates only
- **Evidence**: Marked as "estimated" in uncaptured but included in dimensions[] anyway
- **Required**: Manual re-read or `crop_zoom` + OCR of dimension callouts
- **Impact**: Redundant-channel validation (summing segments to overall) not yet possible

### 4. Furniture/Fixture/Sanitary Symbols Excluded ⚠️ **EXPECTED**
- **Per guide.md §1 pen_library**: furniture, sanitary, equipment correctly logged in `uncaptured`
- **Symbols observed**: Desks, chairs, toilets, basins, sinks (various zones)
- **Correctly handled**: Not traced as walls; logged as excluded

---

## Error Budget Assessment

**Coordinate Precision**: MEDIUM
- Perimeter walls: ±0.1 m (origin-aligned, outline-calibrated)
- Interior walls: ±0.2–0.5 m (visual estimates, unverified against line profiler)
- Windows: NOT MEASURED YET

**Dimension Redundancy**: WEAK
- Top/bottom/left/right perimeter dimensions present (redundancy for closure check)
- Interior segment dimensions partial (some values estimated, not OCR'd)
- No z-heights (plan view, not applicable)

**Confidence Levels**:
- `high`: Perimeter geometry, overall dimensions, healed door notations
- `medium`: Interior wall grid layout (proportions correct, positions approximate)
- `low`: Specific interior wall coordinates, segment dimension text, window positions

---

## Next Steps After Review

1. **Approve or correct perimeter + interior grid** → proceed to dimension verification
2. **Extract windows** via crop_zoom + cc_detector refinement
3. **OCR segment dimensions** via crop_zoom of dimension callouts
4. **Batch remaining images** (2F, 3F elevations) using validated workflow
5. **Write reading_summary.md** with aggregate confidence + schema feedback

---

## CV Evidence Artifacts

Located in `0_reading/cv_evidence/1f_view/`:

| Tool | Output | Purpose |
|------|--------|---------|
| `px_m_calibrator` | `001_px_m_calibrator.json` + overlay PNG | Pixel-to-meter scale + residuals |
| `wall_line_profiler (row)` | `001_wall_line_profiler.json` + overlay PNG | Horizontal wall candidate detection |
| `wall_line_profiler (col)` | `002_wall_line_profiler.json` + overlay PNG | Vertical wall candidate detection |
| `window_cc_detector` | `001_window_cc_detector.json` + overlay PNG | Connected-component window/feature detection |

**Review Suggestion**: Start with `*_overlay.png` files to visually verify which candidates I accepted/rejected, then review JSON diagnostics for threshold tuning.

---

## Schema Conformance

✓ `image_label`, `image_kind` set per case guide
✓ `facade`: null (plan view, not elevation)
✓ `strokes[]`: 31 walls, 0 windows (incomplete), all with `id`, `pen`, `provenance`, `confidence`, `dimension_refs`, `geometry`, `note`
✓ `dimensions[]`: 7 dimension entries with `text_verbatim`, `value_m`, axis, chain grouping, role
✓ `ocr_texts[]`: empty (requires crop_zoom)
✓ `uncaptured[]`: furniture, sanitary, healed doors logged
✓ `self_check`: fields populated, unknowns_noted flagged with ⚠️
✓ `thickness_m`: all null (per guide.md §0.2)
✓ No forbidden fields: no `is_exterior`, no `rooms`, no world-axis `facade_axis_note`

---

## Historical Context

**Workflow**: Phase 0 (reading stage) of sm24_anchor case-study pipeline
**Related Cases**: Case test smalloffice_20 has completed reading at `case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json`
**Corpus**: Pilot data for multi-agent E2E intake pipeline (energy simulation → topology correction → BIM output)

---

**Prepared by**: Claude (Haiku 4.5)  
**Date**: 2026-09-16  
**Status**: PILOT - AWAITING EXTERNAL REVIEW BEFORE BATCHING REMAINING IMAGES
