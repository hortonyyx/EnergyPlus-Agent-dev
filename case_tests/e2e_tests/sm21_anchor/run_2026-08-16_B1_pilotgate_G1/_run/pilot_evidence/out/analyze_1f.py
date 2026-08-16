"""Analyze 1f_view.png to find pixel coordinates of key features"""
import numpy as np
from PIL import Image
from scipy import ndimage

# Load the image
img = Image.open('case_data/1f_view.png')
img_array = np.array(img.convert('RGB'))

# Convert to grayscale
img_gray = np.array(img.convert('L'))

# Find bright green pixels (dimension marks are bright green: RGB ~0,255,0)
green_channel = img_array[:,:,1]
red_channel = img_array[:,:,0]
blue_channel = img_array[:,:,2]

# Green pixels have high G, low R, low B
green_mask = (green_channel > 200) & (red_channel < 100) & (blue_channel < 100)

# Find connected components of green pixels
labeled, num_features = ndimage.label(green_mask)
print(f"Found {num_features} green regions")

# Find bounding boxes of each region
for i in range(1, min(num_features + 1, 20)):  # Check first 20
    points = np.where(labeled == i)
    if len(points[0]) > 5:  # Only consider regions with >5 pixels
        min_y, min_x = np.min(points[0]), np.min(points[1])
        max_y, max_x = np.max(points[0]), np.max(points[1])
        center_y = (min_y + max_y) / 2
        center_x = (min_x + max_x) / 2
        area = len(points[0])
        print(f"Region {i}: bbox=({min_x},{min_y})-({max_x},{max_y}), center=({center_x:.0f},{center_y:.0f}), area={area}")
