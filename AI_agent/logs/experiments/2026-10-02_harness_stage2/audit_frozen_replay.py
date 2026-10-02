"""Independently check state survival against real tool events and file hashes."""

from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
import sys

from PIL import Image

from src.agent.runtime_tools import _result_metadata
from src.agent_runtime.store import json_bytes
from src.harness_contracts import EventEnvelope


ROOT = Path(__file__).resolve().parents[4]
STATE_PREFIX = "Current runtime state (machine generated; epistemic status is authoritative): "


def sha(data):
    return hashlib.sha256(data).hexdigest()


def changed_fields(before, after, prefix=""):
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        return [row for key in sorted(before.keys() | after.keys())
                for row in changed_fields(before.get(key), after.get(key), prefix + "/" + key)]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [row for index, (left, right) in enumerate(zip(before, after, strict=True))
                for row in changed_fields(left, right, prefix + "/" + str(index))]
    return [{"path": prefix, "historical_value_sha256": sha(json_bytes(before)),
             "actual_value_sha256": sha(json_bytes(after))}]


def difference_reason(step, path):
    if step == 1:
        return "fresh_runtime_input_manifest_not_historical_runner_configuration"
    if path.endswith("/remaining_seconds"):
        return "historical_tool_deadline_removed_runtime_owns_deadline"
    if path.endswith(("/view_record_sha256", "/view_sha256")):
        return "view_record_hash_changes_with_remaining_seconds"
    if path.endswith("source_model_sha256"):
        return "fresh_provenance_and_current_frozen_public_names_change_source_hash"
    if "/provenance/" in path:
        return "fresh_runtime_input_provenance"
    if path.startswith("/resolved_operations/") and "/source_refs/" in path:
        return "claim_hash_includes_changed_view_record_hash"
    if path.startswith("/claim_application/"):
        return "application_records_reference_current_claims_and_provenance"
    return "unclassified"


