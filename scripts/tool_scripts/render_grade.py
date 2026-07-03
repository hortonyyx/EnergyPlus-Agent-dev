"""Render a judge-side grade sheet from score_vs_gt.json.

The renderer is deliberately sidecar-driven: hit/miss/extra/drift decisions are
read from the scorer output, not recomputed here. Ground truth is used only as a
quiet geometric reference for zone fills, merged wall extents, and elevation
window heights.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from _grade_transform import MetricTransform, plan_transform

BG = (250, 250, 248)
GT_FILL = (238, 238, 234)
GT_EDGE = (208, 208, 203)
GREEN = (52, 150, 96)
RED = (208, 46, 36)
REFERENCE = (150, 150, 145)
FILL_G = (224, 240, 230)
FILL_R = (250, 226, 222)
BAND = (198, 228, 206)
TRUTH = (148, 148, 142)
TEXT = (45, 45, 45)
SUBTLE = (105, 105, 100)
PANEL_GAP = 44
HEADER = 88
LABEL_H = 26
SCALE = 50.0
PLAN_MARGIN_M = 1.15
CUE_EPS_M = 0.05
BOUNDARY_EPS_M = 0.30
FACADE_CODES = ("N", "S", "E", "W")
FACADE_NAMES = {"N": "North", "S": "South", "E": "East", "W": "West"}


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _dashed(
    d: ImageDraw.ImageDraw,
    p1: tuple[float, float],
    p2: tuple[float, float],
    fill: tuple[int, int, int],
    width: int,
    *,
    dash: int = 8,
    gap: int = 5,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    if length <= 0:
        return
    ux, uy = dx / length, dy / length
    t = 0.0
    while t < length:
        s = min(t + dash, length)
        d.line(
            [(x1 + ux * t, y1 + uy * t), (x1 + ux * s, y1 + uy * s)],
            fill=fill,
            width=width,
        )
        t += dash + gap


def _box(a: tuple[float, float], b: tuple[float, float]) -> list[float]:
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]


def _dashed_box(
    d: ImageDraw.ImageDraw,
    box: list[float],
    fill: tuple[int, int, int] | None,
    edge: tuple[int, int, int],
    width: int,
) -> None:
    if fill is not None:
        d.rectangle(box, fill=fill)
    x0, y0, x1, y1 = box
    _dashed(d, (x0, y0), (x1, y0), edge, width, dash=7, gap=4)
    _dashed(d, (x1, y0), (x1, y1), edge, width, dash=7, gap=4)
    _dashed(d, (x1, y1), (x0, y1), edge, width, dash=7, gap=4)
    _dashed(d, (x0, y1), (x0, y0), edge, width, dash=7, gap=4)


def _merge(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for a, b in sorted((min(a, b), max(a, b)) for a, b in intervals):
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def _interior_coords(zones: list[dict], axis: str, limit: float) -> dict[float, list[tuple[float, float]]]:
    coords: dict[float, list[tuple[float, float]]] = {}
    for zone in zones:
        x0, y0, x1, y1 = [float(v) for v in zone.get("rect_m", [])]
        if axis == "v":
            for x in (x0, x1):
                if BOUNDARY_EPS_M < x < limit - BOUNDARY_EPS_M:
                    coords.setdefault(round(x, 2), []).append((y0, y1))
        else:
            for y in (y0, y1):
                if BOUNDARY_EPS_M < y < limit - BOUNDARY_EPS_M:
                    coords.setdefault(round(y, 2), []).append((x0, x1))
    return {coord: _merge(segs) for coord, segs in coords.items()}


def _scores_by_floor(score_sidecar: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key, score in (score_sidecar.get("scores") or {}).items():
        if isinstance(score, dict) and score.get("floor"):
            out[str(score["floor"])] = score
        elif isinstance(score, dict):
            out[str(key)] = score
    return out


def _floor_score_has_facade(score: dict, facade: str) -> bool:
    return (
        isinstance(score.get("windows"), dict)
        and facade in score["windows"]
        and isinstance(score.get("extra_windows"), dict)
        and facade in score["extra_windows"]
    )


def _has_no_data_for_facade(scores_by_floor: dict[str, dict], floors: list[dict], facade: str) -> bool:
    for floor in floors:
        score = scores_by_floor.get(str(floor.get("name")))
        if score is None or not _floor_score_has_facade(score, facade):
            return True
    return False


def _window_meta(gt: dict) -> dict[tuple[str, str, tuple[float, float]], tuple[float, float]]:
    meta: dict[tuple[str, str, tuple[float, float]], tuple[float, float]] = {}
    facade_codes = {v: k for k, v in FACADE_NAMES.items()}
    for entry in gt.get("windows", []):
        floor = str(entry.get("floor"))
        facade = facade_codes.get(str(entry.get("facade")))
        if facade is None:
            continue
        for op in entry.get("openings") or []:
            start = round(float(op.get("x_m", 0.0)), 2)
            end = round(start + float(op.get("width_m", 0.0)), 2)
            sill = float(op.get("sill_m", entry.get("sill_m", 1.0)))
            head = float(op.get("head_m", entry.get("head_m", 2.6)))
            meta[(floor, facade, (start, end))] = (sill, head)
    return meta


def _draw_gt_floor(d: ImageDraw.ImageDraw, tr: MetricTransform, W: float, D: float, floor: dict) -> None:
    for zone in floor.get("zones", []):
        vals = zone.get("rect_m") or []
        if len(vals) != 4:
            continue
        x0, y0, x1, y1 = [float(v) for v in vals]
        d.rectangle(tr.rect(x0, y0, x1, y1), fill=GT_FILL, outline=GT_EDGE, width=1)
    d.rectangle(tr.rect(0, 0, W, D), outline=REFERENCE, width=6)


def _draw_no_data(d: ImageDraw.ImageDraw, x: float, y: float) -> None:
    d.text((x, y), "no data", font=_font(13), fill=RED)


def _wall_match_map(score: dict, key: str) -> dict[float, dict]:
    return {
        round(float(m.get("truth")), 2): m
        for m in score.get(key, [])
        if isinstance(m, dict) and m.get("truth") is not None
    }


def _draw_wall_axis(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    axis: str,
    coordmap: dict[float, list[tuple[float, float]]],
    matches: dict[float, dict],
    wall_tol: float,
) -> None:
    for coord, segs in coordmap.items():
        match = matches.get(round(coord, 2))
        if match is None:
            continue
        read = match.get("read")
        delta = float(match.get("delta") or 0.0) if read is not None else 0.0
        for lo, hi in segs:
            if read is None:
                p1, p2 = (
                    (tr.px(coord, lo), tr.px(coord, hi))
                    if axis == "v"
                    else (tr.px(lo, coord), tr.px(hi, coord))
                )
                _dashed(d, p1, p2, RED, 4)
                continue
            if abs(delta) > CUE_EPS_M:
                if axis == "v":
                    d.rectangle(_box(tr.px(coord - wall_tol, lo), tr.px(coord + wall_tol, hi)), fill=BAND)
                    d.line([tr.px(coord, lo), tr.px(coord, hi)], fill=TRUTH, width=1)
                else:
                    d.rectangle(_box(tr.px(lo, coord - wall_tol), tr.px(hi, coord + wall_tol)), fill=BAND)
                    d.line([tr.px(lo, coord), tr.px(hi, coord)], fill=TRUTH, width=1)
            product_coord = float(read)
            p1, p2 = (
                (tr.px(product_coord, lo), tr.px(product_coord, hi))
                if axis == "v"
                else (tr.px(lo, product_coord), tr.px(hi, product_coord))
            )
            d.line([p1, p2], fill=GREEN, width=4)


def _lane(tr: MetricTransform, W: float, D: float, facade: str, a: float, b: float):
    off = 11
    if facade == "N":
        return (tr.px(a, D)[0], tr.px(a, D)[1] - off), (tr.px(b, D)[0], tr.px(b, D)[1] - off)
    if facade == "S":
        return (tr.px(a, 0)[0], tr.px(a, 0)[1] + off), (tr.px(b, 0)[0], tr.px(b, 0)[1] + off)
    if facade == "E":
        return (tr.px(W, a)[0] + off, tr.px(W, a)[1]), (tr.px(W, b)[0] + off, tr.px(W, b)[1])
    return (tr.px(0, a)[0] - off, tr.px(0, a)[1]), (tr.px(0, b)[0] - off, tr.px(0, b)[1])


def _draw_plan_windows(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    W: float,
    D: float,
    score: dict,
) -> None:
    for facade in FACADE_CODES:
        for match in score.get("windows", {}).get(facade, []):
            truth = match.get("truth")
            if not truth or len(truth) != 2:
                continue
            p1, p2 = _lane(tr, W, D, facade, float(truth[0]), float(truth[1]))
            if match.get("read") is not None:
                read = match["read"]
                p1, p2 = _lane(tr, W, D, facade, float(read[0]), float(read[1]))
                d.line([p1, p2], fill=GREEN, width=7)
            else:
                _dashed(d, p1, p2, RED, 7, dash=6, gap=4)
        for span in score.get("extra_windows", {}).get(facade, []):
            if len(span) != 2:
                continue
            p1, p2 = _lane(tr, W, D, facade, float(span[0]), float(span[1]))
            d.line([p1, p2], fill=RED, width=7)


def _draw_plan_panel(
    d: ImageDraw.ImageDraw,
    ox: int,
    oy: int,
    W: float,
    D: float,
    floor: dict,
    score: dict | None,
    wall_tol: float,
) -> None:
    tr = plan_transform(W, D, scale=SCALE, offset_x=ox, offset_y=oy, margin_m=PLAN_MARGIN_M)
    floor_name = str(floor.get("name"))
    d.text((ox, oy - LABEL_H), f"{floor_name} plan", font=_font(13), fill=TEXT)
    _draw_gt_floor(d, tr, W, D, floor)
    if score is None or "vwalls" not in score or "hwalls" not in score:
        _draw_no_data(d, ox + 12, oy + 12)
        return
    zones = floor.get("zones") or []
    _draw_wall_axis(
        d,
        tr,
        "v",
        _interior_coords(zones, "v", W),
        _wall_match_map(score, "vwalls"),
        wall_tol,
    )
    _draw_wall_axis(
        d,
        tr,
        "h",
        _interior_coords(zones, "h", D),
        _wall_match_map(score, "hwalls"),
        wall_tol,
    )
    for x in score.get("extra_vwalls", []):
        d.line([tr.px(float(x), 0), tr.px(float(x), D)], fill=RED, width=5)
    for y in score.get("extra_hwalls", []):
        d.line([tr.px(0, float(y)), tr.px(W, float(y))], fill=RED, width=5)
    _draw_plan_windows(d, tr, W, D, score)


def _facade_span_limit(gt: dict, facade: str) -> float:
    fp = gt["footprint"]
    return float(fp["W_m"] if facade in {"N", "S"} else fp["D_m"])


def _building_height(gt: dict) -> float:
    top = 0.0
    for floor in gt.get("floors", []):
        z = float(floor.get("z_floor", 0.0))
        h = float(floor.get("ceiling_height", 3.0))
        top = max(top, z + h)
    return max(top, 3.0)


def _floor_z_lookup(gt: dict) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for floor in gt.get("floors", []):
        z = float(floor.get("z_floor", 0.0))
        h = float(floor.get("ceiling_height", 3.0))
        out[str(floor.get("name"))] = (z, h)
    return out


def _draw_elevation_panel(
    d: ImageDraw.ImageDraw,
    ox: int,
    oy: int,
    gt: dict,
    facade: str,
    scores_by_floor: dict[str, dict],
    meta: dict[tuple[str, str, tuple[float, float]], tuple[float, float]],
) -> None:
    floors = list(gt.get("floors", []))
    span_limit = _facade_span_limit(gt, facade)
    height = _building_height(gt)
    tr = MetricTransform(
        min_x=-0.9,
        min_y=-0.9,
        max_x=span_limit + 0.9,
        max_y=height + 0.9,
        scale=SCALE,
        offset_x=ox,
        offset_y=oy,
        flip_y=True,
    )
    d.text((ox, oy - LABEL_H), f"{FACADE_NAMES[facade]} elevation", font=_font(13), fill=TEXT)
    d.rectangle(tr.rect(0, 0, span_limit, height), fill=GT_FILL, outline=REFERENCE, width=6)
    for floor in floors:
        z = float(floor.get("z_floor", 0.0))
        if z > 0:
            d.line([tr.px(0, z), tr.px(span_limit, z)], fill=REFERENCE, width=4)

    if _has_no_data_for_facade(scores_by_floor, floors, facade):
        _draw_no_data(d, ox + 12, oy + 12)
        return

    floor_z = _floor_z_lookup(gt)
    for floor in floors:
        floor_name = str(floor.get("name"))
        score = scores_by_floor.get(floor_name) or {}
        z0, fh = floor_z.get(floor_name, (0.0, 3.0))
        for match in score.get("windows", {}).get(facade, []):
            truth = match.get("truth")
            if not truth or len(truth) != 2:
                continue
            ts, te = round(float(truth[0]), 2), round(float(truth[1]), 2)
            sill, head = meta.get((floor_name, facade, (ts, te)), (z0 + min(1.0, fh * 0.35), z0 + min(2.6, fh * 0.85)))
            if match.get("read") is not None:
                rs, re = [float(v) for v in match["read"]]
                d.rectangle(_box(tr.px(rs, sill), tr.px(re, head)), fill=FILL_G, outline=GREEN, width=3)
            else:
                _dashed_box(d, _box(tr.px(ts, sill), tr.px(te, head)), FILL_R, RED, 3)
        for span in score.get("extra_windows", {}).get(facade, []):
            if len(span) != 2:
                continue
            xs, xe = [float(v) for v in span]
            sill = z0 + min(1.0, fh * 0.35)
            head = z0 + min(2.6, fh * 0.85)
            d.rectangle(_box(tr.px(xs, sill), tr.px(xe, head)), fill=FILL_R, outline=RED, width=3)


def render_grade(stage: str, score_sidecar: dict, gt: dict) -> Image.Image:
    if stage not in {"0_reading", "1_correction"}:
        raise ValueError(f"grade unsupported for stage {stage!r}")
    W = float(gt["footprint"]["W_m"])
    D = float(gt["footprint"]["D_m"])
    panel_tr = plan_transform(W, D, scale=SCALE, margin_m=PLAN_MARGIN_M)
    panel_w, panel_h = panel_tr.width_px, panel_tr.height_px
    floors = list(gt.get("floors", []))
    facade_w = int((_facade_span_limit(gt, "N") + 1.8) * SCALE)
    facade_h = int((_building_height(gt) + 1.8) * SCALE)
    total_w = max(
        960,
        panel_w * max(1, len(floors)) + PANEL_GAP * max(0, len(floors) - 1),
        facade_w * 2 + PANEL_GAP,
    )
    plan_row_h = LABEL_H + panel_h
    elev_row_h = LABEL_H + facade_h
    total_h = HEADER + plan_row_h + PANEL_GAP + elev_row_h * 2 + PANEL_GAP + 20
    img = Image.new("RGB", (total_w, total_h), BG)
    d = ImageDraw.Draw(img)

    tol = score_sidecar.get("tolerances") or {}
    wall_tol = float(tol.get("wall_tol_m", 0.30))
    win_tol = float(tol.get("window_centre_tol_m", 0.40))
    d.text((14, 12), f"{stage} grade", font=_font(18), fill=TEXT)
    d.text(
        (14, 40),
        f"source score_vs_gt.json; wall_tol_m={wall_tol:.2f}; window_centre_tol_m={win_tol:.2f}",
        font=_font(11),
        fill=SUBTLE,
    )
    lx, ly = 14, 63
    d.line([(lx, ly + 7), (lx + 28, ly + 7)], fill=GREEN, width=5)
    d.text((lx + 34, ly), "hit", font=_font(11), fill=SUBTLE)
    lx += 86
    _dashed(d, (lx, ly + 7), (lx + 28, ly + 7), RED, 5, dash=6, gap=4)
    d.text((lx + 34, ly), "miss", font=_font(11), fill=SUBTLE)
    lx += 96
    d.line([(lx, ly + 7), (lx + 28, ly + 7)], fill=RED, width=5)
    d.text((lx + 34, ly), "extra or wrong-place", font=_font(11), fill=SUBTLE)
    lx += 190
    d.rectangle([lx, ly + 1, lx + 28, ly + 13], fill=BAND)
    d.text((lx + 34, ly), "within-tol drift band", font=_font(11), fill=SUBTLE)
    lx += 190
    d.line([(lx, ly + 7), (lx + 28, ly + 7)], fill=REFERENCE, width=5)
    d.text((lx + 34, ly), "gray outline = reference geometry (not graded)", font=_font(11), fill=SUBTLE)

    scores_by_floor = _scores_by_floor(score_sidecar)
    for i, floor in enumerate(floors):
        ox = i * (panel_w + PANEL_GAP)
        oy = HEADER + LABEL_H
        _draw_plan_panel(
            d,
            ox,
            oy,
            W,
            D,
            floor,
            scores_by_floor.get(str(floor.get("name"))),
            wall_tol,
        )

    meta = _window_meta(gt)
    elev_y = HEADER + plan_row_h + PANEL_GAP + LABEL_H
    for idx, facade in enumerate(FACADE_CODES):
        col = idx % 2
        row = idx // 2
        ox = col * (facade_w + PANEL_GAP)
        oy = elev_y + row * (elev_row_h + PANEL_GAP)
        _draw_elevation_panel(d, ox, oy, gt, facade, scores_by_floor, meta)
    return img


def render_grade_to_path(stage: str, score_sidecar: dict, gt: dict, out_path: Path | str) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    render_grade(stage, score_sidecar, gt).save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["0_reading", "1_correction"])
    ap.add_argument("score_sidecar")
    ap.add_argument("gt_json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    score_sidecar = json.loads(Path(args.score_sidecar).read_text(encoding="utf-8"))
    gt = json.loads(Path(args.gt_json).read_text(encoding="utf-8"))
    render_grade_to_path(args.stage, score_sidecar, gt, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
