"""Render a judge-side grade sheet from score_vs_gt.json.

The renderer is deliberately sidecar-driven: hit/miss/extra/tolerance decisions are
read from the scorer output, not recomputed here. Ground truth is used only as a
quiet geometric reference for zone fills, truth bases, and explicit miss
annotations.
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
ORANGE = (205, 118, 35)
RED = (208, 46, 36)
REFERENCE = (150, 150, 145)
FILL_R = (250, 226, 222)
FILL_DRIFT = (249, 235, 214)
BAND = FILL_DRIFT
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


def _plan_panel_label(floor_name: str) -> str:
    return f"{floor_name} plan-derived (secondary)"


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
    dash: float = 8,
    gap: float = 5,
    min_cycles: int = 3,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    if length <= 0:
        return
    # Adaptive dashes: a tiny segment drawn with the fixed period renders as one
    # solid-looking nub. Shrink the period so a short segment still shows at least
    # `min_cycles` dashes (with a hard floor so it never collapses to a dotted
    # line). Long segments keep the requested dash/gap unchanged.
    period = dash + gap
    if length < period * min_cycles:
        ratio = dash / period if period > 0 else 0.6
        period = max(2.4, length / min_cycles)
        dash = max(1.2, period * ratio)
        gap = max(0.8, period - dash)
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


# The orange tolerance band must be semi-transparent so the gray gt truth
# underneath shows through instead of being painted over.
BAND_RGB = ORANGE
BAND_ALPHA = 70  # ~27% — a faint orange wash that gt reads through


def _fill_band(d: ImageDraw.ImageDraw, box: list[float]) -> None:
    """Alpha-composite a translucent orange band so gt shows through."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    if x1 <= x0 or y1 <= y0:
        return
    img = getattr(d, "_image", None)
    if img is None:  # fallback: opaque (older Pillow without _image)
        d.rectangle([x0, y0, x1, y1], fill=BAND)
        return
    region = img.crop((x0, y0, x1, y1)).convert("RGBA")
    overlay = Image.new("RGBA", region.size, (*BAND_RGB, BAND_ALPHA))
    img.paste(Image.alpha_composite(region, overlay).convert("RGB"), (x0, y0))


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


def _scores_by_floor(score_sidecar: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key, score in (score_sidecar.get("scores") or {}).items():
        if isinstance(score, dict) and score.get("floor"):
            out[str(score["floor"])] = score
        elif isinstance(score, dict):
            out[str(key)] = score
    return out


def _draw_gt_floor(d: ImageDraw.ImageDraw, tr: MetricTransform, W: float, D: float, floor: dict) -> None:
    for zone in floor.get("zones", []):
        vals = zone.get("rect_m") or []
        if len(vals) != 4:
            continue
        x0, y0, x1, y1 = [float(v) for v in vals]
        d.rectangle(tr.rect(x0, y0, x1, y1), fill=GT_FILL, outline=GT_EDGE, width=1)
    d.rectangle(tr.rect(0, 0, W, D), outline=REFERENCE, width=6)


def _draw_no_data(d: ImageDraw.ImageDraw, x: float, y: float) -> None:
    d.text((x, y), "no data", font=_font(13), fill=SUBTLE)


def _draw_no_elevation_score(d: ImageDraw.ImageDraw, x: float, y: float) -> None:
    d.text((x, y), "no elevation score", font=_font(13), fill=RED)


def _numeric_pair(value: object) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        a = float(value[0])
        b = float(value[1])
    except (TypeError, ValueError):
        return None
    return (min(a, b), max(a, b))


def _segment(value: object) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        coord = float(value[0])
        a = float(value[1])
        b = float(value[2])
    except (TypeError, ValueError):
        return None
    return coord, min(a, b), max(a, b)


def _segments(values: object, fallback: object = None) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    if isinstance(values, list):
        for value in values:
            seg = _segment(value)
            if seg is not None:
                out.append(seg)
    if not out:
        seg = _segment(fallback)
        if seg is not None:
            out.append(seg)
    return out


def _piece_span(piece: dict) -> tuple[float, float] | None:
    return _numeric_pair(piece.get("span")) if isinstance(piece, dict) else None


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float] | None:
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    if hi <= lo + 1e-9:
        return None
    return lo, hi


