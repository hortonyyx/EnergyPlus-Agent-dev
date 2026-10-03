"""Fixed protocol and evaluation helpers for the R1 sm24 facade experiment.

The run manifest and the evaluation references are deliberately separate.  A
caller may build child tasks from the manifest, but only the offline evaluator
accepts the reference file.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image


FACADES = ("north", "south", "east", "west")
CHILD_BUDGET = {"model_calls": 2, "tool_calls": 0, "tokens": 90_000, "seconds": 360}
WINDOW_RE = re.compile(
    r"\bWINDOW\s+floor=(?P<floor>[A-Za-z0-9_-]+)\s+order=(?P<order>\d+)\s+"
    r"width_mm=(?P<width>\d+(?:\.\d+)?)\s+sill_m=(?P<sill>\d+(?:\.\d+)?)\s+"
    r"head_m=(?P<head>\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
COUNT_RE = re.compile(
    r"\bCOUNT\s+floor=(?P<floor>[A-Za-z0-9_-]+)\s+windows=(?P<count>\d+)\b",
    re.IGNORECASE,
)


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_run_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    errors: list[str] = []
    cases = manifest.get("cases", [])
    ids = [row.get("case_id") for row in cases]
    if [row.get("facade") for row in cases] != list(FACADES):
        errors.append("run manifest must contain north/south/east/west once, in fixed order")
    if len(ids) != len(set(ids)):
        errors.append("run case identities must be unique")
    serialized_manifest = json.dumps(manifest, ensure_ascii=False).lower()
    for forbidden in ("reference_answer", "expected_windows", "ground_truth", "rubric"):
        if forbidden in serialized_manifest:
            errors.append(f"run manifest contains evaluation field {forbidden!r}")
    for case in cases:
        path = root / case.get("image", "")
        if not path.is_file():
            errors.append(f"{case.get('case_id')}: image missing")
            continue
        if sha256(path) != case.get("image_sha256"):
            errors.append(f"{case.get('case_id')}: image hash changed")
        with Image.open(path) as opened:
            if [opened.width, opened.height] != case.get("image_size"):
                errors.append(f"{case.get('case_id')}: image dimensions changed")
        if not str(case.get("question", "")).strip():
            errors.append(f"{case.get('case_id')}: empty question")
        if case.get("budget") != CHILD_BUDGET:
            errors.append(f"{case.get('case_id')}: child budget changed")
    return {"ok": not errors, "cases": len(cases), "errors": errors}


def validate_protocol(root: Path, manifest_path: Path, references_path: Path) -> dict[str, Any]:
    run_check = validate_run_manifest(root, manifest_path)
    manifest = load_json(manifest_path)
    references = load_json(references_path)
    errors = list(run_check["errors"])
    ids = [row.get("case_id") for row in manifest.get("cases", [])]
    refs = references.get("cases", [])
    ref_ids = [row.get("case_id") for row in refs]
    if len(ref_ids) != len(set(ref_ids)) or set(ids) != set(ref_ids):
        errors.append("run and reference case identities must be unique and equal")
    if not references.get("evaluation_side_only"):
        errors.append("references must be marked evaluation_side_only")
    special = []
    for ref in refs:
        for window in ref.get("expected_windows", []):
            if window.get("special_4800_east_west"):
                special.append((ref.get("facade"), window.get("order")))
        for basis in ref.get("basis", []):
            path = root / basis.get("path", "")
            if not path.is_file() or sha256(path) != basis.get("sha256"):
                errors.append(f"{ref.get('case_id')}: reference basis missing or hash changed")
    if sorted(special) != [("east", 1), ("west", 5)]:
        errors.append("exactly the east and west 4800 mm windows must be scored separately")
    return {"ok": not errors, "cases": len(manifest.get("cases", [])),
            "special_4800_windows": special, "errors": errors}


def build_tasks(manifest: dict[str, Any], view_ids: dict[str, str], mode: str) -> list[dict[str, Any]]:
    if mode not in {"concurrent", "sequential"}:
        raise ValueError("mode must be concurrent or sequential")
    tasks = []
    for case in manifest["cases"]:
        facade = case["facade"]
        tasks.append({
            "task_id": f"{mode}_{facade}",
            "role_id": "local_observer",
            "question": case["question"],
            "view_ids": [view_ids[case["image_name"]]],
            "notes": [
                "Input kind: original elevation drawing.",
                "Use only the supplied facade image; evaluation references are not supplied.",
                "The complete image is already visible, so answer directly without calling tools.",
            ],
            "budget": case["budget"],
        })
    return tasks


def parse_observation(outcome: dict[str, Any]) -> dict[str, Any]:
    parsed = {"windows": [], "counts": [], "unparsed_statements": []}
    result = outcome.get("result") or {}
    for row in result.get("directly_seen", []):
        statement = row.get("statement", "")
        window = WINDOW_RE.search(statement)
        count = COUNT_RE.search(statement)
        location = row.get("location") or {}
        box = location.get("box_original_pixels")
        if window:
            parsed["windows"].append({
                "floor": window.group("floor"), "order": int(window.group("order")),
                "width_mm": float(window.group("width")), "sill_m": float(window.group("sill")),
                "head_m": float(window.group("head")), "box_original_pixels": box,
                "statement": statement,
            })
        elif count:
            parsed["counts"].append({"floor": count.group("floor"),
                                     "windows": int(count.group("count")), "statement": statement})
        else:
            parsed["unparsed_statements"].append(statement)
    parsed["windows"].sort(key=lambda row: (row["floor"], row["order"]))
    return parsed


def _box_metrics(actual: Any, expected: Any) -> dict[str, Any]:
    if not (isinstance(actual, list) and len(actual) == 4):
        return {"loose_match": False, "intersection_over_union": 0.0,
                "actual_to_expected_area": None}
    ax0, ay0, ax1, ay1 = map(float, actual)
    ex0, ey0, ex1, ey1 = map(float, expected)
    if not (ax0 < ax1 and ay0 < ay1):
        return {"loose_match": False, "intersection_over_union": 0.0,
                "actual_to_expected_area": None}
    intersection = max(0.0, min(ax1, ex1) - max(ax0, ex0)) * max(0.0, min(ay1, ey1) - max(ay0, ey0))
    expected_area = max(1.0, (ex1 - ex0) * (ey1 - ey0))
    actual_area = (ax1 - ax0) * (ay1 - ay0)
    union = actual_area + expected_area - intersection
    ratio = actual_area / expected_area
    # This is only a loose object-localization check.  Requiring overlap and a
    # bounded area ratio prevents a whole-facade box from masquerading as a
    # precise per-window location; no pixel-exact claim is made.
    loose = intersection > 0 and 0.1 <= ratio <= 10.0 and intersection / union >= 0.1
    return {"loose_match": loose, "intersection_over_union": intersection / union,
            "actual_to_expected_area": ratio}


def evaluate_outcome(outcome: dict[str, Any], reference: dict[str, Any], tolerance_m: float = 0.05) -> dict[str, Any]:
    parsed = parse_observation(outcome)
    actual_by_order = {row["order"]: row for row in parsed["windows"]}
    rows = []
    for expected in reference["expected_windows"]:
        actual = actual_by_order.get(expected["order"])
        width_ok = bool(actual) and abs(actual["width_mm"] - expected["width_mm"]) <= 50
        sill_error = abs(actual["sill_m"] - expected["sill_m"]) if actual else None
        head_error = abs(actual["head_m"] - expected["head_m"]) if actual else None
        # Decimal values arrive through binary floats. Keep the stated inclusive
        # 5 cm boundary inclusive instead of rejecting 3.45 - 3.40 as a tiny
        # representation excess over 0.05.
        height_ok = (bool(actual) and sill_error <= tolerance_m + 1e-9
                     and head_error <= tolerance_m + 1e-9)
        location = _box_metrics(actual.get("box_original_pixels") if actual else None,
                                expected["expected_bbox_px"])
        rows.append({
            "order": expected["order"], "expected": expected, "actual": actual,
            "width_within_50mm": width_ok, "sill_error_m": sill_error,
            "head_error_m": head_error, "height_within_5cm": height_ok,
            "loose_localization_matches_window": location["loose_match"],
            "localization_metrics": location,
        })
    expected_count = reference["expected_count_by_floor"]
    count_pairs = [(row["floor"].upper(), row["windows"]) for row in parsed["counts"]]
    actual_counts = {floor: count for floor, count in count_pairs}
    window_keys = [(row["floor"].upper(), row["order"]) for row in parsed["windows"]]
    expected_floors = {floor.upper() for floor in expected_count}
    expected_total = sum(expected_count.values())
    inventory_structure_ok = (
        len(count_pairs) == len(expected_count)
        and len({floor for floor, _ in count_pairs}) == len(count_pairs)
        and {floor for floor, _ in count_pairs} == expected_floors
        and len(window_keys) == expected_total
        and len(set(window_keys)) == len(window_keys)
        and {floor for floor, _ in window_keys} == expected_floors
    )
    count_ok = inventory_structure_ok and all(
        actual_counts.get(floor.upper()) == count for floor, count in expected_count.items())
    special_rows = [row for row in rows if row["expected"].get("special_4800_east_west")]
    return {
        "case_id": reference["case_id"], "facade": reference["facade"],
        "runtime_status": outcome.get("status"), "interface_accepted": bool(outcome.get("result")),
        "expected_count_by_floor": expected_count, "actual_count_by_floor": actual_counts,
        "count_correct": count_ok, "inventory_structure_correct": inventory_structure_ok,
        "parsed_window_entries": len(parsed["windows"]), "windows": rows,
        "height_windows_correct": sum(row["height_within_5cm"] for row in rows),
        "height_windows_total": len(rows),
        "loose_localizations_correct": sum(row["loose_localization_matches_window"] for row in rows),
        "localizations_total": len(rows),
        "special_4800": [{"facade": reference["facade"], "order": row["order"],
                           "width_within_50mm": row["width_within_50mm"],
                           "height_within_5cm": row["height_within_5cm"],
                           "correct": row["width_within_50mm"] and row["height_within_5cm"],
                           "actual": row["actual"]} for row in special_rows],
        "unparsed_statements": parsed["unparsed_statements"],
    }


def evaluate_batches(batch_results: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
    ref_by_id = {row["case_id"]: row for row in references["cases"]}
    modes = {}
    for mode in ("concurrent", "sequential"):
        batch = batch_results[mode]
        cases = []
        for outcome in batch["results"]:
            task_id = (outcome.get("package") or {}).get("task_id", "")
            case_id = task_id.removeprefix(mode + "_")
            cases.append(evaluate_outcome(outcome, ref_by_id[case_id]))
        correct = sum(case["height_windows_correct"] for case in cases)
        total = sum(case["height_windows_total"] for case in cases)
        modes[mode] = {
            "wall_seconds": batch["wall_seconds"], "requests": batch["requests"],
            "reported_usage": batch["reported_usage"], "cases": cases,
            "height_windows_correct": correct, "height_windows_total": total,
            "height_within_5cm_ratio": correct / total if total else 0.0,
            "facade_counts_correct": sum(case["count_correct"] for case in cases),
            "facade_counts_total": len(cases),
            "loose_localizations_correct": sum(case["loose_localizations_correct"] for case in cases),
            "localizations_total": sum(case["localizations_total"] for case in cases),
            "special_4800": [special for case in cases for special in case["special_4800"]],
        }
    return {"schema_version": "runtime-r1-facade-evaluation/v1", "tolerance_m": 0.05,
            "modes": modes, "sampling": "fixed 4 questions x 2 modes; no added samples"}
