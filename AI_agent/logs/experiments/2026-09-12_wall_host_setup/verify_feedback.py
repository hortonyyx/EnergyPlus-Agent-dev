"""Post-generation audit of saved projections and actual model tool responses.

This verifies execution and image provenance, not drawing interpretation.
"""
from __future__ import annotations

import argparse
import base64
import io
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops
from src.agent.geometry.source_image_overlay import render_source_overlay


def read(path):
    return json.loads(path.read_text())


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path)
args = parser.parse_args()
run = args.run.resolve()
assert (run / "summary.json").is_file(), "generation must finish first"
manifest = read(run / "inputs.json")
records = []
for path in sorted((run / "image_overlays").glob("overlay_*.json")):
    meta = read(path)
    source = read(run / meta["candidate"] / "source_model.json")
    original = run / "images" / meta["image"]
    checks = {
        "source_binding": meta["source_model_sha256"] == source["source_model_sha256"],
        "image_binding": hashlib.sha256(original.read_bytes()).hexdigest()
            == meta["image_sha256"] == manifest["images"][meta["image"]]["sha256"],
        "fidelity_not_certified": meta["drawing_fidelity"] == "not_evaluated",
        "calibration_unverified": meta["calibration_unverified"] is True,
    }
    with Image.open(original) as raw:
        expected, expected_meta = render_source_overlay(source, raw, floor_id=meta["floor_id"],
            x_anchors=meta["anchors"]["x"], y_anchors=meta["anchors"]["y"], basis=meta["basis"], image_name=meta["image"])
    checks["wall_evidence_projection_replay"] = expected_meta["wall_evidence_projection"] == meta["wall_evidence_projection"]
    with Image.open(run / meta["overlay_image"]) as actual:
        checks["pixels_match_actual_source_projection"] = expected.size == actual.size and (
            ImageChops.difference(expected.convert("RGB"), actual.convert("RGB")).getbbox() is None)
    reused = meta.get("reused_calibration")
    if reused:
        calibration = read(run / reused["calibration_file"])
        checks["registered_anchors_unchanged"] = all(
            meta["anchors"][axis] == calibration[f"{axis}_anchors"] for axis in ("x", "y"))
        checks["registered_basis_unchanged"] = meta["basis"] == calibration["basis"]
        checks["registered_image_floor_match"] = all(
            meta[key] == calibration[key] for key in ("image", "floor_id", "image_sha256"))
        registration_source = read(run / calibration["registered_by_candidate"] / "source_model.json")
        checks["registration_source_binding"] = (
            registration_source["source_model_sha256"] == calibration["registered_source_model_sha256"])
    records.append({"metadata": str(path.relative_to(run)), "candidate": meta["candidate"],
        "floor_id": meta["floor_id"], "automatic": meta.get("automatic_projection", False),
        "trigger": meta.get("trigger_action"), "checks": checks})

stream_path = run / "agent_stream.jsonl"
opener = open
if not stream_path.is_file():
    stream_path = stream_path.with_suffix(".jsonl.gz")
    opener = gzip.open
calls = {}
responses = []
with opener(stream_path, "rt") as stream:
    for line in stream:
        event = json.loads(line)
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                calls[block["id"]] = block["name"]
            elif block.get("type") == "tool_result":
                tool = calls.get(block["tool_use_id"], "unknown")
                if not tool.endswith(("overlay_candidate", "build_bim", "revise_bim")):
                    continue
                content = block.get("content", [])
                images = sum(item.get("type") == "image" for item in content if isinstance(item, dict))
                text_items = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
                payload = None
                for value in text_items:
                    try:
                        decoded = json.loads(value)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(decoded, dict):
                        payload = decoded
                        break
                image_items = [item for item in content if isinstance(item, dict) and item.get("type") == "image"]
                projections = [] if payload is None else ([payload] if payload.get("mode") == "source_image_overlay" else payload.get("source_image_projections", []))
                image_checks = []
                for item, projection in zip(image_items, projections):
                    with Image.open(run / projection["overlay_image"]) as saved:
                        presented = saved.convert("RGB")
                        if tool.endswith("overlay_candidate"):
                            presented = presented.crop(projection["box_original_pixels"])
                        presented.thumbnail((1600, 1600))
                    actual = Image.open(io.BytesIO(base64.b64decode(item["source"]["data"]))).convert("RGB")
                    image_checks.append(presented.size == actual.size and ImageChops.difference(presented, actual).getbbox() is None)
                responses.append({"tool": tool, "tool_use_id": block["tool_use_id"],
                    "returned_image_count": images, "is_error": block.get("is_error", False),
                    "actual_image_pixels_match": image_checks,
                    "expected_projection_count": len(projections),
                    "image_transport_passed": len(image_items) == len(projections) and all(image_checks)})

all_checks_passed = bool(records) and all(all(row["checks"].values()) for row in records) and all(row["image_transport_passed"] for row in responses)
report = {"mode": "post_generation_execution_audit_not_visual_verdict",
    "all_projection_checks_passed": all_checks_passed,
    "projection_count": len(records), "automatic_projection_count": sum(row["automatic"] for row in records),
    "projections": records, "model_tool_responses": responses,
    "limits": ["Returned image content does not prove it was correctly interpreted.",
               "Matching saved source projection does not independently validate the calibration or BIM."]}
with (run / "feedback_verification.json").open("x") as output:
    output.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
assert all_checks_passed, report
print(json.dumps({key: report[key] for key in (
    "all_projection_checks_passed", "projection_count", "automatic_projection_count", "model_tool_responses")},
    ensure_ascii=False, indent=2))
