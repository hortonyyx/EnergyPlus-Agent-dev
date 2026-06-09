"""Render a phase-2a CorrectedGeometry JSON to PNG for visual validation.

phase 2a does NOT emit a drawing — it emits structured geometry primitives
(rectangular room cells + windows + per-floor z + audit). This renders that
abstraction to a plan view (one panel per floor) so the correction result can be
eyeballed: are cells tiling the footprint? did cross-floor axes unify? do windows
sit on the right facade? — the phase-2a analogue of render_vector_to_png.py for
phase 1.

Usage:
    python Tool_scripts/render_corrected_geometry.py <corrected_geometry.json> [--out x.png]

Pure PIL, no other deps (mirrors render_vector_to_png.py).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw

SCALE = 30          # px per metre
MARGIN = 24         # px padding inside each floor panel
GAP = 28            # px between floor panels
HEADER = 46         # px top title bar
FLOOR_TITLE = 18    # px per-floor caption height

ROLE_FILL = {
    "office": "#cfe3f2",
    "corridor": "#fdf0c8",
    "lobby": "#fdf0c8",
    "wc": "#e7d8f0",
    "toilet": "#e7d8f0",
    "stair": "#e0ddd6",
    "shaft": "#e0ddd6",
    "core": "#e0ddd6",
}
DEFAULT_FILL = "#e9e9e9"
CELL_EDGE = "#444444"
FOOTPRINT = "#111111"
WINDOW = "#1f77b4"
GRID = "#dddddd"
TEXT = "#222222"
SUBTLE = "#777777"


def _floor_windows(data: dict, floor_name: str) -> list[dict]:
    return [w for w in (data.get("windows") or []) if w.get("floor") == floor_name]


def render(data: dict) -> Image.Image:
    fx = data.get("footprint_x") or [0, 1]
    fy = data.get("footprint_y") or [0, 1]
    minx, maxx = float(fx[0]), float(fx[1])
    miny, maxy = float(fy[0]), float(fy[1])
    w_m, h_m = maxx - minx, maxy - miny
    floors = data.get("floors") or []
    n = max(1, len(floors))

    panel_w = int(w_m * SCALE) + 2 * MARGIN
    panel_h = int(h_m * SCALE) + 2 * MARGIN
    total_w = panel_w * n + GAP * (n - 1)
    total_h = HEADER + FLOOR_TITLE + panel_h + MARGIN

    img = Image.new("RGB", (max(total_w, 520), total_h), (252, 252, 252))
    d = ImageDraw.Draw(img)

    title = (
        f"phase2a CorrectedGeometry  |  footprint {w_m:g}×{h_m:g} m  |  "
        f"corrections={len(data.get('corrections') or [])} "
        f"conflicts={len(data.get('conflicts') or [])} "
        f"unsupported={len(data.get('unsupported') or [])}"
    )
    d.text((10, 8), title, fill=TEXT)
    d.text((10, 24), "plan view per floor — cells filled by role, windows = blue on facade",
           fill=SUBTLE)

    for i, fl in enumerate(floors):
        ox = i * (panel_w + GAP)
        oy = HEADER + FLOOR_TITLE

        def tx(x: float) -> float:
            return ox + MARGIN + (x - minx) * SCALE

        def ty(y: float) -> float:
            # flip Y so +y (world) points up
            return oy + MARGIN + (maxy - y) * SCALE

        cap = f"{fl.get('name','?')}   z_floor={fl.get('z_floor')} h={fl.get('ceiling_height')}"
        d.text((ox + MARGIN, HEADER), cap, fill=TEXT)

        # 1 m grid
        gx = int(minx)
        while gx <= maxx + 1e-6:
            d.line([(tx(gx), ty(maxy)), (tx(gx), ty(miny))], fill=GRID, width=1)
            gx += 1
        gy = int(miny)
        while gy <= maxy + 1e-6:
            d.line([(tx(minx), ty(gy)), (tx(maxx), ty(gy))], fill=GRID, width=1)
            gy += 1

        # cells
        for c in fl.get("cells") or []:
            cx, cy = c.get("x") or [0, 0], c.get("y") or [0, 0]
            x0, y0, x1, y1 = tx(cx[0]), ty(cy[1]), tx(cx[1]), ty(cy[0])
            fill = ROLE_FILL.get(str(c.get("role", "")).lower(), DEFAULT_FILL)
            d.rectangle([x0, y0, x1, y1], fill=ImageColor.getrgb(fill), outline=CELL_EDGE, width=2)
            label = c.get("id", "")
            d.text((x0 + 4, y0 + 4), str(label), fill=TEXT)
            d.text((x0 + 4, y0 + 16), str(c.get("role", "")), fill=SUBTLE)

        # footprint outline on top
        d.rectangle([tx(minx), ty(maxy), tx(maxx), ty(miny)], outline=FOOTPRINT, width=3)

        # windows on facade edges
        for w in _floor_windows(data, fl.get("name", "")):
            facade = str(w.get("facade", "")).lower()
            span = w.get("span") or [0, 0]
            z = w.get("z") or [0, 0]
            if facade.startswith("n"):
                p = [(tx(span[0]), ty(maxy)), (tx(span[1]), ty(maxy))]
            elif facade.startswith("s"):
                p = [(tx(span[0]), ty(miny)), (tx(span[1]), ty(miny))]
            elif facade.startswith("e"):
                p = [(tx(maxx), ty(span[0])), (tx(maxx), ty(span[1]))]
            else:  # west
                p = [(tx(minx), ty(span[0])), (tx(minx), ty(span[1]))]
            d.line(p, fill=ImageColor.getrgb(WINDOW), width=5)
            mx, my = (p[0][0] + p[1][0]) / 2, (p[0][1] + p[1][1]) / 2
            d.text((mx - 8, my - 10), f"{w.get('id','')} z{z[0]:g}-{z[1]:g}", fill=WINDOW)

    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help="CorrectedGeometry JSON (phase2a_geometry[_snapped].json)")
    ap.add_argument("--out", help="output PNG path (default: <json>.png)")
    args = ap.parse_args()
    j = Path(args.json_path)
    data = json.loads(j.read_text(encoding="utf-8"))
    out = Path(args.out) if args.out else j.with_suffix(".png")
    render(data).save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
