from __future__ import annotations

import asyncio
import base64
import gzip
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from src.agent_runtime.adapter import ScriptedAdapter
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore
from src.harness_contracts import (
    BudgetAmounts,
    InputMaterialRequirement,
    RemoteModelIdentity,
    ReturnRequirement,
    RoleDefinition,
    ToolGrant,
    VersionManifest,
    VersionStamp,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE2_DIRECTORY = (
    REPOSITORY_ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage2"
)
FIXTURE_PATH = STAGE2_DIRECTORY / "run99_long_fixture.json"
SOURCE_MANIFEST_PATH = STAGE2_DIRECTORY / "source_manifest.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


class Run99Sequence:
    """Load exact historical calls/results without copying their base64 fixture."""

    def __init__(self) -> None:
        self.fixture = json.loads(FIXTURE_PATH.read_bytes())
        self.source_manifest = json.loads(SOURCE_MANIFEST_PATH.read_bytes())
        self._verify_source_files()
        stream_path = self._path(self.fixture["source_stream"])
        with gzip.open(stream_path, "rt", encoding="utf-8") as stream:
            self.stream_lines = [None, *(json.loads(line) for line in stream)]
        self.steps = [self._load_step(item) for item in self.fixture["steps"]]

    def _path(self, relative: str) -> Path:
        path = (REPOSITORY_ROOT / relative).resolve()
        if not path.is_relative_to(REPOSITORY_ROOT):
            raise ValueError("historical fixture path escapes repository")
        return path

    def _verify_source_files(self) -> None:
        for item in self.source_manifest["sources"].values():
            data = self._path(item["path"]).read_bytes()
            assert len(data) == item["byte_size"]
            assert _sha256(data) == item["sha256"]

    @staticmethod
    def _at_path(value: Any, path: list[Any]) -> Any:
        for component in path:
            value = value[component]
        return value

    def _image_bytes(self, image: dict[str, Any], historical_block: dict[str, Any]) -> bytes:
        historical = base64.b64decode(historical_block["source"]["data"], validate=True)
        origin = image["origin"]
        if origin["kind"] == "historical_file":
            stored = self._path(origin["files"][0]["path"]).read_bytes()
            assert stored == historical
            value = stored
        else:
            located = self._at_path(
                self.stream_lines[origin["line"]], origin["json_path"]
            )
            value = base64.b64decode(located["source"]["data"], validate=True)
            assert value == historical
        assert len(value) == image["byte_size"]
        assert _sha256(value) == image["sha256"]
        return value

    def _load_step(self, item: dict[str, Any]) -> dict[str, Any]:
        call_record = self.stream_lines[item["call"]["stream_line"]]
        call = call_record["message"]["content"][item["call"]["content_block"]]
        result_record = self.stream_lines[item["result"]["stream_line"]]
        result = result_record["message"]["content"][item["result"]["content_block"]]
        assert call["id"] == result["tool_use_id"] == item["call"]["tool_call_id"]
        assert call["name"].removeprefix("mcp__bim__") == item["tool_name"]
        assert _sha256(_canonical_bytes(call["input"])) == item["call"]["arguments_sha256"]
        assert _sha256(_canonical_bytes(result["content"])) == item["result"]["content_sha256"]

        source_content = result["content"]
        blocks = (
            [{"type": "text", "text": source_content}]
            if isinstance(source_content, str)
            else source_content
        )
        expected_images = {image["response_block"]: image for image in item["result"]["images"]}
        normalized: list[dict[str, Any]] = []
        for block_index, block in enumerate(blocks):
            if block.get("type") == "image":
                image = expected_images.pop(block_index)
                raw = self._image_bytes(image, block)
                normalized.append(
                    {
                        "type": "image",
                        "mimeType": block["source"]["media_type"],
                        "data": base64.b64encode(raw).decode("ascii"),
                    }
                )
            else:
                normalized.append(block)
        assert not expected_images
        return {
            **item,
            "tool_call_id": call["id"],
            "arguments": call["input"],
            "raw_result": {
                "isError": bool(result.get("is_error", False)),
                "content": normalized,
            },
        }

    def scripted_responses(self, *, final_text: str = "fixture complete") -> list[dict[str, Any]]:
        responses: list[dict[str, Any]] = []
        for item in self.steps:
            responses.append(
                {
                    "id": f"fixture-response-{item['ordinal']:03d}",
                    "model": "offline-run99-fixture",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": item["tool_call_id"],
                                        "type": "function",
                                        "function": {
                                            "name": item["tool_name"],
                                            "arguments": json.dumps(
                                                item["arguments"],
                                                ensure_ascii=False,
                                                separators=(",", ":"),
                                            ),
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    # Explicit fixture usage; it is not provider usage.
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 10,
                        "total_tokens": 20,
                    },
                }
            )
        responses.append(
            {
                "id": "fixture-response-final",
                "model": "offline-run99-fixture",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": final_text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                    "total_tokens": 20,
                },
            }
        )
        return responses


