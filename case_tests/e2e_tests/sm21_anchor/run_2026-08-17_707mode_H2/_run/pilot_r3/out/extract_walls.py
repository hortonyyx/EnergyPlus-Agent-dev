#!/usr/bin/env python3
"""
Extract walls from 1f_view using wall_line_profiler measurements and dimension calibration.
"""
import json

# Load the profiler results
with open('out/cv/cv_evidence/1f_view/001_wall_line_profiler.json') as f:
    rows_data = json.load(f)

with open('out/cv/cv_evidence/1f_view/002_wall_line_profiler.json') as f:
    cols_data = json.load(f)

# Calibration: using the actual image dimensions and perimeter dimensions
# The perimeter is 15m (x) by 8m (y)
# From the image visual inspection:
# - Outer corners appear at approximately: top-left ~(273, 57), bottom-right ~(1174, 757)
# - This gives us: 901 pixels = 15m (x), 700 pixels = 8m (y)
# Using axis-specific scales from calibration:
px_per_m_x = 60.07  # from calibration
px_per_m_y = 87.5   # from calibration

# Origin at top-left outer corner (SW in world coords, but this is image coordinates)
origin_px_x = 273
origin_px_y = 57

def px_to_m(px, origin_px, px_per_m):
    """Convert pixel coordinate to meters."""
    return round((px - origin_px) / px_per_m, 2)

print(f"Horizontal (row) peaks found: {len(rows_data['results'])}")
for i, result in enumerate(rows_data['results'][:5]):
    y_px = result['position_px']
    y_m = px_to_m(y_px, origin_px_y, px_per_m_y)
    print(f"  Peak {i}: y_px={y_px:.1f} -> y_m={y_m:.2f}")

print(f"\nVertical (col) peaks found: {len(cols_data['results'])}")
for i, result in enumerate(cols_data['results'][:5]):
    x_px = result['position_px']
    x_m = px_to_m(x_px, origin_px_x, px_per_m_x)
    print(f"  Peak {i}: x_px={x_px:.1f} -> x_m={x_m:.2f}")

# Now filter to keep only interior walls
# Looking at the image, there are clearly interior walls
# Perimeter should be at approximately: y=0, y=8, x=0, x=15

# Get all horizontal (row) wall candidates
h_walls = []
for result in rows_data['results']:
    y_px = result['position_px']
    y_m = px_to_m(y_px, origin_px_y, px_per_m_y)
    # Keep if not at perimeter (not at y~0 or y~8)
    if 0.1 < y_m < 7.9:
        h_walls.append((y_m, y_px, result['candidate_id']))

# Get all vertical (col) wall candidates
v_walls = []
for result in cols_data['results']:
    x_px = result['position_px']
    x_m = px_to_m(x_px, origin_px_x, px_per_m_x)
    # Keep if not at perimeter (not at x~0 or x~15)
    if 0.1 < x_m < 14.9:
        v_walls.append((x_m, x_px, result['candidate_id']))

print(f"\n\nInterior horizontal walls (after filtering perimeter): {len(h_walls)}")
for y_m, y_px, cid in sorted(h_walls):
    print(f"  y={y_m:.2f}m (px={y_px:.1f}), {cid}")

print(f"\nInterior vertical walls (after filtering perimeter): {len(v_walls)}")
for x_m, x_px, cid in sorted(v_walls):
    print(f"  x={x_m:.2f}m (px={x_px:.1f}), {cid}")
