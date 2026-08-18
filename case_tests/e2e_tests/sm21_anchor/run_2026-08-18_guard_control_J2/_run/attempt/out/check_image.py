from PIL import Image
import json

# Load image to check dimensions
img = Image.open('case_data/1f_view.png')
print(f"Image size: {img.width} x {img.height}")
