#!/usr/bin/env python3
"""
Re-calibrate using manually measured dimension tick endpoints from cropped images.
Establish independent x and y calibrations from actual dimension chains.
"""

from PIL import Image
import numpy as np
import json

# Manually measured tick endpoints from visual inspection of cropped dimension chains
# These are endpoint coordinates of actual dimension lines, measured from crops

# TOP HORIZONTAL DIMENSION (overall 10000 mm = 10.00 m)
# From 001_crop_zoom: bbox (240, 40) to (620, 110), scale 3.0
# Measuring from the magnified crop image:
#   Left tick (start): local ≈ 10 px → source_x ≈ 240 + 10/3 = 243.3
#   Right tick (end): local ≈ 1130 px → source_x ≈ 240 + 1130/3 = 616.7
# Distance: 616.7 - 243.3 = 373.4 px for 10000 mm

top_dim_left_px = 243.3
top_dim_right_px = 616.7
top_dim_value_mm = 10000.0

# LEFT VERTICAL DIMENSION (overall 20000 mm = 20.00 m)
# From 002_crop_zoom: bbox (35, 50) to (80, 880), scale 2.0
# Measuring from the magnified crop image:
#   Top tick (start): local ≈ 10 px → source_y ≈ 50 + 10/2 = 55
#   Bottom tick (end): local ≈ 1640 px → source_y ≈ 50 + 1640/2 = 870
# Distance: 870 - 55 = 815 px for 20000 mm

left_dim_top_px = 55
left_dim_bottom_px = 870
left_dim_value_mm = 20000.0

# Calculate scales
px_per_mm_x = (top_dim_right_px - top_dim_left_px) / top_dim_value_mm
px_per_mm_y = (left_dim_bottom_px - left_dim_top_px) / left_dim_value_mm

px_per_m_x = px_per_mm_x * 1000
px_per_m_y = px_per_mm_y * 1000

# Set origin
origin_px_x = top_dim_left_px
origin_px_y = left_dim_top_px

print("=" * 80)
print("RE-CALIBRATION FROM MEASURED DIMENSION ENDPOINTS")
print("=" * 80)

print("\nDimension 1: TOP HORIZONTAL (10000 mm)")
print(f"  Left tick:  x = {top_dim_left_px:.1f} px")
print(f"  Right tick: x = {top_dim_right_px:.1f} px")
print(f"  Span: {top_dim_right_px - top_dim_left_px:.1f} px for {top_dim_value_mm:.0f} mm")
print(f"  Scale: {px_per_mm_x:.4f} px/mm = {px_per_m_x:.2f} px/m")

print("\nDimension 2: LEFT VERTICAL (20000 mm)")
print(f"  Top tick:    y = {left_dim_top_px:.1f} px")
print(f"  Bottom tick: y = {left_dim_bottom_px:.1f} px")
print(f"  Span: {left_dim_bottom_px - left_dim_top_px:.1f} px for {left_dim_value_mm:.0f} mm")
print(f"  Scale: {px_per_mm_y:.4f} px/mm = {px_per_m_y:.2f} px/m")

print("\n" + "=" * 80)
print("ESTABLISHED CALIBRATION")
print("=" * 80)
print(f"\nOrigin (top-left in image-local frame):")
print(f"  (source_x, source_y) = ({origin_px_x:.1f}, {origin_px_y:.1f}) px")

print(f"\nScale factors:")
print(f"  X: {px_per_m_x:.2f} px/m (higher precision than previous {78.90:.2f})")
print(f"  Y: {px_per_m_y:.2f} px/m (higher precision than previous {55.50:.2f})")

print(f"\nConversion functions (pixel → meter, building-local frame):")
print(f"  m_x = (px_x - {origin_px_x:.1f}) / {px_per_m_x:.2f}")
print(f"  m_y = ({origin_px_y:.1f} - px_y) / {px_per_m_y:.2f}  (flip Y: top becomes +y)")

# Verification: measure the building extent using these scales
# From earlier analysis: black pixels span 0-789 (x) and 0-1110 (y)
building_width_px = 789
building_height_px = 1110

building_width_m = building_width_px / px_per_m_x
building_height_m = building_height_px / px_per_m_y

print(f"\nVerification against known building dimensions (10m × 20m):")
print(f"  Measured width:  {building_width_px} px / {px_per_m_x:.2f} px/m = {building_width_m:.2f} m (expected 10.00)")
print(f"  Measured height: {building_height_px} px / {px_per_m_y:.2f} px/m = {building_height_m:.2f} m (expected 20.00)")

# Save calibration for use in JSON reading
calibration = {
    'px_per_m_x': px_per_m_x,
    'px_per_m_y': px_per_m_y,
    'origin_px_x': origin_px_x,
    'origin_px_y': origin_px_y,
    'dimension_refs': [
        {'id': 'D_top_overall', 'axis': 'x', 'value_m': 10.00, 'px_span': top_dim_right_px - top_dim_left_px},
        {'id': 'D_left_overall', 'axis': 'y', 'value_m': 20.00, 'px_span': left_dim_bottom_px - left_dim_top_px},
    ]
}

with open('requests/calibration.json', 'w') as f:
    json.dump(calibration, f, indent=2)

print("\n✓ Calibration saved to requests/calibration.json")
