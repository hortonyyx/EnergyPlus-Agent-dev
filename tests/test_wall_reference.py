"""Wall baseline conversions preserve source topology and report missing evidence."""
import copy
import json

import pytest
from PIL import Image

from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.proposal_edits import apply_proposal_edits
from src.agent.geometry.source_image_overlay import render_source_overlay
from src.agent.geometry.wall_reference import resolve_wall_references, convert_wall_dimensions
from tests.test_source_proposal import _proposal


def reference(identity, boundary_id, offsets):
    return {"id": identity, "boundary_id": boundary_id, "offsets_m": offsets,
            "thickness_m": 0.24, "reference_basis": "synthetic declared reference plane",
            "thickness_scope": "unknown", "evidence_status": "inferred", "source_refs": ["synthetic"]}


def dimension(start="positive", end="negative", value=2760, direction=1):
    return {"id": "span", "axis": "x", "direction": direction, "value": value, "unit": "mm",
            "start": {"wall_id": "west", "side": start, "image": "plan.png", "pixel": [10, 20]},
            "end": {"wall_id": "shared", "side": end, "image": "plan.png", "pixel": [100, 20]},
            "source_refs": ["synthetic"]}


@pytest.fixture
def example(tmp_path):
    proposal = _proposal()
    export_source_proposal(proposal, tmp_path / "base")
    source = json.loads((tmp_path / "base/source_model.json").read_text())
    refs = [reference("west", "space/hall/wall/3", [-0.12, 0.12]),
            reference("shared", "space/hall/wall/1", [-0.12, 0.12])]
    return proposal, source, refs


@pytest.mark.parametrize("sides,value,converted", [
    (("positive", "negative"), 2760, 3),
    (("representative", "representative"), 3000, 3),
    (("negative", "positive"), 3240, 3),
    (("representative", "negative"), 2880, 3),
])
def test_same_walls_different_endpoint_baselines(example, sides, value, converted):
    _, source, refs = example
    walls = resolve_wall_references(source, refs)
    row = convert_wall_dimensions(walls, [dimension(*sides, value)])['dimensions'][0]
    assert row['representative_length_m'] == converted
    assert row['residual_m'] == 0


def test_eccentric_offsets_and_reverse_direction(example):
    _, source, refs = example
    refs[0]["offsets_m"] = [-0.08, 0.16]
    walls = resolve_wall_references(source, refs)
    d = dimension(value=2720)
    row = convert_wall_dimensions(walls, [d])["dimensions"][0]
    assert row["conversion_m"] == 0.28
    assert row["residual_m"] == 0
    d["start"], d["end"] = d["end"], d["start"]
    d["direction"] = -1
    assert convert_wall_dimensions(walls, [d])["dimensions"][0]["residual_m"] == 0


def test_thickness_does_not_imply_half_offsets(example):
    _, source, refs = example
    refs[0]["offsets_m"] = None
    walls = resolve_wall_references(source, refs)
    assert walls[0]["face_endpoints"] is None
    row = convert_wall_dimensions(walls, [dimension()])["dimensions"][0]
    assert row["status"] == "unknown_basis"
    assert row["representative_length_m"] is None and row["residual_m"] is None


def test_missing_wall_band_is_not_a_connected_dimension_chain(example):
    _, source, refs = example
    refs.append(reference("east", "space/room/wall/1", [-0.12, 0.12]))
    walls = resolve_wall_references(source, refs)
    a = dimension()
    b = dimension()
    b.update(id="next")
    b["start"]["wall_id"] = "shared"
    b["end"]["wall_id"] = "east"
    b["start"]["side"] = "positive"
    report = convert_wall_dimensions(walls, [a, b])
    assert not report["chain_connected"]
    assert report["raw_sum_m"] == 5.52
    # The next span now really begins at the preceding span's declared face.
    b["start"]["side"] = "negative"
    b["value"] = 3000
    report = convert_wall_dimensions(walls, [a, b])
    assert report["chain_connected"]
    assert report["raw_sum_m"] == 5.76
    assert sum(d["representative_length_m"] for d in report["dimensions"]) == 6


@pytest.mark.parametrize("change,match", [
    ({"offsets_m": [-0.1, 0.1]}, "disagree"),
    ({"offsets_m": [0.12, -0.12]}, "increasing"),
    ({"offsets_m": [float("nan"), 0.12]}, "finite"),
    ({"boundary_id": "space/hall/floor"}, "physical source wall"),
])
def test_bad_wall_evidence_is_not_silently_accepted(example, change, match):
    _, source, refs = example
    refs[0].update(change)
    with pytest.raises(ValueError, match=match):
        resolve_wall_references(source, refs)


def test_shared_wall_uses_one_record_for_both_rooms(example):
    _, source, refs = example
    walls = resolve_wall_references(source, refs)
    assert set(walls[1]["boundary_ids"]) == {"space/hall/wall/1", "space/room/wall/3"}
    refs.append(reference("duplicate", "space/room/wall/3", [-0.12, 0.12]))
    with pytest.raises(ValueError, match="same physical wall"):
        resolve_wall_references(source, refs)


def test_export_edit_overlay_keep_geometry_and_openings(example, tmp_path):
    proposal, baseline, refs = example
    before = copy.deepcopy(proposal)
    revised = apply_proposal_edits(proposal, [{"op": "set_wall_references", "wall_references": refs,
                                             "wall_dimensions": [dimension()], "reason": "synthetic"}])
    report = export_source_proposal(revised, tmp_path / "candidate")
    assert report["source_geometry_ready"], report
    source = json.loads((tmp_path / "candidate/source_model.json").read_text())
    assert proposal == before
    for field in ("spaces", "boundaries", "openings", "connections"):
        assert source[field] == baseline[field]
    overlay, meta = render_source_overlay(source, Image.new("RGB", (400, 400), "white"), floor_id="F1",
                                          x_anchors=[[40, 0], [340, 6]], y_anchors=[[340, 0], [40, 6]], basis="synthetic")
    assert overlay.getpixel((184, 150)) == (0, 160, 255)
    assert overlay.getpixel((190, 150)) == (255, 0, 255)
    assert len(meta["projected_wall_faces"]) == 2
    assert source["wall_dimension_report"]["dimensions"][0]["residual_m"] == 0
    with pytest.raises(ValueError, match="explicit revised proposal"):
        apply_proposal_edits(revised, [{"op": "reflect", "axis": "x", "reason": "synthetic"}])
    moved = apply_proposal_edits(revised, [{"op": "move_shared_wall", "space_ids": ["hall", "room"],
                                            "coordinate_m": 3.2, "source_refs": ["synthetic"], "reason": "synthetic"}])
    report = export_source_proposal(moved, tmp_path / "moved")
    assert report["source_geometry_ready"]
    assert report["wall_dimension_report"]["dimensions"][0]["residual_m"] == 0.2
    current = json.loads((tmp_path / "moved/source_model.json").read_text())
    assert current["wall_references"][1]["face_endpoints"][0][0][0] == pytest.approx(3.08)
    assert current["openings"][1]["space_ids"] == baseline["openings"][1]["space_ids"]
