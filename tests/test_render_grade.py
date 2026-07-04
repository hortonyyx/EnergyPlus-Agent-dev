from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_grade  # noqa: E402


def _gt(*, windows: bool = False) -> dict:
    openings = []
    if windows:
        openings = [
            {
                "facade": "North",
                "floor": "Floor 1",
                "sill_m": 1.0,
                "head_m": 2.6,
                "openings": [{"x_m": 1.0, "width_m": 2.0, "sill_m": 1.0, "head_m": 2.6}],
            }
        ]
    return {
        "case": "tiny",
        "footprint": {"W_m": 10.0, "D_m": 4.0},
        "floors": [
            {
                "name": "Floor 1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "zones": [
                    {"id": "A", "role": "office", "rect_m": [0.0, 0.0, 5.0, 4.0]},
                    {"id": "B", "role": "office", "rect_m": [5.0, 0.0, 10.0, 4.0]},
                ],
            }
        ],
        "windows": openings,
        "doors": [],
    }


def _wall_record(
    status: str = "complete",
    *,
    product: list[float] | None = None,
    gt: list[float] | None = None,
    pieces: list[dict] | None = None,
    orientation: str = "v",
    lateral_drift: bool = False,
    extent_drift: bool = False,
    extent_start_drift: bool = False,
    extent_end_drift: bool = False,
) -> dict:
    return {
        "status": status,
        "orientation": orientation,
        "truth": gt[0] if gt else None,
        "read": product[0] if product else None,
        "delta": round(product[0] - gt[0], 3) if product and gt else None,
        "lateral_drift": lateral_drift,
        "extent_drift": extent_drift,
        "extent_start_drift": extent_start_drift,
        "extent_end_drift": extent_end_drift,
        "product": product,
        "gt": gt,
        "product_intervals": [product] if product else [],
        "gt_intervals": [gt] if gt else [],
        "pieces": pieces or [],
    }


def _sidecar() -> dict:
    return {
        "stage": "0_reading",
        "attempt": 1,
        "source": "attempt_output",
        "scorer_schema": "7",
        "tolerances": {
            "wall_tol_m": 0.30,
            "window_centre_tol_m": 0.40,
            "elevation_along_tol_m": 0.40,
            "sill_tol_m": 0.30,
            "head_tol_m": 0.30,
            "width_tol_m": 0.40,
            "position_tol_m": 0.30,
            "extent_tol_m": 0.30,
            "complete_eps_m": 0.05,
            "overlap_accept": 0.75,
            "overlap_complete": 0.95,
            "floor_line_tol_m": 0.30,
        },
        "scores": {
            "1f_view": {
                "floor": "Floor 1",
                "vwalls": [],
                "hwalls": [],
                "vwall_records": [_wall_record(product=[5.0, 0.0, 4.0], gt=[5.0, 0.0, 4.0])],
                "hwall_records": [],
                "windows": {"N": [], "S": [], "E": [], "W": []},
                "extra_window_records": {"N": [], "S": [], "E": [], "W": []},
            }
        },
    }


def _elevation_floor(
    *,
    facade: str = "North",
    floor: str = "Floor 1",
    matches: list[dict] | None = None,
    extras: list[dict] | None = None,
    no_data: bool = False,
) -> dict:
    return {
        "facade": facade,
        "floor": floor,
        "orientation": "aligned",
        "no_data": no_data,
        "gt_count": len(matches or []),
        "read_count": len(matches or []) + len(extras or []),
        "matched_total": sum(1 for m in matches or [] if m.get("status") in {"complete", "within_tol"}),
        "placed_hit_total": sum(1 for m in matches or [] if m.get("status") == "complete"),
        "complete_total": sum(1 for m in matches or [] if m.get("status") == "complete"),
        "within_tol_total": sum(1 for m in matches or [] if m.get("status") == "within_tol"),
        "matches": matches or [],
        "extras": extras or [],
    }


