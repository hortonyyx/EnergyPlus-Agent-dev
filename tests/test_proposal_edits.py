"""Deterministic proposal edits preserve source identities and audit history."""
from __future__ import annotations

import copy

import pytest

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.geometry.proposal_edits import apply_proposal_edits
from src.agent.geometry.source_bim import build_source_bim


def _proposal():
    return {
        "geometry": {
            "schema_version": "2", "footprint_x": [0, 8], "footprint_y": [0, 6],
            "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
                {"id": "left", "role": "office", "x": [0, 4], "y": [0, 6],
                 "polygon": [[0, 0], [4, 0], [4, 2], [3, 2], [3, 4], [4, 4], [4, 6], [0, 6]]},
                {"id": "right", "role": "corridor", "x": [3, 8], "y": [0, 6],
                 "polygon": [[4, 0], [8, 0], [8, 6], [4, 6], [4, 4], [3, 4], [3, 2], [4, 2]]},
            ]}],
            "windows": [
                {"id": "north", "floor": "F1", "facade": "North", "span": [1, 2], "z": [1, 2], "room": "left"},
                {"id": "south", "floor": "F1", "facade": "South", "span": [5, 6], "z": [1, 2], "room": "right"},
                {"id": "east", "floor": "F1", "facade": "East", "span": [1, 2], "z": [1, 2], "room": "right"},
                {"id": "west", "floor": "F1", "facade": "West", "span": [4, 5], "z": [1, 2], "room": "left"},
            ],
            "openings": [{"id": "door", "kind": "door", "space_id": "left", "other_space_id": "right",
                          "p1": [4, .5], "p2": [4, 1.5], "z": [0, 2.1], "source_refs": ["fixture:door"]}],
        },
        "assumptions": ["west side inferred"],
        "unresolved": ["orientation needs review"],
    }


def _without_audit(geometry):
    result = copy.deepcopy(geometry)
    result.pop("corrections", None)
    return result


def _rectangular_wall_proposal():
    return {
        "geometry": {
            "schema_version": "2", "footprint_x": [0, 10], "footprint_y": [0, 4],
            "floors": [
                {"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
                    {"id": "left", "role": "office", "x": [0, 4], "y": [0, 4]},
                    {"id": "right", "role": "office", "x": [4, 10], "y": [0, 4]},
                ]},
                {"name": "F2", "z_floor": 3, "ceiling_height": 3, "cells": [
                    {"id": "upper", "role": "office", "x": [0, 10], "y": [0, 4]},
                ]},
            ],
            "windows": [{"id": "left_south", "floor": "F1", "facade": "South", "span": [1, 2],
                         "z": [1, 2], "room": "left"}],
            "openings": [
                {"id": "between", "kind": "door", "space_id": "left", "other_space_id": "right",
                 "p1": [4, 1], "p2": [4, 2], "z": [0, 2.1], "source_refs": ["fixture:shared wall"]},
                {"id": "south", "kind": "door", "space_id": "left", "other_space_id": None,
                 "p1": [2, 0], "p2": [3, 0], "z": [0, 2.1], "source_refs": ["fixture:south wall"]},
            ],
        },
        "assumptions": ["synthetic rectangle"], "unresolved": [],
    }


def test_reflection_preserves_nonrectangular_rooms_openings_and_source_buildability():
    proposal = _proposal()
    x_reflected = apply_proposal_edits(proposal, [{"op": "reflect", "axis": "x", "reason": "plan is mirrored"}])
    facades = {window["id"]: window["facade"] for window in x_reflected["geometry"]["windows"]}
    assert facades == {"north": "North", "south": "South", "east": "West", "west": "East"}
    assert x_reflected["geometry"]["openings"][0]["p1"] == [4, .5]
    assert x_reflected["geometry"]["floors"][0]["cells"][0]["id"] == "left"
    assert "direction language" in x_reflected["geometry"]["corrections"][-1]["notice"]
    assert any("direction language" in item for item in x_reflected["unresolved"])
    assert build_source_bim(ensure_corrected_geometry(x_reflected["geometry"]),
                            capability_profile="orthogonal_polygon")["validation"]["status"] == "pass"

    y_reflected = apply_proposal_edits(proposal, [{"op": "reflect", "axis": "y", "reason": "north arrow corrected"}])
    assert {window["id"]: window["facade"] for window in y_reflected["geometry"]["windows"]} == {
        "north": "South", "south": "North", "east": "East", "west": "West"}
    twice = apply_proposal_edits(proposal, [
        {"op": "reflect", "axis": "x", "reason": "first transform"},
        {"op": "reflect", "axis": "x", "reason": "inverse transform"},
    ])
    assert _without_audit(twice["geometry"]) == _without_audit(proposal["geometry"])
    assert proposal == _proposal()
    assert apply_proposal_edits(proposal, [
        {"op": "reflect", "axis": "x", "reason": "plan is mirrored"},
        {"op": "set_notes", "assumptions": ["corrected orientation"], "unresolved": []},
    ])["unresolved"] == []


