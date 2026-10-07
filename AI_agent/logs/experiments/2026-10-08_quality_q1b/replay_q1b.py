"""Deterministic Q1b pre-compile replay over the frozen input snapshot.

This script makes zero model requests and writes only the explicitly supplied
report.  A replay requires ``--report`` so preparing the package cannot start
the replay by accident.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import inspect
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANIFEST_PATH = HERE / "snapshot_manifest.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def json_equivalent(left: object, right: object) -> bool:
    """Compare persisted JSON values, ignoring tuple/list runtime representation."""
    return canonical_sha(left) == canonical_sha(right)


def error_category(error: str | None) -> str:
    text = str(error or "")
    if not text:
        return "pass"
    if "polygonize produced dangles" in text:
        return "dangle"
    if "physical partition overlaps footprint boundary" in text:
        return "partition_overlaps_footprint"
    if "occupy the same space" in text:
        return "duplicate_space_seed"
    if "requires one exterior or two interior full-boundary hosts" in text:
        return "opening_missing_host"
    if "has only one full space host" in text:
        return "opening_partial_host"
    if "line is outside footprint" in text:
        return "partition_outside_footprint"
    if "is degenerate" in text:
        return "degenerate_partition"
    return "other"


def validate_snapshot(manifest: Mapping[str, Any]) -> dict[str, Any]:
    errors = []
    checked = 0
    for row in manifest["items"]:
        for key in ("plan", "result"):
            record = row.get(key)
            if not record:
                continue
            path = ROOT / record["local_path"]
            checked += 1
            if not path.is_file():
                errors.append({"path": str(path), "error": "missing"})
                continue
            actual = sha256(path)
            if actual != record["local_sha256"] or actual != record["source_sha256"]:
                errors.append({
                    "path": str(path),
                    "error": "hash_mismatch",
                    "actual": actual,
                    "local_expected": record["local_sha256"],
                    "source_expected": record["source_sha256"],
                })
        image = row.get("image") or {}
        if image.get("local_path"):
            path = ROOT / image["local_path"]
            checked += 1
            if not path.is_file():
                errors.append({"path": str(path), "error": "missing"})
            else:
                actual = sha256(path)
                if actual != image["local_sha256"] or actual != image["source_sha256"]:
                    errors.append({
                        "path": str(path),
                        "error": "image_hash_mismatch",
                        "actual": actual,
                        "local_expected": image["local_sha256"],
                        "source_expected": image["source_sha256"],
                    })
    return {"status": "pass" if not errors else "fail", "files_checked": checked, "errors": errors}


def compile_plan(plan: dict, *, image_size: tuple[int, int], image_name: str) -> dict[str, Any]:
    from src.agent.geometry.plan_partition import compile_plan_partition

    try:
        proposal, metadata = compile_plan_partition(
            copy.deepcopy(plan), image_size=image_size, image_name=image_name
        )
    except Exception as error:
        return {
            "status": "error",
            "error_type": type(error).__name__,
            "error": str(error),
            "proposal_sha256": None,
            "metadata_sha256": None,
        }
    return {
        "status": "pass",
        "error_type": None,
        "error": None,
        "proposal_sha256": canonical_sha(proposal),
        "metadata_sha256": canonical_sha(metadata),
    }


def supported_call(function: Any, *args: Any, **kwargs: Any) -> Any:
    parameters = inspect.signature(function).parameters
    return function(*args, **{key: value for key, value in kwargs.items() if key in parameters})


def prepare_plan(plan: dict, *, image_size: tuple[int, int], image_name: str) -> tuple[dict, dict]:
    from src.agent.geometry import plan_regularization as production

    function = getattr(production, "prepare_plan_junctions", None)
    if function is None:
        raise RuntimeError("production prepare_plan_junctions is not available")
    output = supported_call(
        function,
        copy.deepcopy(plan),
        image_size=image_size,
        image_name=image_name,
        max_movement_m=0.30,
    )
    if isinstance(output, tuple) and len(output) == 2:
        prepared, report = output
    elif isinstance(output, Mapping) and isinstance(output.get("plan"), Mapping):
        prepared = output["plan"]
        report = output.get("report", {})
    else:
        raise TypeError(
            "prepare_plan_junctions must return (plan, report) or {'plan': ..., 'report': ...}"
        )
    if not isinstance(prepared, dict) or not isinstance(report, Mapping):
        raise TypeError("prepare_plan_junctions returned invalid plan/report types")
    return copy.deepcopy(prepared), copy.deepcopy(dict(report))


def public_regularize_plan(
    plan: dict, *, image_size: tuple[int, int], image_name: str
) -> dict[str, Any]:
    """Replay the actual shared single-floor save path, including Q1 gates."""
    from src.agent.geometry import plan_regularization as production

    try:
        output, report = supported_call(
            production.regularize_plan,
            copy.deepcopy(plan),
            image_size=image_size,
            image_name=image_name,
        )
        supported_call(
            production.enforce_regularized_plan,
            output,
            image_size=image_size,
            image_name=image_name,
        )
        compiled = compile_plan(output, image_size=image_size, image_name=image_name)
    except Exception as error:
        failure = getattr(error, "report", None)
        failure_report = copy.deepcopy(dict(failure)) if isinstance(failure, Mapping) else {}
        error_text = nested_compile_error(failure_report) or str(error)
        attempted = list(failure_report.get("attempted_changes") or [])
        return {
            "status": "error",
            "error_type": type(error).__name__,
            "error": error_text,
            "error_category": error_category(error_text),
            "report": compact_regularization_report(failure_report),
            "reported_change_items": [],
            "attempted_change_type_counts": item_type_counts(attempted),
            "change_type_counts": {},
            "opening_or_seed_change_type_counts": {},
            "q1_seed_or_opening_change_type_counts": {},
            "semantic_signature_after": None,
            "strict_compile_output_sha256": None,
        }
    items = list(report.get("changes") or [])
    change_types = Counter(str(item.get("type", "unknown")) for item in items)
    seed_opening_types = {
        key: value
        for key, value in change_types.items()
        if "seed" in key.lower() or "opening" in key.lower()
    }
    q1_seed_opening_types = {
        key: value for key, value in change_types.items()
        if key in {
            "remove_narrow_strip_space_seeds",
            "merge_overlapping_openings",
            "move_openings_to_merged_wall",
            "retain_openings_on_merged_wall",
        }
    }
    return {
        "status": "pass",
        "error_type": None,
        "error": None,
        "error_category": "pass",
        "report": compact_regularization_report(report),
        "reported_change_items": items,
        "change_type_counts": dict(sorted(change_types.items())),
        "opening_or_seed_change_type_counts": dict(sorted(seed_opening_types.items())),
        "q1_seed_or_opening_change_type_counts": dict(sorted(q1_seed_opening_types.items())),
        "semantic_signature_after": semantic_signature(output),
        "strict_compile_output_sha256": canonical_sha(compiled),
        "output_plan_sha256": canonical_sha(output),
    }


def semantic_signature(plan: Mapping[str, Any]) -> dict[str, Any]:
    openings = list(plan.get("openings") or [])
    partitions = list(plan.get("partitions") or [])
    seeds = list(plan.get("space_seeds") or [])
    return {
        "floor_id": str(plan.get("floor_id")),
        "footprint_vertex_count": len(plan.get("footprint_pixels") or []),
        "partition_count": len(partitions),
        "partition_ids": sorted(str(row.get("id")) for row in partitions),
        "opening_count": len(openings),
        "opening_ids": sorted(str(row.get("id")) for row in openings),
        "opening_kinds": sorted((str(row.get("id")), str(row.get("kind"))) for row in openings),
        "space_seed_count": len(seeds),
        "space_seed_ids": sorted(str(row.get("id")) for row in seeds),
    }


def leaf_changes(before: Any, after: Any, path: str = "$") -> list[dict[str, Any]]:
    if type(before) is not type(after):
        return [{"path": path, "before": before, "after": after}]
    if isinstance(before, Mapping):
        changes = []
        for key in sorted(set(before) | set(after), key=str):
            child = f"{path}.{key}"
            if key not in before:
                changes.append({"path": child, "before": None, "after": after[key]})
            elif key not in after:
                changes.append({"path": child, "before": before[key], "after": None})
            else:
                changes.extend(leaf_changes(before[key], after[key], child))
        return changes
    if isinstance(before, list):
        changes = []
        for index in range(max(len(before), len(after))):
            child = f"{path}[{index}]"
            if index >= len(before):
                changes.append({"path": child, "before": None, "after": after[index]})
            elif index >= len(after):
                changes.append({"path": child, "before": before[index], "after": None})
            else:
                changes.extend(leaf_changes(before[index], after[index], child))
        return changes
    return [] if before == after else [{"path": path, "before": before, "after": after}]


def report_change_items(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in {"changes", "applied_changes", "repairs"} and isinstance(child, list):
                    for item in child:
                        if isinstance(item, Mapping):
                            found.append({"report_path": child_path, **copy.deepcopy(dict(item))})
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(report, "$report")
    unique = []
    seen = set()
    for item in found:
        marker = canonical_sha(item)
        if marker not in seen:
            unique.append(item)
            seen.add(marker)
    return unique


def q1_reported_change_items(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Match the original Q1 reader's report flattening exactly."""
    found: list[dict[str, Any]] = []

    def visit(value: Any, key: str | None = None) -> None:
        if key in {"changes", "attempted_changes", "eliminated", "applied"} and isinstance(value, list):
            found.extend(copy.deepcopy(item) for item in value if isinstance(item, Mapping))
        if isinstance(value, Mapping):
            for child_key, child in value.items():
                visit(child, str(child_key))
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(report)
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in found:
        marker = canonical_sha(item)
        if marker not in seen:
            seen.add(marker)
            unique.append(item)
    return unique


