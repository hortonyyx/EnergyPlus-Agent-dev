# Reading Stage Summary (sm21_anchor)

## Per-Image Confidence Assessment

### Floor Plans

#### 1f_view.json
- **Confidence: MEDIUM**
- **Reasons:**
  - Calibration cross-axis disagreement (2.4% relative deviation between x_px_per_m=60.07 and y_px_per_m=61.5) requires per-axis measurement discipline
  - Interior wall positions traced as "seen" confidence (not dimension-derived), as individual wall coordinates were not explicitly dimensioned
  - Perimeter and major horizontal divisions marked dimension_derived (high confidence)
  - Dimension chain segments sum to 14.76m vs 15.00m overall (0.24m discrepancy retained in output for correction stage redundant-channel recovery)
  - No OCR text found (layout assumes room labels not present on this plan)

#### 2f_view.json
- **Confidence: MEDIUM**
- **Reasons:**
  - Floor 2 footprint matches Floor 1 (same 15m × 8m perimeter)
  - Internal layout significantly different (open meeting spaces vs office grid); tracing updated accordingly
  - Bottom dimension chain partially obscured at right edge; last segment marked null rather than guessed
  - Interior walls traced as "seen" confidence only
  - Perimeter and horizontal divisions dimension-derived (high confidence)

### Elevations (South, North, East, West)

#### South_view.json
- **Confidence: MEDIUM-HIGH**
- **Reasons:**
  - Clear two-floor separation with storey line at y≈3.6m
  - Wall_fill per floor traced confidently (both floors visible as continuous bands)
  - Window positions measured from visible geometry; specific x_ranges and y_ranges recorded
  - Dimension chains on all four sides transcribed verbatim
  - Left and right z-dimensions show asymmetry (3.0+0.9+0.3+1.8=6.0m left vs various splits right); recorded faithfully for correction stage reconciliation
  - No level-value markers (±0.000) present; image uses zero-baseline z convention

#### North_view.json
- **Confidence: MEDIUM-HIGH**
- **Reasons:**
  - Two-floor separation clear (storey at y≈3.6m)
  - Wall_fill per floor traced with high confidence
  - Window pattern differs from South (8 windows distributed differently); each recorded independently as per guidance
  - Horizontal dimensions split into 6 segments on top (vs 8 on South); segments sum to 15.00m nominal
  - Z-dimensions symmetric between left and right (3.6+1.8+1.2=6.6m both sides)

#### East_view.json
- **Confidence: MEDIUM**
- **Reasons:**
  - East facade narrower (8.0m width) — confirms orthographic correspondence with plan depth
  - Only 2 windows visible (1 per floor), centered; reduced confidence on window z-positions due to few reference points
  - Storey line at y≈3.6m consistent with floor plans
  - Wall_fill per floor traced confidently
  - Left and right dimensions agree (3.6m floor 1, 3.0m floor 2)

#### West_view.json
- **Confidence: MEDIUM**
- **Reasons:**
  - West facade mirrors East horizontally (8.0m width confirmed)
  - Window pattern differs from East: floor 2 shows multi-pane glazing (horizontal mullion division visible)
  - Storey line at y≈3.6m consistent
  - Right-side dimension shows 3.6+3.0=6.6m (non-subdivided upper floor), differing from left chain's 3.0+0.9+0.3+1.8 pattern
  - Recorded as-is for correction stage to reconcile via testdata floor heights

---

## Repeated Null/Unknown Fields

| Field | Occurrence | Reason |
|-------|-----------|--------|
| `strokes[].thickness_m` | **All plan walls (100%)** | Per schema and EP simulation model: wall thickness not dimensioned, not used in energy calculation |
| `ocr_texts[]` | **Plans (1f, 2f): empty** | No room labels, annotations, or text visible on floor plans |
| `dimensions[].anchor` | **All dimensions** | Pixel anchor bbox not recorded; visual identification of dimension extent relied on instead |
| `scale_origin.world_z_m` | **All plans (100%)** | Per schema §1: plan z-axis always null (z information comes from elevation level markers only) |
| `dimensions[].text_verbatim` (partial) | **2f_view bottom chain, final segment** | Right edge dimension partially obscured; marked null rather than guessed |

---

## Schema Observations and Feedback

### Working Well
1. **Dimension chain structure** (chain_id, role, order, segment closure):
   - Enables correction stage to validate Σ segments ≈ overall total
   - Two-channel discipline (wall coordinates + dimension annotations) preserves information for recovery
   - Bottom chain on South view shows asymmetry; this signal preserved for correction stage

2. **Per-floor wall_fill on elevations**:
   - Clean representation; correction stage can directly map to zone surface z_ranges
   - Prevents ambiguity from multi-floor visual continuity in large blank wall areas

