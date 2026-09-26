"""Assembly keeps each observed floor and shifts apertures with its elevation."""
from __future__ import annotations

import copy
import json

import pytest

from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.plan_assembly import assemble_plan_proposals
from src.agent.geometry.plan_partition import compile_plan_partition


def _compiled(*, x_end: int = 90, z_floor: float = 0.0, concave: bool = False) -> dict:
    plan = {
        "floor_id": "original",
        "z_floor": z_floor,
        "ceiling_height": 3.2,
        "x_anchors": [[0, 0.0], [99, 9.9]],
        "y_anchors": [[0, 9.9], [99, 0.0]],
        "basis": "test calibration",
        "footprint_pixels": (
            [[10, 10], [x_end, 10], [x_end, 50], [60, 50], [60, 90], [10, 90]]
            if concave else [[10, 10], [x_end, 10], [x_end, 90], [10, 90]]
        ),
        "partitions": [{
            "id": "wall", "points": [[50, 10], [50, 90]],
            "source_refs": ["drawing:wall"],
        }],
        "openings": [
            {"id": "door", "kind": "door", "p1": [50, 60], "p2": [50, 70],
             "z": [z_floor, z_floor + 2.1], "source_refs": ["drawing:door"],
             "state": "closed"},
            {"id": "window", "kind": "window", "p1": [60, 10], "p2": [70, 10],
             "z": [z_floor + 0.9, z_floor + 2.4], "source_refs": ["drawing:window"]},
        ],
        "assumptions": ["physical centerlines"],
        "unresolved": ["calibration unverified"],
    }
    return compile_plan_partition(plan, image_size=(100, 100), image_name="plan.png")[0]


def _items() -> list[dict]:
    # Both source proposals deliberately reuse every room and opening ID.
    return [
        {"proposal": _compiled(), "floor_id": "L1", "z_floor": 0.0,
         "height": 3.2, "source_ref": "drawing:first"},
        {"proposal": _compiled(x_end=80, z_floor=12.0), "floor_id": "L2",
         "z_floor": 3.2, "height": 3.2, "source_ref": "drawing:second"},
    ]


def test_two_real_floors_rebase_openings_and_export_with_connections(tmp_path):
    items = _items()
    before = copy.deepcopy(items)
    assembled = assemble_plan_proposals(items)
    assert items == before

    geom = assembled["geometry"]
    assert len(geom["floors"]) == 2
    assert [floor["z_floor"] for floor in geom["floors"]] == [0.0, 3.2]
    assert [floor["ceiling_height"] for floor in geom["floors"]] == [3.2, 3.2]
    assert [len(floor["cells"]) for floor in geom["floors"]] == [2, 2]
    assert geom["floors"][0]["footprint"]["vertices"][1][0] == 9.0
    assert geom["floors"][1]["footprint"]["vertices"][1][0] == 8.0
    assert len({cell["id"] for floor in geom["floors"] for cell in floor["cells"]}) == 4
    assert [opening["id"] for opening in geom["openings"]] == ["L1:door", "L2:door"]
    assert [window["id"] for window in geom["windows"]] == ["L1:window", "L2:window"]
    assert [opening["z"] for opening in geom["openings"]] == [[0.0, 2.1], [3.2, 5.3]]
    assert [window["z"] for window in geom["windows"]] == [[0.9, 2.4], [4.1, 5.6]]
    assert all(opening["other_space_id"] is not None for opening in geom["openings"])
    assert all(opening["space_id"].split(":", 1)[0] == opening["other_space_id"].split(":", 1)[0]
               for opening in geom["openings"])
    assert [window["floor"] for window in geom["windows"]] == ["L1", "L2"]
    assert all(window["room"].startswith(window["floor"] + ":") for window in geom["windows"])
    assert "drawing:first" in geom["notes"] and "drawing:second" in geom["notes"]
    assert assembled["assumptions"] == items[0]["proposal"]["assumptions"] + items[1]["proposal"]["assumptions"]
    assert assembled["unresolved"] == items[0]["proposal"]["unresolved"] + items[1]["proposal"]["unresolved"]
    assert [opening["source_refs"] for opening in geom["openings"]] == [["drawing:door"]] * 2

    report = export_source_proposal(assembled, tmp_path / "assembled")
    assert report["source_geometry_ready"], report
    source = json.loads((tmp_path / "assembled/source_model.json").read_text())
    assert len(source["floors"]) == 2 and len(source["spaces"]) == 4
    assert len(source["openings"]) == 4 and not source["unbuilt_openings"]
    connections = {row["opening_id"]: row for row in source["connections"]}
    assert set(connections) == {"L1:door", "L2:door"}
    assert all(len(row["space_ids"]) == 2 and not row["exterior"] for row in connections.values())
    assert [source["floors"][i]["footprint"][1][0] for i in range(2)] == [9.0, 8.0]
    assert "drawing:second" in source["generation"]["notes"]


def test_rejects_height_mismatch_duplicate_floor_and_nonfinite_values():
    items = _items()
    items[1]["height"] = 3.5
    with pytest.raises(ValueError, match="differs from compiled ceiling_height"):
        assemble_plan_proposals(items)

    items = _items()
    items[1]["floor_id"] = "L1"
    with pytest.raises(ValueError, match="duplicate floor_id"):
        assemble_plan_proposals(items)

    items = _items()
    items[1]["z_floor"] = float("nan")
    with pytest.raises(ValueError, match="finite number"):
        assemble_plan_proposals(items)

    items = _items()
    items[1]["proposal"]["geometry"]["floors"][0]["spanning_space_ids"] = ["L1:room"]
    with pytest.raises(ValueError, match="spanning_space_ids"):
        assemble_plan_proposals(items)


def test_rejects_unknown_or_cross_floor_opening_and_window_owners():
    items = _items()
    items[1]["proposal"]["geometry"]["openings"][0]["other_space_id"] = "L1:original_S01"
    with pytest.raises(ValueError, match="unknown or cross-floor space"):
        assemble_plan_proposals(items)

    items = _items()
    items[1]["proposal"]["geometry"]["windows"][0]["room"] = "other-floor-room"
    with pytest.raises(ValueError, match="unknown room"):
        assemble_plan_proposals(items)


def test_concave_floor_ring_is_preserved_when_another_floor_is_wider(tmp_path):
    from shapely.geometry import Polygon

    lower = _compiled()
    upper = _compiled(concave=True)
    original_ring = copy.deepcopy(upper["geometry"]["floors"][0]["footprint"]["vertices"])
    assembled = assemble_plan_proposals([
        {"proposal": lower, "floor_id": "L1", "z_floor": 0.0},
        {"proposal": upper, "floor_id": "L2", "z_floor": 3.2},
    ])
    assert assembled["geometry"]["floors"][1]["footprint"]["vertices"] == original_ring
    assert Polygon(original_ring).area < Polygon(original_ring).envelope.area
    report = export_source_proposal(assembled, tmp_path / "concave")
    assert report["source_geometry_ready"], report
    source = json.loads((tmp_path / "concave/source_model.json").read_text())
    assert Polygon(source["floors"][1]["footprint"]).equals(Polygon(original_ring))


def test_preserves_extra_compiled_floor_details_without_mutating_source():
    proposal = _compiled()
    proposal["geometry"]["floors"][0]["drawing_label"] = "north wing"
    original = copy.deepcopy(proposal)
    assembled = assemble_plan_proposals([{
        "proposal": proposal, "floor_id": "L1", "z_floor": 4.0,
    }])
    assert proposal == original
    assert assembled["geometry"]["floors"][0]["drawing_label"] == "north wing"
