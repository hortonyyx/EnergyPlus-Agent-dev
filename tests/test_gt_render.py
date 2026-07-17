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
import pytest
from src.agent.judge.gt_render_model import gt_to_render_model, render_elevation_model, render_plan_model
from b4b_contract_fixture import make_b4b_gt_document

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
    assert plan.size == (1724, 634) and elev.size == (1828, 980)  # legacy sm21 pixel lock


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


def test_v3_candidate_watermark_and_plan_uses_concave_vertices():
    from test_gt_schema import _rehash, _payload
    raw = _payload(ring=[[0.0, 0.0], [5.0, 0.0], [5.0, 1.0], [2.0, 1.0], [2.0, 4.0], [0.0, 4.0]])
    raw = _rehash(raw)
    from src.agent.judge.gt_schema import GroundTruthV3
    model = gt_to_render_model(GroundTruthV3.model_validate(raw))
    image = render_plan_model(model)
    primitives = image.info["render_primitives"]
    assert len(primitives[0]["points"]) == 6  # never reduce an L to its bbox
    assert image.getpixel((2, image.height - 2))[0] < 120  # candidate watermark is mandatory


def _captured_render_text(monkeypatch, render):
    """Test-side structured ledger of renderer text without pixel-coordinate coupling."""
    from PIL import ImageDraw
    original = ImageDraw.ImageDraw.text
    seen = []
    def record(draw, xy, text, *args, **kwargs):
        seen.append(str(text))
        return original(draw, xy, text, *args, **kwargs)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    image = render()
    return image, seen


def test_v3_dynamic_elevation_panels_partial_and_plan_only_legends(monkeypatch):
    from test_gt_schema import _opening_payload, _rehash
    from src.agent.judge.gt_schema import GroundTruthV3
    raw = _opening_payload(observed=True)
    extra = {"id": "elev-N", "kind": "elevation", "floor_ids": ["F1"], "projection_surface_key": "surface-N",
             "facade_family": "North", "view_kind": "partial", "world_along_coverage": {"lo": 0.0, "hi": 2.0},
             "direction_semantics": "building_axis", "azimuth_deg": None}
    raw["sources"][0]["views"].append(extra)
    raw["sources"][0]["views"].sort(key=lambda item: item["id"])
    north = next(item for item in raw["floors"][0]["boundary_segments"] if item["facade_family"] == "North")
    north["projection_surface_keys"] = ["surface-N"]
    raw["openings"][0]["z_interval"] = None
    raw = _rehash(raw)
    image, text = _captured_render_text(monkeypatch, lambda: render_elevation_model(gt_to_render_model(GroundTruthV3.model_validate(raw))))
    assert len(image.info["render_primitives"]) == 2  # keys, not a fixed facade quartet
    assert image.width > 0
    assert "PLAN-ONLY / Z UNSET" in text and not any("NA" in item for item in text)
    assert "PARTIAL — CLIPPED AT COVERAGE" in text


def test_v3_null_north_omits_true_north_vector():
    from test_gt_schema import _document
    image = render_plan_model(gt_to_render_model(_document()))
    assert image.info["north_vectors"] == [None]


def test_v3_no_elevation_binding_has_explicit_panel_text(monkeypatch):
    from test_gt_schema import _document
    image, text = _captured_render_text(monkeypatch, lambda: render_elevation_model(gt_to_render_model(_document())))
    assert image.width > 0 and "NO ELEVATION SOURCE BINDING" in text


def test_b4b_contract_fixture_is_typed_and_contains_only_b4a_inputs():
    document = make_b4b_gt_document(observed_elevation=True)
    assert len(document.floors) == 2 and document.north_axis_deg == 27.5 and document.openings
    assert any(segment.depth > 0 and not segment.visible_intervals for floor in document.floors for segment in floor.boundary_segments)
    assert any(segment.depth > 0 and segment.visible_intervals for floor in document.floors for segment in floor.boundary_segments)
    assert any(len(segment.projection_surface_keys) == 2 for floor in document.floors for segment in floor.boundary_segments)
    assert any(not segment.projection_surface_keys for floor in document.floors for segment in floor.boundary_segments)
    assert not {"scoreable", "claim_status", "denominator", "completeness"} & set(document.model_dump())


def test_v3_absolute_along_interval_and_elevation_floor_z_are_preserved():
    document = make_b4b_gt_document(); model = gt_to_render_model(document)
    plan = render_plan_model(model)
    opening = next(item for item in document.openings if item.id == "O1")
    assert next(item for item in plan.info["opening_primitives"] if item["id"] == "O1")["points"] == ((opening.world_along_interval.lo, 3.0), (opening.world_along_interval.hi, 3.0))
    elevation = render_elevation_model(model)
    north = [item for item in elevation.info["segment_primitives"] if item["id"].startswith("F2:boundary:North:")][0]
    expected = next(segment for floor in model.floors if floor.floor_id == "F2" for segment in floor.boundary_segments if segment.id == north["id"])
    assert north["z_floor_m"] == 3.0 and north["visible_intervals"] == expected.visible_intervals


def test_v3_verified_header_and_north_vector_without_candidate_watermark():
    from test_gt_schema import _payload, _rehash
    from src.agent.judge.gt_schema import GroundTruthV3
    raw = _rehash(_payload(verified=True, north=27.5))
    image = render_plan_model(gt_to_render_model(GroundTruthV3.model_validate(raw)))
    assert image.info["north_vectors"][0] == pytest.approx((-0.461749, 0.887011), abs=1e-6)
    assert image.getpixel((2, image.height - 2)) == (252, 252, 251)