class HistoricalToolBackend:
    """Replay run99 results and isolate every simulated source-BIM write."""

    def __init__(
        self,
        sequence: Run99Sequence,
        state_directory: Path,
        *,
        start_step: int = 0,
        unknown_write_ordinal: int | None = None,
    ) -> None:
        self.sequence = sequence
        self.state_directory = state_directory
        self.state_directory.mkdir(parents=True, exist_ok=True)
        self.source_model_path = self.state_directory / "source_model.json"
        self.ledger_path = self.state_directory / "applied_operations.json"
        seed = sequence.source_manifest["sources"]["isolated_write_seed"]
        if not self.source_model_path.exists():
            shutil.copyfile(sequence._path(seed["path"]), self.source_model_path)
        if not self.ledger_path.exists():
            self._write_ledger([])
        self.position = start_step
        self.unknown_write_ordinal = unknown_write_ordinal
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._origins_by_sha: dict[str, dict[str, Any]] = {}
        for step in self.sequence.steps:
            metadata = self._result_metadata(step["raw_result"])
            images = [
                block
                for block in step["raw_result"]["content"]
                if block.get("type") == "image"
            ]
            identity = (
                metadata.get("view_id")
                or metadata.get("overview_id")
                or metadata.get("profile_id")
                or (metadata.get("result") or {}).get("profile_id")
                or f"run99-step-{step['ordinal']:03d}"
            )
            for index, block in enumerate(images):
                digest = _sha256(base64.b64decode(block["data"], validate=True))
                # Identical bytes may recur in several saved candidates. Their
                # first historical identity is stable and sufficient for exact
                # retrieval by view_id + hash.
                self._origins_by_sha.setdefault(
                    digest,
                    {
                        "view_id": (
                            identity
                            if len(images) == 1
                            else f"{identity}:image-{index + 1}"
                        ),
                        "tags": tuple(
                            value
                            for value in (
                                f"tool:{step['tool_name']}",
                                (
                                    f"image:{step['arguments'].get('name')}"
                                    if step["arguments"].get("name")
                                    else None
                                ),
                            )
                            if value
                        ),
                    },
                )

    @staticmethod
    def _result_metadata(raw_result: dict[str, Any]) -> dict[str, Any]:
        for block in raw_result["content"]:
            if block.get("type") != "text":
                continue
            try:
                decoded = json.loads(block["text"])
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(decoded, dict):
                return decoded
        return {}

    async def list_tools(self) -> list[dict[str, Any]]:
        names = tuple(dict.fromkeys(item["tool_name"] for item in self.sequence.steps))
        return [
            {
                "name": name,
                "description": f"offline historical fixture tool {name}",
                "inputSchema": {"type": "object", "additionalProperties": True},
            }
            for name in names
        ]

    def repeatability(self, name: str) -> str:
        matches = {
            item["repeatability"]
            for item in self.sequence.steps
            if item["tool_name"] == name
        }
        assert len(matches) == 1
        return matches.pop()

    def _ledger(self) -> list[str]:
        return json.loads(self.ledger_path.read_bytes())

    def _write_ledger(self, entries: list[str]) -> None:
        temporary = self.ledger_path.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_bytes(_canonical_bytes(entries) + b"\n")
        os.replace(temporary, self.ledger_path)

    def _apply_write(self, step: dict[str, Any]) -> None:
        operation_key = f"historical-step-{step['ordinal']:03d}"
        ledger = self._ledger()
        if operation_key in ledger:
            raise AssertionError(f"non-idempotent fixture write repeated: {operation_key}")
        candidate = step["historical_candidate_source_model"]
        if candidate:
            shutil.copyfile(self.sequence._path(candidate), self.source_model_path)
        self._write_ledger([*ledger, operation_key])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.position >= len(self.sequence.steps):
            raise AssertionError("fixture received more tool calls than the historical sequence")
        step = self.sequence.steps[self.position]
        assert name == step["tool_name"]
        assert arguments == step["arguments"]
        self.position += 1
        self.calls.append((name, arguments))
        if step["repeatability"] != "read_only" and not step["is_error"]:
            self._apply_write(step)
            if step["ordinal"] == self.unknown_write_ordinal:
                raise ConnectionError("injected return-path loss after isolated fixture write")
        return step["raw_result"]

    def image_origins(self, raw_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            digest: self._origins_by_sha[digest]
            for digest in (
                _sha256(base64.b64decode(block["data"], validate=True))
                for block in raw_result.get("content", ())
                if block.get("type") == "image"
            )
            if digest in self._origins_by_sha
        }

    def snapshot_state(self) -> dict[str, str]:
        return {
            path.name: _sha256(path.read_bytes())
            for path in self.artifacts()
        }

    def artifacts(self) -> list[Path]:
        return sorted((self.source_model_path, self.ledger_path))


