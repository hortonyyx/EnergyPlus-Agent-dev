#!/usr/bin/env python3
"""Analyze the 1f_view.png image to establish calibration and identify major features."""

from PIL import Image
import numpy as np
import json

# Load image
img_path = 'case_data/1f_view.png'
img = Image.open(img_path).convert('RGB')
pixels = np.array(img)
height, width = pixels.shape[:2]

print(f"Image size: {width} x {height} pixels")

# Analyze colors in the image
# Green: R<150, G>150, B<150
# Black: R<50, G<50, B<50
# White: R>200, G>200, B>200
# Cyan: R<100, G>150, B>150

green_mask = (pixels[:,:,0] < 150) & (pixels[:,:,1] > 150) & (pixels[:,:,2] < 150)
black_mask = (pixels[:,:,0] < 50) & (pixels[:,:,1] < 50) & (pixels[:,:,2] < 50)
cyan_mask = (pixels[:,:,0] < 100) & (pixels[:,:,1] > 150) & (pixels[:,:,2] > 150)
white_mask = (pixels[:,:,0] > 200) & (pixels[:,:,1] > 200) & (pixels[:,:,2] > 200)

green_pixels = np.where(green_mask)
black_pixels = np.where(black_mask)
cyan_pixels = np.where(cyan_mask)
white_pixels = np.where(white_mask)

if len(green_pixels[0]) > 0:
    green_y_min, green_y_max = green_pixels[0].min(), green_pixels[0].max()
    green_x_min, green_x_max = green_pixels[1].min(), green_pixels[1].max()
    print(f"\nGreen pixels (dimensions):")
    print(f"  x range: {green_x_min} to {green_x_max} ({green_x_max - green_x_min} pixels)")
    print(f"  y range: {green_y_min} to {green_y_max} ({green_y_max - green_y_min} pixels)")

if len(black_pixels[0]) > 0:
    black_y_min, black_y_max = black_pixels[0].min(), black_pixels[0].max()
    black_x_min, black_x_max = black_pixels[1].min(), black_pixels[1].max()
    print(f"\nBlack pixels (walls/outline):")
    print(f"  x range: {black_x_min} to {black_x_max} ({black_x_max - black_x_min} pixels)")
    print(f"  y range: {black_y_min} to {black_y_max} ({black_y_max - black_y_min} pixels)")

    # Estimate scale from building dimensions
    # Known: building is 10.0 m (width) x 20.0 m (height)
    building_width_px = black_x_max - black_x_min
    building_height_px = black_y_max - black_y_min

    scale_x = building_width_px / 10.0
    scale_y = building_height_px / 20.0

    print(f"\nEstimated scale:")
    print(f"  X scale: {scale_x:.2f} px/m (from width {building_width_px} px = 10.0 m)")
    print(f"  Y scale: {scale_y:.2f} px/m (from height {building_height_px} px = 20.0 m)")
    print(f"  Average: {(scale_x + scale_y) / 2:.2f} px/m")

if len(cyan_pixels[0]) > 0:
    print(f"\nCyan pixels (doors): {len(cyan_pixels[0])} pixels")

if len(white_pixels[0]) > 0:
    print(f"White pixels (windows/fixtures): {len(white_pixels[0])} pixels")