def item_type_counts(items: list[Any]) -> dict[str, int]:
    return dict(sorted(Counter(
        str(item.get("type") or item.get("action") or "unknown")
        for item in items if isinstance(item, Mapping)
    ).items()))


def nested_compile_error(report: Mapping[str, Any]) -> str | None:
    junction = report.get("junction_preparation")
    if isinstance(junction, Mapping) and junction.get("compile_error"):
        return str(junction["compile_error"])
    for row in report.get("rejections") or []:
        if isinstance(row, Mapping) and row.get("error"):
            return str(row["error"])
    for key in ("compile_error", "error"):
        if report.get(key):
            return str(report[key])
    return None


def compact_regularization_report(report: Mapping[str, Any]) -> dict[str, Any]:
    junction = report.get("junction_preparation")
    hard = report.get("hard_constraints")
    violations = hard.get("violations") if isinstance(hard, Mapping) else []
    return {
        "report_sha256": canonical_sha(report),
        "schema": report.get("schema"),
        "status": report.get("status"),
        "summary": copy.deepcopy(report.get("summary")),
        "change_type_counts": item_type_counts(list(report.get("changes") or [])),
        "attempted_change_type_counts": item_type_counts(list(report.get("attempted_changes") or [])),
        "junction_preparation": ({
            "status": junction.get("status"),
            "compile_error_before": junction.get("compile_error_before"),
            "compile_error": junction.get("compile_error"),
            "change_type_counts": item_type_counts(list(junction.get("changes") or [])),
            "attempted_change_type_counts": item_type_counts(list(junction.get("attempted_changes") or [])),
        } if isinstance(junction, Mapping) else None),
        "hard_constraints": ({
            "status": hard.get("status"),
            "violation_type_counts": dict(sorted(Counter(
                str(item.get("type", "unknown"))
                for item in violations or [] if isinstance(item, Mapping)
            ).items())),
        } if isinstance(hard, Mapping) else None),
        "rejection_type_counts": dict(sorted(Counter(
            str(item.get("type", "unknown"))
            for item in report.get("rejections") or [] if isinstance(item, Mapping)
        ).items())),
    }


