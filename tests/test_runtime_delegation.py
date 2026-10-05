import asyncio
import hashlib
import io
import json
import tarfile
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pytest
from PIL import Image

from src.agent.contracts import EvidencePackage
from src.agent.contracts.refs import (
    CoordinateRelation,
    ExistingEvidenceRef,
    RunQualifiedEvidenceRef,
)
from src.agent.runtime_coordinator import CoordinatorSession
from src.agent.runtime_delegation import (
    EvidenceTools,
    RegisteredView,
    hydrate_observation,
    run_observer,
)
from src.agent.runtime_tools import local_observer_role
from src.agent_runtime.adapter import ScriptedAdapter
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts


ROOT = Path(__file__).resolve().parents[1]


def _png_bytes(size, color):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


def _registered_view(store):
    original_bytes = _png_bytes((100, 100), "white")
    sent_bytes = _png_bytes((80, 60), "gray")
    original = store.put_bytes(original_bytes, "image/png")
    sent = store.put_bytes(sent_bytes, "image/png")
    relation = CoordinateRelation(
        referenced_space="view_pixels",
        relation="crop_and_affine",
        crop_original_pixels=(10.0, 20.0, 90.0, 80.0),
        original_to_referenced_affine=(1.0, 0.0, -10.0, 0.0, 1.0, -20.0),
    )
    return RegisteredView(
        reference=RunQualifiedEvidenceRef(
            run_id=store.run_id,
            reference=ExistingEvidenceRef(scheme="view_id", value="view_0001"),
            original_sha256=original.sha256,
            coordinate_relation=relation,
        ),
        original=original,
        sent=sent,
        original_size=(100, 100),
        sent_size=(80, 60),
        image_name="plan.png",
        tool_event_id="event-view-source",
    )


def _registered_west_view(store):
    original_bytes = _png_bytes((2639, 931), "white")
    original = store.put_bytes(original_bytes, "image/png")
    sent = store.put_bytes(_png_bytes((263, 93), "gray"), "image/png")
    relation = CoordinateRelation(
        referenced_space="view_pixels",
        relation="crop_and_affine",
        crop_original_pixels=(0.0, 0.0, 2639.0, 931.0),
        original_to_referenced_affine=(263 / 2639, 0.0, 0.0, 0.0, 93 / 931, 0.0),
    )
    return RegisteredView(
        reference=RunQualifiedEvidenceRef(
            run_id=store.run_id,
            reference=ExistingEvidenceRef(scheme="view_id", value="view_0001"),
            original_sha256=original.sha256,
            coordinate_relation=relation,
        ),
        original=original,
        sent=sent,
        original_size=(2639, 931),
        sent_size=(263, 93),
        image_name="west.png",
        tool_event_id="event-view-source",
    )


def _package(view, *, task_id="observer-1", version="source-v1"):
    return EvidencePackage(
        package_id="package-" + task_id,
        task_id=task_id,
        role_id="local_observer",
        question="What is directly visible inside the marked crop?",
        known_evidence_ids=(),
        image_refs=(view.reference,),
        source_model_version_id=version,
        budget_reservation_id=task_id + ":request-1",
    )


def _answer(*, view_id="view_0001", box=(20.0, 30.0, 40.0, 50.0)):
    return json.dumps(
        {
            "directly_seen": [
                {
                    "observation_id": "seen-1",
                    "statement": "A dimension line is visible in the crop.",
                    "view_id": view_id,
                    "box_original_pixels": box,
                }
            ],
            "interpretations": [
                {
                    "interpretation_id": "interpretation-1",
                    "statement": "The line may describe the adjacent opening.",
                    "based_on_observation_ids": ["seen-1"],
                    "confidence": "medium",
                }
            ],
            "uncertain": [
                {
                    "uncertainty_id": "uncertain-1",
                    "statement": "The crop alone does not establish the real building size.",
                    "related_observation_ids": ["seen-1"],
                }
            ],
        }
    )


