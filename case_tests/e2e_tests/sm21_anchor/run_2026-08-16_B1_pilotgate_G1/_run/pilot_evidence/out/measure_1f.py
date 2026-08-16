"""Measure calibration anchors for 1f_view.png"""
import numpy as np
from PIL import Image

# Load the image
img = Image.open('case_data/1f_view.png')
img_array = np.array(img)

print(f"Image shape: {img_array.shape}")
print(f"Image size: {img.size} (width x height)")

# The top-right green dimension tick for the 15000 dimension is around:
# Looking at the image, the left tick of the top "15000" dimension line is around x≈289px
# The right tick is around x≈1257px in original coords
# This spans 968 pixels for 15000mm = 15.0m

# For vertical: the left side shows 8000mm total height
# Top tick is around y≈212px, bottom tick around y≈1276px in original coords
# This spans 1064 pixels for 8000mm = 8.0m

px_to_m_x = (1257 - 289) / 15.0  # pixels per meter
px_to_m_y = (1276 - 212) / 8.0   # pixels per meter

print(f"\nCalibration:")
print(f"X scale: {px_to_m_x:.2f} px/m ({(1257-289)} px / 15.0 m)")
print(f"Y scale: {px_to_m_y:.2f} px/m ({(1276-212)} px / 8.0 m)")
print(f"Average scale: {(px_to_m_x + px_to_m_y)/2:.2f} px/m")
