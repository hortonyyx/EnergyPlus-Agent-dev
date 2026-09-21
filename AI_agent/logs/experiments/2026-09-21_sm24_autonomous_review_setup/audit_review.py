"""Audit a completed BIM Agent run from saved files; never load GT or call a model.

This records observed tool use, candidate provenance, and literal changes. It does
not decide whether any drawing was read correctly. Output is a new JSON file.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_read(path: Path):
    return read(path) if path.is_file() else None


def fields(before: dict, after: dict, *, omit=()) -> dict:
    return {key: {"before": before.get(key), "after": after.get(key)}
            for key in sorted(before.keys() | after.keys())
            if key not in omit and before.get(key) != after.get(key)}


def item_map(rows: list, *, prefix="") -> dict:
    result = {}
    for item in rows:
        key = prefix + str(item.get("id", "<missing-id>"))
        if key in result:
            raise ValueError(f"duplicate object ID: {key}")
        result[key] = item
    return result


def compare_items(before: dict, after: dict, *, omit=()) -> dict:
    old_ids, new_ids = set(before), set(after)
    changed = {key: fields(before[key], after[key], omit=omit)
               for key in sorted(old_ids & new_ids)}
    return {"before_count": len(before), "after_count": len(after),
            "added": {key: after[key] for key in sorted(new_ids - old_ids)},
            "removed": {key: before[key] for key in sorted(old_ids - new_ids)},
            "changed": {key: value for key, value in changed.items() if value}}


def proposal_items(proposal: dict) -> dict:
    geometry = proposal.get("geometry", {})
    floors = {str(floor.get("id", floor.get("floor_id", index))): floor
              for index, floor in enumerate(geometry.get("floors", []))}
    cells = {}
    for floor_id, floor in floors.items():
        cells.update(item_map(floor.get("cells", []), prefix=floor_id + "/"))
    return {"floors": {key: {k: v for k, v in floor.items() if k != "cells"}
                        for key, floor in floors.items()},
            "cells": cells,
            "windows": item_map(geometry.get("windows", [])),
            "openings": item_map(geometry.get("openings", []))}


def proposal_diff(before: dict, after: dict) -> dict:
    old, new = proposal_items(before), proposal_items(after)
    return {"geometry_header": fields(before.get("geometry", {}), after.get("geometry", {}),
                                      omit=("floors", "windows", "openings", "corrections")),
            "objects": {key: compare_items(old[key], new[key]) for key in old},
            "explanation": fields(before, after, omit=("geometry",)),
            "correction_count": [len(before.get("geometry", {}).get("corrections", [])),
                                 len(after.get("geometry", {}).get("corrections", []))]}


def source_diff(before: dict, after: dict) -> dict:
    collections = ("spaces", "boundaries", "openings", "connections", "floors")
    result = {}
    for name in collections:
        def keyed(source):
            rows = source.get(name, [])
            if name == "connections":
                rows = [dict(item, id=item.get("opening_id", index))
                        for index, item in enumerate(rows)]
            return item_map(rows)
        result[name] = compare_items(keyed(before), keyed(after))
    result["source_geometry_sha256"] = [before.get("source_geometry_sha256"),
                                        after.get("source_geometry_sha256")]
    result["source_model_sha256"] = [before.get("source_model_sha256"),
                                     after.get("source_model_sha256")]
    return result


def stream_records(run: Path) -> list[dict]:
    stream = run / "agent_stream.jsonl"
    if not stream.is_file():
        stream = run / "agent_stream.jsonl.gz"
    if not stream.is_file():
        return []
    opener = gzip.open if stream.suffix == ".gz" else open
    calls, results = [], {}
    with opener(stream, "rt", encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            for block in event.get("message", {}).get("content", []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    calls.append(block)
                elif block.get("type") == "tool_result":
                    results[block.get("tool_use_id")] = block
    records = []
    for call in calls:
        result = results.get(call.get("id"))
        payload = None
        if result:
            for block in reversed(result.get("content", [])):
                if isinstance(block, dict) and block.get("type") == "text":
                    try:
                        parsed = json.loads(block.get("text", ""))
                    except (ValueError, TypeError):
                        continue
                    if isinstance(parsed, dict):
                        payload = parsed
                        break
        records.append({"tool_use_id": call.get("id"),
                        "action": call.get("name", "").rsplit("__", 1)[-1],
                        "input": call.get("input", {}), "response": payload,
                        "result_linked": result is not None,
                        "result_is_error": bool(result.get("is_error") or result.get("isError"))
                            if result else None,
                        "error_text": str(result.get("content", ""))[:1000]
                            if result and (result.get("is_error") or result.get("isError")) else None,
                        "returned_images": sum(isinstance(part, dict) and part.get("type") == "image"
                                               for part in result.get("content", [])) if result else 0})
    return records


def tool_review(run: Path) -> dict:
    records = stream_records(run)
    logged = []
    path = run / "tools.jsonl"
    if path.is_file():
        logged = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    views = []
    original_actions = {"view_image", "pixel_profile", "view_pixel_profile",
                        "view_pixel_region", "view_pixel_region_overview", "view_space_trace",
                        "preview_space_trace"}
    for record in records:
        action = record["action"]
        if action not in original_actions | {"view_candidate", "overlay_candidate",
                                             "view_elevation_candidate", "overlay_mesh_candidate"}:
            continue
        arg, response = record["input"], record["response"] or {}
        # For view_pixel_profile, input.name is a saved profile ID; the result
        # names the original drawing. Prefer the returned drawing identity.
        image = (response.get("image_name") or response.get("image") or
                 response.get("name") or arg.get("image") or arg.get("image_name") or
                 arg.get("name"))
        successful_return = (record["result_linked"] and not record["result_is_error"] and
                             (record["returned_images"] > 0 if action != "pixel_profile"
                              else bool(record["response"])))
        views.append({"action": action, "tool_use_id": record["tool_use_id"],
                      "image": image, "candidate": arg.get("candidate"),
                      "request_name": arg.get("name"),
                      "facade": arg.get("facade"), "floor_id": arg.get("floor_id"),
                      "box_requested": arg.get("box") or arg.get("crop"),
                      "box_original_pixels": response.get("box_original_pixels"),
                      "axis": arg.get("axis"), "at": arg.get("at"),
                      "input": arg if action in {"pixel_profile", "view_pixel_profile"} else None,
                      "result_linked": record["result_linked"],
                      "result_is_error": record["result_is_error"],
                      "error_text": record["error_text"],
                      "successful_return": successful_return,
                      "returned_images": record["returned_images"]})
    by_image = defaultdict(Counter)
    for view in views:
        if view["action"] in original_actions:
            counts = by_image[str(view["image"] or "<unidentified>")]
            counts[view["action"] + "_requested"] += 1
            if view["successful_return"]:
                counts[view["action"] + "_successful"] += 1
    declared = sorted((safe_read(run / "inputs.json") or {}).get("images", {}))
    inspected = {name for name, counts in by_image.items()
                 if name in declared and any(key.endswith("_successful") and value > 0
                                             for key, value in counts.items())}
    events = []
    for record in records:
        if record["action"] in {"build_plan_bim", "build_bim", "build_parametric_bim", "revise_bim", "finish_bim"}:
            arg, response = record["input"], record["response"] or {}
            operations = None
            if record["action"] == "revise_bim":
                try:
                    operations = json.loads(arg.get("operations_json", "null"))
                except (ValueError, TypeError):
                    operations = "unparseable"
            events.append({"action": record["action"], "tool_use_id": record["tool_use_id"],
                           "result_linked": record["result_linked"],
                           "requested_candidate": arg.get("candidate"),
                           "produced_candidate": response.get("candidate"),
                           "source_geometry_ready": response.get("source_geometry_ready"),
                           "status": response.get("status"),
                           "result_is_error": record["result_is_error"],
                           "error_text": record["error_text"],
                           "plan_image": arg.get("image"),
                           "operations": operations,
                           "plan_json_sha256": hashlib.sha256(arg["plan_json"].encode()).hexdigest()
                               if isinstance(arg.get("plan_json"), str) else None})
    return {"stream_tool_count": len(records), "stream_tool_counts": dict(Counter(r["action"] for r in records)),
            "logged_tool_count": len(logged), "logged_tool_counts": dict(Counter(r.get("action") for r in logged)),
            "unlinked_tool_results": [r["tool_use_id"] for r in records if not r["result_linked"]],
            "errored_tool_results": [{"tool_use_id": r["tool_use_id"], "action": r["action"],
                                      "error_text": r["error_text"]}
                                     for r in records if r["result_is_error"]],
            "images_declared": declared, "original_image_actions_by_file":
                {key: dict(value) for key, value in sorted(by_image.items())},
            "images_with_no_successful_original_view_or_measurement": sorted(set(declared) - inspected),
            "views_and_measurements": views, "build_revision_finish_events": events,
            "note": "Image calls and boxes describe exposure, not correct reading. Some tools return generated images."}


def candidate_chain(run: Path, candidate: str, events: list[dict]) -> dict:
    chain, visited = [], set()
    while candidate and candidate not in visited:
        visited.add(candidate)
        folder = run / candidate
        report = safe_read(folder / "report.json")
        if report is None:
            chain.append({"candidate": candidate, "report_missing": True})
            break
        provenance = report.get("provenance", {})
        proposal_path = folder / "proposal.json"
        operations_path = folder / "operations.json"
        parent = provenance.get("parent_candidate")
        if candidate == "seed":
            relevant = []
        elif parent:
            relevant = [event for event in events if event["action"] == "revise_bim"
                        and event["requested_candidate"] == parent
                        and event["produced_candidate"] == candidate]
        else:
            relevant = [event for event in events if event["action"] in
                        {"build_plan_bim", "build_bim", "build_parametric_bim"}
                        and event["produced_candidate"] == candidate]
        saved_operations = safe_read(operations_path)
        chain.append({"candidate": candidate, "mode": provenance.get("mode"),
                      "parent_candidate": parent, "plan_input": provenance.get("plan_input"),
                      "parent_proposal_hash_matches":
                          digest(run / parent / "proposal.json") == provenance.get("parent_proposal_sha256")
                          if parent and (run / parent / "proposal.json").is_file() else None,
                      "plan_hash_matches":
                          digest(run / provenance["plan_input"]["plan_file"]) ==
                          provenance["plan_input"].get("plan_sha256")
                          if provenance.get("plan_input", {}).get("plan_file") and
                          (run / provenance["plan_input"]["plan_file"]).is_file() else None,
                      "proposal_hash_matches_report": proposal_path.is_file() and
                          digest(proposal_path) == report.get("proposal_sha256"),
                      "source_geometry_ready": report.get("source_geometry_ready"),
                      "source_model_sha256": report.get("source_model_sha256"),
                      "operations_file": str(operations_path.relative_to(run))
                          if operations_path.is_file() else None,
                      "operations": saved_operations,
                      "matching_tool_event_ids": [event["tool_use_id"] for event in relevant],
                      "matching_tool_result_present": any(event["result_linked"] for event in relevant),
                      "matching_tool_event_successful": any(
                          event["result_linked"] and not event["result_is_error"] and
                          event["source_geometry_ready"] is True for event in relevant)
                          if candidate != "seed" else None,
                      "revision_request_matches_saved_operations":
                          any(event["operations"] == saved_operations for event in relevant)
                          if parent and saved_operations is not None else None})
        candidate = parent
    return {"steps_final_to_ancestor": chain,
            "cycle_detected": candidate in visited if candidate else False,
            "complete_to_seed_or_build": bool(chain) and not chain[-1].get("report_missing") and
                not (candidate in visited if candidate else False)}


def audit(run: Path, baseline: str | None) -> dict:
    summary = safe_read(run / "summary.json")
    receipt = safe_read(run / "agent_receipt.json")
    if summary is None or receipt is None:
        raise ValueError("run must be complete (summary.json and agent_receipt.json required)")
    candidate = (summary.get("delivery") or {}).get("candidate")
    if baseline is None:
        baseline = "seed" if (run / "seed" / "proposal.json").is_file() else None
    if baseline and ("/" in baseline or "\\" in baseline or baseline in {".", ".."}):
        raise ValueError("baseline must be one local candidate directory name")
    final = run / candidate if candidate else None
    comparisons = {}
    if candidate and baseline:
        final_proposal = read(final / "proposal.json")
        final_source = read(final / "source_model.json")
        base = run / baseline
        comparisons = {"baseline": baseline,
                       "proposal": proposal_diff(read(base / "proposal.json"), final_proposal),
                       "source": source_diff(read(base / "source_model.json"), final_source)}
    resume_plan = safe_read(run / "resume_plan.json")
    if resume_plan is not None:
        plan_inputs = []
        for path in sorted((run / "plan_drafts").glob("draft_*/plan.json")):
            plan_inputs.append({"file": str(path.relative_to(run)), "sha256": digest(path),
                                "difference_from_resume_plan": fields(resume_plan, read(path))})
        comparisons["resume_plan"] = {"sha256": digest(run / "resume_plan.json"),
                                       "drafts": plan_inputs,
                                       "limit": "A pixel plan is not a source BIM; no source object baseline exists unless a seed is saved."}
    tool = tool_review(run)
    events = tool["build_revision_finish_events"]
    selection = safe_read(run / "delivery_selection.json")
    delivery = safe_read(run / "delivery.json")
    final_source = safe_read(final / "source_model.json") if final else None
    selected_sha = final_source.get("source_model_sha256") if final_source else None
    successful_finish = bool(candidate and selected_sha and any(
        event["action"] == "finish_bim" and event["requested_candidate"] == candidate and
        event["produced_candidate"] == candidate and event["result_linked"] and
        not event["result_is_error"] for event in events))
    selection_matches = bool(candidate and selected_sha and selection and
                             selection.get("candidate") == candidate and
                             selection.get("source_model_sha256") == selected_sha)
    delivery_matches = bool(candidate and selected_sha and delivery and
                            delivery.get("candidate") == candidate and
                            delivery.get("source_model_sha256") == selected_sha and
                            delivery.get("viewer_exists") is True)
    return {"schema_version": "autonomous_review_audit_v1", "run": str(run),
            "input_mode": (safe_read(run / "inputs.json") or {}).get("input_mode"),
            "delivered_candidate": candidate, "baseline": baseline,
            "delivery_absent": not bool(candidate),
            "candidate_chain": candidate_chain(run, candidate, events) if candidate else None,
            "finish_event_successful": successful_finish,
            "selection_file_matches_final_source": selection_matches,
            "delivery_file_matches_final_source": delivery_matches,
            "finish_selected_delivery": successful_finish and selection_matches and delivery_matches,
            "tool_review": tool,
            "changes": comparisons,
            "final_counts": (safe_read(final / "report.json") or {}).get("counts") if final else None,
            "unverified_by_this_audit": ["Whether images were interpreted correctly",
                "Whether claimed evidence or measurements really support each explanation",
                "Drawing fidelity, missing rooms or openings, and user acceptance",
                "GT comparison, which must remain post-generation and independent"],
            "evidence_limits": ["Tool calls show requested/returned content, not the model's attention.",
                "A preserved object may still be wrong; a changed object may be right or wrong.",
                "No GT or historical quality report is read by this audit."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--baseline", help="Local candidate folder; defaults to seed if present")
    parser.add_argument("--out", type=Path, help="New JSON path; defaults to RUN/autonomous_review_audit.json")
    args = parser.parse_args()
    run = args.run.resolve()
    result = audit(run, args.baseline)
    out = (args.out or run / "autonomous_review_audit.json").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(out), "candidate": result["delivered_candidate"],
                      "baseline": result["baseline"],
                      "tool_calls": result["tool_review"]["stream_tool_count"],
                      "unviewed_original_images": result["tool_review"]["images_with_no_successful_original_view_or_measurement"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
