"""Q1-H deterministic offline replay and evidence report.

The script reads historical plans and calls the production regularization and
reader-alignment APIs.  It contains no geometry repair implementation and
makes no model requests.

Usage:
  python replay.py --manifest-only
  python replay.py --report replay_report.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MAIN_ROOT = Path(os.environ.get("ENERGYPLUS_AGENT_MAIN", r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev"))
CMP3 = MAIN_ROOT / "AI_agent/archive/local_backup/cmp3"
LOCAL_BACKUP = MAIN_ROOT / "AI_agent/archive/local_backup"
COMPARISON = ROOT / "AI_agent/logs/experiments/2026-10-07_three_case_comparison"
REFERENCES = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis/references"
SCORER_PATH = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis/score_role_answers.py"
ROLE_FIXTURE_DIMENSION_INPUTS = HERE / "role_fixture_dimension_inputs.json"

RULE_VERSION = "plan_regularization_v1"
ROUND2_EVIDENCE_NAMES = (
    "README.md", "replay.py", "replay_report.json", "replay_notes.md",
    "itemized_changes.md", "verification_summary.json", "scope_check.json",
    "reader_dimension_handoff.py", "reader_dimension_handoff.json",
)
ROUND2_REPORT = HERE / "round2/replay_report.json"
ROUND3_EXPECTED_EXTERIOR_RUNS = {
    "sm25_role", "sm25_single",
    "2026-09-26_sm25_height_cold_claude_run53",
    "2026-09-26_sm25_height_repeat_claude_run54",
}
CMP3_RUNS = (
    "sm21_role", "sm21_single", "sm24_role", "sm24_single", "sm25_role", "sm25_single",
)
HISTORICAL_RUNS = (
    "2026-10-01_opus_dev_sm21",
    "2026-10-01_opus_dev_sm24",
    "2026-10-01_opus_dev_sm25",
    "2026-09-26_sm25_height_cold_claude_run53",
    "2026-09-26_sm25_height_repeat_claude_run54",
    "2026-09-26_sm24_whole_building_claude_run55",
    "2026-09-26_sm24_whole_building_repeat_claude_run56",
    "2026-09-26_sm21_whole_building_claude_run57",
    "2026-09-27_sm21_whole_building_repeat_claude_run58",
)
TRIAL_RUNS = (
    ("sm24_plan_reader_run3", LOCAL_BACKUP / "plan_reader_probe/run3"),
    ("sm24_role_debug_run3", LOCAL_BACKUP / "role_debug/sm24_run3"),
    ("sm24_role_debug_run7", LOCAL_BACKUP / "role_debug/sm24_run7"),
    ("sm21_role_debug_run1", LOCAL_BACKUP / "role_debug/sm21_run1"),
    ("sm25_cmp3_role_trials", CMP3 / "sm25_role"),
)

# Read manually from the visible source annotations with view_image.  These are
# development aids for F, never work-model input and never derived from GT.
DEV_DIMENSION_FIXTURES: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("sm24_role_debug_run7", "F1"): [{
        "id": "X_TOP_VISIBLE",
        "axis": "x",
        "segments_mm": [540, 1600, 2520, 4800, 540],
        "total_mm": 10000,
        "tick_pixels": [248.0, 268.0, 326.0, 417.0, 592.0, 611.0],
        "source_refs": ["1f_view.png: top dimension chain 540/1600/2520/4800/540"],
        "source_bbox_px": [240, 45, 620, 165],
        "provenance": "dev_auxiliary labels and green extension-line pixels read from original after view_image; no GT",
    }],
    ("sm21_role_debug_run1", "F1"): [{
        "id": "X_OVERALL_VISIBLE",
        "axis": "x", "segments_mm": [15000], "total_mm": 15000,
        "tick_pixels": [425.0, 1815.0],
        "source_refs": ["1f_view.png: top overall dimension 15000"],
        "source_bbox_px": [370, 60, 1710, 225],
        "provenance": "dev_auxiliary label and green extension-line pixels read from original after view_image; no GT",
    }],
    ("sm21_role_debug_run1", "F2"): [{
        "id": "X_OVERALL_VISIBLE",
        "axis": "x", "segments_mm": [15000], "total_mm": 15000,
        "tick_pixels": [427.0, 1813.0],
        "source_refs": ["2f_view.png: top overall dimension 15000"],
        "source_bbox_px": [375, 55, 1725, 220],
        "provenance": "dev_auxiliary label and green extension-line pixels read from original after view_image; no GT",
    }],
    ("sm25_cmp3_role_trials", "F1"): [{
        "id": "X_BOTTOM_VISIBLE",
        "axis": "x", "segments_mm": [5000, 8000, 7940, 4060], "total_mm": 25000,
        "tick_pixels": [282.0, 513.0, 883.0, 1250.0, 1437.0],
        "source_refs": ["1f_view.png: bottom chain 5000/8000/7940/4060, overall 25000"],
        "source_bbox_px": [260, 1190, 1430, 1415],
        "provenance": "dev_auxiliary labels and green extension-line pixels read from original after view_image; no GT",
    }],
    ("sm25_cmp3_role_trials", "F2"): [{
        "id": "X_BOTTOM_VISIBLE",
        "axis": "x", "segments_mm": [5000, 4090, 3910, 3910, 4030, 4060], "total_mm": 25000,
        "tick_pixels": [241.0, 470.0, 658.0, 837.0, 1016.0, 1201.0, 1387.0],
        "source_refs": ["2f_view.png: bottom chain 5000/4090/3910/3910/4030/4060, overall 25000"],
        "source_bbox_px": [220, 1290, 1380, 1485],
        "provenance": "dev_auxiliary labels and green extension-line pixels read from original after view_image; no GT",
    }],
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def case_key(name: str) -> str:
    for key in ("sm21", "sm24", "sm25"):
        if key in name:
            return key
    raise ValueError(f"cannot determine case for {name}")


def reference_path(name: str) -> Path:
    key = case_key(name)
    return REFERENCES / ({"sm21": "sm21_anchor.json", "sm24": "sm24_anchor.json", "sm25": "sm25-L_anchor.json"}[key])


def draft_record(path: Path, *, run: str, evidence_class: str) -> dict[str, Any]:
    plan = read_json(path)
    folder = path.parent
    compilation_path = folder / "compilation.json"
    input_path = folder / "input.json"
    compilation = read_json(compilation_path) if compilation_path.is_file() else {}
    input_row = read_json(input_path) if input_path.is_file() else {}
    image_name = compilation.get("image_name") or input_row.get("image") or plan.get("image")
    image_size = compilation.get("image_size")
    image_path = None
    if image_name:
        candidates = [folder.parent.parent / "images" / image_name]
        candidates += list(path.parents[2].glob(f"images/{image_name}")) if len(path.parents) > 2 else []
        candidates += list(path.parents[4].glob(f"bim/images/{image_name}")) if len(path.parents) > 4 else []
        image_path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if image_path is None:
            image_path = next((candidate for candidate in path.parents[0].parents[0].rglob(image_name)
                               if candidate.parent.name == "images"), None)
    if image_size is None and image_path and image_path.is_file():
        with Image.open(image_path) as image:
            image_size = list(image.size)
    return {
        "run": run,
        "case": case_key(run),
        "evidence_class": evidence_class,
        "floor_id": str(plan.get("floor_id")),
        "plan_path": str(path),
        "plan_sha256": sha256(path),
        "image_name": image_name,
        "image_path": str(image_path) if image_path else None,
        "image_sha256": sha256(image_path) if image_path and image_path.is_file() else None,
        "image_size": image_size,
        "plan": plan,
    }


def latest_drafts(run_root: Path, *, run: str, evidence_class: str) -> list[dict[str, Any]]:
    drafts = sorted(run_root.glob("plan_drafts/draft_*/plan.json"))
    by_floor: dict[str, dict[str, Any]] = {}
    for path in drafts:
        row = draft_record(path, run=run, evidence_class=evidence_class)
        by_floor[row["floor_id"]] = row
    return [by_floor[key] for key in sorted(by_floor)]


def passed_trial_drafts(run_root: Path, *, run: str) -> list[dict[str, Any]]:
    by_floor: dict[str, dict[str, Any]] = {}
    for receipt_path in sorted(run_root.rglob("trial_receipts/trial_*.json")):
        if not receipt_path.stem.removeprefix("trial_").isdigit():
            continue
        receipt = read_json(receipt_path)
        if receipt.get("status") != "passed":
            continue
        workspace = receipt_path.parent.parent
        expected = receipt.get("plan_sha256")
        matches = [path for path in workspace.glob("plan_drafts/draft_*/plan.json") if sha256(path) == expected]
        if not matches:
            companion = receipt_path.with_name(receipt_path.stem + "_plan.json")
            matches = [companion] if companion.is_file() and sha256(companion) == expected else []
        if not matches:
            continue
        row = draft_record(matches[-1], run=run, evidence_class="real_reader_trial")
        row["trial_receipt_path"] = str(receipt_path)
        row["trial_receipt_sha256"] = sha256(receipt_path)
        by_floor[row["floor_id"]] = row
    return [by_floor[key] for key in sorted(by_floor)]


def inventory() -> dict[str, Any]:
    groups = []
    for name in CMP3_RUNS:
        root = CMP3 / name / "bim"
        delivery = read_json(root / "delivery.json")
        rows = latest_drafts(root, run=name, evidence_class="real_work_model_delivery")
        delivered_source = root / str(delivery.get("candidate")) / "source_model.json"
        groups.append({
            "run": name,
            "case": case_key(name),
            "evidence_class": "real_work_model_delivery",
            "root": str(root),
            "delivery_path": str(root / "delivery.json"),
            "delivery_sha256": sha256(root / "delivery.json"),
            "delivered_candidate": delivery.get("candidate"),
            "delivered_source_path": str(delivered_source),
            "delivered_source_sha256": sha256(delivered_source),
            "selection": "latest saved plan draft per floor; delivery source retained separately",
            "plans": rows,
        })
    for name in HISTORICAL_RUNS:
        root = ROOT / "AI_agent/logs/experiments" / name
        evidence_class = "dev_auxiliary_opus" if "opus_dev" in name else "legal_replay_claude_code"
        delivery_path = root / "delivery.json"
        delivery = read_json(delivery_path) if delivery_path.is_file() else {}
        delivered_source = root / str(delivery.get("candidate")) / "source_model.json"
        group = {
            "run": name, "case": case_key(name), "evidence_class": evidence_class,
            "root": str(root), "selection": "latest saved plan draft per floor",
            "plans": latest_drafts(root, run=name, evidence_class=evidence_class),
        }
        if delivery_path.is_file() and delivered_source.is_file():
            group["legacy_delivery_path"] = str(delivery_path)
            group["legacy_delivery_sha256"] = sha256(delivery_path)
            group["legacy_delivered_candidate"] = delivery.get("candidate")
            group["legacy_saved_source_path"] = str(delivered_source)
            group["legacy_saved_source_sha256"] = sha256(delivered_source)
        groups.append(group)
    trials = []
    for name, root in TRIAL_RUNS:
        trials.append({
            "run": name, "case": case_key(name), "evidence_class": "real_reader_trial",
            "root": str(root), "selection": "last passed isolated trial per floor",
            "plans": passed_trial_drafts(root, run=name),
        })
    return {
        "schema": "q1_replay_manifest_v1",
        "model_requests": 0,
        "production_repairs_only": True,
        "round1_evidence": {
            name: {"path": str(HERE / "round1" / name), "sha256": sha256(HERE / "round1" / name)}
            for name in ("replay_report.json", "replay_notes.md", "itemized_changes.md")
        },
        "round2_evidence": {
            name: {"path": str(HERE / "round2" / name), "sha256": sha256(HERE / "round2" / name)}
            for name in ROUND2_EVIDENCE_NAMES
        },
        "groups": groups,
        "reader_trials": trials,
        "dev_dimension_fixtures": [
            {"run": run, "floor_id": floor, "chains": copy.deepcopy(chains)}
            for (run, floor), chains in DEV_DIMENSION_FIXTURES.items()
        ],
        "pipeline_dev_auxiliary_reference": {
            "path": str(ROLE_FIXTURE_DIMENSION_INPUTS),
            "sha256": sha256(ROLE_FIXTURE_DIMENSION_INPUTS),
            "schema": read_json(ROLE_FIXTURE_DIMENSION_INPUTS).get("schema"),
            "scope": (
                "new role-fixture dimension chains for end-to-end development probes; "
                "excluded from the historical five-floor H reader comparison"
            ),
            "gt_used": bool(read_json(ROLE_FIXTURE_DIMENSION_INPUTS).get("gt_used")),
        },
        "evaluation_implementation": {
            "score_role_answers": {"path": str(SCORER_PATH), "sha256": sha256(SCORER_PATH)},
            "three_case_evaluate": {
                "path": str(COMPARISON / "evaluate.py"), "sha256": sha256(COMPARISON / "evaluate.py")},
            "three_case_metrics": {
                "path": str(COMPARISON / "metrics.py"), "sha256": sha256(COMPARISON / "metrics.py")},
            "references": {
                key: {"path": str(reference_path(key)), "sha256": sha256(reference_path(key))}
                for key in ("sm21", "sm24", "sm25")
            },
        },
        "production_implementation": {
            name: {"path": str(ROOT / relative), "sha256": sha256(ROOT / relative)}
            for name, relative in {
                "regularization": "src/agent/geometry/plan_regularization.py",
                "ink_alignment": "src/agent/geometry/plan_ink_alignment.py",
                "dimension_alignment": "src/agent/geometry/plan_dimension_alignment.py",
                "plan_compiler": "src/agent/geometry/plan_partition.py",
                "plan_assembly": "src/agent/geometry/plan_assembly.py",
                "building_precision": "src/agent/geometry/building_precision.py",
                "source_bim": "src/agent/geometry/source_bim.py",
                "source_proposal": "src/agent/execution/source_proposal.py",
                "source_save_gate": "scripts/tool_scripts/bim_agent_regularization.py",
            }.items()
        },
        "forbidden_paths": [
            str(MAIN_ROOT / "AI_agent/archive/local_backup/merged"),
            r"D:\EnergyPlus-Agent-worktrees\runs-next",
            r"D:\EnergyPlus-Agent-worktrees\runs-cc",
        ],
    }


def tiers(values: Iterable[float]) -> dict[str, int]:
    spec = importlib.util.spec_from_file_location("q1_three_case_metrics", COMPARISON / "metrics.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load tier implementation from {COMPARISON / 'metrics.py'}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.tiers(values)


def load_scorer():
    spec = importlib.util.spec_from_file_location("q1_role_scorer", SCORER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load scorer {SCORER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def neutral_plan(plan: Mapping[str, Any], image_size: list[int], image_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from src.agent.geometry.plan_partition import compile_plan_partition
    proposal, metadata = compile_plan_partition(copy.deepcopy(dict(plan)), image_size=tuple(image_size), image_name=image_name)
    floor = proposal["geometry"]["floors"][0]
    floor_id = str(floor["name"])
    openings = []
    for item in metadata["opening_hosts"]:
        p1, p2 = item["p1_world_m"], item["p2_world_m"]
        if abs(p1[0] - p2[0]) <= 1e-8:
            axis, span, cross = "y", sorted([p1[1], p2[1]]), (p1[0] + p2[0]) / 2
        else:
            axis, span, cross = "x", sorted([p1[0], p2[0]]), (p1[1] + p2[1]) / 2
        openings.append({
            "id": item["opening_id"], "floor_id": floor_id, "kind": item["kind"],
            "axis": axis, "span_m": span, "cross_m": cross, "width_m": item["width_m"],
            "host_room_ids": list(item["space_ids"]), "exterior": bool(item["exterior"]),
        })
    row = {
        "floor_id": floor_id, "z_floor_m": float(floor["z_floor"]),
        "ceiling_height_m": float(floor["ceiling_height"]),
        "exterior_m": metadata["footprint"]["world_polygon_m"],
        "partitions_m": {"type": "MultiLineString", "coordinates": [p["world_points_m"] for p in metadata["partition_mapping"]]},
        "rooms": [{"id": c["id"], "name": None, "role": c.get("role"), "polygon_m": c["polygon"]} for c in floor["cells"]],
        "openings": openings,
    }
    semantics = {
        "rooms": len(row["rooms"]), "openings": len(openings),
        "doors": sum(item["kind"] == "door" for item in openings),
        "windows": sum(item["kind"] == "window" for item in openings),
        "room_ids": sorted(str(item["id"]) for item in row["rooms"]),
        "space_seed_ids": sorted(
            str(item["id"]) for item in plan.get("space_seeds", []) if item.get("id") is not None),
        "opening_kinds": sorted((item["id"], item["kind"]) for item in openings),
        "opening_hosts": sorted((item["id"], tuple(sorted(item["host_room_ids"]))) for item in openings),
        "door_connections": sorted((item["id"], tuple(sorted(item["host_room_ids"]))) for item in openings if item["kind"] == "door"),
    }
    return row, semantics


def score_plans(name: str, plans: list[dict[str, Any]]) -> dict[str, Any]:
    scorer = load_scorer()
    rows, semantics = [], {}
    for item in plans:
        row, counts = neutral_plan(item["plan"], item["image_size"], item["image_name"])
        normalized_floor = scorer.normalize_floor(row["floor_id"])
        row["floor_id"] = normalized_floor
        for opening in row["openings"]:
            opening["floor_id"] = normalized_floor
        rows.append(row)
        semantics[normalized_floor] = counts
    answer = {"schema_version": "role_answer_v1", "case": case_key(name),
              "coordinate_frame": "building_axis_world_m", "plan_questions": rows, "elevation_questions": []}
    reference = read_json(reference_path(name))
    submitted_floors = {row["floor_id"] for row in rows}
    reference["plan_questions"] = [row for row in reference["plan_questions"]
                                   if row["floor_id"] in submitted_floors]
    reference["elevation_questions"] = []
    raw = scorer.score(reference, answer)
    room_offsets, opening_offsets = [], []
    for floor in raw.get("floors", []):
        room_offsets += [m["boundary_hausdorff_m"] for m in floor.get("rooms", {}).get("matches", []) if isinstance(m.get("boundary_hausdorff_m"), (int, float))]
        opening_offsets += [m["max_endpoint_error_m"] for m in floor.get("openings", {}).get("comparisons", []) if isinstance(m.get("max_endpoint_error_m"), (int, float))]
    return {
        "floor_statuses": {row["floor_id"]: row["status"] for row in raw.get("floors", [])},
        "tiers_room_boundary": tiers(room_offsets),
        "tiers_opening_along_wall": tiers(opening_offsets),
        "room_offsets_m": sorted(round(value, 6) for value in room_offsets),
        "opening_offsets_m": sorted(round(value, 6) for value in opening_offsets),
        "semantics": semantics,
        "score": raw,
    }


def supported_call(function, first, **kwargs):
    accepted = inspect.signature(function).parameters
    return function(first, **{key: value for key, value in kwargs.items() if key in accepted})


def flatten_report(report: Mapping[str, Any]) -> dict[str, Any]:
    def gather(keys: set[str]) -> list[Any]:
        found = []
        def visit(value: Any, key: str | None = None):
            if key in keys and isinstance(value, list):
                found.extend(copy.deepcopy(value))
            if isinstance(value, Mapping):
                for child_key, child in value.items():
                    visit(child, str(child_key))
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(report)
        unique = []
        seen = set()
        for item in found:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique
    semantic_mappings = []
    def visit_mappings(value: Any, inherited_floor: str | None = None):
        if not isinstance(value, Mapping):
            return
        floor_id = str(value.get("floor_id") or inherited_floor or "")
        mapping = value.get("semantic_mapping")
        if isinstance(mapping, Mapping):
            semantic_mappings.append({"floor_id": floor_id, **copy.deepcopy(dict(mapping))})
        floor_reports = value.get("floor_reports")
        if isinstance(floor_reports, Mapping):
            for key, child in floor_reports.items():
                visit_mappings(child, str(key))
        for key, child in value.items():
            if key not in {"semantic_mapping", "floor_reports"} and isinstance(child, Mapping):
                visit_mappings(child, floor_id)
    visit_mappings(report)
    unique_mappings = []
    seen_mappings = set()
    for mapping in semantic_mappings:
        key = json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if key not in seen_mappings:
            seen_mappings.add(key)
            unique_mappings.append(mapping)
    return {
        "reported_changes": gather({"changes", "attempted_changes", "eliminated", "applied"}),
        "rejected": gather({"rejections", "rejected"}),
        "hard_constraints": gather({"hard_constraints", "violations"}),
        "preserved_ge_30cm": gather({"preserved_separations", "unchanged_legitimate_separations"}),
        "semantic_mappings": unique_mappings,
    }


def classify_items(report: Mapping[str, Any], *, delivered: bool, error: str | None = None) -> dict[str, Any]:
    items = flatten_report(report)
    changes = items.pop("reported_changes")
    items["applied_changes"] = changes if delivered else []
    items["attempted_changes_not_delivered"] = [] if delivered else changes
    items["eliminated"] = [
        item for item in items["applied_changes"]
        if isinstance(item, Mapping) and any(
            word in str(item.get("type") or item.get("action") or "").lower()
            for word in ("delete", "remove", "eliminate", "merge_duplicate")
        )
    ]
    items["exterior_alignment_changes"] = [
        item for item in items["applied_changes"]
        if isinstance(item, Mapping) and item.get("type") == "move_footprint_edge"
    ]
    items["attempted_exterior_alignment_changes_not_delivered"] = [
        item for item in items["attempted_changes_not_delivered"]
        if isinstance(item, Mapping) and item.get("type") == "move_footprint_edge"
    ]
    # Stack reports keep stage-B changes at the top level and stage-A changes
    # in floor_reports.  Use that production boundary rather than guessing from
    # basis labels such as existing_line, which are shared by several rules.
    top_level_changes = report.get("changes", []) if isinstance(report, Mapping) else []
    items["cross_storey_internal_wall_moves"] = [
        copy.deepcopy(dict(item)) for item in top_level_changes
        if (isinstance(report.get("floor_reports"), Mapping)
            and isinstance(item, Mapping) and item.get("type") == "move_wall_line")
    ] if delivered else []
    # One eliminated cross-storey overlap is one unique source/target edge pair.
    # Collinear source segments remain separate change records, per production audit.
    seen_edge_pairs = set()
    eliminated_edge_pairs = []
    invalid_edge_pair_changes = []
    for item in items["exterior_alignment_changes"]:
        if (not isinstance(item.get("source_edge_index"), int)
                or not isinstance(item.get("target_edge_index"), int)
                or not item.get("source_floor_id") or not item.get("target_floor_id")):
            invalid_edge_pair_changes.append(copy.deepcopy(dict(item)))
            continue
        key = (
            str(item.get("source_floor_id")), item.get("source_edge_index"),
            str(item.get("target_floor_id")), item.get("target_edge_index"),
        )
        if key not in seen_edge_pairs:
            seen_edge_pairs.add(key)
            eliminated_edge_pairs.append({
                "source_floor_id": item.get("source_floor_id"),
                "source_edge_index": item.get("source_edge_index"),
                "target_floor_id": item.get("target_floor_id"),
                "target_edge_index": item.get("target_edge_index"),
                "axis": item.get("axis"), "from_m": item.get("from_m"),
                "to_m": item.get("to_m"), "span_m": copy.deepcopy(item.get("span_m")),
                "movement_m": item.get("movement_m"), "basis": item.get("basis"),
            })
    items["eliminated_cross_storey_footprint_overlaps"] = eliminated_edge_pairs
    items["invalid_exterior_alignment_changes_not_counted"] = invalid_edge_pair_changes
    if not delivered and error and not any(
            row.get("type") == "production_runtime_failure" for row in items["rejected"]
            if isinstance(row, Mapping)):
        items["rejected"].append({"type": "production_runtime_failure", "error": error})
    return items


def semantic_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, bool]]:
    return {
        floor: {
            key: after["semantics"].get(floor, {}).get(key) != values.get(key)
            for key in ("rooms", "openings", "doors", "windows", "room_ids", "space_seed_ids",
                        "opening_kinds", "opening_hosts", "door_connections")
        }
        for floor, values in before["semantics"].items()
    }


def _ids(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, Mapping):
        result = set()
        for key in ("id", "opening_id", "seed_id", "removed_id", "merged_id"):
            if value.get(key) is not None:
                result.add(str(value[key]))
        return result
    if isinstance(value, list):
        return set().union(*(_ids(item) for item in value)) if value else set()
    return set()


def declared_merge_effects(changes: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Read allowed narrow-strip effects from the production audit, never infer them from GT."""
    removed_seeds, removed_openings, kept_openings, merge_items = set(), set(), set(), []
    for change in changes:
        kind = str(change.get("type") or change.get("action") or "").lower()
        if kind not in {
                "merge_duplicate_wall_lines", "merge_duplicate_wall_into_fixed_footprint",
                "remove_narrow_strip_space_seeds", "move_openings_to_merged_wall",
                "retain_openings_on_merged_wall", "merge_overlapping_openings",
                "remove_collapsed_wall_step"}:
            continue
        if kind.startswith("merge_duplicate_wall"):
            merge_items.append(copy.deepcopy(dict(change)))
        for key, value in change.items():
            name = str(key).lower()
            if "seed" in name and any(word in name for word in ("remove", "delete", "drop", "merged")):
                removed_seeds.update(_ids(value))
            if "opening" in name and any(word in name for word in ("remove", "delete", "drop", "merged", "absorbed")):
                removed_openings.update(_ids(value))
            if "opening" in name and any(word in name for word in ("keep", "retain", "surviv", "target")):
                kept_openings.update(_ids(value))
    removed_openings.difference_update(kept_openings)
    return {
        "merge_items": merge_items,
        "removed_space_seed_ids": sorted(removed_seeds),
        "removed_opening_ids": sorted(removed_openings),
        "kept_opening_ids": sorted(kept_openings),
    }


