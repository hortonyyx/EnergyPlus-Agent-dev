"""Current drawing reviews follow real source edits and gate only opted-in runs.

All drawings are synthetic. The MCP scenario executes the actual stdio tools,
plan compiler, source exporter and claim transaction; no model is contacted.
"""

from __future__ import annotations

import asyncio
import copy
import json
import shutil

import pytest
from PIL import Image, ImageDraw

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, run_guide
from scripts.tool_scripts.bim_agent_drawing_readings import (
    compare_reading, load_reading, prepare_elevation_reading,
)
from scripts.tool_scripts.bim_agent_process_reviews import (
    POLICY, apply_readings, process_status, record_reviews, require_process_reviews,
)
from src.agent.runtime_entry import prepare_inputs
from tests.test_bim_agent_tools import _error_text, _json_result, _server_session


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _plan(window_pixels):
    return {
        "floor_id": "local", "z_floor": 0, "ceiling_height": 3,
        "x_anchors": [[20, 0], [200, 9]], "y_anchors": [[20, 10], [220, 0]],
        "basis": "Synthetic axis-aligned 9 by 10 metre floor.",
        "footprint_pixels": [[20, 20], [200, 20], [200, 220], [20, 220]],
        "partitions": [], "openings": [{
            "id": "W", "kind": "window", "p1": [window_pixels[0], 20],
            "p2": [window_pixels[1], 20], "z": [0.8, 2.0],
            "source_refs": ["Synthetic north-wall window."],
        }], "assumptions": [], "unresolved": [],
    }


def _reading():
    return {
        "x_calibration": {"pixel_start": 20, "pixel_end": 200,
            "distance_start_m": 0, "distance_end_m": 9, "facade_length_m": 9},
        "z_calibration": {"pixel_start": 20, "pixel_end": 140,
            "world_start_m": 6, "world_end_m": 0},
        "elevations": [
            {"id": "ground", "floor_id": "F1", "kind": "floor", "value_m": 0,
             "evidence_type": "annotation", "bbox": [20, 139, 200, 141]},
            {"id": "upper", "floor_id": "F2", "kind": "floor", "value_m": 3,
             "evidence_type": "annotation", "bbox": [20, 79, 200, 81]},
            {"id": "roof", "floor_id": "F2", "kind": "roof", "value_m": 6,
             "evidence_type": "annotation", "bbox": [20, 19, 200, 21]},
        ],
        "openings": [
            {"id": "W1", "floor_id": "F1", "kind": "window",
             "evidence_type": "pixels", "opening_bbox": [60, 96, 100, 120]},
            {"id": "W2", "floor_id": "F2", "kind": "window",
             "evidence_type": "pixels", "opening_bbox": [120, 36, 160, 60]},
        ],
        "counts": [{"floor_id": floor, "window_count": 1, "door_count": 0}
                   for floor in ("F1", "F2")],
        "unresolved": [],
    }


def _review(kind, **values):
    return {"kind": kind, "outcome": "consistent",
            "summary": "Compared the returned synthetic original and actual-result view.",
            "issues": [], **values}


def _plan_reviews():
    return [_review("plan", image=f"{floor}.png", floor_id=floor) for floor in ("F1", "F2")]


def _statuses(status):
    return {row["scope"]: row["status"] for row in status["reviews"]}


def _source(toolkit, candidate):
    return json.loads((toolkit.candidate_path(candidate) / "source_model.json").read_bytes())


def _prepare(toolkit):
    _, metadata = prepare_elevation_reading(toolkit, "North.png", "North", json.dumps(_reading()))
    return metadata