def _store(tmp_path):
    return EventStore(
        tmp_path / "audit",
        run_id="delegation-test",
        task_id="coordinator",
        budget_limit=BudgetAmounts(
            tokens=100_000,
            calls=100,
            seconds=Decimal("600"),
        ),
    )


def test_hydrate_observation_preserves_three_sections_and_original_pixel_box(tmp_path):
    with _store(tmp_path) as store:
        view = _registered_view(store)
        package = _package(view)

        result = hydrate_observation(_answer(), package, [view])

    assert result.package_id == package.package_id
    assert result.task_id == package.task_id
    assert result.based_on_source_model_version_id == "source-v1"
    assert result.directly_seen[0].location.image_ref == view.reference
    assert result.directly_seen[0].location.box_original_pixels == (20.0, 30.0, 40.0, 50.0)
    assert result.interpretations[0].based_on_observation_ids == ("seen-1",)
    assert result.uncertain[0].related_observation_ids == ("seen-1",)


@pytest.mark.parametrize(
    ("answer", "message"),
    [
        (_answer(view_id="view_9999"), "image not supplied"),
        # This box is valid in the 100x100 original but outside the delivered
        # crop, which begins at original x=10 and y=20.
        (_answer(box=(5.0, 30.0, 40.0, 50.0)), "outside its delivered crop"),
    ],
)
def test_hydrate_observation_rejects_undelivered_or_out_of_crop_evidence(
    tmp_path, answer, message
):
    with _store(tmp_path) as store:
        view = _registered_view(store)
        package = _package(view)

        with pytest.raises(ValueError, match=message):
            hydrate_observation(answer, package, [view])


class _ForbiddenWriteTools:
    def __init__(self, run_directory):
        self.run_directory = run_directory
        self.calls = []

    def repeatability(self, _name):
        return "non_idempotent_write"

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        raise AssertionError("the backing client must not receive a denied write")


def test_evidence_tools_reject_write_before_backing_client(tmp_path):
    with _store(tmp_path) as store:
        view = _registered_view(store)
        frozen = _ForbiddenWriteTools(tmp_path)
        tools = EvidenceTools(
            frozen,
            local_observer_role(BudgetAmounts(calls=2)),
            [view],
        )

        with pytest.raises(ValueError, match="not whitelisted|no write grant"):
            asyncio.run(tools.call_tool("revise_bim", {"revision_note": "must be denied"}))

    assert frozen.calls == []


@pytest.mark.parametrize("image_key", ["plan_image", "elevation_image"])
def test_evidence_tools_refuse_undelivered_facade_inputs(tmp_path, image_key):
    with _store(tmp_path) as store:
        frozen = _ForbiddenWriteTools(tmp_path)
        frozen.repeatability = lambda name: "read_only"
        tools = EvidenceTools(frozen, local_observer_role(BudgetAmounts(calls=2)),
                              [_registered_view(store)])
        result = asyncio.run(tools.call_tool("compare_facade_spans", {
            "plan_image": "plan.png", "elevation_image": "plan.png",
            image_key: "undelivered.png"}))

        assert result["isError"] is True
        assert result["structuredContent"] == {
            "status": "evidence_scope_rejected",
            "reason": "tool image is outside the local evidence package: " + image_key,
            "tool_image_names": ["plan.png"],
        }
        assert frozen.calls == []


class _ReadOnlyTools:
    def __init__(self, run_directory):
        self.run_directory = run_directory
        self.calls = []

    def repeatability(self, _name):
        return "read_only"

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {
            "content": [{"type": "text", "text": "profile measured"}],
            "structuredContent": {"status": "ok"},
            "isError": False,
        }