def semantic_audit(
        before: Mapping[str, Any], after: Mapping[str, Any],
        applied_changes: list[Mapping[str, Any]],
        semantic_mappings: list[Mapping[str, Any]]) -> dict[str, Any]:
    scorer = load_scorer()
    effects_by_floor: dict[str, list[Mapping[str, Any]]] = {}
    for change in applied_changes:
        raw_floor = str(change.get("floor_id") or "")
        floor = scorer.normalize_floor(raw_floor) if raw_floor else ""
        effects_by_floor.setdefault(floor, []).append(change)
    mappings_by_floor: dict[str, list[Mapping[str, Any]]] = {}
    for mapping in semantic_mappings:
        raw_floor = str(mapping.get("floor_id") or "")
        floor = scorer.normalize_floor(raw_floor) if raw_floor else ""
        mappings_by_floor.setdefault(floor, []).append(mapping)
    floors = {}
    for floor_id, old in before["semantics"].items():
        new = after["semantics"].get(floor_id, {})
        floor_changes = list(effects_by_floor.get(floor_id, []))
        if len(before["semantics"]) == 1:
            floor_changes.extend(effects_by_floor.get("", []))
        effects = declared_merge_effects(floor_changes)
        floor_mappings = list(mappings_by_floor.get(floor_id, []))
        if len(before["semantics"]) == 1:
            floor_mappings.extend(mappings_by_floor.get("", []))
        mapped_openings = [row for mapping in floor_mappings
                           for row in mapping.get("opening_id_map", [])]
        mapped_removed_seeds = {
            identity for mapping in floor_mappings
            for identity in _ids(mapping.get("removed_space_seeds", []))
        }
        mapped_eliminated_spaces = [row for mapping in floor_mappings
                                    for row in mapping.get("eliminated_strip_spaces", [])]
        old_kinds, new_kinds = dict(old.get("opening_kinds", [])), dict(new.get("opening_kinds", []))
        old_hosts, new_hosts = dict(old.get("opening_hosts", [])), dict(new.get("opening_hosts", []))
        old_doors, new_doors = dict(old.get("door_connections", [])), dict(new.get("door_connections", []))
        missing_openings = set(old_kinds) - set(new_kinds)
        added_openings = set(new_kinds) - set(old_kinds)
        common_kind_ids = set(old_kinds) & set(new_kinds)
        changed_kinds = sorted(opening_id for opening_id in common_kind_ids
                               if old_kinds[opening_id] != new_kinds[opening_id])
        missing_rooms = set(old.get("room_ids", [])) - set(new.get("room_ids", []))
        added_rooms = set(new.get("room_ids", [])) - set(old.get("room_ids", []))
        missing_seeds = set(old.get("space_seed_ids", [])) - set(new.get("space_seed_ids", []))
        added_seeds = set(new.get("space_seed_ids", [])) - set(old.get("space_seed_ids", []))
        common_openings = set(old_hosts) & set(new_hosts)
        common_doors = set(old_doors) & set(new_doors)
        changed_hosts = sorted(
            opening_id for opening_id in common_openings
            if old_hosts[opening_id] != new_hosts[opening_id])
        changed_connections = sorted(
            opening_id for opening_id in common_doors
            if old_doors[opening_id] != new_doors[opening_id])
        valid_mapping_rows, invalid_mapping_rows = [], []
        for row in mapped_openings:
            old_id, new_id = str(row.get("old_opening_id")), str(row.get("surviving_opening_id"))
            valid = (
                old_id in old_hosts and new_id in new_hosts
                and sorted(map(str, row.get("before_hosts") or [])) == sorted(map(str, old_hosts[old_id]))
                and sorted(map(str, row.get("after_hosts") or [])) == sorted(map(str, new_hosts[new_id]))
                and row.get("before_connection") is not None
                and row.get("after_connection") is not None
            )
            (valid_mapping_rows if valid else invalid_mapping_rows).append(row)
        declared_openings = set(effects["removed_opening_ids"])
        declared_openings.update(
            str(row.get("old_opening_id")) for row in valid_mapping_rows
            if row.get("old_opening_id") != row.get("surviving_opening_id"))
        declared_seeds = set(effects["removed_space_seed_ids"]) | mapped_removed_seeds
        allowed_host_changes = {
            str(row.get("old_opening_id")) for row in valid_mapping_rows
            if (row.get("old_opening_id") == row.get("surviving_opening_id")
                and row.get("before_hosts") is not None and row.get("after_hosts") is not None
                and row.get("after_connection") is not None)
        }
        room_delta = int(new.get("rooms", 0)) - int(old.get("rooms", 0))
        expected_room_delta = -len(mapped_eliminated_spaces)
        mapping_counts_valid = all(
            (mapping.get("space_count_before") is None
             or (mapping.get("space_count_before") == old.get("rooms")
                 and mapping.get("space_count_after") == new.get("rooms")
                 and mapping.get("expected_space_count_after") == new.get("rooms")))
            for mapping in floor_mappings)
        checks = {
            "no_added_openings": not added_openings,
            "removed_openings_declared": missing_openings <= declared_openings,
            "surviving_opening_kinds_unchanged": not changed_kinds,
            "surviving_opening_host_changes_explicitly_mapped":
                set(changed_hosts) <= allowed_host_changes,
            "surviving_door_connection_changes_explicitly_mapped":
                set(changed_connections) <= allowed_host_changes,
            "no_added_space_seeds": not added_seeds,
            "removed_space_seeds_declared": missing_seeds <= declared_seeds,
            "room_count_change_matches_eliminated_strip_spaces": room_delta == expected_room_delta,
            "production_semantic_mapping_counts_consistent": mapping_counts_valid,
            "production_opening_mapping_rows_match_compiled_before_after": not invalid_mapping_rows,
        }
        floors[floor_id] = {
            "status": "pass" if all(checks.values()) else "rejected",
            "checks": checks,
            "room_count_before": old.get("rooms"), "room_count_after": new.get("rooms"),
            "room_count_delta": room_delta,
            "removed_space_seed_ids": sorted(missing_seeds),
            "declared_removed_space_seed_ids": effects["removed_space_seed_ids"],
            "removed_opening_ids": sorted(missing_openings),
            "declared_removed_opening_ids": effects["removed_opening_ids"],
            "added_opening_ids": sorted(added_openings),
            "changed_surviving_opening_kinds": changed_kinds,
            "removed_room_ids": sorted(missing_rooms), "added_room_ids": sorted(added_rooms),
            "changed_surviving_opening_hosts": changed_hosts,
            "changed_surviving_door_connections": changed_connections,
            "allowed_merge_items": effects["merge_items"],
            "production_semantic_mappings": floor_mappings,
            "invalid_production_opening_mapping_rows": invalid_mapping_rows,
        }
    return {"status": "pass" if all(row["status"] == "pass" for row in floors.values()) else "rejected",
            "floors": floors}