@pytest.fixture(scope="module")
def built_case(tmp_path_factory):
    """Compile and assemble once; tests get isolated copies of this tiny fixture."""
    root = tmp_path_factory.mktemp("process_reviews_build")
    images = root / "originals"
    images.mkdir()
    for floor, span in (("F1", [120, 160]), ("F2", [60, 100])):
        picture = Image.new("RGB", (220, 240), "white")
        ink = ImageDraw.Draw(picture)
        ink.rectangle((20, 20, 200, 220), outline="black")
        ink.line((span[0], 20, span[1], 20), fill="blue", width=2)
        picture.save(images / f"{floor}.png")
    facade = Image.new("RGB", (220, 180), "white")
    ink = ImageDraw.Draw(facade)
    for rectangle in ((60, 96, 100, 120), (120, 36, 160, 60)):
        ink.rectangle(rectangle, outline="black", width=1)
    facade.save(images / "North.png")
    run, guide, task = prepare_inputs(root / "execution", images=images, mesh=None,
        building_input=None, scope="Synthetic two-storey drawing-review behavior fixture.",
        image_kind="drawings", floor_plan_images=["F1.png", "F2.png"],
        max_candidates=20, process_reviews=True)
    toolkit = Toolkit(run)
    assert toolkit.manifest["drawing_review_policy"] == POLICY
    assert (run.parent / "guide.txt").read_text(encoding="utf-8") == guide
    assert (run.parent / "task.txt").read_text(encoding="utf-8") == task
    assert POLICY in guide and POLICY in run_guide(run)
    for name in ("prepare_elevation_reading", "record_bim_review", "apply_elevation_readings"):
        assert name in guide and name in run_guide(run)
    assert all(digest(images / name) == digest(toolkit.image_path(name))
               for name in toolkit.manifest["images"])
    floors = []
    for index, span in enumerate(([120, 160], [60, 100]), 1):
        result = toolkit.build_plan(f"F{index}.png", json.dumps(_plan(span)))
        assert result["source_geometry_ready"], result
        draft = f"draft_{index:03d}"
        floors.append({"draft_id": draft, "expected_plan_sha256": toolkit.inspect_plan(draft)["plan_sha256"],
                       "floor_id": f"F{index}", "z_floor": 3 * (index - 1),
                       "evidence": "Synthetic explicit storey placement."})
    result = toolkit.assemble_plans(json.dumps(floors))
    assert result["source_geometry_ready"], result
    assert {row["floor_id"] for row in result["source_image_projections"]} >= {"F1", "F2"}
    return run, result["candidate"]


@pytest.fixture
def case(tmp_path, built_case):
    original, candidate = built_case
    run = tmp_path / "run"
    shutil.copytree(original, run)
    return Toolkit(run), candidate


def test_plan_reviews_follow_xy_scope_and_building_judgment_follows_current_source(case):
    toolkit, original = case
    before = (toolkit.candidate_path(original) / "source_model.json").read_bytes()
    saved = record_reviews(toolkit, original, json.dumps([*_plan_reviews(), _review("building")]))
    assert _statuses(saved["process_review"]) == {
        "plan:F1.png:F1": "consistent", "plan:F2.png:F2": "consistent", "building": "consistent"}
    assert saved["drawing_fidelity"] == "not_evaluated"
    assert saved["process_review"]["missing_images"] == ["North.png"]

    def revise(candidate, identity, changes):
        result = toolkit.revise(candidate, json.dumps([{
            "op": "update_window", "id": identity, "changes": changes,
            "reason": "Synthetic local revision.", "source_refs": ["Synthetic new observation."],
        }]))
        assert result["source_geometry_ready"], result
        return result["candidate"]

    height = revise(original, "F2:W", {"z": [4.0, 5.2]})
    assert _statuses(process_status(toolkit, height)) == {
        "plan:F1.png:F1": "consistent", "plan:F2.png:F2": "consistent", "building": "stale"}
    record_reviews(toolkit, height, json.dumps([_review("building")]))
    assert _statuses(process_status(toolkit, height))["building"] == "consistent"

    shifted = revise(height, "F2:W", {"span": [2.2, 4.2]})
    assert _statuses(process_status(toolkit, shifted)) == {
        "plan:F1.png:F1": "consistent", "plan:F2.png:F2": "stale", "building": "stale"}
    record_reviews(toolkit, shifted, json.dumps([_plan_reviews()[1]]))
    assert _statuses(process_status(toolkit, shifted))["plan:F2.png:F2"] == "consistent"
    assert (toolkit.candidate_path(original) / "source_model.json").read_bytes() == before