def test_evidence_tools_reject_out_of_crop_profile_and_allow_in_crop_profile(tmp_path):
    with _store(tmp_path) as store:
        frozen = _ReadOnlyTools(tmp_path)
        tools = EvidenceTools(
            frozen,
            local_observer_role(BudgetAmounts(calls=2)),
            [_registered_view(store)],
        )

        rejected = asyncio.run(tools.call_tool("pixel_profile", {
            "name": "plan.png",
            "box": [5, 30, 40, 50],
            "axis": "x",
            "rgb": [255, 255, 255],
            "tolerance": 10,
        }))
        assert rejected["isError"] is True
        assert rejected["structuredContent"] == {
            "status": "evidence_scope_rejected",
            "reason": "measurement lies outside the supplied crop",
            "tool_image_names": ["plan.png"],
        }
        assert frozen.calls == []

        allowed_arguments = {
            "name": "plan.png",
            "box": [20, 30, 40, 50],
            "axis": "x",
            "rgb": [255, 255, 255],
            "tolerance": 10,
        }
        allowed = asyncio.run(tools.call_tool("pixel_profile", allowed_arguments))
        assert allowed["isError"] is False
        assert frozen.calls == [("pixel_profile", allowed_arguments)]


def _response(*, text=None, calls=()):
    message = {"role": "assistant", "content": text}
    if calls:
        message["tool_calls"] = [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)},
            }
            for call_id, name, arguments in calls
        ]
    return {
        "id": "scripted-observer-response",
        "model": "scripted-observer",
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": "tool_calls" if calls else "stop",
        }],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }


class _ObserverFrozenTools:
    def __init__(self, run_directory):
        self.run_directory = run_directory
        self.calls = []

    async def list_tools(self):
        return [{
            "name": "pixel_profile",
            "description": "Measure an existing image by original-pixel coordinates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "box": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "axis": {"type": "string"},
                },
                "required": ["name", "box", "axis"],
            },
        }]

    def repeatability(self, _name):
        return "read_only"

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        raise AssertionError("a rejected image name must not reach the frozen client")

    def snapshot_state(self):
        return {}

    def image_origins(self, _raw):
        return {}


class _MeasuringObserverFrozenTools(_ObserverFrozenTools):
    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {
            "content": [{"type": "text", "text": "profile measured"}],
            "structuredContent": {"status": "ok"},
            "isError": False,
        }


def _profile_call(call_id, *, box=(20, 30, 40, 50)):
    return (
        call_id,
        "pixel_profile",
        {"name": "plan.png", "box": list(box), "axis": "x"},
    )


def _run_scripted_observer(tmp_path, *, task_id, limits, responses):
    adapter = ScriptedAdapter(responses)
    frozen = _MeasuringObserverFrozenTools(tmp_path)
    with EventStore(
        tmp_path / "observer-run",
        run_id=task_id + "-run",
        task_id="coordinator",
        budget_limit=BudgetAmounts(
            tokens=300_000,
            calls=6,
            seconds=Decimal("180"),
        ),
    ) as root_store:
        store = root_store.for_task(task_id, parent_task_id="coordinator")
        view = _registered_view(store)
        outcome = asyncio.run(run_observer(
            store=store,
            frozen_tools=frozen,
            adapter=adapter,
            model="scripted-observer",
            parameters={"max_tokens": 4096, "temperature": 0.0},
            limits=limits,
            package=_package(view, task_id=task_id),
            views=[view],
            notes=["offline scripted observer budget revision test"],
            root=ROOT,
            route={"route_id": "offline-test", "model": "scripted-observer"},
        ))
        executions = [
            event.payload
            for event in store.events
            if event.payload.event_type == "tool_execution"
        ]
    return outcome, adapter, frozen, executions


@lru_cache
def _stage3_west_answer(run_id):
    expected = {
        "final_02_27b": (
            "role_final/final_02_27b/role_case.json",
            "e83002fc70f0ca1dfbd0b48344f27a85baba4231032014c2eae32609b2fe8999",
        ),
        "final_02_flash": (
            "role_final/final_02_flash/role_case.json",
            "7dd0427bac016a658b386df45efabae4be9fdd129ab769dbd5b3f177e1ddf08c",
        ),
    }
    archived_path, answer_sha256 = expected[run_id]
    archive = (ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage3"
        / "evidence_all.compact.tar.xz")
    with tarfile.open(archive) as bundle:
        manifest = json.loads(bundle.extractfile("manifest.json").read())
        entry = manifest["files"][archived_path]
        raw = bundle.extractfile(entry["object"]).read()
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    role_case = json.loads(raw)
    assert role_case["run_id"] == run_id
    answer = role_case["outcome"]["runtime"]["answer"]
    assert hashlib.sha256(answer.encode("utf-8")).hexdigest() == answer_sha256
    return answer


