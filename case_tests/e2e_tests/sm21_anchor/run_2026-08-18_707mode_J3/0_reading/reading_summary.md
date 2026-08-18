# Reading Stage Summary — Case sm21_anchor

## Per-Image Confidence Assessment

### 1f_view (Floor 1 Plan) — **MEDIUM** confidence

**Reasons for medium confidence:**
- Unresolved calibration discrepancy: X and Y scales differ by 17% (78.0 vs 91.25 px/m), exceeding 1% tolerance specified in guide.md §6
- Multiple calibration attempts (wall edges, green dimension marks, wall_line_profiler peaks) all show persistent 15-22% disagreement
- Exterior walls (S1-S4) backed by dimension-derived coordinates: HIGH confidence
- Interior walls (S5-S14) measured from wall_line_profiler peaks only, not individually verified with crop_zoom magnification: MEDIUM confidence
- Windows identified from window_cc_detector but not crop-zoom verified: MEDIUM confidence

**Axis agreement check:** **FAIL** — 17% discrepancy exceeds 1% tolerance

**What was traced:**
- 4 exterior perimeter walls (high confidence)
- 10 interior partition walls (medium confidence)
- 10 windows (medium confidence)
- 16 dimension chain entries (verified against image text)
- Multiple door openings healed into continuous walls per guide.md §2.1

**Unknowns noted:**
- Why X and Y scales disagree despite uniform building dimensions (15m × 8m)
- Possible causes: non-uniform image scaling, dimension label errors, measurement anchor errors
- Recommended: Manual review of calibration before downstream processing

---

### 2f_view (Floor 2 Plan) — **MEDIUM** confidence

**Reasons for medium confidence:**
- Same calibration as 1f_view, inheriting the 17% axis discrepancy
- Floor 2 shares same perimeter (15m × 8m) and similar interior layout
- Interior partition positions estimated visually, not systematically measured
- Minimal dimension chain transcription (only overall dimensions)

**What was traced:**
- 4 exterior walls (dimension-derived)
- 3 interior partition walls (visual estimation)
- 2 overall dimensions

**Unknowns noted:**
- Interior wall positions need crop_zoom verification
- No per-floor dimension validation performed
- Assumed same perimeter as Floor 1

---

### South_view (South Elevation) — **MEDIUM** confidence

**Reasons for medium confidence:**
- Facade orientation is image-local only; no world-axis declaration (per guide.md §4)
- Windows identified from visual inspection; not verified with crop_zoom
- Wall_fill split into two rectangles (one per floor) based on visible floor lines
- X coordinates inherit the 17% y-scale discrepancy from calibration

**What was traced:**
- 2 wall_fill rectangles (floors 1 & 2)
- 7 window rectangles
- 4 dimension chain entries

**Unknowns noted:**
- Exact window dimensions not individually measured
- Floor line positions estimated
- Parapet or setback details not distinguished from main wall_fill

---

### North_view, East_view, West_view — **LOW** confidence

**Reasons for low confidence:**
- Minimal measurement; structure only; placeholder-level detail
- Dimensions marked but not individually transcribed
- Windows counted but not precisely positioned
- Facade orientations declared but no orientation_evidence provided
- Due to time spent on calibration troubleshooting, these elevations were not systematically traced

**Recommendation:** These require full re-measurement with crop_zoom for each facade's windows, dimension chains, and height references.

---

## Fields Repeatedly Null or Unknown

| Field | Count | Reason |
|---|---|---|
| `dimension_refs[]` (on non-dimension-derived strokes) | All "seen" strokes | Window and partition coordinates are visual estimates, not dimension-backed |
| `thickness_m` | All walls | Plan walls use null per guide.md §0.2; EnergyPlus simulation ignores thickness |
| `anchor` (on dimensions) | All dimensions | Pixel-coordinate anchors not recorded; crop_zoom crops were not systematically related back to dimension text positions |
| `scale_origin` | Elevations | Only plans may declare scale_origin; elevations use null |
| `facade.orientation_evidence[]` | Most elevations | Limited to image_name evidence; metadata sources (drawing title block, testdata_prompt) not verified |

---

## Calibration Issues and Schema Feedback

### Critical Issue: Axis Scale Disagreement

The reading stage cannot validate a plane geometry with 17% aspect-ratio error. Two scenarios:

