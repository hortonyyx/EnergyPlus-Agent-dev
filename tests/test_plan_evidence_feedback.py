"""Unit mistakes, collateral aperture changes and wrong-location self-reviews."""
import asyncio
import copy
import json

import pytest

from scripts.tool_scripts.run_bim_agent import Toolkit, digest
from src.agent.geometry.plan_feedback import plan_geometry_feedback, resolve_plan_lengths
from src.agent.geometry.opening_review import review_openings
from tests.test_bim_agent_plan_partition import example
from tests.test_bim_agent_tools import _run_with_one_image, _server_session, _json_result
from tests.test_opening_review import _source, _images, _review
from tests.test_plan_revision import operation


def test_explicit_mixed_units_reach_numeric_saved_plan_without_scaling_pixels(tmp_path):
    run = _run_with_one_image(tmp_path)
    plan = example()
    plan["x_anchors"][1][1] = dict(value=6000, unit="mm")
    plan["y_anchors"][0][1] = dict(value=400, unit="cm")
    plan["z_floor"] = dict(value=0, unit="mm")
    plan["ceiling_height"] = dict(value=3000, unit="mm")
    plan["openings"][0]["z"][1] = dict(value=2100, unit="mm")
    raw = json.dumps(plan)
    result = Toolkit(run).build_plan("plan.png", raw)
    assert result["source_geometry_ready"]
    record = result["plan_input"]
    assert json.loads((run / record["plan_file"]).read_text()) == example()
    assert (run / record["submitted_plan_file"]).read_text() == raw
    assert record["measurement_bindings"]["length_count"] == 5
    assert record["geometry_feedback"]["footprint_span_m"] == pytest.approx([6, 4])
    source = json.loads((run / result["candidate"] / "source_model.json").read_text())
    assert source["floors"][0]["footprint"] == [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]
    assert digest(run / record["geometry_feedback"]["file"]) == record["geometry_feedback"]["sha256"]
    assert plan["x_anchors"][1][0] == 11
    # Legacy numeric input is literal. Large sizes are exposed, never guessed away.
    bad_units = example()
    bad_units["x_anchors"][1][1] = 6000
    resolved, bindings = resolve_plan_lengths(bad_units)
    assert resolved == bad_units and bindings == []
    assert plan_geometry_feedback(resolved, (12, 8))["footprint_span_m"][0] == 6000


@pytest.mark.parametrize("quantity", [dict(value=1, unit="feet"), dict(value=True, unit="mm"),
    dict(value=float("nan"), unit="m"), dict(value=1, unit="mm", scale=2)])
def test_invalid_quantity_retains_raw_draft_and_cannot_create_geometry(tmp_path, quantity):
    run = _run_with_one_image(tmp_path)
    plan = example()
    plan["ceiling_height"] = quantity
    raw = json.dumps(plan)
    result = Toolkit(run).build_plan("plan.png", raw)
    assert result["error_stage"] == "length_binding"
    assert not result["source_geometry_ready"] and not list(run.glob("candidate_*"))
    assert (run / result["plan_input"]["plan_file"]).read_text() == raw


def test_calibration_revision_exposes_indirect_geometry_changes_and_height_only_preservation(tmp_path):
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    toolkit.build_plan("plan.png", json.dumps(example()))
    saved = toolkit.inspect_plan("draft_001")
    result = toolkit.revise_plan("draft_001", saved["plan_sha256"], json.dumps([
        operation("set", field="y_anchors", value=[[1, 8], [7, 0]])]))
    assert result["source_geometry_ready"]
    report = result["plan_revision"]["geometry_changes"]
    assert result["plan_revision"]["unchanged_ids"]["openings"] == ["D1", "W1"]
    assert report["unchanged_opening_ids"] == []
    assert report["changed_count"] == 2
    for row in report["changed_openings"]:
        assert row["after"]["width_m"] == pytest.approx(2 * row["before"]["width_m"])
        assert row["before"]["z_m"] == row["after"]["z_m"]
    assert digest(run / report["file"]) == report["sha256"]
    revised = toolkit.revise_plan("draft_001", saved["plan_sha256"], json.dumps([
        operation("update", collection="openings", id="D1", changes={"z": [0, 2.2]})]))
    change = revised["plan_revision"]["geometry_changes"]
    assert change["unchanged_opening_ids"] == ["W1"]
    row = change["changed_openings"][0]
    assert row["before"]["width_m"] == row["after"]["width_m"]
    assert row["before"]["height_m"] == 2.1 and row["after"]["height_m"] == 2.2
    assert toolkit.inspect_plan("draft_001") == saved


