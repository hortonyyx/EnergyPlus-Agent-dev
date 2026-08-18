#!/usr/bin/env python3
"""
Measure wall and window coordinates from 1f_view.png
Using px_per_m = 60.0 calibration
"""

import numpy as np
from PIL import Image, ImageDraw
import json

# Load image
img = Image.open('case_data/1f_view.png')
img_array = np.array(img)
print(f"Image shape: {img_array.shape}")

# Calibration: px_per_m = 60.0
# Origin appears to be at bottom-left of outer perimeter
# Estimate origin pixel coordinates by finding the outer boundary

# The image appears to have the floor plan centered with margins
# Let me find the outer wall boundaries

# Convert to grayscale for analysis
if len(img_array.shape) == 3:
    gray = np.mean(img_array[:,:,:3], axis=2)
else:
    gray = img_array

# Find the bounds of the dark wall area (looking for gray pixels)
# Walls appear as gray/dark pixels
dark_mask = gray < 200  # walls are darker than background

if dark_mask.any():
    rows, cols = np.where(dark_mask)
    min_y, max_y = rows.min(), rows.max()
    min_x, max_x = cols.min(), cols.max()
    print(f"Wall bounds (pixels): x=[{min_x}, {max_x}], y=[{min_y}, {max_y}]")
    print(f"Wall span (pixels): x={max_x - min_x}, y={max_y - min_y}")

    # Expected span at 60 px/m
    # 15m × 8m = 900 px × 480 px
    expected_x_px = 900
    expected_y_px = 480
    print(f"Expected span: x={expected_x_px} px, y={expected_y_px} px")

# Now let me manually identify key wall positions by examining the structure
# Looking at the gray walls (thickness indicates outer vs inner)

# Let me find vertical and horizontal lines by scanning
# This will help identify wall positions

# Look for vertical wall lines by scanning columns
print("\nScanning for vertical walls...")
col_intensity = np.sum((gray < 100), axis=0)  # count dark pixels per column
# Find peaks (columns with many dark pixels = walls)

# Look for horizontal wall lines
print("Scanning for horizontal walls...")
row_intensity = np.sum((gray < 100), axis=1)  # count dark pixels per row

# Show some stats
print(f"\nGray pixel value range: [{gray.min()}, {gray.max()}]")
print(f"Dark pixels (gray < 100): {(gray < 100).sum()}")
print(f"Medium pixels (100 <= gray < 150): {((gray >= 100) & (gray < 150)).sum()}")
print(f"Light pixels (150 <= gray < 200): {((gray >= 150) & (gray < 200)).sum()}")

# Let me look at a horizontal line to find wall positions
# Sample the middle row
mid_row = 450
print(f"\nRow {mid_row} grayscale values (first 100 pixels):")
print(gray[mid_row, :100])

# Find edges by looking for gray lines
# In the image, walls appear to be gray (value ~180)
wall_mask = (gray > 100) & (gray < 200)
print(f"\nWall-colored pixels (100 < gray < 200): {wall_mask.sum()}")

# Cyan/turquoise elements (windows/doors) would have high blue channel
# Let me check the color image
if len(img_array.shape) == 3:
    print(f"\nColor range: R=[{img_array[:,:,0].min()}, {img_array[:,:,0].max()}], "
          f"G=[{img_array[:,:,1].min()}, {img_array[:,:,1].max()}], "
          f"B=[{img_array[:,:,2].min()}, {img_array[:,:,2].max()}]")

    # Find cyan pixels (high G and B, low R)
    cyan_mask = (img_array[:,:,2] > 100) & (img_array[:,:,1] > 100) & (img_array[:,:,0] < 100)
    print(f"Cyan pixels: {cyan_mask.sum()}")

print("\nDone with analysis. Ready to manually identify walls and windows.")
