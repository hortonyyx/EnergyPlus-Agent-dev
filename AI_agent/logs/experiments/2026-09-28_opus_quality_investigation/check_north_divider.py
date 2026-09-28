"""Pixel check on the original sm21 2f_view.png: which vertical strokes span the F2 north rooms?

Counts, per original x column, how many rows between the north wall and the corridor
wall (y 360..540) contain light (drawing) ink. A physical divider spans nearly all rows;
furniture strokes do not. Read-only; prints columns with >=60% vertical coverage.
"""
import sys

import numpy as np
from PIL import Image

path = sys.argv[1]
img = np.asarray(Image.open(path).convert("RGB")).astype(int)
y0, y1 = 360, 540
band = img[y0:y1]
light = (band.max(axis=2) > 80) & ((band.max(axis=2) - band.min(axis=2)) < 60)  # neutral (white/grey) ink on black background; excludes green/cyan annotation
coverage = light.mean(axis=0)
hits = [(x, round(float(coverage[x]), 2)) for x in range(400, 1820) if coverage[x] >= 0.6]
print(f"columns with >=60 percent vertical ink coverage between y={y0}..{y1}:")
print(hits)
print("coverage near x=718 (700..740):", [(x, round(float(coverage[x]), 2)) for x in range(700, 741, 4)])