@pytest.mark.parametrize("enabled", [True, False], ids=["policy-required", "historical-manifest"])
def test_finish_mcp_rejects_missing_reviews_without_formal_delivery_only_when_enabled(case, enabled):
    toolkit, candidate = case
    if not enabled:
        manifest = copy.deepcopy(toolkit.manifest)
        del manifest["drawing_review_policy"]
        _write(toolkit.run / "inputs.json", manifest)

    async def scenario():
        async with _server_session(toolkit.run, readonly=False) as session:
            result = await session.call_tool("finish_bim", {"candidate": candidate})
            if enabled:
                assert "finish_bim" in _error_text(result)
                assert all(not (toolkit.run / name).exists()
                           for name in ("delivery_selection.json", "delivery.json", "delivery.html"))
            else:
                assert _json_result(result)["candidate"] == candidate
                assert all((toolkit.run / name).is_file()
                           for name in ("delivery_selection.json", "delivery.json", "delivery.html"))
    asyncio.run(scenario())


def test_mcp_prepare_review_apply_and_finish_use_saved_height_transaction(case):
    toolkit, candidate = case
    old_bytes = (toolkit.candidate_path(candidate) / "source_model.json").read_bytes()

    async def scenario():
        async with _server_session(toolkit.run, readonly=False) as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert {"prepare_elevation_reading", "record_bim_review", "apply_elevation_readings"} <= tools
            prepared = await session.call_tool("prepare_elevation_reading", {
                "image": "North.png", "facade": "North", "reading_json": json.dumps(_reading())})
            reading = _json_result(prepared)
            assert len([item for item in prepared.content if item.type == "image"]) == 2
            assert reading["independently_verified"] is False
            assert (toolkit.run / reading["reading_file"]).is_file()
            assert "read_candidate_items" in reading["details_read"]
            adopted = _json_result(await session.call_tool("read_candidate_items", {
                "candidate": "", "collection": "report", "report_file": reading["details_file"],
                "json_pointer": "/artifact/openings"}))
            assert adopted["sha256"] == reading["details_sha256"]
            assert {row["id"]: [row["sill_m"], row["head_m"]] for row in adopted["value"]} == {
                "W1": [1.0, 2.2], "W2": [4.0, 5.2]}
            local = _json_result(await session.call_tool("record_bim_review", {
                "candidate": candidate, "reviews_json": json.dumps([
                    *_plan_reviews(), _review("elevation", reading_id=reading["reading_id"])])}))
            assert len(local["saved_reviews"]) == 3
            assert not process_status(toolkit, candidate)["ready"]
            conflicts = _json_result(await session.call_tool("read_candidate_items", {
                "candidate": "", "collection": "report", "report_file": local["details_file"],
                "json_pointer": "/process_review/pending/0/details/issues"}))
            assert len(conflicts["value"]) == 2
            assert {row["type"] for row in conflicts["value"]} == {"height_difference"}
            comparison = compare_reading(toolkit, reading["reading_id"], candidate)
            assert not comparison["current_consistent"] and comparison["height_difference_count"] == 2

            applied = await session.call_tool("apply_elevation_readings", {
                "candidate": candidate, "reading_ids": [reading["reading_id"]]})
            updated = _json_result(applied)
            assert updated["candidate"] != candidate
            assert updated["saved_candidate"] == updated["candidate"]
            assert updated["all_readings_consistent"] and updated["matched_openings"] == 2
            assert updated["comparison_summary"] == [{"reading_id": reading["reading_id"],
                "facade": "North", "current_consistent": True, "matched_count": 2,
                "issue_count": 0, "height_difference_count": 0}]
            assert any(item.type == "image" for item in applied.content)
            source = _source(toolkit, updated["candidate"])
            assert {row["id"]: sorted({point[2] for point in row["vertices"]})
                    for row in source["openings"]} == {"F1:W": [1.0, 2.2], "F2:W": [4.0, 5.2]}
            assert compare_reading(toolkit, reading["reading_id"], updated["candidate"])["current_consistent"]
            details = toolkit.run / updated["details_file"]
            assert digest(details) == updated["details_sha256"]
            full_updated = json.loads(details.read_bytes())
            assert all(row["source_model_sha256"] == source["source_model_sha256"]
                       for row in full_updated["source_image_projections"])
            comparison_receipt = _json_result(await session.call_tool("read_candidate_items", {
                "candidate": "", "collection": "report", "report_file": updated["details_file"],
                "json_pointer": "/comparisons/0/details_file"}))
            positions = _json_result(await session.call_tool("read_candidate_items", {
                "candidate": "", "collection": "report", "report_file": comparison_receipt["value"],
                "json_pointer": "/match/position_comparisons"}))
            assert positions["sha256"] == full_updated["comparisons"][0]["details_sha256"]
            assert positions["reference"]["item_count"] == 2
            position_ids = set()
            # Position reports may be paged; inspect scalar children through the
            # same returned report rather than relying on an inline size limit.
            for index in range(2):
                fields = {}
                for key in ("artifact_opening_id", "max_difference_m"):
                    page = _json_result(await session.call_tool("read_candidate_items", {
                        "candidate": "", "collection": "report", "report_file": comparison_receipt["value"],
                        "json_pointer": f"/match/position_comparisons/{index}/{key}"}))
                    fields[key] = page["value"]
                position_ids.add(fields["artifact_opening_id"])
                assert fields["max_difference_m"] <= 1e-6
            assert position_ids == {"W1", "W2"}
            assert len(list((toolkit.run / "claims").glob("claim_*.json"))) == 1
            applications = list((toolkit.run / "claims").glob("application_*.json"))
            assert len(applications) == 1
            audit = json.loads(applications[0].read_bytes())
            assert audit["status"] == "applied" and len(audit["resolved_operations"]) == 2
            assert _statuses(process_status(toolkit, updated["candidate"])) == {
                "plan:F1.png:F1": "consistent", "plan:F2.png:F2": "consistent",
                "elevation:North.png:North": "consistent"}

            await session.call_tool("record_bim_review", {"candidate": updated["candidate"],
                "reviews_json": json.dumps([_review("building", outcome="uncertain",
                    summary="Two explicit floors and facade openings agree; vertical circulation is not supplied.",
                    issues=["No stair information in these synthetic inputs."])])})
            assert process_status(toolkit, updated["candidate"])["ready"]
            delivered = _json_result(await session.call_tool("finish_bim", {"candidate": updated["candidate"]}))
            assert delivered["candidate"] == updated["candidate"]
            assert delivered["source_model_sha256"] == source["source_model_sha256"]
            selection = json.loads((toolkit.run / "delivery_selection.json").read_bytes())
            assert selection == {"candidate": updated["candidate"], "source_model_sha256": source["source_model_sha256"]}
    asyncio.run(scenario())
    assert (toolkit.candidate_path(candidate) / "source_model.json").read_bytes() == old_bytes


