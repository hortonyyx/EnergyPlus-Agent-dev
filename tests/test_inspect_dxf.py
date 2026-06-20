"""Tests for inspect_dxf.py on a synthetic 天正-style merged DXF.

Builds (with ezdxf) a single model space holding multiple views (two floor plans +
four elevations) with layers split by COMPONENT TYPE (WALL / WINDOW / DOOR) and 图名
title texts — i.e. the structure inspect_dxf must cope with — then asserts the
inspector reports units, classifies component layers, finds the titles, and spatially
separates the views. Proves the toolchain before the real merged DXF arrives."""

from __future__ import annotations

import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import inspect_dxf as idx  # noqa: E402


def _box(msp, layer, x0, y0, x1, y1):
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
                       dxfattribs={"layer": layer})


def _build_synthetic(path: Path) -> None:
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # millimetres (天正 default)
    for lyr in ("WALL", "WINDOW", "DOOR", "PUB_DIM", "PUB_TEXT"):
        doc.layers.add(lyr)
    msp = doc.modelspace()

    # two floor plans (15000 x 8000 mm), spaced apart in model space
    for i, (ox, title) in enumerate([(0, "一层平面图"), (25000, "二层平面图")]):
        _box(msp, "WALL", ox, 0, ox + 15000, 8000)              # footprint
        msp.add_line((ox + 5000, 0), (ox + 5000, 8000), dxfattribs={"layer": "WALL"})  # partition
        for wx in (ox + 2000, ox + 7000, ox + 12000):           # 3 windows on south wall
            msp.add_line((wx, 0), (wx + 1500, 0), dxfattribs={"layer": "WINDOW"})
        msp.add_line((ox + 500, 0), (ox + 1400, 0), dxfattribs={"layer": "DOOR"})
        msp.add_text(title, dxfattribs={"layer": "PUB_TEXT"}).set_placement((ox + 5000, -1500))

    # four elevations (15000 x 6600 mm), placed below the plans
    for i, (ox, title) in enumerate([(0, "南立面图"), (25000, "北立面图"),
                                     (50000, "东立面图"), (75000, "西立面图")]):
        oy = -20000
        _box(msp, "WALL", ox, oy, ox + 15000, oy + 6600)
        for wx in (ox + 3000, ox + 9000):
            _box(msp, "WINDOW", wx, oy + 4000, wx + 1200, oy + 5800)
        msp.add_text(title, dxfattribs={"layer": "PUB_TEXT"}).set_placement((ox + 5000, oy - 1500))

    doc.saveas(str(path))


def test_inspector_reads_synthetic_tianzheng_dxf(tmp_path):
    p = tmp_path / "merged.dxf"
    _build_synthetic(p)
    rep = idx.inspect(p)

    assert rep["units"] == "mm"
    assert rep["proxy_or_unsupported"] == 0          # plain entities, nothing to explode

    # component layers classified from their names
    kinds = {l["layer"]: l["kind"] for l in rep["layers"]}
    assert kinds["WALL"] == "wall"
    assert kinds["WINDOW"] == "window"
    assert kinds["DOOR"] == "door"

    # all six 图名 titles found
    titles = {t["text"] for t in rep["titles"]}
    assert "一层平面图" in titles and "二层平面图" in titles
    assert "南立面图" in titles and {"北立面图", "东立面图", "西立面图"} <= titles

    # the six views are spatially separated into distinct candidate regions
    assert len(rep["candidate_view_regions"]) >= 6


def test_inspector_flags_units_and_extents(tmp_path):
    p = tmp_path / "merged.dxf"
    _build_synthetic(p)
    rep = idx.inspect(p)
    assert rep["entity_total"] > 0
    # drawing spans the full multi-view layout in mm
    assert rep["extents"][2] - rep["extents"][0] > 80000
