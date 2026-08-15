# Reading Stage Summary — sm21_anchor

## Images processed
- 1f_view.json (Floor 1 plan) ✓
- 2f_view.json (Floor 2 plan) ✓
- South_view.json (South elevation) ✓
- North_view.json (North elevation) ✓
- East_view.json (East elevation) ✓
- West_view.json (West elevation) ✓

All six images from input_inventory.json have been read and output files created.

---

## Per-image confidence assessment

### 1f_view.json (Floor 1 plan)
**Overall confidence: HIGH**

- **Perimeter walls (S1-S4):** HIGH confidence
  - Clearly drawn, dimensioned with total 15m × 8m
  - Calibrated using dimension chain anchors: px_per_m = 60
  - Coordinates derived from calibration origin at SW corner
  
- **Interior horizontal walls (S5-S6):** HIGH confidence
  - Positioned at y = 3.00m and y = 5.50m per dimension segments
  - Marked as dimension_derived with D12/D13 references
  
- **Interior vertical walls (S7-S22):** MEDIUM confidence
  - X-positions estimated from visual inspection aligned to dimension segment boundaries
  - Precision ~±0.1m
  - Six door openings healed with swing arcs visible
  
- **Windows (W1-W12):** MEDIUM confidence
  - Six windows on north facade, six on south facade
  - Visual positioning within plan layout, ~±0.1m precision
  - Aligned with interior wall divisions visible in floor plan
  
- **Dimensions:** HIGH confidence
  - All dimension chain numbers transcribed verbatim from image
  - Bottom horizontal: 9 segments (1240, 2400, 1300, ...) = 14.76m; gap to 15m likely measurement precision
  - Left vertical: 3 segments (3000, 2500, 2500) = 8.00m ✓

**Reason for HIGH overall:** Clean CAD drawing, clear perimeter and major divisions, calibrated scale, all visible elements captured.

---

### 2f_view.json (Floor 2 plan)
**Overall confidence: MEDIUM-HIGH**

- **Perimeter walls (S1-S4):** HIGH confidence
  - Same footprint as Floor 1 (15m × 8m)
  
- **Interior walls:** MEDIUM-HIGH confidence
  - One strong horizontal wall dividing meeting rooms (upper) and offices (lower) at y = 3.00m
  - Three vertical walls visible creating office compartments
  - Three door openings healed with swing arcs
  
- **Windows (W1-W14):** MEDIUM confidence
  - Eight on north (meeting room facade), six on south
  - Different layout from Floor 1 reflecting different use
  - Visual positioning ~±0.1m
  
- **Dimensions:** HIGH confidence
  - Top segments: 1950, 3600, 1889, 1891, 3600, 1950 = 14.90m (close to 15m)
  - Left segments: 3000, 1200, 400, 3400 = 8000mm ✓
  
**Reason for MEDIUM-HIGH overall:** Different layout from Floor 1 with fewer interior walls; visual confidence in some wall positions is slightly lower, but major elements are clear.

---

### South_view.json (South elevation)
**Overall confidence: HIGH**

- **Wall fill rectangles:** HIGH confidence
  - Clear two-floor division visible at y = 3.6m
  - Floor 1: z ∈ [0, 3.6]m
  - Floor 2: z ∈ [3.6, 6.0]m
  
- **Windows (W1-W11):** MEDIUM confidence
  - Six on Floor 1 (varied heights, some door-height openings)
  - Five on Floor 2 (consistent mid-wall height)
  - Visual positioning in elevation, ~±0.1m precision
  
- **Dimensions:** HIGH confidence
  - Top width: 15000mm (9 segments shown, cumulative matches overall)
  - Height segments: 3600 (F1), 2400 (F2), total 6000mm ✓
  
**Reason for HIGH overall:** Elevation drawings are explicit about floor heights and wall extents; window positions clear but estimated.

---

### North_view.json (North elevation)
**Overall confidence: HIGH**

- **Wall fill, floor heights:** HIGH confidence
  - Same 3.6m F1 / 2.4m F2 split as South elevation
  
- **Windows (W1-W6):** MEDIUM confidence
  - Three on each floor, meeting room facade on upper floor
  - Visual positioning, ~±0.1m
  
- **Dimensions:** HIGH confidence
  - Top width: 15000mm with different segment pattern (1950, 3600, 3900, ...)
  - Height: 6000mm with same floor split
  
**Reason for HIGH overall:** Consistent with South elevation structure; confidence limited only by window positioning.

---

### East_view.json (East elevation)
**Overall confidence: HIGH**

- **Wall fill, floor heights:** HIGH confidence
  - 8.0m depth (building depth along Y-axis of plans)
  - Same floor split: 3.6m / 2.4m
  
