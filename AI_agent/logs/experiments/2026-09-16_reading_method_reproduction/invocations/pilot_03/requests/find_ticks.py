#!/usr/bin/env python3
"""Find the exact pixel positions of dimension tick marks in the cropped images."""

from PIL import Image
import numpy as np

# Load the magnified top dimension crop
crop_top = Image.open('0_reading/cv_evidence/1f_view/001_crop_zoom_crop.png')
crop_top_px = np.array(crop_top)

# Find green pixels (the ticks and dimension line)
# Green color typically has high G, low R and B
# Looking for bright green in RGB space
green_mask = (crop_top_px[:,:,1] > 200) & (crop_top_px[:,:,0] < 100) & (crop_top_px[:,:,2] < 100)

print("TOP DIMENSION CROP (magnified 3x):")
print(f"Crop size: {crop_top_px.shape[1]} × {crop_top_px.shape[0]} pixels")

# Find green pixels
green_coords = np.where(green_mask)
if len(green_coords[0]) > 0:
    green_y_min = green_coords[0].min()
    green_y_max = green_coords[0].max()
    green_x_min = green_coords[1].min()
    green_x_max = green_coords[1].max()

    print(f"Green pixels span:")
    print(f"  X: {green_x_min} to {green_x_max} (width = {green_x_max - green_x_min} px)")
    print(f"  Y: {green_y_min} to {green_y_max} (height = {green_y_max - green_y_min} px)")

    # Look at the main horizontal dimension line (highest density of green at a certain y)
    y_density = green_mask.sum(axis=1)
    main_dimension_row = np.argmax(y_density)
    print(f"\nMain dimension line at cropped y = {main_dimension_row}")

    # Find x positions of green pixels on this row (the ticks and marks)
    dimension_line_green = np.where(green_mask[main_dimension_row, :])[0]
    if len(dimension_line_green) > 0:
        print(f"Green marks on dimension line (x coordinates):")
        print(f"  {sorted(set(dimension_line_green))}")

        # Try to find peaks (tick marks are narrow, so gaps indicate segment boundaries)
        # Ticks typically are at: start, after 540, after 1600, after 2520, after 4800, end
        # Calculate expected positions if each segment 540, 1600, 2520, 4800, 540 = 10000
        # spans equal pixel space given the total width

        total_span_px = green_x_max - green_x_min
        segment_values = [540, 1600, 2520, 4800, 540]
        total_mm = sum(segment_values)

        tick_positions_px = [green_x_min]  # Start tick
        cumulative = 0
        for seg in segment_values[:-1]:  # All but the last segment
            cumulative += seg
            pos = green_x_min + (total_span_px * cumulative / total_mm)
            tick_positions_px.append(pos)
        tick_positions_px.append(green_x_max)  # End tick

        print(f"\nPredicted tick positions (in crop-local x):")
        for i, pos in enumerate(tick_positions_px):
            print(f"  Tick {i}: x_crop ≈ {pos:.1f} px")

        # Convert to source image coordinates
        # source_x = 240.0 + local_x / 3.0
        print(f"\nTick positions in SOURCE IMAGE (using crop_zoom inverse: src_x = 240 + crop_x/3):")
        tick_positions_source = []
        for pos in tick_positions_px:
            src_x = 240.0 + pos / 3.0
            tick_positions_source.append(src_x)
            print(f"  crop_x = {pos:.1f} → source_x = {src_x:.1f} px")

        # Calculate scale
        span_source = tick_positions_source[-1] - tick_positions_source[0]
        scale_px_per_mm = span_source / total_mm
        scale_px_per_m = scale_px_per_mm * 1000

        print(f"\nCalibration from TOP DIMENSION:")
        print(f"  Source span: {span_source:.1f} px for {total_mm} mm")
        print(f"  Scale: {scale_px_per_mm:.4f} px/mm = {scale_px_per_m:.2f} px/m")
        print(f"  Origin (left tick): {tick_positions_source[0]:.1f} px")

# Also load and analyze left dimension
print("\n" + "="*80)
print("\nLEFT DIMENSION CROP (magnified 2x):")
crop_left = Image.open('0_reading/cv_evidence/1f_view/002_crop_zoom_crop.png')
crop_left_px = np.array(crop_left)

print(f"Crop size: {crop_left_px.shape[1]} × {crop_left_px.shape[0]} pixels")

# Find green pixels
green_mask_left = (crop_left_px[:,:,1] > 200) & (crop_left_px[:,:,0] < 100) & (crop_left_px[:,:,2] < 100)

green_coords_left = np.where(green_mask_left)
if len(green_coords_left[0]) > 0:
    green_y_min = green_coords_left[0].min()
    green_y_max = green_coords_left[0].max()
    green_x_min = green_coords_left[1].min()
    green_x_max = green_coords_left[1].max()

    print(f"Green pixels span:")
    print(f"  X: {green_x_min} to {green_x_max}")
    print(f"  Y: {green_y_min} to {green_y_max} (height = {green_y_max - green_y_min} px)")

    # The left dimension is vertical
    total_span_py = green_y_max - green_y_min
    total_mm_y = 20000

    # The left dimension likely doesn't have visible segment marks, just overall
    # So we can use the overall tick positions

    print(f"\nLeft dimension overall span: {total_span_py} px for {total_mm_y} mm")
    scale_px_per_mm_y = total_span_py / total_mm_y
    scale_px_per_m_y = scale_px_per_mm_y * 1000

    print(f"Scale: {scale_px_per_mm_y:.4f} px/mm = {scale_px_per_m_y:.2f} px/m")
    print(f"Origin (top tick): y_crop = {green_y_min} → source_y = {35 + green_y_min/2:.1f} px (using bbox 35-80, scale 2)")