def _correct_stage3_reference_answer(answer):
    corrected = json.loads(json.dumps(answer))
    replacements = {
        "int_chain_left": "obs_left_chain",
        "int_chain_right": "obs_right_chain",
    }
    for row in corrected["interpretations"]:
        row["based_on_observation_ids"] = [
            replacements.get(reference, reference)
            for reference in row["based_on_observation_ids"]
        ]
    return corrected


def _run_west_format_repair(tmp_path, *, task_id, first, second, model_calls=2):
    adapter = ScriptedAdapter([
        _response(text=first),
        second if isinstance(second, dict) else _response(text=second),
    ])
    limits = RunLimits(model_calls=model_calls, tool_calls=0, seconds=60.0, tokens=1_000_000)
    with EventStore(tmp_path / "observer-run", run_id=task_id + "-run",
            task_id="coordinator", budget_limit=BudgetAmounts(
                tokens=2_000_000, calls=4, seconds=Decimal("120"))) as root_store:
        store = root_store.for_task(task_id, parent_task_id="coordinator")
        view = _registered_west_view(store)
        outcome = asyncio.run(run_observer(store=store,
            frozen_tools=_MeasuringObserverFrozenTools(tmp_path), adapter=adapter,
            model="scripted-observer", parameters={"max_tokens": 4096, "temperature": 0.0},
            limits=limits, package=_package(view, task_id=task_id), views=[view],
            notes=["stage-3 final west answer format-repair counterexample"], root=ROOT,
            route={"route_id": "offline-test", "model": "scripted-observer"}))
        repairs = [event.payload for event in store.events
                   if event.payload.event_type == "answer_repair"]
        resolved = [{**row.model_dump(mode="json"),
                     "original_answer_value": store.resolve(row.original_answer),
                     "repaired_answer_value": (store.resolve(row.repaired_answer)
                         if row.repaired_answer else None)} for row in repairs]
        root_store.validate()
    return outcome, adapter, resolved


@pytest.mark.parametrize("failure", ["extra_closing_bracket", "interpretation_ids"])
def test_stage3_real_format_failures_are_repaired_once_and_recorded(tmp_path, failure):
    if failure == "extra_closing_bracket":
        invalid = _stage3_west_answer("final_02_27b")
        _, valid_prefix_end = json.JSONDecoder().raw_decode(invalid)
        assert invalid[valid_prefix_end:] == "}"
        corrected = invalid[:valid_prefix_end]
    else:
        invalid = _stage3_west_answer("final_02_flash")
        corrected = json.dumps(_correct_stage3_reference_answer(json.loads(invalid)), ensure_ascii=False)

    outcome, adapter, repairs = _run_west_format_repair(tmp_path,
        task_id="repair-" + failure, first=invalid, second=corrected)

    assert outcome["status"] == "completed"
    assert outcome["runtime"]["model_calls"] == 2
    assert len(outcome["runtime"]["task_budget"]["reservations"]) == 2
    assert len(outcome["runtime"]["task_budget"]["settlements"]) == 2
    assert len(adapter.requests) == 2
    assert [row["phase"] for row in repairs] == ["request", "result"]
    assert repairs[0]["original_answer_value"] == invalid
    assert repairs[1]["original_answer_value"] == invalid
    assert repairs[1]["repaired_answer_value"] == corrected
    assert repairs[1]["accepted"] is True
    repair_wire = json.loads(adapter.requests[1])
    repair_messages = [message["content"] for message in repair_wire["messages"]
                       if isinstance(message.get("content"), str)
                       and "single allowed repair" in message["content"]]
    assert len(repair_messages) == 1
    assert repairs[0]["validation_error"] in repair_messages[0]


