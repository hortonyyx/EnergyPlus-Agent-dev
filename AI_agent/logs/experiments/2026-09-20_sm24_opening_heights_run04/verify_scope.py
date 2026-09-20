"""Audit run04 after completion: only exterior opening heights may change; no GT."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path


_PREVIOUS = Path(__file__).resolve().parent.parent / "2026-09-20_sm24_southeast_recovery_run03" / "verify_scope.py"
_SPEC = importlib.util.spec_from_file_location("sm24_run03_verify_scope", _PREVIOUS)
assert _SPEC and _SPEC.loader
_HELPERS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_HELPERS)
sha = _HELPERS.sha
load = _HELPERS.load
item_diff = _HELPERS.item_diff
find_prior_candidate = _HELPERS.find_prior_candidate
build_stream_pairs = _HELPERS.build_stream_pairs


def revision_stream_pairs(path: Path | None) -> list[dict]:
    if path is None:
        return []
    uses, results = [], {}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            content = event.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name", "").endswith("revise_bim"):
                    uses.append(block)
                elif block.get("type") == "tool_result":
                    results[block.get("tool_use_id", "")] = block
    pairs = []
    for use in uses:
        result = results.get(use["id"])
        content = result.get("content", []) if result else []
        texts = ([part.get("text") for part in content if isinstance(part, dict) and part.get("type") == "text"]
                 if isinstance(content, list) else [content] if isinstance(content, str) else [])
        parsed = None
        if texts:
            try:
                parsed = json.loads(texts[-1])
            except json.JSONDecodeError:
                pass
        pairs.append({"tool_use_id": use["id"], "request": use.get("input", {}),
                      "result_linked": bool(result and result.get("tool_use_id") == use["id"]),
                      "response": parsed})
    return pairs


def candidate_chain(run: Path, candidate: str, manifest_sha: str,
                    builds: list[dict], revisions: list[dict],
                    build_pairs: list[dict], revision_pairs: list[dict]) -> dict:
    """Trace final candidate to its actual build, without treating parent plan as final."""
    steps = []
    seen = set()
    current = candidate
    while current and current not in seen:
        seen.add(current)
        report_path = run / current / "report.json"
        if not report_path.is_file():
            return {"complete": False, "steps": steps, "reason": f"missing {current}/report.json"}
        report = load(report_path)
        provenance = report.get("provenance", {})
        step = {"candidate": current,
                "manifest_sha_matches": provenance.get("input_manifest_sha256") == manifest_sha,
                "proposal_sha_matches_report": sha((run / current / "proposal.json").read_bytes()) == report.get("proposal_sha256")}
        parent = provenance.get("parent_candidate")
        if parent:
            ops_path = run / current / "operations.json"
            operations = load(ops_path) if ops_path.is_file() else None
            parent_proposal = run / parent / "proposal.json"
            matching_stream = [pair for pair in revision_pairs if pair["response"] and
                               pair["response"].get("candidate") == current and
                               pair["request"].get("candidate") == parent]
            step.update({"action": "revise_bim", "parent_candidate": parent,
                         "parent_proposal_sha_matches": parent_proposal.is_file() and
                            sha(parent_proposal.read_bytes()) == provenance.get("parent_proposal_sha256"),
                         "operations_file": str(ops_path.relative_to(run)) if operations is not None else None,
                         "operations": operations,
                         "linked_by_tool_log": any(row.get("candidate") == current and
                                                   row.get("provenance", {}).get("parent_candidate") == parent
                                                   for row in revisions),
                         "linked_by_mcp_stream": any(pair["result_linked"] and
                            json.loads(pair["request"].get("operations_json", "null")) == operations
                            for pair in matching_stream)})
            steps.append(step)
            current = parent
        else:
            plan_input = provenance.get("plan_input", {})
            plan_file = plan_input.get("plan_file")
            base_plan = run / plan_file if plan_file else None
            matching_stream = [pair for pair in build_pairs if pair["response"] and
                               pair["response"].get("candidate") == current and
                               pair["response"].get("plan_input", {}).get("plan_file") == plan_file]
            step.update({"action": "build_plan_bim" if plan_file else "other_build",
                         "plan_file": plan_file,
                         "plan_sha_matches_report": bool(base_plan and base_plan.is_file() and
                            sha(base_plan.read_bytes()) == plan_input.get("plan_sha256")),
                         "linked_by_tool_log": any(row.get("candidate") == current and
                            row.get("plan_input", {}).get("plan_file") == plan_file for row in builds) if plan_file else False,
                         "linked_by_mcp_stream": any(pair["result_linked"] and
                            "plan_json" in pair["request"] and
                            json.loads(pair["request"]["plan_json"]) == load(base_plan)
                            for pair in matching_stream) if base_plan and base_plan.is_file() else False})
            steps.append(step)
            current = None
    if current in seen:
        return {"complete": False, "steps": steps, "reason": "candidate parent cycle"}
    return {"complete": True, "steps": steps,
            "all_links_verified": all(step.get("manifest_sha_matches") and
                                      step.get("proposal_sha_matches_report") and
                                      step.get("linked_by_tool_log") and
                                      step.get("linked_by_mcp_stream") and
                                      (step.get("parent_proposal_sha_matches", True)) and
                                      (step.get("plan_sha_matches_report", True))
                                      for step in steps)}


def exterior_side(item: dict, footprint: list[list[float]]) -> str | None:
    a, b = item.get("p1"), item.get("p2")
    if not isinstance(a, list) or not isinstance(b, list):
        return None
    xs, ys = [p[0] for p in footprint], [p[1] for p in footprint]
    if a[0] == b[0] == min(xs):
        return "west"
    if a[0] == b[0] == max(xs):
        return "east"
    if a[1] == b[1] == min(ys):
        return "north"
    if a[1] == b[1] == max(ys):
        return "south"
    return None


def physical_boundary(item: dict) -> dict:
    fields = ("id", "kind", "geometry_type", "space_id", "adjacent_space_ids",
              "counterpart_ids", "vertices")
    return {key: item.get(key) for key in fields}


def physical_space(item: dict) -> dict:
    fields = ("id", "floor_id", "z_floor", "height", "polygon", "role")
    return {key: item.get(key) for key in fields}


def source_checks(old: dict, new: dict, outer_ids: set[str]) -> dict:
    old_open = {item["id"]: item for item in old.get("openings", [])}
    new_open = {item["id"]: item for item in new.get("openings", [])}
    old_links = {item["opening_id"]: item for item in old.get("connections", [])}
    new_links = {item["opening_id"]: item for item in new.get("connections", [])}
    diffs = {}
    inventory = {}
    for key in sorted(old_open.keys() | new_open.keys()):
        a, b = old_open.get(key), new_open.get(key)
        if a is None or b is None:
            diffs[key] = {"before": a, "after": b}
            continue
        inventory[key] = {
            "facade_or_interior": "exterior" if key in outer_ids else "interior",
            "kind_before_after": [a.get("kind"), b.get("kind")],
            "xy_vertices_before_after": [[vertex[:2] for vertex in a.get("vertices", [])],
                                         [vertex[:2] for vertex in b.get("vertices", [])]],
            "z_vertices_before_after": [[vertex[2] for vertex in a.get("vertices", [])],
                                        [vertex[2] for vertex in b.get("vertices", [])]],
            "host_before_after": [a.get("host_boundary_id"), b.get("host_boundary_id")],
            "state_before_after": [old_links.get(key, {}).get("state"), new_links.get(key, {}).get("state")],
        }
        fields = ("kind", "exterior", "connectivity", "host_boundary_id", "space_ids")
        changed = {field: {"before": a.get(field), "after": b.get(field)}
                   for field in fields if a.get(field) != b.get(field)}
        old_xy = [vertex[:2] for vertex in a.get("vertices", [])]
        new_xy = [vertex[:2] for vertex in b.get("vertices", [])]
        old_z = [vertex[2] for vertex in a.get("vertices", [])]
        new_z = [vertex[2] for vertex in b.get("vertices", [])]
        if old_xy != new_xy:
            changed["xy_vertices"] = {"before": old_xy, "after": new_xy}
        if old_z != new_z:
            changed["z_vertices"] = {"before": old_z, "after": new_z}
        if changed:
            diffs[key] = changed
    old_spaces = {item["id"]: physical_space(item) for item in old.get("spaces", [])}
    new_spaces = {item["id"]: physical_space(item) for item in new.get("spaces", [])}
    old_bounds = {item["id"]: physical_boundary(item) for item in old.get("boundaries", [])}
    new_bounds = {item["id"]: physical_boundary(item) for item in new.get("boundaries", [])}
    common_old_openings_kept = old_open.keys() == new_open.keys()
    disallowed_opening_changes = {
        key: change for key, change in diffs.items()
        if any(field != "z_vertices" for field in change) or key not in outer_ids
    }
    return {
        "floor_geometry_unchanged": old.get("floors") == new.get("floors"),
        "spaces_unchanged": old_spaces == new_spaces,
        "spaces_before_count": len(old_spaces), "spaces_after_count": len(new_spaces),
        "space_changes": {key: {"before": old_spaces.get(key), "after": new_spaces.get(key)}
                          for key in sorted(old_spaces.keys() | new_spaces.keys())
                          if old_spaces.get(key) != new_spaces.get(key)},
        "boundaries_unchanged": old_bounds == new_bounds,
        "boundaries_before_count": len(old_bounds), "boundaries_after_count": len(new_bounds),
        "boundary_changed_ids": sorted(key for key in old_bounds.keys() | new_bounds.keys()
                                       if old_bounds.get(key) != new_bounds.get(key)),
        "boundary_relations_unchanged": old.get("boundary_relations") == new.get("boundary_relations"),
        "connections_unchanged": old.get("connections") == new.get("connections"),
        "connection_changes": item_diff(
            [{"id": row["opening_id"], **row} for row in old.get("connections", [])],
            [{"id": row["opening_id"], **row} for row in new.get("connections", [])],
            ("kind", "exterior", "space_ids", "state")),
        "opening_hosts_unchanged": old.get("opening_hosts") == new.get("opening_hosts"),
        "all_old_source_opening_ids_kept": common_old_openings_kept,
        "opening_changes": diffs,
        "opening_inventory": inventory,
        "disallowed_opening_changes": disallowed_opening_changes,
        "source_opening_scope_pass": common_old_openings_kept and not disallowed_opening_changes,
    }


def audit(run: Path) -> dict:
    if not (run / "summary.json").is_file():
        raise RuntimeError("summary.json absent; wait until generation finishes")
    manifest_raw = (run / "inputs.json").read_bytes()
    manifest = json.loads(manifest_raw)
    summary = load(run / "summary.json")
    recovery = manifest.get("plan_recovery", {})
    source_path = Path(recovery["source_path"]) if recovery.get("source_path") else None
    frozen_path = run / recovery.get("frozen_path", "resume_plan.json")
    source_raw = source_path.read_bytes() if source_path and source_path.is_file() else None
    frozen_raw = frozen_path.read_bytes() if frozen_path.is_file() else None
    old_plan = json.loads(frozen_raw) if frozen_raw else None
    image_name = recovery.get("image")
    image_path = run / "images" / image_name if image_name else None
    provenance = {
        "input_mode": manifest.get("input_mode"), "source_path": str(source_path) if source_path else None,
        "frozen_path": str(frozen_path.relative_to(run)),
        "source_exists": source_raw is not None, "frozen_exists": frozen_raw is not None,
        "frozen_equals_source_bytes": frozen_raw == source_raw if source_raw is not None else None,
        "frozen_sha_matches_manifest": sha(frozen_raw) == recovery.get("raw_sha256") if frozen_raw else False,
        "declaration_matches_frozen": recovery.get("declaration") == old_plan,
        "image": image_name,
        "image_sha_matches_manifest": bool(image_path and image_path.is_file() and
            sha(image_path.read_bytes()) == recovery.get("image_sha256") == manifest.get("images", {}).get(image_name, {}).get("sha256")),
        "manifest_sha256": sha(manifest_raw),
    }
    prior_source_path, prior_candidate = find_prior_candidate(source_path) if source_raw else (None, None)
    provenance["prior_candidate"] = prior_candidate
    rows = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    builds = [row.get("data", {}) for row in rows if row.get("action") == "build_plan_bim"]
    revisions = [row.get("data", {}) for row in rows if row.get("action") == "revise_bim"]
    stream_path = next((p for p in (run / "agent_stream.jsonl.gz", run / "agent_stream.jsonl") if p.is_file()), None)
    stream_builds = build_stream_pairs(stream_path)
    stream_revisions = revision_stream_pairs(stream_path)
    candidate = (summary.get("delivery") or {}).get("candidate")
    final = {"candidate": candidate, "complete": False}
    outer = ({key: exterior_side(item, old_plan["footprint_pixels"])
              for key, item in ((row["id"], row) for row in old_plan.get("openings", []))
              if exterior_side(item, old_plan["footprint_pixels"])} if old_plan else {})
    if candidate and (run / candidate / "report.json").is_file() and old_plan:
        report = load(run / candidate / "report.json")
        chain = candidate_chain(run, candidate, provenance["manifest_sha256"],
                                builds, revisions, stream_builds, stream_revisions)
        final["candidate_chain"] = chain
        base = chain.get("steps", [])[-1] if chain.get("steps") else {}
        base_plan_file = base.get("plan_file")
        if base_plan_file and (run / base_plan_file).is_file():
            base_plan = load(run / base_plan_file)
            final["base_plan_changed_fields"] = sorted(
                key for key in old_plan.keys() | base_plan.keys() if old_plan.get(key) != base_plan.get(key))
            final["base_plan_structurally_equals_frozen"] = base_plan == old_plan
            fields = ("floor_id", "z_floor", "ceiling_height", "x_anchors", "y_anchors", "footprint_pixels")
            final["base_plan_physical_equals_frozen"] = (
                all(base_plan.get(field) == old_plan.get(field) for field in fields) and
                not any(item_diff(old_plan.get("partitions", []), base_plan.get("partitions", []), ("points",)).values()) and
                not any(item_diff(old_plan.get("space_seeds", []), base_plan.get("space_seeds", []), ("point", "role")).values()) and
                not any(item_diff(old_plan.get("openings", []), base_plan.get("openings", []),
                                  ("kind", "p1", "p2", "z")).values()))
        else:
            final["base_plan_structurally_equals_frozen"] = None
            final["base_plan_physical_equals_frozen"] = None
        associated = report.get("provenance", {}).get("plan_input", {})
        plan_file = associated.get("plan_file")
        final["plan_file"] = plan_file
        final["report_manifest_sha_matches_actual"] = report.get("provenance", {}).get("input_manifest_sha256") == provenance["manifest_sha256"]
        if plan_file and (run / plan_file).is_file():
            final["plan_comparison_applicability"] = "final candidate directly compiled from saved plan"
            raw = (run / plan_file).read_bytes()
            new_plan = json.loads(raw)
            fixed_fields = ("floor_id", "z_floor", "ceiling_height", "x_anchors", "y_anchors", "footprint_pixels")
            fixed = {field: old_plan.get(field) == new_plan.get(field) for field in fixed_fields}
            partitions = item_diff(old_plan.get("partitions", []), new_plan.get("partitions", []), ("points",))
            seeds = item_diff(old_plan.get("space_seeds", []), new_plan.get("space_seeds", []), ("point", "role"))
            old_open = {item["id"]: item for item in old_plan.get("openings", [])}
            new_open = {item["id"]: item for item in new_plan.get("openings", [])}
            opening_diffs = {}
            for key in sorted(old_open.keys() | new_open.keys()):
                a, b = old_open.get(key), new_open.get(key)
                if a is None or b is None:
                    opening_diffs[key] = {"before": a, "after": b}
                    continue
                fields = sorted((a.keys() | b.keys()) - {"z", "source_refs", "notes", "assumptions"})
                changed = {field: {"before": a.get(field), "after": b.get(field)}
                           for field in fields if a.get(field) != b.get(field)}
                if a.get("z") != b.get("z"):
                    changed["z"] = {"before": a.get("z"), "after": b.get("z")}
                if changed:
                    opening_diffs[key] = changed
            disallowed = {key: change for key, change in opening_diffs.items()
                          if key not in outer or any(field != "z" for field in change)}
            matching_log = any(row.get("candidate") == candidate and
                               row.get("plan_input", {}).get("plan_file") == plan_file for row in builds)
            matching_stream = any(row["result_linked"] and row["response"] and
                                  row["response"].get("candidate") == candidate and
                                  row["response"].get("plan_input", {}).get("plan_file") == plan_file and
                                  "plan_json" in row["request"] and json.loads(row["request"]["plan_json"]) == new_plan
                                  for row in stream_builds)
            final.update({
                "complete": True, "plan_sha_matches_report": sha(raw) == associated.get("plan_sha256"),
                "candidate_linked_by_tool_log": matching_log, "candidate_linked_by_mcp_stream": matching_stream,
                "fixed_plan_fields": fixed, "partitions": partitions, "seeds": seeds,
                "all_old_plan_opening_ids_kept": old_open.keys() == new_open.keys(),
                "exterior_opening_sides": outer,
                "opening_changes": opening_diffs, "disallowed_plan_opening_changes": disallowed,
                "plan_scope_pass": all(fixed.values()) and all(not part for part in partitions.values()) and
                                   all(not part for part in seeds.values()) and
                                   old_open.keys() == new_open.keys() and not disallowed,
            })
        else:
            final.update({"complete": True,
                          "plan_comparison_applicability": "not applicable: final candidate is a revision, not a plan compilation",
                          "inherited_base_plan_file_not_final_declaration": base.get("plan_file"),
                          "exterior_opening_sides_from_frozen_plan": outer})
        new_source_path = run / candidate / "source_model.json"
        if prior_source_path and prior_source_path.is_file() and new_source_path.is_file():
            final["source_checks"] = source_checks(load(prior_source_path), load(new_source_path), set(outer))
        else:
            final["source_checks_incomplete"] = "prior or final source_model.json unavailable"
        final["complete"] = bool(chain.get("complete") and "source_checks" in final and
                                 (not plan_file or (run / plan_file).is_file()))
        source = final.get("source_checks", {})
        final["scope_pass"] = bool(final["complete"] and chain.get("all_links_verified") and
            final.get("report_manifest_sha_matches_actual") and
            final.get("base_plan_physical_equals_frozen") and
            (final.get("plan_scope_pass") is not False) and
            source.get("floor_geometry_unchanged") and source.get("spaces_unchanged") and
            source.get("boundaries_unchanged") and source.get("boundary_relations_unchanged") and
            source.get("connections_unchanged") and source.get("opening_hosts_unchanged") and
            source.get("source_opening_scope_pass"))
    else:
        final["incomplete_reason"] = "no delivered candidate, report, or frozen plan"
    actions = []
    for index, row in enumerate(rows):
        action = row.get("action")
        if action not in ("view_image", "view_pixel_profile", "pixel_profile", "map_dimension_chain",
                          "build_plan_bim", "revise_bim", "overlay_candidate", "view_elevation_candidate", "check_openings",
                          "view_candidate", "finish_bim"):
            continue
        data = row.get("data") or {}
        actions.append({"index": index, "action": action, "image": data.get("name") or data.get("image"),
                        "facade": data.get("facade"),
                        "original_box": data.get("box_original_pixels") or data.get("box"),
                        "candidate": data.get("candidate"), "status": data.get("status"), "error": data.get("error")})
    original_elevation_actions = [row for row in actions if row["action"] in ("view_image", "view_pixel_profile", "pixel_profile")
                                  and row["image"] not in (None, image_name)]
    source_elevation_actions = [row for row in actions if row["action"] == "view_elevation_candidate"]
    return {"schema_version": "opening_height_scope_audit_v1", "run": str(run), "checks_exclude_gt": True,
            "provenance": provenance, "final_candidate": final,
            "tool_action_counts": dict(Counter(row.get("action") for row in rows)),
            "original_elevation_actions": original_elevation_actions,
            "source_elevation_actions": source_elevation_actions,
            "observed_actions": actions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    result = audit(run)
    output = args.out or run / "scope_verification.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    final = result["final_candidate"]
    print(json.dumps({"output": str(output), "candidate": final.get("candidate"),
                      "complete": final.get("complete"), "scope_pass": final.get("scope_pass"),
                      "plan_comparison_applicability": final.get("plan_comparison_applicability"),
                      "source_opening_scope_pass": final.get("source_checks", {}).get("source_opening_scope_pass"),
                      "opening_changes": final.get("source_checks", {}).get("opening_changes", final.get("opening_changes")),
                      "original_elevation_views": len(result["original_elevation_actions"]),
                      "source_elevation_views": len(result["source_elevation_actions"])},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
