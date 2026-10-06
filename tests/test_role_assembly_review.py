"""D1b assembly comparisons preserve accepted per-floor reader facts."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agent.execution.source_proposal import export_source_proposal
from src.agent.runtime_roles.assembly_review import AssemblyReview, compare_floor
from src.agent.runtime_roles.config import load_roles
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore
from src.harness_contracts import ToolInvocationPayload
from tests.test_bim_claims import setup_run
from tests.test_source_proposal import _proposal


ROOT = Path(__file__).resolve().parents[1]


def _source(tmp_path, name="source", proposal=None):
    folder = tmp_path / name
    assert export_source_proposal(proposal or _proposal(), folder)["source_geometry_ready"]
    return json.loads((folder / "source_model.json").read_bytes())


def test_compare_floor_ignores_height_only_but_catches_plan_facts(tmp_path):
    expected = _source(tmp_path)
    height_only = copy.deepcopy(expected)
    for opening in height_only["openings"]:
        for vertex in opening["vertices"]:
            vertex[2] += 0.35
    assert compare_floor(expected, height_only, "F1") == []

    changed = copy.deepcopy(height_only)
    window = next(row for row in changed["openings"] if row["id"] == "window")
    for vertex in window["vertices"]:
        vertex[1] += 0.2
    changed["boundary_relations"] = []
    changes = compare_floor(expected, changed, "F1")
    assert {row["item"] for row in changes} == {"adjacency", "openings:window"}
    assert all(row["change_id"] for row in changes)
    assert all(
        all(len(point) == 2 for point in row[side]["xy"])
        for row in changes
        if row["item"] == "openings:window"
        for side in ("before", "after")
    )


def test_changed_assembly_requires_one_nonempty_reason_per_change(tmp_path):
    limits = RunLimits(model_calls=1, tool_calls=1, seconds=10, tokens=1000)
    with EventStore(
        tmp_path / "journal",
        run_id="assembly",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as store:
        review = AssemblyReview(SimpleNamespace(store=store))
        changes = [
            {"change_id": "change-a", "floor_id": "F1", "item": "room_count"},
            {"change_id": "change-b", "floor_id": "F1", "item": "openings:W1"},
        ]
        report = {
            "candidate": "candidate_01",
            "source_sha256": "a" * 64,
            "require_all": True,
            "bindings": {},
            "checked_floors": ["F1"],
            "changes": changes,
            "review_id": "review-current",
            "status": "needs_review",
        }
        store.write_json("role_assembly_reviews/review-current.json", report)
        store.write_json("role_assembly_current.json", {"review_id": "review-current"})
        review.check = lambda candidate, require_all=False: report

        with pytest.raises(ValueError, match="exactly one nonempty reason"):
            review.acknowledge(
                "review-current", [{"change_id": "change-a", "reason": "accepted"}]
            )
        with pytest.raises(ValueError, match="exactly one nonempty reason"):
            review.acknowledge(
                "review-current",
                [
                    {"change_id": "change-a", "reason": "accepted"},
                    {"change_id": "change-b", "reason": "  "},
                ],
            )
        accepted = review.acknowledge(
            "review-current",
            [
                {"change_id": "change-a", "reason": "Room merge is intended."},
                {"change_id": "change-b", "reason": "Opening move is intended."},
            ],
        )
        assert accepted["status"] == "reviewed"
        assert {row["change_id"] for row in accepted["decisions"]} == {
            "change-a",
            "change-b",
        }


class _Registry:
    def __init__(self, task_directory, source_sha256):
        self.task_directory = task_directory
        self.records = {
            "plan-f1": {
                "artifact": {"sha256": "artifact-sha"},
                "validation": {
                    "candidate": "candidate_01",
                    "candidate_source_sha256": source_sha256,
                },
            }
        }

    def read(self, task_id, *, sha256=None, role_id=None):
        assert task_id == "plan-f1" and role_id == "plan_reader"
        if sha256 is not None:
            assert sha256 == "artifact-sha"
        return {"plan": {"floor_id": "F1"}}

    def child(self, task_id):
        assert task_id == "plan-f1"
        return SimpleNamespace(task_directory=self.task_directory)


class _AssemblySession:
    def __init__(self, store, run_directory, registry):
        self.store = store
        self.run_directory = run_directory
        self.registry = registry

    def _source(self, candidate):
        return json.loads(
            (self.run_directory / candidate / "source_model.json").read_bytes()
        )


def _bound_review_environment(tmp_path):
    expected = _source(tmp_path, "expected")
    raw = json.dumps(expected, ensure_ascii=False, sort_keys=True).encode()
    task = tmp_path / "reader-task"
    accepted = task / "bim/trial_workspace/candidate_01/source_model.json"
    accepted.parent.mkdir(parents=True)
    accepted.write_bytes(raw)
    run = tmp_path / "run"
    candidate = run / "candidate_01/source_model.json"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(raw)
    limits = RunLimits(model_calls=1, tool_calls=1, seconds=10, tokens=1000)
    return run, task, raw, limits


def test_candidate_hash_change_invalidates_old_review_even_when_only_height_changed(tmp_path):
    run, task, raw, limits = _bound_review_environment(tmp_path)
    with EventStore(
        tmp_path / "journal",
        run_id="assembly-hash",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as store:
        registry = _Registry(task, hashlib.sha256(raw).hexdigest())
        review = AssemblyReview(_AssemblySession(store, run, registry))
        review.bind("plan-f1")
        first = review.check("candidate_01", require_all=True)
        assert first["status"] == "unchanged" and first["changes"] == []

        changed = json.loads(raw)
        for vertex in changed["openings"][0]["vertices"]:
            vertex[2] += 0.2
        (run / "candidate_01/source_model.json").write_text(
            json.dumps(changed, ensure_ascii=False), encoding="utf-8", newline="\n"
        )
        with pytest.raises(ValueError, match="source or reader references changed"):
            review.acknowledge(first["review_id"], [])
        assert review.current()["review_id"] != first["review_id"]


def test_require_all_reports_each_unbound_actual_floor(tmp_path):
    source = _source(tmp_path, "two-floor")
    second = copy.deepcopy(source["spaces"][0])
    second.update(id="F2:extra", floor_id="F2", polygon=[
        [0, 0, 3.0], [2, 0, 3.0], [2, 2, 3.0], [0, 2, 3.0]
    ])
    source["spaces"].append(second)
    run = tmp_path / "run"
    path = run / "candidate_01/source_model.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(source), encoding="utf-8", newline="\n")
    limits = RunLimits(model_calls=1, tool_calls=1, seconds=10, tokens=1000)
    with EventStore(
        tmp_path / "journal",
        run_id="assembly-unbound",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as store:
        registry = SimpleNamespace(records={})
        review = AssemblyReview(_AssemblySession(store, run, registry))
        report = review.check("candidate_01", require_all=True)

    unexpected = [row for row in report["changes"] if row["item"] == "unexpected_floor"]
    assert {row["floor_id"] for row in unexpected} == {"F1", "F2"}
    assert all(row["change_id"] for row in unexpected)


def test_recovered_build_receipt_still_binds_and_checks_reader_floor(tmp_path):
    run, _ = setup_run(tmp_path)
    limits = RunLimits(model_calls=1, tool_calls=4, seconds=30, tokens=10_000)
    routes = load_roles(
        {
            role: {
                "provider": "scripted",
                "model": "scripted-model",
                "reasoning_effort": "medium",
                "output_tokens": 1000,
            }
            for role in ("coordinator", "plan_reader", "elevation_reader")
        },
        allow_scripted=True,
    )

    class Frozen:
        run_directory = run

        def snapshot_state(self):
            return {}

    class AssemblyProbe:
        def __init__(self):
            self.binds = []
            self.checks = []

        def bind(self, task_id):
            self.binds.append(task_id)

        def check(self, candidate, *, require_all=False):
            self.checks.append((candidate, require_all))
            return {"candidate": candidate, "status": "unchanged", "changes": []}

        def current(self):
            return None

        def _load(self, name, default):
            return default

    with EventStore(
        tmp_path / "journal",
        run_id="assembly-recovery",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as store:
        session = RoleSession(
            store=store,
            frozen=Frozen(),
            routes=routes,
            adapter_factory=lambda *args: None,
            limits=limits,
            root=ROOT,
        )
        plan = {"floor_id": "F1", "partitions": [], "openings": []}

        class RecoveryRegistry:
            records = {
                "plan-f1": {
                    "artifact": {"sha256": "artifact-sha"},
                    "image": "plan.png",
                    "validation": {"validation_passed": True},
                }
            }

            def read(self, task_id, *, sha256=None, role_id=None):
                assert (task_id, sha256, role_id) == (
                    "plan-f1",
                    "artifact-sha",
                    "plan_reader",
                )
                return {"plan": plan}

            def state(self):
                return {"tasks": {}}

        session.registry = RecoveryRegistry()
        probe = AssemblyProbe()
        session.assembly = probe
        arguments = {"task_id": "plan-f1", "sha256": "artifact-sha"}
        identity = "plan:plan-f1"
        operation_path = hashlib.sha256(identity.encode()).hexdigest()
        durable_result = envelope(
            {"candidate": "candidate_01", "source_geometry_ready": True}
        )
        store.write_json(
            "role_operations/" + operation_path + ".json",
            {
                "operation_id": identity,
                "tool": "build_plan_bim",
                "arguments": {
                    "image": "plan.png",
                    "plan_json": json.dumps(plan, ensure_ascii=False),
                },
                "reference": arguments,
                "result": durable_result,
            },
        )
        invocation = store.append(
            ToolInvocationPayload(
                call_id="recover-build",
                tool_name="build_from_artifact",
                full_arguments=arguments,
                repeatability="non_idempotent_write",
                operation_key="assembly-recovery:recover-build",
            )
        )

        recovered = asyncio.run(session.recover_pending())

    assert recovered == [invocation.event_id]
    assert probe.binds == ["plan-f1"]
    assert probe.checks == [("candidate_01", False)]