@pytest.mark.parametrize("failure", ["extra_closing_bracket", "interpretation_ids"])
def test_stage3_real_format_failures_still_wrong_are_rejected_after_one_repair(tmp_path, failure):
    if failure == "extra_closing_bracket":
        answer = _stage3_west_answer("final_02_27b")
    else:
        answer = _stage3_west_answer("final_02_flash")

    outcome, adapter, repairs = _run_west_format_repair(tmp_path,
        task_id="reject-" + failure, first=answer, second=answer)

    assert outcome["status"] == "answer_validation_failed"
    assert outcome["result"] is None
    assert outcome["runtime"]["model_calls"] == 2
    assert len(adapter.requests) == 2
    assert [row["phase"] for row in repairs] == ["request", "result"]
    assert repairs[1]["accepted"] is False
    assert repairs[1]["repaired_validation_error"]


def test_format_repair_without_remaining_model_budget_records_request_but_does_not_send(tmp_path):
    invalid = _stage3_west_answer("final_02_27b")
    outcome, adapter, repairs = _run_west_format_repair(tmp_path,
        task_id="repair-no-budget", first=invalid, second="unused", model_calls=1)

    assert outcome["status"] == "child_model_budget_exhausted"
    assert outcome["result"] is None
    assert outcome["runtime"]["model_calls"] == 1
    assert len(adapter.requests) == 1
    assert [row["phase"] for row in repairs] == ["request"]
    assert repairs[0]["original_answer_value"] == invalid


def test_format_repair_tool_call_is_rejected_without_execution_or_third_request(tmp_path):
    invalid = _stage3_west_answer("final_02_27b")
    outcome, adapter, repairs = _run_west_format_repair(tmp_path,
        task_id="repair-tool-call", first=invalid,
        second=_response(calls=(_profile_call("repair-tool"),)), model_calls=3)

    assert outcome["status"] == "answer_validation_failed"
    assert outcome["runtime"]["tool_calls"] == 0
    assert len(adapter.requests) == 2
    assert json.loads(adapter.requests[1]).get("tools", []) == []
    assert [row["phase"] for row in repairs] == ["request", "result"]
    assert repairs[-1]["accepted"] is False
    assert repairs[-1]["repaired_validation_error"] == (
        "the single answer repair response must not invoke tools"
    )


def _remaining_budget_entry(wire_bytes):
    body = json.loads(wire_bytes)
    state_messages = [
        message["content"]
        for message in body["messages"]
        if message["role"] == "user"
        and isinstance(message.get("content"), str)
        and message["content"].startswith("Current runtime state")
    ]
    assert len(state_messages) == 1
    entries = json.loads(state_messages[0].partition(": ")[2])
    return next(entry for entry in entries
                if entry["key"] == "observer-remaining-budget")


def test_run_observer_updates_budget_revision_for_two_tools_in_one_response(tmp_path):
    limits = RunLimits(
        model_calls=2,
        tool_calls=3,
        seconds=60.0,
        tokens=100_000,
    )
    outcome, adapter, frozen, executions = _run_scripted_observer(
        tmp_path,
        task_id="observer-two-tools-one-turn",
        limits=limits,
        responses=[
            _response(calls=(
                _profile_call("profile-left"),
                _profile_call("profile-right", box=(40, 30, 60, 50)),
            )),
            _response(text=_answer()),
        ],
    )

    assert outcome["status"] == "completed"
    assert [execution.outcome for execution in executions] == ["succeeded", "succeeded"]
    assert len(frozen.calls) == 2
    assert len(adapter.requests) == 2
    remaining = _remaining_budget_entry(adapter.requests[1])
    assert remaining["revision"] == 2
    assert remaining["value"]["model_calls"] == 1
    assert remaining["value"]["tool_calls"] == 1