def _elevation_record(
    status: str,
    *,
    gt_span: list[float] | None = None,
    gt_z: list[float] | None = None,
    product_span: list[float] | None = None,
    product_z: list[float] | None = None,
    orientation: str = "aligned",
) -> dict:
    gt_box = None
    if gt_span is not None and gt_z is not None:
        gt_box = {
            "id": "North/Floor 1/0",
            "span": gt_span,
            "z": gt_z,
            "center": sum(gt_span) / 2,
            "width": gt_span[1] - gt_span[0],
        }
    product_box = None
    if product_span is not None and product_z is not None:
        product_box = {
            "span": product_span,
            "z": product_z,
            "center": sum(product_span) / 2,
            "width": product_span[1] - product_span[0],
            "source_id": "R1",
            "source_span": product_span,
        }
    return {
        "status": status,
        "facade": "North",
        "floor": "Floor 1",
        "orientation": orientation,
        "source_id": "R1" if product_box else None,
        "product_box": product_box,
        "gt_box": gt_box,
        "overlap_ratio": 1.0 if status == "complete" else 0.8 if status == "within_tol" else 0.0,
        "gt_coverage": 1.0,
        "product_coverage": 1.0,
    }


def _floor_lines(no_data: bool = False) -> dict:
    return {
        facade: {
            "facade": facade,
            "gt_floor_lines": [0.0, 3.0],
            "product_floor_lines": [] if no_data else [0.0, 3.0],
            "matches": [] if no_data else [
                {"facade": facade, "gt_z": 0.0, "product_z": 0.0, "status": "complete", "delta": 0.0},
                {"facade": facade, "gt_z": 3.0, "product_z": 3.0, "status": "complete", "delta": 0.0},
            ],
            "extras": [],
            "no_data": no_data,
            "no_data_reason": "no_product_floor_line_source" if no_data else None,
        }
        for facade in ("North", "South", "East", "West")
    }


def _boundary() -> dict:
    return {
        facade: {
            "floors": {
                "Floor 1": {
                    "side_left": {"source_boundary": "W", "status": "complete", "truth": 0.0, "product": 0.0, "delta": 0.0},
                    "side_right": {"source_boundary": "E", "status": "complete", "truth": span, "product": span, "delta": 0.0},
                }
            }
        }
        for facade, span in {"North": 10.0, "South": 10.0, "East": 4.0, "West": 4.0}.items()
    }


def _with_elevation(
    sidecar: dict,
    floors_by_facade: dict[str, dict[str, dict]] | None = None,
    *,
    floor_lines: dict | None = None,
    boundary: dict | None = None,
    orientations: dict[str, str] | None = None,
) -> dict:
    out = copy.deepcopy(sidecar)
    floors_by_facade = floors_by_facade or {}
    orientations = orientations or {}
    facades = {}
    for facade in ("North", "South", "East", "West"):
        span = 10.0 if facade in {"North", "South"} else 4.0
        facades[facade] = {
            "orientation": orientations.get(facade, "aligned"),
            "span_limit_m": span,
            "floors": floors_by_facade.get(
                facade,
                {"Floor 1": _elevation_floor(facade=facade, floor="Floor 1")},
            ),
        }
    out["elevation"] = {
        "summary": {},
        "facades": facades,
        "floor_lines": floor_lines if floor_lines is not None else _floor_lines(),
        "boundary": boundary if boundary is not None else _boundary(),
        "evidence": [],
    }
    return out


def _count_color(img, color, box=None) -> int:
    view = img.crop(box) if box else img
    return sum(1 for px in view.getdata() if px == color)


def _count_near(img, color, box=None, tol: int = 8) -> int:
    view = img.crop(box) if box else img
    return sum(1 for px in view.getdata() if all(abs(int(px[i]) - color[i]) <= tol for i in range(3)))


def _plan_tr() -> render_grade.MetricTransform:
    return render_grade.plan_transform(
        10.0,
        4.0,
        scale=render_grade.SCALE,
        offset_x=0,
        offset_y=render_grade.HEADER + render_grade.LABEL_H,
        margin_m=render_grade.PLAN_MARGIN_M,
    )


def _plan_px(x: float, y: float) -> tuple[int, int]:
    return tuple(round(v) for v in _plan_tr().px(x, y))


def _plan_window_px(facade: str, a: float, b: float) -> tuple[int, int]:
    p1, p2 = render_grade._lane(_plan_tr(), 10.0, 4.0, facade, a, b)
    return round((p1[0] + p2[0]) / 2), round((p1[1] + p2[1]) / 2)


