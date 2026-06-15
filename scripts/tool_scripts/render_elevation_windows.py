"""Render the corrected windows back onto each facade as an elevation view (PNG).

The correction stage places every window on a facade in world coordinates (along-
facade span + absolute z [sill, head]). This draws, per facade (South / North /
East / West), the wall envelope split into floor bands plus each window in its
world position, so the result can be eyeballed against the original elevation
drawing: did windows land on the right facade / floor / position? — the elevation
analogue of render_corrected_geometry.py's filled plan (`*_zones.png`).

Output: one panel per facade that has windows, stacked vertically → `*_elev.png`.
Pure PIL, no other deps (mirrors render_corrected_geometry.py).

Usage:
    python scripts/tool_scripts/render_elevation_windows.py <correction_geometry_snapped.json> [--out x_elev.png]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

SCALE = 26          # px per metre
MARGIN = 28
GAP = 30
HEADER = 44
TITLE = 18

WALL_FILL = "#e8e4dc"
WALL_EDGE = "#444444"
WINDOW = "#1f77b4"
WINDOW_EDGE = "#0d3b66"
TEXT = "#222222"
SUBTLE = "#777777"
GRID = "#dddddd"

_FACADES = ("South", "North", "East", "West")


def _along_extent(data: dict, facade: str) -> tuple[float, float]:
    """The world extent of the building along the given facade."""
    fx = data.get("footprint_x") or [0, 0]
    fy = data.get("footprint_y") or [0, 0]
    return (min(fx), max(fx)) if facade in ("South", "North") else (min(fy), max(fy))


def _z_extent(data: dict) -> tuple[float, float]:
    floors = data.get("floors") or []
    if not floors:
        return 0.0, 3.0
    zb = min(float(f["z_floor"]) for f in floors)
    zt = max(float(f["z_floor"]) + float(f["ceiling_height"]) for f in floors)
    return zb, zt


def _facade_windows(data: dict, facade: str) -> list[dict]:
    return [w for w in (data.get("windows") or []) if w.get("facade") == facade]


def render(data: dict) -> Image.Image:
    present = [f for f in _FACADES if _facade_windows(data, f)]
    if not present:
        present = list(_FACADES)  # still draw empty envelopes for context

    z0, z1 = _z_extent(data)
    zspan = max(z1 - z0, 0.1)
    panel_h = int(zspan * SCALE) + TITLE + 6

    widths = []
    for f in present:
        a0, a1 = _along_extent(data, f)
        widths.append(int((a1 - a0) * SCALE) + 2 * MARGIN)
    W = max(widths) if widths else 400
    H = HEADER + sum(panel_h + GAP for _ in present)

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((MARGIN, 14), "Corrected elevation — windows per facade", fill=TEXT)

    y = HEADER
    for f in present:
        a0, a1 = _along_extent(data, f)
        aspan = max(a1 - a0, 0.1)
        d.text((MARGIN, y), f"{f} facade  (along {a0:.1f}..{a1:.1f} m, z {z0:.1f}..{z1:.1f} m)",
                fill=SUBTLE)
        oy = y + TITLE

        def ax(world_along: float) -> float:
            return MARGIN + (world_along - a0) * SCALE

        def az(world_z: float) -> float:
            return oy + (z1 - world_z) * SCALE  # z up → smaller pixel y

        # floor-band wall envelope
        for fl in data.get("floors") or []:
            zf = float(fl["z_floor"])
            zt = zf + float(fl["ceiling_height"])
            d.rectangle([ax(a0), az(zt), ax(a1), az(zf)], fill=WALL_FILL, outline=WALL_EDGE)
        # windows
        for w in _facade_windows(data, f):
            s = sorted(float(v) for v in w["span"])
            zz = sorted(float(v) for v in w["z"])
            d.rectangle([ax(s[0]), az(zz[1]), ax(s[1]), az(zz[0])],
                        fill=WINDOW, outline=WINDOW_EDGE)
            d.text((ax(s[0]) + 1, az(zz[1]) + 1), str(w.get("id", "")), fill="white")
        y += panel_h + GAP
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("json", help="correction_geometry_snapped.json")
    ap.add_argument("--out", help="output PNG (default: <json>_elev.png)")
    args = ap.parse_args()
    j = Path(args.json)
    data = json.loads(j.read_text(encoding="utf-8"))
    out = Path(args.out) if args.out else j.with_name(j.stem + "_elev.png")
    render(data).save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
