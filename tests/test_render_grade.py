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


def _sidecar() -> dict:
    return {
        "stage": "0_reading",
        "attempt": 1,
        "source": "attempt_output",
        "tolerances": {"wall_tol_m": 0.30, "window_centre_tol_m": 0.40},
        "scores": {
            "1f_view": {
                "floor": "Floor 1",
                "vwalls": [{"truth": 5.0, "read": 5.0, "delta": 0.0}],
                "hwalls": [],
                "extra_vwalls": [],
                "extra_hwalls": [],
                "windows": {"N": [], "S": [], "E": [], "W": []},
                "extra_windows": {"N": [], "S": [], "E": [], "W": []},
            }
        },
    }


def _count_color(img, color, box=None) -> int:
    view = img.crop(box) if box else img
    return sum(1 for px in view.getdata() if px == color)


def _count_near(img, color, box=None, tol: int = 8) -> int:
    view = img.crop(box) if box else img
    return sum(
        1
        for px in view.getdata()
        if all(abs(int(px[i]) - color[i]) <= tol for i in range(3))
    )


def _plan_px(x: float, y: float) -> tuple[int, int]:
    tr = render_grade.plan_transform(
        10.0,
        4.0,
        scale=render_grade.SCALE,
        offset_x=0,
        offset_y=render_grade.HEADER + render_grade.LABEL_H,
        margin_m=render_grade.PLAN_MARGIN_M,
    )
    return tuple(round(v) for v in tr.px(x, y))


def _with_boundary(sidecar: dict, read: float | None = 0.0) -> dict:
    out = copy.deepcopy(sidecar)
    out["scores"]["1f_view"]["boundary"] = {
        "S": {"truth": 0.0, "read": read, "delta": None if read is None else read},
        "N": {"truth": 4.0, "read": 4.0 if read is not None else None, "delta": 0.0 if read is not None else None},
        "W": {"truth": 0.0, "read": 0.0 if read is not None else None, "delta": 0.0 if read is not None else None},
        "E": {"truth": 10.0, "read": 10.0 if read is not None else None, "delta": 0.0 if read is not None else None},
    }
    return out


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


def test_render_grade_draws_reference_geometry_gray_not_hit_green():
    gt = copy.deepcopy(_gt())
    gt["floors"].append(
        {
            "name": "Floor 2",
            "z_floor": 3.0,
            "ceiling_height": 3.0,
            "zones": [
                {"id": "A2", "role": "office", "rect_m": [0.0, 0.0, 5.0, 4.0]},
                {"id": "B2", "role": "office", "rect_m": [5.0, 0.0, 10.0, 4.0]},
            ],
        }
    )
    sidecar = copy.deepcopy(_sidecar())
    sidecar["scores"]["1f_view"]["vwalls"] = []
    sidecar["scores"]["2f_view"] = copy.deepcopy(sidecar["scores"]["1f_view"])
    sidecar["scores"]["2f_view"]["floor"] = "Floor 2"

    img = render_grade.render_grade("0_reading", sidecar, gt)

    content = (0, render_grade.HEADER, img.width, img.height)
    assert _count_color(img, render_grade.REFERENCE, content) > 1000
    assert _count_color(img, render_grade.GREEN, content) == 0


def test_render_grade_draws_miss_dashes_from_sidecar():
    sidecar = _sidecar()
    sidecar["scores"]["1f_view"]["vwalls"][0]["read"] = None
    sidecar["scores"]["1f_view"]["vwalls"][0]["delta"] = None

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert _count_color(img, render_grade.RED) > 20


def test_render_grade_draws_extra_lines_from_sidecar():
    sidecar = _sidecar()
    sidecar["scores"]["1f_view"]["extra_vwalls"] = [7.5]

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert _count_color(img, render_grade.RED) > 20


def test_render_grade_draws_drift_band_from_sidecar_delta():
    sidecar = _sidecar()
    sidecar["scores"]["1f_view"]["vwalls"][0]["read"] = 5.2
    sidecar["scores"]["1f_view"]["vwalls"][0]["delta"] = 0.2

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert _count_color(img, render_grade.BAND) > 100
    assert _count_color(img, render_grade.TRUTH) > 10