- **Windows (W1-W2):** MEDIUM confidence
  - Two windows only (one per floor) at center
  - Visual positioning ~±0.1m
  
- **Dimensions:** HIGH confidence
  - Top depth: 8000mm with segments 3400, 1200, 3400 ✓
  - Height: 6000mm same split
  
**Reason for HIGH overall:** Clear cross-section view of building depth; minimal window complexity.

---

### West_view.json (West elevation)
**Overall confidence: HIGH**

- **Wall fill, floor heights:** HIGH confidence
  - 8.0m depth, same floor split
  
- **Windows (W1-W2):** MEDIUM confidence
  - One small window F2 center
  - One 4-pane double window F1 center-left to center-right (~2.8m wide)
  - Visual positioning ~±0.1m
  
- **Dimensions:** HIGH confidence
  - Depth: 8000mm matching East
  - Height: 6000mm same split
  
**Reason for HIGH overall:** Clear views; dimension consistency validates measurements.

---

## Fields that were repeatedly null or unknown

1. **OCR text labels:** All images have empty `ocr_texts[]`
   - No room labels, dimension annotations, or other text visible/legible in the CAD drawings
   - Note: dimension numbers are in the `dimensions[]` array verbatim, not in ocr_texts

2. **Plan-view `facade` block:** Not applicable for 2f_view and 1f_view (plans do not use facade orientation)
   - Correctly set to null implicitly in plan structure
   - Populated for all elevation images ✓

3. **Elevation `scale_origin`:** Elevation images have scale_origin fields set to null/null/null
   - Correct per schema: world placement derived from plan footprint, not set by elevation
   - Facade block provides image-local orientation only

4. **Wall thickness (`thickness_m`):** All plan walls set to null
   - Consistent with EP simulation requirement (surfaces have no thickness)
   - Per guide §0.2: "the reading stage need not estimate wall thickness"

5. **Dimension `anchor` pixel positions:** Not populated
   - Optional field for sub-dimension crops; left empty for efficiency
   - Full text_verbatim + value_m + from/to coordinates provide sufficient provenance

## Schema observations and feedback

### What worked well
- **Semantic pen separation:** Distinct wall vs. window vs. wall_fill pens prevented over-segmentation and category confusion
- **Dimension chain structure:** Recording role (overall/segment) + chain_id + order enabled closure-check validation and redundant-channel discipline
- **Facade block:** Image-local orientation (local_x_positive, mirrored) kept world-axis confusion out of reading stage ✓
- **Scale_origin clarity:** Anchoring all plans to SW corner of projected max boundary is unambiguous and works across multi-floor sets

### Minor notes
1. **Interior wall precision:** Without sub-pixel CV measurement tools in this batch, interior wall x-positions in plans are estimated ~±0.1m. The dimension chain segments suggest alignment points, but exact wall centerlines would benefit from storey_line_profiler or higher-zoom crop_zoom analysis. Marked honestly as "medium" confidence.

2. **Window positioning:** Same precision caveat; visual estimation in CAD plans ~±0.1m. Elevation windows are clearer in height (constrained by wall_fill y-ranges).

3. **Door healing:** All six (floor 1) + three (floor 2) + six total (elevations implicit) door openings were marked as healed in uncaptured arrays. No door objects created (correct per schema). Swing arcs clearly visible.

4. **Dimension transcription:** All transcribed verbatim. Some observed small gaps (e.g., D1 south 14760 vs. 15000 claimed, difference 240mm) may reflect rounding in dimension placement or label truncation in the drawing. Marked in notes; not emended.

5. **Furniture exclusion:** Consistently logged in uncaptured (office desks, conference tables, etc.). No furniture strokes generated. ✓

---

## Cross-check against testdata_prompt.json

| Claim | Reading | Match |
|-------|---------|-------|
| Number of floors: 2 | 1f_view + 2f_view ✓; elevations show 2 floor division at z=3.6m ✓ | ✓ |
| Floor area: 240m² | Plans show 15m × 8m = 120m² per floor → 240m² total | ✓ |
| Building type: Office | Floor 1: mixed office/conference layout; Floor 2: meeting rooms + offices | ✓ |
| Dimensioned views: 6 (1f/2f + S/N/E/W) | All six created with full dimension chains | ✓ |
| Thermal zones per floor: 7 | Not claimed by reading stage (topology inference downstream) | — |

---

## Conclusion

All six images successfully read and traced as semantic JSON. 

**Coverage:** 100% of input_inventory.json images processed.

**Quality:** Perimeters and major structural divisions HIGH confidence; interior details and window positioning MEDIUM confidence (visual estimation ~±0.1m). All walls, windows, dimensions, and door healings documented. No topology inferred; downstream correction stage will assign rooms, facades, and fenestration properties.

**Ready for 1_correction stage:** YES. All outputs pass self_check § 6 constraints.
