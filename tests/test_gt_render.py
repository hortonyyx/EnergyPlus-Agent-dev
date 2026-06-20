"""Tests for the gt dimension-annotated renderer (backlog #4).

render_gt.py turns an evaluation ground-truth JSON into annotated plan + elevation
PNGs so a human can verify the gt against the original drawings instead of reading
bare coordinates. The rendered pixels need a human to confirm visually; these tests
guard the data-derivation logic (partition / facade-width / height) and that both
views render without crashing on the real sm21 gt and on degenerate inputs.

render_gt is a human/judge-side visualisation tool: reading gt here is allowed (the
gt discipline only forbids gate① + executors — see test_gt_discipline.py)."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_gt as rg  # noqa: E402


def _gt() -> dict:
    # read the gt JSON directly via the tool's own resolver (no judge-package import)
    _, gt = rg._resolve_gt("sm21_anchor")
    return gt


def test_renders_both_views_on_real_gt():
    gt = _gt()
    plan, elev = rg.render_plan(gt), rg.render_elev(gt)
    assert isinstance(plan, Image.Image) and plan.mode == "RGB"
    assert isinstance(elev, Image.Image) and elev.mode == "RGB"
    # plan holds both floor panels side by side -> wider than one footprint
    assert plan.width > gt["footprint"]["W_m"] * rg.SCALE * 2
    assert elev.height > rg._total_height(gt) * rg.SCALE


def test_footprint_and_height_derivation():
    gt = _gt()
    assert rg._total_height(gt) == 6.6                 # max(0+3.0, 3.0+3.6)
    assert rg._facade_width(gt, "South") == 15.0       # N/S span W
    assert rg._facade_width(gt, "North") == 15.0
    assert rg._facade_width(gt, "East") == 8.0         # E/W span D
    assert rg._facade_width(gt, "West") == 8.0


def test_band_partition_derivation():
    gt = _gt()
    f1, f2 = gt["floors"]
    w = gt["footprint"]["W_m"]
    # F1 north band (y 5..8): three offices split at 5, 10
    assert rg._uniq_x(f1["zones"], 5.0, 8.0, w) == [0.0, 5.0, 10.0, 15.0]
    # F2 north band: two meeting rooms split at 7.5
    assert rg._uniq_x(f2["zones"], 5.0, 8.0, w) == [0.0, 7.5, 15.0]
    # F2 south band (y 0..3): four offices split at 3.75 / 7.5 / 11.25
    assert rg._uniq_x(f2["zones"], 0.0, 3.0, w) == [0.0, 3.75, 7.5, 11.25, 15.0]


def test_door_frac_from_note():
    assert rg._door_frac({"note": "main entrance, bottom-left in plan"}) == 0.12
    assert rg._door_frac({"note": "far right"}) == 0.88
    assert rg._door_frac({"note": "corridor west end"}) == 0.5  # no left/right hint


def test_renders_degenerate_gt_without_crashing():
    """Single floor, a facade with 0 windows, no doors at all."""
    gt = {
        "case": "tiny",
        "footprint": {"W_m": 6.0, "D_m": 4.0},
        "floors": [{
            "name": "Floor 1", "z_floor": 0.0, "ceiling_height": 3.0, "zone_count": 1,
            "zones": [{"id": "Z1", "role": "office", "rect_m": [0.0, 0.0, 6.0, 4.0], "note": ""}],
        }],
        "windows": [
            {"facade": "South", "floor": "Floor 1", "count": 1, "sill_m": 1.0, "head_m": 2.2},
            {"facade": "North", "floor": "Floor 1", "count": 0, "sill_m": None, "head_m": None},
        ],
        "doors": [],
    }
    assert rg.render_plan(gt).mode == "RGB"
    assert rg.render_elev(gt).mode == "RGB"
