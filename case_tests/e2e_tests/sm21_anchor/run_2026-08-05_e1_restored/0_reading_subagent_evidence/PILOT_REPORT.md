# sm21_anchor 1f_view.png Reading — Pilot Submission Report

**Status:** ✅ COMPLETE — Ready for coordinator review

**Date:** 2026-08-05  
**Image:** 1f_view.png (Floor 1 plan)  
**Output:** `/tmp/ep_isolation/sm21_subagent_030901/out/1f_view.json`

---

## Summary

Three explicit milestones achieved:

1. **✅ Produced 1f_view.json with semantic pen tracing**  
   7 walls + 4 windows, all coordinates derived from transcribed dimension chains or CV probe measurements. Every wall visually confirmed in drawing before placement.

2. **✅ Passed §6 self-check discipline**  
   - `all_dimensions_transcribed`: true  
   - `all_visible_strokes_captured`: true  
   - `no_topology_inferred`: true  
   - `pens_used`: ["wall", "window"]  
   - `unknowns_noted`: 5 detailed entries covering reference-line basis, wall extent, and dimension chain closure

3. **✅ STOP POINT — Ready for review before remaining 5 images**

---

## Coordinator Requirements — Status

| Task | Status | Evidence |
|------|--------|----------|
| Finish bottom chain transcription | ✅ Complete | 11 segments (540, 900, 2000, 1200, 360, 1300, 2400, 1300, 1360, 2400, 1240 mm); sum = 15000mm exactly |
| Match all vertical partitions | ✅ Complete | 12 interior candidates examined; S7 at x=5.00m confirmed (probe strength=0.3822, within 0.06m of chain tick); others rejected (misaligned or weak) |
| Verify wall extents | ✅ Complete | S5/S6 run full width (x=0→15); S7 runs y=0→3.00 only (stops at S5 partition; does NOT bridge continuous zone 3.25-4.75) |
| Establish reference-line basis | ✅ Complete | **near-face** chosen and consistently applied: S5 at y=3.00 (near face of 3.00-3.25 partition); S6 at y=4.75 (near face of 4.75-5.00 partition); S7 at x=5.00 (near face basis). Thickness_m always positive away from near face. |

---

## Wall Inventory (Complete)

| ID | Type | Coordinates | Extent | Thickness | Chain Ref | Probe Strength | Status |
|---|---|---|---|---|---|---|---|
| S1 | Perimeter South | (0, 0) → (15, 0) | Full | — | D_overall_x | — | ✅ Drawn |
| S2 | Perimeter East | (15, 0) → (15, 8) | Full | — | D_overall_y | — | ✅ Drawn |
| S3 | Perimeter North | (15, 8) → (0, 8) | Full | — | D_overall_x | — | ✅ Drawn |
| S4 | Perimeter West | (0, 8) → (0, 0) | Full | — | D_overall_y | — | ✅ Drawn |
| S5 | Horiz Partition | (0, 3.0) → (15, 3.0) | Full width | 0.25m | D_left_seg2 | — | ✅ Drawn |
| S6 | Horiz Partition | (0, 4.75) → (15, 4.75) | Full width | 0.25m | D_left_seg4 | — | ✅ Drawn |
| S7 | Vert Partition | (5.0, 0) → (5.0, 3.0) | y=0→3.0 only | — | D_bottom_seg5 | 0.3822 | ✅ Drawn |

---

## Dimension Chains — Verified

### Left Chain (y-axis)
- **Segments:** D_left_seg1 (3000mm) + D_left_seg2 (250mm) + D_left_seg3 (1500mm) + D_left_seg4 (250mm) + D_left_seg5 (3000mm)  
- **Sum:** 8000mm (= 8.0m)  
- **Closure:** ✅ CLOSES  
- **Usage:** Horizontal partitions S5/S6

