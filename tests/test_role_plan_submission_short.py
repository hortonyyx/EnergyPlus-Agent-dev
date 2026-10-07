"""Reference-only plan submission and full/operation rework share the same safeguards."""

import asyncio
import copy
import hashlib
import json

import pytest
from PIL import Image

from src.agent.runtime_roles.readers import _evidence_targets
from src.agent.runtime_roles.submission import ReaderSubmission
from src.agent.runtime_roles.trial import PlanTrial, canonical_plan_sha256
from tests.test_role_readers import plan
from tests.test_role_submission import PassedTrial, operation
from tests.test_role_trial import Tools


def test_automatic_boxes_use_resolved_pixels_keep_inferences_and_allow_wall_override():
    trial = PassedTrial()
    numeric = copy.deepcopy(trial.plan)
    trial.plan["openings"][0]["p1"][0] = {"profile": "profile_001", "candidate": "C01"}
    trial.receipt["plan_sha256"] = canonical_plan_sha256(trial.plan)
    trial.numeric_plan = lambda receipt: copy.deepcopy(numeric)
    submission = ReaderSubmission(role_id="plan_reader", image_name="plan.png", trial=trial)
    result = submission.submit({"trial_id": "latest", "notes": [
        {"item": "plan.space_seeds:left", "kind": "inferred", "basis": "use from furniture"},
        {"item": "plan.openings:W1", "kind": "unresolved", "basis": "verify height"}],
        "wall_reference": {"partitions": {"convention": "inner_face", "basis": "dimension converted to inner face"}}})
    assert result["status"] == "accepted"
    saved = submission.read()
    evidence = {row["item"]: row for row in saved["artifact"]["evidence"]}
    assert set(evidence) == _evidence_targets(trial.plan)
    assert evidence["plan.openings:W1"]["bbox"] == [8, 28, 12, 42]
    assert {row["source"] for row in evidence.values()} == {"plan.png"}
    assert "[inferred] use from furniture" in evidence["plan.space_seeds:left"]["basis"]
    assert "plan.openings:W1: verify height" in saved["artifact"]["unresolved"]
    assert saved["artifact"]["plan"] == trial.plan
    refs = saved["validation"]["wall_reference"]
    assert refs["perimeter"]["convention"] == "outer_face"
    assert refs["partitions"]["dimension_basis"] == "inner_face"
    assert saved["validation"]["notes"][0]["kind"] == "inferred"


def test_latest_reference_survives_resume_and_rejects_stale_or_tampered_plan(tmp_path):
    workspace = tmp_path / "trial"
    (workspace / "images").mkdir(parents=True)
    Image.new("RGB", (120, 120)).save(workspace / "images/plan.png")
    digest = hashlib.sha256((workspace / "images/plan.png").read_bytes()).hexdigest()
    (workspace / "inputs.json").write_text(json.dumps({"images": {"plan.png": {
        "sha256": digest, "size": [120, 120]}}}), encoding="utf-8", newline="\n")

    def make_trial():
        return PlanTrial(Tools(workspace=workspace), image_name="plan.png", workspace=workspace,
                         receipt_directory=workspace / "trial_receipts")

    async def prepare():
        trial = make_trial()
        first = await trial.run(plan())
        second = await trial.run(operations=[operation(p2=[10, 41])])
        return first, second

    first, second = asyncio.run(prepare())
    resumed = make_trial()
    submission = ReaderSubmission(role_id="plan_reader", image_name="plan.png", trial=resumed,
                                  directory=tmp_path / "submission", target="F1")
    for params in ({"trial_id": first["trial_id"]}, {"plan_sha256": first["plan_sha256"]},
                   {"trial_id": "latest", "plan_sha256": "0" * 64}):
        with pytest.raises(ValueError):
            submission.submit(params)
    assert submission.submit({"trial_id": second["trial_id"]})["status"] == "accepted"
    restored = ReaderSubmission(role_id="plan_reader", image_name="plan.png", trial=make_trial(),
                                 directory=tmp_path / "submission", target="F1")
    assert restored.read() == submission.read()
    assert restored.read()["validation"]["wall_reference"]["partitions"]["convention"] == "centerline"
    (workspace / second["compiled_numeric_plan_file"]).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        restored.read()


def test_full_and_operation_rework_allow_notes_but_preserve_unpointed_geometry():
    async def scenario():
        prior = PlanTrial(Tools(), image_name="plan.png")
        first = await prior.run(plan())
        current = PlanTrial(Tools(), image_name="plan.png")
        current.inherit_reference(prior, first["plan_sha256"], ["plan.openings:W1"])
        changed = plan()
        changed["openings"][0]["p2"] = [10, 41]
        changed["unresolved"] = ["recheck after correction"]
        changed["partitions"][0]["source_refs"] += ["plan.png: unchanged wall reviewed"]
        full = await current.run(changed)
        assert [row["item"] for row in full["changes"]] == ["plan.openings:W1"]
        assert {row["item"] for row in full["plan_revision"]["annotation_changes"]} == {
            "plan.unresolved", "plan.partitions:P1"}
        revised = await current.run(operations=[operation(p2=[10, 42]), {
            "op": "set", "field": "unresolved", "value": [], "reason": "resolved", "bbox": [0, 0, 110, 110],
            "source_refs": ["plan.png: rechecked"]}])
        assert revised["base_plan_sha256"] == full["plan_sha256"]
        assert current.load_plan(revised)["unresolved"] == []
        invalid = current.load_plan(revised)
        invalid["partitions"][0]["points"] = [[61, 10], [61, 110]]
        with pytest.raises(ValueError):
            await current.run(invalid)
        with pytest.raises(ValueError):
            await current.run(operations=[{**operation(), "collection": "space_seeds", "id": "left",
                                          "changes": {"role": "corridor"}}])
        assert current.baseline()[1] == revised["plan_sha256"]

    asyncio.run(scenario())
