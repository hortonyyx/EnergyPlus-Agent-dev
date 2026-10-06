"""Shared accounting, immutable references and recovery guards for D1."""

import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from PIL import Image

from src.agent.runtime_roles.artifacts import ArtifactRegistry
from src.agent.runtime_roles.config import load_roles
from src.agent.runtime_roles.readers import ELEVATION_READER_TOOL_NAMES
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent_runtime.adapter import ScriptedAdapter
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore

from test_agent_runtime import response, versions


ROOT = Path(__file__).resolve().parents[1]
ROUTES = load_roles({role: {"provider": "scripted", "model": "scripted-model",
    "reasoning_effort": "medium", "output_tokens": 4000}
    for role in ("coordinator", "plan_reader", "elevation_reader")}, allow_scripted=True)


def elevation():
    return {"orientation": "North", "view_direction": "South",
        "x_calibration": {"pixel_start": 0, "pixel_end": 100, "world_start_m": 10, "world_end_m": 0},
        "elevations": [{"id": "ground", "kind": "ground", "value_m": 0,
                        "evidence_type": "assumption", "bbox": [0, 0, 10, 10]}],
        "openings": [], "counts": [{"floor_id": "F1", "window_count": 0, "door_count": 0}],
        "unresolved": ["Scripted empty facade fixture, not drawing quality evidence."]}


def dispatch(identity="north", **extra):
    return {"task_id": identity, "role_id": "elevation_reader", "image": "north.png",
            "target": "North/F1", "instructions": "Report this one facade.", **extra}


def submit_elevation(call_id="submit"):
    return response((call_id, "submit_elevation_reading", elevation()))


def delivered_adapter():
    return ScriptedAdapter([submit_elevation(), response(text="Submission acknowledged.")])


class Frozen:
    def __init__(self, run):
        self.run_directory = run
        self.calls = []

    @staticmethod
    @asynccontextmanager
    async def task_session(*, directory, images, **kwargs):
        directory.mkdir(parents=True, exist_ok=True)
        yield Frozen(directory)

    async def list_tools(self):
        return [{"name": name, "description": "test read tool", "inputSchema": {"type": "object"}}
                for name in ELEVATION_READER_TOOL_NAMES]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return envelope({"candidate": "candidate_01", "value": arguments})

    def repeatability(self, name):
        return "read_only"

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []

    def image_origins(self, raw):
        return {}


@pytest.fixture
def environment(tmp_path, request, monkeypatch):
    # These protocol tests exercise scripted readers against an actively edited
    # worktree. Agent registry sealing has its own tests and must not prevent the
    # submit/ack state machine from running before the new version is registered.
    monkeypatch.setattr("src.agent.runtime_roles.session.make_versions",
                        lambda *args, **kwargs: versions())
    run = tmp_path / "bim"
    (run / "images").mkdir(parents=True)
    image = run / "images/north.png"
    Image.new("RGB", (100, 100), "white").save(image)
    manifest = {"images": {"north.png": {"sha256": hashlib.sha256(image.read_bytes()).hexdigest()}}}
    (run / "inputs.json").write_text(json.dumps(manifest))
    limits = RunLimits(model_calls=getattr(request, "param", 10), tool_calls=10, seconds=120, tokens=200_000)
    with EventStore(tmp_path / "journal", run_id="roles", task_id="coordinator",
                    budget_limit=limits.ledger_limit()) as store:
        def make(factory=None, **kwargs):
            return RoleSession(store=store, frozen=Frozen(run), routes=ROUTES,
                adapter_factory=factory or (lambda *args: delivered_adapter()),
                limits=limits, root=ROOT, **kwargs)
        yield store, make


def test_completed_delivery_is_hashed_reusable_and_cannot_be_replaced(environment):
    store, make = environment
    session = make()
    first = asyncio.run(session.delegate_many([dispatch()]))["results"][0]
    assert first["status"] == "completed", first
    before = len(store.all_events)
    registry = ArtifactRegistry(store)
    assert registry.read("north")["image"] == "north.png"
    with pytest.raises(ValueError, match="hash"):
        registry.read("north", sha256="0" * 64)
    second = asyncio.run(make().delegate_many([dispatch()]))["results"][0]
    assert second["reused_saved_result"] and len(store.all_events) == before
    with pytest.raises(ValueError, match="cannot be overwritten"):
        registry.save(registry.task("north"), status="failed", reason="should preserve result")
    with pytest.raises(ValueError, match="different input"):
        asyncio.run(make().delegate_many([dispatch(instructions="Changed task")]))


