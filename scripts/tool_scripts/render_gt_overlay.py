"""Overlay the DXF-built gt onto the ORIGINAL drawing PNGs — cross-source validation.

The original case_data drawings and the source.dxf are two INDEPENDENT data sources for
the same building. Overlaying gt (built from the DXF) onto the original PNG cross-checks
that the two sources agree: if the gt zones/windows land on the drawing's real
walls/openings, the sources are consistent; if not, there is a real DATA problem (the
DXF and the drawing disagree, or one is wrong). This is the strong human-QA gate — unlike
gt-over-DXF, which (for a deterministic dxf→gt) only re-confirms the code.

Calibration is automatic: the footprint / facade-envelope pixel box is found from
wall-line pixel density per column/row, cross-checked by px-per-metre agreement between
the two axes (a mismatch flags a contaminated edge, corrected from the cleaner axis).

Usage:
    python scripts/tool_scripts/render_gt_overlay.py sm21_anchor
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

DIM = 0.38     # original drawing dimmed to this brightness so the gt overlay stands out

GT_DIR = Path("case_tests/test_baseline/gt")
CASE_DATA = Path("case_tests/e2e_tests/{case}/case_data")

ROLE = {"office": (90, 140, 220), "meeting": (70, 175, 90), "corridor": (220, 170, 40)}
WIN = (0, 200, 255)
DOOR = (255, 120, 0)
# elevation x runs west→east for S, south→north for E; N & W are viewed mirrored.
_MIRRORED = {"North", "West"}
_FACADE_PNG = {"South": "South_view", "North": "North_view",
               "East": "East_view", "West": "West_view"}
_FLOOR_PNG = {"Floor 1": "1f_view", "Floor 2": "2f_view"}


def _font(sz):
    return ImageFont.load_default(size=sz)


def _density_box(mask):
    cden, rden = mask.sum(0), mask.sum(1)
    if mask.sum() < 100:
        return None
    cols = np.where(cden > cden.max() * 0.38)[0]
    rows = np.where(rden > rden.max() * 0.38)[0]
    return int(cols.min()), int(cols.max()), int(rows.min()), int(rows.max())


def _box_gray(im):
    r, g, b = im[:, :, 0].astype(int), im[:, :, 1].astype(int), im[:, :, 2].astype(int)
    return _density_box((abs(r - g) < 25) & (abs(g - b) < 25) & (r > 60) & (r < 210))


def _box_white(im):
    r, g, b = im[:, :, 0].astype(int), im[:, :, 1].astype(int), im[:, :, 2].astype(int)
    return _density_box((r > 170) & (g > 170) & (b > 170))


def _calibrate(im, w_m, h_m):
    """Footprint / envelope pixel box. Try the gray-wall and white-envelope detectors;
    use whichever gives px-per-metre AGREEMENT between the two axes (the consistent one
    is the clean calibration — a contaminated edge inflates one axis). The two detectors
    are complementary across views, so one of them is almost always clean."""
    best = None
    for box in (_box_gray(im), _box_white(im)):
        if not box:
            continue
        x0, x1, yt, yb = box
        if x1 <= x0 or yb <= yt:
            continue
        sx, sy = (x1 - x0) / w_m, (yb - yt) / h_m
        err = abs(sx - sy) / max(sx, sy)
        if err < 0.05:
            return box
        if best is None or err < best[0]:
            best = (err, box)
    # fallback: anchor x on the gray box centre, width from the (reliable) y-scale
    x0, x1, yt, yb = best[1] if best else _box_gray(im)
    sy = (yb - yt) / h_m
    cx, half = (x0 + x1) / 2, sy * w_m / 2
    return round(cx - half), round(cx + half), yt, yb


def _load(case):
    gt = json.loads((GT_DIR / case / "gt.json").read_text(encoding="utf-8"))
    cd = Path(str(CASE_DATA).format(case=case))
    return gt, cd


def overlay_plan(case, gt, cd, floor):
    png = cd / f"{_FLOOR_PNG[floor]}.png"
    base = Image.open(png).convert("RGBA")
    im = np.asarray(base.convert("RGB"))               # calibrate on the full-brightness original
    dim = ImageEnhance.Brightness(base.convert("RGB")).enhance(DIM).convert("RGBA")
    W, D = gt["footprint"]["W_m"], gt["footprint"]["D_m"]
    x0, x1, yt, yb = _calibrate(im, W, D)

    def PX(gx):
        return x0 + gx / W * (x1 - x0)

    def PY(gy):
        return yb - gy / D * (yb - yt)         # gy=0 (south) at bottom

    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    fl = next(f for f in gt["floors"] if f["name"] == floor)
    for z in fl["zones"]:
        a, c, e, f = z["rect_m"]
        col = ROLE.get(z["role"], (150, 150, 150))
        d.rectangle([PX(a), PY(f), PX(e), PY(c)], fill=col + (70,), outline=col + (255,), width=3)
        d.text((PX(a) + 5, PY(f) + 4), f"{z['id']} {z['role']}", font=_font(20), fill=col + (255,))
    for w in gt["windows"]:
        if w["floor"] != floor:
            continue
        for o in w.get("openings", []):
            p, q = o["x_m"], o["x_m"] + o["width_m"]
            if w["facade"] in ("North", "South"):
                yy = PY(D) if w["facade"] == "North" else PY(0)
                d.line([(PX(p), yy), (PX(q), yy)], fill=WIN + (255,), width=9)
            else:
                xx = PX(W) if w["facade"] == "East" else PX(0)
                yA = yb - p / D * (yb - yt); yB = yb - q / D * (yb - yt)
                d.line([(xx, yA), (xx, yB)], fill=WIN + (255,), width=9)
    for dr in gt["doors"]:
        if dr["floor"] != floor:
            continue
        if dr["facade"] == "South":
            d.line([(PX(0.3), PY(0)), (PX(1.2), PY(0))], fill=DOOR + (255,), width=10)
        elif dr["facade"] == "West":
            d.line([(PX(0), PY(3.2)), (PX(0), PY(4.8))], fill=DOOR + (255,), width=10)
    d.text((10, 8), f"TYPE 2  {floor}:  gt over dimmed original  (is gt faithful to the drawing?)",
           font=_font(22), fill=(255, 255, 255, 255))
    out = Image.alpha_composite(dim, ov).convert("RGB")
    return out


def overlay_elev(case, gt, cd, facade):
    png = cd / f"{_FACADE_PNG[facade]}.png"
    base = Image.open(png).convert("RGBA")
    im = np.asarray(base.convert("RGB"))
    dim = ImageEnhance.Brightness(base.convert("RGB")).enhance(DIM).convert("RGBA")
    fw = gt["footprint"]["W_m"] if facade in ("North", "South") else gt["footprint"]["D_m"]
    ht = max(f["z_floor"] + f["ceiling_height"] for f in gt["floors"])
    x0, x1, yt, yb = _calibrate(im, fw, ht)
    mir = facade in _MIRRORED

    def PX(fx):
        t = (fw - fx) / fw if mir else fx / fw
        return x0 + t * (x1 - x0)

    def PZ(z):
        return yb - z / ht * (yb - yt)

    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for w in gt["windows"]:
        if w["facade"] != facade:
            continue
        for o in w.get("openings", []):
            if "sill_m" not in o:
                continue
            xa, xb = PX(o["x_m"]), PX(o["x_m"] + o["width_m"])
            d.rectangle([min(xa, xb), PZ(o["head_m"]), max(xa, xb), PZ(o["sill_m"])],
                        outline=WIN + (255,), width=4)
    d.text((10, 8), f"TYPE 2  {facade} elevation:  gt over dimmed original  "
           "(do gt windows match the drawing?)", font=_font(20), fill=(255, 255, 255, 255))
    out = Image.alpha_composite(dim, ov).convert("RGB")
    return out


def main():
    ap = argparse.ArgumentParser(description="Overlay DXF-built gt onto the original drawing PNGs.")
    ap.add_argument("case")
    args = ap.parse_args()
    gt, cd = _load(args.case)
    out_dir = GT_DIR / args.case / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    for floor in ("Floor 1", "Floor 2"):
        p = out_dir / f"overlay_{_FLOOR_PNG[floor]}.png"
        overlay_plan(args.case, gt, cd, floor).save(p)
        print(f"wrote {p}")
    for facade in ("South", "North", "East", "West"):
        p = out_dir / f"overlay_{_FACADE_PNG[facade]}.png"
        overlay_elev(args.case, gt, cd, facade).save(p)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