def calibration():
    return dict(image="plan.png", floor_id="F1", image_sha256="a"*64,
                x_anchors=[[0, 0], [80, 4]], y_anchors=[[0, 2], [40, 0]])


def test_identity_only_review_cannot_certify_wrong_location_with_plan_calibration():
    source, review = _source(), _review()
    before = copy.deepcopy(source)
    # IDs and room pairs alone previously passed, despite arbitrary mark boxes.
    assert not review_openings(source, review, _images())["findings"]
    result = review_openings(source, review, _images(), plan_calibration=calibration())
    wrong = [r for r in result["findings"] if r["code"] == "mark_source_location_mismatch"]
    assert {r["opening_id"] for r in wrong} == {"D1", "DOUT"}
    assert not result["matched_opening_ids"]
    review["marks"][0]["box"] = [39, 15, 41, 33]
    review["marks"][1]["box"] = [0, 15, 1, 33]
    assert not review_openings(source, review, _images(), plan_calibration=calibration())["findings"]
    review["marks"].append(dict(mark_id="missing", box=[50, 0, 60, 5], opening_ids=[],
        space_ids=["B"], basis="visible", note="additional observed door"))
    result = review_openings(source, review, _images(), plan_calibration=calibration())
    assert {r["code"] for r in result["findings"]} == {"unmodeled_observed_mark"}
    assert source == before
    with pytest.raises(ValueError, match="exact image"):
        review_openings(source, review, _images(), plan_calibration={**calibration(), "image_sha256": "changed"})


def test_plan_location_check_reaches_mcp_and_delivery_but_skips_elevations(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            result = _json_result(await session.call_tool("build_plan_bim", dict(image="plan.png", plan_json=json.dumps(example()))))
            candidate = result["candidate"]
            source = json.loads((run / candidate / "source_model.json").read_text())
            door = next(r for r in source["openings"] if r["id"] == "D1")
            review = dict(floor_id="F1", kind="door", image="plan.png", coverage="complete", marks=[
                dict(mark_id="wrong-place", box=[1, 1, 2, 2], opening_ids=["D1"],
                     space_ids=door["space_ids"], basis="visible", note="synthetic wrong placement")])
            checked = _json_result(await session.call_tool("check_openings", dict(candidate=candidate, review_json=json.dumps(review))))
            assert checked["location_check"]["status"] == "checked_against_supplied_plan_boxes"
            assert "mark_source_location_mismatch" in {r["code"] for r in checked["findings"]}
            await session.call_tool("finish_bim", dict(candidate=candidate))
            delivery = json.loads((run / "delivery.json").read_text())
            assert any(r["review_status"] == "observations_require_follow_up" for r in delivery["opening_review_scopes"])
            # An updated plan calibration must not leave an old location review current.
            await session.call_tool("overlay_candidate", dict(candidate=candidate, image="plan.png", floor_id="F1",
                x_anchors=[[1, 0], [11, 12]], y_anchors=example()["y_anchors"], basis="synthetic revised calibration"))
            await session.call_tool("finish_bim", dict(candidate=candidate))
            delivery = json.loads((run / "delivery.json").read_text())
            assert not delivery["current_reviews"]
            assert delivery["stale_reviews"][0]["stale_reason"] == "plan_calibration_changed"
            review.update(facade="North", marks=[], coverage="partial")
            checked = _json_result(await session.call_tool("check_openings", dict(candidate=candidate, review_json=json.dumps(review))))
            assert checked["location_check"]["status"] == "not_checked"
    asyncio.run(scenario())