def _n_elevation_tr(height: float = 3.0) -> render_grade.MetricTransform:
    panel_h = int((4.0 + 2 * render_grade.PLAN_MARGIN_M) * render_grade.SCALE)
    elev_y = render_grade.HEADER + (render_grade.LABEL_H + panel_h) + render_grade.PANEL_GAP + render_grade.LABEL_H
    return render_grade.MetricTransform(
        min_x=-0.9,
        min_y=-0.9,
        max_x=10.0 + 0.9,
        max_y=height + 0.9,
        scale=render_grade.SCALE,
        offset_x=0,
        offset_y=elev_y,
        flip_y=True,
    )


def _w_facade_box(img) -> tuple[int, int, int, int]:
    facade_w = int((10.0 + 1.8) * render_grade.SCALE)
    facade_h = int((3.0 + 1.8) * render_grade.SCALE)
    plan_h = render_grade.LABEL_H + int((4.0 + 2 * render_grade.PLAN_MARGIN_M) * render_grade.SCALE)
    elev_h = render_grade.LABEL_H + facade_h
    x0 = facade_w + render_grade.PANEL_GAP
    y0 = render_grade.HEADER + plan_h + render_grade.PANEL_GAP + render_grade.LABEL_H + elev_h + render_grade.PANEL_GAP
    return (x0, y0, min(img.width, x0 + 320), min(img.height, y0 + facade_h))


def test_render_grade_draws_hit_from_sidecar():
    img = render_grade.render_grade("0_reading", _sidecar(), _gt())

    assert img.mode == "RGB"
    assert _count_color(img, render_grade.GREEN) > 100


def test_render_grade_draws_reference_geometry_gray_not_hit_green_without_product_records():
    sidecar = copy.deepcopy(_sidecar())
    sidecar["scores"]["1f_view"]["vwall_records"] = []

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    content = (0, render_grade.HEADER, img.width, img.height)
    assert _count_color(img, render_grade.REFERENCE, content) > 1000
    assert _count_color(img, render_grade.GREEN, content) == 0


def test_render_grade_red_line_plan_wall_uses_product_extent_not_gt_extent():
    sidecar = _sidecar()
    sidecar["scores"]["1f_view"]["vwall_records"] = [
        _wall_record(
            "miss",
            product=[5.0, 0.0, 2.0],
            gt=[5.0, 0.0, 4.0],
            pieces=[
                {"kind": "matched", "span": [0.0, 2.0], "within_tol": True},
                {"kind": "missing", "span": [2.0, 4.0], "within_tol": False},
            ],
        )
    ]

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert img.getpixel(_plan_px(5.0, 1.0)) == render_grade.GREEN
    assert img.getpixel(_plan_px(5.0, 3.5)) != render_grade.GREEN
    miss = _plan_px(5.0, 3.0)
    assert _count_color(img, render_grade.RED, (miss[0] - 4, miss[1] - 45, miss[0] + 5, miss[1] + 45)) > 10


def _is_band(px) -> bool:
    """The orange tolerance band is now semi-transparent, so its pixels are the
    orange wash blended over whatever is underneath (gt shows through) — not the
    opaque BAND color. It reads as an orange tint (r>g>b) that is lighter than the
    solid ORANGE product (g high), which distinguishes band from product."""
    r, g, b = px[0], px[1], px[2]
    return r > g > b and (r - b) >= 25 and g >= 150


def test_render_grade_lateral_wall_drift_draws_acceptance_strip_and_orange_product():
    sidecar = _sidecar()
    sidecar["scores"]["1f_view"]["vwall_records"] = [
        _wall_record(
            "within_tol",
            product=[5.2, 0.0, 4.0],
            gt=[5.0, 0.0, 4.0],
            lateral_drift=True,
        )
    ]

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert img.getpixel(_plan_px(5.2, 2.0)) == render_grade.ORANGE
    assert _is_band(img.getpixel(_plan_px(4.8, 2.0)))
    assert img.getpixel(_plan_px(5.2, 2.0)) != render_grade.GREEN


