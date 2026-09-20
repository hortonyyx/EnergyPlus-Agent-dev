#!/usr/bin/env python3
"""Systematically measure walls using dimension text as ground truth anchors."""

from PIL import Image
import numpy as np

# Load image
img = Image.open('case_data/1f_view.png').convert('RGB')
pixels = np.array(img)
h, w = pixels.shape[:2]

# From visual inspection of dimension text in the image:
# Top dimensions: 540, 1600, 2520, 4800, 540 (segments from left to right, all in mm)
# These cumulate to: 540, 2140, 4660, 9460, 10000 (positions in mm)

# Calibration anchors (pixel positions where dimension ticks are marked)
# Looking at the green dimension marks in the image:
dim_anchors_mm = [0, 540, 2140, 4660, 9460, 10000]  # meter positions in mm

# Find the pixel coordinates of these dimension endpoints
# The dimension marks are marked with green vertical ticks
# By visual inspection of the image:
# - Left edge tick at x≈ 60 px
# - Right edge tick at x≈ 610 px
# - These span 10000 mm

# So the conversion is approximately:
# px 60 → 0 mm, px 610 → 10000 mm
# scale: (610-60) / 10000 = 550 / 10000 = 0.055 px/mm = 55 px/m

# Actually, let's be more careful. Looking at the image, the green ticks are at:
# Left end of top dimension: x≈ 60
# Right end of top dimension: x≈ 610
# This spans 550 px for 10000 mm = 10.0 m
# So: scale_x = 550 / 10000 = 0.055 px/mm = 55.0 px/m

# For y-axis, left dimension shows 20000 mm total
# Top of left dimension: y≈ 95
# Bottom of left dimension: y≈ 875
# This spans 780 px for 20000 mm
# scale_y = 780 / 20000 = 0.039 px/mm = 39.0 px/m

# But these don't match. Let me measure more carefully from the image.

# From px_m_calibrator tool (using green dimension mark spans):
# X: 673 px for 10.0 m → 67.3 px/m, origin at x=57
# Y: 998 px for 20.0 m → 49.9 px/m, origin at y=1049
px_per_m_x = 67.3  # pixels per meter (horizontal)
px_per_m_y = 49.9  # pixels per meter (vertical)
origin_px_x = 57   # pixel x coordinate of 0.00 m
origin_px_y = 1049  # pixel y coordinate of 0.00 m (at bottom, since y increases downward in image)

def px_to_m(px_x, px_y):
    m_x = (px_x - origin_px_x) / px_per_m_x
    m_y = (origin_px_y - px_y) / px_per_m_y  # flip Y
    return round(m_x, 2), round(m_y, 2)

print(f"Calibration: {px_per_m_x:.1f} px/m (X), {px_per_m_y:.1f} px/m (Y)")
print(f"Origin: ({origin_px_x}, {origin_px_y}) pixels = (0.00, 0.00) meters\n")

# Test calibration with known dimensions
print("Verification tests:")
m_top_left = px_to_m(60, 95)
m_top_right = px_to_m(610, 95)
m_bottom_left = px_to_m(60, 875)
m_bottom_right = px_to_m(610, 875)

print(f"  Top-left (60, 95) px → {m_top_left} m")
print(f"  Top-right (610, 95) px → {m_top_right} m")
print(f"  Bottom-left (60, 875) px → {m_bottom_left} m")
print(f"  Bottom-right (610, 875) px → {m_bottom_right} m")

width_check = m_top_right[0] - m_top_left[0]
height_check = m_top_left[1] - m_bottom_left[1]
print(f"\nDimension check:")
print(f"  Width: {width_check:.2f} m (expected 10.00 m)")
print(f"  Height: {height_check:.2f} m (expected 20.00 m)")

# Now manually identify major walls by visual inspection
# I'll read their approximate pixel positions from the image and convert to meters

print("\n\nMajor wall segments (identified by visual inspection):\n")

# The building has these major walls visible:
walls = [
    # Perimeter walls
    ("S1 south perim", 60, 863, 610, 863),      # bottom wall
    ("S2 east perim", 610, 863, 610, 95),       # right wall
    ("S3 north perim", 610, 95, 60, 95),        # top wall
    ("S4 west perim", 60, 95, 60, 863),         # left wall

    # Interior vertical walls (from visual inspection of black lines)
    ("S5 vert left", 132, 863, 132, 488),       # leftmost interior vertical
    ("S6 vert", 184, 863, 184, 488),            # next interior vertical
    ("S7 vert center", 236, 863, 236, 488),     # center interior vertical
    ("S8 vert", 288, 863, 288, 488),            # next interior vertical
    ("S9 vert right-inner", 340, 863, 340, 488), # right-inner interior vertical
    ("S10 vert right", 392, 863, 392, 488),     # rightmost interior vertical

    # Interior horizontal walls (from visual inspection)
    ("S11 horiz lower", 60, 488, 610, 488),    # horizontal wall lower
    ("S12 horiz middle", 60, 325, 610, 325),   # horizontal wall middle
    ("S13 horiz upper", 60, 162, 610, 162),    # horizontal wall upper
]

for name, x1, y1, x2, y2 in walls:
    m1 = px_to_m(x1, y1)
    m2 = px_to_m(x2, y2)
    length = ((m2[0]-m1[0])**2 + (m2[1]-m1[1])**2)**0.5
    print(f"{name:20s}: ({m1[0]:5.2f},{m1[1]:5.2f}) to ({m2[0]:5.2f},{m2[1]:5.2f}) | length={length:.2f}m")