def test_run99_fixture_recovers_exact_ordered_calls_results_and_image_bytes():
    sequence = Run99Sequence()
    assert len(sequence.steps) == sequence.fixture["step_count"] == 75
    assert len(sequence.scripted_responses()) == 76
    assert Counter(step["repeatability"] for step in sequence.steps) == {
        "read_only": 56,
        "non_idempotent_write": 19,
    }
    images = [
        image
        for step in sequence.steps
        for image in step["result"]["images"]
    ]
    assert len(images) == 67
    assert len({image["sha256"] for image in images}) == 56
    assert sum(image["byte_size"] for image in images) == 2_259_103
    assert sum(step["is_error"] for step in sequence.steps) == 7


def test_simulated_backend_keeps_writes_in_copy_and_counts_each_once(tmp_path):
    sequence = Run99Sequence()
    backend = HistoricalToolBackend(sequence, tmp_path / "isolated-bim")
    seed_path = sequence._path(
        sequence.source_manifest["sources"]["isolated_write_seed"]["path"]
    )
    assert backend.source_model_path != seed_path
    assert backend.source_model_path.read_bytes() == seed_path.read_bytes()
    first_view = sequence.steps[1]["raw_result"]
    first_digest = sequence.steps[1]["result"]["images"][0]["sha256"]
    assert backend.image_origins(first_view)[first_digest]["view_id"] == "view_0001"

    async def replay() -> None:
        for step in sequence.steps:
            await backend.call_tool(step["tool_name"], step["arguments"])

    asyncio.run(replay())
    successful_writes = sum(
        step["repeatability"] != "read_only" and not step["is_error"]
        for step in sequence.steps
    )
    assert len(backend._ledger()) == successful_writes == 14
    assert backend.position == 75
    assert _sha256(seed_path.read_bytes()) == sequence.source_manifest["sources"][
        "isolated_write_seed"
    ]["sha256"]


MESSAGES = [
    {"role": "system", "content": "frozen run99 long-task fixture"},
    {"role": "user", "content": "replay the captured tool sequence"},
]


def _versions() -> VersionManifest:
    stamp = VersionStamp(identifier="run99-fixture-v1")
    return VersionManifest(
        code_commit=stamp,
        dependency_lock=stamp,
        prompt=stamp,
        tool_definitions=stamp,
        inference_parameters=stamp,
        model_route=stamp,
        remote_model=RemoteModelIdentity(
            route_id="offline-run99",
            remote_alias="offline-run99-fixture",
            alias_status="unverified",
        ),
    )


def _limits(*, model_calls: int = 90) -> RunLimits:
    return RunLimits(
        model_calls=model_calls,
        tool_calls=80,
        seconds=900.0,
        tokens=80_000_000,
        context_tokens=12_000_000,
        max_model_retries=1,
    )