def test_render_grade_within_tol_missing_piece_remains_dashed():
    sidecar = _sidecar()
    sidecar["tolerances"]["extent_tol_m"] = 0.60
    sidecar["scores"]["1f_view"]["vwall_records"] = [
        _wall_record(
            "within_tol",
            product=[5.0, 0.0, 3.45],
            gt=[5.0, 0.0, 4.0],
            pieces=[
                {"kind": "matched", "span": [0.0, 3.45], "within_tol": True},
                {"kind": "missing", "span": [3.45, 4.0], "within_tol": True},
            ],
            extent_drift=True,
            extent_end_drift=True,
        )
    ]

    img = render_grade.render_grade("0_reading", sidecar, _gt())
    start = _plan_px(5.0, 3.45)
    end = _plan_px(5.0, 4.0)
    crop = (start[0] - 4, min(start[1], end[1]), start[0] + 5, max(start[1], end[1]) + 1)

    orange_pixels = _count_color(img, render_grade.ORANGE, crop)
    assert orange_pixels > 20
    assert orange_pixels < 150
    assert _is_band(img.getpixel(_plan_px(5.0, 4.35)))


def test_render_grade_red_line_plan_window_uses_product_span_not_gt_span():
    sidecar = _sidecar()
    sidecar["scores"]["1f_view"]["windows"]["N"] = [
        {
            "status": "complete",
            "facade": "N",
            "truth": [1.0, 3.0],
            "read": [4.0, 6.0],
            "product": [4.0, 6.0],
            "gt": [1.0, 3.0],
            "product_intervals": [[4.0, 6.0]],
            "gt_intervals": [[1.0, 3.0]],
            "pieces": [],
        }
    ]

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert img.getpixel(_plan_window_px("N", 4.0, 6.0)) == render_grade.GREEN
    assert img.getpixel(_plan_window_px("N", 1.0, 3.0)) != render_grade.GREEN


def test_render_grade_draws_boundary_hit_green_from_sidecar():
    sidecar = _sidecar()
    sidecar["scores"]["1f_view"]["boundary"] = {
        "S": {"truth": 0.0, "read": 0.0, "delta": 0.0},
        "N": {"truth": 4.0, "read": 4.0, "delta": 0.0},
        "W": {"truth": 0.0, "read": 0.0, "delta": 0.0},
        "E": {"truth": 10.0, "read": 10.0, "delta": 0.0},
    }

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert img.getpixel(_plan_px(2.0, 0.0)) == render_grade.GREEN


def test_render_grade_draws_boundary_miss_red_dashes_from_sidecar():
    sidecar = _sidecar()
    sidecar["scores"]["1f_view"]["boundary"] = {
        "S": {"truth": 0.0, "read": None, "delta": None},
    }

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    south = _plan_px(2.0, 0.0)
    assert _count_color(img, render_grade.RED, (south[0] - 80, south[1] - 4, south[0] + 80, south[1] + 5)) > 20


def test_render_grade_red_line_elevation_window_uses_product_box_not_gt_box():
    floor = _elevation_floor(
        matches=[
            _elevation_record(
                "complete",
                gt_span=[1.0, 3.0],
                gt_z=[1.0, 2.6],
                product_span=[5.0, 7.0],
                product_z=[0.25, 0.75],
            )
        ]
    )

    img = render_grade.render_grade(
        "0_reading",
        _with_elevation(_sidecar(), {"North": {"Floor 1": floor}}),
        _gt(windows=True),
    )
    tr = _n_elevation_tr()

    assert img.getpixel(tuple(round(v) for v in tr.px(6.0, 0.75))) == render_grade.GREEN
    assert img.getpixel(tuple(round(v) for v in tr.px(2.0, 2.6))) != render_grade.GREEN


def test_render_grade_draws_elevation_miss_annotation_plus_extra_product():
    floor = _elevation_floor(
        matches=[
            _elevation_record("miss", gt_span=[1.0, 3.0], gt_z=[1.0, 2.6]),
        ],
        extras=[
            _elevation_record("extra", product_span=[5.0, 7.0], product_z=[1.2, 2.4]),
        ],
    )

    img = render_grade.render_grade(
        "0_reading",
        _with_elevation(_sidecar(), {"North": {"Floor 1": floor}}),
        _gt(windows=True),
    )

    assert _count_color(img, render_grade.FILL_R) > 100
    assert _count_color(img, render_grade.RED) > 100


