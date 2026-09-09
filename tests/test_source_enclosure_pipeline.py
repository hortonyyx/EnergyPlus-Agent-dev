"""Verify source declarations survive export, display and backend boundaries."""
import json
from hashlib import sha256

import pytest
from shapely.geometry import Polygon

from scripts.tool_scripts.diagnose_source_enclosure import PRIOR, declaration
from src.agent.execution.source_bim import export_source_bim
from src.agent.execution.ep_branch import derive_ep_geometry


@pytest.fixture
def baseline(tmp_path):
    run = PRIOR / "flow_sm21_run"
    report = export_source_bim(run, tmp_path / "baseline", capability_profile="rectangular")
    assert report["source_geometry_ready"]
    return run, json.loads((tmp_path / "baseline/source_model.json").read_bytes())


@pytest.mark.parametrize("condition,partial,physical_area,unknown_area", [
    ("open", False, 0, 0), ("open", True, 2.2, 0), ("unknown", False, 0, 6),
])
def test_declared_enclosure_keeps_source_and_projects_actual_area(
    tmp_path, baseline, condition, partial, physical_area, unknown_area,
):
    run, base = baseline
    raw = json.dumps(declaration(base, condition, partial=partial), ensure_ascii=False).encode()
    path = tmp_path / "declaration.json"
    path.write_bytes(raw)
    out = tmp_path / "enclosure"
    report = export_source_bim(run, out, capability_profile="rectangular", enclosure_input_path=path)
    assert report["source_geometry_ready"]
    assert report["model_calls"] == report["solver_calls"] == 0
    assert report["enclosure_input"]["sha256"] == sha256(raw).hexdigest()
    assert (out / "enclosure_input.json").read_bytes() == raw
    source = json.loads((out / "source_model.json").read_bytes())
    display = json.loads((out / "display_geometry.json").read_bytes())
    assert source["openings"] == base["openings"]
    assert source["connections"] == base["connections"]
    assert source["boundary_relations"] == base["boundary_relations"]
    assert [(s["id"], s["polygon"], s["height"]) for s in source["spaces"]] == [
        (s["id"], s["polygon"], s["height"]) for s in base["spaces"]]
    bid = "space/F1_corridor/wall/3"
    area = {"physical": 0, "unknown": 0}
    for part in display["display_surface_parts"][bid]:
        polygon = Polygon([v[1:] for v in part["verts"]], [[v[1:] for v in h] for h in part["holes"]])
        area[part["enclosure_condition"]] += polygon.area
    assert area == pytest.approx({"physical": physical_area, "unknown": unknown_area})
    logical = next(s for s in display["surfaces"] if s["name"] == bid)
    assert Polygon([v[1:] for v in logical["verts"]]).area == pytest.approx(6)
    assert report["enclosure_information_complete"] == (condition != "unknown")
    if condition == "unknown":
        assert report["source_validation"]["status"] == "warning"
        assert not source["source_enclosure"]["open_connections"]
    else:
        assert source["source_enclosure"]["open_connections"]
    with pytest.raises(ValueError, match="source_bim_v2"):
        derive_ep_geometry(source, {s["id"]: s["id"] for s in source["spaces"]})


@pytest.mark.parametrize("raw", [b"null", b"[]", b"{broken"])
def test_invalid_enclosure_is_recorded_and_never_silently_ignored(tmp_path, baseline, raw):
    run, _base = baseline
    path = tmp_path / "invalid.json"
    path.write_bytes(raw)
    out = tmp_path / "rejected"
    report = export_source_bim(run, out, capability_profile="rectangular", enclosure_input_path=path)
    assert not report["source_geometry_ready"]
    assert report["status"] == "error"
    assert (out / "enclosure_input.json").read_bytes() == raw
    assert not (out / "source_model.json").exists()
