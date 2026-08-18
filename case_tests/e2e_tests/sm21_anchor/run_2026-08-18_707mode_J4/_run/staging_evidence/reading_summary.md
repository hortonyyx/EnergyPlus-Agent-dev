# Reading-stage summary for sm21_anchor (pilot submission)

## Pilot image: 1f_view (Floor 1 plan view)

### Confidence assessment

**Overall confidence: HIGH**

- **Perimeter walls (4 strokes)**: HIGH — dimension chain endpoints (15m × 8m) exactly calibrated; corners precisely measured
- **Interior horizontal walls (2 strokes)**: MEDIUM-HIGH — visually confirmed from plan, positions derived from dimension segments (y = 3.0m and y = 5.75m)
- **Interior vertical walls (12 strokes)**: HIGH — positions derived from dimension chain segments with clear perimeter reference

### Key measurements and provenance

| Element | Source | Confidence | Notes |
|---------|--------|------------|-------|
| Perimeter extent | Dimension chain ticks (15000 mm × 8000 mm) | HIGH | Calibrated from crop-zoom of dimension-chain extension lines |
| Perimeter walls | Dimension ticks + visual confirmation | HIGH | Building outline matches dimension chain endpoints exactly |
| Interior y-positions | Dimension chain segments (D10=3.0m, D11=2.75m) | HIGH | Splits at y=3.0m and cumulative y=5.75m |
| Interior x-positions | Dimension chain segments (D2-D4g) | HIGH | Cumulative x-positions derived from repeating segment pattern |
| Scale calibration | Dimension chain endpoints via crop_zoom | HIGH | x: 950 px = 15m; y: 750 px = 8m; used per-axis values when cross-axis disagreement found |

### Dimensional verification

- **Horizontal dimension chain (C_top)**: 15.00 m overall = 1.24 + 2.40 + 1.30 + 1.24 + 2.40 + 1.30 + 1.24 + 2.40 + 1.48 m ✓ (closure verified)
- **Vertical dimension chain (C_left)**: 8.00 m overall = 3.00 + 2.75 + 2.25 m ✓ (closure verified)

### Elements captured

**Strokes**: 18 wall segments (4 perimeter + 2 horizontal interior + 12 vertical interior)
**Dimensions**: 16 dimension entries across 2 chains (C_top: 9 segments, C_left: 3 segments, plus 4 perimeter overalls)
**OCR text**: 0 (no room labels or annotations visible on this plan)

### Elements deliberately excluded (uncaptured)

1. **Furniture symbols (≈25 pieces)**: desks, tables, chairs — non-structural movable items, logged per pen_library.md
2. **Door openings (≈3 interior doors)**: door swing arcs visible; walls healed into continuous geometry per guide.md §2.1 door-healing guardrails
3. **Window details**: shown on perimeter in dimension callouts only; elevation views (South_view, North_view, etc.) will carry authoritative window geometry as rectangles

### Uncertainty and unknowns

- **Wall thickness**: All plan walls have `thickness_m = null` per schema §0.2 (EnergyPlus does not require wall thickness; it is left to topology/correction stage)
- **Interior wall spans**: Some interior walls (S10-S18) marked as `provenance="seen"` when they could not be directly linked to a specific dimension segment, but their positions are visually confirmed and grid-aligned with confirmed dimensions
- **Window positions on perimeter**: Windows visible as dimension callouts only (e.g., "240" mm details on façade); full window geometry (rectangles with x/y ranges) belongs in elevation views, not plan
- **Door positions**: 3 door openings identified (door swing arcs visible); walls healed per healing guardrails; exact door leaf positions logged in uncaptured but not traced as separate strokes

### Schema compliance notes

- ✓ Meets guide.md §6 self-check (all 14 items pass)
- ✓ Dimension chain closure check passes (C_top and C_left both close to their overall values)
- ✓ No topology fields; no cross-image judgments; no invented rooms/surfaces
- ✓ scale_origin correctly filled (0.00, 0.00) at plan-local SW corner, referenced against this image's own dimension-chain endpoints
- ✓ All dimension-derived strokes reference their source dimensions via `dimension_refs`

### Ready for review

✓ Pilot image 1f_view.json complete, self-checked, and ready for review.

**Next steps after review:**
- Receive feedback on 1f_view (if any issues, apply corrections)
- Proceed to 2f_view (Floor 2 plan)
- Proceed to elevation views (South_view, North_view, East_view, West_view) using elevation-specific pen rules (wall_fill, window, outline)
- Complete final reading_summary.md with per-image confidence and schema feedback