def test_unknown_unreviewed_and_superseded_readings_are_refused_before_source_edits(case):
    toolkit, candidate = case
    before = {path.name for path in toolkit.run.glob("candidate_*")}
    first = _prepare(toolkit)["reading_id"]
    with pytest.raises(ValueError):
        apply_readings(toolkit, candidate, [first])
    record_reviews(toolkit, candidate, json.dumps([_review("elevation", reading_id=first)]))
    second = _prepare(toolkit)["reading_id"]
    assert second != first
    for identity in (first, "reading_9999", "../reading_0001"):
        with pytest.raises(ValueError):
            apply_readings(toolkit, candidate, [identity])
        with pytest.raises(ValueError):
            record_reviews(toolkit, candidate, json.dumps([_review("elevation", reading_id=identity)]))
    assert _statuses(process_status(toolkit, candidate))["elevation:North.png:North"] == "stale"
    assert {path.name for path in toolkit.run.glob("candidate_*")} == before
    assert not list((toolkit.run / "claims").glob("application_*.json"))


def test_review_batch_requires_full_current_overlay_and_validates_before_any_save(case):
    toolkit, candidate = case
    # A valid first review must not be written when the second scope is invalid.
    with pytest.raises(ValueError):
        record_reviews(toolkit, candidate, json.dumps([
            _plan_reviews()[0], _review("elevation", reading_id="reading_9999")]))
    assert not list((toolkit.run / "process_reviews").glob("review_*.json"))
    for path in (toolkit.run / "image_overlays").glob("overlay_*.json"):
        metadata = json.loads(path.read_bytes())
        if metadata["candidate"] == candidate and metadata["floor_id"] == "F1":
            metadata["box_original_pixels"] = [20, 20, 80, 80]
            _write(path, metadata)
    with pytest.raises(ValueError):
        record_reviews(toolkit, candidate, json.dumps([_plan_reviews()[0]]))
    assert not list((toolkit.run / "process_reviews").glob("review_*.json"))


