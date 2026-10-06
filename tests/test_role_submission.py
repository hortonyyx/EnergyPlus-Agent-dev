import asyncio
import copy
import hashlib
import json

import pytest

from src.agent.runtime_roles.guidance import ELEVATION_EXAMPLE
from src.agent.runtime_roles.plan_review import (
    CONTINUOUS_HINT, opening_hosts, revise_operations, topology_issues,
    validate_topology, validate_wall_reference,
)
from src.agent.runtime_roles.readers import ReaderTools
from src.agent.runtime_roles.submission import ReaderSubmission
from src.agent.runtime_roles.trial import PlanTrial, canonical_plan_sha256
from tests.test_role_readers import Frozen, artifact, plan
from tests.test_role_trial import Tools


WALL_REFERENCE = {
    "perimeter": {"convention": "outer_face", "dimension_basis": "outer_face",
                  "basis": "overall dimension chain ends on outer faces", "bbox": [5, 5, 115, 15]},
    "partitions": {"convention": "centerline", "dimension_basis": "centerline",
                   "basis": "internal dimensions converted to the divider midplane", "bbox": [55, 5, 65, 115]},
}


def operation(**changes):
    return {"op": "update", "collection": "openings", "id": "W1", "changes": changes,
            "reason": "flagged endpoint", "source_refs": ["plan.png: observed window"], "bbox": [8, 25, 13, 45]}


class PassedTrial:
    inherited_topology_issues = []

    def __init__(self):
        self.plan = plan()
        self.receipt = {"status": "passed", "plan_sha256": canonical_plan_sha256(self.plan),
                        "candidate_source_sha256": "a" * 64, "validation_passed": True}
        self.receipts = [self.receipt]

    def verified_plan(self, digest):
        if digest != self.receipt["plan_sha256"] or self.receipt["status"] != "passed":
            raise ValueError("requires a successful isolated trial hash")
        return copy.deepcopy(self.plan), copy.deepcopy(self.receipt)

    def numeric_plan(self, receipt):
        return copy.deepcopy(self.plan)


def arguments(trial):
    return {"plan_sha256": trial.receipt["plan_sha256"], "evidence": artifact()["evidence"],
            "unresolved": ["additional review note"], "wall_reference": WALL_REFERENCE,
            "topology_decisions": []}


