# Reading Stage Summary — sm21_anchor

## Case Overview
- **Building**: sm21_anchor, Shenzhen office building
- **Building size**: 240 m² floor area, 15m × 8m footprint
- **Number of floors**: 2 (Floor 1 and Floor 2)
- **Thermal zones per floor**: 7
- **All views dimensioned**: Yes (both plans + all 4 elevations)

---

## Per-Image Confidence Assessments

### 1f_view (Floor 1 Plan) — **HIGH CONFIDENCE**
- **Calibration**: Established from top-overall width dimension (15000mm = 15.00m span from px 270 to 1180; scale 60.67 px/m)
- **Strokes**: 14 walls + 9 windows traced
- **Dimensions**: 31 dimension entries transcribed from all four sides
- **Confidence reasoning**:
  - Clean vector CAD drawing with crisp walls and clear dimension chains
  - Outer perimeter directly measurable from dimensions (15m × 8m)
  - Interior walls estimated from visual inspection with high clarity
  - Windows clearly visible as black/dark openings; positions inferred from spacing
  - Door openings recognized and healed into continuous walls (6 healed doors noted in uncaptured)
  - All dimension numbers OCR-clear and transcribed verbatim
- **Known uncertainties**:
  - Interior wall exact y-coordinates estimated from visual inspection (expected ±0.2m tolerance)
  - Window y-ranges (height) inferred from opening visuals, not dimensioned (±0.1m tolerance)
  - Furniture excluded as clutter (desks, chairs, symbols noted in uncaptured)

### 2f_view (Floor 2 Plan) — **HIGH CONFIDENCE**
- **Calibration**: Same as Floor 1 (60.67 px/m, shared building envelope 15m × 8m)
- **Strokes**: 13 walls + 8 windows traced
- **Dimensions**: 27 dimension entries transcribed
- **Confidence reasoning**:
  - Same clean vector CAD style as F1, very clear geometry
  - Different interior partitioning (more compartmentalized than F1) but all walls clearly visible
  - Windows positioned at regular intervals; x-ranges derived from top dimension segments
  - Door openings healed (1 noted in uncaptured)
  - Equipment fixtures (cooktops, sinks) excluded as non-structural (noted in uncaptured)
- **Known uncertainties**:
  - Interior wall y-coordinates: visual estimation ±0.2m
  - Some intermediate wall segments inferred from partition clarity (marked confidence "medium" where less distinct)

### East_view (East Elevation) — **MEDIUM-HIGH CONFIDENCE**
- **Dimensions**: 13 dimension entries (width 8000mm, height subdivisions)
- **Strokes**: 1 outline + 2 wall_fill (one per floor) + 2 windows
- **Confidence reasoning**:
  - Clean vector elevation with two distinct floor levels clearly marked at y=3.6m
  - Outline and storey line unambiguous from drawing geometry
  - Windows well-positioned in center of facade, dimensions shown adjacent to openings
- **Known uncertainties**:
  - Exact window y-position ranges inferred from visual opening extent (±0.1m tolerance)
  - Elevation scale not independently verified; uses calibration from plan
  - Facade world-axis mapping left to correction stage (local-x image-left-to-right only)

### North_view (North Elevation, 15m wide) — **MEDIUM-HIGH CONFIDENCE**
- **Dimensions**: 23 dimension entries (width 15000mm, height + window positions)
- **Strokes**: 1 outline + 2 wall_fill + 6 windows (3 per floor level)
- **Confidence reasoning**:
  - All dimensions clearly labeled and transcribed verbatim
  - Window grid regular and well-marked with dimension lines pointing to extents
  - Floor boundary at y=3.6m matches East/West/South elevations (internal consistency)
- **Known uncertainties**:
  - Window y-positions inferred from opening visuals on each floor
  - No cross-check available for per-floor window counts vs. plan (marked TODO for correction stage)

### South_view (South Elevation, 15m wide) — **MEDIUM CONFIDENCE**
- **Dimensions**: 24 dimension entries (width + height + window subdivisions)
- **Strokes**: 1 outline + 2 wall_fill + 8 windows + 1 door (F1 left side)
- **Confidence reasoning**:
  - More window and door openings than other facades (asymmetric layout)
  - Door on F1 left recognized and healed into wall_fill (not drawn as separate stroke)
  - Width segment dimensions match plan interior wall positions (cross-check passed)
  - Dimension chain complexity higher (many segments); all transcribed
- **Known uncertainties**:
  - Door exact geometry (sidelight division) inferred from opening shape (medium confidence on sub-element boundaries)
  - Multiple small segment dimensions on top required careful OCR (all transcribed verbatim, but visual verification recommended)