def _linear_points(
    tr: MetricTransform,
    axis: str,
    coord: float,
    span: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    if axis == "v":
        return tr.px(coord, span[0]), tr.px(coord, span[1])
    return tr.px(span[0], coord), tr.px(span[1], coord)


def _draw_linear_band(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    axis: str,
    coord: float,
    span: tuple[float, float],
    tol: float,
) -> None:
    tol = max(float(tol), 0.04)
    if axis == "v":
        _fill_band(d, _box(tr.px(coord - tol, span[0]), tr.px(coord + tol, span[1])))
    else:
        _fill_band(d, _box(tr.px(span[0], coord - tol), tr.px(span[1], coord + tol)))


def _draw_acceptance_rect(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    axis: str,
    coord: float,
    span: tuple[float, float],
    lateral_half_width: float,
) -> None:
    lateral_half_width = max(float(lateral_half_width), 0.04)
    if axis == "v":
        _fill_band(
            d,
            _box(tr.px(coord - lateral_half_width, span[0]), tr.px(coord + lateral_half_width, span[1])),
        )
    else:
        _fill_band(
            d,
            _box(tr.px(span[0], coord - lateral_half_width), tr.px(span[1], coord + lateral_half_width)),
        )


def _infer_extent_drift(record: dict) -> bool:
    for piece in record.get("pieces") or []:
        if isinstance(piece, dict) and piece.get("kind") in {"missing", "extra"} and bool(piece.get("within_tol")):
            return True
    return False


def _draw_plan_wall_acceptance_band(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    record: dict,
    axis: str,
    *,
    position_tol: float,
    extent_tol: float,
) -> None:
    if record.get("status") != "within_tol":
        return
    gt_segments = _segments(record.get("gt_intervals"), record.get("gt"))
    if not gt_segments:
        return
    lateral_drift = bool(record.get("lateral_drift"))
    extent_drift = bool(record.get("extent_drift")) or _infer_extent_drift(record)
    if not lateral_drift and not extent_drift:
        try:
            lateral_drift = abs(float(record.get("delta"))) > CUE_EPS_M
        except (TypeError, ValueError):
            lateral_drift = False
    if not lateral_drift and not extent_drift:
        return

    if lateral_drift and extent_drift:
        for coord, lo, hi in gt_segments:
            _draw_acceptance_rect(d, tr, axis, coord, (lo - extent_tol, hi + extent_tol), position_tol)
        return

    if lateral_drift:
        for coord, lo, hi in gt_segments:
            _draw_acceptance_rect(d, tr, axis, coord, (lo, hi), position_tol)
        return

    start_drift = bool(record.get("extent_start_drift"))
    end_drift = bool(record.get("extent_end_drift"))
    if not start_drift and not end_drift:
        start_drift = end_drift = True
    for coord, lo, hi in gt_segments:
        if start_drift:
            _draw_acceptance_rect(d, tr, axis, coord, (lo - extent_tol, lo + extent_tol), 0.04)
        if end_drift:
            _draw_acceptance_rect(d, tr, axis, coord, (hi - extent_tol, hi + extent_tol), 0.04)


def _draw_linear_segment(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    axis: str,
    coord: float,
    span: tuple[float, float],
    color: tuple[int, int, int],
    width: int,
    *,
    dashed: bool = False,
) -> None:
    p1, p2 = _linear_points(tr, axis, coord, span)
    if dashed:
        _dashed(d, p1, p2, color, width, dash=7, gap=4)
    else:
        d.line([p1, p2], fill=color, width=width)


def _draw_plan_linear_gt_base(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    records: list[dict],
    axis: str,
    *,
    width: int,
) -> None:
    for record in records:
        for coord, lo, hi in _segments(record.get("gt_intervals"), record.get("gt")):
            _draw_linear_segment(d, tr, axis, coord, (lo, hi), TRUTH, width)


def _draw_plan_linear_products(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    records: list[dict],
    axis: str,
    *,
    position_tol: float,
    extent_tol: float,
    width: int,
) -> None:
    for record in records:
        product_segments = _segments(record.get("product_intervals"), record.get("product"))
        gt_segments = _segments(record.get("gt_intervals"), record.get("gt"))
        status = record.get("status")
        pieces = [p for p in record.get("pieces") or [] if isinstance(p, dict)]
        _draw_plan_wall_acceptance_band(
            d,
            tr,
            record,
            axis,
            position_tol=position_tol,
            extent_tol=extent_tol,
        )

        if status == "complete":
            for coord, lo, hi in product_segments:
                _draw_linear_segment(d, tr, axis, coord, (lo, hi), GREEN, width)
            continue

        if not pieces:
            color = ORANGE if status == "within_tol" else RED
            if status == "within_tol":
                for coord, lo, hi in product_segments:
                    _draw_linear_segment(d, tr, axis, coord, (lo, hi), ORANGE, width)
            elif status == "miss":
                for coord, lo, hi in gt_segments:
                    _draw_linear_segment(d, tr, axis, coord, (lo, hi), color, width, dashed=True)
            else:
                for coord, lo, hi in product_segments:
                    _draw_linear_segment(d, tr, axis, coord, (lo, hi), color, width)
            continue

        for piece in pieces:
            span = _piece_span(piece)
            if span is None:
                continue
            kind = piece.get("kind")
            within_tol = bool(piece.get("within_tol"))
            color = ORANGE if within_tol and kind in {"missing", "extra"} else GREEN
            if kind == "matched":
                color = ORANGE if status == "within_tol" and bool(record.get("lateral_drift")) else GREEN
                for coord, lo, hi in product_segments:
                    overlap = _overlap((lo, hi), span)
                    if overlap is not None:
                        _draw_linear_segment(d, tr, axis, coord, overlap, color, width)
            elif kind == "missing":
                color = ORANGE if within_tol else RED
                for coord, lo, hi in gt_segments:
                    overlap = _overlap((lo, hi), span)
                    if overlap is not None:
                        _draw_linear_segment(d, tr, axis, coord, overlap, color, width, dashed=True)
            elif kind == "extra":
                color = ORANGE if within_tol else RED
                for coord, lo, hi in product_segments:
                    overlap = _overlap((lo, hi), span)
                    if overlap is not None:
                        _draw_linear_segment(d, tr, axis, coord, overlap, color, width)


def _boundary_line(
    tr: MetricTransform,
    W: float,
    D: float,
    side: str,
    coord: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    if side == "S":
        return tr.px(0, coord), tr.px(W, coord)
    if side == "N":
        return tr.px(0, coord), tr.px(W, coord)
    if side == "W":
        return tr.px(coord, 0), tr.px(coord, D)
    return tr.px(coord, 0), tr.px(coord, D)


def _draw_plan_boundary(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    W: float,
    D: float,
    score: dict,
) -> None:
    boundary = score.get("boundary")
    if not isinstance(boundary, dict):
        return
    for side in ("S", "N", "W", "E"):
        match = boundary.get(side)
        if not isinstance(match, dict):
            continue
        read = match.get("read")
        truth = match.get("truth")
        if truth is None:
            continue
        coord = float(read if read is not None else truth)
        p1, p2 = _boundary_line(tr, W, D, side, coord)
        if read is None:
            _dashed(d, p1, p2, RED, 5, dash=7, gap=4)
        else:
            d.line([p1, p2], fill=GREEN, width=5)


def _lane(tr: MetricTransform, W: float, D: float, facade: str, a: float, b: float):
    off = 11
    if facade == "N":
        return (tr.px(a, D)[0], tr.px(a, D)[1] - off), (tr.px(b, D)[0], tr.px(b, D)[1] - off)
    if facade == "S":
        return (tr.px(a, 0)[0], tr.px(a, 0)[1] + off), (tr.px(b, 0)[0], tr.px(b, 0)[1] + off)
    if facade == "E":
        return (tr.px(W, a)[0] + off, tr.px(W, a)[1]), (tr.px(W, b)[0] + off, tr.px(W, b)[1])
    return (tr.px(0, a)[0] - off, tr.px(0, a)[1]), (tr.px(0, b)[0] - off, tr.px(0, b)[1])


def _spans(values: object, fallback: object = None) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    if isinstance(values, list):
        for value in values:
            span = _numeric_pair(value)
            if span is not None:
                out.append(span)
    if not out:
        span = _numeric_pair(fallback)
        if span is not None:
            out.append(span)
    return out


def _draw_lane_segment(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    W: float,
    D: float,
    facade: str,
    span: tuple[float, float],
    color: tuple[int, int, int],
    width: int,
    *,
    dashed: bool = False,
) -> None:
    p1, p2 = _lane(tr, W, D, facade, span[0], span[1])
    if dashed:
        _dashed(d, p1, p2, color, width, dash=6, gap=4)
    else:
        d.line([p1, p2], fill=color, width=width)


def _draw_plan_windows(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    W: float,
    D: float,
    score: dict,
) -> None:
    for facade in FACADE_CODES:
        records = [
            m for m in (score.get("windows", {}) or {}).get(facade, [])
            if isinstance(m, dict)
        ] + [
            m for m in (score.get("extra_window_records", {}) or {}).get(facade, [])
            if isinstance(m, dict)
        ]
        for record in records:
            for span in _spans(record.get("gt_intervals"), record.get("gt")):
                _draw_lane_segment(d, tr, W, D, facade, span, TRUTH, 5)
        for record in records:
            product_spans = _spans(record.get("product_intervals"), record.get("product") or record.get("read"))
            gt_spans = _spans(record.get("gt_intervals"), record.get("gt") or record.get("truth"))
            status = record.get("status")
            pieces = [p for p in record.get("pieces") or [] if isinstance(p, dict)]
            if status == "complete":
                for span in product_spans:
                    _draw_lane_segment(d, tr, W, D, facade, span, GREEN, 7)
                continue
            if not pieces:
                if status == "within_tol":
                    for span in product_spans:
                        _draw_lane_segment(d, tr, W, D, facade, span, BAND, 11)
                        _draw_lane_segment(d, tr, W, D, facade, span, ORANGE, 7)
                elif status == "miss":
                    for span in gt_spans:
                        _draw_lane_segment(d, tr, W, D, facade, span, RED, 7, dashed=True)
                else:
                    for span in product_spans:
                        _draw_lane_segment(d, tr, W, D, facade, span, RED, 7)
                continue
            for piece in pieces:
                span = _piece_span(piece)
                if span is None:
                    continue
                kind = piece.get("kind")
                within_tol = bool(piece.get("within_tol"))
                if kind == "matched":
                    for product_span in product_spans:
                        overlap = _overlap(product_span, span)
                        if overlap is not None:
                            _draw_lane_segment(d, tr, W, D, facade, overlap, GREEN, 7)
                elif kind == "missing":
                    color = ORANGE if within_tol else RED
                    for gt_span in gt_spans:
                        overlap = _overlap(gt_span, span)
                        if overlap is not None:
                            if within_tol:
                                _draw_lane_segment(d, tr, W, D, facade, overlap, BAND, 11)
                            _draw_lane_segment(d, tr, W, D, facade, overlap, color, 7, dashed=True)
                elif kind == "extra":
                    color = ORANGE if within_tol else RED
                    for product_span in product_spans:
                        overlap = _overlap(product_span, span)
                        if overlap is not None:
                            if within_tol:
                                _draw_lane_segment(d, tr, W, D, facade, overlap, BAND, 11)
                            _draw_lane_segment(d, tr, W, D, facade, overlap, color, 7)


def _draw_plan_panel(
    d: ImageDraw.ImageDraw,
    ox: int,
    oy: int,
    W: float,
    D: float,
    floor: dict,
    score: dict | None,
    position_tol: float,
    extent_tol: float,
) -> None:
    tr = plan_transform(W, D, scale=SCALE, offset_x=ox, offset_y=oy, margin_m=PLAN_MARGIN_M)
    floor_name = str(floor.get("name"))
    d.text((ox, oy - LABEL_H), _plan_panel_label(floor_name), font=_font(13), fill=TEXT)
    _draw_gt_floor(d, tr, W, D, floor)
    if score is None:
        _draw_no_data(d, ox + 12, oy + 12)
        return
    vwall_records = [
        m for m in score.get("vwall_records", score.get("vwalls", [])) or []
        if isinstance(m, dict)
    ]
    hwall_records = [
        m for m in score.get("hwall_records", score.get("hwalls", [])) or []
        if isinstance(m, dict)
    ]
    _draw_plan_linear_gt_base(d, tr, vwall_records, "v", width=3)
    _draw_plan_linear_gt_base(d, tr, hwall_records, "h", width=3)
    _draw_plan_linear_products(d, tr, vwall_records, "v", position_tol=position_tol, extent_tol=extent_tol, width=5)
    _draw_plan_linear_products(d, tr, hwall_records, "h", position_tol=position_tol, extent_tol=extent_tol, width=5)
    _draw_plan_boundary(d, tr, W, D, score)
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


def _elevation_box(record: dict | None, key: str) -> tuple[tuple[float, float], tuple[float, float]] | None:
    if not isinstance(record, dict):
        return None
    aliases = {
        "truth": ("gt_box", "truth"),
        "read": ("product_box", "read"),
        "gt_box": ("gt_box", "truth"),
        "product_box": ("product_box", "read"),
    }
    box = None
    for candidate in aliases.get(key, (key,)):
        box = record.get(candidate)
        if isinstance(box, dict):
            break
    if not isinstance(box, dict):
        return None
    span = _numeric_pair(box.get("span"))
    z = _numeric_pair(box.get("z"))
    if span is None or z is None:
        return None
    return span, z


def _draw_truth_wire(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    truth_box: tuple[tuple[float, float], tuple[float, float]] | None,
) -> None:
    if truth_box is None:
        return
    span, z = truth_box
    d.rectangle(_box(tr.px(span[0], z[0]), tr.px(span[1], z[1])), outline=TRUTH, width=2)


def _draw_elevation_gt_windows(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    gt: dict,
    facade_name: str,
) -> None:
    for record in gt.get("windows", []) or []:
        if record.get("facade") != facade_name:
            continue
        sill = record.get("sill_m")
        head = record.get("head_m")
        for opening in record.get("openings", []) or []:
            try:
                x0 = float(opening.get("x_m"))
                width = float(opening.get("width_m"))
                z0 = float(opening.get("sill_m", sill))
                z1 = float(opening.get("head_m", head))
            except (TypeError, ValueError):
                continue
            d.rectangle(_box(tr.px(x0, z0), tr.px(x0 + width, z1)), outline=TRUTH, width=2)


def _draw_vertical_tolerance_cues(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    record: dict,
    truth_box: tuple[tuple[float, float], tuple[float, float]] | None,
    *,
    sill_tol: float,
    head_tol: float,
) -> None:
    if truth_box is None:
        return
    deltas = record.get("deltas") if isinstance(record.get("deltas"), dict) else {}
    span, z = truth_box
    cue_span = _numeric_pair((span[0], span[1]))
    if cue_span is None:
        return
    for idx, (key, tol) in enumerate((("sill_m", sill_tol), ("head_m", head_tol))):
        try:
            delta = float(deltas.get(key))
        except (TypeError, ValueError):
            continue
        if abs(delta) <= CUE_EPS_M or abs(delta) > tol:
            continue
        zz = z[idx]
        _fill_band(d, _box(tr.px(cue_span[0], zz - tol), tr.px(cue_span[1], zz + tol)))
        d.line([tr.px(cue_span[0], zz), tr.px(cue_span[1], zz)], fill=TRUTH, width=1)


def _draw_elevation_record(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    record: dict,
    *,
    sill_tol: float,
    head_tol: float,
) -> None:
    status = record.get("status")
    truth_box = _elevation_box(record, "truth")
    read_box = _elevation_box(record, "read")
    if status == "complete":
        if read_box is None:
            return
        span, z = read_box
        d.rectangle(_box(tr.px(span[0], z[0]), tr.px(span[1], z[1])), outline=GREEN, width=3)
        return
    if status == "within_tol":
        if read_box is not None:
            span, z = read_box
            d.rectangle(
                _box(tr.px(span[0], z[0]), tr.px(span[1], z[1])),
                fill=FILL_DRIFT,
                outline=ORANGE,
                width=3,
            )
        _draw_vertical_tolerance_cues(d, tr, record, truth_box, sill_tol=sill_tol, head_tol=head_tol)
        return
    if status == "miss":
        if truth_box is None:
            return
        span, z = truth_box
        _dashed_box(d, _box(tr.px(span[0], z[0]), tr.px(span[1], z[1])), None, RED, 3)
        return
    if status == "extra":
        if read_box is None:
            return
        span, z = read_box
        d.rectangle(_box(tr.px(span[0], z[0]), tr.px(span[1], z[1])), fill=FILL_R, outline=RED, width=3)


def _draw_elevation_boundary(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    floors: list[dict],
    facade: str,
    span_limit: float,
    elevation_sidecar: dict | None,
) -> None:
    facade_name = FACADE_NAMES[facade]
    boundary = (elevation_sidecar or {}).get("boundary") if isinstance(elevation_sidecar, dict) else None
    facade_boundary = (boundary or {}).get(facade_name) if isinstance(boundary, dict) else None
    floors_boundary = (facade_boundary or {}).get("floors") if isinstance(facade_boundary, dict) else None
    for floor in floors:
        floor_name = str(floor.get("name"))
        z0 = float(floor.get("z_floor", 0.0))
        z1 = z0 + float(floor.get("ceiling_height", 3.0))
        floor_boundary = (floors_boundary or {}).get(floor_name) if isinstance(floors_boundary, dict) else None
        if not isinstance(floor_boundary, dict):
            continue
        for key, default_x in (("side_left", 0.0), ("side_right", span_limit)):
            match = floor_boundary.get(key)
            if not isinstance(match, dict):
                continue
            status = match.get("status")
            raw_coord = match.get("product") if match.get("product") is not None else match.get("truth")
            try:
                coord = float(raw_coord)
            except (TypeError, ValueError):
                coord = default_x
            p1, p2 = tr.px(coord, z0), tr.px(coord, z1)
            if status in {"complete", "within_tol"}:
                color = GREEN if status == "complete" else ORANGE
                d.line([p1, p2], fill=color, width=5)
            elif status == "miss":
                _dashed(d, p1, p2, RED, 5, dash=7, gap=4)
            elif status == "no_data":
                d.line([p1, p2], fill=REFERENCE, width=3)


def _draw_elevation_floor_lines(
    d: ImageDraw.ImageDraw,
    tr: MetricTransform,
    facade_name: str,
    span_limit: float,
    elevation_sidecar: dict | None,
) -> None:
    if not isinstance(elevation_sidecar, dict):
        return
    floor_lines = elevation_sidecar.get("floor_lines")
    if not isinstance(floor_lines, dict):
        return
    score = floor_lines.get(facade_name)
    if not isinstance(score, dict):
        return

    for z in score.get("gt_floor_lines") or []:
        try:
            zz = float(z)
        except (TypeError, ValueError):
            continue
        d.line([tr.px(0, zz), tr.px(span_limit, zz)], fill=TRUTH, width=2)

    if score.get("no_data") is True:
        px, py = tr.px(0.25, 0.25)
        _draw_no_data(d, px, py)
        return

    for match in score.get("matches") or []:
        if not isinstance(match, dict):
            continue
        status = match.get("status")
        try:
            gt_z = float(match.get("gt_z"))
        except (TypeError, ValueError):
            continue
        product_z_raw = match.get("product_z")
        if product_z_raw is None or status == "miss":
            _dashed(d, tr.px(0, gt_z), tr.px(span_limit, gt_z), RED, 4, dash=7, gap=4)
            continue
        try:
            product_z = float(product_z_raw)
        except (TypeError, ValueError):
            continue
        if status == "within_tol":
            _fill_band(d, _box(tr.px(0, product_z - 0.05), tr.px(span_limit, product_z + 0.05)))
            d.line([tr.px(0, product_z), tr.px(span_limit, product_z)], fill=ORANGE, width=4)
        else:
            d.line([tr.px(0, product_z), tr.px(span_limit, product_z)], fill=GREEN, width=4)

    for extra in score.get("extras") or []:
        if not isinstance(extra, dict):
            continue
        try:
            product_z = float(extra.get("product_z"))
        except (TypeError, ValueError):
            continue
        d.line([tr.px(0, product_z), tr.px(span_limit, product_z)], fill=RED, width=4)


def _draw_elevation_panel(
    d: ImageDraw.ImageDraw,
    ox: int,
    oy: int,
    gt: dict,
    facade: str,
    elevation_sidecar: dict | None,
    *,
    sill_tol: float,
    head_tol: float,
) -> None:
    floors = list(gt.get("floors", []))
    facade_name = FACADE_NAMES[facade]
    facade_data = (
        (elevation_sidecar.get("facades") or {}).get(facade_name)
        if isinstance(elevation_sidecar, dict)
        else None
    )
    sidecar_span = facade_data.get("span_limit_m") if isinstance(facade_data, dict) else None
    try:
        span_limit = float(sidecar_span)
    except (TypeError, ValueError):
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
    d.text((ox, oy - LABEL_H), f"{facade_name} elevation", font=_font(13), fill=TEXT)
    d.rectangle(tr.rect(0, 0, span_limit, height), fill=GT_FILL, outline=REFERENCE, width=6)
    _draw_elevation_gt_windows(d, tr, gt, facade_name)
    for floor in floors:
        z = float(floor.get("z_floor", 0.0))
        if z > 0:
            d.line([tr.px(0, z), tr.px(span_limit, z)], fill=REFERENCE, width=4)
    _draw_elevation_boundary(d, tr, floors, facade, span_limit, elevation_sidecar)
    _draw_elevation_floor_lines(d, tr, facade_name, span_limit, elevation_sidecar)

    if not isinstance(elevation_sidecar, dict) or not elevation_sidecar or not isinstance(facade_data, dict):
        _draw_no_elevation_score(d, ox + 12, oy + 12)
        return

    orientation = str(facade_data.get("orientation") or "aligned")
    if orientation in {"flipped", "ambiguous"}:
        label = "flip" if orientation == "flipped" else "ambig"
        d.text((ox + max(12, tr.width_px - 48), oy + 8), label, font=_font(12), fill=ORANGE)

    for floor in floors:
        floor_name = str(floor.get("name"))
        score = (facade_data.get("floors") or {}).get(floor_name)
        if not isinstance(score, dict):
            _draw_no_data(d, ox + 12, oy + 12)
            continue
        if score.get("no_data") is True:
            z0 = float(floor.get("z_floor", 0.0))
            z1 = z0 + float(floor.get("ceiling_height", 3.0))
            px, py = tr.px(0.25, (z0 + z1) / 2.0)
            _draw_no_data(d, px, py)
            continue
        for record in (score.get("matches") or []) + (score.get("extras") or []):
            if isinstance(record, dict):
                _draw_truth_wire(d, tr, _elevation_box(record, "truth"))
        for record in score.get("matches") or []:
            if isinstance(record, dict):
                _draw_elevation_record(d, tr, record, sill_tol=sill_tol, head_tol=head_tol)
        for record in score.get("extras") or []:
            if isinstance(record, dict):
                _draw_elevation_record(d, tr, record, sill_tol=sill_tol, head_tol=head_tol)


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
        1120,
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
    position_tol = float(tol.get("position_tol_m", wall_tol))
    extent_tol = float(tol.get("extent_tol_m", wall_tol))
    win_tol = float(tol.get("window_centre_tol_m", 0.40))
    elev_along_tol = float(tol.get("elevation_along_tol_m", win_tol))
    sill_tol = float(tol.get("sill_tol_m", 0.30))
    head_tol = float(tol.get("head_tol_m", 0.30))
    overlap_accept = float(tol.get("overlap_accept", 0.75))
    floor_line_tol = float(tol.get("floor_line_tol_m", 0.30))
    d.text((14, 12), f"{stage} grade", font=_font(18), fill=TEXT)
    d.text(
        (14, 40),
        (
            "source score_vs_gt.json; "
            f"plan position/extent tol={position_tol:.2f}/{extent_tol:.2f}m; "
            f"elev overlap_accept={overlap_accept:.2f}; floor_line_tol={floor_line_tol:.2f}m"
        ),
        font=_font(11),
        fill=SUBTLE,
    )
    lx, ly = 14, 63
    d.rectangle([lx, ly + 1, lx + 28, ly + 13], outline=TRUTH, width=2)
    d.text((lx + 34, ly), "gray = gt truth", font=_font(11), fill=SUBTLE)
    lx += 130
    d.rectangle([lx, ly + 1, lx + 28, ly + 13], outline=GREEN, width=2)
    d.text((lx + 34, ly), "complete", font=_font(11), fill=SUBTLE)
    lx += 104
    d.rectangle([lx, ly + 1, lx + 28, ly + 13], outline=ORANGE, width=2)
    d.text((lx + 34, ly), "within-tol", font=_font(11), fill=SUBTLE)
    lx += 112
    _dashed_box(d, [lx, ly + 1, lx + 28, ly + 13], None, RED, 2)
    d.text((lx + 34, ly), "miss", font=_font(11), fill=SUBTLE)
    lx += 78
    d.rectangle([lx, ly + 1, lx + 28, ly + 13], fill=FILL_R, outline=RED, width=2)
    d.text((lx + 34, ly), "extra", font=_font(11), fill=SUBTLE)
    lx += 82
    _fill_band(d, [lx, ly + 1, lx + 28, ly + 13])
    d.text((lx + 34, ly), "orange tol band", font=_font(11), fill=SUBTLE)
    lx += 104
    d.line([(lx, ly + 7), (lx + 28, ly + 7)], fill=REFERENCE, width=5)
    d.text((lx + 34, ly), "gray line = reference / no data", font=_font(11), fill=SUBTLE)

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
            position_tol,
            extent_tol,
        )

    elevation_sidecar = score_sidecar.get("elevation")
    elev_y = HEADER + plan_row_h + PANEL_GAP + LABEL_H
    for idx, facade in enumerate(FACADE_CODES):
        col = idx % 2
        row = idx // 2
        ox = col * (facade_w + PANEL_GAP)
        oy = elev_y + row * (elev_row_h + PANEL_GAP)
        _draw_elevation_panel(
            d,
            ox,
            oy,
            gt,
            facade,
            elevation_sidecar,
            sill_tol=sill_tol,
            head_tol=head_tol,
        )
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
