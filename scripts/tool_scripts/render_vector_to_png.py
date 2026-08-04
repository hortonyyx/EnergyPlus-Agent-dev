"""Render reading-stage vector JSON to PNG (PIL) for side-by-side validation against the source image.

Companion to render_vector_to_svg.py. PNG is easier to eyeball next to the original than the SVG,
and (unlike SVG) can be read back by a multimodal model for self-inspection.

Usage:
    python scripts/tool_scripts/render_vector_to_png.py <vector_json> [--out <png_path>]
    python scripts/tool_scripts/render_vector_to_png.py --dir <dir-of-vector-jsons>

Handles image_kind='plan' and 'elevation'. Geometry mirrors render_vector_to_svg.py:
world -> px with y flipped (north up), walls dark, windows blue, dims green, ocr purple.
Pure PIL, no other deps.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

PALETTE = {
    "wall": (34, 34, 34),
    "window": (31, 119, 180),
    "wall_fill": (153, 153, 153),
    "outline": (0, 0, 0),
    "dim": (44, 160, 44),
    "ocr": (148, 103, 189),
}
SCALE_PX_PER_M = 45
MARGIN_M = 1.5

# G-8 pixel budget (ruling §4 G8): two NAMED caps — a per-side cap and a
# total-pixel cap. A render that would exceed either is REFUSED (raises), never
# clamped: clamping would silently hide a broken extent (the O-4 root cause — a
# pixel OCR anchor read as metric blew a ~10×20 m drawing up to 3.3e8 px). L-51
# asserts these constants take effect (changing them changes the lock behaviour);
# the numbers must not be scattered at call sites.
MAX_CANVAS_SIDE_PX = 8192
MAX_CANVAS_PIXELS = 50_000_000


class CanvasBudgetExceeded(ValueError):
    """The rendered canvas would exceed the pixel budget (G-8). Refused, never
    clamped — clamping hides a broken extent instead of surfacing it (O-4)."""


def _stroke_points(g: dict) -> list[tuple[float, float]]:
    kind = g.get("kind")
    if kind == "line":
        return [tuple(g["p1"]), tuple(g["p2"])]
    if kind == "rect":
        x0, x1 = g.get("x_range_m", [None, None])
        y0, y1 = g.get("y_range_m", [None, None])
        if None in (x0, x1, y0, y1):
            return []
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if kind == "polyline":
        return [tuple(p) for p in (g.get("points") or [])]
    return []


def _collect_points(data: dict) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for s in data.get("strokes") or []:
        pts.extend(_stroke_points(s.get("geometry") or {}))
    for d in data.get("dimensions") or []:
        if d.get("from"):
            pts.append(tuple(d["from"]))
        if d.get("to"):
            pts.append(tuple(d["to"]))
    # O-4: OCR/annotation anchors are NOT structural geometry — they must not
    # expand the metric canvas (a pixel anchor read as metric was the 3.3e8-px
    # root cause). The canvas extent comes from structural strokes + dimension
    # endpoints ONLY; OCR anchors are drawn against that fixed canvas (and may
    # fall outside it, which the gate① OCR-bounds FLAG surfaces — G-9).
    return pts


def render(data: dict) -> Image.Image:
    pts = _collect_points(data)
    if not pts:
        img = Image.new("RGB", (400, 80), (250, 250, 250))
        ImageDraw.Draw(img).text((10, 35), "empty vector", fill=(120, 120, 120))
        return img

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs) - MARGIN_M, max(xs) + MARGIN_M
    miny, maxy = min(ys) - MARGIN_M, max(ys) + MARGIN_M
    W = max(1, int((maxx - minx) * SCALE_PX_PER_M))
    H = max(1, int((maxy - miny) * SCALE_PX_PER_M))
    # G-8: refuse an over-budget canvas BEFORE Image.new — never clamp (O-4).
    if W > MAX_CANVAS_SIDE_PX or H > MAX_CANVAS_SIDE_PX or W * H > MAX_CANVAS_PIXELS:
        raise CanvasBudgetExceeded(
            f"canvas {W}x{H} ({W * H} px) exceeds the pixel budget "
            f"(side <= {MAX_CANVAS_SIDE_PX}, total <= {MAX_CANVAS_PIXELS}); "
            f"structural extent = {maxx - minx:.1f} x {maxy - miny:.1f} m. "
            "Annotation must not expand the canvas; a pixel anchor mistaken for "
            "metric is the likely cause (O-4)."
        )

    def tx(x: float) -> float:
        return (x - minx) * SCALE_PX_PER_M

    def ty(y: float) -> float:
        return H - (y - miny) * SCALE_PX_PER_M

    img = Image.new("RGB", (W, H), (250, 250, 250))
    dr = ImageDraw.Draw(img)

    gx = int(minx)
    while gx <= maxx:
        dr.line([(tx(gx), 0), (tx(gx), H)], fill=(225, 225, 225), width=1)
        gx += 1
    gy = int(miny)
    while gy <= maxy:
        dr.line([(0, ty(gy)), (W, ty(gy))], fill=(225, 225, 225), width=1)
        gy += 1

    for d in data.get("dimensions") or []:
        f_, t_ = d.get("from"), d.get("to")
        if f_ and t_:
            dr.line([(tx(f_[0]), ty(f_[1])), (tx(t_[0]), ty(t_[1]))], fill=PALETTE["dim"], width=1)
            dr.text(((tx(f_[0]) + tx(t_[0])) / 2, (ty(f_[1]) + ty(t_[1])) / 2),
                    d.get("text", ""), fill=PALETTE["dim"])

    for s in data.get("strokes") or []:
        g = s.get("geometry") or {}
        col = PALETTE.get(s.get("pen"), (170, 170, 170))
        kind = g.get("kind")
        width = 6 if s.get("pen") == "wall" else 4
        if kind == "line":
            p1, p2 = g.get("p1"), g.get("p2")
            if p1 and p2:
                dr.line([(tx(p1[0]), ty(p1[1])), (tx(p2[0]), ty(p2[1]))], fill=col, width=width)
                dr.text(((tx(p1[0]) + tx(p2[0])) / 2, (ty(p1[1]) + ty(p2[1])) / 2 - 8),
                        s.get("id", ""), fill=(120, 120, 120))
        elif kind == "rect":
            x0, x1 = g.get("x_range_m", [None, None])
            y0, y1 = g.get("y_range_m", [None, None])
            if None not in (x0, x1, y0, y1):
                dr.rectangle([tx(x0), ty(y1), tx(x1), ty(y0)], outline=col, width=3)
        elif kind == "polyline":
            pl = g.get("points") or []
            if len(pl) >= 2:
                dr.line([(tx(p[0]), ty(p[1])) for p in pl], fill=col, width=width)

    for o in data.get("ocr_texts") or []:
        a = o.get("anchor")
        if a:
            dr.text((tx(a[0]), ty(a[1])), (o.get("text", "") or "").replace("\n", " / "),
                    fill=PALETTE["ocr"])

    dr.text((6, 6), f'{data.get("image_kind")} | {data.get("image_label", "")}', fill=(60, 60, 60))
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", nargs="?", help="single vector JSON to render")
    ap.add_argument("--dir", help="render every *.json under this directory")
    ap.add_argument("--out", help="output PNG path (single-file mode only)")
    args = ap.parse_args()

    if args.dir:
        d = Path(args.dir)
        targets = sorted(d.glob("*.json"))
        if not targets:
            print(f"no *.json in {d}")
            return
        for j in targets:
            data = json.loads(j.read_text(encoding="utf-8"))
            out = j.with_name(j.stem + "_render.png")
            render(data).save(out)
            print(f"  {j.name} -> {out.name}")
        return

    if not args.json_path:
        ap.error("provide json_path or --dir")
    j = Path(args.json_path)
    data = json.loads(j.read_text(encoding="utf-8"))
    out = Path(args.out) if args.out else j.with_name(j.stem + "_render.png")
    render(data).save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
