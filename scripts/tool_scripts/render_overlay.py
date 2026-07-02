"""Render accepted attempt output against gt on one shared metric canvas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from _overlay_transform import MetricTransform, plan_transform

BG = (250, 250, 248)
GRID = (226, 226, 222)
GT_FILL = (218, 218, 214)
GT_EDGE = (125, 125, 120)
GT_WINDOW = (130, 150, 168)
OUT_RED = (202, 48, 38)
OUT_RED_LIGHT = (232, 129, 120)
TEXT = (45, 45, 45)
SUBTLE = (105, 105, 100)
PANEL_GAP = 28
HEADER = 72
LABEL_H = 26
SCALE = 48.0


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _line_segment(g: dict) -> tuple[float, float, float, float] | None:
    if g.get("kind") == "line" and g.get("p1") and g.get("p2"):
        return (*g["p1"], *g["p2"])
    if g.get("kind") == "rect":
        xr = g.get("x_range_m")
        yr = g.get("y_range_m")
        if xr and yr and len(xr) == 2 and len(yr) == 2:
            dx, dy = abs(xr[1] - xr[0]), abs(yr[1] - yr[0])
            if dx >= dy:
                ym = (yr[0] + yr[1]) / 2
                return min(xr), ym, max(xr), ym
            xm = (xr[0] + xr[1]) / 2
            return xm, min(yr), xm, max(yr)
    return None


def _floor_name_for_stem(stem: str, gt: dict) -> str | None:
    digit = "".join(ch for ch in stem if ch.isdigit())[:1]
    if not digit:
        return None
    idx = int(digit) - 1
    floors = gt.get("floors", [])
    return str(floors[idx]["name"]) if 0 <= idx < len(floors) else None


def _reading_by_gt_floor(output: dict, gt: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for stem, view in output.items():
        if not isinstance(view, dict) or view.get("image_kind") not in (None, "plan"):
            continue
        floor = _floor_name_for_stem(stem, gt)
        if floor:
            out[floor] = view
    return out


def _correction_by_gt_floor(output: dict, gt: dict) -> dict[str, dict]:
    from src.agent.judge.correction_score import _map_floors
    from src.agent.correction.schema import CorrectedGeometry

    geom = CorrectedGeometry.model_validate(output)
    floor_map, _evidence = _map_floors(geom, gt)
    return {floor_map[fl.name]: fl.model_dump() for fl in geom.floors if fl.name in floor_map}


def _draw_grid(d: ImageDraw.ImageDraw, tr: MetricTransform, W: float, D: float) -> None:
    x = 0
    while x <= W + 1e-6:
        d.line([tr.px(x, 0), tr.px(x, D)], fill=GRID, width=1)
        x += 1
    y = 0
    while y <= D + 1e-6:
        d.line([tr.px(0, y), tr.px(W, y)], fill=GRID, width=1)
        y += 1


def _draw_gt_floor(d: ImageDraw.ImageDraw, tr: MetricTransform, gt: dict, floor: dict) -> None:
    W = float(gt["footprint"]["W_m"])
    D = float(gt["footprint"]["D_m"])
    _draw_grid(d, tr, W, D)
    for zone in floor.get("zones", []):
        x0, y0, x1, y1 = zone["rect_m"]
        d.rectangle(tr.rect(x0, y0, x1, y1), fill=GT_FILL, outline=GT_EDGE, width=2)
    d.rectangle(tr.rect(0, 0, W, D), outline=GT_EDGE, width=3)
    _draw_gt_windows(d, tr, gt, str(floor.get("name")))


def _draw_gt_windows(d: ImageDraw.ImageDraw, tr: MetricTransform, gt: dict, floor_name: str) -> None:
    W = float(gt["footprint"]["W_m"])
    D = float(gt["footprint"]["D_m"])
    for entry in gt.get("windows", []):
        if entry.get("floor") != floor_name:
            continue
        facade = entry.get("facade")
        for op in entry.get("openings") or []:
            a = float(op["x_m"])
            b = a + float(op["width_m"])
            if facade == "North":
                d.line([tr.px(a, D), tr.px(b, D)], fill=GT_WINDOW, width=7)
            elif facade == "South":
                d.line([tr.px(a, 0), tr.px(b, 0)], fill=GT_WINDOW, width=7)
            elif facade == "East":
                d.line([tr.px(W, a), tr.px(W, b)], fill=GT_WINDOW, width=7)
            elif facade == "West":
                d.line([tr.px(0, a), tr.px(0, b)], fill=GT_WINDOW, width=7)


def _draw_reading(d: ImageDraw.ImageDraw, tr: MetricTransform, view: dict) -> None:
    for stroke in view.get("strokes") or []:
        seg = _line_segment(stroke.get("geometry") or {})
        if seg is None:
            continue
        x1, y1, x2, y2 = seg
        pen = stroke.get("pen")
        width = 5 if pen == "wall" else 4
        fill = OUT_RED if pen in {"wall", "window"} else OUT_RED_LIGHT
        d.line([tr.px(x1, y1), tr.px(x2, y2)], fill=fill, width=width)


def _draw_correction(d: ImageDraw.ImageDraw, tr: MetricTransform, floor: dict) -> None:
    for cell in floor.get("cells") or []:
        x0, x1 = cell.get("x", [None, None])
        y0, y1 = cell.get("y", [None, None])
        if None in (x0, x1, y0, y1):
            continue
        d.rectangle(tr.rect(x0, y0, x1, y1), outline=OUT_RED, width=4)


def render_overlay(stage: str, output: dict, gt: dict) -> Image.Image:
    if stage not in {"0_reading", "1_correction"}:
        raise ValueError(f"overlay unsupported for stage {stage!r}")
    W = float(gt["footprint"]["W_m"])
    D = float(gt["footprint"]["D_m"])
    panel_tr = plan_transform(W, D, scale=SCALE)
    panel_w, panel_h = panel_tr.width_px, panel_tr.height_px
    floors = list(gt.get("floors", []))
    total_w = max(640, panel_w * len(floors) + PANEL_GAP * max(0, len(floors) - 1))
    total_h = HEADER + LABEL_H + panel_h + 18
    img = Image.new("RGB", (total_w, total_h), BG)
    d = ImageDraw.Draw(img)

    d.text((12, 10), f"{stage} attempt vs gt overlay", font=_font(19), fill=TEXT)
    d.text(
        (12, 37),
        "gt clear-space/cell truth in gray-blue; accepted attempt output in red; "
        "wall tol 0.30 m, window centre tol 0.40 m",
        font=_font(12),
        fill=SUBTLE,
    )
    d.text(
        (12, 54),
        "clear-space bbox vs correction centerline offsets are tolerance context, not hard red errors",
        font=_font(12),
        fill=SUBTLE,
    )

    if stage == "0_reading":
        product_by_floor = _reading_by_gt_floor(output, gt)
    else:
        product_by_floor = _correction_by_gt_floor(output, gt)

    for i, floor in enumerate(floors):
        ox = i * (panel_w + PANEL_GAP)
        oy = HEADER + LABEL_H
        tr = plan_transform(W, D, scale=SCALE, offset_x=ox, offset_y=oy)
        floor_name = str(floor.get("name"))
        d.text((ox + 4, HEADER), floor_name, font=_font(14), fill=TEXT)
        _draw_gt_floor(d, tr, gt, floor)
        product = product_by_floor.get(floor_name)
        if product:
            if stage == "0_reading":
                _draw_reading(d, tr, product)
            else:
                _draw_correction(d, tr, product)
        else:
            d.text((ox + 8, oy + 8), "no mapped attempt floor", font=_font(12), fill=OUT_RED)
    return img


def render_overlay_to_path(stage: str, output: dict, gt: dict, out_path: Path | str) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    render_overlay(stage, output, gt).save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["0_reading", "1_correction"])
    ap.add_argument("attempt_output")
    ap.add_argument("gt_json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    output = json.loads(Path(args.attempt_output).read_text(encoding="utf-8"))
    gt = json.loads(Path(args.gt_json).read_text(encoding="utf-8"))
    render_overlay_to_path(args.stage, output, gt, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