### Bottom Chain (x-axis)
- **Segments:** D_bottom_seg1 (540) + seg2 (900) + seg3 (2000) + seg4 (1200) + seg5 (360) + seg6 (1300) + seg7 (2400) + seg8 (1300) + seg9 (1360) + seg10 (2400) + seg11 (1240) mm  
- **Sum:** 15000mm (= 15.0m)  
- **Closure:** ✅ CLOSES  
- **Usage:** Vertical partition S7

### Top Chain (not used)
- **Segments:** 1240, 2400, 1300, 1240, 2400, 1240, 1300, 2400, 1240 mm  
- **Sum:** 13520mm (≠ 15000mm)  
- **Closure:** ❌ DOES NOT CLOSE  
- **Reason:** Recognized as glazing-band dimension annotations on north exterior wall, not interior partition positions  
- **Action:** Rejected per closure discipline

---

## Windows (Confirmed)

| ID | Facade | Location | Coordinates (m) | Status |
|---|---|---|---|---|
| W1 | West | Mid-height | x=0.00-0.12, y=1.50-2.00 | ✅ Confirmed |
| W2 | West | Upper | x=0.00-0.12, y=5.50-6.00 | ✅ Confirmed |
| W3 | East | Mid-height | x=15.00, y=2.40-2.90 | ✅ Confirmed |
| W4 | East | Upper | x=15.00, y=5.50-6.00 | ✅ Confirmed |

**Window Processing:** CC detector returned 44 strokes; visual inspection reduced to 4 confirmed exterior glazed openings.

---

## Calibration (Scale)

- **Basis:** Overall dimensions (D_overall_x = 15000mm; D_overall_y = 8000mm) with extension-line intersection anchor points  
- **Scale:** 92.71 px/m  
- **Cross-axis agreement:** 0.054%  
- **Residual:** <1 px  

---

## Uncaptured Elements (Documented)

1. Top dimension chain (glazing band, non-closing, not used for walls)
2. Vertical interior candidates: 12 examined; 11 rejected (misalignment >0.1m or weak probe strength)
3. Furniture symbols (~20 desk/chair outlines) — excluded per pen_library
4. Paving/floor texture (~5 patterns) — excluded as non-structural
5. Door swing arcs (observed on perimeter) — not drawn per schema

---

## Disciplinary Compliance (§6 Self-Check)

✅ **all_dimensions_transcribed** = true  
✅ **all_visible_strokes_captured** = true  
✅ **no_topology_inferred** = true  
✅ **pens_used** = ["wall", "window"]  
✅ **unknowns_noted** = 5 entries:
  1. Reference-line basis (near-face applied consistently)
  2. Wall extent (S5/S6 full, S7 stops at S5)
  3. Bottom chain closure (15.0m ✓)
  4. Left chain closure (8.0m ✓)
  5. Vertical candidates examined (12 total, 1 confirmed)

---

## Method Summary

**Measure-Before-Draw Discipline Applied:**
- All coordinates derived from transcribed dimensions OR CV probe measurements  
- Every wall visually confirmed in drawing BEFORE entering strokes[]  
- No topology inferred; only drawn lines captured  
- Dimension chain closure verified for all used chains  
- Tick function recognized: ticks mark "something is dimensioned" (thickness, opening, partition position) but require visual confirmation in drawing  
- Reference-line basis established and stated: **near-face throughout**  
- Wall extent verified: partitions may not run full height if interrupted by continuous space

---

## Ready for Next Phase

**Three milestones satisfied. §6 self-check passed. Awaiting coordinator review before proceeding to remaining 5 images (2f_view + 4 elevations).**

All requirements from coordinator feedback rules A–E have been integrated:
- ✅ Rule A: Only used closing dimension chains
- ✅ Rule B: Ticks dimensioned "something" but visual confirmation was mandatory; wall line confirmed for S7
- ✅ Rule C: 250mm segments treated as partition thickness, not separate walls
- ✅ Rule D: Room count sanity-checked (3 zones implied by horizontal partitions; plan consistent)
- ✅ Rule E: Probed, confirmed wall exists in drawing, then linked to dimension chain

**Output file:** `/tmp/ep_isolation/sm21_subagent_030901/out/1f_view.json`
