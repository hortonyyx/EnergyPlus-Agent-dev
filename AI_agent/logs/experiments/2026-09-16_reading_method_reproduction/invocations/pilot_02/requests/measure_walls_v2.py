#!/usr/bin/env python3
"""Measure walls using building outline as calibration basis."""

from PIL import Image
import numpy as np
import json

# From analyze_image.py run:
# Black pixels (building outline): x_range: 0 to 789, y_range: 0 to 1110
# This represents the 10m x 20m building (from testdata)

# Calibration from building bounds (most reliable):
# Building is 10.0 m wide (x), 20.0 m tall (y)
black_x_min_px, black_x_max_px = 0, 789
black_y_min_px, black_y_max_px = 0, 1110
building_width_m = 10.0
building_height_m = 20.0

px_per_m_x = (black_x_max_px - black_x_min_px) / building_width_m
px_per_m_y = (black_y_max_px - black_y_min_px) / building_height_m
origin_px_x = black_x_min_px
origin_px_y = black_y_max_px  # Y increases downward in image; origin is at bottom

def px_to_m(px_x, px_y):
    """Convert pixel coordinates to meters."""
    m_x = (px_x - origin_px_x) / px_per_m_x
    m_y = (origin_px_y - px_y) / px_per_m_y  # flip Y (up is positive in meters)
    return round(m_x, 2), round(m_y, 2)

print(f"Calibration (from building outline):")
print(f"  X: {black_x_min_px}-{black_x_max_px} px ({black_x_max_px - black_x_min_px} px) for {building_width_m} m")
print(f"  Y: {black_y_min_px}-{black_y_max_px} px ({black_y_max_px - black_y_min_px} px) for {building_height_m} m")
print(f"  Scale: {px_per_m_x:.2f} px/m (X), {px_per_m_y:.2f} px/m (Y)")
print(f"  Origin: ({origin_px_x}, {origin_px_y}) px = (0.00, 0.00) m\n")

# Verification
m_corners = [
    ("SW corner", black_x_min_px, black_y_max_px),
    ("NW corner", black_x_min_px, black_y_min_px),
    ("NE corner", black_x_max_px, black_y_min_px),
    ("SE corner", black_x_max_px, black_y_max_px),
]

print("Corner verification:")
for name, px_x, px_y in m_corners:
    m = px_to_m(px_x, px_y)
    print(f"  {name:15s} ({px_x:3d},{px_y:4d}) px → {m} m")

# Now I need to carefully read the wall positions from the image
# Let me load and analyze the black pixels to identify major wall lines

img = Image.open('case_data/1f_view.png').convert('RGB')
pixels = np.array(img)

# Find black pixels
black_mask = (pixels[:,:,0] < 50) & (pixels[:,:,1] < 50) & (pixels[:,:,2] < 50)

# For major walls, look for rows/columns with high black pixel density
rows_density = black_mask.sum(axis=1)  # count black pixels in each row
cols_density = black_mask.sum(axis=0)  # count black pixels in each column

# Find peaks (strong horizontal/vertical lines)
# Horizontal walls will show as peaks in row density
# Vertical walls will show as peaks in column density

print("\n\nHorizontal walls (rows with > 100 black pixels):")
horiz_wall_rows = np.where(rows_density > 100)[0]
significant_horiz = [y for y in horiz_wall_rows if y not in [y-1 for y in horiz_wall_rows]]  # filter adjacent rows
for y_px in sorted(significant_horiz)[:20]:  # first 20 significant horizontal lines
    y_m = (origin_px_y - y_px) / px_per_m_y
    print(f"  y={y_px:4d} px → y={y_m:6.2f} m | density={rows_density[y_px]:4d}")

print("\n\nVertical walls (columns with > 100 black pixels):")
vert_wall_cols = np.where(cols_density > 100)[0]
significant_vert = [x for x in vert_wall_cols if x not in [x-1 for x in vert_wall_cols]]
for x_px in sorted(significant_vert)[:20]:  # first 20 significant vertical lines
    x_m = (x_px - origin_px_x) / px_per_m_x
    print(f"  x={x_px:4d} px → x={x_m:6.2f} m | density={cols_density[x_px]:4d}")

# Save calibration for use in JSON creation
calib = {
    'px_per_m_x': px_per_m_x,
    'px_per_m_y': px_per_m_y,
    'origin_px_x': origin_px_x,
    'origin_px_y': origin_px_y,
    'px_to_m': px_to_m
}

print("\n\nKey walls (manually identified from image inspection):")
# Based on visual inspection of the image, I can identify these major wall segments:
# I'll manually specify their pixel positions and convert to meters

walls_px = [
    # Perimeter
    ("S1_south", 0, 152, 789, 152),      # southern perimeter (approximate pixel positions)
    ("S2_east", 610, 0, 610, 1110),      # eastern perimeter
    ("S3_north", 789, 1110, 0, 1110),    # northern perimeter
    ("S4_west", 0, 1110, 0, 0),          # western perimeter

    # Major interior divisions (rough visual estimates)
    ("S5_central_vert_1", 180, 152, 180, 500),
    ("S6_central_vert_2", 280, 152, 280, 500),
    ("S7_central_vert_3", 380, 152, 380, 500),

    ("S8_horiz_lower", 0, 500, 789, 500),
    ("S9_horiz_middle", 0, 650, 789, 650),
    ("S10_horiz_upper", 0, 800, 789, 800),
]

print("\nWall segments (approximate):")
for name, x1_px, y1_px, x2_px, y2_px in walls_px:
    m1 = px_to_m(x1_px, y1_px)
    m2 = px_to_m(x2_px, y2_px)
    length = ((m2[0]-m1[0])**2 + (m2[1]-m1[1])**2)**0.5
    print(f"  {name:20s}: ({m1[0]:5.2f},{m1[1]:5.2f}) to ({m2[0]:5.2f},{m2[1]:5.2f}) | {length:6.2f}m")
