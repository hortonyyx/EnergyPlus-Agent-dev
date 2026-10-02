#!/usr/bin/env python3
"""Extract small, hash-addressable Stage 0 evidence fixtures without mutating history.

Run from any directory: ``python AI_agent/logs/experiments/2026-10-02_harness_stage0/extract_sources.py``.
It reads only archived files under ``AI_agent/logs`` and writes only
``tests/fixtures/harness_stage0/sources``.  The excerpts deliberately retain
the historical IDs instead of assigning fixture-specific ones.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "AI_agent").is_dir() or not (ROOT / "tests").is_dir():
    if ROOT.parent == ROOT:
        raise RuntimeError("repository root not found")
    ROOT = ROOT.parent
OUT = ROOT / "tests" / "fixtures" / "harness_stage0" / "sources"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def source(path: Path, selector: str, *, line: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "path": rel(path),
        "sha256": sha256(path),
        "selector": selector,
    }
    if line is not None:
        value["line"] = line
    return value


def write(name: str, data: dict[str, Any]) -> None:
    target = OUT / name
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact(value: Any, limit: int = 1400) -> Any:
    """Keep an actual source value small while recording its full source hash."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…[truncated in fixture]"


def extract_sm25() -> None:
    worklog = ROOT / "AI_agent/logs/worklog/2026-10-02_reconstruction_discussion.md"
    f1 = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25/dev_inputs/plan_f1.json"
    f2 = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25/dev_inputs/plan_f2.json"
    v1 = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25/image_views/view_0001.json"
    v2 = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25/image_views/view_0002.json"
    images = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25/images"
    saved = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25/candidate_04/source_model.json"
    p1, p2, view1, view2, saved_data = read_json(f1), read_json(f2), read_json(v1), read_json(v2), read_json(saved)
    # These are the actual divider and corresponding upper room edge.  P_MRe/P_AB
    # are unrelated to the documented six-centimetre strip.
    part1 = next(item for item in p1["partitions"] if item["id"] == "P_off16")
    part2 = next(item for item in p2["partitions"] if item["id"] == "P_top")
    o2 = next(item for item in saved_data["spaces"] if item["id"] == "F1:O2")
    o3 = next(item for item in saved_data["spaces"] if item["id"] == "F1:O3")
    upper = next(item for item in saved_data["spaces"] if item["id"] == "F2:O1")
    write(
        "sm25_cross_floor_excerpt.json",
        {
            "case": "sm25",
            "historical_identity": "2026-10-01_opus_dev_sm25",
            "facts": {
                "cross_floor_strip": {
                    "statement": "F1 O2/O3 divider is 4.00 m from the north outer face; the corresponding F2 wall is 3.94 m. The documented contact strip is 0.06 m × 3.94 m = 0.2364 m² and the documented regularization target is 3.94 m.",
                    "source": source(worklog, "markdown:24", line=24),
                },
                "f1_saved_drawing_declaration": {
                    "floor_id": p1["floor_id"],
                    "partition": part1,
                    "calibration": {"y_anchors": p1["y_anchors"], "north_outer_y_m": 20.0, "divider_y_m": 16.0, "distance_from_north_m": 4.0},
                    "source": source(f1, "/partitions[id=P_off16]", line=1),
                },
                "f2_saved_drawing_declaration": {
                    "floor_id": p2["floor_id"],
                    "partition": part2,
                    "calibration": {"y_anchors": p2["y_anchors"], "north_outer_y_m": 20.0, "divider_y_m": 16.06, "distance_from_north_m": 3.94},
                    "source": source(f2, "/partitions[id=P_top]", line=1),
                },
                "saved_objects": {
                    "F1:O2": o2,
                    "F1:O3": o3,
                    "F2:O1": upper,
                    "source": source(saved, "/spaces[id=F1:O2],/spaces[id=F1:O3],/spaces[id=F2:O1]", line=1),
                },
            },
            "raw_drawing_views": [
                {
                    "view_id": view1["view_id"],
                    "name": view1["name"],
                    "raw_image_sha256": view1["image_sha256"],
                    "raw_file_sha256": sha256(images / view1["name"]),
                    "returned_png_sha256": view1["returned_png_sha256"],
                    "source": source(v1, "/", line=1),
                },
                {
                    "view_id": view2["view_id"],
                    "name": view2["name"],
                    "raw_image_sha256": view2["image_sha256"],
                    "raw_file_sha256": sha256(images / view2["name"]),
                    "returned_png_sha256": view2["returned_png_sha256"],
                    "source": source(v2, "/", line=1),
                },
            ],
            "missing": [
                "No historical record expresses the 4.00 m and 3.94 m as record_claim IDs; the dimension conclusion is the documented worklog finding and the saved drawing declarations above.",
                "The original drawings are raster images; their dimension glyphs do not have JSON selectors beyond the view records and raw-image hashes.",
            ],
        },
    )