def audit_frozen_replay(files):
    # Reuse only the byte-exact historical input loader, never the simulated backend.
    tests = str(ROOT / "tests")
    if tests not in sys.path:
        sys.path.insert(0, tests)
    from test_runtime_long_task import Run99Sequence

    sequence = Run99Sequence()
    report = json.loads(files["frozen_replay_report.json"])
    limits = report["limits"]
    events = [EventEnvelope.model_validate_json(line) for line in files["events.jsonl"].splitlines()]
    reservations = {}
    expected_views = set()
    persisted = {}
    tool_count = 0
    requests, differences, checkpoints = [], [], []

    def blob(ref):
        if not isinstance(ref, dict):
            ref = ref.model_dump(mode="json")
        raw = files[ref["uri"]]
        assert sha(raw) == ref["sha256"]
        return raw

    def captured(value):
        return value.value if value.kind == "inline" else json.loads(blob(value.blob))

    for event in events:
        payload = event.payload
        if payload.event_type == "budget" and payload.action == "reserve":
            reservations[payload.reservation.reservation_id] = payload.reservation
        elif payload.event_type == "checkpoint":
            checkpoints.append(json.loads(blob(payload.state)))
        elif payload.event_type == "tool_execution":
            historical = sequence.steps[tool_count]
            tool_count += 1
            assert payload.tool_name == historical["tool_name"]
            assert payload.full_arguments == historical["arguments"]
            raw = captured(payload.raw_result)
            actual = _result_metadata(raw)
            old = _result_metadata(historical["raw_result"])
            assert bool(raw.get("isError")) == historical["is_error"]
            for view in [actual, *actual.get("evidence_previews", [])]:
                if view.get("view_id"):
                    expected_views.add(view["view_id"])
            persisted = json.loads(blob(event.source_refs[0].blob))["files"]
            fields = changed_fields(old, actual)
            for field in fields:
                field["reason"] = difference_reason(tool_count, field["path"])
                assert field["reason"] != "unclassified", (tool_count, field)
            text = "\n".join(item["text"] for item in raw["content"] if item.get("type") == "text")
            call = report["calls"][tool_count - 1]
            assert call["raw_result"]["sha256"] == payload.raw_result.blob.sha256
            returned_images = [base64.b64decode(block["data"], validate=True)
                               for block in raw["content"] if block.get("type") == "image"]
            assert call["images"] == [{"sha256": sha(data), "bytes": len(data)} for data in returned_images]
            assert call["historical_images"] == [
                {"sha256": image["sha256"], "bytes": image["byte_size"]}
                for image in historical["result"]["images"]]
            differences.append({"step": tool_count, "tool": payload.tool_name,
                "executed_with_unchanged_arguments": True,
                "historical_and_actual_error": bool(raw.get("isError")),
                "actual_error_text": text if raw.get("isError") else None,
                "metadata_differences": fields,
                "image_bytes_equal_to_history": call["images"] == call["historical_images"]})
        elif payload.event_type == "adapter_request":
            wire = blob(payload.final_request_body.blob)
            body = json.loads(wire)
            state_messages = [json.loads(m["content"][len(STATE_PREFIX):]) for m in body["messages"]
                if isinstance(m.get("content"), str) and m["content"].startswith(STATE_PREFIX)]
            assert len(state_messages) == 1
            entries = state_messages[0]
            state = {entry["key"]: entry for entry in entries}
            assert state == {entry["key"]: entry for entry in checkpoints[-1]["context"]["state"]
                             if entry["active"]}
            assert checkpoints[-1]["config"]["limits"] == limits
            actual_views = {entry["value"]["view_id"] for key, entry in state.items()
                            if key.startswith("view:")}
            assert actual_views == expected_views
            for view_id in expected_views:
                entry = state["view:" + view_id]
                assert blob(entry["value"]["record"]) == files[f"bim/image_views/{view_id}.json"]
            claim_paths = sorted(path for path in persisted if path.startswith("claims/claim_")
                                 and path.endswith(".json"))
            assert {key.removeprefix("claims:") for key in state if key.startswith("claims:")} == {
                Path(path).stem for path in claim_paths}
            for path in claim_paths:
                entry = state["claims:" + Path(path).stem]
                assert entry["epistemic_status"] == "inferred"
                assert entry["value"]["record"]["sha256"] == persisted[path]
                claim = json.loads(blob(entry["value"]["record"]))
                assert all(source["view_id"] in expected_views for source in claim["sources"])
            candidate_paths = sorted(path for path in persisted
                if path.startswith("candidate_") and path.endswith("/source_model.json"))
            if candidate_paths:
                path = candidate_paths[-1]
                current = state["current-source-bim"]["value"]
                assert current["candidate"] == path.split("/")[0]
                assert current["file"]["sha256"] == persisted[path]
                source = json.loads(blob(current["file"]))
                assert current["source_model_sha256"] == source["source_model_sha256"]
                assert current["source_geometry_sha256"] == source["source_geometry_sha256"]
                for key in ("source-bim-geometry", "source-bim-dimensions"):
                    assert state[key]["value"]["file"] == current["file"]
                assert state["source-bim-objects"]["value"] == {
                    name: [obj["id"] for obj in source[name]] for name in ("spaces", "boundaries", "openings")}
                unresolved = state["source-bim-unresolved"]
                report_ref = next(ref for ref in unresolved["source_refs"]
                                  if ref["locator"] == path.replace("source_model.json", "report.json"))
                assert report_ref["blob"]["sha256"] == persisted[report_ref["locator"]]
                assert unresolved["value"]["report_unresolved"] == json.loads(blob(report_ref["blob"]))["unresolved"]
                assert state["source-bim-todo"]["value"]["unresolved"] == unresolved["value"]
            else:
                assert "current-source-bim" not in state
            pixels = 0
            for image in payload.images:
                with Image.open(io.BytesIO(blob(image.sent))) as decoded:
                    pixels += decoded.width * decoded.height
            estimated = len(wire) + pixels + body["max_tokens"]
            assert estimated == reservations[payload.reservation_id].amounts.tokens
            assert estimated <= limits["context_tokens"]
            assert len(requests) < limits["model_calls"]
            row = report["steps"][tool_count]
            assert row["state_bytes"] == len(json_bytes(entries))
            if tool_count in (20, 40, 75):
                snapshot = json.loads(files[f"state_step_{tool_count:02d}.json"])
                assert {e["key"]: e for group in snapshot["categories"].values() for e in group} == state
                assert blob(row["checklist"]) == json_bytes(snapshot)
            requests.append({"after_step": tool_count, "state_bytes": len(json_bytes(entries)),
                "request_bytes": len(wire), "estimated_tokens": estimated,
                "context_limit": limits["context_tokens"], "within_budget": True,
                "images": [image.sent.sha256 for image in payload.images]})
    assert tool_count == 75 and len(requests) == 76
    assert len(expected_views) == 26
    for item in report["retrievals"]:
        assert item["sha256"] in requests[item["after_step"]]["images"]
        assert any(e.payload.event_type == "context" and e.payload.action == "retrieve_image"
                   and e.payload.view_id == item["view_id"] and e.payload.image.sha256 == item["sha256"]
                   for e in events)
    for number in range(1, 6):
        relative = f"candidate_{number:02d}/source_model.json"
        saved = json.loads(files["bim/" + relative])
        historical = json.loads((ROOT / report["source"]["path"] / relative).read_bytes())
        assert saved["source_geometry_sha256"] == historical["source_geometry_sha256"]
    assert all(row["image_bytes_equal_to_history"] for row in differences)
    return {"tool_calls": tool_count, "requests": requests, "differences": differences,
        "all_saved_views_indexed": len(expected_views), "all_claims_indexed": len(claim_paths),
        "state_samples": [report["steps"][step] for step in (20, 40, 75)],
        "candidate_updates": [row for index, row in enumerate(report["steps"])
            if row["current_source_bim"] and row["current_source_bim"] != report["steps"][index - 1]["current_source_bim"]],
        "retrievals": report["retrievals"],
        "not_executable_historical_calls": [],
        "historical_errors_reproduced": [row["step"] for row in differences if row["historical_and_actual_error"]],
        "all_5_candidate_geometry_hashes_match_history": True,
        "budget_note": "All configured local limits checked; 20 tokens/response is synthetic. "
            "No service tokenizer, context limit, price or bill is claimed."}
