"""Public naming must preserve source IDs, hosts, geometry and CCW semantics."""
import copy
import hashlib
import json


from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.source_bim import build_source_bim, source_view_geometry
from src.agent.geometry.source_naming import build_public_names, viewer_names
from src.agent.roles import CATALOG, CATALOG_PATH, ROOM_TYPES, require_role


def proposal():
    return {"assumptions": [], "unresolved": [], "geometry": {
        "schema_version": "2", "footprint_x": [0, 8], "footprint_y": [0, 8],
        "floors": [{"name": "ground-original", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "west", "role": "meeting", "x": [0, 4], "y": [0, 8]},
            {"id": "east", "role": "office", "x": [4, 8], "y": [0, 8]}]}],
        "windows": [
            {"id": "low", "floor": "ground-original", "facade": "West", "room": "west", "span": [1, 2], "z": [1, 2]},
            {"id": "high", "floor": "ground-original", "facade": "West", "room": "west", "span": [6, 7], "z": [1, 2]}],
        "openings": [{"id": "shared", "kind": "door", "space_id": "west", "other_space_id": "east", "p1": [4, 3], "p2": [4, 4], "z": [0, 2], "source_refs": ["synthetic door"]}]}}


def source():
    return build_source_bim(CorrectedGeometry.model_validate(proposal()["geometry"]), capability_profile="orthogonal_polygon")