def extract_partial_inference() -> None:
    accepted = ROOT / "AI_agent/logs/experiments/2026-10-01_voimatalo_door_revision/acceptance.json"
    doors = ROOT / "AI_agent/logs/experiments/2026-10-01_voimatalo_door_revision/door_layout.json"
    model = ROOT / "AI_agent/logs/experiments/2026-10-01_voimatalo_door_revision/candidate_02/source_model.json"
    comparison = ROOT / "AI_agent/logs/experiments/2026-10-01_partial_inference_developer_tests/comparison.json"
    review61 = ROOT / "AI_agent/logs/experiments/2026-10-01_partial_inference_framework_setup/evaluation/review_61sol.md"
    review6 = ROOT / "AI_agent/logs/experiments/2026-10-01_partial_inference_framework_setup/evaluation/review_6sol.md"
    accepted_data, door_data, model_data, comparison_data = read_json(accepted), read_json(doors), read_json(model), read_json(comparison)
    continuous_core = next(item for item in model_data["spaces"] if item["id"] == "CORE_E")
    nonpaired_door = next(item for item in door_data["changed_doors"] if item["id"] == "D_F2_W_01_CORE_S")
    pair = next(item for item in door_data["paired_groups"] if item["id"] == "PAIR_027")
    write(
        "partial_inference_excerpt.json",
        {
            "case": accepted_data["case"],
            "accepted_revision": accepted_data["revision"],
            "accepted_source_model_sha256": accepted_data["source_model_sha256"],
            "acceptance": {
                "status": accepted_data["status"],
                "user_statement": accepted_data["user_statement"],
                "counts": accepted_data["counts"],
                "source": source(accepted, "/status,/user_statement,/counts,/source_model_sha256", line=1),
            },
            "accepted_repeated_with_exception": {
                "paired_group": pair,
                "nonpaired_exception": {key: nonpaired_door[key] for key in ("id", "room", "floor", "pair", "paired_space", "partition_at", "offset_from_partition_line_m", "width_m")},
                "source": source(doors, "/paired_groups[id=PAIR_027],/changed_doors[id=D_F2_W_01_CORE_S]", line=1),
            },
            "accepted_cross_floor_hall": {
                "space": continuous_core,
                "evidence": "CORE_E is one accepted source-space object from z=0.0 with height 27.6; it is a real continuous cross-floor object, not two halls inferred to be continuous.",
                "source": source(model, "/spaces[id=CORE_E]", line=1),
            },
            "sol_runs": comparison_data["models"],
            "fine_detail_miss": {
                "six_one_sol": "66 office/enclosed spaces include no one-window office; 49 have two windows. F2-F7 basically repeat one plan.",
                "six_sol": "Of 184 ordinary room doors, 176 are exactly at 0.50 of their host-side wall; the review identifies this as a systematic midpoint pattern.",
                "sources": [
                    source(review61, "markdown:27-34", line=27),
                    source(review6, "markdown:45-49", line=45),
                    source(comparison, "/models/0,/models/1", line=1),
                ],
            },
            "missing": [
                "The accepted revision is a user-approved inferred BIM; it does not contain a historical work-model run receipt.",
                "door_layout.json preserves pair IDs and non-paired changed doors but does not name a general template ID for the standard floor.",
            ],
        },
    )