def _role(sequence: Run99Sequence, limits: RunLimits) -> RoleDefinition:
    names = tuple(dict.fromkeys(item["tool_name"] for item in sequence.steps))
    return RoleDefinition(
        role_id="coordinator",
        responsibilities=("replay the offline run99 recovery fixture",),
        tool_whitelist=tuple(
            ToolGrant(
                tool_name=name,
                access=(
                    "read"
                    if next(
                        item["repeatability"]
                        for item in sequence.steps
                        if item["tool_name"] == name
                    )
                    == "read_only"
                    else "write"
                ),
            )
            for name in names
        ),
        input_materials=(
            InputMaterialRequirement(name="run99 fixture", media_type="application/json"),
        ),
        return_requirements=(
            ReturnRequirement(name="offline result", schema_ref="stage2/run99-fixture"),
        ),
        budget=limits.ledger_limit(),
    )


def _open_runtime(
    run_directory: Path,
    sequence: Run99Sequence,
    backend: HistoricalToolBackend,
    responses: list[dict[str, Any]],
    *,
    limits: RunLimits,
    fault_hook=None,
    retrieve_images: tuple[tuple[str, str], ...] = (),
) -> tuple[EventStore, Runtime, ScriptedAdapter]:
    store = EventStore(
        run_directory,
        run_id="run99-long-fixture",
        task_id="stage2-fault-injection",
        budget_limit=limits.ledger_limit(),
    )
    adapter = ScriptedAdapter(responses)
    engine = Runtime(
        store=store,
        adapter=adapter,
        tools=backend,
        role=_role(sequence, limits),
        model="offline-run99-fixture",
        parameters={"max_tokens": 64, "temperature": 0.0},
        versions=_versions(),
        limits=limits,
        context_policy=ContextPolicy(
            active_window_messages=8,
            preserve_initial_messages=2,
            max_images=2,
            max_image_bytes=250_000,
        ),
        fault_hook=fault_hook,
        retrieve_images=retrieve_images,
    )
    return store, engine, adapter


class InjectedCrash(BaseException):
    pass


class FaultOnce:
    def __init__(self, name: str, predicate) -> None:
        self.name = name
        self.predicate = predicate
        self.triggered = False
        self.observed: dict[str, Any] | None = None

    def __call__(self, name: str, engine: Runtime) -> None:
        if not self.triggered and name == self.name and self.predicate(engine):
            self.triggered = True
            self.observed = {
                "name": name,
                "model_calls": engine.counts["model_calls"],
                "tool_calls": engine.counts["tool_calls"],
                "stage": engine.stage,
            }
            raise InjectedCrash(name)


def _crash_then_resume(
    tmp_path: Path,
    *,
    fault: FaultOnce,
    retrieve_images: tuple[tuple[str, str], ...] = (),
) -> tuple[dict[str, Any], Run99Sequence, HistoricalToolBackend, Runtime, int, list[str]]:
    sequence = Run99Sequence()
    responses = sequence.scripted_responses()
    limits = _limits()
    run_directory = tmp_path / "run"
    backend = HistoricalToolBackend(sequence, tmp_path / "isolated-bim")
    store, engine, adapter = _open_runtime(
        run_directory,
        sequence,
        backend,
        responses,
        limits=limits,
        fault_hook=fault,
    )
    with store:
        with pytest.raises(InjectedCrash):
            asyncio.run(engine.run(MESSAGES))
    sent = len(adapter.requests)
    ledger_at_crash = list(backend._ledger())
    store, resumed, _ = _open_runtime(
        run_directory,
        sequence,
        backend,
        responses[sent:],
        limits=limits,
        retrieve_images=retrieve_images,
    )
    with store:
        receipt = asyncio.run(resumed.run(MESSAGES, resume=True))
    return receipt, sequence, backend, resumed, sent, ledger_at_crash


@pytest.mark.parametrize(
    ("hook_name", "predicate"),
    [
        ("before_request", lambda engine: engine.counts["model_calls"] == 20),
        ("after_request", lambda engine: engine.counts["model_calls"] == 20),
        ("after_response", lambda engine: engine.counts["model_calls"] == 20),
    ],
)
def test_long_run_recovers_across_request_boundaries(tmp_path, hook_name, predicate):
    fault = FaultOnce(hook_name, predicate)
    receipt, _, backend, _, _, _ = _crash_then_resume(tmp_path, fault=fault)
    assert fault.triggered and receipt["status"] == "completed"
    assert backend.position == 75
    assert len(backend._ledger()) == 14
    assert len({key for key in backend._ledger()}) == 14


