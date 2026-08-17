"""Build the synthetic fixture image used for the substrate sweep exploration."""
from __future__ import annotations

import numpy as np
from PIL import Image

W, H = 1200, 900
GRAY = 128
LINE_HALF = 2  # width 5: [c-2, c+3)

# Vertical lines: confined to y in [50, 650) so their bbox does not reach the
# rectangles' corner (kept away from image edges deliberately, unlike a
# full-bleed line, so a component-detector's bbox stays local).
V_LINES = {"A": 100, "B": 700}
V_Y0, V_Y1 = 50, 650

# Horizontal lines: confined to x in [50, 750).
H_LINES = {"A": 150, "B": 550}
H_X0, H_X1 = 50, 750

# Two small separate rectangles, far from the cross of lines above (gap far
# beyond merge_gap_px default of 2 px) and small enough that their row/col
# projection bump stays under the clean_vector_v1 prominence threshold
# (0.04): row bump (both, same y-range) = (20+20)/1200 = 0.033; col bump
# (each) = 15/900 = 0.017.
RECT_A = (900, 750, 920, 765)   # x0,y0,x1,y1 half-open, 20x15, area 300
RECT_B = (960, 750, 980, 765)   # 20x15, area 300; x-gap from RECT_A = 40px


def build() -> np.ndarray:
    arr = np.full((H, W, 3), 255, dtype=np.uint8)
    for x in V_LINES.values():
        arr[V_Y0:V_Y1, x - LINE_HALF : x + LINE_HALF + 1, :] = GRAY
    for y in H_LINES.values():
        arr[y - LINE_HALF : y + LINE_HALF + 1, H_X0:H_X1, :] = GRAY
    for (x0, y0, x1, y1) in (RECT_A, RECT_B):
        arr[y0:y1, x0:x1, :] = GRAY
    return arr


if __name__ == "__main__":
    arr = build()
    out = "/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/d8fe0051-7002-4586-92bc-937faf7f6a52/scratchpad/synth_probe.png"
    Image.fromarray(arr, mode="RGB").save(out)
    print("wrote", out, arr.shape)
