"""Post-generation scope audit for the southeast partition recovery (no GT)."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def item_diff(old: list[dict], new: list[dict], fields: tuple[str, ...]) -> dict:
    before = {item["id"]: item for item in old}
    after = {item["id"]: item for item in new}
    return {
        "added": {key: {field: after[key].get(field) for field in fields}
                  for key in sorted(after.keys() - before.keys())},
        "deleted": {key: {field: before[key].get(field) for field in fields}
                    for key in sorted(before.keys() - after.keys())},
        "modified": {
            key: {field: {"before": before[key].get(field), "after": after[key].get(field)}
                  for field in fields if before[key].get(field) != after[key].get(field)}
            for key in sorted(before.keys() & after.keys())
            if any(before[key].get(field) != after[key].get(field) for field in fields)
        },
    }


def no_change(diff: dict) -> bool:
    return not any(diff[key] for key in ("added", "deleted", "modified"))


def find_prior_candidate(source_plan: Path) -> tuple[Path | None, str | None]:
    for ancestor in source_plan.parents:
        if not (ancestor / "inputs.json").is_file():
            continue
        try:
            relative = str(source_plan.relative_to(ancestor))
        except ValueError:
            continue
        original_sha = sha(source_plan.read_bytes())
        for report_path in sorted(ancestor.glob("candidate_*/report.json")):
            associated = load(report_path).get("provenance", {}).get("plan_input", {})
            if associated.get("plan_file") == relative and associated.get("plan_sha256") == original_sha:
                return report_path.parent / "source_model.json", report_path.parent.name
        break
    return None, None


def build_stream_pairs(path: Path | None) -> list[dict]:
    if path is None:
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    uses, results = [], {}
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
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
    rows = []
    for use in uses:
        response = results.get(use["id"])
        texts = [part.get("text") for part in response.get("content", []) if part.get("type") == "text"] if response else []
        parsed = None
        if texts:
            try:
                parsed = json.loads(texts[-1])
            except json.JSONDecodeError:
                pass
        rows.append({"id": use["id"], "request": use.get("input", {}),
                     "result_linked": bool(response and response.get("tool_use_id") == use["id"]),
                     "response": parsed})
    return rows


def source_audit(old: dict, new: dict, merged_id: str, area_tol: float) -> dict:
    floor_fields = ("id", "z_floor", "height", "footprint")
    old_floors = [{field: floor.get(field) for field in floor_fields} for floor in old.get("floors", [])]
    new_floors = [{field: floor.get(field) for field in floor_fields} for floor in new.get("floors", [])]
    old_open = {item["id"]: item for item in old.get("openings", [])}
    new_open = {item["id"]: item for item in new.get("openings", [])}
    missing_old = sorted(old_open.keys() - new_open.keys())
    changed_old = {
        key: {field: {"before": old_open[key].get(field), "after": new_open[key].get(field)}
              for field in ("kind", "vertices") if old_open[key].get(field) != new_open[key].get(field)}
        for key in sorted(old_open.keys() & new_open.keys())
        if old_open[key].get("kind") != new_open[key].get("kind") or
           old_open[key].get("vertices") != new_open[key].get("vertices")
    }
    old_spaces = {item["id"]: item for item in old.get("spaces", [])}
    new_spaces = {item["id"]: item for item in new.get("spaces", [])}
    unrelated = {}
    for key, space in sorted(old_spaces.items()):
        if key == merged_id:
            continue
        current = new_spaces.get(key)
        overlap_error = (Polygon(space["polygon"]).symmetric_difference(Polygon(current["polygon"])).area
                         if current else None)
        unrelated[key] = {"present": current is not None,
                          "polygon_symmetric_difference_m2": overlap_error,
                          "role_preserved": current is not None and current.get("role") == space.get("role"),
                          "preserved": current is not None and overlap_error <= area_tol and
                                       current.get("role") == space.get("role")}
    merged = old_spaces.get(merged_id)
    coverage: dict = {"old_space_id": merged_id, "old_space_exists": merged is not None}
    if merged:
        old_poly = Polygon(merged["polygon"])
        contributing = []
        pieces = []
        for key, space in sorted(new_spaces.items()):
            current = Polygon(space["polygon"])
            overlap = current.intersection(old_poly)
            if overlap.area > area_tol:
                contributing.append({"id": key, "role": space.get("role"),
                                     "overlap_m2": overlap.area,
                                     "outside_old_merged_m2": current.difference(old_poly).area})
                pieces.append(overlap)
        covered = unary_union(pieces) if pieces else Polygon()
        coverage.update({"old_area_m2": old_poly.area, "new_spaces_covering_old": contributing,
                         "uncovered_m2": old_poly.difference(covered).area,
                         "overlap_sum_minus_union_m2": sum(piece.area for piece in pieces) - covered.area,
                         "coverage_preserved": old_poly.symmetric_difference(covered).area <= area_tol,
                         "split_into_multiple_spaces": len(contributing) >= 2})
    def links(model: dict) -> dict:
        return {entry["opening_id"]: {"kind": entry.get("kind"), "exterior": entry.get("exterior"),
                                       "space_ids": entry.get("space_ids"), "state": entry.get("state")}
                for entry in model.get("connections", []) if entry.get("kind") == "door"}
    before_links, after_links = links(old), links(new)
    door_links = {
        key: {"before": before_links.get(key), "after": after_links.get(key)}
        for key in sorted(before_links.keys() | after_links.keys())
    }
    new_interior_doors = {
        key: {"endpoints_xyz": new_open[key].get("vertices", [])[:2],
              "vertices": new_open[key].get("vertices"), "space_ids": new_open[key].get("space_ids"),
              "connection": after_links.get(key)}
        for key in sorted(new_open.keys() - old_open.keys())
        if new_open[key].get("kind") == "door" and not new_open[key].get("exterior")
    }
    return {"old_floor_geometry": old_floors, "new_floor_geometry": new_floors,
            "floor_geometry_preserved": old_floors == new_floors,
            "old_opening_count": len(old_open), "new_opening_count": len(new_open),
            "old_openings_missing": missing_old, "old_opening_kind_or_vertices_changed": changed_old,
            "all_old_opening_kind_and_vertices_preserved": not missing_old and not changed_old,
            "new_opening_ids": sorted(new_open.keys() - old_open.keys()),
            "unrelated_spaces": unrelated,
            "all_unrelated_spaces_preserved": all(row["preserved"] for row in unrelated.values()),
            "old_merged_space_coverage": coverage,
            "door_connections_before_after": door_links, "new_interior_doors": new_interior_doors}


def audit(run: Path, merged_id: str, area_tol: float) -> dict:
    if not (run / "summary.json").is_file():
        raise RuntimeError("summary.json absent; generation must finish before this audit reads the run")
    manifest_raw = (run / "inputs.json").read_bytes()
    manifest = json.loads(manifest_raw)
    summary = load(run / "summary.json")
    recovery = manifest.get("plan_recovery", {})
    frozen = run / recovery.get("frozen_path", "resume_plan.json")
    source_path = Path(recovery["source_path"]) if recovery.get("source_path") else None
    source_raw = source_path.read_bytes() if source_path and source_path.is_file() else None
    frozen_raw = frozen.read_bytes() if frozen.is_file() else None
    old_plan = json.loads(frozen_raw) if frozen_raw else None
    image = recovery.get("image")
    image_path = run / "images" / image if image else None
    provenance = {
        "input_mode": manifest.get("input_mode"), "source_path": str(source_path) if source_path else None,
        "source_exists": source_raw is not None, "frozen_path": str(frozen.relative_to(run)),
        "frozen_exists": frozen_raw is not None,
        "frozen_equals_source_bytes": frozen_raw == source_raw if source_raw is not None else None,
        "frozen_sha_matches_manifest": sha(frozen_raw) == recovery.get("raw_sha256") if frozen_raw else False,
        "declaration_matches_frozen": recovery.get("declaration") == old_plan,
        "image": image, "image_sha_matches_manifest": bool(image_path and image_path.is_file() and
            sha(image_path.read_bytes()) == recovery.get("image_sha256") == manifest.get("images", {}).get(image, {}).get("sha256")),
        "manifest_sha256": sha(manifest_raw),
    }
    prior_source_path, prior_candidate = find_prior_candidate(source_path) if source_raw else (None, None)
    provenance["prior_candidate"] = prior_candidate
    provenance["prior_source_model"] = str(prior_source_path) if prior_source_path else None
    rows = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    builds = [row.get("data", {}) for row in rows if row.get("action") == "build_plan_bim"]
    stream_path = next((path for path in (run / "agent_stream.jsonl.gz", run / "agent_stream.jsonl") if path.is_file()), None)
    stream_builds = build_stream_pairs(stream_path)
    candidate = (summary.get("delivery") or {}).get("candidate")
    final: dict = {"candidate": candidate, "complete": False}
    if candidate and (run / candidate / "report.json").is_file():
        report = load(run / candidate / "report.json")
        plan_record = report.get("provenance", {}).get("plan_input", {})
        plan_file = plan_record.get("plan_file")
        final["plan_file"] = plan_file
        final["report_manifest_sha_matches_actual"] = report.get("provenance", {}).get("input_manifest_sha256") == provenance["manifest_sha256"]
        if plan_file and (run / plan_file).is_file() and old_plan is not None:
            new_raw = (run / plan_file).read_bytes()
            new_plan = json.loads(new_raw)
            matching_log = [row for row in builds if row.get("candidate") == candidate and
                            row.get("plan_input", {}).get("plan_file") == plan_file]
            matching_stream = [row for row in stream_builds if row["response"] and
                               row["response"].get("candidate") == candidate and
                               row["response"].get("plan_input", {}).get("plan_file") == plan_file]
            old_op = old_plan.get("openings", [])
            new_op = new_plan.get("openings", [])
            old_ids = {item["id"] for item in old_op}
            old_only = [item for item in new_op if item["id"] in old_ids]
            opening_changes = item_diff(old_op, new_op, ("kind", "p1", "p2", "z"))
            partition_changes = item_diff(old_plan.get("partitions", []), new_plan.get("partitions", []), ("points",))
            seed_changes = item_diff(old_plan.get("space_seeds", []), new_plan.get("space_seeds", []), ("point", "role"))
            unrelated_seed_changes = item_diff(
                [item for item in old_plan.get("space_seeds", []) if item["id"] != merged_id],
                [item for item in new_plan.get("space_seeds", []) if item["id"] != merged_id and
                 item["id"] in {old_item["id"] for old_item in old_plan.get("space_seeds", [])}],
                ("point", "role"))
            scalars = ("floor_id", "z_floor", "ceiling_height", "x_anchors", "y_anchors", "footprint_pixels")
            fixed = {field: old_plan.get(field) == new_plan.get(field) for field in scalars}
            final.update({
                "complete": True, "plan_sha_matches_report": sha(new_raw) == plan_record.get("plan_sha256"),
                "candidate_linked_by_tool_log": bool(matching_log),
                "candidate_linked_by_mcp_stream": any(
                    row["result_linked"] and json.loads(row["request"]["plan_json"]) == new_plan
                    for row in matching_stream if "plan_json" in row["request"]),
                "unchanged_frame_and_calibration": fixed,
                "partitions": partition_changes,
                "all_prior_partition_paths_preserved": not partition_changes["deleted"] and not partition_changes["modified"],
                "space_seeds": seed_changes,
                "unrelated_prior_seeds_preserved": no_change(unrelated_seed_changes),
                "openings": opening_changes,
                "all_prior_plan_openings_preserved": no_change(item_diff(old_op, old_only, ("kind", "p1", "p2", "z"))),
            })
            new_source_path = run / candidate / "source_model.json"
            if prior_source_path and prior_source_path.is_file() and new_source_path.is_file():
                final["source_comparison"] = source_audit(load(prior_source_path), load(new_source_path), merged_id, area_tol)
            else:
                final["source_comparison_incomplete"] = "prior or new source_model.json unavailable"
        else:
            final["incomplete_reason"] = "candidate has no saved plan_input.plan_file or frozen old plan"
    elif candidate:
        final["incomplete_reason"] = "candidate report.json unavailable"
    else:
        final["incomplete_reason"] = "summary has no delivered candidate"
    actions = []
    for index, row in enumerate(rows):
        action = row.get("action")
        if action not in ("view_image", "view_pixel_profile", "pixel_profile", "map_dimension_chain", "build_plan_bim",
                          "overlay_candidate", "view_elevation_candidate", "check_openings", "view_candidate", "finish_bim"):
            continue
        data = row.get("data") or {}
        actions.append({"index": index, "action": action, "image": data.get("name") or data.get("image"),
                        "original_box": data.get("box_original_pixels") or data.get("box"),
                        "candidate": data.get("candidate"), "status": data.get("status"),
                        "error": data.get("error")})
    return {"schema_version": "southeast_recovery_scope_audit_v1", "run": str(run),
            "checks_exclude_gt": True, "merged_space_id_under_test": merged_id,
            "polygon_area_tolerance_m2": area_tol, "provenance": provenance,
            "final_candidate": final, "tool_action_counts": dict(Counter(row.get("action") for row in rows)),
            "observed_actions": actions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--merged-space-id", default="CorridorN_SE_open")
    parser.add_argument("--area-tolerance-m2", type=float, default=1e-4)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    result = audit(run, args.merged_space_id, args.area_tolerance_m2)
    output = args.out or run / "scope_verification.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    final = result["final_candidate"]
    source = final.get("source_comparison", {})
    print(json.dumps({"output": str(output), "candidate": final.get("candidate"),
                      "complete": final.get("complete"),
                      "plan_old_openings_preserved": final.get("all_prior_plan_openings_preserved"),
                      "source_old_openings_preserved": source.get("all_old_opening_kind_and_vertices_preserved"),
                      "unrelated_spaces_preserved": source.get("all_unrelated_spaces_preserved"),
                      "merged_space_coverage": source.get("old_merged_space_coverage"),
                      "partitions": final.get("partitions"), "seeds": final.get("space_seeds"),
                      "openings": final.get("openings")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
