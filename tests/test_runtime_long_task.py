from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


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

    import asyncio

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