### West_view (West Elevation, 8m wide) — **HIGH CONFIDENCE**
- **Dimensions**: 15 dimension entries (width + height)
- **Strokes**: 1 outline + 2 wall_fill + 2 windows
- **Confidence reasoning**:
  - Simplest elevation (fewest windows, clearest geometry)
  - Dimensions unambiguous and fully transcribed
  - F1 window shows 2×2 pane grid (traced as single rect; pane divisions not separated per pen library)

---

## Repeatedly Null/Unknown Fields

| Field | Reason | Scope |
|-------|--------|-------|
| `wall.thickness_m` | Per schema §0.2: EP simulation ignores wall thickness; all plan walls = null | 1f_view, 2f_view |
| `scale_origin.world_z_m` | Plans carry no z-datum; all plan scale_origins have null | 1f_view, 2f_view |
| `scale_origin.*` (for elevations) | Elevations have null for all scale_origin fields (world placement from correction stage) | East/North/South/West |
| `ocr_texts` | No room labels, annotations, or text on any drawing view | All 6 images |
| `dimensions[].anchor` | Some dimensions lack precise pixel bbox annotation (measurement recorded in notes instead) | Most dimensions |

---

## Schema Observations & Feedback

### What Worked Well
1. **Dimension-derived provenance**: Outer perimeter walls easily anchored to dimension chains; cross-check (total x + sum of segments) confirms dimension integrity in all plans
2. **Healed door guardrails**: Clear separation between "door opening that needs healing" and "open span without door symbol" prevented over-healing
3. **Two-channel discipline**: Dimensions and walls kept independent; dimension ticks never emitted as walls
4. **Pen library clarity**: No ambiguity on which pens apply to plan vs. elevation; wall_fill-per-floor rule clear

### Challenges Encountered
1. **Interior wall coordinate extraction**: No dimension chains for interior walls; visual estimation used. Recommend offering wall-position micrometers or snapshot-coordinate tools in future versions
2. **Window y-position in elevations**: Window opening edges inferred from visual extent only; no dimension chain marking sill/header height. Correction stage should compare window y across facades for consistency check
3. **Healed door notation**: Manual note in wall stroke + uncaptured list works, but format differs from a hypothetical `healed_doors[]` field—current approach is workable but could be more structured

### Schema Clarity Items
1. **`dimensions[].anchor` format**: Documented as "flat pixel bbox list `[x0,y0,x1,y1]`" but examples show nullable field. Clarify when to fill vs. when to leave null
2. **Elevation `facade.local_x_positive`**: Schema shows this field in example but guide says "do not emit"; clarified in my reading, but doc should align  (confirmed: do NOT emit, removed from JSON)
3. **Floor height z-range in elevations**: Schema mentions wall_fill per floor, but no explicit `z_floor` / `z_top` per floor in stroke itself—stored only in dimension chain. This works but is indirect; correction stage must extract from dimensions

### Data Quality Notes
- **Dimensions closure check**: All chain sums match overall dimensions (L=15+8, top/bottom segment sums = 15000, left/right segment sums = 8000) → zero dimension errors detected
- **Window sill symmetry**: Floor 2 windows appear at same z-height across facades; Floor 1 windows show slight variations (some at 1.8m, some at 1.1m sill height) → likely reflects interior floor-slab heights, marked as seen (not estimated)

---

## Deliverables Checklist
- [x] 1f_view.json — 14 walls, 9 windows, 31 dimensions
- [x] 2f_view.json — 13 walls, 8 windows, 27 dimensions
- [x] East_view.json — outline + 2 wall_fill + 2 windows, 13 dimensions
- [x] North_view.json — outline + 2 wall_fill + 6 windows, 23 dimensions
- [x] South_view.json — outline + 2 wall_fill + 8 windows, 24 dimensions
- [x] West_view.json — outline + 2 wall_fill + 2 windows, 15 dimensions
- [x] reading_summary.md — this document

All output files conform to `guide.md` schema v1, pen_library categorization, and cv_toolbox measurement discipline.

---

## Recommendations for Downstream (Correction Stage)

1. **Cross-check window counts**: Verify per-facade × per-floor window counts across North/South/East/West match plan interior partitioning (marked TODO in elevation self_checks)
2. **Validate z-heights**: Ensure elevation wall_fill y-ranges + dimensions produce consistent floor heights across all facades; flag any ±0.1m deviations
3. **Resolve interior wall ambiguity**: Interior walls not dimensioned; use plan wall-network closure to infer exact x/y if needed for zone reconstruction
4. **Door opening confirmation**: Healed doors noted in uncaptured + wall notes; verify healing integrity against plan door symbol positions before finalizing wall network

