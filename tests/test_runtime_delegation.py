import asyncio
import io
import json
from decimal import Decimal

import pytest
from PIL import Image

from src.agent.contracts import EvidencePackage
from src.agent.contracts.refs import (
    CoordinateRelation,
    ExistingEvidenceRef,
    RunQualifiedEvidenceRef,
)
from src.agent.runtime_coordinator import CoordinatorSession
from src.agent.runtime_delegation import EvidenceTools, RegisteredView, hydrate_observation
from src.agent.runtime_tools import local_observer_role
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts


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
        with pytest.raises(ValueError, match="outside the local evidence package"):
            asyncio.run(tools.call_tool("compare_facade_spans", {
                "plan_image": "plan.png", "elevation_image": "plan.png",
                image_key: "undelivered.png"}))
        assert frozen.calls == []


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
            "structuredContent": {"status": "ok"},
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
