"""Per-opening calibrated source coverage; advisory even when evidence is absent."""
import json

import pytest

from scripts.tool_scripts.bim_agent_facade_checks import located_height_report
from tests.test_bim_claims import setup_run, claim, adopt
from tests.test_source_proposal import _proposal


def _calibrate(toolkit, facade="West"):
    toolkit.elevation_view("seed", facade, "plan.png",
        horizontal_anchors=[[0, 0], [11, 11]], z_anchors=[[0, 7], [7, 0]], basis="synthetic elevation anchors")


def _observe(toolkit, box):
    row = adopt(toolkit, claim(objects=[dict(kind="window", id="window")],
        sources=[dict(image="plan.png", box=box)],
        values={"height": dict(type="literal", value=[1, 2], unit="m")}))
    toolkit.confirm_claims("seed", json.dumps([dict(op="update_window", id="window",
        changes={"z": dict(claim=row["id"], value="height")}, reason="confirm synthetic height")]))


@pytest.mark.parametrize("box,status", [([0, 4, 4, 7], "located_confirmed"),
    ([8, 0, 11, 2], "outside_source_region"), ([0, 0, 12, 8], "whole_image_only")])
def test_height_requires_own_region_not_adjacent_chain_or_whole_sheet(tmp_path, box, status):
    _, toolkit = setup_run(tmp_path)
    _calibrate(toolkit)
    _observe(toolkit, box)
    report = located_height_report(toolkit, "seed")
    assert report["openings"][0]["status"] == (status if status == "located_confirmed" else "missing")
    if status != "located_confirmed":
        assert status in report["openings"][0]["issues"]
    assert report["delivery_blocked"] is False
    delivery = toolkit.delivery("seed", selection_origin="agent_selected")
    assert delivery["height_coverage"]["openings"] == report["openings"]
    assert (toolkit.run / "delivery.html").exists()


def test_missing_or_wrong_facade_calibration_does_not_claim_coverage(tmp_path):
    _, toolkit = setup_run(tmp_path)
    _observe(toolkit, [0, 4, 4, 7])
    assert "no_elevation_calibration" in located_height_report(toolkit, "seed")["openings"][0]["issues"]
    _calibrate(toolkit, "East")
    assert "no_elevation_calibration" in located_height_report(toolkit, "seed")["openings"][0]["issues"]


def test_current_geometry_and_retracted_claims_are_recomputed(tmp_path):
    _, toolkit = setup_run(tmp_path)
    _calibrate(toolkit)
    _observe(toolkit, [0, 4, 4, 7])
    assert located_height_report(toolkit, "seed")["summary"]["located_count"] == 1
    result = toolkit.revise("seed", json.dumps([dict(op="update_window", id="window",
        changes={"z": [1, 2.5]}, reason="new height", source_refs=["synthetic"])]))
    assert result["height_coverage"]["openings"][0]["opening_id"] == "window"
    assert result["height_coverage"]["openings"][0]["status"] == "missing"
    assert result["height_coverage"]["summary"]["located_count"] == 0
    toolkit.decide_claim("claim_0001", "retracted", "incorrect reading")
    assert located_height_report(toolkit, "seed")["openings"][0]["status"] == "missing"


def test_one_frame_over_multiple_openings_never_counts_as_individual_coverage(tmp_path):
    proposal = _proposal()
    proposal["geometry"]["windows"].append({**proposal["geometry"]["windows"][0],
        "id": "second", "span": [4.5, 5.5]})
    _, toolkit = setup_run(tmp_path, proposal)
    _calibrate(toolkit)
    row = adopt(toolkit, claim(objects=[dict(kind="window", id=name) for name in ("window", "second")],
        sources=[dict(image="plan.png", box=[0, 4, 7, 7])],
        values={"height": dict(type="literal", value=[1, 2], unit="m")}))
    toolkit.confirm_claims("seed", json.dumps([dict(op="update_window", id=name,
        changes={"z": dict(claim=row["id"], value="height")}, reason="shared frame")
        for name in ("window", "second")]))
    report = located_height_report(toolkit, "seed")
    assert report["summary"]["located_count"] == 0
    assert len(report["openings"]) == 2
    for item in report["openings"]:
        assert item["status"] == "missing"
        assert "needs_per_opening_confirmation" in item["issues"]
        assert item["evidence"][0]["views"][0]["covered_opening_ids"] == ["second", "window"]
    # A new precise source for just one opening clears only its own row.
    _observe(toolkit, [.5, 4.5, 2.5, 6.5])
    rows = {item["opening_id"]: item for item in located_height_report(toolkit, "seed")["openings"]}
    assert rows["window"]["status"] == "located_confirmed"
    assert rows["second"]["status"] == "missing"


@pytest.mark.parametrize("basis,action,status", [
    ("annotation_and_pixels", "confirm", "located_confirmed"),
    ("annotation_and_pixels", "apply", "located_applied"),
    ("inference", "confirm", "assumed"), ("declared", "confirm", "assumed")])
def test_unified_table_exposes_values_status_claim_and_view(tmp_path, basis, action, status):
    _, toolkit = setup_run(tmp_path)
    _calibrate(toolkit)
    z = [1, 2.2] if action == "apply" else [1, 2]
    data = claim(objects=[dict(kind="window", id="window")], basis=basis,
        sources=[dict(image="plan.png", box=[0, 4, 4, 7])] if basis == "annotation_and_pixels" else [],
        values={"height": dict(type="literal", value=z, unit="m")})
    result = toolkit.claim_transaction("seed", json.dumps([dict(claim=data, action=action,
        operations=[dict(op="update_window", id="window", changes={"z": dict(claim="$claim", value="height")},
                         reason="synthetic height")])]))
    row = result["height_coverage"]["openings"][0]
    assert row["absolute_z_m"] == z and row["status"] == status
    assert row["evidence"][0]["claim_id"] == "claim_0001"
    if basis == "annotation_and_pixels":
        assert row["evidence"][0]["views"][0]["image"] == "plan.png"
    report = toolkit.delivery(result["result_candidate"], selection_origin="test")
    assert report["height_coverage"]["openings"] == result["height_coverage"]["openings"]
    assert "located_height_coverage" not in report


def test_changed_source_view_cannot_keep_a_located_height(tmp_path):
    run, toolkit = setup_run(tmp_path)
    _calibrate(toolkit)
    _observe(toolkit, [0, 4, 4, 7])
    path = run / "claims/claim_0001.json"
    row = json.loads(path.read_text())
    row["claim"]["sources"][0]["box"] = [0, 0, 12, 8]
    path.write_text(json.dumps(row))
    result = located_height_report(toolkit, "seed")
    assert result["openings"][0]["status"] == "missing"
    assert "source_view_or_value_changed" in result["openings"][0]["issues"]
