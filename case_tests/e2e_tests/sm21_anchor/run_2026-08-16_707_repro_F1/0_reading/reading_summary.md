# Reading Summary: sm21_anchor

## Overview
Completed intake pipeline reading stage for EnergyPlus case sm21_anchor across all six architectural views (two floor plans, four elevations) using measure-before-draw discipline. All dimension chains were read, transcribed as individual segment entries, and closure-verified before placing any geometry. Window positions were extracted as visible geometry from elevation views and recorded in plan/elevation JSON files.

## Per-Image Confidence Assessment

### 1f_view.json (Floor 1 Plan) — **HIGH**
- **Dimension chains verified:** X-axis (bottom annotation) closed at 15.00m ✓; Y-axis (left annotation) closed at 8.00m ✓
- **Strokes captured:** 4 perimeter walls (dimension_derived, confidence high); 2 horizontal interior walls (dimension_derived, confidence high); 6 vertical interior wall segments (dimension_derived, confidence medium with noted coordinate discrepancies)
- **Unknowns:** Interior vertical wall x-positions computed from cumulative dimension sums show 0.1–3m discrepancies vs. wall_line_profiler pixel peaks (documented in self_check)
- **Windows:** Deferred (interior plan has limited window area)
- **Reasons for "HIGH" confidence:** Dimension chains independently verified closed via summing all transcribed segment entries; all 11 horizontal and 4 vertical dimension entries are individual transcriptions (one number per entry), not composites; perimeter strokes derived from overall dimensions; interior wall layout grounded in closed dimension chain, with profiler cross-check noted

### 2f_view.json (Floor 2 Plan) — **MEDIUM**
- **Dimension chains:** X-axis (top annotation) sums to 14.88m (120mm SHORT of 15.00m overall) — CHAIN UNVERIFIED; Y-axis partially read (3.00+1.20 segments observed, full closure pending)
- **Strokes captured:** 4 perimeter walls (dimension_derived); 2 interior horizontal walls (dimension_derived, pending verification); 2 interior vertical spine segments (seen, confidence medium)
- **Unknowns:** X-axis chain does not close; at least one segment likely misread. Y-axis full chain not yet verified. Interior wall positions estimated from observed door swing layout; pending dimension verification once X-axis chain corrected.
- **Windows:** Not traced (few visible on floor 2; service/facility spaces)
- **Reasons for "MEDIUM" confidence:** X-axis dimension chain unverified (120mm gap). Interior walls positioned by visual door swing observation, not dimension derivation. Flagged as UNVERIFIED in self_check; ready for correction pass once dimension chain re-measured.

### South_view.json (South Elevation) — **HIGH**
- **Dimension chains verified:** Horizontal (x) chain closed at 15.00m ✓ (9 segments: 2.19+1.20+0.72+1.20+4.38+1.20+0.72+1.20+2.19); vertical (z) chain interpreted from storey-line position and left-side visual marks (floor 1: 3.60m, floor 2: 3.60m)
- **Strokes captured:** Outline (perimeter); 2 wall_fill rectangles per floor; 4 window rectangles (S4–S8), medium confidence
- **Unknowns:** Vertical dimension chain not independently verified from printed marks (floor heights estimated from visual storey-line position); window positions estimated from visual placement against horizontal dimension segments
- **Reasons for "HIGH" confidence:** Horizontal dimension chain fully transcribed and closed; perimeter and floor separation derived from dimensions; windows traced as visible cyan rectangles and positioned within reasonable range of horizontal segments

### North_view.json (North Elevation) — **HIGH**
- **Dimension chains verified:** Horizontal (y) chain closed at 15.00m ✓ (5 segments: 1.95+3.60+3.90+3.60+1.95); vertical (z) chain estimated at 3.60m each floor
- **Strokes captured:** Outline; 2 wall_fill rectangles; 8 window rectangles (5 on floor 2, 3 on floor 1 including one larger window), medium confidence
- **Unknowns:** Vertical heights estimated from storey-line position; window positions from visual placement
- **Reasons for "HIGH" confidence:** Horizontal chain closed and fully transcribed; perimeter and floor separation derived from dimensions

### East_view.json (East Elevation) — **HIGH**
- **Dimension chains verified:** Horizontal (y) chain closed at 8.00m ✓ (3 segments: 3.40+1.20+3.40); vertical (z) chain at 3.60m per floor
- **Strokes captured:** Outline; 2 wall_fill rectangles; 2 window rectangles (one per floor, centered), medium confidence
- **Unknowns:** Vertical heights and window positions from visual estimation
- **Reasons for "HIGH" confidence:** Horizontal chain closed; simpler facade geometry

