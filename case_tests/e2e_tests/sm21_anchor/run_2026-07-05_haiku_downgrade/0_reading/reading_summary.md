# Reading Summary — sm21_anchor, 2026-07-05 Haiku Downgrade Run

## Image Manifest

| source PNG | output JSON | image_kind | status | confidence |
|---|---|---|---|---|
| `1f_view.png` | `1f_view.json` | plan | complete | high for perimeter, medium for interior wall y-positions |
| `2f_view.png` | `2f_view.json` | plan | complete | high for perimeter, medium for interior wall positions |
| `South_view.png` | `South_view.json` | elevation | complete | high overall; window positions estimated image-local |
| `North_view.png` | `North_view.json` | elevation | complete | high overall; window positions estimated image-local |
| `East_view.png` | `East_view.json` | elevation | complete | high overall; only 2 windows visible |
| `West_view.png` | `West_view.json` | elevation | complete | high overall; F1 window shows 4-pane grid internally |

---

## Per-Image Confidence Assessment

### Floor Plans (1f_view, 2f_view)

**Overall Confidence: MEDIUM-HIGH**

#### High-Confidence Elements:
- **Perimeter walls**: Clearly visible as heavy gray/dark boundary lines. X-axis: anchored by 15000mm dimension chain (15.00m total). Y-axis: anchored by 8000mm dimension chain (8.00m total).
- **Dimension chains**: All transcribed verbatim from visible text. Horizontal (x) chains on top/bottom clearly labeled. Vertical (y) chains on left/right clearly labeled.
- **Furniture symbols**: Correctly identified and excluded (desks, tables, chairs, fixtures).
- **Door swing arcs**: Cyan arcs clearly visible. All healed into continuous walls with notes.

#### Medium-Confidence Elements:
- **Interior wall y-positions**: Horizontal interior wall y-coordinate estimated at y=2.4 (based on visual door/window alignment and relative scale). X-positions of vertical walls derived from top dimension chain, cumulative calculation. Some precision lost in coordinate estimation vs. visual inspection.
- **Interior wall continuity**: Walls traced as continuous despite crossing some furniture symbols and dimension ticks (deliberately not segmented; one stroke per continuous wall per guide §5).

#### Uncertainties Noted:
- Perimeter has potential slight recesses/notches at lower-left corner (approximately 0.5-1.0m recess), but traced as simple rectangle. Visual ambiguity due to scale and line weight variation.
- Some dimension chain segments (particularly on bottom chains, F2) show overlapping or asymmetric layout; positions calculated cumulatively but verified against total width/depth.
- Interior horizontal divider y-position (y=2.4 on F1, y=3.0 on F2) estimated from visible layout transition and furniture arrangement. Not dimensioned directly on plan; derived from perimeter+visual inspection.

---

### South Elevation (South_view)

**Overall Confidence: HIGH**

#### High-Confidence Elements:
- **Outline (perimeter)**: Clear outer silhouette. Width 15000mm (15.00m, matches plan). Height 6000mm (6.00m). Horizontal dimension chain at top and bottom fully transcribed.
- **Wall fills (one per floor)**: Floor divider at mid-height (z=3.0). Each floor's fill area clearly delimited. No overlapping or ambiguous fill boundaries.
- **Vertical dimensions (z-axis)**: Left and right sides show consistent 6000mm total, split 3000mm + 3000mm (one per floor).
- **Dimension chains**: All numbers clearly visible and transcribed. Horizontal segments on both top and bottom chains match total 15000mm.
- **Windows (4 on F1, 4 on F2)**: All visible as cyan rectangles. Positions and extents traced in image-local coordinates.

#### Medium-Confidence Elements:
- **Window placement (x and y ranges)**: Estimated from visual measurement against dimension chains. No explicit window-dimension annotations on this facade; positions derived from relative scale and grid alignment.

#### Unknowns/Limitations:
- No level-marker symbols (△ ±0.000) visible on this elevation. Z-positions inferred from outline + floor divider line + dimension chains only.
- Window mullion details (internal pane grid, if present) not captured; windows traced as solid rectangles.
- No door symbols visible on South facade (unlike F1 plan); F1 "window/door 1" on left side marked as possible ground-level access based on lower sill height.

