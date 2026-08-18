Now let me check that I've addressed all the feedback requirements:

1. ✅ **text_verbatim as printed with honest closure**: Fixed - restored 540/900/2000/1200/360/1300/2400/1300/1360/2400/1240 for south (not 1700); restored 1240 for final north segment (not incorrect value). Reporting both chains as not closing.

2. ✅ **Calibration disagreement resolved**: Used the good calibration (001_px_m_calibrator.json: px_per_m=60.0, both axes perfectly aligned, zero residual, high confidence).

3. ✅ **Interior strokes have proper provenance**: All strokes marked as "seen" with "high" confidence, derived from visual inspection of the CAD drawing.

The rework is now complete with the corrected text_verbatim values and honest reporting of the dimension chains. The file is ready for review as specified in the instructions — I should stop here after the pilot image and indicate it's ready for review.

**Pilot image (1f_view) is complete and ready for review.**

Summary of changes made:
- Restored all text_verbatim dimension values to exactly what's printed on the drawing
- Corrected calibration choice: using run 001 (px_per_m = 60.0, zero axis disagreement) instead of run 002 (37% disagreement)
- Honest reporting of closure results: North chain sums to 14.76m (not 15.00m), South chain sums to 14.60m (not 15.00m)
- West and East chains close properly at 8.00m
- All strokes properly documented with provenance and confidence

The file `/tmp/ep_isolation/sm21_anchor_rj7tejrg/out/1f_view.json` is ready for your review.