def test_artifact_file_tampering_is_rejected_on_reopen(environment):
    store, make = environment
    result = asyncio.run(make().delegate_many([dispatch()]))["results"][0]
    path = store.directory / result["artifact"]["path"]
    path.write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        ArtifactRegistry(store)


def test_submit_tool_then_ack_is_audited_in_same_role_and_root_budget(environment):
    store, make = environment
    session = make(lambda *args: delivered_adapter())
    row = asyncio.run(session.delegate_many([dispatch()]))["results"][0]
    assert row["status"] == "completed", row
    usage = session.state()["usage"]
    role = usage["by_role"]["elevation_reader"]
    assert usage["requests"] == role["requests"] == 2
    assert role["format_errors"] == role["repair_requests"] == role["repair_successes"] == 0
    assert role["first_pass_rate"] == 1 and role["after_repair_rate"] == 1
    assert sum(r["requests"] for r in usage["by_role"].values()) == usage["requests"]
    assert role["request_seconds"] >= 0


def test_answer_text_without_submit_stops_after_one_bounded_repair(environment):
    store, make = environment
    session = make(lambda *args: ScriptedAdapter([
        response(text=json.dumps(elevation())), response(text=json.dumps(elevation())),
    ]))
    row = asyncio.run(session.delegate_many([dispatch()]))["results"][0]
    assert row["status"] == "failed" and row["artifact"] is None
    assert session.state()["usage"]["requests"] == 2
    role = session.state()["usage"]["by_role"]["elevation_reader"]
    assert role["format_errors"] == 2 and role["repair_failures"] == 1
    assert role["repair_incomplete"] == 0 and role["delivery_failures"]
    assert role["task_elapsed_seconds_sum"] > 0 and role["task_wall_span_seconds"] > 0


def test_rejected_submit_tool_can_be_fixed_and_resubmitted_without_answer_repair(environment):
    store, make = environment
    session = make(lambda *args: ScriptedAdapter([
        response(("bad-submit", "submit_elevation_reading", {})),
        submit_elevation("good-submit"),
        response(text="Submission acknowledged."),
    ]))
    row = asyncio.run(session.delegate_many([dispatch()]))["results"][0]
    assert row["status"] == "completed", row
    executions = [
        event.payload for event in store.all_events
        if event.payload.event_type == "tool_execution"
        and event.payload.tool_name == "submit_elevation_reading"
    ]
    assert [event.outcome for event in executions] == ["failed", "succeeded"]
    role = session.state()["usage"]["by_role"]["elevation_reader"]
    assert role["requests"] == 3
    assert role["format_errors"] == role["repair_requests"] == 0
    assert role["submission_attempts"] == 2 and role["submission_rejections"] == 1
    assert role["submission_repaired_tasks"] == 1
    assert role["first_pass_rate"] == 0 and role["after_repair_rate"] == 1
    assert session.registry.read("north")["orientation"] == "North"


@pytest.mark.parametrize("environment", [1], indirect=True)
def test_submit_on_last_model_request_is_still_a_completed_delivery(environment):
    store, make = environment
    session = make(lambda *args: ScriptedAdapter([submit_elevation()]))
    row = asyncio.run(session.delegate_many([dispatch()]))["results"][0]
    assert row["status"] == "completed", row
    assert row["runtime_status"].endswith("model_budget_exhausted")
    assert session.registry.read("north")["orientation"] == "North"
    assert sum(event.payload.event_type == "adapter_request" for event in store.all_events) == 1


def test_single_image_is_validated_for_entire_batch_before_any_model_call(environment):
    store, make = environment
    with pytest.raises(ValueError, match="original filename"):
        asyncio.run(make().delegate_many([dispatch(), dispatch("other", image="../secret.png")]))
    assert not store.all_events


