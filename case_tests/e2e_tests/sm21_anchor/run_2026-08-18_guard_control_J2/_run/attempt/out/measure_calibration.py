from PIL import Image
import json

# Load image
img = Image.open('case_data/1f_view.png')
img_array = img.convert('RGB')

# Looking at the 1f_view.png, I can identify:
# - Top dimension labeled "15000" (15.0m width)
# - Left dimension labeled segments summing to "8000" (8.0m height)
# - Green tick marks at dimension endpoints

# Visual inspection shows:
# - Top-left corner of green dimension marks: approximately x≈275, y≈65
# - Top-right corner of green dimension marks: approximately x≈1175, y≈65
# - This spans the "15000" dimension = 15.0m
# px_width = 1175 - 275 = 900px for 15.0m
# px_per_m (x-axis) = 900 / 15.0 = 60 px/m

# For Y-axis:
# - Top green mark: approximately y≈65
# - Bottom green mark: approximately y≈740
# - But need to check which dimensions these endpoints represent
# - Left side shows: 3000 + 250 + 1500 + 250 + 3000 = 8000mm = 8.0m
# - If the full height is 8.0m and spans 675px (740-65), then:
# - px_per_m (y-axis) = 675 / 8.0 = 84.375 px/m

# Let me refine: Looking at segment marks in the image:
# Top shows 1240, 2400, 1300, 1240, 2400, 1240, 1300, 2400, 1240
# Sum = 1240+2400+1300+1240+2400+1240+1300+2400+1240 = 15000 (in mm)

# The visible positions need to be refined. Let me estimate based on the layout:
# Using reference from worked_example: grid is 15m x 8m with specific wall positions

# Rough estimates from visual inspection:
x_anchors = [
    {"px_a": 275, "px_b": 1175, "value_m": 15.0, "axis": "x", "dimension_ref": "overall_15000"}
]

y_anchors = [
    {"px_a": 65, "px_b": 740, "value_m": 8.0, "axis": "y", "dimension_ref": "overall_8000"}
]

print("X-axis calibration: 900px for 15.0m = 60 px/m")
print("Y-axis calibration: 675px for 8.0m = 84.375 px/m")
print("\nWill use wall_line_profiler to verify")
