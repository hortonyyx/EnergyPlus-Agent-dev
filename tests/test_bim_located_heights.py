"""Per-opening calibrated source coverage; advisory even when evidence is absent."""
import json

import pytest

from scripts.tool_scripts.bim_agent_facade_checks import located_height_report
from tests.test_bim_claims import setup_run, claim, adopt


def _calibrate(toolkit, facade="West"):
    toolkit.elevation_view("seed", facade, "plan.png",
        horizontal_anchors=[[0, 0], [11, 11]], z_anchors=[[0, 7], [7, 0]], basis="synthetic elevation anchors")


def _observe(toolkit, box):
    row = adopt(toolkit, claim(objects=[dict(kind="window", id="window")],
        sources=[dict(image="plan.png", box=box)],
        values={"height": dict(type="literal", value=[1, 2], unit="m")}))
    toolkit.confirm_claims("seed", json.dumps([dict(op="update_window", id="window",
        changes={"z": dict(claim=row["id"], value="height")}, reason="confirm synthetic height")]))


@pytest.mark.parametrize("box,status", [([0, 4, 4, 7], "covered"),
    ([8, 0, 11, 2], "outside_source_region"), ([0, 0, 12, 8], "whole_image_only")])
def test_height_requires_own_region_not_adjacent_chain_or_whole_sheet(tmp_path, box, status):
    _, toolkit = setup_run(tmp_path)
    _calibrate(toolkit)
    _observe(toolkit, box)
    report = located_height_report(toolkit, "seed")
    assert report["openings"][0]["status"] == status
    assert report["delivery_blocked"] is False
    delivery = toolkit.delivery("seed", selection_origin="agent_selected")
    assert delivery["located_height_coverage"]["openings"][0]["status"] == status
    assert (toolkit.run / "delivery.html").exists()


def test_missing_or_wrong_facade_calibration_does_not_claim_coverage(tmp_path):
    _, toolkit = setup_run(tmp_path)
    _observe(toolkit, [0, 4, 4, 7])
    assert located_height_report(toolkit, "seed")["openings"][0]["status"] == "no_elevation_calibration"
    _calibrate(toolkit, "East")
    assert located_height_report(toolkit, "seed")["openings"][0]["status"] == "no_elevation_calibration"


def test_current_geometry_and_retracted_claims_are_recomputed(tmp_path):
    _, toolkit = setup_run(tmp_path)
    _calibrate(toolkit)
    _observe(toolkit, [0, 4, 4, 7])
    assert located_height_report(toolkit, "seed")["summary"]["located_count"] == 1
    result = toolkit.revise("seed", json.dumps([dict(op="update_window", id="window",
        changes={"z": [1, 2.5]}, reason="new height", source_refs=["synthetic"])]))
    assert result["located_height_coverage"]["unchecked_opening_ids"] == ["window"]
    assert result["located_height_coverage"]["summary"]["located_count"] == 0
    toolkit.decide_claim("claim_0001", "retracted", "incorrect reading")
    assert located_height_report(toolkit, "seed")["openings"][0]["status"] == "no_height_observation"
