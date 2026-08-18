#!/usr/bin/env python3
"""
Trace 1f_view.png into JSON using CV probe guidance and visual inspection.
Calibration: x_px_per_m=60, y_px_per_m=80, origin_px=(275, 900)
"""
import json

# Calibration parameters (from px_m_calibrator, using per-axis values)
x_px_per_m = 60.0
y_px_per_m = 80.0
origin_x_px = 275.0
origin_y_px = 900.0

def px_to_m(x_px=None, y_px=None):
    """Convert pixel coordinates to meters."""
    result = {}
    if x_px is not None:
        result['x'] = round((x_px - origin_x_px) / x_px_per_m, 2)
    if y_px is not None:
        # y_px increases downward in image, but building y increases upward
        result['y'] = round((origin_y_px - y_px) / y_px_per_m, 2)
    return result

# From visual inspection and dimension chains, identify wall positions
# Horizontal dimension chain at top: 1240, 2400, 1300, 1240, 2400, 1240, 1300, 2400, 1240
# Cumulative: 1240, 3640, 4940, 6180, 8580, 9820, 11120, 13520, 14760, 15000 mm

# Vertical dimension chain on left: 3000, 2250, 2750
# Cumulative: 3000, 5250, 8000 mm (top to bottom)
# Or from bottom: 3000, 2750, 2250
# Cumulative from bottom: 0, 3000, 5750, 8000

# Build walls from visual inspection and CV profiler guidance
strokes = []
stroke_id = 1

# PERIMETER WALLS
# Bottom wall (horizontal) - from CV profiler y_px ≈ 896-900
p1 = px_to_m(x_px=275, y_px=900)
p2 = px_to_m(x_px=1805, y_px=900)
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "seen",
    "confidence": "high",
    "dimension_refs": ["D5"],  # References the 15000 overall dimension
    "geometry": {
        "kind": "line",
        "p1": [p1['x'], p1['y']],
        "p2": [p2['x'], p2['y']],
        "thickness_m": None
    },
    "note": "south perimeter wall (bottom horizontal)"
})
stroke_id += 1

# Right wall (vertical) - from CV profiler x_px ≈ 1805
p1 = px_to_m(x_px=1805, y_px=900)
p2 = px_to_m(x_px=1805, y_px=215)
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "seen",
    "confidence": "high",
    "dimension_refs": ["D13"],  # References the 8000 vertical dimension on right
    "geometry": {
        "kind": "line",
        "p1": [p1['x'], p1['y']],
        "p2": [p2['x'], p2['y']],
        "thickness_m": None
    },
    "note": "east perimeter wall (right vertical)"
})
stroke_id += 1

# Top wall (horizontal) - from CV profiler y_px ≈ 215
p1 = px_to_m(x_px=1805, y_px=215)
p2 = px_to_m(x_px=275, y_px=215)
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "seen",
    "confidence": "high",
    "dimension_refs": ["D1"],  # References the 15000 overall dimension at top
    "geometry": {
        "kind": "line",
        "p1": [p1['x'], p1['y']],
        "p2": [p2['x'], p2['y']],
        "thickness_m": None
    },
    "note": "north perimeter wall (top horizontal)"
})
stroke_id += 1

# Left wall (vertical) - from CV profiler x_px ≈ 275
p1 = px_to_m(x_px=275, y_px=215)
p2 = px_to_m(x_px=275, y_px=900)
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "seen",
    "confidence": "high",
    "dimension_refs": ["D9"],  # References the 8000 vertical dimension on left
    "geometry": {
        "kind": "line",
        "p1": [p1['x'], p1['y']],
        "p2": [p2['x'], p2['y']],
        "thickness_m": None
    },
    "note": "west perimeter wall (left vertical)"
})
stroke_id += 1

# INTERIOR HORIZONTAL WALLS (from visual inspection and wall profiler)
# Lower horizontal interior wall at y_px ≈ 557 (corresponds to 3000 mm from bottom = 3.00 m)
p1 = px_to_m(x_px=275, y_px=557)
p2 = px_to_m(x_px=1805, y_px=557)
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "seen",
    "confidence": "high",
    "dimension_refs": ["D10"],
    "geometry": {
        "kind": "line",
        "p1": [p1['x'], p1['y']],
        "p2": [p2['x'], p2['y']],
        "thickness_m": None
    },
    "note": "interior horizontal wall (lower)"
})
stroke_id += 1

# Upper horizontal interior wall at y_px ≈ 380 (corresponds to 5750 mm from bottom ≈ 5.75 m)
p1 = px_to_m(x_px=275, y_px=378)
p2 = px_to_m(x_px=1805, y_px=378)
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "seen",
    "confidence": "high",
    "dimension_refs": ["D11", "D12"],
    "geometry": {
        "kind": "line",
        "p1": [p1['x'], p1['y']],
        "p2": [p2['x'], p2['y']],
        "thickness_m": None
    },
    "note": "interior horizontal wall (upper)"
})
stroke_id += 1

