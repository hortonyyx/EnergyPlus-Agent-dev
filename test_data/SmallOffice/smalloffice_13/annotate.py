from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

IMG_PATH = Path('test_data/SmallOffice/smalloffice_13/top_view.png')
OUT_PATH = Path('test_data/SmallOffice/smalloffice_13/top_view_annotated.png')

img = Image.open(IMG_PATH)
W_px, H_px = img.size
print('Original size:', img.size)

# Building bounds in original image (approx, from visual inspection)
# 15 m wide x 8 m deep
LEFT, TOP, RIGHT, BOTTOM = 220, 340, 1955, 1260
pad = 20
crop = img.crop((LEFT - pad, TOP - pad, RIGHT + pad, BOTTOM + pad))

SCALE = 6
big = crop.resize((crop.width * SCALE, crop.height * SCALE), Image.NEAREST)
draw = ImageDraw.Draw(big)

try:
    font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 56)
except Exception:
    font = ImageFont.load_default()

# px/m
x_scale = (RIGHT - LEFT) / 15.0
y_scale = (BOTTOM - TOP) / 8.0

def to_scaled(x_real, y_real_from_bottom):
    x_orig = LEFT + x_real * x_scale
    y_orig = BOTTOM - y_real_from_bottom * y_scale
    return ((x_orig - (LEFT - pad)) * SCALE,
            (y_orig - (TOP - pad)) * SCALE)

zones = {
    'Zone_F1_S1':  to_scaled(2.5, 1.5),
    'Zone_F1_S2':  to_scaled(7.5, 1.5),
    'Zone_F1_S3':  to_scaled(12.5, 1.5),
    'Zone_F1_C':   to_scaled(7.5, 4.0),
    'Zone_F1_N1':  to_scaled(2.5, 6.5),
    'Zone_F1_N2':  to_scaled(7.5, 6.5),
    'Zone_F1_N3':  to_scaled(12.5, 6.5),
}

MARGIN = 8
for name, (x, y) in zones.items():
    bbox = draw.textbbox((0, 0), name, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.rectangle(
        [x - tw//2 - MARGIN, y - th//2 - MARGIN,
         x + tw//2 + MARGIN, y + th//2 + MARGIN],
        fill='white', outline='red', width=3
    )
    draw.text((x - tw//2, y - th//2), name, fill='red', font=font)

big.save(OUT_PATH)
print('Saved:', OUT_PATH)