def test_run_observer_updates_budget_revision_across_two_tool_rounds(tmp_path):
    limits = RunLimits(
        model_calls=3,
        tool_calls=3,
        seconds=60.0,
        tokens=100_000,
    )
    outcome, adapter, frozen, executions = _run_scripted_observer(
        tmp_path,
        task_id="observer-two-tool-rounds",
        limits=limits,
        responses=[
            _response(calls=(_profile_call("profile-first"),)),
            _response(calls=(_profile_call("profile-second", box=(40, 30, 60, 50)),)),
            _response(text=_answer()),
        ],
    )

    assert outcome["status"] == "completed"
    assert [execution.outcome for execution in executions] == ["succeeded", "succeeded"]
    assert len(frozen.calls) == 2
    assert len(adapter.requests) == 3
    after_first = _remaining_budget_entry(adapter.requests[1])
    assert after_first["revision"] == 1
    assert after_first["value"]["model_calls"] == 2
    assert after_first["value"]["tool_calls"] == 2
    after_second = _remaining_budget_entry(adapter.requests[2])
    assert after_second["revision"] == 2
    assert after_second["value"]["model_calls"] == 1
    assert after_second["value"]["tool_calls"] == 1


def test_run_observer_recovers_from_known_bad_image_name_with_budget_update(tmp_path):
    root_limits = BudgetAmounts(tokens=200_000, calls=4, seconds=Decimal("120"))
    child_limits = RunLimits(
        model_calls=2,
        tool_calls=2,
        seconds=60.0,
        tokens=100_000,
    )
    adapter = ScriptedAdapter([
        _response(calls=((
            "bad-image-name",
            "pixel_profile",
            {"name": "measurement-label", "box": [20, 30, 40, 50], "axis": "x"},
        ),)),
        _response(text=_answer()),
    ])

    with EventStore(
        tmp_path / "observer-run",
        run_id="observer-wire-test",
        task_id="coordinator",
        budget_limit=root_limits,
    ) as root_store:
        store = root_store.for_task("observer-wire", parent_task_id="coordinator")
        view = _registered_view(store)
        package = _package(view, task_id="observer-wire")
        frozen = _ObserverFrozenTools(tmp_path)

        outcome = asyncio.run(run_observer(
            store=store,
            frozen_tools=frozen,
            adapter=adapter,
            model="scripted-observer",
            parameters={"max_tokens": 4096, "temperature": 0.0},
            limits=child_limits,
            package=package,
            views=[view],
            notes=["offline scripted observer test"],
            root=ROOT,
            route={"route_id": "offline-test", "model": "scripted-observer"},
        ))

        assert outcome["status"] == "completed"
        assert outcome["runtime"]["status"] == "completed"
        assert outcome["result"]["directly_seen"][0]["observation_id"] == "seen-1"
        assert frozen.calls == []

        executions = [
            event.payload
            for event in store.events
            if event.payload.event_type == "tool_execution"
        ]
        assert len(executions) == 1
        assert executions[0].outcome == "failed"
        rejected = store.resolve(executions[0].raw_result)
        assert rejected["isError"] is True
        assert rejected["structuredContent"]["status"] == "evidence_scope_rejected"
        assert not [event for event in store.events
                    if event.payload.event_type == "tool_execution"
                    and event.payload.outcome == "unknown"]

    first_wire, second_wire = [json.loads(raw) for raw in adapter.requests]
    first_payload = json.loads(first_wire["messages"][1]["content"][0]["text"])
    assert first_payload["task_limits"] == child_limits.model_dump(mode="json")
    assert first_payload["tool_image_names"] == ["plan.png"]
    state_messages = [
        message["content"]
        for message in second_wire["messages"]
        if message["role"] == "user" and isinstance(message.get("content"), str)
        and message["content"].startswith("Current runtime state")
    ]
    assert len(state_messages) == 1
    assert '"key":"observer-remaining-budget"' in state_messages[0]
    assert '"model_calls":1' in state_messages[0]
    assert '"tool_calls":1' in state_messages[0]


