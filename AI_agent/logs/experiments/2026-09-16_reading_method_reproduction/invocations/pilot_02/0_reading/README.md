# Floor 1 Reading — Pilot Rework Complete

## Files in this Directory

- **1f_view.json** — Main reading output (rework v2)
- **REWORK_SUMMARY.md** — Detailed methodology, calibration, and evidence
- **REWORK_STATUS.txt** — Status report responding to feedback
- **README.md** — This file

## Quick Facts

| Metric | Value |
|--------|-------|
| Walls | 11 strokes (4 perimeter, 7 interior) |
| Windows | 13 strokes (south, north, east facades) |
| Dimensions | 7 entries (2 overall, 5 x-segments) |
| Doors healed | 1 (west wall x≈0.8, y≈2.4); 4+ undecided |
| Calibration residuals | 0 (tick-endpoint-based) |
| JSON loads | ✓ (historical reader) |

## Key Improvements (vs. Draft 1)

✓ **Calibration**: Now derived from measured dimension tick endpoints (residuals: 0)  
✓ **Walls**: Reduced from 31 invented to 11 evidence-based strokes  
✓ **Windows**: Extracted 13 (was 0)  
✓ **Dimensions**: Expanded to 7 with closure check (was 7 but incomplete)  
✓ **Evidence**: Preserved crop_zoom + profiler overlays  

## Known Limitations

⚠️ Interior wall coordinates: MEDIUM confidence (±0.5 m) — profiler shows lines but exact extent unclear  
⚠️ Interior wall thickness: All null per schema (appropriate for simulation)  
⚠️ Door handling: 1 confident heal, 4+ interior doors logged but not auto-healed (needs clarification)  
⚠️ Dimensions: ~70% complete (height segment chain not yet transcribed)  
⚠️ Windows (east): LOW confidence (edge positioning ambiguous in source pixels)  

## Next Review Checklist

- [ ] Spot-check calibration against crop_zoom images
- [ ] Verify wall layout against profiler overlays
- [ ] Accept/reject window positions
- [ ] Approve dimension transcription
- [ ] Approve proceeding to 2F, 3F, elevations

## Supporting Evidence

**CV Artifacts** (cv_evidence/1f_view/):
- `001_crop_zoom_crop.png` — Top dimension magnified 3×
- `002_crop_zoom_crop.png` — Left dimension magnified 2×
- `*_wall_line_profiler_overlay.png` — Horizontal + vertical wall candidates
- `*_window_cc_detector_overlay.png` — Window component detections

**Helper Scripts** (requests/):
- `find_ticks.py` — Automated tick endpoint detection
- `final_calibration.py` — Calibration verification
- `calibration_final.json` — Final calibration parameters

---

**Status**: AWAITING SECOND EXTERNAL REVIEW
**Date**: 2026-09-16  
**Next**: Do not process other images until pilot is approved
