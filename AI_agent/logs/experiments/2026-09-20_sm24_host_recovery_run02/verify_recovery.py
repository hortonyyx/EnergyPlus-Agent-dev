"""Post-run audit of the saved-plan recovery experiment; no GT is read.

Run only after summary.json exists.  This checks provenance, the first failed
MCP feedback, and the geometry actually used for the delivered candidate.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def same_image(a: Image.Image, b: Image.Image) -> bool:
    return a.size == b.size and ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None


def events(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def stream_builds(path: Path) -> list[dict]:
    uses: list[dict] = []
    results: dict[str, dict] = {}
    for event in events(path):
        content = event.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name", "").endswith("build_plan_bim"):
                uses.append(block)
            elif block.get("type") == "tool_result":
                results[block.get("tool_use_id", "")] = block
    return [{"use": use, "result": results.get(use["id"])} for use in uses]


def compare_items(before: list[dict], after: list[dict], fields: tuple[str, ...]) -> dict:
    old = {x["id"]: x for x in before}
    new = {x["id"]: x for x in after}
    return {
        "added": {key: {f: new[key].get(f) for f in fields} for key in sorted(new.keys() - old.keys())},
        "deleted": {key: {f: old[key].get(f) for f in fields} for key in sorted(old.keys() - new.keys())},
        "modified": {
            key: {f: {"before": old[key].get(f), "after": new[key].get(f)}
                  for f in fields if old[key].get(f) != new[key].get(f)}
            for key in sorted(old.keys() & new.keys())
            if any(old[key].get(f) != new[key].get(f) for f in fields)
        },
    }


def unchanged(diff: dict) -> bool:
    return not any(diff[k] for k in ("added", "deleted", "modified"))


def facade(p: dict, footprint: list[list[float]]) -> str:
    xs = [pt[0] for pt in footprint]
    ys = [pt[1] for pt in footprint]
    a, b = p.get("p1"), p.get("p2")
    if not isinstance(a, list) or not isinstance(b, list):
        return "unclassified"
    if a[0] == b[0] == max(xs):
        return "east"
    if a[0] == b[0] == min(xs):
        return "west"
    if a[1] == b[1] == min(ys):
        return "north"
    if a[1] == b[1] == max(ys):
        return "south"
    return "interior_or_unclassified"


def audit(run: Path) -> dict:
    if not (run / "summary.json").is_file():
        raise RuntimeError("summary.json is absent: wait until generation finishes")
    manifest = read_json(run / "inputs.json")
    summary = read_json(run / "summary.json")
    recovery = manifest["plan_recovery"]
    frozen_raw = (run / recovery["frozen_path"]).read_bytes()
    source = Path(recovery["source_path"])
    source_raw = source.read_bytes() if source.is_file() else None
    original = json.loads(frozen_raw)
    image_name = recovery["image"]
    image_path = run / "images" / image_name
    provenance = {
        "input_mode": manifest.get("input_mode"),
        "source_path": str(source),
        "source_exists": source_raw is not None,
        "frozen_path": recovery["frozen_path"],
        "frozen_sha256": sha(frozen_raw),
        "frozen_matches_manifest_sha": sha(frozen_raw) == recovery["raw_sha256"],
        "frozen_matches_original_bytes": source_raw == frozen_raw if source_raw is not None else None,
        "declaration_matches_frozen": recovery["declaration"] == original,
        "image": image_name,
        "image_matches_manifest_sha": image_path.is_file() and sha(image_path.read_bytes()) == recovery["image_sha256"] == manifest["images"][image_name]["sha256"],
    }
    rows = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    tool_builds = [row for row in rows if row.get("action") == "build_plan_bim"]
    stream_path = next((p for p in (run / "agent_stream.jsonl.gz", run / "agent_stream.jsonl") if p.is_file()), None)
    stream_pairs = stream_builds(stream_path) if stream_path else []
    first: dict = {"available": bool(tool_builds), "checks": {}}
    if tool_builds:
        tool_result = tool_builds[0]["data"]
        plan_input = tool_result.get("plan_input", {})
        first_plan_path = run / plan_input["plan_file"]
        first_plan_raw = first_plan_path.read_bytes()
        saved_result = read_json(first_plan_path.parent / "result.json")
        original_result_path = source.with_name("result.json")
        original_result = read_json(original_result_path) if original_result_path.is_file() else None
        first["checks"].update({
            "first_draft_plan": plan_input["plan_file"],
            "first_draft_structurally_equals_frozen": json.loads(first_plan_raw) == original,
            "first_draft_sha_matches_record": sha(first_plan_raw) == plan_input["plan_sha256"],
            "saved_result_equals_tool_log": saved_result == tool_result,
            "status": tool_result.get("status"),
            "error": tool_result.get("error"),
            "original_error": original_result.get("error") if original_result else None,
            "original_host_error_reproduced": bool(original_result and
                                                   tool_result.get("status") == "error" and
                                                   tool_result.get("error") == original_result.get("error") and
                                                   "full-boundary hosts" in tool_result.get("error", "")),
        })
        if stream_pairs:
            pair = stream_pairs[0]
            use = pair["use"]
            response = pair["result"]
            first["checks"]["mcp_tool_use_id"] = use["id"]
            first["checks"]["mcp_request_plan_structurally_equals_frozen"] = json.loads(use["input"]["plan_json"]) == original
            first["checks"]["mcp_result_linked_by_tool_use_id"] = bool(response and response.get("tool_use_id") == use["id"])
            if response:
                blocks = response.get("content", [])
                image_blocks = [block for block in blocks if block.get("type") == "image"]
                text_blocks = [block for block in blocks if block.get("type") == "text"]
                payload = json.loads(text_blocks[-1]["text"]) if text_blocks else {}
                local = plan_input.get("host_failure_view")
                returned_local = payload.get("plan_input", {}).get("host_failure_view")
                first["checks"].update({
                    "mcp_image_count": len(image_blocks),
                    "mcp_text_error_matches_saved": payload.get("error") == tool_result.get("error"),
                    "mcp_inline_host_metadata": bool(returned_local and returned_local.get("metadata") == local.get("metadata")) if local else False,
                })
                if local:
                    metadata = read_json(run / local["metadata_file"])
                    saved_image = run / local["image_file"]
                    first["checks"].update({
                        "host_metadata_equals_sidecar": local.get("metadata") == metadata,
                        "host_image_sha_matches_record": sha(saved_image.read_bytes()) == local["image_sha256"],
                        "metadata_plan_and_image_sha_match": metadata["plan"]["sha256"] == plan_input["plan_sha256"] and metadata["image"]["sha256"] == recovery["image_sha256"],
                        "full_opening_preserved_in_metadata": metadata["opening"]["full_declared_segment_preserved"] and
                            metadata["opening"]["id"] == local["opening_id"] and
                            metadata["opening"]["p1_original_pixels"] == local["p1_original_pixels"] and
                            metadata["opening"]["p2_original_pixels"] == local["p2_original_pixels"],
                    })
                    with Image.open(saved_image) as image:
                        saved = image.copy()
                    crop = metadata["crop_original_pixels"]
                    panel = metadata["panels"]["clean_original"]
                    with Image.open(image_path) as image:
                        expected = image.convert("RGB").crop(tuple(crop)).resize(
                            (panel[2] - panel[0], panel[3] - panel[1]), Image.Resampling.NEAREST)
                    clean = saved.crop(tuple(panel))
                    first["checks"]["clean_panel_is_original_crop_nearest"] = same_image(clean, expected)
                    local_bytes = saved_image.read_bytes()
                    first["checks"]["mcp_local_image_matches_saved_pixels"] = any(
                        same_image(Image.open(BytesIO(base64.b64decode(block["source"]["data"]))), saved)
                        for block in image_blocks)
                    first["checks"]["mcp_local_image_matches_saved_bytes"] = any(
                        base64.b64decode(block["source"]["data"]) == local_bytes for block in image_blocks)
    delivery = summary.get("delivery") or {}
    candidate = delivery.get("candidate")
    final: dict = {"candidate": candidate, "complete_geometry_check": False}
    if candidate:
        report_path = run / candidate / "report.json"
        if report_path.is_file():
            report = read_json(report_path)
            final_plan_input = report.get("provenance", {}).get("plan_input", {})
            plan_file = final_plan_input.get("plan_file")
            final["plan_file"] = plan_file
            if plan_file and (run / plan_file).is_file():
                final_raw = (run / plan_file).read_bytes()
                revised = json.loads(final_raw)
                scalars = ("floor_id", "z_floor", "ceiling_height", "x_anchors", "y_anchors", "footprint_pixels")
                fixed = {field: original.get(field) == revised.get(field) for field in scalars}
                partitions = compare_items(original.get("partitions", []), revised.get("partitions", []), ("points",))
                seeds = compare_items(original.get("space_seeds", []), revised.get("space_seeds", []), ("point",))
                old_op = {item["id"]: item for item in original.get("openings", [])}
                new_op = {item["id"]: item for item in revised.get("openings", [])}
                all_op = compare_items(list(old_op.values()), list(new_op.values()), ("kind", "p1", "p2", "z"))
                east_ids = {key for key, value in old_op.items() if facade(value, original["footprint_pixels"]) == "east"}
                east_ids |= {key for key, value in new_op.items() if facade(value, revised["footprint_pixels"]) == "east"}
                east = compare_items([v for k, v in old_op.items() if k in east_ids],
                                     [v for k, v in new_op.items() if k in east_ids], ("kind", "p1", "p2", "z"))
                retained = compare_items([v for k, v in old_op.items() if k not in east_ids],
                                         [v for k, v in new_op.items() if k not in east_ids], ("kind", "p1", "p2", "z"))
                final.update({
                    "complete_geometry_check": True,
                    "candidate_plan_sha_matches_report": sha(final_raw) == final_plan_input.get("plan_sha256"),
                    "plan_was_submitted_by_build_plan_bim": any(
                        row["data"].get("candidate") == candidate and row["data"].get("plan_input", {}).get("plan_file") == plan_file
                        for row in tool_builds),
                    "fixed_fields_unchanged": fixed,
                    "interior_partitions": partitions,
                    "space_seeds": seeds,
                    "all_openings": all_op,
                    "east_opening_ids_from_footprint_right_edge": sorted(east_ids),
                    "east_openings": east,
                    "other_openings": retained,
                    "retention_pass": all(fixed.values()) and unchanged(partitions) and unchanged(seeds) and unchanged(retained),
                })
            else:
                final["incomplete_reason"] = "candidate report has no saved plan_input.plan_file"
        else:
            final["incomplete_reason"] = "candidate report.json is absent"
    else:
        final["incomplete_reason"] = "summary has no delivered candidate"
    selected = ("view_image", "view_pixel_profile", "pixel_profile", "map_dimension_chain", "build_plan_bim",
                "overlay_candidate", "view_elevation_candidate", "check_openings", "finish_bim")
    actions = []
    for index, row in enumerate(rows):
        if row.get("action") not in selected:
            continue
        data = row.get("data") or {}
        actions.append({"index": index, "action": row["action"], "image": data.get("name") or data.get("image"),
                        "original_box": data.get("box_original_pixels") or data.get("box"),
                        "candidate": data.get("candidate"), "status": data.get("status"),
                        "error": data.get("error")})
    return {"schema_version": "saved_plan_recovery_audit_v1", "run": str(run),
            "checks_exclude_gt": True, "provenance": provenance, "first_build": first,
            "final_candidate": final, "tool_action_counts": dict(Counter(row.get("action") for row in rows)),
            "observed_actions": actions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--out", type=Path, help="JSON output; defaults to RUN/recovery_verification.json")
    args = parser.parse_args()
    result = audit(args.run.resolve())
    output = args.out or args.run / "recovery_verification.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "first_build": result["first_build"]["checks"],
                      "retention_pass": result["final_candidate"].get("retention_pass"),
                      "east_changes": result["final_candidate"].get("east_openings")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