def replay_item(row: Mapping[str, Any]) -> dict[str, Any]:
    plan_path = ROOT / row["plan"]["local_path"]
    plan = read_json(plan_path)
    image_size = tuple(int(value) for value in row["image"]["size"])
    image_name = str(row["image_name"])
    before_compile = compile_plan(plan, image_size=image_size, image_name=image_name)
    before_semantics = semantic_signature(plan)
    public_regularization = public_regularize_plan(
        plan, image_size=image_size, image_name=image_name
    )
    public_semantics = public_regularization.get("semantic_signature_after")
    public_regularization["semantic_signature_changed"] = (
        public_semantics is not None and public_semantics != before_semantics
    )
    prepared = copy.deepcopy(plan)
    preparation_report: dict[str, Any] = {}
    preparation_error = None
    try:
        prepared, preparation_report = prepare_plan(
            plan, image_size=image_size, image_name=image_name
        )
    except Exception as error:
        preparation_error = f"{type(error).__name__}: {error}"
    after_compile = compile_plan(prepared, image_size=image_size, image_name=image_name)
    after_semantics = semantic_signature(prepared)
    changes = leaf_changes(plan, prepared)
    returned_plan_error = after_compile.get("error")
    attempted_remaining_error = preparation_report.get("compile_error")
    attempted_change_items = copy.deepcopy(
        preparation_report.get("attempted_changes") or []
    )
    return {
        "group": row["group"],
        "run": row["run"],
        "item": row["item"],
        "floor_id": row["floor_id"],
        "source_plan_sha256": row["plan"]["source_sha256"],
        "strict_compile_before": before_compile,
        "strict_compile_after": after_compile,
        "recovered_compile": before_compile["status"] == "error" and after_compile["status"] == "pass",
        "regressed_compile": before_compile["status"] == "pass" and after_compile["status"] == "error",
        "compiled_geometry_unchanged": (
            before_compile["status"] == "pass"
            and after_compile["status"] == "pass"
            and before_compile["proposal_sha256"] == after_compile["proposal_sha256"]
        ),
        "plan_sha256_before": canonical_sha(plan),
        "plan_sha256_after": canonical_sha(prepared),
        "plan_changes": changes,
        "semantic_signature_before": before_semantics,
        "semantic_signature_after": after_semantics,
        "semantic_signature_unchanged": before_semantics == after_semantics,
        "preparation_report": preparation_report,
        "reported_change_items": report_change_items(preparation_report),
        "attempted_change_items": attempted_change_items,
        "preparation_error": preparation_error,
        "returned_plan_error": returned_plan_error,
        "attempted_remaining_error": attempted_remaining_error,
        "remaining_error": attempted_remaining_error or returned_plan_error,
        "public_regularization": public_regularization,
        "baseline": copy.deepcopy(row.get("baseline", {})),
        "_prepared_plan": prepared,
        "_image_size": list(image_size),
        "_image_name": image_name,
        "_local_plan_path": row["plan"]["local_path"],
    }