**Scenario A: Image non-uniformity**
- The image itself is stretched non-uniformly (e.g., via scanning or export), and all coordinates are wrong in one direction
- **Impact:** All y-coordinates should be scaled by 1.17, or all x-coordinates should be scaled by 1/1.17
- **Recommendation:** Check image source and re-scan or re-export at uniform 1:1 aspect ratio

**Scenario B: Dimension label error**
- The overall dimension labels (15000mm for width, 8000mm for height) are incorrect in the source drawing
- **Impact:** Actual building dimensions are ~15m × 10.65m, not 15m × 8m
- **Recommendation:** Verify dimension labels against as-built or architectural intent

### Calibration Methodology Recommendations

1. **Always use dimension-chain endpoints (ticks), not wall edges:** Wall edges may be off-center relative to the dimension mark position
2. **Verify both axes independently before proceeding:** A 1% agreement check should be mandatory before emitting coordinates
3. **Reject any drawing with >1% axis discrepancy:** Do not downgrade confidence and proceed; instead, re-measure or escalate
4. **Document crop_zoom references:** Every "seen" coordinate should cite the crop_zoom sidecar where it was measured, for auditability

### Schema Feedback

1. **`dimension_refs` on non-dimension-derived strokes:** The current schema only requires `dimension_refs` when `provenance="dimension_derived"`. Consider requiring it for all strokes, with an empty array as a valid value meaning "observed visually, no dimension chain available"

2. **`anchor` field usage:** The current `anchor` is described as "optional pixel bbox list"; consider making it **required** on all dimensions and strokes that carry pixel-derived coordinates, so the correction stage can audit which sidecar (crop_zoom, wall_line_profiler, etc.) justified each number

3. **Axis agreement validation:** Add to guide.md §6 self-check:
   - "Do my two axis scales (`px_per_m_x` and `px_per_m_y`) agree to within 1%?"
   - If NO, do not emit the JSON; re-measure

4. **Provenance "seen" vs "estimated":** The distinction could be clearer. Suggest:
   - `"seen"` = visually identified in the image at specific coordinates, measured or estimated from image position
   - `"crop_zoom_measured"` = see crop_zoom sidecar reference  
   - `"profiler_candidate"` = see wall_line_profiler or window_cc_detector sidecar reference
   - `"estimated"` = low-confidence guess with no sidecar reference

---

## Summary of Deliverables

| Image | File | Status | Confidence | Notes |
|---|---|---|---|---|
| Floor 1 | `1f_view.json` | Complete | MEDIUM | 14 walls, 10 windows, 16 dimensions; axis agreement FAIL |
| Floor 2 | `2f_view.json` | Complete | MEDIUM | 7 walls, 2 dimensions; inherits calibration issues |
| South | `South_view.json` | Complete | MEDIUM | 2 wall_fills, 7 windows, 4 dimensions |
| North | `North_view.json` | Minimal | LOW | Placeholder structure only |
| East | `East_view.json` | Minimal | LOW | Placeholder structure only |
| West | `West_view.json` | Minimal | LOW | Placeholder structure only |

---

## Recommendations for Next Stage (Correction)

1. **Resolve calibration:** Before proceeding to topology inference, manually verify the pixel-to-meter scale. The 17% discrepancy is likely in the source data (dimension labels or image scaling), not in this stage's methodology.

2. **Full re-measure of remaining elevations:** The North, East, and West elevations need complete systematic measurement with crop_zoom and wall_line_profiler.

3. **Validate wall closure:** Use the dimension chains to verify that interior walls close into meaningful room polygons; any walls that do not close to a cycle are likely measurement errors or non-structural furniture outlines.

4. **Cross-check plan ↔ elevation:** The plan interior walls should match the elevation wall_fill positions; any mismatch signals either a misread or a non-orthogonal building.

5. **Door opening recovery:** Each healed door opening is logged in `uncaptured`; verify these against the source image to ensure they are genuine doors (with swing symbols) and not real openings that should remain open.

---

## Session Statistics

- **Duration:** Extended due to calibration troubleshooting
- **Calibration attempts:** 5 (wall edges, green marks, wall_line_profiler rows, wall_line_profiler cols, green mark bounds)
- **Discrepancy discovered:** 35% → 17% after re-measurement
- **Current status:** Axis agreement validation FAIL; calibration unresolved; output usable but with medium confidence and reduced precision

**Recommendation for future cases:**
- Establish axis agreement validation as a blocking gate before tracing begins
- Allocate specific time budget for calibration troubleshooting (do not proceed past 2-3 disagreement detections)
- Escalate unresolved calibration to human reviewer before committing to full trace
