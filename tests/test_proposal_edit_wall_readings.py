"""Geometry edits keep wall thickness evidence local and explicitly auditable."""
import copy
import json

import pytest

from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.proposal_edits import apply_proposal_edits
from tests.test_proposal_edits import _rectangular_wall_proposal


def _proposal(*, known=True):
    proposal = _rectangular_wall_proposal()
    lines = [([[0, 0], [10, 0]], "footprint:0"),
             ([[10, 0], [10, 4]], "footprint:1"),
             ([[0, 4], [10, 4]], "footprint:2"),
             ([[0, 0], [0, 4]], "footprint:3"),
             ([[4, 0], [4, 4]], "partition:P")]
    proposal["wall_readings"] = [{"floor_id": floor, "walls": [
        {"target": target, "segments_m": [segment], "thickness_m": .2 if known else None,
         "reference_side": "negative_face" if known else "unknown",
         "evidence_status": "observed" if known else "unknown",
         "basis": f"{floor} measured thickness" if known else "No thickness supplied",
         "source_refs": [f"plan:{floor}/{target}"] if known else []}
        for segment, target in lines]} for floor in ("F1", "F2")]
    return proposal


def _export(proposal, path):
    report = export_source_proposal(proposal, path)
    assert report["source_geometry_ready"], report
    return json.loads((path / "source_model.json").read_text(encoding="utf-8"))


def _wall_refs(source, *, floor, x=None):
    boundaries = {row["id"]: row for row in source["boundaries"]}
    spaces = {row["id"]: row for row in source["spaces"]}
    return [row for row in source["wall_references"]
            if spaces[boundaries[row["boundary_ids"][0]]["space_id"]]["floor_id"] == floor
            and (x is None or {point[0] for point in boundaries[row["boundary_ids"][0]]["vertices"]} == {x})]


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize("known", [False, True])
def test_reflection_rebinds_world_side_and_keeps_original_observations(axis, known, tmp_path):
    proposal = _proposal(known=known)
    original = copy.deepcopy(proposal)
    revised = apply_proposal_edits(proposal, [{"op": "reflect", "axis": axis,
                                             "reason": "drawing orientation corrected"}])
    source = _export(revised, tmp_path / "reflected")
    changed = next(row for row in revised["wall_readings"][0]["walls"] if row["target"] == "partition:P")
    assert {p[0] for segment in changed["segments_m"] for p in segment} == ({6} if axis == "x" else {4})
    assert changed["reference_side"] == ("positive_face" if known and axis == "x"
                                          else "negative_face" if known else "unknown")
    assert changed["thickness_m"] == (.2 if known else None)
    audit = source["generation"]["corrections"][-1]["wall_readings"]
    assert audit["action"] == "explicit_coordinate_rebinding"
    assert audit["before"] == original["wall_readings"]
    assert audit["after"] == revised["wall_readings"]
    assert proposal == original


def test_reflection_splits_a_polyline_when_its_world_normal_sides_differ(tmp_path):
    proposal = _proposal()
    rows = proposal["wall_readings"][0]["walls"]
    horizontal, vertical = rows[:2]
    horizontal["segments_m"].extend(vertical["segments_m"])
    rows.remove(vertical)
    revised = apply_proposal_edits(proposal, [{"op": "reflect", "axis": "x", "reason": "correct orientation"}])
    split = [row for row in revised["wall_readings"][0]["walls"] if row["target"].startswith("footprint:0:")]
    assert {row["reference_side"] for row in split} == {"negative_face", "positive_face"}
    assert all("plan-wall:F1/footprint:0" in row["source_refs"] for row in split)
    _export(revised, tmp_path / "polyline")


@pytest.mark.parametrize("known", [False, True])
def test_wall_move_invalidates_only_moved_support_and_never_moves_old_observation(known, tmp_path):
    proposal = _proposal(known=known)
    original = copy.deepcopy(proposal)
    revised = apply_proposal_edits(proposal, [{
        "op": "move_shared_wall", "space_ids": ["left", "right"], "coordinate_m": 4.5,
        "reason": "new partition trace", "source_refs": ["plan:corrected partition"],
    }])
    source = _export(revised, tmp_path / "moved")
    moved = _wall_refs(source, floor="F1", x=4.5)
    assert moved and all(row["thickness_m"] is None and row["evidence_status"] == "unknown" for row in moved)
    assert all(row["thickness_m"] == (.2 if known else None) for row in _wall_refs(source, floor="F1", x=0))
    assert revised["wall_readings"][1] == original["wall_readings"][1]
    audit = source["generation"]["corrections"][-1]["wall_readings"]
    assert audit["before"] == [original["wall_readings"][0]]
    old_partition = next(row for row in audit["before"][0]["walls"] if row["target"] == "partition:P")
    assert old_partition["segments_m"] == [[[4, 0], [4, 4]]]
    assert old_partition["thickness_m"] == (.2 if known else None)
    assert proposal == original


def test_reshape_preserves_unchanged_parts_of_observation_and_invalidates_new_step(tmp_path):
    proposal = _proposal()
    proposal["geometry"]["openings"][0].update(p1=[4, .2], p2=[4, .8])
    revised = apply_proposal_edits(proposal, [{
        "op": "reshape_spaces", "spaces": [
            {"id": "left", "polygon": [[0, 0], [4, 0], [4, 1], [5, 1], [5, 3], [4, 3], [4, 4], [0, 4]]},
            {"id": "right", "polygon": [[4, 0], [10, 0], [10, 4], [4, 4], [4, 3], [5, 3], [5, 1], [4, 1]]},
        ], "reason": "new step is visible", "source_refs": ["plan:step"],
    }])
    source = _export(revised, tmp_path / "reshaped")
    kept = _wall_refs(source, floor="F1", x=4)
    created = _wall_refs(source, floor="F1", x=5)
    assert kept and all(row["thickness_m"] == .2 for row in kept)
    assert created and all(row["thickness_m"] is None for row in created)
    retained = next(row for row in revised["wall_readings"][0]["walls"] if row["target"] == "partition:P")
    assert retained["segments_m"] == [[[4.0, 0.0], [4.0, 1.0]], [[4.0, 3.0], [4.0, 4.0]]]
    assert revised["wall_readings"][1] == proposal["wall_readings"][1]


def test_region_replacement_and_opening_edit_export_with_unaffected_thickness(tmp_path):
    proposal = _proposal()
    revised = apply_proposal_edits(proposal, [{
        "op": "replace_space_region", "space_id": "left", "neighbor_space_id": "right",
        "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
        "reason": "room trace corrected", "source_refs": ["plan:replacement"],
    }, {
        "op": "update_opening", "id": "between", "changes": {"p1": [5, 1], "p2": [5, 2]},
        "reason": "opening follows explicit trace", "source_refs": ["plan:door"],
    }])
    source = _export(revised, tmp_path / "replaced")
    assert all(row["thickness_m"] is None for row in _wall_refs(source, floor="F1", x=5))
    assert all(row["thickness_m"] == .2 for row in _wall_refs(source, floor="F1", x=0))
    assert revised["wall_readings"][1] == proposal["wall_readings"][1]
    assert "wall_readings" not in source["generation"]["corrections"][-1]


def test_non_geometric_edit_preserves_wall_readings_exactly(tmp_path):
    proposal = _proposal()
    revised = apply_proposal_edits(proposal, [{"op": "update_window", "id": "left_south",
        "changes": {"z": [1.1, 2.2]}, "reason": "elevation sill", "source_refs": ["elevation:sill"]}])
    assert revised["wall_readings"] == proposal["wall_readings"]
    _export(revised, tmp_path / "height")