def test_render_grade_draws_elevation_within_tol_orange_band():
    floor = _elevation_floor(
        matches=[
            _elevation_record(
                "within_tol",
                gt_span=[1.0, 3.0],
                gt_z=[1.0, 2.6],
                product_span=[1.1, 3.1],
                product_z=[1.1, 2.7],
            )
        ]
    )

    img = render_grade.render_grade(
        "0_reading",
        _with_elevation(_sidecar(), {"North": {"Floor 1": floor}}),
        _gt(windows=True),
    )

    assert _count_color(img, render_grade.BAND) > 100
    assert _count_color(img, render_grade.ORANGE) > 20


def test_render_grade_draws_floor_line_miss_extra_and_no_data_distinctly():
    floor_lines = _floor_lines()
    floor_lines["North"] = {
        "facade": "North",
        "gt_floor_lines": [0.0, 3.0],
        "product_floor_lines": [0.0, 2.5],
        "matches": [
            {"facade": "North", "gt_z": 0.0, "product_z": 0.0, "status": "complete", "delta": 0.0},
            {"facade": "North", "gt_z": 3.0, "product_z": None, "status": "miss", "delta": None},
        ],
        "extras": [{"facade": "North", "product_z": 2.5, "status": "extra"}],
        "no_data": False,
        "no_data_reason": None,
    }
    floor_lines["West"]["no_data"] = True
    floor_lines["West"]["matches"] = []
    floor_lines["West"]["product_floor_lines"] = []

    img = render_grade.render_grade("0_reading", _with_elevation(_sidecar(), floor_lines=floor_lines), _gt())

    tr = _n_elevation_tr()
    miss = tuple(round(v) for v in tr.px(5.0, 3.0))
    extra = tuple(round(v) for v in tr.px(5.0, 2.5))
    assert _count_color(img, render_grade.RED, (miss[0] - 60, miss[1] - 4, miss[0] + 60, miss[1] + 5)) > 10
    assert img.getpixel(extra) == render_grade.RED


def test_render_grade_draws_serialized_elevation_boundary():
    boundary = _boundary()
    boundary["North"]["floors"]["Floor 1"]["side_left"] = {
        "source_boundary": "W",
        "status": "complete",
        "truth": 0.0,
        "product": 0.2,
        "delta": 0.2,
    }
    boundary["North"]["floors"]["Floor 1"]["side_right"] = {
        "source_boundary": "E",
        "status": "miss",
        "truth": 10.0,
        "product": None,
        "delta": None,
    }

    img = render_grade.render_grade("0_reading", _with_elevation(_sidecar(), boundary=boundary), _gt())
    tr = _n_elevation_tr()

    assert img.getpixel(tuple(round(v) for v in tr.px(0.2, 1.5))) == render_grade.GREEN
    right = tuple(round(v) for v in tr.px(10.0, 1.5))
    assert _count_color(img, render_grade.RED, (right[0] - 4, right[1] - 40, right[0] + 5, right[1] + 40)) > 10


def test_render_grade_draws_orientation_cue_for_flipped_facade():
    img = render_grade.render_grade(
        "0_reading",
        _with_elevation(_sidecar(), orientations={"North": "flipped"}),
        _gt(),
    )

    assert _count_color(img, render_grade.ORANGE) > 0


def test_render_grade_absent_elevation_section_reports_no_elevation_score():
    sidecar = _sidecar()

    img = render_grade.render_grade("0_reading", sidecar, _gt(windows=True))

    assert _count_color(img, render_grade.RED) > 0


def test_render_grade_plan_label_marks_secondary():
    assert render_grade._plan_panel_label("Floor 1") == "Floor 1 plan-derived (secondary)"


def test_render_grade_draws_no_data_for_missing_score_floor():
    sidecar = copy.deepcopy(_sidecar())
    sidecar["scores"] = {}

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert _count_near(img, render_grade.SUBTLE, tol=8) > 0


def test_render_grade_empty_facade_is_not_no_data():
    sidecar = _with_elevation(_sidecar())

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    w_box = _w_facade_box(img)
    assert _count_color(img, render_grade.RED, w_box) == 0
    assert _count_color(img, render_grade.FILL_R, w_box) == 0


def test_render_grade_missing_facade_key_is_no_data():
    sidecar = _with_elevation(_sidecar())
    sidecar["elevation"]["facades"]["West"]["floors"]["Floor 1"]["no_data"] = True

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert _count_near(img, render_grade.SUBTLE, _w_facade_box(img), tol=8) > 0
