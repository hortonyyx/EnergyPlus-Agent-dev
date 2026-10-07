"""Deterministic single-floor replay for the legacy sm25 F2 E->F->A handoff.

This script uses the original H one-axis dimension fixture.  It does not load
role_fixture_dimension_inputs.json and makes no model request.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("q1_handoff_replay", HERE / "replay.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load replay.py")
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)

from src.agent.geometry import plan_regularization as production
from src.agent.geometry.plan_dimension_alignment import align_plan_to_dimensions
from src.agent.geometry.plan_ink_alignment import align_plan_to_ink
from src.agent.geometry.plan_partition import compile_plan_partition


def stage_summary(score: dict[str, Any]) -> dict[str, Any]:
    semantic = score["semantics"]["F2"]
    return {
        "compiled": True,
        "counts": {key: semantic[key] for key in ("rooms", "openings", "doors", "windows")},
        "room_ids": semantic["room_ids"],
        "space_seed_ids": semantic["space_seed_ids"],
        "room_boundary_tiers": score["tiers_room_boundary"],
        "opening_along_wall_tiers": score["tiers_opening_along_wall"],
        "opening_hosts": semantic["opening_hosts"],
        "door_connections": semantic["door_connections"],
    }


def mapping_delta(before: dict[str, Any], after: dict[str, Any], key: str) -> list[dict[str, Any]]:
    old, new = dict(before[key]), dict(after[key])
    return [
        {"opening_id": identity, "before": old[identity], "after": new[identity]}
        for identity in sorted(old.keys() & new.keys()) if old[identity] != new[identity]
    ]


def semantic_delta(before_score: dict[str, Any], after_score: dict[str, Any]) -> dict[str, Any]:
    before, after = before_score["semantics"]["F2"], after_score["semantics"]["F2"]
    return {
        "room_ids_removed": sorted(set(before["room_ids"]) - set(after["room_ids"])),
        "room_ids_added": sorted(set(after["room_ids"]) - set(before["room_ids"])),
        "opening_host_changes": mapping_delta(before, after, "opening_hosts"),
        "door_connection_changes": mapping_delta(before, after, "door_connections"),
    }


def compile_status(plan: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    try:
        compile_plan_partition(
            plan, image_size=tuple(item["image_size"]), image_name=item["image_name"])
    except Exception as error:
        return {"status": "rejected", "error": f"{type(error).__name__}: {error}"}
    return {"status": "pass", "error": None}


def polygon_area(vertices: list[list[float]]) -> float:
    return abs(sum(
        float(vertices[index][0]) * float(vertices[(index + 1) % len(vertices)][1])
        - float(vertices[(index + 1) % len(vertices)][0]) * float(vertices[index][1])
        for index in range(len(vertices))
    )) / 2.0 if len(vertices) >= 3 else 0.0


def compiled_cells(plan: dict[str, Any], item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    proposal, _ = compile_plan_partition(
        plan, image_size=tuple(item["image_size"]), image_name=item["image_name"])
    floors = proposal.get("geometry", {}).get("floors", [])
    return {
        str(cell["id"]): copy.deepcopy(cell)
        for floor in floors for cell in floor.get("cells", [])
    }


def handoff_semantic_audit(
        original_score: dict[str, Any], after_score: dict[str, Any],
        original_plan: dict[str, Any], report: dict[str, Any],
        item: dict[str, Any]) -> dict[str, Any]:
    """Audit only the explicit fixed-footprint strip merges in this handoff.

    F itself cannot compile, so production cannot derive a pre-A semantic
    signature.  This audit compares the last compilable original trial with
    the delivered A result and accepts only changes tied to the exact fixed
    merge and retain-opening records emitted by production.
    """
    before = original_score["semantics"]["F2"]
    after = after_score["semantics"]["F2"]
    changes = [row for row in report.get("changes", []) if isinstance(row, dict)]
    fixed_merges = [
        row for row in changes
        if row.get("type") == "merge_duplicate_wall_into_fixed_footprint"
    ]
    retain_rows = [
        row for row in changes if row.get("type") == "retain_openings_on_merged_wall"
    ]
    fixed_partition_ids = {
        str(row.get("partition_id")) for row in fixed_merges if row.get("partition_id")
    }
    fixed_opening_ids = {
        str(identity) for row in fixed_merges
        for identity in (row.get("object_ids") or {}).get("openings", [])
    }
    retained_opening_ids = {
        str(identity) for row in retain_rows for identity in row.get("opening_ids", [])
    }

    old_rooms, new_rooms = set(before["room_ids"]), set(after["room_ids"])
    old_seeds, new_seeds = set(before["space_seed_ids"]), set(after["space_seed_ids"])
    old_kinds, new_kinds = dict(before["opening_kinds"]), dict(after["opening_kinds"])
    old_hosts, new_hosts = dict(before["opening_hosts"]), dict(after["opening_hosts"])
    old_doors, new_doors = dict(before["door_connections"]), dict(after["door_connections"])
    removed_rooms, added_rooms = old_rooms - new_rooms, new_rooms - old_rooms
    removed_openings, added_openings = set(old_kinds) - set(new_kinds), set(new_kinds) - set(old_kinds)
    changed_kinds = {
        identity for identity in old_kinds.keys() & new_kinds.keys()
        if old_kinds[identity] != new_kinds[identity]
    }
    changed_hosts = {
        identity for identity in old_hosts.keys() & new_hosts.keys()
        if old_hosts[identity] != new_hosts[identity]
    }
    changed_doors = {
        identity for identity in old_doors.keys() & new_doors.keys()
        if old_doors[identity] != new_doors[identity]
    }

    source_refs_by_partition = {
        str(row.get("id")): set(map(str, row.get("source_refs", [])))
        for row in original_plan.get("partitions", []) if row.get("id") is not None
    }
    cells = compiled_cells(original_plan, item)
    eliminated_strips = []
    for room_id in sorted(removed_rooms):
        cell = cells.get(room_id, {})
        cell_refs = set(map(str, cell.get("source_refs", [])))
        matched = sorted(
            partition_id for partition_id in fixed_partition_ids
            if cell_refs & source_refs_by_partition.get(partition_id, set())
        )
        polygon = copy.deepcopy(cell.get("polygon", []))
        eliminated_strips.append({
            "room_id": room_id,
            "was_named_space_seed": room_id in old_seeds,
            "matched_fixed_merge_partition_ids": matched,
            "matched_boundary_count": len(matched),
            "polygon": polygon,
            "area_m2": round(polygon_area(polygon), 9),
            "source_refs": sorted(cell_refs),
            "accepted": room_id not in old_seeds and len(matched) >= 2,
        })

    allowed_opening_mappings = []
    for opening_id in sorted(changed_hosts):
        supporting_merges = sorted({
            str(row.get("partition_id")) for row in fixed_merges
            if opening_id in set(map(str, (row.get("object_ids") or {}).get("openings", [])))
        })
        supporting_retains = sorted({
            str(row.get("partition_id")) for row in retain_rows
            if opening_id in set(map(str, row.get("opening_ids", [])))
        })
        allowed_opening_mappings.append({
            "old_opening_id": opening_id,
            "surviving_opening_id": opening_id,
            "kind_before": old_kinds.get(opening_id),
            "kind_after": new_kinds.get(opening_id),
            "before_hosts": old_hosts.get(opening_id),
            "after_hosts": new_hosts.get(opening_id),
            "before_connection": {
                "kind": old_kinds.get(opening_id), "is_exterior": True,
                "connected_space_count": len(old_hosts.get(opening_id, [])),
            },
            "after_connection": {
                "kind": new_kinds.get(opening_id), "is_exterior": True,
                "connected_space_count": len(new_hosts.get(opening_id, [])),
            },
            "supporting_fixed_merge_partition_ids": supporting_merges,
            "supporting_retain_change_partition_ids": supporting_retains,
            "accepted": bool(
                opening_id in fixed_opening_ids
                and opening_id in retained_opening_ids
                and old_kinds.get(opening_id) == new_kinds.get(opening_id)
                and len(old_hosts.get(opening_id, [])) == len(new_hosts.get(opening_id, [])) == 1
            ),
        })

    checks = {
        "no_added_or_removed_openings": not added_openings and not removed_openings,
        "surviving_opening_kinds_unchanged": not changed_kinds,
        "door_connections_unchanged": not changed_doors,
        "named_space_seeds_unchanged": old_seeds == new_seeds,
        "no_added_rooms": not added_rooms,
        "room_delta_exactly_matches_audited_unseeded_strips": (
            len(after["room_ids"]) - len(before["room_ids"]) == -len(eliminated_strips)
            and all(row["accepted"] for row in eliminated_strips)
        ),
        "host_changes_exactly_match_fixed_merge_retains": (
            changed_hosts == fixed_opening_ids == retained_opening_ids
            and all(row["accepted"] for row in allowed_opening_mappings)
        ),
    }
    return {
        "schema": "q1_dimension_handoff_semantic_audit_v1",
        "status": "pass" if all(checks.values()) else "rejected",
        "checks": checks,
        "counts_before": {
            key: before[key] for key in ("rooms", "openings", "doors", "windows")},
        "counts_after": {
            key: after[key] for key in ("rooms", "openings", "doors", "windows")},
        "removed_room_ids": sorted(removed_rooms),
        "added_room_ids": sorted(added_rooms),
        "eliminated_unseeded_fixed_strip_spaces": eliminated_strips,
        "changed_opening_host_ids": sorted(changed_hosts),
        "allowed_opening_mappings": allowed_opening_mappings,
        "changed_door_connection_ids": sorted(changed_doors),
        "production_fixed_merge_partition_ids": sorted(fixed_partition_ids),
        "production_fixed_merge_opening_ids": sorted(fixed_opening_ids),
        "production_retain_opening_ids": sorted(retained_opening_ids),
    }


def run_probe() -> dict[str, Any]:
    manifest = replay.inventory()
    group = next(row for row in manifest["reader_trials"]
                 if row["run"] == "sm25_cmp3_role_trials")
    item = next(row for row in group["plans"] if row["floor_id"] == "F2")
    fixture = copy.deepcopy(replay.DEV_DIMENSION_FIXTURES[(group["run"], "F2")])

    original_score = replay.score_plans(group["run"], [item])
    with Image.open(item["image_path"]) as image:
        ink_plan, ink_report = align_plan_to_ink(
            image, copy.deepcopy(item["plan"]), search_world_m=0.30)
    ink_item = copy.deepcopy(item)
    ink_item["plan"] = ink_plan
    ink_score = replay.score_plans(group["run"], [ink_item])

    dimension_input = copy.deepcopy(ink_plan)
    dimension_input["dimension_chains"] = [
        {key: copy.deepcopy(chain[key]) for key in
         ("id", "axis", "segments_mm", "total_mm", "tick_pixels", "source_refs")}
        for chain in fixture
    ]
    dimension_plan, dimension_report = align_plan_to_dimensions(dimension_input)
    dimension_compile = compile_status(dimension_plan, item)
    dimension_item = copy.deepcopy(item)
    dimension_item["plan"] = dimension_plan
    dimension_source_gate = replay.source_save_gate([dimension_item])

    regularized_plan = None
    regularization_report: dict[str, Any] = {}
    regularization_error = None
    strict_compile_after_a = {"status": "not_reached", "error": "no A output"}
    after_a_score = None
    after_a_source_gate: dict[str, Any] = {
        "status": "not_reached", "reason": "regularize_plan returned no deliverable plan"}
    try:
        regularized_plan, regularization_report = replay.supported_call(
            production.regularize_plan, copy.deepcopy(dimension_plan),
            image_size=tuple(item["image_size"]), image_name=item["image_name"],
            rule_version=replay.RULE_VERSION)
        replay.supported_call(
            production.enforce_regularized_plan, regularized_plan,
            image_size=tuple(item["image_size"]), image_name=item["image_name"],
            rule_version=replay.RULE_VERSION)
        strict_compile_after_a = compile_status(regularized_plan, item)
        if strict_compile_after_a["status"] == "pass":
            after_item = copy.deepcopy(item)
            after_item["plan"] = regularized_plan
            after_a_score = replay.score_plans(group["run"], [after_item])
            after_a_source_gate = replay.source_save_gate([after_item])
    except Exception as error:
        regularization_error = f"{type(error).__name__}: {error}"
        failure = getattr(error, "report", None)
        if isinstance(failure, dict):
            regularization_report = failure
            compile_rejection = next((
                row for row in failure.get("rejections", [])
                if row.get("type") == "strict_compile_failed_after_regularization"
            ), None)
            if compile_rejection is not None:
                strict_compile_after_a = {
                    "status": "rejected_inside_regularize_plan",
                    "error": compile_rejection.get("error"),
                    "contradiction_category": compile_rejection.get("contradiction_category"),
                }

    attempted = [row for row in regularization_report.get("attempted_changes", [])
                 if isinstance(row, dict)]
    delivered = [row for row in regularization_report.get("changes", [])
                 if isinstance(row, dict)]
    rejections = [row for row in regularization_report.get("rejections", [])
                  if isinstance(row, dict)]
    items = replay.classify_items(regularization_report, delivered=after_a_score is not None)
    after_a_semantic_audit = None
    handoff_audit = None
    if after_a_score is not None:
        after_a_semantic_audit = replay.semantic_audit(
            original_score, after_a_score, items["applied_changes"], items["semantic_mappings"])
        handoff_audit = handoff_semantic_audit(
            original_score, after_a_score, item["plan"], regularization_report, item)

    delivered_merges = sum(
        str(row.get("type", "")).startswith("merge_duplicate_wall") for row in delivered)
    delivery_ready = bool(
        after_a_score is not None and strict_compile_after_a["status"] == "pass"
        and after_a_source_gate.get("status") == "pass"
        and (handoff_audit or {}).get("status") == "pass"
    )
    return {
        "schema": "q1_reader_dimension_handoff_v1",
        "model_requests": 0,
        "scope": {
            "run": group["run"], "floor_id": "F2",
            "pipeline": "original passed trial -> production ink E -> original one-axis legacy F fixture -> production single-floor A -> literal compile -> source gate",
            "fixture_scope": "original H X_BOTTOM_VISIBLE fixture only; role_fixture_dimension_inputs.json is excluded",
            "interpretation": "The main H 4/5 dimension count measures F output in isolation. This probe tests whether production A can consume the fifth F candidate.",
        },
        "production_sha256": {
            "regularization": replay.sha256(replay.ROOT / "src/agent/geometry/plan_regularization.py"),
            "ink_alignment": replay.sha256(replay.ROOT / "src/agent/geometry/plan_ink_alignment.py"),
            "dimension_alignment": replay.sha256(replay.ROOT / "src/agent/geometry/plan_dimension_alignment.py"),
            "plan_compiler": replay.sha256(replay.ROOT / "src/agent/geometry/plan_partition.py"),
            "source_save_gate": replay.sha256(replay.ROOT / "scripts/tool_scripts/bim_agent_regularization.py"),
        },
        "input": {
            "plan_path": item["plan_path"], "plan_sha256": item["plan_sha256"],
            "image_path": item["image_path"], "image_sha256": item["image_sha256"],
            "image_size": item["image_size"], "fixture": fixture,
        },
        "plan_digests": {
            "original": replay.canonical_sha(item["plan"]),
            "after_ink": replay.canonical_sha(ink_plan),
            "after_dimension": replay.canonical_sha(dimension_plan),
            "after_a": replay.canonical_sha(regularized_plan) if regularized_plan is not None else None,
        },
        "stage_metrics": {
            "original": stage_summary(original_score),
            "after_ink": stage_summary(ink_score),
            "after_dimension_then_a": (
                stage_summary(after_a_score) if after_a_score is not None else {
                    "compiled": False, "counts": None, "room_boundary_tiers": None,
                    "opening_along_wall_tiers": None,
                    "reason": "regularize_plan returned no deliverable plan",
                }),
        },
        "semantic_comparison": {
            "original_to_ink": semantic_delta(original_score, ink_score),
            "original_to_after_a": (
                semantic_delta(original_score, after_a_score) if after_a_score is not None else None),
            "after_a_audit": after_a_semantic_audit,
            "handoff_fixed_strip_audit": handoff_audit,
            "production_mapping": copy.deepcopy(
                regularization_report.get("semantic_mapping", {})),
        },
        "ink": {"status": ink_report.get("status"), "report": ink_report},
        "dimension": {
            "status": dimension_report.get("status"), "report": dimension_report,
            "origin_basis": [row.get("origin_basis") for row in dimension_report.get("items", [])
                             if row.get("origin_basis") is not None],
            "raw_plan_object_counts_not_compiled_semantics": {
                "partitions": len(dimension_plan.get("partitions", [])),
                "openings": len(dimension_plan.get("openings", [])),
                "space_seeds": len(dimension_plan.get("space_seeds", [])),
                "footprint_vertices": len(dimension_plan.get("footprint_pixels", [])),
            },
            "literal_compile": dimension_compile,
        },
        "regularization_a": {
            "status": regularization_report.get("status", "rejected"),
            "error": regularization_error,
            "report": regularization_report,
            "attempted_change_counts": dict(sorted(Counter(
                str(row.get("type")) for row in attempted).items())),
            "delivered_change_counts": dict(sorted(Counter(
                str(row.get("type")) for row in delivered).items())),
            "attempted_duplicate_wall_merges": sum(
                str(row.get("type", "")).startswith("merge_duplicate_wall") for row in attempted),
            "delivered_duplicate_wall_merges": delivered_merges,
            "attempted_rehost_opening_ids": sorted({
                str(identity) for row in attempted
                if row.get("type") == "retain_openings_on_merged_wall"
                for identity in row.get("opening_ids", [])
            }),
            "rejection_counts": dict(sorted(Counter(
                str(row.get("type")) for row in rejections).items())),
            "strict_compile_after_a": strict_compile_after_a,
        },
        "source_gate": {
            "on_dimension_candidate_actual_result": dimension_source_gate,
            "after_a": after_a_source_gate,
        },
        "outcome": {
            "status": "delivered_after_a" if delivery_ready else "rejected_no_deliverable_after_a",
            "delivered_duplicate_wall_merges": delivered_merges if delivery_ready else 0,
            "after_a_metrics_available": after_a_score is not None,
            "cause": None if delivery_ready else regularization_error,
            "specific_rejection": rejections,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=HERE / "reader_dimension_handoff.json")
    args = parser.parse_args()
    args.report.write_text(
        json.dumps(run_probe(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