def test_plan_submission_preserves_exact_trial_with_additional_outer_unresolved(tmp_path):
    trial = PassedTrial()
    submission = ReaderSubmission(role_id="plan_reader", image_name="plan.png", directory=tmp_path, trial=trial)
    params = arguments(trial)
    receipt = submission.submit(params)
    saved = submission.read()
    assert receipt["status"] == "accepted"
    assert canonical_plan_sha256(saved["artifact"]["plan"]) == params["plan_sha256"]
    assert saved["artifact"]["plan"] == trial.plan
    assert saved["artifact"]["unresolved"] == ["verify sill from elevation", "additional review note"]
    assert submission.submit(params) == receipt
    resumed = ReaderSubmission(role_id="plan_reader", image_name="plan.png", directory=tmp_path, trial=trial)
    assert resumed.read() == saved
    assert b"\r" not in (tmp_path / "reader_submission.json").read_bytes()
    with pytest.raises(ValueError, match="accepted submission"):
        resumed.submit({**params, "unresolved": []})
    trial.receipt["candidate_source_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="immutable successful trial"):
        resumed.read()


def test_failed_or_rewritten_trial_and_evidence_gaps_cannot_submit():
    trial = PassedTrial()
    submission = ReaderSubmission(role_id="plan_reader", image_name="plan.png", trial=trial)
    with pytest.raises(ValueError, match="successful.*Minimum correct example"):
        submission.submit({**arguments(trial), "plan_sha256": "0" * 64})
    trial.receipt["status"] = "failed"
    with pytest.raises(ValueError, match="successful.*Minimum correct example"):
        submission.submit(arguments(trial))
    trial.receipt["status"] = "passed"
    with pytest.raises(ValueError, match="plan.space_seeds:left.*Minimum correct example"):
        submission.submit({**arguments(trial), "evidence": artifact()["evidence"][:-1]})
    with pytest.raises(ValueError, match="Additional properties.*Minimum correct example"):
        submission.submit({**arguments(trial), "plan": trial.plan})
    assert submission.read() is None


def test_elevation_rejects_bad_count_with_example_then_accepts_and_reloads(tmp_path):
    async def scenario():
        tools = ReaderTools(Frozen(tmp_path), role_id="elevation_reader", image_name="North.png")
        params = copy.deepcopy(ELEVATION_EXAMPLE)
        params["counts"][0]["window_count"] += 1
        failed = await tools.call_tool("submit_elevation_reading", params)
        assert failed["isError"] and "Minimum correct example" in failed["content"][0]["text"]
        assert tools.submission.read() is None
        accepted = await tools.call_tool("submit_elevation_reading", ELEVATION_EXAMPLE)
        assert not accepted["isError"] and accepted["structuredContent"]["status"] == "accepted"
        persisted = ReaderSubmission(role_id="elevation_reader", image_name="North.png", directory=tmp_path)
        assert persisted.read()["artifact"]["openings"][0]["head_m"] == ELEVATION_EXAMPLE["openings"][0]["head_m"]
        raw = json.loads((tmp_path / "reader_submission.json").read_bytes())
        raw["artifact"]["openings"][0]["head_m"] += 1
        (tmp_path / "reader_submission.json").write_text(json.dumps(raw), encoding="utf-8", newline="\n")
        with pytest.raises(ValueError, match="hash mismatch"):
            ReaderSubmission(role_id="elevation_reader", image_name="North.png", directory=tmp_path)
    asyncio.run(scenario())


def topology_warning(kind="unsupported_open_separator"):
    row = {"type": kind, "divider": "P1", "opening": "D1", "x_px": 60, "y_px": [10, 110],
           "look_box": [55, 8, 65, 112], "check": CONTINUOUS_HINT}
    return topology_issues([{"plan_sha256": "a" * 64, "drawing_differences": {"items": [row]}}])[0]


@pytest.mark.parametrize("kind", ["unsupported_open_separator", "opening_offset_from_gap"])
def test_each_topology_warning_needs_located_consistent_decision(kind):
    warning = topology_warning(kind)
    value = plan()
    value["openings"].append({"id": "D1", "p1": [60, 10], "p2": [60, 110]})
    with pytest.raises(ValueError, match="missing"):
        validate_topology([warning], [], value)
    decision = {"issue_id": warning["issue_id"], "decision": "retain_opening",
                "basis": "wall returns are drawn at the flagged gap", "bbox": [55, 8, 65, 112]}
    assert validate_topology([warning], [decision], value) == [decision]
    with pytest.raises(ValueError, match="overlap"):
        validate_topology([warning], [{**decision, "bbox": [0, 0, 2, 2]}], value)
    value["openings"].pop()
    decision["decision"] = "continuous_space"
    with pytest.raises(ValueError, match="declared wall"):
        validate_topology([warning], [decision], value)
    # Deleting/renaming the opening cannot hide even a surviving half of its artificial wall.
    value["partitions"][0]["points"] = [[60, 10], [60, 40]]
    with pytest.raises(ValueError, match="declared wall"):
        validate_topology([warning], [decision], value)
    value["partitions"] = []
    assert validate_topology([warning], [decision], value)


def test_opening_endpoints_and_dimension_reference_cannot_be_silently_snapped():
    value = plan()
    assert opening_hosts(value)[0]["wall"] == "footprint:3"
    value["openings"][0]["p2"][0] += 0.02
    with pytest.raises(ValueError, match="plan.openings:W1.*no automatic snapping"):
        opening_hosts(value)
    assert validate_wall_reference(WALL_REFERENCE) == WALL_REFERENCE
    with pytest.raises(ValueError, match="same declared"):
        validate_wall_reference({**WALL_REFERENCE, "partitions": {**WALL_REFERENCE["partitions"], "dimension_basis": "outer_face"}})


def test_local_operations_preserve_untouched_rows_and_reject_unpointed_edits():
    old = plan()
    updated, audit = revise_operations(old, [operation(p2=[10, 41])], allowed_targets=["plan.openings:W1"])
    assert audit["actual_changes"][0]["before"] == old["openings"][0]
    assert audit["actual_changes"][0]["after"] == updated["openings"][0]
    assert updated["partitions"] == old["partitions"]
    assert audit["unchanged_ids"]["partitions"] == ["P1"]
    with pytest.raises(ValueError, match="outside the coordinator"):
        revise_operations(old, [operation(p2=[10, 41])], allowed_targets=["plan.partitions:P1"])


def test_trial_rework_remembers_baseline_and_records_actual_changes():
    async def scenario():
        tools = Tools()
        trial = PlanTrial(tools, image_name="plan.png")
        first = await trial.run(plan())
        modified = plan()
        modified["openings"][0]["p2"][1] += 1
        with pytest.raises(ValueError, match="operations"):
            await trial.run(modified)
        assert len(tools.calls) == 1
        changed = await trial.run(operations=[operation(p2=[10, 41])])
        assert len(tools.calls) == 2 and changed["changes"][0]["item"] == "plan.openings:W1"
        assert changed["base_plan_sha256"] == first["plan_sha256"]
        assert trial.load_plan(changed) == modified
    asyncio.run(scenario())