def test_updates_removal_and_notes_keep_full_audit_history():
    proposal = _proposal()
    revised = apply_proposal_edits(proposal, [
        {"op": "update_window", "id": "west", "changes": {"z": [1.2, 2.2], "assumptions": ["elevation replaces placeholder"]},
         "reason": "elevation confirms sill", "source_refs": ["elevation:west"]},
        {"op": "update_opening", "id": "door", "changes": {"state": "closed", "assumptions": ["leaf state observed"]},
         "reason": "door leaf visible", "source_refs": ["plan:door-leaf"]},
        {"op": "remove_opening", "id": "door", "reason": "later view disproves opening",
         "source_refs": ["elevation:no-door"]},
        {"op": "set_notes", "assumptions": ["new orientation"], "unresolved": []},
    ])
    assert proposal == _proposal()
    assert not revised["geometry"]["openings"]
    audit = revised["geometry"]["corrections"]
    assert [row["operation"] for row in audit] == ["update_window", "update_opening", "remove_opening", "set_notes"]
    assert audit[0]["before"]["z"] == [1, 2] and audit[0]["after"]["z"] == [1.2, 2.2]
    assert revised["geometry"]["windows"][3]["source_refs"] == ["elevation:west"]
    assert revised["geometry"]["windows"][3]["assumptions"] == ["elevation replaces placeholder"]
    assert audit[1]["before"]["source_refs"] == ["fixture:door"]
    assert audit[1]["after"]["source_refs"] == ["plan:door-leaf"]
    assert audit[1]["after"]["assumptions"] == ["leaf state observed"]
    assert audit[2]["before"]["id"] == "door" and audit[2]["after"] is None
    assert audit[2]["source_refs"] == ["elevation:no-door"]
    assert revised["assumptions"] == ["new orientation"] and revised["unresolved"] == []


def test_move_shared_wall_preserves_unrelated_geometry_and_hosts_its_door():
    proposal = _rectangular_wall_proposal()
    revised = apply_proposal_edits(proposal, [{
        "op": "move_shared_wall", "space_ids": ["left", "right"], "coordinate_m": 4.5,
        "reason": "plan dimension locates the complete interior wall", "source_refs": ["plan: wall dimension"],
    }])
    floor = revised["geometry"]["floors"][0]
    cells = {cell["id"]: cell for cell in floor["cells"]}
    openings = {opening["id"]: opening for opening in revised["geometry"]["openings"]}
    assert cells["left"]["x"] == [0, 4.5]
    assert cells["right"]["x"] == [4.5, 10]
    assert openings["between"]["p1"] == [4.5, 1]
    assert openings["between"]["p2"] == [4.5, 2]
    assert openings["south"] == proposal["geometry"]["openings"][1]
    assert revised["geometry"]["windows"] == proposal["geometry"]["windows"]
    assert revised["geometry"]["floors"][1] == proposal["geometry"]["floors"][1]
    audit = revised["geometry"]["corrections"][-1]
    assert audit["axis"] == "x" and audit["from_coordinate_m"] == 4
    assert audit["moved_openings"][0]["id"] == "between"
    assert proposal == _rectangular_wall_proposal()
    assert build_source_bim(ensure_corrected_geometry(revised["geometry"]),
                            capability_profile="orthogonal_polygon")["validation"]["status"] == "pass"


def test_invalid_operations_do_not_mutate_input_or_silently_ignore_unknowns():
    proposal = _proposal()
    original = copy.deepcopy(proposal)
    with pytest.raises(ValueError, match="unsupported changes"):
        apply_proposal_edits(proposal, [{"op": "update_window", "id": "west", "changes": {"id": "new"},
                                         "reason": "bad", "source_refs": ["test"]}])
    assert proposal == original
    with pytest.raises(ValueError, match="nonempty enclosure_declaration"):
        apply_proposal_edits({**proposal, "enclosure_declaration": {"declared": True}}, [
            {"op": "reflect", "axis": "x", "reason": "would omit enclosure transform"}])
    with pytest.raises(ValueError, match="floor.footprint"):
        with_footprint = copy.deepcopy(proposal)
        with_footprint["geometry"]["floors"][0]["footprint"] = {"vertices": [[0, 0], [8, 0], [8, 6], [0, 6]]}
        apply_proposal_edits(with_footprint, [{"op": "reflect", "axis": "x", "reason": "would omit footprint"}])


@pytest.mark.parametrize("coordinate", [True, float("inf"), 0, 10])
def test_move_shared_wall_rejects_invalid_coordinate_without_mutating_input(coordinate):
    proposal = _rectangular_wall_proposal()
    original = copy.deepcopy(proposal)
    with pytest.raises(ValueError, match="coordinate_m"):
        apply_proposal_edits(proposal, [{
            "op": "move_shared_wall", "space_ids": ["left", "right"], "coordinate_m": coordinate,
            "reason": "synthetic", "source_refs": ["plan: synthetic"],
        }])
    assert proposal == original


def test_move_shared_wall_rejects_partial_polygon_and_enclosure_cases():
    proposal = _rectangular_wall_proposal()
    polygon = copy.deepcopy(proposal)
    polygon["geometry"]["floors"][0]["cells"][0]["polygon"] = [[0, 0], [4, 0], [4, 4], [0, 4]]
    partial = copy.deepcopy(proposal)
    partial["geometry"]["floors"][0]["cells"][1]["y"] = [1, 4]
    enclosed = {**proposal, "enclosure_declaration": {"declared": True}}
    operation = {"op": "move_shared_wall", "space_ids": ["left", "right"], "coordinate_m": 4.5,
                 "reason": "synthetic", "source_refs": ["plan: synthetic"]}
    with pytest.raises(ValueError, match="without polygon"):
        apply_proposal_edits(polygon, [operation])
    with pytest.raises(ValueError, match="complete axis-aligned"):
        apply_proposal_edits(partial, [operation])
    with pytest.raises(ValueError, match="explicit enclosure_declaration"):
        apply_proposal_edits(enclosed, [operation])