@pytest.mark.parametrize("evidence", ["metadata", "picture"])
def test_changed_plan_overlay_evidence_makes_review_stale(case, evidence):
    toolkit, candidate = case
    record_reviews(toolkit, candidate, json.dumps([_plan_reviews()[0]]))
    review = json.loads(next((toolkit.run / "process_reviews").glob("review_*.json")).read_bytes())
    path = toolkit.run / review["evidence_file"]
    if evidence == "metadata":
        value = json.loads(path.read_bytes())
        value["basis"] = "Changed after review."
        _write(path, value)
    else:
        path = toolkit.run / json.loads(path.read_bytes())["overlay_image"]
        path.write_bytes(path.read_bytes() + b"changed")
    status = process_status(toolkit, candidate)
    assert _statuses(status)["plan:F1.png:F1"] == "stale"
    assert "changed" in status["reviews"][0]["reason"]
    with pytest.raises(ValueError):
        require_process_reviews(toolkit, candidate)


def test_changed_calibration_needs_new_projection_before_new_review(case):
    toolkit, candidate = case
    record_reviews(toolkit, candidate, json.dumps([_plan_reviews()[0]]))
    _, calibration = next((path, row) for path, row in toolkit.registered_calibrations()
                          if row["image"] == "F1.png" and row["floor_id"] == "F1")
    toolkit._save_calibration(candidate=candidate, image="F1.png", floor_id="F1",
        x_anchors=[[20, 0], [200, 9.2]], y_anchors=calibration["y_anchors"],
        basis="Synthetic revised calibration.", metadata=_source(toolkit, candidate))
    assert _statuses(process_status(toolkit, candidate))["plan:F1.png:F1"] == "stale"
    with pytest.raises(ValueError):
        record_reviews(toolkit, candidate, json.dumps([_plan_reviews()[0]]))


@pytest.mark.parametrize("evidence", ["artifact", "overlay", "original"])
def test_changed_reading_evidence_refuses_review_and_apply(case, evidence):
    toolkit, candidate = case
    reading = _prepare(toolkit)
    identity = reading["reading_id"]
    record_reviews(toolkit, candidate, json.dumps([_review("elevation", reading_id=identity)]))
    if evidence == "artifact":
        path = toolkit.run / reading["reading_file"]
        record = json.loads(path.read_bytes())
        record["artifact"]["openings"][0]["sill_m"] += 0.1
        _write(path, record)
    else:
        path = toolkit.run / (reading["overlay_file"] if evidence == "overlay" else "images/North.png")
        path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError):
        load_reading(toolkit, identity)
    with pytest.raises(ValueError):
        record_reviews(toolkit, candidate, json.dumps([_review("elevation", reading_id=identity)]))
    with pytest.raises(ValueError):
        apply_readings(toolkit, candidate, [identity])
    assert _statuses(process_status(toolkit, candidate))["elevation:North.png:North"] == "stale"
    assert not list((toolkit.run / "claims").glob("application_*.json"))


def test_changed_review_record_cannot_authorize_height_application(case):
    toolkit, candidate = case
    identity = _prepare(toolkit)["reading_id"]
    record_reviews(toolkit, candidate, json.dumps([_review("elevation", reading_id=identity)]))
    path = next((toolkit.run / "process_reviews").glob("review_*.json"))
    record = json.loads(path.read_bytes())
    record["outcome"] = "uncertain"
    _write(path, record)
    with pytest.raises(ValueError):
        process_status(toolkit, candidate)
    with pytest.raises(ValueError):
        apply_readings(toolkit, candidate, [identity])
    assert not list((toolkit.run / "claims").glob("application_*.json"))