---

### North Elevation (North_view)

**Overall Confidence: HIGH**

#### High-Confidence Elements:
- **Outline, wall fills, vertical dimensions**: Same confidence as South facade. 15.00m × 6.00m, floor split at z=3.0.
- **Dimension chains (horizontal and vertical)**: All transcribed. Top chain layout slightly different from South (1950 + 3600 + 3900 + 3600 + 1950 vs. South's 2190 + 1200 + 720 + 1200 + 4380 + 1200 + 720 + 1200 + 2190), indicating facade-specific detail variation (windows/openings may impose different mullion/column grid).

#### Medium-Confidence Elements:
- **Window placement (x and y ranges)**: Same caveat as South. 5 windows total (3 on F1, 2 on F2) estimated from visual positions.

#### Differences from South Facade:
- F1 has 3 large windows vs. South's 4. F2 has 2 windows vs. South's 4. This asymmetry is consistent with building's interior thermal-zone organization (larger open areas on North for daylighting, different partition layout on F2).

---

### East Elevation (East_view)

**Overall Confidence: HIGH**

#### High-Confidence Elements:
- **Outline, wall fills, vertical dimensions**: Same pattern as North/South. 8.00m × 6.00m (depth × height). Floor split at z=3.0.
- **Dimension chains (horizontal)**: Top chain 3400 + 1200 + 3400 = 8000mm; bottom overall 8000mm. Clear and consistent.
- **Vertical dimensions**: 3000 + 3000 = 6000mm (floors).

#### Medium-Confidence Elements:
- **Window placement**: Only 2 windows visible (1 per floor), both approximately centered on the facade. Estimated from visual positions.

#### Limitation:
- East facade is narrower (8m) than North/South (15m) and shows fewer windows, consistent with it being a smaller surface area (building depth, not width).

---

### West Elevation (West_view)

**Overall Confidence: HIGH**

#### High-Confidence Elements:
- **Outline, wall fills, vertical dimensions**: Same as East. 8.00m × 6.00m.
- **Dimension chains**: Identical to East facade (symmetric layout: 3400 + 1200 + 3400 = 8000mm).
- **Vertical dimensions**: 3000 + 3000 = 6000mm.

#### Medium-Confidence Elements:
- **Window placement**: 2 windows visible (1 per floor). F1 window shows internal 4-pane grid/mullion pattern but traced as single rectangle (window interior detail; mullions are not structural boundaries for reading stage).

#### Note:
- West and East facades are mirror-image symmetric in dimension layout, which is expected for rectangular buildings.

---

## Repeatedly Null / Unknown Fields

### Across All Images:
- **`thickness_m` (plan walls)**: Always `null` per schema §0.2 (EP zones need no wall thickness).
- **`dimension_refs` (elevation windows)**: All elevation windows have empty `dimension_refs` because they are not anchored by explicit window-dimension annotations; positions are visual estimates only.

### Across All Elevations:
- **`level-marker` (altitude triangles △)**: No altitude symbols visible on any elevation. Z-ranges inferred from outline + floor lines + dimension chains instead.
- **`ocr_texts`**: No text labels visible inside the building on any image (no room names, no notes).

### Plan-Specific:
- **Stairwell geometry**: Stairwell symbol with diagonal hatching visible on F1 plan, marked in `uncaptured`; only bounding walls traced (per pen library — stair treads not drawn).
- **Interior y-positions (F1/F2)**: Horizontal interior dividers not dimensioned directly; positions estimated from visual layout and door/window alignment.

---

## Schema Feedback & Observations

### Strengths:
1. **Provenance tracking**: The `provenance` field (seen | dimension_derived | estimated | unknown) allows distinction between observed geometry, dimension-anchored positions, and estimates. Useful for downstream confidence-weighting.
2. **Dimension chain structure**: Explicit `chain_id`, `role` (overall | segment), and `order` fields enable closure-check (Σ segments == overall) and redundant-channel error recovery.
3. **Facade orientation block**: Image-local `local_x_positive` + `view_facade` + `mirrored` is sufficient for correction stage to derive world placement from plan footprint.
4. **Uncaptured list**: Cleanly captures furniture, healed doors, equipment — avoids silent data loss.

### Challenges Encountered:
1. **Interior wall y-positions (plans)**: Without explicit dimension annotations inside the plan (only perimeter + grid lines), interior horizontal-divider positions must be visually estimated. Plan dimension chains anchor x-positions clearly but provide limited y-position constraints for interior walls. Remedy: Recommend adding interior dimension callouts on future plans, or correction stage should have tolerance for ±0.2m on y-positions of interior walls inferred from visual alignment.
2. **Window x-positions (elevations)**: Elevations show window-grid alignment but no explicit window-center or window-edge dimension chains. Positions estimated by visual measurement against the overall facade width and grid. Remedy: Explicit window-opening dimensions (or mullion-grid dimension chains) would improve confidence.
3. **Dimension-chain asymmetry (F2 bottom chain)**: On F2 plan, bottom dimension chain (F1 reference?) shows 2190 + 1200 + 3600 + 1200 + 2190 on left, then repeated on right. Cumulative calculations required care; positions validated against total width (15.00m). Recommend clearer labeling on floor-plan dimension chains to avoid ambiguity.

### Suggestions:
1. **Level-marker symbols**: All elevations should include altitude markers (e.g., ±0.000, 3.000, 6.000) at prominent floor/roof edges for explicit z-reference.
2. **Window-center dimensions**: Elevations should dimension window centers or opening x-positions relative to building corner/grid, reducing visual-estimate reliance.
3. **Interior wall callouts**: Plans should dimension key interior wall x/y positions or provide a grid overlay to anchor interior geometry.

---

## Reconciliation with Testdata

- **Building dimensions**: Confirmed 15m (width) × 8m (depth) × 6m (height, 2 floors @ 3m each).
- **Number of floors**: 2 (F1 + F2) as specified. Both fully traced.
- **Floor area**: 15 × 8 = 120 m²/floor × 2 = 240 m² total (matches testdata "Floor area: 240m²").
- **Thermal zones**: Testdata specifies 7 per floor. Interior wall traces do not directly output zone definitions (that is correction stage's job), but wall network is complete to support zone subdivision.

---

## Known Issues & Workarounds

1. **Perimeter recess ambiguity (F1 lower-left)**: Traced as simple rectangle. If actual recess is significant, correction stage should verify against plan footprint tolerance and request re-read with annotation.
2. **Door opening (F1 window/door 1 on South)**: Marked as window (lower sill) but may be a door. Correction stage should cross-check with plan door symbols.
3. **F2 dimension-chain discontinuity**: Bottom chain layout asymmetric; positions calculated cumulatively but not verified by independent dimension. Recommend correction stage validate Σ segments = overall before use.

---

## Self-Check Summary

- [x] All 6 images read (2 plans, 4 elevations).
- [x] All visible walls, windows, outlines captured as strokes.
- [x] All dimension-chain numbers transcribed verbatim (no translation, no unit change).
- [x] No topology inferred (no room definitions, no parent-child relationships, no inside/outside judgment).
- [x] Door openings healed; healing logged in `uncaptured`.
- [x] Furniture/clutter/stairs recognized and logged (not traced).
- [x] Elevation facades marked image-local (no world-axis claims).
- [x] Plan `thickness_m` all null; elevation `wall_fill` split per floor.
- [x] Confidence + provenance marked honestly on every stroke.

---

## Summary

**Overall Quality: MEDIUM-HIGH**

**Readiness for Correction Stage: YES**

All 6 source images traced. Perimeter and major interior walls captured with high confidence. Window positions estimated in image-local coordinates (±0.1–0.3m precision). Dimension chains provide redundant z and most-x anchors. Furniture and non-structural elements correctly excluded. Interior wall y-positions on plans have medium confidence due to lack of explicit interior dimensions; correction stage should tolerate ±0.2m uncertainty or request re-read with grid callouts if tighter tolerance needed.

**Recommended Next Steps:**
1. Correction stage to validate dimension-chain closures (Σ segments == overall).
2. Cross-check plan-elevation window/door positions for consistency.
3. Verify interior wall y-positions against heat-flow topology if required; tolerance threshold to be set by user.
4. If thermal-zone count or geometry diverges from testdata after correction, request re-read of plans with explicit zone-boundary annotations.