class _CoordinatorTools:
    def __init__(self, run_directory):
        self.run_directory = run_directory
        self.calls = []
        self.catalog = [
            {
                "name": "revise_bim",
                "description": "Test-only coordinator write.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"revision_note": {"type": "string", "minLength": 1}},
                    "required": ["revision_note"],
                    "additionalProperties": False,
                },
            }
        ]

    async def list_tools(self):
        return self.catalog

    def repeatability(self, _name):
        return "non_idempotent_write"

    def snapshot_state(self):
        return {"files": {}}

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {
            "content": [{"type": "text", "text": "revision recorded"}],
            # This coordinator fixture represents a real geometric write.
            # C3-T integration checks exercise the corresponding persisted BIM.
            "structuredContent": {"status": "ok", "saved_candidate": "candidate_01",
                "save_effects": {"created_candidates": ["candidate_01"],
                    "geometry_applied": True, "audit_written": True}},
            "isError": False,
        }

    def image_origins(self, _raw):
        return {}


def _seed_completed_child(session, view, task_id, version):
    package = _package(view, task_id=task_id, version=version)
    result = hydrate_observation(_answer(), package, [view])
    session.children[task_id] = {
        "status": "completed",
        "package": package.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "views": [view.as_json()],
    }


def _application(task_id):
    return {
        "task_id": task_id,
        "tool_name": "revise_bim",
        "arguments": {"revision_note": "Apply checked local evidence."},
        "reason": "The coordinator reviewed the localized evidence.",
    }


def test_coordinator_applies_current_result_once_rejects_stale_and_logs_rejections(tmp_path):
    run_directory = tmp_path / "bim"
    run_directory.mkdir()
    inputs = run_directory / "inputs.json"
    inputs.write_text('{"revision": 1}', encoding="utf-8")
    frozen = _CoordinatorTools(run_directory)

    with _store(tmp_path) as store:
        view = _registered_view(store)
        session = CoordinatorSession(
            store=store,
            tools=frozen,
            observer_tools=object(),
            adapter_factory=lambda _task_id: (_ for _ in ()).throw(
                AssertionError("no model adapter should be constructed")
            ),
            model="offline-test-model",
            parameters={},
        )
        asyncio.run(session.initialize())

        current_version = session.source_bim()["version_id"]
        _seed_completed_child(session, view, "current-child", current_version)
        inspected = session.inspect("current-child")
        assert inspected["applicable"] is True
        assert inspected["applicability_reason"] == "current_source_version"

        first = asyncio.run(session.call_tool("apply_local_observation", _application("current-child")))
        assert first["isError"] is False
        assert frozen.calls == [
            ("revise_bim", {"revision_note": "Apply checked local evidence."})
        ]
        assert session.inspect("current-child")["applicability_reason"] == "already_applied"

        repeated = asyncio.run(
            session.call_tool("apply_local_observation", _application("current-child"))
        )
        assert repeated["isError"] is True
        assert repeated["structuredContent"]["status"] == "rejected"
        assert "already_applied" in repeated["structuredContent"]["reason"]
        assert len(frozen.calls) == 1

        stale_version = session.source_bim()["version_id"]
        _seed_completed_child(session, view, "stale-child", stale_version)
        inputs.write_text('{"revision": 2}', encoding="utf-8")
        stale = session.inspect("stale-child")
        assert stale["applicable"] is False
        assert "stale source model version" in stale["applicability_reason"]

        rejected_stale = asyncio.run(
            session.call_tool("apply_local_observation", _application("stale-child"))
        )
        assert rejected_stale["isError"] is True
        assert "stale source model version" in rejected_stale["structuredContent"]["reason"]
        assert len(frozen.calls) == 1

        invalid = asyncio.run(session.call_tool("unknown_tool", {"unexpected": True}))
        assert invalid["isError"] is True
        assert invalid["structuredContent"] == {
            "status": "rejected",
            "reason": "unknown coordinator tool",
        }

        external = [
            event
            for event in store.events
            if event.payload.event_type == "external_coordinator_mcp"
        ]
        invalid_events = [event for event in external if event.payload.method == "unknown_tool"]
        assert [event.payload.phase for event in invalid_events] == ["operation", "return"]
        assert all(
            any(source.source_id == "external-model-request-and-usage" for source in event.source_refs)
            for event in invalid_events
        )
