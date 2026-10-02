"""Persist the stage-1 offline acceptance run using a scripted model and real MCP."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw
from src.agent.runtime_entry import execute, parser
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts, EventLog


HERE = Path(__file__).resolve().parent


def reply(number, tool=None, arguments=None):
    message = {"role": "assistant", "content": "Offline protocol exercise."}
    if tool:
        message["tool_calls"] = [{"id": f"offline-{number}", "type": "function",
            "function": {"name": tool, "arguments": json.dumps(arguments)}}]
    return {"id": f"scripted-{number}", "model": "scripted-model",
        "choices": [{"index": 0, "message": message,
            "finish_reason": "tool_calls" if tool else "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
        "fixture_notice": "usage is synthetic test data, not provider billing"}


def main():
    out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "offline_run"
    inputs = HERE / "offline_inputs"
    inputs.mkdir(exist_ok=True)
    image = Image.new("RGB", (320, 240), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 300, 220), outline="black", width=3)
    draw.line((160, 20, 160, 100), fill="black", width=3)
    draw.line((160, 145, 160, 220), fill="black", width=3)
    image.save(inputs / "plan.png")
    proposal = {"geometry": {"schema_version": "2", "footprint_x": [0, 6],
        "footprint_y": [0, 4], "floors": [{"name": "F1", "z_floor": 0,
        "ceiling_height": 3, "cells": [
            {"id": "left", "role": "office", "x": [0, 3], "y": [0, 4]},
            {"id": "right", "role": "corridor", "x": [3, 6], "y": [0, 4]}]}],
        "windows": [], "openings": [{"id": "door", "kind": "door", "space_id": "left",
            "other_space_id": "right", "p1": [3, 1], "p2": [3, 2], "z": [0, 2.1],
            "source_refs": ["synthetic-stage1-fixture"]}]},
        "assumptions": ["Offline transport fixture; not an inferred real building."], "unresolved": []}
    script = [reply(1, "view_image", {"name": "plan.png", "coordinate_grid": False}),
        reply(2, "view_image", {"name": "missing.png"}),
        reply(3, "build_bim", {"proposal_json": json.dumps(proposal)}),
        reply(4, "finish_bim", {"candidate": "candidate_01"}), reply(5)]
    script_path = HERE / "offline_responses.json"
    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n")
    args = parser().parse_args(["--provider", "scripted", "--script", str(script_path),
        "--images", str(inputs), "--out", str(out), "--model-calls", "5",
        "--tool-calls", "4", "--seconds", "180", "--tokens", "15000000",
        "--scope", "Offline two-room transport fixture; exercise image, error, write and finish using frozen tools."])
    result = asyncio.run(execute(args))
    if result["status"] != "completed":
        raise RuntimeError(f"offline run stopped: {result['status']}")
    metadata = json.loads((out / "journal.json").read_bytes())
    events = EventStore.read_events(out / "events.jsonl")
    EventLog(mode="complete", events=tuple(events), budget_limit=BudgetAmounts.model_validate_json(json.dumps(metadata["budget_limit"])))
    tool_events = [e for e in events if e.payload.event_type == "tool_execution"]
    assert any(e.payload.outcome == "failed" for e in tool_events)
    assert any(e.payload.applied_write_id for e in tool_events)
    assert any(e.payload.event_type == "tool_presentation" for e in events)
    candidate = out / "bim/candidate_01"
    source = json.loads((candidate / "source_model.json").read_bytes())
    assert len(source["spaces"]) == 2 and len(source["openings"]) == 1
    assert (candidate / "viewer.html").is_file()
    checks = {"status": "passed", "events": len(events), "model_calls": result["model_calls"],
        "tool_calls": result["tool_calls"], "real_model_calls": 0,
        "source_spaces": len(source["spaces"]), "source_openings": len(source["openings"]),
        "viewer": str((candidate / "viewer.html").relative_to(HERE)),
        "usage_notice": "all model usage in this run is fixture data"}
    (out / "verification.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    main()