def test_catalog_is_exact_pinned_upstream_plus_explicit_unknown():
    raw = (CATALOG_PATH.parent / "openstudio/level_1_space_types.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CATALOG["source"]["sha256"]
    rows = json.loads(raw)
    assert len(rows) == 61
    assert set(ROOM_TYPES) == {r["space_type_name"] for r in rows} | {"unknown"}
    for row in rows:
        local = ROOM_TYPES[row["space_type_name"]]
        assert (local["upstream_id"], local["annotation"]) == (row["id"], row["annotation"])
        assert require_role(local["code"]) == local["code"]
        assert require_role(local["name_token"]) == local["code"]
        assert require_role(local["label_zh"]) == local["code"]
    assert ROOM_TYPES["unknown"]["upstream_id"] is None
    assert require_role("Meeting Room") == "conference/meeting/multipurpose"


def test_room_use_feedback_distinguishes_explained_unknown_and_missing_records():
    from src.agent.roles import room_use_review
    source = {"spaces": [
        {"id": "blank", "role": "unknown"},
        {"id": "old", "role": "office", "source_refs": ["legacy desk inference"]},
        {"id": "unclear", "role": "unknown", "role_evidence": {"basis": "unknown"}},
        {"id": "inferred", "role": "office", "role_evidence": {"basis": "inferred"}},
    ]}
    result = room_use_review(source)
    assert result["unrecorded_space_ids"] == ["blank", "old"]
    assert result["summary"] == dict(total_count=4, recorded_count=2, unrecorded_count=2,
                                     observed_count=0, inferred_count=1, unknown_count=1)
    assert result["delivery_blocked"] is False and result["drawing_fidelity"] == "not_evaluated"
    source["spaces"] = [{"id": str(i), "role": "unknown"} for i in range(100)]
    bounded = room_use_review(source)
    assert bounded["summary"]["unrecorded_count"] == 100
    assert len(bounded["unrecorded_space_ids"]) == 20 and bounded["unrecorded_ids_truncated"]


def test_room_wall_window_shared_door_names():
    s = source()
    n = s["public_names"]
    assert n["floors"] == {"ground-original": "F1"}
    assert n["spaces"]["west"] == "Z01_F1_Conference_Meeting_Multipurpose_W"
    assert n["spaces"]["east"] == "Z02_F1_Office_E"
    walls = {n["boundaries"][b["id"]]: b for b in s["boundaries"] if b["space_id"] == "west"}
    for name, axis, value in [("Z01_W1", 1, 0), ("Z01_W2", 0, 4), ("Z01_W3", 1, 8), ("Z01_W4", 0, 0)]:
        assert all(v[axis] == value for v in walls[name]["vertices"])
    # Final CCW west wall runs north→south, opposite numeric Y ordering.
    assert n["openings"]["high"] == "Z01_W4_Win1"
    assert n["openings"]["low"] == "Z01_W4_Win2"
    assert set(n["opening_sides"]["shared"].values()) == {"Z01_W2_Door1", "Z02_W4_Door1"}
    assert len([o for o in s["openings"] if o["id"] == "shared"]) == 1
    assert {b["id"] for b in s["boundaries"]} == set(n["boundaries"])


def test_names_survive_record_order_ring_start_and_winding():
    s = source()
    original = copy.deepcopy(s)
    for key in ("floors", "spaces", "boundaries", "openings"):
        s[key].reverse()
    for space in s["spaces"]:
        space["polygon"] = list(reversed(space["polygon"][1:] + space["polygon"][:1]))
    for b in s["boundaries"]:
        b["vertices"].reverse()
    for hosts in s["opening_hosts"].values():
        hosts.reverse()
    assert build_public_names(s) == original["public_names"]


def test_concave_ring_has_six_ccw_walls_from_southernmost_westernmost():
    p = proposal()["geometry"]
    ring = [[0, 0], [8, 0], [8, 4], [4, 4], [4, 8], [0, 8]]
    p["floors"][0]["cells"] = [{"id": "L", "role": "corridor", "x": [0, 8], "y": [0, 8], "polygon": ring}]
    from src.agent.correction.schema import FootprintRing
    geom = CorrectedGeometry.model_validate(p)
    geom.windows = []; geom.openings = []
    geom.floors[0].footprint = FootprintRing(vertices=ring)
    s = build_source_bim(geom, capability_profile="orthogonal_polygon")
    for b in s["boundaries"]:
        if b["geometry_type"] != "wall":
            continue
        index = int(s["public_names"]["boundaries"][b["id"]].split("_W")[1])-1
        assert {tuple(v[:2]) for v in b["vertices"]} == {tuple(ring[index]), tuple(ring[(index+1)%6])}


def test_reversed_floors_use_global_bbox_and_floor_identity():
    s = source()
    upper = {**s["floors"][0], "id": "upper", "name": "upper", "z_floor": 3,
             "footprint": [[0, 0], [4, 0], [4, 8], [0, 8]]}
    s["floors"].insert(0, upper)
    s["spaces"].append({**s["spaces"][0], "id": "upper-room", "floor_id": "upper",
                        "polygon": upper["footprint"], "z_floor": 3})
    n = build_public_names(s)
    assert n["floors"]["upper"] == "F2"
    assert n["spaces"]["upper-room"].endswith("_W")  # whole building, not its own center
    assert "_F2_" in n["spaces"]["upper-room"]


def test_export_rejects_invented_roles_preserves_input_and_uses_unknown(tmp_path):
    p = proposal()
    p["geometry"]["floors"][0]["cells"][0]["role"] = "office_inferred"
    before = copy.deepcopy(p)
    report = export_source_proposal(p, tmp_path / "invalid")
    assert report["status"] == "error" and "room_types" in report["error"]
    assert p == before
    del p["geometry"]["floors"][0]["cells"][0]["role"]
    report = export_source_proposal(p, tmp_path / "unknown")
    assert report["source_geometry_ready"]
    s = json.loads((tmp_path / "unknown/source_model.json").read_text())
    assert next(x for x in s["spaces"] if x["id"] == "west")["role"] == "unknown"
    assert "_Unknown_" in s["public_names"]["spaces"]["west"]
    assert json.loads((tmp_path / "unknown/proposal.json").read_text()) == p


def test_view_names_cover_objects_fragments_regions_and_edges_without_mutation():
    d = source_view_geometry(source())
    b = d["surfaces"][0]
    d["enclosure_regions"] = [{"boundary_id": b["name"], "space_id": b["zone"], "condition": "unknown", "verts": b["verts"]}]
    before = copy.deepcopy(d)
    n = viewer_names(d, d["display_surface_parts"])
    assert d == before
    objects = d["surfaces"] + d["windows"] + d["openings"]
    assert set(n["objects"]) == {x["name"] for x in objects}
    assert len(set(n["objects"].values())) == len(objects)
    assert n["regions"][0].endswith("_Unknown1")
    for obj in objects:
        assert len(n["edges"][obj["name"]]) == len(obj["verts"])
        assert all(name.startswith(n["objects"][obj["name"]]+"_Edge") for name in n["edges"][obj["name"]])
    assert all(len(n["parts"][bid]) == len(rows) for bid, rows in d["display_surface_parts"].items())