def q1_group_replay(run: str, rows: list[dict[str, Any]], expected: Mapping[str, Any]) -> dict[str, Any]:
    from src.agent.geometry import plan_regularization as production

    inputs = [
        {
            "plan": copy.deepcopy(row["_prepared_plan"]),
            "image_size": tuple(row["_image_size"]),
            "image_name": row["_image_name"],
            "floor_id": row["floor_id"],
            "z_floor": row["_prepared_plan"].get("z_floor"),
            "source_ref": row["_local_plan_path"],
        }
        for row in rows
        if row["strict_compile_after"]["status"] == "pass"
    ]
    if len(inputs) != len(rows):
        return {
            "run": run,
            "status": "not_run_after_strict_compile_failure",
            "expected": copy.deepcopy(dict(expected)),
            "strict_compile_passed": len(inputs),
            "input_count": len(rows),
            "regression_guard": {
                "status": "fail",
                "reason": "strict compile failed before Q1 group regularization",
            },
        }
    try:
        if len(inputs) == 1:
            plan, report = supported_call(
                production.regularize_plan,
                inputs[0]["plan"],
                image_size=inputs[0]["image_size"],
                image_name=inputs[0]["image_name"],
            )
            supported_call(
                production.enforce_regularized_plan,
                plan,
                image_size=inputs[0]["image_size"],
                image_name=inputs[0]["image_name"],
            )
            output_hashes = [canonical_sha(plan)]
        else:
            output, report = supported_call(production.regularize_plan_stack, inputs)
            supported_call(production.enforce_regularized_plan_stack, output)
            output_hashes = [canonical_sha(item.get("plan") or item.get("regularized_plan")) for item in output]
    except Exception as error:
        failure = getattr(error, "report", None)
        compact_failure = (
            compact_regularization_report(failure)
            if isinstance(failure, Mapping) else None
        )
        if isinstance(failure, Mapping):
            hard = failure.get("hard_constraints")
            if isinstance(hard, Mapping):
                compact_failure["hard_constraint_violations"] = [
                    {
                        "type": item.get("type"),
                        "distance_m": item.get("distance_m"),
                        "objects": copy.deepcopy(item.get("objects")),
                    }
                    for item in hard.get("violations") or []
                    if isinstance(item, Mapping)
                ]
        return {
            "run": run,
            "status": "error",
            "error": f"{type(error).__name__}: {error}",
            "error_report": compact_failure,
            "expected": copy.deepcopy(dict(expected)),
            "strict_compile_passed": len(inputs),
            "input_count": len(rows),
            "regression_guard": {
                "status": "fail",
                "reason": "Q1 group regularization raised",
            },
        }
    change_count = len(q1_reported_change_items(report))
    expected_change_count = expected.get("source_q1_applied_change_count")
    guard = (
        {
            "status": "pass" if change_count == expected_change_count else "fail",
            "expected_change_count": expected_change_count,
            "current_change_count": change_count,
            "expected_source_status": expected.get("source_q1_status"),
            "scope": "strict compile plus Q1 group regularization",
        }
        if expected_change_count is not None
        else {
            "status": "partial_only",
            "reason": "original Q1 reader ink/dimension alignment is outside this pre-compile replay",
            "expected_reader_statuses": copy.deepcopy(
                expected.get("source_q1_reader_statuses", {})
            ),
            "scope": "strict compile plus Q1 group regularization only",
        }
    )
    return {
        "run": run,
        "status": "pass",
        "report_sha256": canonical_sha(report),
        "reported_change_count": change_count,
        "output_plan_sha256": output_hashes,
        "expected": copy.deepcopy(dict(expected)),
        "strict_compile_passed": len(inputs),
        "input_count": len(rows),
        "regression_guard": guard,
    }