def extract_claude_run99() -> None:
    run = ROOT / "AI_agent/logs/experiments/2026-09-30_sm21_instruction_fix_run99"
    request_path = run / "agent_request.json"
    receipt_path = run / "agent_receipt.json"
    stream_path = run / "agent_stream.jsonl.gz"
    request, receipt = read_json(request_path), read_json(receipt_path)
    with gzip.open(stream_path, "rt", encoding="utf-8") as source_file:
        events = [json.loads(line) for line in source_file]
    thinking = next(event for event in events if event["type"] == "assistant" and any(block["type"] == "thinking" for block in event["message"]["content"]))
    visible = next(event for event in events if event["type"] == "assistant" and any(block["type"] == "text" for block in event["message"]["content"]))
    tool_call = next(event for event in events if event["type"] == "assistant" and any(block["type"] == "tool_use" for block in event["message"]["content"]))
    tool_id = next(block["id"] for block in tool_call["message"]["content"] if block["type"] == "tool_use")
    tool_result = next(event for event in events if event["type"] == "user" and event["message"]["content"][0].get("tool_use_id") == tool_id)
    thinking_block = next(block for block in thinking["message"]["content"] if block["type"] == "thinking")
    visible_block = next(block for block in visible["message"]["content"] if block["type"] == "text")
    call_block = next(block for block in tool_call["message"]["content"] if block["type"] == "tool_use")
    write(
        "claude_run99_excerpt.json",
        {
            "historical_run": "run99",
            "request": {
                "requested_model": request["requested_model"],
                "provider": request["provider"],
                "effort": request["effort"],
                "prompt_excerpt": compact(request["prompt"]),
                "system_prompt_excerpt": compact(request["system_prompt"]),
                "source": source(request_path, "/requested_model,/provider,/effort,/prompt,/system_prompt", line=1),
            },
            "stream": {
                "thinking_message": {"message": thinking["message"], "event_uuid": thinking["uuid"], "line": events.index(thinking) + 1},
                "visible_text_message": {"message": visible["message"], "event_uuid": visible["uuid"], "line": events.index(visible) + 1},
                "tool_call_message": {"message": tool_call["message"], "event_uuid": tool_call["uuid"], "line": events.index(tool_call) + 1},
                "tool_result_message": {"message": tool_result["message"], "event_uuid": tool_result["uuid"], "line": events.index(tool_result) + 1},
                "source": source(stream_path, "JSONL event UUIDs above; line numbers are decompressed JSONL", line=events.index(thinking) + 1),
            },
            "receipt": {
                "actual_model": receipt["actual_model"],
                "elapsed_seconds": receipt["elapsed_seconds"],
                "stop_reason": receipt["result"]["stop_reason"],
                "usage": receipt["result"]["usage"],
                "source": source(receipt_path, "/actual_model,/elapsed_seconds,/result/stop_reason,/result/usage", line=1),
            },
            "missing": [
                "The stream exposes a non-empty thinking signature but public thinking content is an empty string; the signature is not treated as thought text.",
                "No independent wire-level final provider request body is archived; agent_request.json is the recorded launcher request.",
                "The stream tool_result is the CLI-visible transformed return, not an independently archived raw MCP/network response.",
            ],
        },
    )


def extract_sol_bridge() -> None:
    run = ROOT / "AI_agent/logs/experiments/2026-10-01_partial_inference_developer_tests/run_61sol"
    request_path = run / "controller_request.json"
    receipt_path = run / "controller_receipt.json"
    bridge = run / "bridge/ed694e699b86430e83618f26ce1d79ee"
    requests_path, replies_path = bridge / "requests.json", bridge / "replies.json"
    request, receipt, calls, replies = map(read_json, (request_path, receipt_path, requests_path, replies_path))
    index = next(index for index, call in enumerate(calls) if call["tool"] == "record_inference")
    # Bridge reply archives are a bare ordered list; their order matches requests.
    reply = replies[index]
    write(
        "sol_bridge_excerpt.json",
        {
            "run": "run_61sol",
            "dispatch": {
                "requested_model": request["requested_model"],
                "reasoning_effort": request["reasoning_effort"],
                "channel": request["channel"],
                "source": source(request_path, "/requested_model,/reasoning_effort,/channel", line=1),
            },
            "exact_bridge_call": {
                "bridge_record_id": bridge.name,
                "call_index": index,
                "tool": calls[index]["tool"],
                "arguments": calls[index]["arguments"],
                "result": reply,
                "sources": [source(requests_path, f"/{index}", line=1), source(replies_path, f"/replies/{index}", line=1)],
            },
            "receipt": {
                "status": receipt["status"],
                "selected_candidate": receipt["selected_candidate"],
                "provider_actual_model_receipt": receipt["provider_actual_model_receipt"],
                "token_usage": receipt["token_usage"],
                "billing": receipt["billing"],
                "receipt_limit": receipt["receipt_limit"],
                "source": source(receipt_path, "/", line=1),
            },
            "missing": [
                "The collaboration interface did not expose a provider actual-model receipt, token usage, or billing receipt; all are null in controller_receipt.json.",
                "The archived bridge preserves tool arguments and the bridge return, but not the development model's prompt/messages or hidden reasoning.",
            ],
        },
    )


def extract_photo_surrogate() -> None:
    image = ROOT / "AI_agent/logs/experiments/2026-10-01_partial_inference_developer_tests/run_61sol/images/parent_detail_front.png"
    write(
        "photo_surrogate_excerpt.json",
        {
            "substitute": True,
            "label": "Historical textured/scanned render; not a real building photo and not evidence for an actual site.",
            "image": {"path": rel(image), "sha256": sha256(image), "bytes": image.stat().st_size},
            "directly_observable": [
                "A vertically cropped tower-like fragment is visible, with a pale main face and a green-tinted upper section.",
                "Along the left edge, about seven separated dark rectangular bands can be distinguished; distortion and crop prevent treating them as building openings.",
                "The textured mesh is visibly fragmented and warped, so floor count and elevations cannot be read reliably.",
            ],
            "use": "A fully inferred sample may use this only to exercise sparse image-observation and byte-hash fields until a user supplies an approved real-photo case.",
            "missing": ["No real-photo full-inference fixture was found in the archived Stage 0 sources."],
        },
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    extract_sm25()
    extract_partial_inference()
    extract_claude_run99()
    extract_sol_bridge()
    extract_photo_surrogate()


if __name__ == "__main__":
    main()
