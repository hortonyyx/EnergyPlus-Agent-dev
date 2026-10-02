"""Offline integrity checks for the Stage 0 historical-evidence fixtures."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/harness_stage0/sources"
EXTRACTOR = ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage0/extract_sources.py"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def records_with_hashes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            yield value
        for child in value.values():
            yield from records_with_hashes(child)
    elif isinstance(value, list):
        for child in value:
            yield from records_with_hashes(child)


def fixture_sources() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for fixture in sorted(FIXTURES.glob("*.json")):
        entries.extend(records_with_hashes(load(fixture)))
    return entries


def test_all_manifest_source_paths_match_archived_hashes() -> None:
    entries = fixture_sources()
    assert entries
    for entry in entries:
        source = ROOT / entry["path"]
        assert source.is_file(), entry
        assert digest(source) == entry["sha256"], entry


def test_run99_messages_are_exact_archived_stream_messages() -> None:
    fixture = load(FIXTURES / "claude_run99_excerpt.json")
    stream_path = ROOT / fixture["stream"]["source"]["path"]
    with gzip.open(stream_path, "rt", encoding="utf-8") as source:
        events = [json.loads(line) for line in source]

    for key in ("thinking_message", "visible_text_message", "tool_call_message", "tool_result_message"):
        recorded = fixture["stream"][key]
        event = events[recorded["line"] - 1]
        assert event["uuid"] == recorded["event_uuid"]
        assert event["message"] == recorded["message"]

    thinking = fixture["stream"]["thinking_message"]["message"]["content"][0]
    tool_call = fixture["stream"]["tool_call_message"]["message"]["content"][0]
    tool_result = fixture["stream"]["tool_result_message"]["message"]["content"][0]
    assert thinking["type"] == "thinking"
    assert thinking["thinking"] == ""
    assert thinking["signature"]
    assert tool_call["type"] == "tool_use"
    assert tool_result["type"] == "tool_result"


def coordinate(value: float, anchors: list[list[float]]) -> float:
    (pixel_a, metre_a), (pixel_b, metre_b) = anchors
    return metre_a + (value - pixel_a) * (metre_b - metre_a) / (pixel_b - pixel_a)


def test_sm25_anchor_math_matches_documented_six_centimetre_difference() -> None:
    fixture = load(FIXTURES / "sm25_cross_floor_excerpt.json")
    first = fixture["facts"]["f1_saved_drawing_declaration"]
    second = fixture["facts"]["f2_saved_drawing_declaration"]

    first_y = coordinate(first["partition"]["points"][0][1], first["calibration"]["y_anchors"])
    second_y = coordinate(second["partition"]["points"][0][1], second["calibration"]["y_anchors"])
    first_distance = first["calibration"]["north_outer_y_m"] - first_y
    second_distance = second["calibration"]["north_outer_y_m"] - second_y

    assert first["partition"]["id"] == "P_off16"
    assert second["partition"]["id"] == "P_top"
    assert first_distance == pytest.approx(4.00, abs=1e-12)
    assert second_distance == pytest.approx(3.94, abs=1e-6)
    assert first_distance - second_distance == pytest.approx(0.06, abs=1e-6)
    assert {"F1:O2", "F1:O3", "F2:O1"} == set(fixture["facts"]["saved_objects"]) - {"source"}


def test_accepted_core_and_door_exception_are_actual_archived_objects() -> None:
    fixture = load(FIXTURES / "partial_inference_excerpt.json")
    core = fixture["accepted_cross_floor_hall"]["space"]
    exception = fixture["accepted_repeated_with_exception"]["nonpaired_exception"]
    pair = fixture["accepted_repeated_with_exception"]["paired_group"]

    assert core["id"] == "CORE_E"
    assert core["z_floor"] == 0.0
    assert core["height"] == 27.6
    assert core["role"] == "stairwell"
    assert pair["id"] == "PAIR_027"
    assert exception["id"] == "D_F2_W_01_CORE_S"
    assert exception["pair"] is None
    assert exception["paired_space"] is None


def test_sol_bridge_call_and_return_are_exact_archived_records() -> None:
    fixture = load(FIXTURES / "sol_bridge_excerpt.json")
    exact = fixture["exact_bridge_call"]
    request_source, reply_source = exact["sources"]
    calls, replies = load(ROOT / request_source["path"]), load(ROOT / reply_source["path"])
    index = exact["call_index"]
    assert calls[index] == {"tool": exact["tool"], "arguments": exact["arguments"]}
    assert replies[index] == exact["result"]
    assert fixture["receipt"]["provider_actual_model_receipt"] is None
    assert fixture["receipt"]["token_usage"] is None
    assert fixture["receipt"]["billing"] is None


def test_extractor_is_deterministic_and_preserves_historical_sources(tmp_path: Path) -> None:
    before = {entry["path"]: digest(ROOT / entry["path"]) for entry in fixture_sources()}
    environment = os.environ.copy()
    environment["TMPDIR"] = str(tmp_path)
    first = {path.name: path.read_bytes() for path in FIXTURES.glob("*.json")}
    subprocess.run([sys.executable, str(EXTRACTOR)], cwd=ROOT, env=environment, check=True)
    second = {path.name: path.read_bytes() for path in FIXTURES.glob("*.json")}
    subprocess.run([sys.executable, str(EXTRACTOR)], cwd=ROOT, env=environment, check=True)
    third = {path.name: path.read_bytes() for path in FIXTURES.glob("*.json")}
    assert first == second == third
    assert before == {path: digest(ROOT / path) for path in before}
