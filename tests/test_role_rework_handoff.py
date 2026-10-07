"""A rework task retains the accepted review, including later failed-trial warnings."""

import asyncio
import copy
from contextlib import asynccontextmanager

import pytest

from src.agent.runtime_roles.plan_format import audit_plan_replacement
from src.agent.runtime_roles.trial import PlanTrial
from src.agent.runtime_roles.trial import _expanded_rework_targets, normalize_rework_targets
from tests.test_role_session import dispatch, environment  # noqa: F401
from tests.test_role_trial import Tools, example


@pytest.mark.parametrize(("raw", "expected"), [
    (["plan.openings"], ["plan.openings"]),
    (["openings"], ["plan.openings"]),
    (["openings:W1"], ["plan.openings:W1"]),
])
def test_rework_target_opening_spellings_are_normalized_without_broadening(raw, expected):
    assert normalize_rework_targets(raw) == expected


def test_openings_collection_scope_preserves_every_other_plan_object():
    before = example()
    after = copy.deepcopy(before)
    after["openings"].append({**copy.deepcopy(after["openings"][0]), "id": "W_NEW"})
    allowed = _expanded_rework_targets(["plan.openings"], before, after)
    audit_plan_replacement(before, after, allowed_targets=allowed)
    after["partitions"][0]["points"][0][0] += 1
    with pytest.raises(ValueError, match="outside.*plan.partitions"):
        audit_plan_replacement(before, after, allowed_targets=allowed)


def test_unknown_rework_target_lists_three_supported_examples():
    with pytest.raises(ValueError) as raised:
        normalize_rework_targets(["doors:W1"])
    message = str(raised.value)
    for example_target in ("plan.openings", "openings", "openings:W1"):
        assert example_target in message


def test_rework_session_keeps_full_submission_review_before_any_adapter_request(environment, monkeypatch):
    store, make = environment
    session = make()
    task = session._task({**dispatch("plan-first"), "role_id": "plan_reader", "target": "F1"})
    child = session.registry.admit(task)
    workspace = child.task_directory / "bim/trial_workspace"
    (workspace / "images").mkdir(parents=True)
    (workspace / "images/north.png").write_bytes((session.run_directory / "images/north.png").read_bytes())
    (workspace / "inputs.json").write_bytes((session.run_directory / "inputs.json").read_bytes())
    prior = PlanTrial(Tools(workspace=workspace), image_name="north.png", workspace=workspace,
                      receipt_directory=workspace / "trial_receipts")
    value = example()
    receipt = asyncio.run(prior.run(value))
    # An accepted delivery can retain an earlier successful geometry while also
    # reviewing a warning discovered in a later, unsuccessful trial.
    review = [*receipt["topology_issues"], {"issue_id": "later-failed-trial", "divider": "P2"}]
    session.registry.save(task, status="completed", artifact={"plan": value, "evidence": [], "unresolved": []},
                          validation={**receipt, "validation_passed": True, "topology_issues": review})
    captured = {}

    @asynccontextmanager
    async def isolated_trial(directory, image_name, *, root):
        captured["trial"] = PlanTrial(Tools(), image_name=image_name)
        yield captured["trial"]

    monkeypatch.setattr("src.agent.runtime_roles.trial.PlanTrialSession", isolated_trial)

    def stop_at_adapter_boundary(*args):
        trial = captured["trial"]
        assert trial.baseline() == (value, receipt["plan_sha256"])
        assert trial.allowed_rework_targets == ["plan.openings:D1"]
        assert trial.inherited_topology_issues == review
        raise ValueError("handoff checked without requesting an adapter")

    session.adapter_factory = stop_at_adapter_boundary
    result = asyncio.run(session.delegate_many([{
        **dispatch("plan-next"), "role_id": "plan_reader", "target": "F1", "previous_task_id": "plan-first",
        "issues": ["correct only D1"], "rework_targets": ["plan.openings:D1"],
    }]))["results"][0]
    assert result["status"] == "failed" and "handoff checked" in result["reason"]
    assert not any(event.payload.event_type == "adapter_request" for event in store.all_events)