def test_rework_has_new_identity_and_cannot_switch_original(environment):
    store, make = environment
    session = make()
    asyncio.run(session.delegate_many([dispatch()]))
    result = asyncio.run(session.delegate_many([dispatch("north-r2", previous_task_id="north",
        issues=["Check the unresolved edge"])]))["results"][0]
    assert result["status"] == "completed"
    previous = session.registry.task("north-r2")["previous_artifact"]
    assert previous == session.registry.records["north"]["artifact"]
    with pytest.raises(ValueError):
        asyncio.run(session.delegate_many([dispatch("north-r3", previous_task_id="north", target="wrong",
                                                      issues=["wrong facade"])]))


@pytest.mark.parametrize("environment", [2], indirect=True)
def test_shared_request_limit_counts_all_concurrent_tasks(environment):
    store, make = environment
    session = make(max_concurrent_readers=4)
    assert store.budget_limit.calls == session.limits.model_calls == 2
    concurrent = 0
    maximum = 0
    class Slow(ScriptedAdapter):
        async def send(self, request, *, timeout):
            nonlocal concurrent, maximum
            concurrent += 1
            maximum = max(maximum, concurrent)
            try:
                await asyncio.sleep(0.03)
                return await super().send(request, timeout=timeout)
            finally:
                concurrent -= 1
    session.adapter_factory = lambda *args: Slow([submit_elevation()])
    rows = asyncio.run(session.delegate_many([dispatch(f"reader-{i}") for i in range(4)]))["results"]
    assert maximum == 2
    assert sum(row["status"] == "completed" for row in rows) == 2, rows
    assert session.state()["usage"]["requests"] == 2


def test_readers_are_bounded_by_configured_concurrency(environment):
    _, make = environment
    concurrent = 0
    maximum = 0
    class Slow(ScriptedAdapter):
        async def send(self, request, *, timeout):
            nonlocal concurrent, maximum
            concurrent += 1
            maximum = max(maximum, concurrent)
            try:
                await asyncio.sleep(0.02)
                return await super().send(request, timeout=timeout)
            finally:
                concurrent -= 1
    session = make(lambda *args: Slow([
        submit_elevation(), response(text="Submission acknowledged."),
    ]), max_concurrent_readers=1)
    rows = asyncio.run(session.delegate_many([dispatch(f"reader-{i}") for i in range(3)]))["results"]
    assert maximum == 1 and all(row["status"] == "completed" for row in rows)


def test_build_reference_expands_original_plan_once_and_retains_audit(environment):
    store, make = environment
    session = make()
    task = session._task({**dispatch("plan"), "role_id": "plan_reader", "target": "F1"})
    artifact = {"plan": {"floor_id": "F1", "partitions": [], "openings": []}, "evidence": [], "unresolved": []}
    row = session.registry.save(task, status="completed", artifact=artifact,
                               validation={"validation_passed": True, "reason": "test receipt"})
    args = {"task_id": "plan", "sha256": row["artifact"]["sha256"]}
    first = asyncio.run(session.build_from_artifact(**args))
    second = asyncio.run(session.build_from_artifact(**args))
    assert first == second and len(session.frozen.calls) == 1
    assert json.loads(session.frozen.calls[0][1]["plan_json"]) == artifact["plan"]
    from src.harness_contracts import HashedBlobRef
    ref = first["structuredContent"]["role_application"]["expanded_parameters"]
    original = json.loads(store.get_bytes(HashedBlobRef.model_validate(ref)))
    assert original["reference"] == args and original["tool"] == "build_plan_bim"


def test_failed_trial_is_readable_but_cannot_build(environment):
    _, make = environment
    session = make()
    task = session._task({**dispatch("plan"), "role_id": "plan_reader", "target": "F1"})
    row = session.registry.save(task, status="completed", artifact={"plan": {}, "unresolved": ["invalid ring"]},
                               validation={"validation_passed": False, "reason": "invalid ring"})
    assert session.registry.read("plan")["unresolved"] == ["invalid ring"]
    with pytest.raises(ValueError, match="successful trial"):
        asyncio.run(session.build_from_artifact("plan", row["artifact"]["sha256"]))
    assert not session.frozen.calls