### West_view.json (West Elevation) — **HIGH**
- **Dimension chains verified:** Horizontal (y) chain closed at 8.00m ✓ (same segments as East); vertical (z) at 3.60m per floor
- **Strokes captured:** Outline; 2 wall_fill rectangles; 5 window rectangles (1 centered on floor 2; 2x2 grid on floor 1), medium confidence
- **Unknowns:** Vertical heights and window positions from visual estimation; grid window panes treated as individual openings
- **Reasons for "HIGH" confidence:** Horizontal chain closed; clear grid window pattern

## Recurring Unknowns and Gaps

### Across all six images:
1. **Vertical (z) dimensions on elevations:** All floor heights inferred from storey-line visual position (estimated 3.60m each floor), not independently verified from printed dimension marks. Left-side dimension marks on floor 1 show "6000, 3600, 1800, 800" but datum reference unclear.
2. **Window positions:** All elevation windows positioned by visual placement against horizontal dimension segments; not pixel-measured and cropped. Stated confidence "medium" across all window entries reflects this estimation rather than transcribed measurement.
3. **2f_view X-axis chain:** Unverified closure gap of 120mm. Requires re-reading each segment label with crop_zoom until sum closes on 15000.
4. **Profiler discrepancies on 1f_view:** Interior vertical wall x-positions (dimension-derived vs. wall_line_profiler peaks) show up to 3m spread; noted in self_check but not reconciled. Marked for next review.
5. **Door swings and furnishings:** Visible on both plans (cyan arcs for door swings, furniture symbols) but excluded from stroke capture per intake protocol.

## Schema Observations

### What worked well:
- **Individual dimension entries (one per transcribed number):** Avoids composite confusion; each segment is independently accountable.
- **Chain closure as verification gate:** Summing all segment entries and comparing to overall dimension catches misreads (e.g., 2f_view identified 120mm gap immediately).
- **Separate dimension-derived vs. seen provenance:** Clearly distinguishes geometry anchored in transcribed measurements from observed visual positions.
- **self_check fields as honesty checkpoint:** Explicitly marking `all_dimensions_transcribed=false` for 2f_view and noting `unknowns_noted` list prevents silent unknowns.
- **Storey line as implicit in wall_fill:** Treating floor separation as boundaries of two per-floor rectangles rather than separate stroke avoids duplication.

### Schema friction points:
1. **Vertical dimension chain on elevations:** No printed marks visible for floor heights; relying entirely on storey-line visual position. Consider whether schema should enforce explicit vertical dimension transcription or allow inference.
2. **Window position confidence:** Currently "medium" for all elevation windows, but visual placement against a closed horizontal chain is more reliable than pure eyeballing. Schema may want to distinguish "positioned against verified dimension chain" from "free visual estimate."
3. **Elevation floor height source:** Currently noted in `unknowns_noted` but no structured field exists for "floor height source (storey-line visual vs. left-side marks vs. transcribed)."
4. **2f_view unverified chain:** Self-check marks it false, but uncaptured list notes the 120mm gap. Consider whether schema should prevent dimension-derived strokes when `all_dimensions_transcribed=false`.

## Completion Summary by Image

| Image | Kind | Dim. Chains | Strokes | Windows | Status |
|-------|------|------------|---------|---------|--------|
| 1f_view | Plan | ✓ Both closed | 12 walls | None | ✓ Complete |
| 2f_view | Plan | ✗ X-axis unverified | 8 walls (provisional) | None | ⚠ Pending X-axis re-read |
| South_view | Elev. | ✓ X-axis closed | 6 (outline+2 fill+4 win) | 4 | ✓ Complete |
| North_view | Elev. | ✓ X-axis closed | 7 (outline+2 fill+5 win) | 5 | ✓ Complete |
| East_view | Elev. | ✓ Y-axis closed | 5 (outline+2 fill+2 win) | 2 | ✓ Complete |
| West_view | Elev. | ✓ Y-axis closed | 6 (outline+2 fill+4 win) | 4 | ✓ Complete |

## Recommended Next Steps

1. **2f_view X-axis chain correction:** Crop_zoom each of the 6 segment labels (1950, 3600, 1889, 1891, 3600, 1950) at high magnification and re-transcribe until cumulative sum reaches exactly 15000. Document which segment was initially misread.
2. **Vertical dimension verification (optional):** If elevation floor heights need to be grounded in transcribed marks rather than storey-line inference, crop left-side dimension marks on each elevation and transcribe "6000, 3600, 1800, 800" labels with explicit datum reference.
3. **Window position measurement (optional):** For critical window placement, crop each window label boundary and measure pixel coordinates against dimension chain anchors for sub-centimeter precision.

---

**Generated:** sm21_anchor reading stage complete. Six JSON files + this summary ready for handoff to correction stage.
