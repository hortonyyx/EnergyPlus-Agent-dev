Warning: no stdin data received in 3s, proceeding without it. If piping from a slow command, redirect stdin explicitly: < /dev/null to skip, or wait longer.
The pilot has been rewritten with proper measurement provenance. Each stroke now cites its CV measurement source (sidecar file, candidate ID), pixel coordinates, and conversion methodology.

## Pilot Summary - Revision 1

**Improvements made:**
1. ✓ **Calibration refined**: 0.65% disagreement (was 28.9%) using precise dimension chain extension line endpoints
   - x: 59.733 px/m (896 px for 15m)
   - y: 60.125 px/m (481 px for 8m) 
   - Source: high-zoom crops of left dimension frame [006, 007 crop_zoom analysis]

2. ✓ **Provenance documented**: Every stroke now includes:
   - Which CV sidecar file (e.g., "wall_line_profiler 002_wall_line_profiler.json")
   - Pixel coordinates (x_px, y_px values)
   - Conversion formula shown explicitly
   - Dimension chain cross-references

3. ✓ **Dimension chains started**: D1-D4 overall dimensions transcribed with proper anchor pixel bboxes

4. ✓ **CV tools used systematically**: 
   - wall_line_profiler (002 file) for vertical walls
   - wall_line_profiler (001 file) for horizontal walls  
   - window_cc_detector (001 file) for window detection
   - crop_zoom (006 file) for calibration verification

5. ✓ **Honest limitations noted**: JSON explicitly documents what's not yet fully measured (segment dimensions, precise window jambs, wall endpoints)

**Status:** The pilot is **ready for review again**. Stopping here as instructed — awaiting feedback before proceeding to remaining images (2f, elevations).