def test_long_run_recovers_write_interrupted_before_intent(tmp_path):
    fault = FaultOnce(
        "before_tool",
        lambda engine: engine.counts["model_calls"] == 46,
    )
    receipt, _, backend, _, _, ledger_at_crash = _crash_then_resume(tmp_path, fault=fault)
    assert receipt["status"] == "completed"
    assert "historical-step-046" not in ledger_at_crash
    assert backend._ledger().count("historical-step-046") == 1


def test_long_run_replays_durable_write_result_without_repeating_write(tmp_path):
    fault = FaultOnce(
        "after_execution",
        lambda engine: engine.counts["tool_calls"] == 46,
    )
    receipt, _, backend, _, _, ledger_at_crash = _crash_then_resume(tmp_path, fault=fault)
    assert receipt["status"] == "completed"
    assert ledger_at_crash.count("historical-step-046") == 1
    assert backend._ledger().count("historical-step-046") == 1


def test_long_run_unknown_write_stops_after_state_check_without_retry(tmp_path):
    fault = FaultOnce(
        "after_tool",
        lambda engine: engine.counts["tool_calls"] == 71,
    )
    receipt, _, backend, resumed, _, ledger_at_crash = _crash_then_resume(
        tmp_path,
        fault=fault,
    )
    assert receipt["status"] == "resume_pending_operation"
    assert ledger_at_crash.count("historical-step-071") == 1
    assert backend._ledger().count("historical-step-071") == 1
    assert backend.position == 71
    inspections = [
        event.payload
        for event in resumed.store.events
        if event.payload.event_type == "state_inspection"
        and event.payload.purpose == "unknown_write_recovery"
    ]
    assert inspections and inspections[-1].conclusion == "inconclusive"


def test_long_run_recovers_after_compaction_and_retrieves_exact_removed_image(tmp_path):
    sequence = Run99Sequence()
    first_image = sequence.steps[1]["result"]["images"][0]
    fault = FaultOnce(
        "after_checkpoint",
        lambda engine: engine.counts["tool_calls"] == 40,
    )
    receipt, _, backend, resumed, _, _ = _crash_then_resume(
        tmp_path,
        fault=fault,
        retrieve_images=(("view_0001", first_image["sha256"]),),
    )
    assert receipt["status"] == "completed"
    assert len(backend._ledger()) == 14
    context_envelopes = [
        event
        for event in resumed.store.events
        if event.payload.event_type == "context"
    ]
    context_events = [event.payload for event in context_envelopes]
    assert any(event.action == "compact" for event in context_events)
    exact_retrieval = next(
        event
        for event in context_envelopes
        if event.payload.action == "retrieve_image"
        and event.payload.image.sha256 == first_image["sha256"]
    )
    retrieved_bytes = resumed.store.get_bytes(exact_retrieval.payload.image)
    assert _sha256(retrieved_bytes) == first_image["sha256"]
    assert len(retrieved_bytes) == first_image["byte_size"]
    request_after_retrieval = next(
        event
        for event in resumed.store.events
        if event.sequence > exact_retrieval.sequence
        and event.payload.event_type == "adapter_request"
        and any(
            transmission.sent.sha256 == first_image["sha256"]
            for transmission in event.payload.images
        )
    )
    sent = next(
        transmission.sent
        for transmission in request_after_retrieval.payload.images
        if transmission.sent.sha256 == first_image["sha256"]
    )
    assert resumed.store.get_bytes(sent) == retrieved_bytes
    full_messages, full_sources = resumed.context.full_history()
    assert len(full_messages) == len(full_sources)
    assert full_messages[:2] == MESSAGES
    assert full_messages[-1]["content"] == "fixture complete"


def test_long_run_budget_stops_before_sixty_first_model_call(tmp_path):
    sequence = Run99Sequence()
    responses = sequence.scripted_responses()
    limits = _limits(model_calls=60)
    backend = HistoricalToolBackend(sequence, tmp_path / "isolated-bim")
    store, engine, adapter = _open_runtime(
        tmp_path / "run",
        sequence,
        backend,
        responses,
        limits=limits,
    )
    with store:
        receipt = asyncio.run(engine.run(MESSAGES))
    assert receipt["status"] == "model_budget_exhausted"
    assert receipt["model_calls"] == len(adapter.requests) == 60
    assert receipt["tool_calls"] == backend.position == 60
