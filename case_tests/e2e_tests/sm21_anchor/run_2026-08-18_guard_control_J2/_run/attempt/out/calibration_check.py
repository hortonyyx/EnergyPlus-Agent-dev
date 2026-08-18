# Analysis of calibration points based on wall profiler and visible dimensions

# From wall_line_profiler detection:
# Key row positions (y-axis):
# row230: y_px ≈ 230 (top of building)
# row405: y_px ≈ 406 (first horizontal division)
# row518: y_px ≈ 518 (middle area)
# row674: y_px ≈ 674 (bottom of building)

# Key col positions (x-axis):
# col282: x_px ≈ 282 (left side)
# col570: x_px ≈ 570 (first major interior wall)
# col839+: x_px ≈ 839 (more walls)

# Building dimensions:
# Width: 15000mm = 15.0m
# Height: 8000mm = 8.0m

# Estimate scale:
# Based on the major walls spanning from ~282 to ~1108 (838px for 15m)
# px_per_m ≈ 55.9

px_per_m = 55.7

# Assuming col282 is x=0, row230 is y=0
origin_x_px = 282
origin_y_px = 230

# Test: if col570 should be 5m:
x_at_col570 = (570 - origin_x_px) / px_per_m
print(f"col570 (x_px=570) -> {x_at_col570:.2f}m (expected 5m)")

# If row405 should be 3m:
y_at_row405 = (405 - origin_y_px) / px_per_m
print(f"row405 (y_px=405) -> {y_at_row405:.2f}m (expected 3m)")

# If row518 should be around 5m:
y_at_row518 = (518 - origin_y_px) / px_per_m
print(f"row518 (y_px=518) -> {y_at_row518:.2f}m (expected 5m)")

# Right edge should be at x=15m
# If that's around col1108:
x_at_col1108 = (1108 - origin_x_px) / px_per_m
print(f"col1108 (x_px=1108) -> {x_at_col1108:.2f}m (expected 15m)")

# North edge should be at y=8m
# If that's around row674:
y_at_row674 = (674 - origin_y_px) / px_per_m
print(f"row674 (y_px=674) -> {y_at_row674:.2f}m (expected 8m)")
