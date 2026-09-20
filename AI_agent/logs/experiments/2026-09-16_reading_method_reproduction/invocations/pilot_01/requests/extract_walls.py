#!/usr/bin/env python3
"""Extract wall positions from the floor plan by analyzing black pixels."""

from PIL import Image
import numpy as np
from scipy import ndimage
import json

# Load image and calibration
img = Image.open('case_data/1f_view.png').convert('RGB')
pixels = np.array(img)

# Calibration from px_m_calibrator
PX_PER_M = 53.38
PX_ORIGIN_X = 57  # green mark at x=57 is the left reference
PX_ORIGIN_Y = 1049  # green mark at y=1049 is the bottom reference (y increases downward in image)

def px_to_m(px_x, px_y):
    """Convert pixel coordinates to meters using calibration."""
    m_x = (px_x - PX_ORIGIN_X) / PX_PER_M
    m_y = (PX_ORIGIN_Y - px_y) / PX_PER_M  # Flip Y for meter coordinates (up is positive)
    return m_x, m_y

def round_m(value):
    """Round to 2 decimal places."""
    return round(value, 2)

# Find black pixels (walls)
black_mask = (pixels[:,:,0] < 50) & (pixels[:,:,1] < 50) & (pixels[:,:,2] < 50)

# Label connected components of black pixels
labeled, num_features = ndimage.label(black_mask)
print(f"Found {num_features} black connected components")

# Analyze each component
components = []
for i in range(1, min(num_features + 1, 50)):  # Limit to first 50 components
    component_mask = labeled == i
    component_pixels = np.where(component_mask)

    if len(component_pixels[0]) < 10:  # Skip tiny noise
        continue

    y_min, y_max = component_pixels[0].min(), component_pixels[0].max()
    x_min, x_max = component_pixels[1].min(), component_pixels[1].max()

    width_px = x_max - x_min
    height_px = y_max - y_min
    pixel_count = len(component_pixels[0])

    components.append({
        'index': i,
        'bbox_px': [x_min, y_min, x_max, y_max],
        'width_px': width_px,
        'height_px': height_px,
        'pixel_count': pixel_count,
        'aspect_ratio': width_px / max(height_px, 1)
    })

# Sort by pixel count
components.sort(key=lambda c: c['pixel_count'], reverse=True)

print("\nLargest black components (potential walls/outlines):")
for c in components[:15]:
    x0, y0, x1, y1 = c['bbox_px']
    m_x0, m_y0 = px_to_m(x0, y1)  # bottom-left corner
    m_x1, m_y1 = px_to_m(x1, y0)  # top-right corner
    print(f"  {c['index']:3d}: {c['pixel_count']:5d} px | {c['width_px']:3d}×{c['height_px']:3d} px | "
          f"aspect={c['aspect_ratio']:.2f} | "
          f"({m_x0:.2f},{m_y0:.2f}) to ({m_x1:.2f},{m_y1:.2f}) m")

# Find major walls (very long thin components or large solid areas)
print("\n\nWall candidates (sorted by likely importance):")

# Horizontal walls (high aspect ratio > 3)
horiz_walls = [c for c in components if c['aspect_ratio'] > 2 and c['height_px'] < 20]
print(f"\nHorizontal walls (aspect > 2, height < 20 px): {len(horiz_walls)}")
for c in horiz_walls[:10]:
    x0, y0, x1, y1 = c['bbox_px']
    m_x0, m_y0 = px_to_m(x0, (y0 + y1) // 2)
    m_x1, m_y1 = px_to_m(x1, (y0 + y1) // 2)
    length_m = ((m_x1 - m_x0) ** 2) ** 0.5
    print(f"  {c['index']:3d}: y≈{(y0+y1)//2}, length={length_m:.2f}m ({m_x0:.2f},{m_y0:.2f}) to ({m_x1:.2f},{m_y1:.2f})")

# Vertical walls (low aspect ratio < 0.5)
vert_walls = [c for c in components if c['aspect_ratio'] < 0.5 and c['width_px'] < 20]
print(f"\nVertical walls (aspect < 0.5, width < 20 px): {len(vert_walls)}")
for c in vert_walls[:10]:
    x0, y0, x1, y1 = c['bbox_px']
    m_x0, m_y0 = px_to_m((x0 + x1) // 2, y0)
    m_x1, m_y1 = px_to_m((x0 + x1) // 2, y1)
    length_m = ((m_y1 - m_y0) ** 2) ** 0.5
    print(f"  {c['index']:3d}: x≈{(x0+x1)//2}, length={length_m:.2f}m ({m_x0:.2f},{m_y0:.2f}) to ({m_x1:.2f},{m_y1:.2f})")
