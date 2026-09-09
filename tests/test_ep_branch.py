"""Offline boundary tests: the EP branch must consume the frozen BIM itself."""
import json
from pathlib import Path

import pytest

from src.agent.execution.ep_branch import assemble_idf, derive_ep_geometry, export_ep_branch
from src.agent.geometry.source_model import _digest

SOURCE = Path("AI_agent/logs/experiments/2026-09-09_source_bim_run04/flow_sm21_bim/source_model.json")
INPUTS = Path("AI_agent/logs/experiments/2026-09-09_ep_branch_sm21/inputs")


@pytest.fixture
def source():
    return json.loads(SOURCE.read_bytes())


@pytest.fixture
def bindings():
    return json.loads((INPUTS/"zone_bindings.json").read_bytes())


def resign(source):
    source["source_model_sha256"] = _digest({k:v for k,v in source.items() if k != "source_model_sha256"})


def test_branch_preserves_source_and_uses_changed_window_vertices(source, bindings, monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail("EP branch attempted to reconstruct correction geometry")
    monkeypatch.setattr("src.agent.geometry.build.build_geometry", forbidden)
    source["openings"][0]["vertices"][1][0] -= .1
    source["openings"][0]["vertices"][2][0] -= .1
    resign(source)
    before = json.dumps(source)
    bg, mapping = derive_ep_geometry(source, bindings)
    assert json.dumps(source) == before
    assert len(bg.zones) == 14 and len(bg.surfaces) == 100 and len(bg.windows) == 15
    assert set(mapping["surfaces"].values()) == {b["id"] for b in source["boundaries"]}
    assert [list(v) for v in bg.windows[0].verts] == source["openings"][0]["vertices"]
    idf = assemble_idf(bg, (INPUTS/"physics.idf").read_text(), source)
    window = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"][0]
    assert window.Vertex_2_Xcoordinate == source["openings"][0]["vertices"][1][0]
    assert len(idf.idfobjects["BUILDINGSURFACE:DETAILED"]) == 100
    assert all(z.X_Origin == 0 for z in idf.idfobjects["ZONE"])


@pytest.mark.parametrize("damage,match", [
    ("digest", "digest mismatch"), ("boundary", "source boundary"),
    ("contact", "contact absent"), ("adjacency", "adjacency disagrees"),
    ("door", "door"), ("unbuilt", "unresolved geometry"),
    ("unknown_kind", "unsupported source opening kind"),
    ("binding", "cover every source space"),
])
def test_fail_closed_on_source_or_branch_mismatch(source, bindings, damage, match):
    if damage == "digest": source["spaces"][0]["height"] += .1
    if damage == "boundary": source["boundaries"].pop(0)
    if damage == "contact": source["boundary_relations"].pop(0)
    if damage == "adjacency": source["boundaries"][0]["adjacent_space_ids"] = []
    if damage == "door": source["openings"][0]["kind"] = "door"
    if damage == "unknown_kind": source["openings"][0]["kind"] = "unsupported_kind"
    if damage == "unbuilt": source["unbuilt_openings"] = [{"id": "unresolved"}]
    if damage == "binding": bindings.pop(next(iter(bindings)))
    if damage != "digest": resign(source)
    with pytest.raises(ValueError, match=match):
        derive_ep_geometry(source, bindings)


def test_physics_cannot_smuggle_old_geometry_or_unknown_zone(source, bindings):
    bg, _ = derive_ep_geometry(source, bindings)
    physics = (INPUTS/"physics.idf").read_text()
    with pytest.raises(ValueError, match="geometry-free"):
        assemble_idf(bg, physics+"\nZone,stale_room;\n", source)
    with pytest.raises(ValueError, match="zone absent"):
        assemble_idf(bg, physics.replace(next(iter(bindings.values())), "unknown_zone"), source)


def test_source_north_controls_ep_orientation_with_zero_zone_transforms(source, bindings):
    source["coordinate_system"]["north_axis"] = {"value_deg": 37, "provenance": "assumed"}
    resign(source)
    bg, _ = derive_ep_geometry(source, bindings)
    idf = assemble_idf(bg, (INPUTS/"physics.idf").read_text(), source)
    assert idf.idfobjects["BUILDING"][0].North_Axis == 37
    assert idf.idfobjects["GLOBALGEOMETRYRULES"][0].Coordinate_System == "Relative"
    assert all(z.Direction_of_Relative_North == 0 and z.X_Origin == z.Y_Origin == z.Z_Origin == 0
               for z in idf.idfobjects["ZONE"])


def test_export_only_and_failure_evidence_are_distinct(tmp_path):
    raw = SOURCE.read_bytes()
    out = tmp_path/"ep"
    report = export_ep_branch(SOURCE, INPUTS/"physics.idf", INPUTS/"zone_bindings.json", out)
    assert report["status"] == "exported", report
    assert report["simulation"]["status"] == "not_run"
    assert report["source_file_unchanged"]
    assert (out/"source_model.json").read_bytes() == SOURCE.read_bytes() == raw
    with pytest.raises(FileExistsError):
        export_ep_branch(SOURCE, INPUTS/"physics.idf", INPUTS/"zone_bindings.json", out)
    bad = tmp_path/"bad.json"
    bad.write_text("{}")
    report = export_ep_branch(bad, INPUTS/"physics.idf", INPUTS/"zone_bindings.json", tmp_path/"failed")
    assert report["status"] == "failed"
    assert (tmp_path/"failed/report.json").is_file()
    assert not (tmp_path/"failed/model.idf").exists()
