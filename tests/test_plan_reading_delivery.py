import asyncio
import copy
import hashlib
import json

import pytest
from PIL import Image

from src.agent.runtime_roles.plan_format import READER_PLAN_EXAMPLE
from src.agent.runtime_roles.submission import ReaderSubmission
from src.agent.runtime_roles.trial import PlanTrial


def setup(tmp_path):
    (tmp_path / "images").mkdir()
    path = tmp_path / "images/plan.png"
    Image.new("RGB", (800, 600), "white").save(path)
    (tmp_path / "inputs.json").write_text(json.dumps({"images": {"plan.png": {
        "size": [800, 600], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}}))
    plan = copy.deepcopy(READER_PLAN_EXAMPLE)
    return plan, PlanTrial(None, image_name="plan.png", workspace=tmp_path,
                           receipt_directory=tmp_path / "trial_receipts", grid_step_m=.1)


def test_planar_reading_has_no_bim_or_fabricated_heights_and_survives_reload(tmp_path):
    plan, trial = setup(tmp_path)
    plan.pop("wall_metadata")
    receipt = asyncio.run(trial.run(plan))
    assert receipt["status"] == "passed", receipt.get("reason")
    assert receipt["reading_geometry_ready"] and receipt["source_geometry_ready"] is False
    assert not list(tmp_path.rglob("source_model.json"))
    product = json.loads((tmp_path / receipt["reading_product_file"]).read_bytes())
    assert "z_floor" not in product["geometry"]["floors"][0]
    assert all("z" not in row for row in product["geometry"]["openings"] + product["geometry"]["windows"])
    assert product["walls"] and all(row["thickness_m"] is None for row in product["walls"])
    restored = PlanTrial(None, image_name="plan.png", workspace=tmp_path, receipt_directory=tmp_path / "trial_receipts")
    _, validated = restored.verified_plan(receipt["plan_sha256"])
    assert len(validated["returned_images"]) == 2
    for row in validated["returned_images"]:
        with Image.open(tmp_path / row["file"]) as picture:
            assert picture.size == (800, 600)
    submission = ReaderSubmission(role_id="plan_reader", image_name="plan.png", directory=tmp_path,
                                  trial=restored, target=plan["floor_id"])
    saved = submission.submit({"trial_id": "latest", "local_review": {"summary": "Offline fixture overlay inspected; no independent fidelity claim."}})
    assert saved["status"] == "accepted"
    assert "z_floor" not in submission.read()["artifact"]["plan"]


@pytest.mark.parametrize("provide_local_thickness", [False, True])
def test_same_trial_reports_wall_coverage_and_accepts_unknown_wall_note_without_new_reading(
        tmp_path, provide_local_thickness):
    plan, trial = setup(tmp_path)
    if not provide_local_thickness:
        plan.pop("wall_metadata")
    result = asyncio.run(trial.call(plan))
    assert not result["isError"] and len(trial.receipts) == 1
    receipt = trial.receipts[0]
    counts = result["structuredContent"]["wall_metadata_summary"]["counts"]
    assert counts == {"total": 5, "supplied": 2 if provide_local_thickness else 0,
                      "known": int(provide_local_thickness),
                      "unknown": 4 if provide_local_thickness else 5,
                      "defaulted_unknown": 3 if provide_local_thickness else 5}
    assert receipt["wall_metadata_summary"] == result["structuredContent"]["wall_metadata_summary"]
    product_path = tmp_path / receipt["reading_product_file"]
    before = product_path.read_bytes()
    product = json.loads(before)
    known = [row for row in product["walls"] if row["thickness_m"] is not None]
    assert len(known) == int(provide_local_thickness)
    if known:
        assert known[0]["thickness_m"] == .18 and known[0]["reference_side"] == "unknown"
        assert known[0]["basis"] and known[0]["source_refs"]
    submission = ReaderSubmission(role_id="plan_reader", image_name="plan.png", directory=tmp_path,
                                  trial=trial, target=plan["floor_id"])
    accepted = submission.submit({"trial_id": "latest", "local_review": {
        "summary": "Offline fixture checked; unmeasured wall attributes remain unknown."},
        "notes": [{"item": "wall_metadata", "kind": "unresolved",
                   "basis": "Only the localized supplied observations are known; remaining thicknesses are unreadable."}]})
    assert accepted["status"] == "accepted" and len(trial.receipts) == 1
    saved = submission.read()
    assert saved["validation"]["notes"][0]["item"] == "plan.wall_metadata"
    assert saved["artifact"]["plan"] == trial.numeric_plan(receipt)
    assert ("wall_metadata" in saved["artifact"]["plan"]) == provide_local_thickness
    assert product_path.read_bytes() == before
    assert not any(row["item"] == "plan.wall_metadata" for row in saved["artifact"]["evidence"])


def test_planar_product_tamper_rejected_and_aperture_overlap_fails(tmp_path):
    plan, trial = setup(tmp_path)
    duplicate = copy.deepcopy(plan["openings"][0])
    duplicate["id"] = "duplicate"
    bad = {**plan, "openings": [*plan["openings"], duplicate]}
    failed = asyncio.run(trial.run(bad))
    assert failed["status"] == "failed" and "overlapping plan openings" in failed["reason"]
    passed = asyncio.run(trial.run(plan))
    assert passed["status"] == "passed", passed.get("reason")
    path = tmp_path / passed["reading_product_file"]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        trial.verified_plan(passed["plan_sha256"])


def test_reader_unit_accepts_reviewed_planar_delivery_without_bim(tmp_path, monkeypatch):
    from src.agent.runtime_roles.entry import execute, parser
    from src.agent_runtime.adapter import ScriptedAdapter
    from test_agent_runtime import versions, response
    monkeypatch.setattr("src.agent.runtime_roles.entry.make_versions", lambda *a, **k: versions())
    monkeypatch.setattr("src.agent.runtime_roles.session.make_versions", lambda *a, **k: versions())
    images = tmp_path / "inputs"
    images.mkdir()
    Image.new("RGB", (800, 600), "white").save(images / "plan.png")
    marker = tmp_path / "script.json"
    marker.write_text("{}")
    routes = {role: {"provider": "scripted", "model": "scripted-model", "output_tokens": 4000}
              for role in ("coordinator", "plan_reader", "elevation_reader")}
    task = {"task_id": "plan-unit", "role_id": "plan_reader", "image": "plan.png", "target": "F1"}
    args = parser().parse_args(["--out", str(tmp_path / "out"), "--run-root", str(tmp_path),
        "--images", str(images), "--provider", "scripted", "--model", "scripted-model", "--script", str(marker),
        "--roles-json", json.dumps(routes), "--seconds", "120", "--model-calls", "2", "--tool-calls", "4",
        "--tokens", "100000000", "--reader-task-json", json.dumps(task)])
    def accept(request):
        assert "reading_geometry_ready" in json.dumps(request["messages"])
        return response(("accept", "submit_plan_reading", {"trial_id": "latest", "local_review": {
            "summary": "Offline scripted fixture inspects its actual returned 2D views."}}))
    def factory(task_id, config, store):
        return ScriptedAdapter([response(("trial", "trial_plan_bim", {"plan": READER_PLAN_EXAMPLE})), accept])
    result = asyncio.run(execute(args, adapter_factory=factory))
    assert result["status"] == "completed", result
    assert result["role_accounting"]["requests"] == 2
    assert not result["whole_building_delivered"]
    assert not list((tmp_path / "out").rglob("source_model.json"))