def test_render_grade_draws_boundary_hit_green_from_sidecar():
    img = render_grade.render_grade("0_reading", _with_boundary(_sidecar()), _gt())

    assert img.getpixel(_plan_px(2.0, 0.0)) == render_grade.GREEN


def test_render_grade_draws_boundary_miss_red_dashes_from_sidecar():
    sidecar = _with_boundary(_sidecar(), read=None)

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    south = _plan_px(2.0, 0.0)
    box = (south[0] - 80, south[1] - 4, south[0] + 80, south[1] + 5)
    assert _count_color(img, render_grade.RED, box) > 20


def test_render_grade_leaves_boundary_gray_when_sidecar_has_no_boundary_field():
    img = render_grade.render_grade("0_reading", _sidecar(), _gt())

    south = _plan_px(2.0, 0.0)
    box = (south[0] - 8, south[1] - 8, south[0] + 9, south[1] + 9)
    assert _count_color(img, render_grade.REFERENCE, box) > 20


def test_render_grade_draws_elevation_boundary_without_coloring_slab_lines():
    gt = copy.deepcopy(_gt())
    gt["floors"].append(
        {
            "name": "Floor 2",
            "z_floor": 3.0,
            "ceiling_height": 3.0,
            "zones": [
                {"id": "A2", "role": "office", "rect_m": [0.0, 0.0, 5.0, 4.0]},
                {"id": "B2", "role": "office", "rect_m": [5.0, 0.0, 10.0, 4.0]},
            ],
        }
    )
    sidecar = _with_boundary(_sidecar())
    sidecar["scores"]["2f_view"] = copy.deepcopy(sidecar["scores"]["1f_view"])
    sidecar["scores"]["2f_view"]["floor"] = "Floor 2"

    img = render_grade.render_grade("0_reading", sidecar, gt)
    panel_h = int((4.0 + 2 * render_grade.PLAN_MARGIN_M) * render_grade.SCALE)
    elev_y = render_grade.HEADER + (render_grade.LABEL_H + panel_h) + render_grade.PANEL_GAP + render_grade.LABEL_H
    tr = render_grade.MetricTransform(
        min_x=-0.9,
        min_y=-0.9,
        max_x=10.0 + 0.9,
        max_y=6.0 + 0.9,
        scale=render_grade.SCALE,
        offset_x=0,
        offset_y=elev_y,
        flip_y=True,
    )

    assert img.getpixel(tuple(round(v) for v in tr.px(0.0, 1.5))) == render_grade.GREEN
    assert img.getpixel(tuple(round(v) for v in tr.px(5.0, 3.0))) == render_grade.REFERENCE


def test_render_grade_draws_wrong_position_as_miss_ghost_plus_extra():
    sidecar = _sidecar()
    score = sidecar["scores"]["1f_view"]
    score["windows"]["N"] = [{"truth": [1.0, 3.0], "read": None, "centre_delta": None}]
    score["extra_windows"]["N"] = [[5.0, 7.0]]

    img = render_grade.render_grade("0_reading", sidecar, _gt(windows=True))

    assert _count_color(img, render_grade.FILL_R) > 100
    assert _count_color(img, render_grade.RED) > 100


def test_render_grade_draws_no_data_for_missing_score_floor():
    sidecar = copy.deepcopy(_sidecar())
    sidecar["scores"] = {}

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert _count_color(img, render_grade.RED) > 0


def test_render_grade_empty_facade_is_not_no_data():
    sidecar = _sidecar()

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    w_box = _w_facade_box(img)
    assert _count_color(img, render_grade.RED, w_box) == 0
    assert _count_color(img, render_grade.FILL_R, w_box) == 0


def test_render_grade_missing_facade_key_is_no_data():
    sidecar = _sidecar()
    del sidecar["scores"]["1f_view"]["windows"]["W"]

    img = render_grade.render_grade("0_reading", sidecar, _gt())

    assert _count_near(img, render_grade.RED, _w_facade_box(img), tol=60) > 0
