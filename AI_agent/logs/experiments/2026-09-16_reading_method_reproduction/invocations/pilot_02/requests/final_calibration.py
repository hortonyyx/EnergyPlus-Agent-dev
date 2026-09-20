import json

# Corrected: origin_px_y should be at BOTTOM (south) for building coordinates
# Image y=1595 corresponds to building y=0 (south)
# Image y=134 corresponds to building y=20 (north)

calibration = {
    'px_per_m_x': 36.77,    # 367.7 px / 10.0 m
    'px_per_m_y': 73.05,    # 1461 px / 20.0 m  
    'origin_px_x': 246.0,   # Building (0,0) X in pixels
    'origin_px_y': 1595.0,  # Building (0,0) Y in pixels (at SOUTH/bottom in image)
    'note': 'm_x = (px_x - 246) / 36.77; m_y = (1595 - px_y) / 73.05'
}

def px_to_m(px_x, px_y):
    m_x = (px_x - calibration['origin_px_x']) / calibration['px_per_m_x']
    m_y = (calibration['origin_px_y'] - px_y) / calibration['px_per_m_y']
    return round(m_x, 2), round(m_y, 2)

print("FINAL CALIBRATION (CORRECTED)")
print(json.dumps(calibration, indent=2))

# Test on building corners
print("\nVerification - building corners:")
print(f"  SW (246, 1595): {px_to_m(246, 1595)} m  (expect 0.00, 0.00)")
print(f"  NW (246, 134):  {px_to_m(246, 134)} m   (expect 0.00, 20.00)")
print(f"  NE (614, 134):  {px_to_m(614, 134)} m   (expect 10.00, 20.00)")
print(f"  SE (614, 1595): {px_to_m(614, 1595)} m  (expect 10.00, 0.00)")

with open('requests/calibration_final.json', 'w') as f:
    json.dump(calibration, f, indent=2)
print("\n✓ Saved to calibration_final.json")