def load_q1_replay_module() -> Any:
    path = HERE.parent / "2026-10-07_quality_q1/replay.py"
    spec = importlib.util.spec_from_file_location("q1_frozen_reader_replay", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Q1 reader replay: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reader_comparable(row: Mapping[str, Any]) -> dict[str, Any]:
    dimension = row.get("dimension")
    if isinstance(dimension, Mapping):
        dimension_value = {
            "status": dimension.get("status"),
            "after": copy.deepcopy(dimension.get("after")),
            "semantic_delta": copy.deepcopy(dimension.get("semantic_delta")),
            "report_status": (
                dimension.get("report", {}).get("status")
                if isinstance(dimension.get("report"), Mapping) else None
            ),
        }
    else:
        dimension_value = None
    return {
        "floor_id": row.get("floor_id"),
        "before": copy.deepcopy(row.get("before")),
        "ink_status": row.get("ink_status"),
        "ink_report_status": (
            row.get("ink_report", {}).get("status")
            if isinstance(row.get("ink_report"), Mapping) else None
        ),
        "ink_after": copy.deepcopy(row.get("ink_after")),
        "ink_semantic_delta": copy.deepcopy(row.get("ink_semantic_delta")),
        "opening_tier_regressions": copy.deepcopy(row.get("opening_tier_regressions")),
        "dimension": dimension_value,
    }


def full_q1_reader_replay(manifest: Mapping[str, Any]) -> dict[str, Any]:
    q1_report_record = manifest["q1_source_report"]
    # The manifest retains original provenance, while replay uses the tracked
    # report in this checkout so it survives collection of the temporary tree.
    q1_report_path = HERE.parent / "2026-10-07_quality_q1/replay_report.json.gz"
    if sha256(q1_report_path) != q1_report_record["sha256"]:
        raise ValueError("source Q1 replay report hash drift")
    with gzip.open(q1_report_path, "rt", encoding="utf-8") as handle:
        source_report = json.load(handle)
    expected_groups = {
        group["run"]: group for group in source_report["reader_alignment_replay"]
    }
    module = load_q1_replay_module()
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in manifest["items"]:
        if row["group"] == "q1_historical_reader_inputs":
            groups[str(row["run"])].append(row)
    outputs = []
    comparisons = []
    for run, rows in groups.items():
        plans = []
        for row in rows:
            image_record = row["image"]
            if not image_record.get("local_path"):
                raise ValueError(f"Q1 reader image is not frozen locally: {run}/{row['floor_id']}")
            plans.append({
                "run": run,
                "case": module.case_key(run),
                "evidence_class": "real_reader_trial",
                "floor_id": row["floor_id"],
                "plan_path": row["plan"]["local_path"],
                "plan_sha256": row["plan"]["local_sha256"],
                "image_name": row["image_name"],
                "image_path": str(ROOT / image_record["local_path"]),
                "image_sha256": image_record["local_sha256"],
                "image_size": image_record["size"],
                "plan": read_json(ROOT / row["plan"]["local_path"]),
            })
        current = module.reader_replay({
            "run": run,
            "case": module.case_key(run),
            "evidence_class": "real_reader_trial",
            "plans": plans,
        })
        outputs.append(current)
        expected = expected_groups[run]
        expected_floors = {row["floor_id"]: row for row in expected["floors"]}
        current_floors = {row["floor_id"]: row for row in current["floors"]}
        for floor_id in sorted(set(expected_floors) | set(current_floors)):
            expected_value = reader_comparable(expected_floors.get(floor_id, {}))
            current_value = reader_comparable(current_floors.get(floor_id, {}))
            field_matches = {
                key: json_equivalent(expected_value.get(key), current_value.get(key))
                for key in expected_value
                if key != "floor_id"
            }
            comparisons.append({
                "run": run,
                "floor_id": floor_id,
                "status": "pass" if all(field_matches.values()) else "changed",
                "field_matches": field_matches,
                "expected_statuses": {
                    "ink_status": expected_value.get("ink_status"),
                    "ink_report_status": expected_value.get("ink_report_status"),
                    "dimension_status": (
                        expected_value.get("dimension") or {}
                    ).get("status") if isinstance(expected_value.get("dimension"), Mapping) else None,
                },
                "current_statuses": {
                    "ink_status": current_value.get("ink_status"),
                    "ink_report_status": current_value.get("ink_report_status"),
                    "dimension_status": (
                        current_value.get("dimension") or {}
                    ).get("status") if isinstance(current_value.get("dimension"), Mapping) else None,
                },
                "expected_sha256": canonical_sha(expected_value),
                "current_sha256": canonical_sha(current_value),
            })
    compact_outputs = []
    for output in outputs:
        compact_outputs.append({
            "run": output.get("run"),
            "case": output.get("case"),
            "status": output.get("status"),
            "output_sha256": canonical_sha(output),
            "floors": [
                {
                    "floor_id": floor.get("floor_id"),
                    "ink_status": floor.get("ink_status"),
                    "ink_report_status": (
                        floor.get("ink_report", {}).get("status")
                        if isinstance(floor.get("ink_report"), Mapping) else None
                    ),
                    "dimension_status": (
                        floor.get("dimension", {}).get("status")
                        if isinstance(floor.get("dimension"), Mapping) else None
                    ),
                    "opening_tier_regression_count": len(
                        floor.get("opening_tier_regressions") or []
                    ),
                }
                for floor in output.get("floors") or []
            ],
        })
    return {
        "source_q1_report": copy.deepcopy(q1_report_record),
        "groups": compact_outputs,
        "comparisons": comparisons,
        "summary": {
            "groups": len(outputs),
            "floors": len(comparisons),
            "exact_match": sum(row["status"] == "pass" for row in comparisons),
            "changed": sum(row["status"] != "pass" for row in comparisons),
            "ink_deliverable": sum(
                floor.get("ink_status") == "deliverable"
                for group in outputs for floor in group["floors"]
            ),
            "dimension_deliverable": sum(
                isinstance(floor.get("dimension"), Mapping)
                and floor["dimension"].get("status") == "deliverable"
                for group in outputs for floor in group["floors"]
            ),
            "dimension_rejected": sum(
                isinstance(floor.get("dimension"), Mapping)
                and floor["dimension"].get("status") == "rejected_no_deliverable_after_metrics"
                for group in outputs for floor in group["floors"]
            ),
        },
    }


def compact_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in row.items() if not key.startswith("_")}


