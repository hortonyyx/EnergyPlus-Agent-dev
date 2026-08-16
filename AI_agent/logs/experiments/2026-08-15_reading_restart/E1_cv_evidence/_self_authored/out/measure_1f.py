#!/usr/bin/env python3
"""Helper script to measure building coordinates from the plan image."""
import json
from PIL import Image
import numpy as np

# Constants
IMAGE_PATH = "case_data/1f_view.png"
PX_PER_M = 60.67  # Calibrated scale
ORIGIN_X_PX = 275  # SW corner x in pixels
ORIGIN_Y_PX = 710  # SW corner y in pixels

def px_to_m(px_x, px_y):
    """Convert pixel coordinates to meter coordinates."""
    plan_x = (px_x - ORIGIN_X_PX) / PX_PER_M
    plan_y = (ORIGIN_Y_PX - px_y) / PX_PER_M
    return (plan_x, plan_y)

# Load image to analyze
img = Image.open(IMAGE_PATH).convert("RGB")
img_array = np.array(img)
height, width = img_array.shape[:2]

print(f"Image size: {width}x{height} pixels")
print(f"Calibration: {PX_PER_M} px/m")
print(f"Origin (SW corner): ({ORIGIN_X_PX}, {ORIGIN_Y_PX}) px")
print()

# Expected building outline
print("Expected building outline (15m x 8m):")
print(f"  SW corner: (0, 0) m = ({ORIGIN_X_PX}, {ORIGIN_Y_PX}) px")
print(f"  SE corner: (15, 0) m = ({ORIGIN_X_PX + 15*PX_PER_M:.0f}, {ORIGIN_Y_PX}) px")
print(f"  NW corner: (0, 8) m = ({ORIGIN_X_PX}, {ORIGIN_Y_PX - 8*PX_PER_M:.0f}) px")
print(f"  NE corner: (15, 8) m = ({ORIGIN_X_PX + 15*PX_PER_M:.0f}, {ORIGIN_Y_PX - 8*PX_PER_M:.0f}) px")
print()

# Detect some key points by looking for grayscale (wall color)
# The walls appear as gray (RGB around 120-150)
gray_pixels = ((img_array[:, :, 0] > 100) & (img_array[:, :, 0] < 200) &
               (img_array[:, :, 1] > 100) & (img_array[:, :, 1] < 200) &
               (img_array[:, :, 2] > 100) & (img_array[:, :, 2] < 200))

# Find wall edges by scanning horizontally and vertically
print("Wall line detection (sampling):")
# Check some known rows for vertical walls
for sample_y in [195, 400, 500]:
    row = gray_pixels[sample_y, :]
    wall_columns = np.where(row)[0]
    if len(wall_columns) > 0:
        x_min, x_max = wall_columns[0], wall_columns[-1]
        plan_x_min, plan_y = px_to_m(x_min, sample_y)
        plan_x_max, _ = px_to_m(x_max, sample_y)
        print(f"  Row y_px={sample_y}: walls from x_px={x_min} ({plan_x_min:.2f}m) to x_px={x_max} ({plan_x_max:.2f}m)")

print("\nInner wall coordinates (estimated from visual inspection):")
print("  Horizontal walls at approximately y_plan = 3.0m and y_plan = 5.0m")
print("  Vertical walls at approximately x_plan = 5.0m and x_plan = 10.0m")