def test_unknown_write_intent_is_not_repeated(environment):
    store, make = environment
    session = make()
    identity = hashlib.sha256(b"test-write").hexdigest()
    store.write_json("role_operations/" + identity + ".json", {
        "operation_id": "test-write", "tool": "build_plan_bim", "arguments": {}, "reference": {}})
    with pytest.raises(ValueError, match="outcome unknown"):
        asyncio.run(session._once("test-write", "build_plan_bim", {}, reference={}))
    assert not session.frozen.calls


@pytest.mark.parametrize("field,value", [("validation", {"validation_passed": False}),
                                       ("role_id", "plan_reader"), ("target", "another floor")])
def test_completed_metadata_tampering_is_rejected(environment, field, value):
    store, make = environment
    session = make()
    asyncio.run(session.delegate_many([dispatch()]))
    path = session.registry.child("north").task_directory / "reader_record.json"
    record = json.loads(path.read_bytes())
    record[field] = value
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="metadata hash"):
        ArtifactRegistry(store)


def test_admitted_instructions_are_bound_to_the_delivery(environment):
    store, make = environment
    session = make()
    asyncio.run(session.delegate_many([dispatch()]))
    path = session.registry.child("north").task_directory / "reader_task.json"
    task = json.loads(path.read_bytes())
    task["instructions"] = "silently changed after observation"
    path.write_text(json.dumps(task))
    with pytest.raises(ValueError, match="task definition changed"):
        ArtifactRegistry(store)


def test_missing_candidate_and_match_are_correctable_tool_errors(environment):
    _, make = environment
    session = make()
    asyncio.run(session.delegate_many([dispatch()]))
    candidate = asyncio.run(session.call_tool("match_elevation", {"task_id": "north", "candidate": "candidate_999"}))
    match = asyncio.run(session.call_tool("apply_elevation_heights", {"match_id": "0" * 64, "confirm": True}))
    # GLM's Anthropic-compatible route sent the old confirm flag as "true" (sm24 debug run2).
    string_confirm = asyncio.run(session.call_tool("apply_elevation_heights", {"match_id": "0" * 64, "confirm": "true"}))
    for result in (candidate, match, string_confirm):
        assert result["isError"] and result["structuredContent"]["status"] == "rejected"
    assert "confirm" not in string_confirm["structuredContent"]["reason"]
    assert not session.frozen.calls


def test_profile_plan_expands_verified_numeric_trial_without_retranscription(environment):
    from src.agent.runtime_roles.trial import canonical_plan_sha256
    store, make = environment
    session = make()
    task = session._task({**dispatch("plan"), "role_id": "plan_reader", "target": "F1"})
    original = {"floor_id": "F1", "x_anchors": [[{"profile": "profile_001", "candidate": "C01"}, 0], [90, 9]]}
    numeric = {"floor_id": "F1", "x_anchors": [[10, 0], [90, 9]]}
    workspace = session.registry.child("plan").task_directory / "bim/trial_workspace"
    workspace.mkdir(parents=True)
    path = workspace / "numeric.json"
    path.write_text(json.dumps(numeric))
    validation = {"validation_passed": True, "plan_sha256": canonical_plan_sha256(original),
        "compiled_numeric_plan_file": "numeric.json", "compiled_numeric_plan_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    row = session.registry.save(task, status="completed", artifact={"plan": original, "unresolved": []}, validation=validation)
    asyncio.run(session.build_from_artifact("plan", row["artifact"]["sha256"]))
    assert json.loads(session.frozen.calls[0][1]["plan_json"]) == numeric
    assert session.registry.read("plan")["plan"] == original
    path.write_text("{}")
    with pytest.raises(ValueError, match="compiled reader plan hash"):
        asyncio.run(session.build_from_artifact("plan", row["artifact"]["sha256"]))


def test_bare_facade_target_takes_the_plan_floors(environment):
    # 10-07 run4: a bare "South" reader named its floor "GF", unmatched by plan F1.
    _, make = environment
    session = make()
    tasks = session._with_plan_floors([
        dispatch("plan", role_id="plan_reader", target="plan F1"),
        dispatch("south", target="South"), dispatch("east", target="East/F1")])
    assert [task["target"] for task in tasks] == ["plan F1", "South/F1", "East/F1"]
    assert session._task(tasks[1])["coordinate_contract"]["floors"] == ["F1"]