def failure_trial_table(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    labels = {
        "dangle": "悬线/未闭合",
        "partition_overlaps_footprint": "隔墙压外轮廓",
        "duplicate_space_seed": "两个种子落在同一空间",
        "opening_missing_host": "门窗无完整宿主墙",
        "opening_partial_host": "门窗只有一个内部宿主",
        "partition_outside_footprint": "隔墙在外轮廓外",
        "degenerate_partition": "零长度或退化隔墙",
        "other": "其他",
        "pass": "严格编译通过",
    }
    table = []
    selected = [row for row in rows if row["group"] == "failure_trials_earliest_two_tasks"]
    for sequence, row in enumerate(selected, start=1):
        baseline_type = str(row.get("baseline", {}).get("failure_type") or "other")
        remaining_type = error_category(row.get("remaining_error"))
        public = row.get("public_regularization") or {}
        applied = list(row.get("preparation_report", {}).get("changes") or [])
        attempted = list(row.get("preparation_report", {}).get("attempted_changes") or [])
        change_types = Counter(str(item.get("type", "unknown")) for item in [*applied, *attempted])
        table.append({
            "sequence": sequence,
            "task": str(row["run"])[:8],
            "draft": row["item"],
            "floor_id": row["floor_id"],
            "baseline_failure_type": baseline_type,
            "baseline_failure_zh": labels.get(baseline_type, labels["other"]),
            "preparation_status": row.get("preparation_report", {}).get("status"),
            "change_count": len(applied) if applied else len(attempted),
            "change_types": dict(sorted(change_types.items())),
            "strict_compile_after": row["strict_compile_after"]["status"],
            "remaining_failure_type": remaining_type,
            "remaining_failure_zh": labels.get(remaining_type, labels["other"]),
            "public_regularization_status": public.get("status"),
            "public_regularization_failure_type": public.get("error_category"),
            "public_regularization_failure_zh": labels.get(
                str(public.get("error_category") or "other"), labels["other"]
            ),
            "public_regularization_change_count": len(
                public.get("reported_change_items") or []
            ),
            "public_regularization_change_types": copy.deepcopy(
                public.get("change_type_counts") or {}
            ),
            "public_opening_or_seed_change_types": copy.deepcopy(
                public.get("opening_or_seed_change_type_counts") or {}
            ),
            "public_q1_seed_or_opening_change_types": copy.deepcopy(
                public.get("q1_seed_or_opening_change_type_counts") or {}
            ),
            "public_semantic_signature_changed": bool(
                public.get("semantic_signature_changed")
            ),
            "semantic_signature_unchanged": row["semantic_signature_unchanged"],
        })
    return table


def write_failure_markdown(path: Path, report: Mapping[str, Any]) -> None:
    type_labels = {
        "pixel_coordinate_precision": "坐标精度",
        "join_near_endpoint": "接近端点",
        "join_partition_to_footprint": "接外轮廓",
        "project_opening_to_host": "门窗投宿主",
        "remove_redundant_partition_segments": "删重叠/退化段",
        "remove_narrow_strip_space_seeds": "Q1合并空间种子",
        "merge_overlapping_openings": "Q1合并重叠开口",
        "move_openings_to_merged_wall": "Q1迁移开口",
        "retain_openings_on_merged_wall": "Q1保留并重挂开口",
    }

    def changes(value: Mapping[str, int]) -> str:
        if not value:
            return "0"
        return "；".join(
            f"{type_labels.get(key, key)}×{count}" for key, count in value.items()
        )

    rows = report["failure_trial_table"]
    strict_pass = sum(row["strict_compile_after"] == "pass" for row in rows)
    public_pass = sum(row["public_regularization_status"] == "pass" for row in rows)
    public_seed_opening = Counter()
    for row in rows:
        public_seed_opening.update(row["public_q1_seed_or_opening_change_types"])
    lines = [
        "# Q1b 最早两项平面读图任务：27 份失败稿离线回放",
        "",
        "本表保持原任务和稿件顺序。`strict` 只表示编译前修整后能否严格编译；",
        "`公共入口` 是两种模式共同调用的 `regularize_plan`，还包含 Q1 规整与硬约束。",
        "编译或公共入口通过都不等于整案建筑正确。全程 0 次模型请求。",
        "`prepare=整稿回滚` 的行中，“修整变化”是未应用的尝试；“尝试稿剩余错误”来自该尝试稿，函数实际返回并保留原稿。",
        "",
        f"结果：strict 通过 {strict_pass}/27；公共入口通过 {public_pass}/27；"
        f"公共入口在 Q1 阶段显式合并/重挂种子或开口 {sum(public_seed_opening.values())} 项"
        + (f"（{changes(dict(sorted(public_seed_opening.items())))}）" if public_seed_opening else "。"),
        "",
        "| # | 任务 | 稿号 | 原失败 | prepare | 修整变化 | strict | 尝试稿剩余错误 | 公共入口 | 公共入口实际变化 | 公共入口剩余 |",
        "|---:|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        public_status = "通过" if row["public_regularization_status"] == "pass" else "失败"
        strict_status = "通过" if row["strict_compile_after"] == "pass" else "失败"
        prepare_status = {
            "applied": "已应用",
            "rolled_back": "整稿回滚",
            "unchanged": "无变化",
        }.get(str(row["preparation_status"]), str(row["preparation_status"]))
        lines.append(
            "| {sequence} | `{task}` | `{draft}` | {baseline_failure_zh} | {prepare} | {prepare_changes} | {strict} | {remaining_failure_zh} | {public} | {public_changes} | {public_remaining} |".format(
                **row,
                prepare=prepare_status,
                prepare_changes=changes(row["change_types"]),
                strict=strict_status,
                public=public_status,
                public_changes=changes(row["public_regularization_change_types"]),
                public_remaining=row["public_regularization_failure_zh"],
            )
        )
    lines.extend([
        "",
        "公共入口在 Q1 阶段显式合并/重挂空间种子或开口的逐稿数量见 `final_replay.json` 的 `public_q1_seed_or_opening_change_types`；普通 prepare 开口投宿主另记在 `public_opening_or_seed_change_types`，失败并整稿回滚时实际变化记为 0。",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_report(manifest: Mapping[str, Any]) -> dict[str, Any]:
    item_rows = [replay_item(row) for row in manifest["items"]]
    q1_reader = full_q1_reader_replay(manifest)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    q1_groups = {
        "three_case_comparison_delivery_plans",
        "q1_historical_regularization_inputs",
        "q1_historical_reader_inputs",
    }
    for row in item_rows:
        if row["group"] in q1_groups:
            grouped[(row["group"], row["run"])].append(row)
    q1_runs = []
    for (group, run), rows in sorted(grouped.items()):
        result = q1_group_replay(
            run,
            rows,
            manifest.get("expected_q1_runs", {}).get(run, {}),
        )
        result["group"] = group
        if group == "q1_historical_reader_inputs":
            result["boundary"] = (
                "Q1b replays pre-compile junctions and Q1 regularization only; "
                "the unchanged Q1 ink/dimension replay remains a separate existing check"
            )
        q1_runs.append(result)
    before_counts = Counter(row["strict_compile_before"]["status"] for row in item_rows)
    after_counts = Counter(row["strict_compile_after"]["status"] for row in item_rows)
    remaining_types = Counter()
    for row in item_rows:
        error = str(row.get("remaining_error") or "")
        if "polygonize produced dangles" in error:
            remaining_types["dangle"] += 1
        elif "occupy the same space" in error:
            remaining_types["duplicate_space_seed"] += 1
        elif "requires one exterior or two interior full-boundary hosts" in error:
            remaining_types["opening_missing_host"] += 1
        elif "has only one full space host" in error:
            remaining_types["opening_partial_host"] += 1
        elif "outside footprint" in error:
            remaining_types["outside_or_overlapping_footprint"] += 1
        elif error:
            remaining_types["other"] += 1
    clean_rows = [compact_row(row) for row in item_rows]
    guard_counts = Counter(
        row.get("regression_guard", {}).get("status", "missing") for row in q1_runs
    )
    return {
        "schema": "q1b_replay_report_v1",
        "model_requests": 0,
        "paratera_requests": 0,
        "deepseek_requests": 0,
        "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "snapshot_validation": validate_snapshot(manifest),
        "summary": {
            "items": len(item_rows),
            "strict_compile_before": dict(sorted(before_counts.items())),
            "strict_compile_after": dict(sorted(after_counts.items())),
            "recovered_compile": sum(row["recovered_compile"] for row in item_rows),
            "regressed_compile": sum(row["regressed_compile"] for row in item_rows),
            "attempted_compile_pass": sum(
                not row.get("attempted_remaining_error") and not row.get("preparation_error")
                for row in item_rows
            ),
            "attempted_change_count": sum(
                len(row.get("attempted_change_items") or []) for row in item_rows
            ),
            "public_regularization": dict(sorted(Counter(
                row.get("public_regularization", {}).get("status", "missing")
                for row in item_rows
            ).items())),
            "failure_trials_public_regularization": dict(sorted(Counter(
                row.get("public_regularization", {}).get("status", "missing")
                for row in item_rows
                if row["group"] == "failure_trials_earliest_two_tasks"
            ).items())),
            "failure_trials_public_semantic_changes": sum(
                bool(row.get("public_regularization", {}).get("semantic_signature_changed"))
                for row in item_rows
                if row["group"] == "failure_trials_earliest_two_tasks"
            ),
            "failure_trials_public_q1_seed_or_opening_change_count": sum(
                sum(row.get("public_regularization", {}).get(
                    "q1_seed_or_opening_change_type_counts", {}
                ).values())
                for row in item_rows
                if row["group"] == "failure_trials_earliest_two_tasks"
            ),
            "all_public_q1_seed_or_opening_change_type_counts": dict(sorted(sum(
                (
                    Counter(row.get("public_regularization", {}).get(
                        "q1_seed_or_opening_change_type_counts", {}
                    )) for row in item_rows
                ),
                Counter(),
            ).items())),
            "semantic_signature_changed": sum(not row["semantic_signature_unchanged"] for row in item_rows),
            "previously_compiling_geometry_changed": sum(
                row["strict_compile_before"]["status"] == "pass"
                and row["strict_compile_after"]["status"] == "pass"
                and not row["compiled_geometry_unchanged"]
                for row in item_rows
            ),
            "remaining_error_types": dict(sorted(remaining_types.items())),
            "q1_group_pass": sum(row["status"] == "pass" for row in q1_runs),
            "q1_group_total": len(q1_runs),
            "q1_regression_guard": dict(sorted(guard_counts.items())),
            "q1_reader_alignment_guard": copy.deepcopy(q1_reader["summary"]),
        },
        "items": clean_rows,
        "failure_trial_table": failure_trial_table(item_rows),
        "q1_group_replay": q1_runs,
        "q1_reader_alignment_replay": q1_reader,
        "reporting_boundary": {
            "strict_compile_pass_is_not_whole_case_correctness": True,
            "source_runs_written": False,
            "model_called": False,
            "images_copied_to_frozen_snapshot": True,
            "frozen_images_used_for_q1_reader_alignment": True,
            "q1_reader_alignment_replayed": True,
            "q1_reader_alignment_scope": "only the frozen five groups and seven floors from Q1",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--verify-snapshot", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--failure-table", type=Path)
    args = parser.parse_args()
    manifest = read_json(MANIFEST_PATH)
    if args.manifest_only:
        print(json.dumps({
            "schema": manifest["schema"],
            "counts": manifest["counts"],
            "copied_bytes": manifest["copied_bytes"],
            "model_requests": 0,
        }, ensure_ascii=False, indent=2))
        return
    validation = validate_snapshot(manifest)
    if args.verify_snapshot:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return
    if args.report is None:
        parser.error("replay was not started; pass --report after the package owner confirms")
    if validation["status"] != "pass":
        raise RuntimeError(f"snapshot verification failed: {validation['errors']}")
    report = build_report(manifest)
    write_json(args.report, report)
    if args.failure_table is not None:
        write_failure_markdown(args.failure_table, report)
    print(json.dumps({
        "report": str(args.report),
        "items": report["summary"]["items"],
        "strict_compile_after": report["summary"]["strict_compile_after"],
        "model_requests": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