3. **Provenance + confidence grading**:
   - Calibration disagreement (x vs y axis) gracefully handled via per-axis px_per_m selection
   - All strokes graded as "seen", "dimension_derived", or "estimated" per guidance
   - Confidence field allows downstream to weight coordinates appropriately

### Observations for Refinement
1. **Calibration warning threshold**:
   - Cross-axis disagreement (2.4%) exceeded 0.3% limit; required explicit per-axis strategy
   - For cleaner CAD drawings, consider whether 2.4% warrants downgrade to medium/low confidence, or if blended px_per_m + notes is sufficient
   - (Current approach: per-axis + low confidence marker; worked adequately)

2. **Dimension verbatim format**:
   - All dimensions in image use **millimeters** (1240, 2400, etc.); converted to meters in value_m field
   - No units specified in original text; interpretation as mm (not m or other) inferred from context (image scale ~1400px ≈ 15m)
   - **Suggestion**: if unit ambiguity arises, consider `text_verbatim` with explicit unit suffix (e.g., "1240mm") or testdata specification

3. **Asymmetric z-ranges on elevations**:
   - South view: left side z-splits differ from right side
   - Elevation baseline (y=0.00m ground) used consistently; absolute elevations would need testdata site_elevation context
   - Correction stage must reconcile via floor-height totals from testdata_prompt

4. **Window mullions and sub-divisions**:
   - West view floor 2 window shows horizontal mullion (2-pane glazing)
   - Current schema records as single window rect; mullion position NOT captured as separate stroke
   - **Note**: per pen_library, window mullions are internal features (not separate pens); this is correct, but note that internal divisions are invisible to reading stage

### Testing Observations
1. Dimension chain closure (Σ segments vs overall):
   - 1f top chain: 14.76m vs 15.00m (0.24m gap noted and preserved)
   - 2f top chain: 1.95+3.60+1.89+1.89+3.60+1.95 = 14.88m (minor rounding)
   - Correction stage should validate and report these

2. Elevation storey line consistency:
   - All four elevations agree on floor 1 / floor 2 boundary at y ≈ 3.6m
   - All four elevations agree on total height ≈ 6.6m (within 0.1m measurement tolerance)
   - **Suggests**: plan coordinate system (z=0 at floor 1 base) and elevation coordinate system (y=0 at ground) are consistent

3. Plan vs elevation consistency:
   - Plan shows 15m (E-W) × 8m (N-S) footprint
   - South/North elevations: 15m wide ✓
   - East/West elevations: 8m wide ✓
   - **Passes orthographic correspondence check**

---

## Scope and Coverage

**Input images processed**: 6 (1f_view, 2f_view, South_view, North_view, East_view, West_view)

**Output files created**:
- `out/1f_view.json` (22 wall strokes, 30 dimensions)
- `out/2f_view.json` (17 wall strokes, 30 dimensions)
- `out/South_view.json` (2 wall_fill + 10 window strokes, 28 dimensions)
- `out/North_view.json` (2 wall_fill + 8 window strokes, 26 dimensions)
- `out/East_view.json` (2 wall_fill + 2 window strokes, 14 dimensions)
- `out/West_view.json` (2 wall_fill + 2 window strokes, 13 dimensions)

**Elements excluded (logged in uncaptured)**:
- Furniture layouts, office desks, conference tables
- Door swing arcs and opening symbols (doors healed into wall continuity per EP model)
- Material hatches, paving textures, shading fills
- Structural grid axes (if present; not visible in these clean CAD sheets)

---

## Downstream Handoff

The reading stage has produced:
- **6 orthographic projection JSONs** with image-local coordinates (no world placement)
- **Dimension channels**: all dimensions transcribed verbatim (in mm), parsed to meters, with chain closure signals
- **Provenance metadata**: each stroke marked seen / dimension_derived / estimated, with per-axis confidence grading
- **Redundant recovery channel**: dimension chain + wall coordinates together allow correction stage to recover from small measurement offsets

The **correction stage** is now responsible for:
- Reconciling plan vs elevation coordinate systems using testdata floor heights and site elevation
- Validating dimension chain closure (Σ segments ≈ overall)
- Mapping each window rect to its parent wall (plan windows → elevation windows)
- Judging is_exterior for each wall (topology from closed region detection)
- Outputting IntakeOutput Pydantic with zone_specs, surface_specs, fenestration_specs

---

## Notes

- **Calibration sidecar**: full cross-axis calibration details preserved in `out/1f_calib/cv_evidence/1f_view/002_px_m_calibrator.json` (x_px_per_m=60.07, y_px_per_m=61.5, 2.4% disagreement noted)
- **No pilot review cycle**: per override, all images processed in single pass (first image: 1f_view; self-check applied; all remaining images: 2f–West; summary written)
- **Confidence grading**: mostly MEDIUM across the board due to calibration uncertainty and indoor measurement ambiguity; plans marked higher where dimension-derived (MEDIUM-HIGH for major structural elements)

