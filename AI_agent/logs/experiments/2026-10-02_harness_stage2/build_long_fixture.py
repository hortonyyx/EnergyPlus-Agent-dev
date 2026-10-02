#!/usr/bin/env python3
"""Build the compact run99 long-task fixture manifest.

The historical Claude stream already contains the exact returned image bytes.
This builder records locators and hashes rather than copying those base64 values
into another checked-in file.  A test loader can reconstruct each response from
the immutable historical stream and verify every referenced byte first.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
STAGE2_DIRECTORY = Path(__file__).resolve().parent
HISTORY_DIRECTORY = (
    REPOSITORY_ROOT
    / "AI_agent/logs/experiments/2026-09-30_sm21_instruction_fix_run99"
)
STREAM_PATH = HISTORY_DIRECTORY / "agent_stream.jsonl.gz"
TOOL_AUDIT_PATH = HISTORY_DIRECTORY / "tools.jsonl"
SEED_SOURCE_MODEL = HISTORY_DIRECTORY / "candidate_05/source_model.json"

READ_ONLY_TOOLS = frozenset(
    {
        "get_bim_reference",
        "inputs",
        "view_image",
        "view_pixel_profile",
        "view_pixel_region_overview",
        "view_claim_evidence",
        "claim_status",
        "inspect_candidate",
    }
)


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


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPOSITORY_ROOT).as_posix()


def _source_file(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": _relative(path),
        "byte_size": len(data),
        "sha256": _sha256(data),
    }


def _standalone_files_by_hash() -> dict[str, list[dict[str, Any]]]:
    matches: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(HISTORY_DIRECTORY.rglob("*")):
        if not path.is_file() or path == STREAM_PATH:
            continue
        data = path.read_bytes()
        matches.setdefault(_sha256(data), []).append(
            {"path": _relative(path), "byte_size": len(data)}
        )
    return matches


def _stream_records() -> tuple[list[dict[str, Any]], Counter[str]]:
    records: list[dict[str, Any]] = []
    kinds: Counter[str] = Counter()
    with gzip.open(STREAM_PATH, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            record = json.loads(line)
            records.append(record)
            kinds[str(record.get("type", "missing"))] += 1
            record["__source_line__"] = line_number
    return records, kinds


def _content_blocks(result: dict[str, Any]) -> list[dict[str, Any]]:
    content = result.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if not isinstance(content, list):
        raise ValueError(f"unsupported historical tool result content: {type(content)!r}")
    if not all(isinstance(block, dict) for block in content):
        raise ValueError("historical tool result has a non-object content block")
    return content


def _candidate_source(blocks: list[dict[str, Any]]) -> str | None:
    for block in blocks:
        if block.get("type") != "text" or not isinstance(block.get("text"), str):
            continue
        try:
            value = json.loads(block["text"])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("candidate"), str):
            path = HISTORY_DIRECTORY / value["candidate"] / "source_model.json"
            if path.is_file():
                return _relative(path)
    return None


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    records, record_kinds = _stream_records()
    standalone = _standalone_files_by_hash()
    calls: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    for record in records:
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        if record.get("type") == "assistant":
            for block_index, block in enumerate(content):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    name = str(block["name"])
                    if not name.startswith("mcp__bim__"):
                        raise ValueError(f"unexpected historical tool prefix: {name}")
                    arguments = block.get("input", {})
                    calls.append(
                        {
                            "tool_call_id": block["id"],
                            "tool_name": name.removeprefix("mcp__bim__"),
                            "arguments": arguments,
                            "request_id": record.get("request_id"),
                            "stream_line": record["__source_line__"],
                            "content_block": block_index,
                        }
                    )
        elif record.get("type") == "user":
            for block_index, block in enumerate(content):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    results.append(
                        {
                            "tool_call_id": block["tool_use_id"],
                            "result": block,
                            "stream_line": record["__source_line__"],
                            "content_block": block_index,
                        }
                    )

    if [item["tool_call_id"] for item in calls] != [item["tool_call_id"] for item in results]:
        raise ValueError("historical tool calls and results are not a one-to-one ordered sequence")
    if not 60 <= len(calls) <= 120:
        raise ValueError(f"fixture needs 60-120 steps, found {len(calls)}")

    steps: list[dict[str, Any]] = []
    image_block_count = 0
    image_total_bytes = 0
    unique_image_hashes: set[str] = set()
    standalone_image_blocks = 0
    stream_only_image_blocks = 0
    for ordinal, (call, returned) in enumerate(zip(calls, results, strict=True), 1):
        result = returned["result"]
        blocks = _content_blocks(result)
        images: list[dict[str, Any]] = []
        for block_index, block in enumerate(blocks):
            if block.get("type") != "image":
                continue
            source = block.get("source")
            if not isinstance(source, dict) or source.get("type") != "base64":
                raise ValueError("run99 fixture only supports captured base64 image blocks")
            raw = base64.b64decode(source["data"], validate=True)
            sha256 = _sha256(raw)
            file_matches = standalone.get(sha256, [])
            if file_matches:
                origin: dict[str, Any] = {
                    "kind": "historical_file",
                    "files": file_matches,
                }
                standalone_image_blocks += 1
            else:
                origin = {
                    "kind": "historical_stream",
                    "path": _relative(STREAM_PATH),
                    "line": returned["stream_line"],
                    "json_path": ["message", "content", returned["content_block"], "content", block_index],
                }
                stream_only_image_blocks += 1
            images.append(
                {
                    "response_block": block_index,
                    "media_type": source["media_type"],
                    "byte_size": len(raw),
                    "sha256": sha256,
                    "origin": origin,
                }
            )
            image_block_count += 1
            image_total_bytes += len(raw)
            unique_image_hashes.add(sha256)

        name = call["tool_name"]
        repeatability = "read_only" if name in READ_ONLY_TOOLS else "non_idempotent_write"
        steps.append(
            {
                "ordinal": ordinal,
                "tool_name": name,
                "repeatability": repeatability,
                "is_error": bool(result.get("is_error", False)),
                "call": {
                    "stream_line": call["stream_line"],
                    "content_block": call["content_block"],
                    "tool_call_id": call["tool_call_id"],
                    "request_id": call["request_id"],
                    "arguments_sha256": _sha256(_canonical_bytes(call["arguments"])),
                },
                "result": {
                    "stream_line": returned["stream_line"],
                    "content_block": returned["content_block"],
                    "content_sha256": _sha256(_canonical_bytes(result.get("content"))),
                    "images": images,
                },
                "historical_candidate_source_model": _candidate_source(blocks),
            }
        )

    action_counts = Counter(step["tool_name"] for step in steps)
    repeatability_counts = Counter(step["repeatability"] for step in steps)
    fixture = {
        "schema": "harness-stage2-long-fixture/v1",
        "fixture_id": "run99-75-tool-turns",
        "historical_run": "2026-09-30_sm21_instruction_fix_run99",
        "source_stream": _relative(STREAM_PATH),
        "step_count": len(steps),
        "script_shape": {
            "model_responses": len(steps) + 1,
            "tool_turns": len(steps),
            "final_response": "fixture complete",
            "grouping": "one scripted model response per historical tool use",
        },
        "image_summary": {
            "blocks": image_block_count,
            "unique_sha256": len(unique_image_hashes),
            "returned_bytes_in_order": image_total_bytes,
            "standalone_file_blocks": standalone_image_blocks,
            "stream_only_blocks": stream_only_image_blocks,
        },
        "steps": steps,
    }
    manifest = {
        "schema": "harness-stage2-source-manifest/v1",
        "fixture_id": fixture["fixture_id"],
        "sources": {
            "agent_stream": _source_file(STREAM_PATH),
            "tool_audit": _source_file(TOOL_AUDIT_PATH),
            "isolated_write_seed": _source_file(SEED_SOURCE_MODEL),
        },
        "observed_history": {
            "stream_records": sum(record_kinds.values()),
            "stream_record_types": dict(sorted(record_kinds.items())),
            "tool_audit_rows": sum(1 for _ in TOOL_AUDIT_PATH.open(encoding="utf-8")),
            "tool_uses_with_results": len(steps),
            "tool_action_counts": dict(sorted(action_counts.items())),
            "tool_repeatability_counts": dict(sorted(repeatability_counts.items())),
            "tool_errors": sum(step["is_error"] for step in steps),
            "images": fixture["image_summary"],
        },
        "adaptations": [
            "Only the 75 ordered model tool uses and their 75 results are scripted; prose, private thinking, rate-limit events, timestamps, and the final CLI receipt remain historical source material rather than model behaviour assertions.",
            "The mcp__bim__ prefix is removed so calls use the frozen runtime tool names.",
            "Concurrent calls originally emitted in one assistant message are split into one scripted model response per tool use, preserving their original order; a synthetic final text response is appended.",
            "Claude CLI tool-result blocks are converted mechanically to MCP result blocks at test load time; text, image byte order, media type, image byte size, and image sha256 are unchanged.",
            "Image base64 is not copied into this fixture. Exact bytes are loaded from a matching historical file when available, otherwise from the named gzip JSONL line, and verified against this manifest before use.",
            "Historical writes are never replayed into the historical directory. The simulator copies the saved source BIM seed into a test temporary directory and records each applied operation key there.",
            "Script usage and billing fields are explicit offline test data, not recovered provider usage and not evidence of a real model run.",
        ],
        "limits": {
            "offline_fixture_only": True,
            "real_model_calls": 0,
            "historical_building_quality_revalidated": False,
        },
    }
    return fixture, manifest


def main() -> None:
    fixture, manifest = build()
    for name, value in (
        ("run99_long_fixture.json", fixture),
        ("source_manifest.json", manifest),
    ):
        target = STAGE2_DIRECTORY / name
        target.write_bytes(_canonical_bytes(value) + b"\n")
    print(
        json.dumps(
            {
                "steps": fixture["step_count"],
                "images": fixture["image_summary"],
                "output": ["run99_long_fixture.json", "source_manifest.json"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