def separation_audit(items: Mapping[str, Any]) -> dict[str, Any]:
    rows = [row for row in items.get("preserved_ge_30cm", []) if isinstance(row, Mapping)]
    dropped = []
    for row in rows:
        lines = row.get("lines", [])
        floor_ids = {str(line.get("floor_id")) for line in lines
                     if isinstance(line, Mapping) and line.get("floor_id") is not None}
        same_floor = len(floor_ids) <= 1
        distance = row.get("after_distance_m")
        overlap = row.get("after_overlap_m")
        if (same_floor and isinstance(distance, (int, float)) and isinstance(overlap, (int, float))
                and distance < 0.30 - 1e-9 and overlap > 1e-9):
            dropped.append(copy.deepcopy(dict(row)))
    return {
        "status": "pass" if not dropped else "rejected",
        "original_ge_30cm_pairs": len(rows),
        "unchanged_pairs": sum(row.get("unchanged") is True for row in rows),
        "changed_but_still_valid_pairs": len(rows) - sum(row.get("unchanged") is True for row in rows) - len(dropped),
        "new_same_floor_sub_30cm_overlaps": dropped,
    }


def _dimension_edge_evidence(plan: Mapping[str, Any], edge: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return explicit F dimension references on one footprint coordinate."""
    rows = (plan.get("regularization_inputs") or {}).get("coordinate_references", [])
    matches = []
    for row in rows if isinstance(rows, list) else []:
        if (isinstance(row, Mapping) and row.get("basis") == "dimension"
                and row.get("axis") == edge.get("axis")
                and isinstance(row.get("value_m"), (int, float))
                and abs(float(row["value_m"]) - float(edge["coordinate_m"])) <= 1e-6):
            matches.append(copy.deepcopy(dict(row)))
    return matches


def exterior_alignment_audit(
        run: str, before_rows: list[Mapping[str, Any]], after_rows: list[Mapping[str, Any]],
        changes: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Check the round-3 cross-storey footprint policy against literal rings."""
    from src.agent.geometry import plan_regularization as production

    before_by_floor = {str(row["floor_id"]): row for row in before_rows}
    after_by_floor = {str(row["floor_id"]): row for row in after_rows}
    z_by_floor = {
        floor: float(row.get("z_floor", row["plan"].get("z_floor", 0.0)) or 0.0)
        for floor, row in before_by_floor.items()
    }
    ordered_floors = sorted(before_by_floor, key=lambda floor: (z_by_floor[floor], floor))
    rank_by_floor = {floor: index for index, floor in enumerate(ordered_floors)}

    def edges(row: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
        calibration = production._calibration(row["plan"], tuple(row["image_size"]))
        return {
            int(edge["segment_index"]): edge
            for edge in production._footprint_segments(row["plan"], calibration)
        }

    before_edges = {floor: edges(row) for floor, row in before_by_floor.items()}
    after_edges = {floor: edges(row) for floor, row in after_by_floor.items()}
    audited = []
    for change in changes:
        if change.get("type") != "move_footprint_edge":
            continue
        source_floor, target_floor = str(change.get("source_floor_id")), str(change.get("target_floor_id"))
        source_index, target_index = change.get("source_edge_index"), change.get("target_edge_index")
        source_before = (before_edges.get(source_floor, {}).get(source_index)
                         if isinstance(source_index, int) else None)
        target_before = (before_edges.get(target_floor, {}).get(target_index)
                         if isinstance(target_index, int) else None)
        source_after = (after_edges.get(source_floor, {}).get(source_index)
                        if isinstance(source_index, int) else None)
        target_after = (after_edges.get(target_floor, {}).get(target_index)
                        if isinstance(target_index, int) else None)
        source_report, target_report = change.get("source") or {}, change.get("target") or {}
        to_m, from_m = change.get("to_m"), change.get("from_m")
        numeric_coordinates = isinstance(to_m, (int, float)) and isinstance(from_m, (int, float))
        source_evidence = (_dimension_edge_evidence(before_by_floor[source_floor]["plan"], source_before)
                           if source_before is not None and source_floor in before_by_floor else [])
        target_evidence = (_dimension_edge_evidence(before_by_floor[target_floor]["plan"], target_before)
                           if target_before is not None and target_floor in before_by_floor else [])
        source_z, target_z = z_by_floor.get(source_floor), z_by_floor.get(target_floor)
        distinct_z = (source_z is not None and target_z is not None
                      and abs(source_z - target_z) > 1e-9)
        source_is_upper = (
            source_z > target_z + 1e-9 if distinct_z
            else rank_by_floor.get(source_floor, -1) > rank_by_floor.get(target_floor, -1)
        )
        source_is_lower = (
            source_z < target_z - 1e-9 if distinct_z
            else rank_by_floor.get(source_floor, -1) < rank_by_floor.get(target_floor, -1)
        )
        upper_to_lower = source_is_upper
        dimension_supported_reverse = (
            source_is_lower and bool(target_evidence) and not source_evidence
        )
        overlap_before = 0.0
        if source_before is not None and target_before is not None:
            overlap_before = max(
                0.0,
                min(source_before["span_m"][1], target_before["span_m"][1])
                - max(source_before["span_m"][0], target_before["span_m"][0]),
            )
        checks = {
            "source_edge_index_is_valid": source_before is not None,
            "target_edge_index_is_valid": target_before is not None,
            "different_storeys": source_floor in before_by_floor and target_floor in before_by_floor
                                  and source_floor != target_floor,
            "source_report_names_indexed_footprint":
                source_report.get("partition_id") == f"footprint[{source_index}]"
                and source_report.get("floor_id") == source_floor,
            "target_report_names_indexed_footprint":
                target_report.get("partition_id") == f"footprint[{target_index}]"
                and target_report.get("floor_id") == target_floor,
            "source_and_target_edges_overlap_before": overlap_before > 1e-9,
            "movement_is_strictly_below_30cm":
                isinstance(change.get("movement_m"), (int, float))
                and 0.0 < float(change["movement_m"]) < 0.30 - 1e-9,
            "direction_is_upper_to_lower_or_dimension_supported_reverse":
                upper_to_lower or dimension_supported_reverse,
            "historical_unannotated_target_direction_is_upper_to_lower":
                run not in ROUND3_EXPECTED_EXTERIOR_RUNS or upper_to_lower,
        }
        if source_before is not None and numeric_coordinates:
            checks["source_axis_and_coordinate_match_input_edge"] = (
                source_before["axis"] == change.get("axis")
                and abs(float(source_before["coordinate_m"]) - float(from_m)) <= 1e-6
            )
        else:
            checks["source_axis_and_coordinate_match_input_edge"] = False
        if target_before is not None and numeric_coordinates:
            checks["target_axis_and_coordinate_match_input_edge"] = (
                target_before["axis"] == change.get("axis")
                and abs(float(target_before["coordinate_m"]) - float(to_m)) <= 1e-6
            )
        else:
            checks["target_axis_and_coordinate_match_input_edge"] = False
        checks["source_edge_lands_on_target_coordinate"] = bool(
            source_after is not None and isinstance(to_m, (int, float))
            and source_after["axis"] == change.get("axis")
            and abs(float(source_after["coordinate_m"]) - float(to_m)) <= 1e-6
        )
        checks["target_edge_remains_at_target_coordinate"] = bool(
            target_after is not None and isinstance(to_m, (int, float))
            and target_after["axis"] == change.get("axis")
            and abs(float(target_after["coordinate_m"]) - float(to_m)) <= 1e-6
        )
        audited.append({
            "source_floor_id": source_floor, "source_edge_index": source_index,
            "target_floor_id": target_floor, "target_edge_index": target_index,
            "axis": change.get("axis"), "from_m": from_m, "to_m": to_m,
            "movement_m": change.get("movement_m"), "basis": change.get("basis"),
            "source_z_floor": source_z, "target_z_floor": target_z,
            "source_storey_rank": rank_by_floor.get(source_floor),
            "target_storey_rank": rank_by_floor.get(target_floor),
            "storey_order_basis": "z_floor" if distinct_z else "z_floor_floor_id_tiebreak",
            "source_dimension_evidence": source_evidence,
            "target_dimension_evidence": target_evidence,
            "overlap_before_m": round(overlap_before, 9),
            "checks": checks, "status": "pass" if all(checks.values()) else "rejected",
        })
    expected = run in ROUND3_EXPECTED_EXTERIOR_RUNS
    return {
        "status": ("pass" if all(row["status"] == "pass" for row in audited)
                   and (not expected or bool(audited)) else "rejected"),
        "expected_round3_exterior_alignment": expected,
        "change_count": len(audited),
        "valid_unique_edge_pairs": len({
            (row["source_floor_id"], row["source_edge_index"],
             row["target_floor_id"], row["target_edge_index"])
            for row in audited if row["status"] == "pass"
        }),
        "invalid_changes": [row for row in audited if row["status"] != "pass"],
        "changes": audited,
    }


def _precision_for_consistency(save_gate: Mapping[str, Any]) -> dict[str, Any]:
    value = (save_gate.get("building_precision")
             or save_gate.get("legacy_existing_source_precision") or {})
    result = copy.deepcopy(dict(value)) if isinstance(value, Mapping) else {}
    result.pop("source_model_sha256", None)
    return result


def round2_consistency_audit(
        run: str, after: Mapping[str, Any], save_gate: Mapping[str, Any]) -> dict[str, Any]:
    """Ensure the eleven non-target histories retain round-2 semantics and precision."""
    if run in ROUND3_EXPECTED_EXTERIOR_RUNS:
        return {"status": "not_applicable_round3_target"}
    if not ROUND2_REPORT.is_file():
        return {"status": "rejected", "reason": "round2 replay report is missing"}
    old_report = read_json(ROUND2_REPORT)
    old = next((row for row in old_report.get("regularization_replay", [])
                if row.get("run") == run), None)
    if not isinstance(old, Mapping) or not isinstance(old.get("after"), Mapping):
        return {"status": "rejected", "reason": "round2 delivered after result is missing"}
    metric_keys = (
        "floor_statuses", "tiers_room_boundary", "tiers_opening_along_wall",
        "room_offsets_m", "opening_offsets_m",
    )
    old_metrics = {key: copy.deepcopy(old["after"].get(key)) for key in metric_keys}
    new_metrics = {key: copy.deepcopy(after.get(key)) for key in metric_keys}
    old_semantics, new_semantics = old["after"].get("semantics"), after.get("semantics")
    old_precision = _precision_for_consistency(old.get("source_save_gate") or {})
    new_precision = _precision_for_consistency(save_gate)
    old_semantics_sha, new_semantics_sha = canonical_sha(old_semantics), canonical_sha(new_semantics)
    old_metrics_sha, new_metrics_sha = canonical_sha(old_metrics), canonical_sha(new_metrics)
    old_precision_sha, new_precision_sha = canonical_sha(old_precision), canonical_sha(new_precision)
    checks = {
        "after_semantics_equal_round2": new_semantics_sha == old_semantics_sha,
        "after_evaluation_metrics_equal_round2": new_metrics_sha == old_metrics_sha,
        "source_precision_equal_round2_ignoring_source_digest": new_precision_sha == old_precision_sha,
    }
    return {
        "status": "pass" if all(checks.values()) else "rejected",
        "round2_report_path": str(ROUND2_REPORT),
        "round2_report_sha256": sha256(ROUND2_REPORT),
        "checks": checks,
        "round2_semantics_sha256": old_semantics_sha,
        "current_semantics_sha256": new_semantics_sha,
        "round2_metrics_sha256": old_metrics_sha,
        "current_metrics_sha256": new_metrics_sha,
        "round2_precision_sha256": old_precision_sha,
        "current_precision_sha256": new_precision_sha,
    }


def cross_storey_near_line_audit(
        input_validation: Mapping[str, Any], report: Mapping[str, Any]) -> dict[str, Any]:
    """Count production-detected unresolved cross-storey near-line pairs before/after."""
    before = [
        copy.deepcopy(dict(row)) for row in input_validation.get("violations", [])
        if isinstance(row, Mapping) and row.get("type") == "storey_wall_offset_under_0_30m"
    ]
    hard = report.get("hard_constraints") or {}
    after = [
        copy.deepcopy(dict(row)) for row in hard.get("violations", [])
        if isinstance(row, Mapping) and row.get("type") == "storey_wall_offset_under_0_30m"
    ] if isinstance(hard, Mapping) else []
    return {
        "status": "pass" if not after else "rejected",
        "definition": "production hard-constraint storey_wall_offset_under_0_30m pairs",
        "before_unaligned_near_line_pairs": len(before),
        "after_unaligned_near_line_pairs": len(after),
        "reduced_pairs": len(before) - len(after),
        "before_items": before,
        "after_items": after,
    }


def tier_label(value: float) -> str:
    return "<=5cm" if value <= 0.05 + 1e-9 else "5-10cm" if value <= 0.10 + 1e-9 else "10-30cm" if value <= 0.30 + 1e-9 else ">30cm"


def opening_tier_regressions(
        before_score: Mapping[str, Any], after_score: Mapping[str, Any],
        before_plan: Mapping[str, Any], after_plan: Mapping[str, Any],
        ink_report: Mapping[str, Any], *, stage: str) -> list[dict[str, Any]]:
    order = {"<=5cm": 0, "5-10cm": 1, "10-30cm": 2, ">30cm": 3}
    before_rows = {
        row["answer_id"]: row
        for floor in before_score["score"].get("floors", [])
        for row in floor.get("openings", {}).get("comparisons", [])
    }
    after_rows = {
        row["answer_id"]: row
        for floor in after_score["score"].get("floors", [])
        for row in floor.get("openings", {}).get("comparisons", [])
    }
    before_openings = {row.get("id"): row for row in before_plan.get("openings", [])}
    after_openings = {row.get("id"): row for row in after_plan.get("openings", [])}
    host_items: dict[str, list[dict[str, Any]]] = {}
    opening_items: dict[str, list[dict[str, Any]]] = {}
    for item in ink_report.get("items", []):
        object_id = str(item.get("object") or "")
        if object_id.startswith("opening:"):
            opening_items.setdefault(object_id.split(":", 1)[1], []).append(copy.deepcopy(item))
        for opening_id in (item.get("moved_with_wall") or {}).get("openings", []):
            host_items.setdefault(opening_id, []).append({
                key: copy.deepcopy(item.get(key)) for key in
                ("object", "kind", "axis", "action", "declared_pixel", "aligned_pixel",
                 "movement_pixels", "movement_m")
            })
    regressions = []
    for opening_id, before in before_rows.items():
        after = after_rows.get(opening_id)
        if after is None:
            continue
        before_tier = tier_label(float(before["max_endpoint_error_m"]))
        after_tier = tier_label(float(after["max_endpoint_error_m"]))
        if order[after_tier] <= order[before_tier]:
            continue
        regressions.append({
            "stage": stage, "opening_id": opening_id, "kind": before.get("kind"),
            "reference_id_evaluation_only": before.get("reference_id"),
            "before_error_m": round(float(before["max_endpoint_error_m"]), 6),
            "after_error_m": round(float(after["max_endpoint_error_m"]), 6),
            "before_tier": before_tier, "after_tier": after_tier,
            "before_pixels": {
                key: copy.deepcopy(before_openings.get(opening_id, {}).get(key)) for key in ("p1", "p2")},
            "after_pixels": {
                key: copy.deepcopy(after_openings.get(opening_id, {}).get(key)) for key in ("p1", "p2")},
            "host_wall_alignment_items": host_items.get(opening_id, []),
            "opening_alignment_items": opening_items.get(opening_id, []),
            "ink_rejections": copy.deepcopy(ink_report.get("rejections", [])),
        })
    return regressions


def source_save_gate(plans: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Run the read-only production source materialisation and precision gate."""
    from src.agent.correction.schema import FootprintRing
    from src.agent.execution.source_proposal import _validate_proposal, ensure_corrected_geometry
    from src.agent.geometry.building_precision import precision_report
    from src.agent.geometry.input_scale import check_geometry_scale
    from src.agent.geometry.plan_assembly import assemble_plan_proposals
    from src.agent.geometry.plan_partition import compile_plan_partition
    from src.agent.geometry.source_bim import build_source_bim

    placements = [{
        "floor_id": row["floor_id"],
        "z_floor": row.get("z_floor", row["plan"].get("z_floor")),
        "height": row.get("height", row["plan"].get("ceiling_height")),
    } for row in plans]
    try:
        compiled = []
        for row in plans:
            proposal, _ = compile_plan_partition(
                row["plan"], image_size=tuple(row["image_size"]), image_name=row["image_name"])
            compiled.append({
                "proposal": proposal,
                "floor_id": row["floor_id"],
                "z_floor": row.get("z_floor", row["plan"].get("z_floor")),
                "source_ref": row["plan_path"],
                **({"height": row["height"]} if row.get("height") is not None else {}),
            })
        proposal = (assemble_plan_proposals(compiled) if len(compiled) > 1
                    else compiled[0]["proposal"])
        geometry, _, _, enclosure = _validate_proposal(proposal)
        corrected = ensure_corrected_geometry(copy.deepcopy(geometry))
        for floor in corrected.floors:
            footprint = getattr(floor, "footprint", None)
            if isinstance(footprint, dict):
                floor.footprint = FootprintRing.model_validate(footprint)
        check_geometry_scale(corrected.model_dump(mode="json"))
        source = build_source_bim(
            corrected, capability_profile="orthogonal_polygon",
            enclosure_declaration=enclosure)
        precision = precision_report(source)
    except (ValueError, TypeError, KeyError) as error:
        return {
            "status": "rejected", "stage": "source_materialization",
            "error": f"{type(error).__name__}: {error}", "building_precision": None,
            "assembly_placements": placements,
        }
    return {
        "status": "pass" if not precision.get("items") else "rejected",
        "stage": "production_source_hard_constraints",
        "source_model_sha256": source.get("source_model_sha256"),
        "building_precision": precision,
        "assembly_placements": placements,
    }


def legacy_source_gate_fallback(
        group: Mapping[str, Any], report: Mapping[str, Any],
        save_gate: Mapping[str, Any]) -> dict[str, Any]:
    """Classify an unchanged historical enum incompatibility without bypassing it."""
    if (group.get("evidence_class") != "legal_replay_claude_code"
            or save_gate.get("stage") != "source_materialization"
            or "room_types catalog" not in str(save_gate.get("error"))
            or flatten_report(report)["reported_changes"]
            or not group.get("legacy_saved_source_path")):
        return copy.deepcopy(dict(save_gate))
    from src.agent.geometry.building_precision import precision_report
    source_path = Path(str(group["legacy_saved_source_path"]))
    legacy_precision = precision_report(read_json(source_path))
    return {
        **copy.deepcopy(dict(save_gate)),
        "status": ("legacy_input_incompatible" if not legacy_precision.get("items")
                   else "rejected"),
        "current_source_save_status": "rejected",
        "compatibility_reason": "historical room enum is not accepted by the current catalog",
        "legacy_saved_source_path": str(source_path),
        "legacy_saved_source_sha256": sha256(source_path),
        "legacy_existing_source_precision": legacy_precision,
    }


def regularize_group(group: Mapping[str, Any]) -> dict[str, Any]:
    from src.agent.geometry import plan_regularization as production
    plans = [copy.deepcopy(row) for row in group["plans"]]
    floor_ids = [str(row["floor_id"]) for row in plans]
    before = score_plans(group["run"], plans)
    report: Mapping[str, Any] = {}
    after_rows: list[dict[str, Any]] = []
    stack_items = [
        {
            "plan": row["plan"], "image_size": tuple(row["image_size"]),
            "image_name": row["image_name"], "floor_id": row["floor_id"],
            "z_floor": row["plan"].get("z_floor"), "source_ref": row["plan_path"],
        }
        for row in plans
    ]
    if len(plans) > 1:
        input_validation = supported_call(
            production.validate_regularized_plan_stack, copy.deepcopy(stack_items),
            rule_version=RULE_VERSION,
        )
    else:
        input_validation = supported_call(
            production.validate_regularized_plan, copy.deepcopy(plans[0]["plan"]),
            image_size=tuple(plans[0]["image_size"]), image_name=plans[0]["image_name"],
            rule_version=RULE_VERSION,
        )
    try:
        if len(plans) > 1:
            output, report = supported_call(
                production.regularize_plan_stack, stack_items, rule_version=RULE_VERSION)
            supported_call(production.enforce_regularized_plan_stack, output, rule_version=RULE_VERSION)
            for old, item in zip(plans, output, strict=True):
                row = copy.deepcopy(old)
                row["plan"] = item.get("plan") or item.get("regularized_plan")
                row["z_floor"] = item["z_floor"]
                if item.get("height") is not None:
                    row["height"] = item["height"]
                after_rows.append(row)
        else:
            old = plans[0]
            new_plan, report = supported_call(
                production.regularize_plan, old["plan"], image_size=tuple(old["image_size"]),
                image_name=old["image_name"], rule_version=RULE_VERSION,
            )
            supported_call(
                production.enforce_regularized_plan, new_plan, image_size=tuple(old["image_size"]),
                image_name=old["image_name"], rule_version=RULE_VERSION,
            )
            row = copy.deepcopy(old); row["plan"] = new_plan; after_rows = [row]
    except Exception as error:
        failure = getattr(error, "report", None)
        if isinstance(failure, Mapping):
            report = failure
        error_text = f"{type(error).__name__}: {error}"
        diagnostic_report = report if report else input_validation
        return {
            "run": group["run"], "case": group["case"], "evidence_class": group["evidence_class"],
            "status": "rejected_no_deliverable_after_metrics", "before": before,
            "after": None, "after_metrics_unavailable": True,
            "error": error_text, "report": report, "input_validation": input_validation,
            "items": classify_items(
                diagnostic_report, delivered=False, error=error_text if not report else None),
            "floor_stage_outcomes": independent_floor_stage_outcomes(
                plans, whole_building_delivery_status="rejected_no_deliverable"),
        }
    save_gate = legacy_source_gate_fallback(group, report, source_save_gate(after_rows))
    if save_gate["status"] not in {"pass", "legacy_input_incompatible"}:
        precision = save_gate.get("building_precision") or {}
        source_rejections = (copy.deepcopy(precision.get("items", []))
                             if isinstance(precision, Mapping) else [])
        if not source_rejections:
            source_rejections = [{
                "type": "source_materialization_failed", "error": save_gate.get("error"),
            }]
        diagnostic_report = {
            "status": "rejected", "regularization_report": report,
            "source_save_gate": {
                "changes": [], "rejections": source_rejections,
                "hard_constraints": precision,
            },
        }
        error_text = (
            "SourceHardConstraintError: production source save gate rejected the "
            "regularized proposal")
        return {
            "run": group["run"], "case": group["case"],
            "evidence_class": group["evidence_class"],
            "status": "rejected_no_deliverable_after_metrics", "before": before,
            "after": None, "after_metrics_unavailable": True,
            "error": error_text, "report": report, "input_validation": input_validation,
            "source_save_gate": save_gate,
            "items": classify_items(diagnostic_report, delivered=False),
            "floor_stage_outcomes": independent_floor_stage_outcomes(
                plans, whole_building_delivery_status="rejected_no_deliverable"),
        }
    try:
        after = score_plans(group["run"], after_rows)
    except Exception as error:
        error_text = f"post_regularization_compile: {type(error).__name__}: {error}"
        return {
            "run": group["run"], "case": group["case"], "evidence_class": group["evidence_class"],
            "status": "rejected_no_deliverable_after_metrics", "before": before,
            "after": None, "after_metrics_unavailable": True,
            "error": error_text,
            "report": report, "input_validation": input_validation,
            "source_save_gate": save_gate,
            "items": classify_items(report, delivered=False, error=error_text),
            "floor_stage_outcomes": independent_floor_stage_outcomes(
                plans, whole_building_delivery_status="rejected_no_deliverable"),
        }
    final_items = classify_items(report, delivered=True)
    semantics = semantic_audit(
        before, after, final_items["applied_changes"], final_items["semantic_mappings"])
    separations = separation_audit(final_items)
    exterior = exterior_alignment_audit(
        group["run"], plans, after_rows, final_items["applied_changes"])
    round2_consistency = round2_consistency_audit(
        group["run"], after, save_gate)
    cross_storey_near_lines = cross_storey_near_line_audit(input_validation, report)
    verification_status = (
        "pass" if (semantics["status"] == "pass"
                   and separations["status"] == "pass"
                   and exterior["status"] == "pass"
                   and cross_storey_near_lines["status"] == "pass"
                   and round2_consistency["status"] in {
                       "pass", "not_applicable_round3_target"})
        else "rejected"
    )
    if verification_status != "pass":
        result_status = "verification_failed_with_deliverable"
    elif save_gate["status"] == "legacy_input_incompatible":
        result_status = "legacy_geometric_pass_source_save_incompatible"
    else:
        result_status = "regularized"
    return {
        "run": group["run"], "case": group["case"], "evidence_class": group["evidence_class"],
        "status": result_status,
        "verification_status": verification_status, "before": before, "after": after,
        "after_metrics_unavailable": False, "report": report,
        "after_metrics_delivery_eligible": result_status == "regularized",
        "input_validation": input_validation,
        "source_save_gate": save_gate,
        "items": final_items,
        "semantic_delta": semantic_delta(before, after),
        "semantic_audit": semantics,
        "separation_audit": separations,
        "exterior_alignment_audit": exterior,
        "cross_storey_near_line_audit": cross_storey_near_lines,
        "round2_consistency_audit": round2_consistency,
        "floor_stage_outcomes": independent_floor_stage_outcomes(
            plans,
            whole_building_delivery_status=(
                "delivered" if result_status == "regularized" else result_status),
        ),
    }


def reader_replay(group: Mapping[str, Any]) -> dict[str, Any]:
    from src.agent.geometry.plan_ink_alignment import align_plan_to_ink
    try:
        from src.agent.geometry.plan_dimension_alignment import align_plan_to_dimensions
    except ImportError:
        align_plan_to_dimensions = None
    rows = []
    for item in group["plans"]:
        before = score_plans(group["run"], [item])
        result = {"trial_run": group["run"], "floor_id": item["floor_id"],
                  "before": before, "ink_after": None,
                  "ink_report": {}, "ink_status": None, "dimension": None,
                  "opening_tier_regressions": []}
        try:
            with Image.open(item["image_path"]) as image:
                ink_plan, ink_report = align_plan_to_ink(
                    image, copy.deepcopy(item["plan"]), search_world_m=0.30
                )
            result["ink_report"] = ink_report
            ink_item = copy.deepcopy(item); ink_item["plan"] = ink_plan
            result["ink_after"] = score_plans(group["run"], [ink_item])
            result["ink_status"] = "deliverable"
            result["ink_semantic_delta"] = semantic_delta(before, result["ink_after"])
            result["opening_tier_regressions"] = opening_tier_regressions(
                before, result["ink_after"], item["plan"], ink_plan, ink_report, stage="ink")
        except Exception as error:
            failure = getattr(error, "report", None)
            if isinstance(failure, Mapping):
                result["ink_report"] = failure
            result["ink_status"] = "rejected_no_deliverable_after_metrics"
            result["ink_error"] = f"{type(error).__name__}: {error}"
            result["after_metrics_unavailable"] = True
            fixture = DEV_DIMENSION_FIXTURES.get((group["run"], item["floor_id"]))
            if fixture:
                result["dimension"] = {
                    "provenance": "dev_auxiliary_not_work_model_output",
                    "fixture": fixture,
                    "status": "not_attempted_invalid_ink_output",
                    "after": None,
                    "after_metrics_unavailable": True,
                }
            rows.append(result)
            continue
        fixture = DEV_DIMENSION_FIXTURES.get((group["run"], item["floor_id"]))
        if fixture and align_plan_to_dimensions is not None:
            try:
                dimension_input = copy.deepcopy(ink_plan)
                dimension_input["dimension_chains"] = [
                    {key: copy.deepcopy(chain[key]) for key in
                     ("id", "axis", "segments_mm", "total_mm", "tick_pixels", "source_refs")}
                    for chain in fixture
                ]
                dimension_plan, dimension_report = align_plan_to_dimensions(dimension_input)
                dimension_item = copy.deepcopy(item); dimension_item["plan"] = dimension_plan
                result["dimension"] = {
                    "provenance": "dev_auxiliary_not_work_model_output",
                    "fixture": fixture, "report": dimension_report,
                    "status": "deliverable",
                    "after": score_plans(group["run"], [dimension_item]),
                    "after_metrics_unavailable": False,
                }
                result["dimension"]["semantic_delta"] = semantic_delta(
                    before, result["dimension"]["after"])
                result["opening_tier_regressions"].extend(opening_tier_regressions(
                    before, result["dimension"]["after"], item["plan"], dimension_plan,
                    ink_report, stage="ink_then_dimension"))
            except Exception as error:
                failure = getattr(error, "report", None)
                result["dimension"] = {
                    "provenance": "dev_auxiliary_not_work_model_output",
                    "fixture": fixture,
                    "report": failure if isinstance(failure, Mapping) else {},
                    "status": "rejected_no_deliverable_after_metrics",
                    "error": f"{type(error).__name__}: {error}",
                    "after": None,
                    "after_metrics_unavailable": True,
                }
        rows.append(result)
    return {"run": group["run"], "case": group["case"], "evidence_class": "real_reader_trial",
            "status": "replayed", "floors": rows}


def add_tier_counts(target: dict[str, int], source: Mapping[str, Any]) -> None:
    for key in target:
        target[key] += int(source.get(key, 0))


def item_type_counts(items: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        kind = str(item.get("type") or item.get("action") or "unspecified")
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def floor_stage_outcomes(
        report: Mapping[str, Any], *, whole_building_delivery_status: str,
        floor_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Keep compile-ready floor-A evidence separate from the delivered stack-B result."""
    raw_floor_reports = report.get("floor_reports")
    if isinstance(raw_floor_reports, Mapping) and raw_floor_reports:
        rows = [(str(floor_id), value) for floor_id, value in raw_floor_reports.items()
                if isinstance(value, Mapping)]
    else:
        identities = list(map(str, floor_ids))
        rows = [(identities[0], report)] if len(identities) == 1 and report else []
    outcomes = []
    whole_building_delivered = whole_building_delivery_status == "delivered"
    for floor_id, floor_report in rows:
        compile_ready = floor_report.get("status") == "pass"
        changes = [row for row in floor_report.get("changes", [])
                   if isinstance(row, Mapping)] if compile_ready else []
        mapping = (copy.deepcopy(dict(floor_report.get("semantic_mapping", {})))
                   if isinstance(floor_report.get("semantic_mapping"), Mapping) else {})
        removed_seeds = {
            identity for row in changes if row.get("type") == "remove_narrow_strip_space_seeds"
            for identity in _ids(row.get("removed_space_seeds", []))
        }
        moved_openings = {
            identity for row in changes if row.get("type") == "move_openings_to_merged_wall"
            for identity in _ids(row.get("openings", []))
        }
        retained_rehosted_openings = {
            identity for row in changes if row.get("type") == "retain_openings_on_merged_wall"
            for identity in _ids(row.get("opening_ids", []))
        }
        removed_openings = {
            identity for row in changes if row.get("type") == "merge_overlapping_openings"
            for identity in _ids(row.get("removed_opening_ids", []))
        }
        retained_openings = {
            str(row["retained_opening_id"])
            for row in changes if row.get("type") == "merge_overlapping_openings"
            and row.get("retained_opening_id") is not None
        }
        wall_merges = [row for row in changes
                       if str(row.get("type", "")).startswith("merge_duplicate_wall")]
        eliminated_spaces = mapping.get("eliminated_strip_spaces", [])
        narrow_counts = {
            "wall_merge_changes": len(wall_merges),
            "eliminated_strip_spaces": len(eliminated_spaces)
                if isinstance(eliminated_spaces, list) else 0,
            "removed_space_seeds": len(removed_seeds),
            "moved_openings": len(moved_openings),
            "retained_rehosted_openings": len(retained_rehosted_openings),
            "opening_merge_changes": sum(
                row.get("type") == "merge_overlapping_openings" for row in changes),
            "removed_overlapping_openings": len(removed_openings),
            "retained_merged_openings": len(retained_openings),
            "collapsed_wall_steps_removed": sum(
                row.get("type") == "remove_collapsed_wall_step" for row in changes),
        }
        elimination_count = (
            narrow_counts["wall_merge_changes"] + narrow_counts["removed_space_seeds"]
            + narrow_counts["removed_overlapping_openings"]
            + narrow_counts["collapsed_wall_steps_removed"])
        outcomes.append({
            "floor_id": floor_id,
            "same_floor_stage_status": floor_report.get("status"),
            "strict_compile_ready": compile_ready,
            "same_floor_compile_ready_change_counts": item_type_counts(changes),
            "same_floor_compile_ready_narrow_strip_counts": narrow_counts,
            "same_floor_compile_ready_removed_space_seed_ids": sorted(removed_seeds),
            "same_floor_compile_ready_moved_opening_ids": sorted(moved_openings),
            "same_floor_compile_ready_retained_rehosted_opening_ids": sorted(
                retained_rehosted_openings),
            "same_floor_compile_ready_removed_opening_ids": sorted(removed_openings),
            "same_floor_compile_ready_retained_opening_ids": sorted(retained_openings),
            "semantic_mapping": mapping,
            "whole_building_delivery_status": whole_building_delivery_status,
            "evidence_only_not_delivered": compile_ready and not whole_building_delivered,
            "counted_as_delivered_changes": len(changes) if whole_building_delivered else 0,
            "counted_as_delivered_eliminations": elimination_count
                if whole_building_delivered else 0,
            "rejection_counts": item_type_counts(
                row for row in floor_report.get("rejections", [])
                if isinstance(row, Mapping)),
        })
    return outcomes


def independent_floor_stage_outcomes(
        plans: list[Mapping[str, Any]], *, whole_building_delivery_status: str
        ) -> list[dict[str, Any]]:
    """Replay production A independently, including its source-save hard gate."""
    from src.agent.geometry import plan_regularization as production

    outcomes = []
    whole_delivered = whole_building_delivery_status == "delivered"
    for original in plans:
        report: Mapping[str, Any] = {}
        effective = copy.deepcopy(dict(original))
        stage_error = None
        try:
            plan, report = supported_call(
                production.regularize_plan, copy.deepcopy(original["plan"]),
                image_size=tuple(original["image_size"]), image_name=original["image_name"],
                rule_version=RULE_VERSION)
            supported_call(
                production.enforce_regularized_plan, plan,
                image_size=tuple(original["image_size"]), image_name=original["image_name"],
                rule_version=RULE_VERSION)
            effective["plan"] = plan
            save_gate = source_save_gate([effective])
        except Exception as error:
            failure = getattr(error, "report", None)
            if isinstance(failure, Mapping):
                report = failure
            save_gate = None
            stage_error = f"{type(error).__name__}: {error}"
        rows = floor_stage_outcomes(
            report, whole_building_delivery_status=whole_building_delivery_status,
            floor_ids=[str(original["floor_id"])])
        outcome = rows[0] if rows else {
            "floor_id": str(original["floor_id"]),
            "same_floor_stage_status": "rejected", "strict_compile_ready": False,
            "same_floor_compile_ready_change_counts": {},
            "same_floor_compile_ready_narrow_strip_counts": {},
            "whole_building_delivery_status": whole_building_delivery_status,
            "counted_as_delivered_changes": 0,
            "counted_as_delivered_eliminations": 0,
            "rejection_counts": {},
        }
        source_pass = isinstance(save_gate, Mapping) and save_gate.get("status") == "pass"
        stage_ready = bool(outcome.get("strict_compile_ready") and source_pass)
        outcome["same_floor_source_save_gate"] = (
            source_gate_summary({"source_save_gate": save_gate}) if save_gate else None)
        outcome["same_floor_delivery_ready"] = stage_ready
        outcome["same_floor_error"] = stage_error
        outcome["evidence_only_not_delivered"] = stage_ready and not whole_delivered
        if not (stage_ready and whole_delivered):
            outcome["counted_as_delivered_changes"] = 0
            outcome["counted_as_delivered_eliminations"] = 0
        outcomes.append(outcome)
    return outcomes


def semantic_count_table(row: Mapping[str, Any]) -> dict[str, Any]:
    before = row["before"]["semantics"]
    after = (row.get("after") or {}).get("semantics", {})
    floors = {}
    for floor_id in sorted(set(before) | set(after)):
        before_floor = before.get(floor_id, {})
        after_floor = after.get(floor_id, {})
        floors[floor_id] = {
            key: {
                "before": before_floor.get(key),
                "after": after_floor.get(key) if row.get("after") is not None else None,
            }
            for key in ("rooms", "openings", "doors", "windows")
        }
        floors[floor_id]["opening_host_rows"] = {
            "before": len(before_floor.get("opening_hosts") or []),
            "after": (len(after_floor.get("opening_hosts") or [])
                      if row.get("after") is not None else None),
        }
        floors[floor_id]["door_connection_rows"] = {
            "before": len(before_floor.get("door_connections") or []),
            "after": (len(after_floor.get("door_connections") or [])
                      if row.get("after") is not None else None),
        }
    return floors


def source_gate_summary(row: Mapping[str, Any]) -> dict[str, Any] | None:
    gate = row.get("source_save_gate")
    if not isinstance(gate, Mapping):
        return None
    precision = gate.get("building_precision")
    legacy_precision = gate.get("legacy_existing_source_precision")
    return {
        "status": gate.get("status"), "stage": gate.get("stage"),
        "current_source_save_status": gate.get("current_source_save_status", gate.get("status")),
        "source_model_sha256": gate.get("source_model_sha256"),
        "assembly_placements": copy.deepcopy(gate.get("assembly_placements", [])),
        "error": gate.get("error"),
        "hard_constraint_total": (precision.get("total")
                                  if isinstance(precision, Mapping) else None),
        "hard_constraint_counts": (copy.deepcopy(precision.get("counts", {}))
                                   if isinstance(precision, Mapping) else {}),
        "legacy_saved_source_path": gate.get("legacy_saved_source_path"),
        "legacy_saved_source_sha256": gate.get("legacy_saved_source_sha256"),
        "legacy_existing_source_precision_status": (
            legacy_precision.get("status") if isinstance(legacy_precision, Mapping) else None),
        "legacy_existing_source_precision_total": (
            legacy_precision.get("total") if isinstance(legacy_precision, Mapping) else None),
        "legacy_existing_source_precision_counts": (
            copy.deepcopy(legacy_precision.get("counts", {}))
            if isinstance(legacy_precision, Mapping) else {}),
    }


def summarize_replay(groups: list[dict[str, Any]], trials: list[dict[str, Any]]) -> dict[str, Any]:
    categories = {}
    for evidence_class in sorted({row["evidence_class"] for row in groups}):
        selected = [row for row in groups if row["evidence_class"] == evidence_class]
        successful = [row for row in selected if row["status"] == "regularized"]
        legacy_incompatible = [row for row in selected
                               if row["status"] == "legacy_geometric_pass_source_save_incompatible"]
        production_rejected = [row for row in selected if row["status"] == "rejected_no_deliverable_after_metrics"]
        verification_failed = [row for row in selected if row["status"] == "verification_failed_with_deliverable"]
        room_before = {key: 0 for key in ("<=5cm", "5-10cm", "10-30cm", ">30cm")}
        room_after = copy.deepcopy(room_before)
        opening_before = copy.deepcopy(room_before)
        opening_after = copy.deepcopy(room_before)
        for row in successful:
            add_tier_counts(room_before, row["before"]["tiers_room_boundary"])
            add_tier_counts(room_after, row["after"]["tiers_room_boundary"])
            add_tier_counts(opening_before, row["before"]["tiers_opening_along_wall"])
            add_tier_counts(opening_after, row["after"]["tiers_opening_along_wall"])
        allowed_semantic_changes = []
        semantic_violations = []
        for row in successful:
            for floor_id, deltas in row.get("semantic_delta", {}).items():
                changed = sorted(key for key, value in deltas.items() if value)
                if changed:
                    audit = row["semantic_audit"]["floors"].get(floor_id, {})
                    allowed_semantic_changes.append({
                        "run": row["run"], "floor_id": floor_id, "changed": changed,
                        "audit": audit,
                    })
        for row in verification_failed:
            semantic_violations.append({
                "run": row["run"], "semantic_audit": row.get("semantic_audit"),
                "separation_audit": row.get("separation_audit"),
                "exterior_alignment_audit": row.get("exterior_alignment_audit"),
                "cross_storey_near_line_audit": row.get("cross_storey_near_line_audit"),
                "round2_consistency_audit": row.get("round2_consistency_audit"),
            })
        floor_stage_rows = [floor for row in selected
                            for floor in row.get("floor_stage_outcomes", [])]
        floor_narrow_keys = (
            "wall_merge_changes", "eliminated_strip_spaces", "removed_space_seeds",
            "moved_openings", "retained_rehosted_openings", "opening_merge_changes",
            "removed_overlapping_openings", "retained_merged_openings",
            "collapsed_wall_steps_removed",
        )
        categories[evidence_class] = {
            "runs": len(selected),
            "regularized": len(successful),
            "geometric_pass_count": sum(
                row["status"] in {"regularized", "legacy_geometric_pass_source_save_incompatible"}
                for row in selected),
            "current_source_save_pass_count": sum(
                (row.get("source_save_gate") or {}).get("status") == "pass"
                for row in selected),
            "legacy_enum_incompatible": len(legacy_incompatible),
            "rejected_no_deliverable_after_metrics": len(production_rejected),
            "verification_failed_with_deliverable": len(verification_failed),
            "applied_changes": sum(len(row["items"]["applied_changes"]) for row in selected),
            "attempted_changes_not_delivered": sum(
                len(row["items"]["attempted_changes_not_delivered"]) for row in selected
            ),
            "eliminated_items": sum(len(row["items"]["eliminated"]) for row in selected),
            "exterior_alignment": {
                "applied_change_segments": sum(
                    len(row["items"]["exterior_alignment_changes"]) for row in selected),
                "eliminated_cross_storey_footprint_overlaps": sum(
                    len(row["items"]["eliminated_cross_storey_footprint_overlaps"])
                    for row in selected),
                "attempted_change_segments_not_delivered": sum(
                    len(row["items"]["attempted_exterior_alignment_changes_not_delivered"])
                    for row in selected),
                "invalid_change_segments_not_counted": sum(
                    len(row["items"]["invalid_exterior_alignment_changes_not_counted"])
                    for row in selected),
                "policy_audit_pass": sum(
                    (row.get("exterior_alignment_audit") or {}).get("status") == "pass"
                    for row in selected),
            },
            "cross_storey_stage": {
                "internal_wall_move_records": sum(
                    len(row["items"]["cross_storey_internal_wall_moves"])
                    for row in selected),
                "unaligned_near_line_pairs_before": sum(
                    int((row.get("cross_storey_near_line_audit") or {})
                        .get("before_unaligned_near_line_pairs", 0))
                    for row in selected),
                "unaligned_near_line_pairs_after": sum(
                    int((row.get("cross_storey_near_line_audit") or {})
                        .get("after_unaligned_near_line_pairs", 0))
                    for row in selected),
                "reduced_unaligned_near_line_pairs": sum(
                    int((row.get("cross_storey_near_line_audit") or {})
                        .get("reduced_pairs", 0))
                    for row in selected),
            },
            "rejected_items": sum(len(row["items"]["rejected"]) for row in selected),
            "same_floor_stage": {
                "floors": len(floor_stage_rows),
                "strict_compile_ready": sum(
                    floor.get("strict_compile_ready") is True for floor in floor_stage_rows),
                "source_save_gate_pass": sum(
                    (floor.get("same_floor_source_save_gate") or {}).get("status") == "pass"
                    for floor in floor_stage_rows),
                "delivery_ready": sum(
                    floor.get("same_floor_delivery_ready") is True for floor in floor_stage_rows),
                "evidence_only_not_delivered": sum(
                    floor.get("evidence_only_not_delivered") is True for floor in floor_stage_rows),
                "compile_ready_change_counts": {
                    key: sum(int(floor.get("same_floor_compile_ready_change_counts", {})
                                 .get(key, 0)) for floor in floor_stage_rows)
                    for key in sorted({
                        key for floor in floor_stage_rows
                        for key in floor.get("same_floor_compile_ready_change_counts", {})
                    })
                },
                "compile_ready_narrow_strip_counts": {
                    key: sum(int(floor.get("same_floor_compile_ready_narrow_strip_counts", {})
                                 .get(key, 0)) for floor in floor_stage_rows)
                    for key in floor_narrow_keys
                },
                "counted_as_delivered_eliminations": sum(
                    int(floor.get("counted_as_delivered_eliminations", 0))
                    for floor in floor_stage_rows),
            },
            "preserved_ge_30cm_reported_items": sum(
                len(row["items"]["preserved_ge_30cm"]) for row in selected),
            "delivered_preserved_ge_30cm": {
                "items": sum(len(row["items"]["preserved_ge_30cm"]) for row in successful),
                "unchanged": sum(
                    item.get("unchanged") is True for row in successful
                    for item in row["items"]["preserved_ge_30cm"] if isinstance(item, Mapping)),
                "changed_but_still_ge_30cm": sum(
                    item.get("unchanged") is False for row in successful
                    for item in row["items"]["preserved_ge_30cm"] if isinstance(item, Mapping)),
                "new_same_floor_sub_30cm_overlaps": sum(
                    len(row["separation_audit"]["new_same_floor_sub_30cm_overlaps"])
                    for row in successful),
            },
            "rejected_attempt_preserved_ge_30cm_diagnostics": sum(
                len(row["items"]["preserved_ge_30cm"])
                for row in selected if row["status"] != "regularized"),
            "successful_cohort_metrics": {
                "room_boundary_before": room_before, "room_boundary_after": room_after,
                "opening_along_wall_before": opening_before, "opening_along_wall_after": opening_after,
            },
            "allowed_declared_semantic_changes": allowed_semantic_changes,
            "unexplained_semantic_or_separation_violations": semantic_violations,
            "legacy_enum_incompatible_runs": [
                {"run": row["run"], "status": row["status"],
                 "source_save_gate": source_gate_summary(row)}
                for row in legacy_incompatible
            ],
            "rejected_runs": [
                {"run": row["run"], "status": row["status"], "error": row.get("error")}
                for row in [*production_rejected, *verification_failed]
            ],
            "run_outcomes": [
                {
                    "run": row["run"], "status": row["status"],
                    "applied_change_counts": item_type_counts(row["items"]["applied_changes"]),
                    "attempted_not_delivered_change_counts": item_type_counts(
                        row["items"]["attempted_changes_not_delivered"]),
                    "rejection_counts": item_type_counts(row["items"]["rejected"]),
                    "exterior_alignment_change_count": len(
                        row["items"]["exterior_alignment_changes"]),
                    "eliminated_cross_storey_footprint_overlap_count": len(
                        row["items"]["eliminated_cross_storey_footprint_overlaps"]),
                    "attempted_exterior_alignment_change_count_not_delivered": len(
                        row["items"]["attempted_exterior_alignment_changes_not_delivered"]),
                    "invalid_exterior_alignment_change_count_not_counted": len(
                        row["items"]["invalid_exterior_alignment_changes_not_counted"]),
                    "cross_storey_internal_wall_move_count": len(
                        row["items"]["cross_storey_internal_wall_moves"]),
                    "semantic_counts_before_after": semantic_count_table(row),
                    "floor_stage_outcomes": row.get("floor_stage_outcomes", []),
                    "source_save_gate": source_gate_summary(row),
                    "semantic_audit": row.get("semantic_audit"),
                    "separation_audit": row.get("separation_audit"),
                    "exterior_alignment_audit": row.get("exterior_alignment_audit"),
                    "cross_storey_near_line_audit": row.get("cross_storey_near_line_audit"),
                    "round2_consistency_audit": row.get("round2_consistency_audit"),
                }
                for row in selected
            ],
        }
    reader_floors = [floor for trial in trials for floor in trial["floors"]]
    dimensions = [floor["dimension"] for floor in reader_floors if floor.get("dimension")]
    def aggregate_scores(rows: list[Mapping[str, Any]], score_key: str) -> dict[str, dict[str, int]]:
        room = {key: 0 for key in ("<=5cm", "5-10cm", "10-30cm", ">30cm")}
        opening = copy.deepcopy(room)
        for row in rows:
            score = row[score_key]
            add_tier_counts(room, score["tiers_room_boundary"])
            add_tier_counts(opening, score["tiers_opening_along_wall"])
        return {"wall_position_proxy_room_boundary": room, "opening_along_wall": opening}
    ink_deliverable = [floor for floor in reader_floors if floor.get("ink_status") == "deliverable"]
    dimension_floors = [
        floor for floor in reader_floors
        if floor.get("dimension") and floor["dimension"].get("status") == "deliverable"
    ]
    reader_semantic_violations = []
    for floor in reader_floors:
        for stage, deltas in (
            ("ink", floor.get("ink_semantic_delta") or {}),
            ("dimension", (floor.get("dimension") or {}).get("semantic_delta") or {}),
        ):
            for normalized_floor, values in deltas.items():
                changed = sorted(key for key, value in values.items() if value)
                if changed:
                    reader_semantic_violations.append({
                        "run": floor["trial_run"], "floor_id": floor["floor_id"],
                        "normalized_floor": normalized_floor,
                        "stage": stage, "changed": changed,
                    })
    return {
        "regularization_by_evidence_class": categories,
        "reader_alignment": {
            "trial_groups": len(trials), "floors": len(reader_floors),
            "ink_deliverable": sum(floor.get("ink_status") == "deliverable" for floor in reader_floors),
            "ink_rejected_no_deliverable_after_metrics": sum(
                floor.get("ink_status") != "deliverable" for floor in reader_floors
            ),
            "dimension_dev_auxiliary_attempts": len(dimensions),
            "dimension_deliverable": sum(row.get("status") == "deliverable" for row in dimensions),
            "dimension_rejected_or_not_attempted": sum(row.get("status") != "deliverable" for row in dimensions),
            "semantic_violations": reader_semantic_violations,
            "opening_tier_regressions": [
                {"run": floor["trial_run"], "floor_id": floor["floor_id"], **row}
                for floor in reader_floors for row in floor.get("opening_tier_regressions", [])
            ],
            "ink_deliverable_cohort_metrics": {
                "before": aggregate_scores(ink_deliverable, "before"),
                "after_ink": aggregate_scores(ink_deliverable, "ink_after"),
            },
            "dimension_dev_auxiliary_deliverable_cohort_metrics": {
                "before": aggregate_scores(dimension_floors, "before"),
                "after_ink": aggregate_scores(dimension_floors, "ink_after"),
                "after_dimension": {
                    "wall_position_proxy_room_boundary": {
                        key: sum(int(floor["dimension"]["after"]["tiers_room_boundary"].get(key, 0))
                                 for floor in dimension_floors)
                        for key in ("<=5cm", "5-10cm", "10-30cm", ">30cm")
                    },
                    "opening_along_wall": {
                        key: sum(int(floor["dimension"]["after"]["tiers_opening_along_wall"].get(key, 0))
                                 for floor in dimension_floors)
                        for key in ("<=5cm", "5-10cm", "10-30cm", ">30cm")
                    },
                },
            },
        },
        "metric_policy": "before/after tier totals include only runs with a deliverable after result",
        "tier_policy": "mutually exclusive buckets: <=5cm, >5cm and <=10cm, >10cm and <=30cm, >30cm",
        "separation_policy": "original >=0.30m spacing may change; a delivered plan fails if it creates a same-floor overlapping parallel pair below 0.30m",
        "cross_storey_footprint_policy": "cross-storey footprint overlaps strictly below 0.30m may align upper edge to lower edge; reverse only when the upper edge has F dimension evidence and the lower edge does not; each unique source/target edge pair counts as one eliminated overlap",
        "same_floor_footprint_policy": "same-floor footprint remains fixed; move_footprint_edge is accepted only as a cross-storey stack change",
        "semantic_policy": "move_footprint_edge must preserve room and opening counts, opening kinds, hosts, and door connections exactly; named seeds removed with an audited same-floor narrow-strip merge and overlapping openings merged on that strip remain separately allowed with exact production semantic_mapping entries",
        "gt_usage_boundary": "reference IDs and errors are evaluation-only; alignment inputs come only from the historical plan image and dev-read dimension fixtures",
    }


def compact_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    for section in ("groups", "reader_trials"):
        for group in result[section]:
            for row in group["plans"]:
                row.pop("plan", None)
    return result


def build_report(manifest: Mapping[str, Any]) -> dict[str, Any]:
    groups = [regularize_group(group) for group in manifest["groups"]]
    trials = [reader_replay(group) for group in manifest["reader_trials"] if group["plans"]]
    return {
        "schema": "q1_replay_report_v1", "rule_version": RULE_VERSION,
        "model_requests": 0, "paratera_requests": 0, "deepseek_requests": 0,
        "manifest": compact_manifest(manifest),
        "regularization_replay": groups,
        "reader_alignment_replay": trials,
        "summary": summarize_replay(groups, trials),
        "reporting_boundary": {
            "real_work_model": [row["run"] for row in groups if row["evidence_class"] == "real_work_model_delivery"],
            "legal_replay": [row["run"] for row in groups if row["evidence_class"] == "legal_replay_claude_code"],
            "dev_auxiliary": [row["run"] for row in groups if row["evidence_class"] == "dev_auxiliary_opus"],
            "pipeline_dev_auxiliary": {
                **manifest["pipeline_dev_auxiliary_reference"],
                "included_in_historical_five_floor_metrics": False,
                "historical_fixture_origin_contract": (
                    "the original five H fixtures omit start_world_m and are expected "
                    "to report origin_basis=legacy_anchor"
                ),
            },
            "round3_cross_storey_footprint": {
                "change_type": "move_footprint_edge",
                "counting": "one alignment change per continuous source edge; one eliminated overlap per unique (source_floor_id, source_edge_index, target_floor_id, target_edge_index)",
                "direction": "upper to lower; reverse only when upper has F dimension evidence and lower does not",
                "stage_columns": {
                    "A_same_floor": "wall merges, narrow-strip and audited seed/opening effects",
                    "B_internal_wall_moves": "top-level stack move_wall_line records; same-floor A records remain in floor_reports",
                    "B_exterior_eliminations": "valid unique move_footprint_edge source/target edge pairs",
                },
                "unaligned_near_line_counting": "production storey_wall_offset_under_0_30m hard-constraint pairs before and after",
                "unchanged_hard_gates": [
                    "same-floor overlapping parallel separation >=0.30m",
                    "minimum space width >=0.60m",
                    "room/opening counts and opening host/door connectivity",
                    "literal compile and production source-save building_precision",
                ],
            },
            "rejected_after_metrics_policy": "unavailable; rejection is not counted as metric improvement",
            "temporary_round3_replay_artifacts": {
                "path": str(ROOT / "AI_agent/archive/local_backup/q1/round3-replay"),
                "retention": "delete_before_delivery",
                "required_for_reproduction": False,
                "reproduction_basis": (
                    "this script plus the original input paths and SHA256 values in manifest; "
                    "formal replay_report.json and reader_dimension_handoff.json remain in logs"
                ),
            },
        },
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--report", type=Path, default=HERE / "replay_report.json")
    args = parser.parse_args()
    manifest = inventory()
    if args.manifest_only:
        print(json.dumps(compact_manifest(manifest), ensure_ascii=False, indent=2))
        return
    report = build_report(manifest)
    write_json(args.report, report)
    print(json.dumps({"report": str(args.report), "groups": len(report["regularization_replay"]),
                      "reader_trials": len(report["reader_alignment_replay"]), "model_requests": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