# INTERIOR VERTICAL WALLS (from visual inspection and dimension chains)
# The dimension chain shows intervals: 1240, 2400, 1300 (repeated pattern)
# In pixels at x_px_per_m=60: 1240mm/60 ≈ 20.67px, 2400mm/60 = 40px, 1300mm/60 ≈ 21.67px

# First interior vertical wall at x ≈ 1.24 m from origin
wall_x = px_to_m(x_px=275+74, y_px=0)['x']  # 1.24 m
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "dimension_derived",
    "confidence": "high",
    "dimension_refs": ["D2"],  # 1240 mm dimension
    "geometry": {
        "kind": "line",
        "p1": [round(wall_x, 2), 0.00],
        "p2": [round(wall_x, 2), 3.00],
        "thickness_m": None
    },
    "note": "interior vertical wall (lower zone, left)"
})
stroke_id += 1

# Second interior vertical wall at x ≈ 3.64 m
wall_x = px_to_m(x_px=275+74+240, y_px=0)['x']  # 1.24 + 2.4 = 3.64 m
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "dimension_derived",
    "confidence": "high",
    "dimension_refs": ["D3"],  # 2400 mm dimension
    "geometry": {
        "kind": "line",
        "p1": [round(wall_x, 2), 0.00],
        "p2": [round(wall_x, 2), 3.00],
        "thickness_m": None
    },
    "note": "interior vertical wall (lower zone, center-left)"
})
stroke_id += 1

# Third interior vertical wall at x ≈ 4.94 m
wall_x = px_to_m(x_px=275+74+240+65, y_px=0)['x']  # 1.24 + 2.4 + 1.3 = 4.94 m
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "dimension_derived",
    "confidence": "high",
    "dimension_refs": ["D4"],  # 1300 mm dimension
    "geometry": {
        "kind": "line",
        "p1": [round(wall_x, 2), 0.00],
        "p2": [round(wall_x, 2), 3.00],
        "thickness_m": None
    },
    "note": "interior vertical wall (lower zone, center)"
})
stroke_id += 1

# Fourth interior vertical wall (repeats pattern)
wall_x = px_to_m(x_px=275+74+240+65+74, y_px=0)['x']  # 1.24 + 2.4 + 1.3 + 1.24 = 6.18 m
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "dimension_derived",
    "confidence": "high",
    "dimension_refs": [],  # No single dimension for this
    "geometry": {
        "kind": "line",
        "p1": [round(wall_x, 2), 0.00],
        "p2": [round(wall_x, 2), 3.00],
        "thickness_m": None
    },
    "note": "interior vertical wall (lower zone, center-right)"
})
stroke_id += 1

# Fifth wall - upper zone left
wall_x = px_to_m(x_px=275+74, y_px=0)['x']  # same as first
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "dimension_derived",
    "confidence": "high",
    "dimension_refs": [],
    "geometry": {
        "kind": "line",
        "p1": [round(wall_x, 2), 5.75],
        "p2": [round(wall_x, 2), 8.00],
        "thickness_m": None
    },
    "note": "interior vertical wall (upper zone, left)"
})
stroke_id += 1

# Sixth wall - upper zone center-left
wall_x = px_to_m(x_px=275+74+240, y_px=0)['x']
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "dimension_derived",
    "confidence": "high",
    "dimension_refs": [],
    "geometry": {
        "kind": "line",
        "p1": [round(wall_x, 2), 5.75],
        "p2": [round(wall_x, 2), 8.00],
        "thickness_m": None
    },
    "note": "interior vertical wall (upper zone, center-left)"
})
stroke_id += 1

# Seventh wall - upper zone center
wall_x = px_to_m(x_px=275+74+240+65, y_px=0)['x']
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "dimension_derived",
    "confidence": "high",
    "dimension_refs": [],
    "geometry": {
        "kind": "line",
        "p1": [round(wall_x, 2), 5.75],
        "p2": [round(wall_x, 2), 8.00],
        "thickness_m": None
    },
    "note": "interior vertical wall (upper zone, center)"
})
stroke_id += 1

# Eighth wall - upper zone center-right
wall_x = px_to_m(x_px=275+74+240+65+74, y_px=0)['x']
strokes.append({
    "id": f"S{stroke_id}",
    "pen": "wall",
    "provenance": "dimension_derived",
    "confidence": "high",
    "dimension_refs": [],
    "geometry": {
        "kind": "line",
        "p1": [round(wall_x, 2), 5.75],
        "p2": [round(wall_x, 2), 8.00],
        "thickness_m": None
    },
    "note": "interior vertical wall (upper zone, center-right)"
})
stroke_id += 1

# Print for verification
print(f"Created {len(strokes)} wall strokes")
for s in strokes:
    print(f"  {s['id']}: {s['geometry']['kind']} from {s['geometry'].get('p1') or s['geometry'].get('x_range_m')}")

