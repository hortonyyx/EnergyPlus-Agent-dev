"""Offline replay for Q2 elevation ink alignment and plan/elevation comparison.

This script reads the immutable 2026-10-06/07 run archives and the checked-in
evaluation anchors.  It performs no model request and writes only compact JSON
and Markdown evidence beside this file.

Run from the q2 worktree root with its prepared Python environment::

    .venv/Scripts/python.exe AI_agent/logs/experiments/2026-10-07_quality_q2/replay.py
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.agent.runtime_roles.elevation import attach_ink_review, compare_opening_positions, match_elevation
from src.agent.runtime_roles.elevation_ink import align_elevation_artifact
from src.agent.runtime_roles.height_evidence import derive_z_calibration


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ARCHIVE = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup")
REFERENCES = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis/references"

RUN_SPECS = (
    *(dict(group="role_debug", run=f"sm24_run{number}", case="sm24") for number in range(3, 8)),
    dict(group="role_debug", run="sm21_run1", case="sm21"),
    dict(group="role_debug", run="sm25_run1", case="sm25"),
    dict(group="cmp3", run="sm24_role", case="sm24"),
    dict(group="cmp3", run="sm21_role", case="sm21"),
    dict(group="cmp3", run="sm25_role", case="sm25"),
    dict(group="reader_model_probe", run="qwen27b_r1", case="sm24"),
)

REFERENCE_FILES = {
    "sm21": REFERENCES / "sm21_anchor.json",
    "sm24": REFERENCES / "sm24_anchor.json",
    "sm25": REFERENCES / "sm25-L_anchor.json",
}

TIERS = (0.05, 0.10, 0.30)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def tier(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "unavailable"
    if value <= TIERS[0] + 1e-9:
        return "<=5cm"
    if value <= TIERS[1] + 1e-9:
        return "5-10cm"
    if value <= TIERS[2] + 1e-9:
        return "10-30cm"
    return ">30cm"


def pixel_to_world(calibration: Mapping[str, Any], pixel: float) -> float:
    pixel_start = float(calibration["pixel_start"])
    pixel_end = float(calibration["pixel_end"])
    world_start = float(calibration["world_start_m"])
    world_end = float(calibration["world_end_m"])
    return world_start + (float(pixel) - pixel_start) * (
        (world_end - world_start) / (pixel_end - pixel_start)
    )


def world_span(calibration: Mapping[str, Any], pixels: Iterable[float]) -> list[float]:
    values = sorted(pixel_to_world(calibration, float(pixel)) for pixel in pixels)
    return [values[0], values[1]]


def reference_openings(case: str) -> list[dict[str, Any]]:
    anchor = read_json(REFERENCE_FILES[case])
    rows = []
    for facade in anchor.get("elevation_questions", ()):
        for item in facade.get("openings", ()):
            rows.append({**item, "facade": facade["facade"]})
    return rows


def ordered_pairs(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Ordered evaluation pairing; topology gaps remain explicit.

    The cost scales mirror the production elevation matcher.  This pairing is
    evaluation-only and never changes either side or feeds GT into production.
    """

    if len(left) == len(right):
        return list(zip(range(len(left)), range(len(right)), strict=True)), [], []
    position_scale, width_scale, gap = 0.35, 0.25, 3.0
    rows, columns = len(left) + 1, len(right) + 1
    costs = [[math.inf] * columns for _ in range(rows)]
    actions: list[list[str | None]] = [[None] * columns for _ in range(rows)]
    costs[0][0] = 0.0
    for index in range(1, rows):
        costs[index][0] = index * gap
        actions[index][0] = "left"
    for index in range(1, columns):
        costs[0][index] = index * gap
        actions[0][index] = "right"
    for i in range(1, rows):
        for j in range(1, columns):
            a, b = left[i - 1], right[j - 1]
            match_cost = abs(a["center_m"] - b["center_m"]) / position_scale + abs(a["width_m"] - b["width_m"]) / width_scale
            options = (
                (costs[i - 1][j - 1] + match_cost, "match"),
                (costs[i - 1][j] + gap, "left"),
                (costs[i][j - 1] + gap, "right"),
            )
            costs[i][j], actions[i][j] = min(options, key=lambda item: (item[0], item[1] != "match", item[1]))
    pairs, left_only, right_only = [], [], []
    i, j = len(left), len(right)
    while i or j:
        action = actions[i][j]
        if action == "match":
            pairs.append((i - 1, j - 1)); i -= 1; j -= 1
        elif action == "left":
            left_only.append(i - 1); i -= 1
        elif action == "right":
            right_only.append(j - 1); j -= 1
        else:
            raise AssertionError("ordered pairing backtrace failed")
    return list(reversed(pairs)), list(reversed(left_only)), list(reversed(right_only))


def pair_artifact_to_reference(
    artifact: Mapping[str, Any], alignment: Mapping[str, Any], references: list[dict[str, Any]]
) -> dict[str, Any]:
    calibration = artifact["x_calibration"]
    aligned_by_id = {row["id"]: row for row in alignment["openings"]}
    observed = []
    for opening in artifact.get("openings", ()):
        raw_span = world_span(calibration, opening["x_px"])
        aligned_row = aligned_by_id[opening["id"]]
        aligned_span = aligned_row["aligned_values"].get("world_span_m") or raw_span
        aligned_span = sorted(float(value) for value in aligned_span)
        observed.append({
            "id": opening["id"], "floor_id": opening["floor_id"], "kind": opening["kind"],
            "raw_span_m": raw_span, "aligned_span_m": aligned_span,
            "center_m": sum(raw_span) / 2.0, "width_m": float(opening["width_m"]),
            "raw": {"width_m": float(opening["width_m"]), "sill_m": float(opening["sill_m"]), "head_m": float(opening["head_m"])},
            "aligned": {
                "width_m": float(aligned_row["aligned_values"]["width_m"]),
                "sill_m": float(aligned_row["aligned_values"]["sill_m"]),
                "head_m": float(aligned_row["aligned_values"]["head_m"]),
            },
            "alignment_status": aligned_row["status"],
        })
    relevant = [row for row in references if row["facade"] == artifact["orientation"]]
    pairs_out, observed_only, reference_only = [], [], []
    groups = sorted({(row["floor_id"], row["kind"]) for row in observed + relevant})
    for floor_id, kind in groups:
        left = sorted(
            (row for row in observed if row["floor_id"] == floor_id and row["kind"] == kind),
            key=lambda row: row["center_m"],
        )
        right = []
        for row in relevant:
            if row["floor_id"] != floor_id or row["kind"] != kind:
                continue
            span = sorted(float(value) for value in row["span_m"])
            right.append({**row, "span_m": span, "center_m": sum(span) / 2.0, "width_m": float(row["width_m"])})
        right.sort(key=lambda row: row["center_m"])
        pairs, only_left, only_right = ordered_pairs(left, right)
        for left_index, right_index in pairs:
            item, ref = left[left_index], right[right_index]
            raw_position = max(abs(a - b) for a, b in zip(item["raw_span_m"], ref["span_m"], strict=True))
            aligned_position = max(abs(a - b) for a, b in zip(item["aligned_span_m"], ref["span_m"], strict=True))
            raw = {
                "position_m": raw_position,
                "width_m": abs(item["raw"]["width_m"] - ref["width_m"]),
                "sill_m": abs(item["raw"]["sill_m"] - float(ref["sill_m"])),
                "head_m": abs(item["raw"]["head_m"] - float(ref["head_m"])),
            }
            aligned = {
                "position_m": aligned_position,
                "width_m": abs(item["aligned"]["width_m"] - ref["width_m"]),
                "sill_m": abs(item["aligned"]["sill_m"] - float(ref["sill_m"])),
                "head_m": abs(item["aligned"]["head_m"] - float(ref["head_m"])),
            }
            pairs_out.append({
                "artifact_opening_id": item["id"], "reference_opening_id": ref["id"],
                "facade": artifact["orientation"], "floor_id": floor_id, "kind": kind,
                "raw_span_m": item["raw_span_m"], "aligned_span_m": item["aligned_span_m"],
                "reference_span_m": ref["span_m"], "raw_deviation_m": raw,
                "aligned_deviation_m": aligned, "raw_tiers": {key: tier(value) for key, value in raw.items()},
                "aligned_tiers": {key: tier(value) for key, value in aligned.items()},
                "alignment_status": item["alignment_status"],
            })
        observed_only.extend({"floor_id": floor_id, "kind": kind, "id": left[index]["id"]} for index in only_left)
        reference_only.extend({"floor_id": floor_id, "kind": kind, "id": right[index]["id"]} for index in only_right)
    return {"pairs": pairs_out, "artifact_only": observed_only, "reference_only": reference_only}


def find_image(run_root: Path, submission: Path, name: str) -> Path | None:
    candidates = (
        run_root / "bim/images" / name,
        submission.parent / "images" / name,
        submission.parent.parent / "images" / name,
    )
    return next((path for path in candidates if path.is_file()), None)


def discover_artifacts(spec: Mapping[str, str]) -> list[dict[str, Any]]:
    run_root = ARCHIVE / spec["group"] / spec["run"]
    rows = []
    for submission in sorted(run_root.rglob("reader_submission.json")):
        envelope = read_json(submission)
        if envelope.get("role_id") != "elevation_reader":
            continue
        artifact = envelope["artifact"]
        image = find_image(run_root, submission, envelope.get("image") or artifact["image"])
        if image is None:
            raise FileNotFoundError(f"image for {submission} was not found")
        z_evidence = derive_z_calibration(artifact.get("elevations", ()))
        z_calibration = z_evidence.get("calibration")
        replay_artifact = copy.deepcopy(artifact)
        if z_calibration is not None:
            replay_artifact["z_calibration"] = z_calibration
        alignment = align_elevation_artifact(image, replay_artifact)
        reference_pairing = pair_artifact_to_reference(
            artifact, alignment, reference_openings(spec["case"])
        )
        rows.append({
            "group": spec["group"], "run": spec["run"], "case": spec["case"],
            "facade": artifact["orientation"], "target": envelope.get("target"),
            "submission_path": str(submission), "submission_sha256": sha256(submission),
            "artifact_content_sha256": json_sha256(artifact),
            "artifact_sha256_recorded": envelope.get("artifact_sha256") or artifact.get("artifact_sha256"),
            "normalized_artifact_sha256_recorded": artifact.get("artifact_sha256"),
            "image_path": str(image), "image_sha256": sha256(image),
            "opening_count": len(artifact.get("openings", ())), "mtime_ns": submission.stat().st_mtime_ns,
            "x_calibration": artifact.get("x_calibration"), "z_calibration": z_calibration,
            "z_calibration_evidence": z_evidence, "alignment": alignment,
            "reference_pairing": reference_pairing,
            "_artifact": artifact,
        })
    return rows


def selected_source(run_root: Path) -> tuple[str | None, Path | None, Mapping[str, Any] | None]:
    selection = run_root / "bim/delivery_selection.json"
    if not selection.is_file():
        return None, None, None
    candidate = read_json(selection).get("candidate")
    path = run_root / "bim" / str(candidate) / "source_model.json"
    if not candidate or not path.is_file():
        return candidate, path, None
    return candidate, path, read_json(path)


def opening_floor_ids(source: Mapping[str, Any]) -> dict[str, str]:
    floors = {row["id"]: row["floor_id"] for row in source.get("spaces", ())}
    result = {}
    for opening in source.get("openings", ()):
        values = {floors[item] for item in opening.get("space_ids", ()) if item in floors}
        if len(values) == 1:
            result[opening["id"]] = next(iter(values))
    return result


def accepted_plan_trials(run_root: Path) -> dict[str, dict[str, Any]]:
    """Load the hash-bound plan-reader trial used by PositionReview."""

    bindings_path = run_root / "role_floor_sources.json"
    state_path = run_root / "role_state.json"
    if not bindings_path.is_file() or not state_path.is_file():
        return {}
    readers = {row["task_id"]: row for row in read_json(state_path).get("readers", ())}
    output = {}
    for floor_id, binding in sorted(read_json(bindings_path).items()):
        record = readers.get(binding["task_id"])
        if record is None:
            continue
        artifact_path = Path(record["artifact"]["path"])
        if len(artifact_path.parts) < 2 or artifact_path.parts[0] != "tasks":
            continue
        task_root = run_root / "tasks" / artifact_path.parts[1]
        submission_path = task_root / "bim/reader_submission.json"
        if not submission_path.is_file():
            continue
        submission = read_json(submission_path)
        trial_candidate = submission["validation"]["candidate"]
        source_path = task_root / "bim/trial_workspace" / trial_candidate / "source_model.json"
        if not source_path.is_file():
            continue
        if sha256(source_path) != binding["source_sha256"]:
            raise AssertionError(f"accepted plan trial source hash changed: {source_path}")
        if record["artifact"]["sha256"] != binding["artifact_sha256"]:
            raise AssertionError(f"accepted plan artifact binding changed: {submission_path}")
        source = read_json(source_path)
        output[floor_id] = {
            "task_id": binding["task_id"], "artifact_sha256": binding["artifact_sha256"],
            "source_sha256": binding["source_sha256"], "trial_candidate": trial_candidate,
            "source_path": str(source_path), "submission_path": str(submission_path),
            "image": submission.get("image"), "artifact": submission.get("artifact", {}),
            "source": source,
        }
    return output


def source_opening_span(opening: Mapping[str, Any], axis: str) -> list[float]:
    index = 0 if axis == "x" else 1
    return [min(float(point[index]) for point in opening["vertices"]),
            max(float(point[index]) for point in opening["vertices"])]


def plan_trial_opening(trials: Mapping[str, Any], item: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    trial = trials.get(item["floor_id"])
    if trial is None:
        return None, None
    identity = item["source_opening_id"]
    seed_id = identity.removeprefix(item["floor_id"] + ":")
    opening = next((row for row in trial["source"].get("openings", ())
                    if row["id"] in {identity, seed_id}), None)
    return trial, opening


def plan_lineage_audit(source: Mapping[str, Any], trials: Mapping[str, Any]) -> dict[str, Any]:
    """Compare every final exterior XY box with its accepted plan trial."""

    floors = opening_floor_ids(source)
    changed, missing = [], []
    compared = 0
    for opening in source.get("openings", ()):
        if not opening.get("exterior"):
            continue
        floor_id = floors.get(opening["id"])
        trial = trials.get(floor_id)
        seed_id = opening["id"].removeprefix((floor_id or "") + ":")
        trial_opening = next((row for row in (trial or {}).get("source", {}).get("openings", ())
                              if row["id"] in {opening["id"], seed_id}), None)
        if trial_opening is None:
            missing.append({"floor_id": floor_id, "source_opening_id": opening["id"],
                            "reason": "accepted_plan_trial_opening_missing"})
            continue
        compared += 1
        old = [
            min(float(point[0]) for point in trial_opening["vertices"]),
            max(float(point[0]) for point in trial_opening["vertices"]),
            min(float(point[1]) for point in trial_opening["vertices"]),
            max(float(point[1]) for point in trial_opening["vertices"]),
        ]
        new = [
            min(float(point[0]) for point in opening["vertices"]),
            max(float(point[0]) for point in opening["vertices"]),
            min(float(point[1]) for point in opening["vertices"]),
            max(float(point[1]) for point in opening["vertices"]),
        ]
        differences = [b - a for a, b in zip(old, new, strict=True)]
        if max(abs(value) for value in differences) > 1e-7:
            changed.append({
                "floor_id": floor_id, "source_opening_id": opening["id"],
                "accepted_plan_trial_xy_bounds_m": old, "final_candidate_xy_bounds_m": new,
                "differences_m": differences, "max_abs_difference_m": max(abs(value) for value in differences),
            })
    exterior = sum(1 for row in source.get("openings", ()) if row.get("exterior"))
    return {
        "final_exterior_opening_count": exterior, "compared_count": compared,
        "unchanged_count": compared - len(changed), "changed_count": len(changed),
        "missing_from_accepted_trial_count": len(missing), "changed": changed, "missing": missing,
    }


def adjusted_artifact(artifact: Mapping[str, Any], alignment: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(artifact)
    result.pop("artifact_sha256", None)
    by_id = {row["id"]: row for row in alignment["openings"]}
    for opening in result.get("openings", ()):
        values = by_id[opening["id"]]["aligned_values"]
        for field in ("x_px", "width_m", "sill_m", "head_m"):
            if values.get(field) is not None:
                opening[field] = copy.deepcopy(values[field])
    result["ink_alignment"] = copy.deepcopy(alignment)
    return result


def plan_elevation_rows(
    source: Mapping[str, Any], artifact_row: Mapping[str, Any], candidate: str,
    trials: Mapping[str, Any],
) -> dict[str, Any]:
    artifact = adjusted_artifact(artifact_row["_artifact"], artifact_row["alignment"])
    report = match_elevation(source, artifact, candidate=candidate)
    rows, unavailable = [], []
    bucket_names = {"le_10cm": "<=10cm", "10_30cm": "10-30cm", "gt_30cm": ">30cm"}
    for item in report.get("position_comparisons", ()):
        # First verify the production matcher exposed the raw candidate span
        # faithfully.  The review decision itself then uses the separately
        # bound plan-reader trial, exactly as PositionReview does.
        candidate_comparison = compare_opening_positions(item["plan_span_m"], item["elevation_span_m"])
        for field in ("differences_m", "max_difference_m", "bucket"):
            if candidate_comparison[field] != item[field]:
                raise AssertionError(
                    f"position comparison integration disagrees for {item['artifact_opening_id']}: {field}"
                )
        trial, trial_opening = plan_trial_opening(trials, item)
        if trial is None or trial_opening is None:
            unavailable.append({
                "facade": report["orientation"], "floor_id": item["floor_id"], "kind": item["kind"],
                "artifact_opening_id": item["artifact_opening_id"],
                "source_opening_id": item["source_opening_id"],
                "type": "accepted_plan_trial_opening_missing", "status": "reread",
                "reason": "accepted plan trial has no independent opening span",
                "one_sided_conflict": {
                    "final_source_opening_id": item["source_opening_id"],
                    "elevation_artifact_opening_id": item["artifact_opening_id"],
                    "accepted_plan_trial_opening_id": None,
                },
                "final_candidate_plan_span_m": item["plan_span_m"],
                "elevation_span_m": item["elevation_span_m"],
            })
            continue
        trial_span = source_opening_span(trial_opening, item["world_axis"])
        independent = compare_opening_positions(trial_span, item["elevation_span_m"])
        numeric_status = independent["status"]
        independent.update(
            reader_width_m=item.get("reader_width_m"),
            width_span_conflict=copy.deepcopy(item.get("width_span_conflict")),
        )
        attach_ink_review(independent, item.get("ink_inconsistencies", ()))
        seed_id = item["source_opening_id"].removeprefix(item["floor_id"] + ":")
        evidence = [row for row in trial["artifact"].get("evidence", ())
                    if row.get("item") == "plan.openings:" + seed_id]
        located = next((row for row in evidence if row.get("bbox")), {})
        candidate_trial = compare_opening_positions(trial_span, item["plan_span_m"])
        rows.append({
            "facade": report["orientation"], "floor_id": item["floor_id"], "kind": item["kind"],
            "artifact_opening_id": item["artifact_opening_id"], "source_opening_id": item["source_opening_id"],
            "world_axis": item["world_axis"],
            "elevation_span_m": item["elevation_span_m"], "plan_span_m": trial_span,
            "plan_width_m": trial_span[1] - trial_span[0], "elevation_width_m": item["elevation_width_m"],
            "differences_m": independent["differences_m"], "max_difference_m": independent["max_difference_m"],
            "max_endpoint_difference_m": max(abs(independent["differences_m"][name]) for name in ("left", "right")),
            "tier": bucket_names[independent["bucket"]], "status": independent["status"],
            "numeric_status": numeric_status,
            "requires_both_views": independent["requires_both_views"],
            "ink_inconsistencies": independent["ink_inconsistencies"],
            "ink_max_difference_m": independent["ink_max_difference_m"],
            "reader_width_m": independent["reader_width_m"],
            "width_span_conflict": independent["width_span_conflict"],
            "identity_matched": item["identity_matched"],
            "horizontal_fit_used_for_identity": bool(item.get("identity_fit")),
            "final_candidate_plan_span_m": item["plan_span_m"],
            "final_candidate_vs_plan_trial": candidate_trial,
            "plan_evidence": {
                "basis": "accepted_plan_reader_trial", "task_id": trial["task_id"],
                "artifact_sha256": trial["artifact_sha256"], "source_sha256": trial["source_sha256"],
                "trial_candidate": trial["trial_candidate"], "source_path": trial["source_path"],
                "submission_path": trial["submission_path"], "image": trial["image"],
                "bbox": located.get("bbox"), "evidence": evidence,
            },
            "elevation_evidence": item.get("elevation_evidence"),
        })
    return {
        "match_id": report.get("match_id"), "rows": rows,
        "counts": dict(Counter(row["tier"] for row in rows)),
        "ink_inconsistent_opening_count": sum(bool(row["ink_inconsistencies"]) for row in rows),
        "ink_inconsistency_item_count": sum(len(row["ink_inconsistencies"]) for row in rows),
        "width_span_conflict_count": sum(row["width_span_conflict"] is not None for row in rows),
        "plan_trial_unavailable": unavailable,
        "elevation_only": report.get("elevation_only", ()), "plan_only": report.get("source_only", ()),
        "other_conflicts": [row for row in report.get("conflicts", ()) if row.get("type") != "position_or_width_conflict"],
    }


def aggregate_tiers(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for state, field in (("before", "raw_deviation_m"), ("after", "aligned_deviation_m")):
        result[state] = {}
        for metric in ("position_m", "width_m", "sill_m", "head_m"):
            counts = Counter()
            for artifact in artifacts:
                for pair in artifact["reference_pairing"]["pairs"]:
                    counts[tier(pair[field][metric])] += 1
            result[state][metric] = {name: counts[name] for name in ("<=5cm", "5-10cm", "10-30cm", ">30cm", "unavailable")}
    return result


def numeric_change_audit(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    """List every effective numeric change before considering reference coverage."""

    rows = []
    regressions = []
    unpaired_changes = 0
    epsilon = 1e-9
    for artifact in artifacts:
        raw_by_id = {row["id"]: row for row in artifact["_artifact"].get("openings", ())}
        ref_by_id = {
            row["artifact_opening_id"]: row
            for row in artifact["reference_pairing"]["pairs"]
        }
        for alignment in artifact["alignment"]["openings"]:
            opening = raw_by_id[alignment["id"]]
            original = alignment["original_values"]
            effective = alignment["aligned_values"]
            original_span = world_span(artifact["x_calibration"], original["x_px"])
            effective_span = sorted(float(value) for value in effective["world_span_m"])
            changes = {
                "position_m": max(abs(a - b) for a, b in zip(original_span, effective_span, strict=True)),
                "width_m": abs(float(effective["width_m"]) - float(original["width_m"])),
                "sill_m": abs(float(effective["sill_m"]) - float(original["sill_m"])),
                "head_m": abs(float(effective["head_m"]) - float(original["head_m"])),
            }
            changed = {key: value for key, value in changes.items() if value > epsilon}
            if not changed:
                continue
            reference = ref_by_id.get(opening["id"])
            quality = None
            if reference is None:
                unpaired_changes += 1
            else:
                quality = {
                    metric: {
                        "before_m": reference["raw_deviation_m"][metric],
                        "after_m": reference["aligned_deviation_m"][metric],
                        "before_tier": reference["raw_tiers"][metric],
                        "after_tier": reference["aligned_tiers"][metric],
                        "not_worse": reference["aligned_deviation_m"][metric]
                        <= reference["raw_deviation_m"][metric] + epsilon,
                    }
                    for metric in ("position_m", "width_m", "sill_m", "head_m")
                }
                for metric, result in quality.items():
                    if not result["not_worse"]:
                        regressions.append({
                            "group": artifact["group"], "run": artifact["run"],
                            "facade": artifact["facade"], "opening_id": opening["id"],
                            "metric": metric, **result,
                        })
            rows.append({
                "group": artifact["group"], "run": artifact["run"], "case": artifact["case"],
                "facade": artifact["facade"], "floor_id": opening["floor_id"],
                "opening_id": opening["id"], "kind": opening["kind"],
                "evidence_type": opening["evidence_type"],
                "submission_path": artifact["submission_path"],
                "submission_sha256": artifact["submission_sha256"],
                "applied_fields": alignment["applied_fields"], "changed_metrics_m": changed,
                "original_values": original, "effective_values": effective,
                "candidate_bbox_px": alignment["candidate_bbox_px"],
                "effective_bbox_px": alignment["effective_bbox_px"],
                "field_decisions": alignment["field_decisions"],
                "floor_contact": alignment["floor_contact"],
                "reference_status": "paired" if reference is not None else "unpaired",
                "reference_quality": quality,
            })
    if regressions:
        raise AssertionError(f"effective ink alignment worsened reference metrics: {regressions}")
    return {
        "changed_opening_count": len(rows),
        "paired_changed_opening_count": len(rows) - unpaired_changes,
        "unpaired_changed_opening_count": unpaired_changes,
        "reference_regression_count": len(regressions),
        "all_paired_changes_not_worse": not regressions,
        "rows": rows,
    }


def ink_inconsistency_audit(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for artifact in artifacts:
        raw_by_id = {row["id"]: row for row in artifact["_artifact"].get("openings", ())}
        for alignment in artifact["alignment"]["openings"]:
            opening = raw_by_id[alignment["id"]]
            for item in alignment["inconsistencies"]:
                rows.append({
                    "group": artifact["group"], "run": artifact["run"], "case": artifact["case"],
                    "facade": artifact["facade"], "floor_id": opening["floor_id"],
                    "opening_id": opening["id"], "kind": opening["kind"],
                    "submission_path": artifact["submission_path"],
                    "submission_sha256": artifact["submission_sha256"],
                    **item,
                })
    fields = Counter(row["field"] for row in rows)
    evidence_types = Counter(row["evidence_type"] for row in rows)
    return {
        "item_count": len(rows),
        "opening_count": len({(row["submission_sha256"], row["opening_id"]) for row in rows}),
        "by_field": dict(sorted(fields.items())),
        "by_evidence_type": dict(sorted(evidence_types.items())),
        "rows": rows,
    }


def width_span_conflict_audit(plan_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep retained-reader-width conflicts separate from unique-ink review."""

    rows = []
    for run in plan_runs:
        for facade, report in sorted(run.get("facades", {}).items()):
            for comparison in report.get("rows", ()):
                evidence = comparison["elevation_evidence"]
                evidence_type = evidence["evidence_type"]
                difference = abs(
                    float(comparison["reader_width_m"])
                    - float(comparison["elevation_width_m"])
                )
                if evidence_type == "pixels" or difference <= 1e-7:
                    continue
                conflict = comparison.get("width_span_conflict")
                calibration = evidence["x_calibration"]
                tolerance = max(
                    0.05,
                    2 * abs(
                        (calibration["world_end_m"] - calibration["world_start_m"])
                        / (calibration["pixel_end"] - calibration["pixel_start"])
                    ),
                )
                rows.append({
                    "group": run["group"], "run": run["run"], "case": run["case"],
                    "facade": facade, "floor_id": comparison["floor_id"],
                    "artifact_opening_id": comparison["artifact_opening_id"],
                    "source_opening_id": comparison["source_opening_id"],
                    "evidence_type": evidence_type,
                    "numeric_bucket": comparison["tier"],
                    "numeric_status": comparison["numeric_status"],
                    "review_status": comparison["status"],
                    "requires_both_views": comparison["requires_both_views"],
                    "reader_width_m": comparison["reader_width_m"],
                    "pixel_span_width_m": comparison["elevation_width_m"],
                    "difference_m": difference,
                    "tolerance_m": tolerance,
                    "use_elevation_allowed": False,
                    "pending_conflict": conflict is not None,
                    "reason": (
                        conflict["reason"] if conflict is not None
                        else "non_pixel_reader_width_differs_from_pixel_interval; use_elevation_requires_reread"
                    ),
                })
    by_run = {}
    for identity in sorted({f"{row['group']}/{row['run']}" for row in rows}):
        selected = [row for row in rows if f"{row['group']}/{row['run']}" == identity]
        by_run[identity] = {
            "guarded_difference_count": len(selected),
            "pending_conflict_count": sum(row["pending_conflict"] for row in selected),
        }
    return {
        "guarded_difference_count": len(rows),
        "pending_conflict_count": sum(row["pending_conflict"] for row in rows),
        "guard_only_count": sum(not row["pending_conflict"] for row in rows),
        "by_run": by_run,
        "rows": rows,
    }


def alignment_diagnostics(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    edge_statuses = {"horizontal": Counter(), "vertical": Counter()}
    z_statuses = Counter()
    paired = artifact_only = reference_only = 0
    candidate_moved_edges = actual_moved_edges = applied_fields = inconsistency_count = 0
    floor_contact_openings = floor_contact_sill_retained = 0
    unmatched_reasons: dict[str, Counter[str]] = defaultdict(Counter)
    transitions = {
        metric: Counter() for metric in ("position_m", "width_m", "sill_m", "head_m")
    }
    rank = {"<=5cm": 0, "5-10cm": 1, "10-30cm": 2, ">30cm": 3, "unavailable": 4}
    for artifact in artifacts:
        summary = artifact["alignment"]["summary"]
        candidate_moved_edges += summary["candidate_moved_edge_count"]
        actual_moved_edges += summary["moved_edge_count"]
        applied_fields += summary["applied_field_count"]
        inconsistency_count += summary["inconsistency_count"]
        z_statuses[artifact["z_calibration_evidence"]["status"]] += 1
        paired += len(artifact["reference_pairing"]["pairs"])
        unmatched_artifact = artifact["reference_pairing"]["artifact_only"]
        unmatched_reference = artifact["reference_pairing"]["reference_only"]
        artifact_only += len(unmatched_artifact)
        reference_only += len(unmatched_reference)
        if unmatched_artifact or unmatched_reference:
            artifact_floors = {row["floor_id"] for row in unmatched_artifact}
            reference_floors = {row["floor_id"] for row in unmatched_reference}
            artifact_kinds = Counter(row["kind"] for row in unmatched_artifact)
            reference_kinds = Counter(row["kind"] for row in unmatched_reference)
            if artifact_kinds == reference_kinds and artifact_floors.isdisjoint(reference_floors):
                reason = "floor_label_mismatch"
            else:
                reason = "position_or_order_conflict"
            unmatched_reasons[reason]["artifact_only"] += len(unmatched_artifact)
            unmatched_reasons[reason]["reference_only"] += len(unmatched_reference)
            unmatched_reasons[reason]["submissions"] += 1
        for opening in artifact["alignment"]["openings"]:
            if opening["floor_contact"]:
                floor_contact_openings += 1
                if opening["field_decisions"].get("sill_m") == "retained_floor_contact":
                    floor_contact_sill_retained += 1
            for name in ("left", "right"):
                edge_statuses["horizontal"][opening["edges"][name]["status"]] += 1
            for name in ("top", "bottom"):
                edge_statuses["vertical"][opening["edges"][name]["status"]] += 1
        for pair in artifact["reference_pairing"]["pairs"]:
            for metric in transitions:
                before = tier(pair["raw_deviation_m"][metric])
                after = tier(pair["aligned_deviation_m"][metric])
                change = "same" if rank[before] == rank[after] else "improved" if rank[after] < rank[before] else "worsened"
                transitions[metric][change] += 1
    return {
        "edge_status_counts": {axis: dict(sorted(counts.items())) for axis, counts in edge_statuses.items()},
        "candidate_moved_edge_count": candidate_moved_edges,
        "moved_edge_count": actual_moved_edges,
        "applied_field_count": applied_fields,
        "inconsistency_count": inconsistency_count,
        "floor_contact_opening_count": floor_contact_openings,
        "floor_contact_sill_retained_count": floor_contact_sill_retained,
        "z_calibration_status_counts": dict(sorted(z_statuses.items())),
        "reference_pairing_counts": {
            "paired": paired, "artifact_only": artifact_only, "reference_only": reference_only
        },
        "reference_pairing_unmatched_reasons": {
            reason: dict(sorted(counts.items()))
            for reason, counts in sorted(unmatched_reasons.items())
        },
        "reference_tier_transitions": {
            metric: {name: counts[name] for name in ("improved", "same", "worsened")}
            for metric, counts in transitions.items()
        },
    }


def run_coverage(spec: Mapping[str, str], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    run_root = ARCHIVE / spec["group"] / spec["run"]
    rows = [row for row in artifacts if row["group"] == spec["group"] and row["run"] == spec["run"]]
    latest = latest_per_facade(rows)
    expected = sorted({row["facade"] for row in reference_openings(spec["case"])})
    present = sorted({row["facade"] for row in latest})
    reader_records = []
    for path in sorted(run_root.rglob("reader_record.json")):
        record = read_json(path)
        if record.get("role_id") != "elevation_reader":
            continue
        reader_records.append({
            "target": record.get("target"), "status": record.get("status"),
            "path": str(path),
        })
    return {
        "group": spec["group"], "run": spec["run"], "case": spec["case"],
        "submission_count": len(rows), "latest_facade_submission_count": len(latest),
        "all_submission_opening_count": sum(row["opening_count"] for row in rows),
        "latest_opening_count": sum(row["opening_count"] for row in latest),
        "expected_facades": expected, "present_facades": present,
        "missing_facades": sorted(set(expected) - set(present)),
        "coverage": "complete" if set(expected) == set(present) else "incomplete",
        "delivery_selection_exists": (run_root / "bim/delivery_selection.json").is_file(),
        "reader_records": reader_records,
    }


def latest_per_facade(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen = {}
    for row in artifacts:
        key = (row["group"], row["run"], row["facade"])
        if key not in chosen or (row["mtime_ns"], row["submission_path"]) > (chosen[key]["mtime_ns"], chosen[key]["submission_path"]):
            chosen[key] = row
    return sorted(chosen.values(), key=lambda row: (row["group"], row["run"], row["facade"]))


def closer_side(plan_error: float, elevation_error: float, *, epsilon: float = 0.005) -> str:
    if abs(plan_error - elevation_error) <= epsilon:
        return "tie_within_5mm"
    return "plan" if plan_error < elevation_error else "elevation"


def sm25_adjudication(artifacts: list[dict[str, Any]], plan_runs: Mapping[tuple[str, str], Any]) -> list[dict[str, Any]]:
    target = next(row for row in artifacts if row["group"] == "cmp3" and row["run"] == "sm25_role")
    # This function is invoked once per latest facade below; kept here for signature clarity.
    del target
    refs = {row["id"]: row for row in reference_openings("sm25")}
    output = []
    for artifact in artifacts:
        if artifact["group"] != "cmp3" or artifact["run"] != "sm25_role":
            continue
        plan = plan_runs[(artifact["group"], artifact["run"])]["facades"].get(artifact["facade"])
        if not plan:
            continue
        plan_run = plan_runs[(artifact["group"], artifact["run"])]
        ref_by_artifact = {row["artifact_opening_id"]: row for row in artifact["reference_pairing"]["pairs"]}
        for row in plan["rows"]:
            if row["max_difference_m"] <= 0.10 + 1e-9:
                continue
            paired = ref_by_artifact.get(row["artifact_opening_id"])
            if paired is None:
                continue
            reference = refs[paired["reference_opening_id"]]
            ref_span = sorted(float(value) for value in reference["span_m"])
            plan_error = max(abs(a - b) for a, b in zip(row["plan_span_m"], ref_span, strict=True))
            elevation_error = max(abs(a - b) for a, b in zip(row["elevation_span_m"], ref_span, strict=True))
            plan_width_error = abs((row["plan_span_m"][1] - row["plan_span_m"][0]) - float(reference["width_m"]))
            elevation_width_error = abs((row["elevation_span_m"][1] - row["elevation_span_m"][0]) - float(reference["width_m"]))
            output.append({
                **row, "reference_opening_id": reference["id"], "reference_span_m": ref_span,
                "plan_reference_position_error_m": plan_error,
                "elevation_reference_position_error_m": elevation_error,
                "closer_for_position": closer_side(plan_error, elevation_error),
                "plan_reference_width_error_m": plan_width_error,
                "elevation_reference_width_error_m": elevation_width_error,
                "closer_for_width": closer_side(plan_width_error, elevation_width_error),
                "plan_candidate": row["plan_evidence"].get("trial_candidate"),
                "plan_source_model_path": row["plan_evidence"].get("source_path"),
                "final_delivery_candidate": plan_run.get("candidate"),
                "final_delivery_source_model_path": plan_run.get("source_model_path"),
                "plan_image_path": str(
                    ARCHIVE / artifact["group"] / artifact["run"] / "bim/images"
                    / f"{int(str(row['floor_id']).lstrip('Ff'))}f_view.png"
                ),
                "elevation_submission_path": artifact["submission_path"],
                "elevation_image_path": artifact["image_path"],
            })
    return sorted(output, key=lambda row: (-row["max_difference_m"], row["facade"], row["floor_id"], row["artifact_opening_id"]))


def compact_artifact(row: dict[str, Any]) -> dict[str, Any]:
    result = {key: value for key, value in row.items() if key != "_artifact"}
    return result


def markdown_report(evidence: Mapping[str, Any]) -> str:
    lines = [
        "# Q2-E 离线重放",
        "",
        "本报告由 `replay.py` 只读历史产物生成；0 次 work model／外部模型请求。参照仅用于评价，未进入生产对齐与平立面匹配。",
        "",
        f"共清点 {evidence['inventory']['submission_count']} 份真实立面提交，{evidence['inventory']['unique_submission_sha256']} 个不同提交文件哈希；按每次运行每个立面取最后一次提交后为 {evidence['inventory']['latest_facade_submission_count']} 份。",
        "",
        "## 指定运行覆盖",
        "",
        "| 运行 | 提交数 | 末次立面 | 末次开口 | 覆盖 | 缺失 |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in evidence["run_coverage"]:
        missing = ", ".join(row["missing_facades"]) or "—"
        lines.append(
            f"| {row['group']}/{row['run']} | {row['submission_count']} | "
            f"{row['latest_facade_submission_count']} | {row['latest_opening_count']} | {row['coverage']} | {missing} |"
        )
    lines += [
        "",
        "## 对参照的 5／10／30 cm 分档（全部提交，含重复/返工）",
        "",
        "| 状态 | 指标 | ≤5 cm | 5–10 cm | 10–30 cm | >30 cm | 不可用 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    labels = {"position_m": "沿墙端点位置", "width_m": "宽度", "sill_m": "窗台/门槛", "head_m": "窗顶/门顶"}
    for state, state_label in (("before", "对齐前"), ("after", "对齐后")):
        for metric, label in labels.items():
            row = evidence["reference_tiers"][state][metric]
            lines.append(f"| {state_label} | {label} | {row['<=5cm']} | {row['5-10cm']} | {row['10-30cm']} | {row['>30cm']} | {row['unavailable']} |")
    lines += [
        "",
        "按每次运行每个立面只保留最后一次提交的同口径统计也保存在 `evidence_replay.json.reference_tiers_latest_per_facade`，用于避免返工重复计权。",
        "",
    ]
    diagnostics = evidence["alignment_diagnostics"]
    horizontal = diagnostics["edge_status_counts"]["horizontal"]
    vertical = diagnostics["edge_status_counts"]["vertical"]
    transitions = diagnostics["reference_tier_transitions"]
    pairing = diagnostics["reference_pairing_counts"]
    unmatched_reasons = diagnostics["reference_pairing_unmatched_reasons"]
    floor_mismatch = unmatched_reasons.get("floor_label_mismatch", {})
    position_conflict = unmatched_reasons.get("position_or_order_conflict", {})
    lines.append(
        f"读图侧共有 {pairing['paired'] + pairing['artifact_only']} 个开口槽位，参照侧也有 "
        f"{pairing['paired'] + pairing['reference_only']} 个；其中只有 {pairing['paired']} 对具备同 facade/floor/kind 且逐序可接受的身份，"
        f"所以尺寸档位分母是 {pairing['paired']}，不是 {pairing['paired'] + pairing['artifact_only']}。"
    )
    lines.append(
        f"未评分的读图侧 {pairing['artifact_only']} 扇和参照侧 {pairing['reference_only']} 扇中，"
        f"{floor_mismatch.get('artifact_only', 0)}+{floor_mismatch.get('reference_only', 0)} 扇来自楼层标签不一致"
        "（`GF`/`PLAN.F*` 对 `F*`）；"
        f"{position_conflict.get('artifact_only', 0)}+{position_conflict.get('reference_only', 0)} 扇来自位置或次序冲突。"
        "它们保留在清单中，但不强配、不计入误差档位；这些数量按 48 份提交统计，含重复/返工。"
    )
    lines.append(
        f"候选墨线中，水平边有 {horizontal.get('confirmed', 0)} 条原位确认、{horizontal.get('aligned', 0)} 条候选移动；"
        f"竖向边有 {vertical.get('confirmed', 0)} 条原位确认、{vertical.get('aligned', 0)} 条候选移动、"
        f"{vertical.get('missing_calibration', 0)} 条因缺少合格标定而不搜索。"
        f"另有水平 {horizontal.get('ambiguous_lines', 0)} 条、竖向 {vertical.get('ambiguous_lines', 0)} 条因候选墨线不唯一而不采纳。"
        f"候选移动边合计 {diagnostics['candidate_moved_edge_count']}，按证据策略实际采纳移动边 "
        f"{diagnostics['moved_edge_count']}、采纳字段 {diagnostics['applied_field_count']}；"
        f"保留值与唯一墨线超过阈值的不一致 {diagnostics['inconsistency_count']} 项。"
        f"识别出 {diagnostics['floor_contact_opening_count']} 个门槛接触已保存 floor/ground 观测，"
        f"其中 {diagnostics['floor_contact_sill_retained_count']} 个明确以 `retained_floor_contact` 保留原 sill。"
    )
    lines.append(
        "相对参照的档位变化：位置 "
        f"{transitions['position_m']['improved']} 改善/{transitions['position_m']['same']} 不变/{transitions['position_m']['worsened']} 变差；"
        "宽度 "
        f"{transitions['width_m']['improved']} 改善/{transitions['width_m']['same']} 不变/{transitions['width_m']['worsened']} 变差；"
        "窗台/门槛 "
        f"{transitions['sill_m']['improved']} 改善/{transitions['sill_m']['same']} 不变/{transitions['sill_m']['worsened']} 变差；"
        "窗顶/门顶 "
        f"{transitions['head_m']['improved']} 改善/{transitions['head_m']['same']} 不变/{transitions['head_m']['worsened']} 变差。"
    )
    changes = evidence["numeric_change_audit"]
    lines += [
        "",
        "## A 实际数值变化与四指标回归闸",
        "",
        f"48 份提交中有 {changes['changed_opening_count']} 扇有效数值发生变化，其中参照可配对 "
        f"{changes['paired_changed_opening_count']} 扇、不可配对 {changes['unpaired_changed_opening_count']} 扇；"
        f"逐项精确误差回归为 {changes['reference_regression_count']}。"
        "对所有可配对变化扇，位置、宽度、窗台/门槛、窗顶/门顶四项均要求 after ≤ before；任一项变差会使重放直接失败。",
        "",
        "| 运行/立面/层/对象 | 提交 SHA | 依据 | 采纳字段 | 数值变化 | 参照状态 | 位置前→后 | 宽度前→后 | sill 前→后 | head 前→后 |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row in changes["rows"]:
        identity = f"{row['group']}/{row['run']}/{row['facade']}/{row['floor_id']}/{row['opening_id']}"
        applied = ", ".join(row["applied_fields"]) or "—"
        changed = ", ".join(f"{name}={value:.6f}m" for name, value in row["changed_metrics_m"].items())
        if row["reference_quality"] is None:
            quality = {metric: "—" for metric in labels}
        else:
            quality = {
                metric: f"{row['reference_quality'][metric]['before_m']:.6f}→{row['reference_quality'][metric]['after_m']:.6f}"
                for metric in labels
            }
        lines.append(
            f"| {identity} | {row['submission_sha256'][:12]} | {row['evidence_type']} | {applied} | {changed} | {row['reference_status']} | "
            f"{quality['position_m']} | {quality['width_m']} | {quality['sill_m']} | {quality['head_m']} |"
        )
    if not changes["rows"]:
        lines.append("| 无：218 个历史开口的 effective values 均与 reader values 相同 | — | — | — | — | — | — | — | — | — |")

    ink_audit = evidence["ink_inconsistency_audit"]
    lines += [
        "",
        "### 保留值与唯一墨线不一致（独立于 B 数值分档）",
        "",
        f"共 {ink_audit['opening_count']} 个提交内开口记录（按 submission SHA + opening id）、{ink_audit['item_count']} 个字段；按字段 "
        f"{json.dumps(ink_audit['by_field'], ensure_ascii=False, sort_keys=True)}，按依据类型 "
        f"{json.dumps(ink_audit['by_evidence_type'], ensure_ascii=False, sort_keys=True)}。这些项进入复核，但不改原 reader 数值，也不改 B 的 ≤10/10–30/>30 桶。",
        "",
        "| 运行/立面/层/对象 | 提交 SHA | 字段 | 依据 | reader | ink | 差值 | 阈值 |",
        "|---|---|---|---|---|---|---:|---:|",
    ]
    for row in ink_audit["rows"]:
        identity = f"{row['group']}/{row['run']}/{row['facade']}/{row['floor_id']}/{row['opening_id']}"
        reader_value = json.dumps(row["reader_value"], ensure_ascii=False, separators=(",", ":"))
        ink_value = json.dumps(row["ink_value"], ensure_ascii=False, separators=(",", ":"))
        lines.append(
            f"| {identity} | {row['submission_sha256'][:12]} | {row['field']} | {row['evidence_type']} | {reader_value} | {ink_value} | "
            f"{row['difference_m']:.6f} m | {row['tolerance_m']:.6f} m |"
        )
    if not ink_audit["rows"]:
        lines.append("| 无 | — | — | — | — | — | — | — |")

    width_audit = evidence["width_span_conflict_audit"]
    lines += [
        "",
        "### reader 宽度与像素跨度内部冲突（独立于唯一墨线不一致）",
        "",
        f"最后一次立面提交的 B 对位中共有 {width_audit['guarded_difference_count']} 扇非 pixels 开口的 reader width "
        "与像素跨度存在大于 1e-7 m 的差异，均禁止直接 `use_elevation`；其中 "
        f"{width_audit['pending_conflict_count']} 扇超过 `max(5 cm, 2 px)`，须主动待裁决/重读，"
        f"其余 {width_audit['guard_only_count']} 扇只在选择 `use_elevation` 时要求重读。"
        "这不是 unique-ink 差异，也不并入 B 原位置三档；阈值只决定是否主动新增一条待裁决记录。"
        "全部逐扇记录保存在 `evidence_replay.json.width_span_conflict_audit.rows`；下表列主动冲突。",
        "",
        "| 运行/立面/层/对象 | 依据 | reader width | pixel span width | 差值 | 阈值 | B 桶 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in width_audit["rows"]:
        if not row["pending_conflict"]:
            continue
        identity = f"{row['group']}/{row['run']}/{row['facade']}/{row['floor_id']}/{row['artifact_opening_id']}"
        lines.append(
            f"| {identity} | {row['evidence_type']} | {row['reader_width_m']:.6f} | "
            f"{row['pixel_span_width_m']:.6f} | {row['difference_m']:.6f} | {row['tolerance_m']:.6f} | "
            f"{row['numeric_bucket']} |"
        )
    if not width_audit["pending_conflict_count"]:
        lines.append("| 无 | — | — | — | — | — | — |")

    lines += [
        "", "## 每次运行平立面差（最后一次立面提交）", "",
        "| 运行 | ≤10 cm | 10–30 cm | >30 cm | 墨线不一致（扇/字段） | reader宽度-像素跨度冲突 | 未匹配/不可评 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in evidence["plan_elevation_runs"]:
        counts = row["counts"]
        unavailable = (counts.get("unavailable", 0) + row["elevation_only_count"]
                       + row["plan_only_count"] + row["other_conflict_count"])
        if row["status"] != "evaluated":
            lines.append(f"| {row['group']}/{row['run']} | — | — | — | — | — | {row['status']} |")
        else:
            lines.append(
                f"| {row['group']}/{row['run']} | {counts.get('<=10cm', 0)} | {counts.get('10-30cm', 0)} | "
                f"{counts.get('>30cm', 0)} | {row['ink_inconsistent_opening_count']}/{row['ink_inconsistency_item_count']} | "
                f"{row['width_span_conflict_count']} | {unavailable} |"
            )
    lines += [
        "",
        "B 的对象身份仍由最终 source 与立面通过生产 `match_elevation` 对位；独立平面量值改从 `role_floor_sources.json` "
        "绑定且哈希复核通过的 accepted plan-reader trial 读取，再调用生产 `compare_opening_positions`。"
        "因此协调者采用立面或后续改 source，不会反写平面观察值。",
    ]
    lineage = [row["final_candidate_plan_lineage_audit"] for row in evidence["plan_elevation_runs"]
               if row.get("final_candidate_plan_lineage_audit")]
    lines += [
        f"逐个核对有交付选择的最终 source 外开口：共 {sum(row['final_exterior_opening_count'] for row in lineage)} 扇；"
        f"{sum(row['unchanged_count'] for row in lineage)} 扇与 accepted trial 的 XY 一致，"
        f"{sum(row['changed_count'] for row in lineage)} 扇被协调者改位，"
        f"{sum(row['missing_from_accepted_trial_count'] for row in lineage)} 扇仅存在于最终 source。",
        "",
        "### 最终 source 相对 accepted plan trial 的 XY 差异",
        "",
        "| 运行/立面/对象 | accepted trial span | final source span | 左右/宽最大变化 | 处理 |",
        "|---|---:|---:|---:|---|",
    ]
    difference_rows = 0
    for run in evidence["plan_elevation_runs"]:
        for row in run.get("final_candidate_vs_plan_trial_changes", ()):
            difference_rows += 1
            trial_span = "–".join(f"{value:.6f}" for value in row["accepted_plan_trial_span_m"])
            final_span = "–".join(f"{value:.6f}" for value in row["final_candidate_plan_span_m"])
            lines.append(
                f"| {run['group']}/{run['run']}/{row['facade']}/{row['source_opening_id']} | "
                f"{trial_span} | {final_span} | {row['difference']['max_difference_m']:.6f} m | trial 作为独立平面量值 |"
            )
        for facade, report in sorted(run.get("facades", {}).items()):
            for row in report.get("plan_trial_unavailable", ()):
                difference_rows += 1
                final_span = "–".join(f"{value:.6f}" for value in row["final_candidate_plan_span_m"])
                lines.append(
                    f"| {run['group']}/{run['run']}/{facade}/{row['source_opening_id']} | — | "
                    f"{final_span} | — | accepted trial 无此开口，记 unavailable/需重读 |"
                )
    if not difference_rows:
        lines.append("| 无 | — | — | — | — |")
    lines += ["", "## sm25 分工位置待裁决（>10 cm）", "", "| 立面/层/对象 | 平立面最大差（左右/宽） | 平面对参照 | 立面对参照 | 位置更近 | 宽度更近 |", "|---|---:|---:|---:|---|---|"]
    for row in evidence["sm25_adjudication"]:
        name = f"{row['facade']}/{row['floor_id']}/{row['artifact_opening_id']}→{row['source_opening_id']}"
        lines.append(
            f"| {name} | {row['max_difference_m']:.3f} m | {row['plan_reference_position_error_m']:.3f} m | "
            f"{row['elevation_reference_position_error_m']:.3f} m | {row['closer_for_position']} | {row['closer_for_width']} |"
        )
    if not evidence["sm25_adjudication"]:
        lines.append("| 无 | — | — | — | — | — |")
    lines += [
        "",
        "## 口径与限制",
        "",
        "- 历史开口 `bbox` 的实际格式是 `[left_px, top_px, right_px, bottom_px]`，它是证据裁剪框；独立水平粗框在 `x_px=[left,right]`。水平标定为 `x_calibration={pixel_start,pixel_end,world_start_m,world_end_m,world_axis}`，允许 world 方向反向。生产派生的竖向标定使用同四个数值键，图像 Y 增大时绝对 Z 必须减小。",
        "- A 仅在 `evidence_type==pixels`、相关墨线唯一且边实际移动时替换对应 reader 字段；annotation、annotation_and_pixels、visual_estimate 均保留。原位 confirmed 只证明边，无权重算 reader 数值。`candidate_bbox_px` 记录墨线候选，`effective_bbox_px`/`aligned_bbox_px` 与 `aligned_values` 记录实际生效值。",
        "- 门槛保护只适用于 door：同层已保存的 floor/ground 观测须为 annotation、annotation_and_pixels 或 pixels，且与原 sill 相距不超过 `min(1 px, 5 cm)`。历史常见 0.16/0.20 m 抬高门槛不会被机械当作地坪。",
        f"- 旧立面提交没有显式 `z_calibration`。重放直接调用生产 `derive_z_calibration`：只认图像证据的横向 level/eave/ground 带，用 bbox 中心与 `value_m` 取跨度最大的两带；其余带保留残差。{sum(diagnostics['z_calibration_status_counts'].values())} 份中 {diagnostics['z_calibration_status_counts'].get('derived_from_saved_level_lines', 0)} 份成功、{diagnostics['z_calibration_status_counts'].get('missing_two_horizontal_level_bands', 0)} 份缺两条合格水平带、{diagnostics['z_calibration_status_counts'].get('rejected_inconsistent_saved_level_lines', 0)} 份残差超 10 cm 被拒；半带不确定度超过 35 cm 也会拒绝。拒绝时保留原 sill/head，不拿不足证据强行吸附。",
        "- 历史 `bbox` 是证据裁剪框，不当作开口框。水平粗框来自 `x_px`；竖向粗框仅由上述 Z 标定把提交的 sill/head 反算成像素。",
        "- 对参照配对按 facade/floor/kind 的世界坐标顺序完成；漏项和多项留作未匹配，不强配。平立面对象身份与冲突直接调用生产 `match_elevation`。",
        "- 平立面对比不把最终 delivery candidate 当作独立平面读数。最终 source 只用于对象身份；span 来自对应楼层哈希绑定的 accepted plan-reader trial。trial 缺对象时保留当前 source 对位与单侧冲突，记为 unavailable/需重读，不进入 ≤10 cm。",
        "- B 的 ≤10/10–30/>30 桶只由 accepted plan-reader trial span 与立面像素 span 的端点/宽度差计算；墨线不一致和 reader width/pixel span 内部冲突是附加复核信号，不改桶。非 pixels 的 reader width 与像素跨度存在任何大于 1e-7 m 的差异时，禁止 `use_elevation`；超过 `max(5 cm, 2 px)` 才另记 pending 冲突。",
        "- `role_debug/sm24_run4` 缺 West 成功提交：原 West reader 记录为 failed，重试仍为 running；plan reader 同时一份 failed、一份 running，根目录无 receipt 与全楼交付选择。因此只能重放 East/North/South，不能给平立面扇数。27B 摸底同样只有立面读图员产物。",
        "- `evidence_inventory.json` 保留每份提交、原图及参照的路径与 SHA-256；未复制历史图片、事件日志或 BIM bytes。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    artifacts = []
    for spec in RUN_SPECS:
        artifacts.extend(discover_artifacts(spec))
    latest = latest_per_facade(artifacts)
    coverage = [run_coverage(spec, artifacts) for spec in RUN_SPECS]

    duplicate_groups = []
    grouped = defaultdict(list)
    for row in artifacts:
        grouped[(row["group"], row["run"], row["facade"])].append(row)
    for (group, run, facade), rows in sorted(grouped.items()):
        if len(rows) > 1:
            duplicate_groups.append({
                "group": group, "run": run, "facade": facade, "submissions": len(rows),
                "submission_sha256": [row["submission_sha256"] for row in sorted(rows, key=lambda item: (item["mtime_ns"], item["submission_path"]))],
            })

    reference_manifest = read_json(REFERENCES / "manifest.json")
    inventory = {
        "schema_version": "q2_evidence_inventory_v1",
        "source_archive": str(ARCHIVE),
        "submission_count": len(artifacts),
        "unique_submission_sha256": len({row["submission_sha256"] for row in artifacts}),
        "latest_facade_submission_count": len(latest),
        "duplicate_or_rework_groups": duplicate_groups,
        "run_coverage": coverage,
        "references": [
            {
                **row,
                "absolute_path": str(REFERENCES / row["path"]),
                "actual_sha256": sha256(REFERENCES / row["path"]),
                "sha256_matches_manifest": sha256(REFERENCES / row["path"]) == row["sha256"],
            }
            for row in reference_manifest["references"]
        ],
        "artifacts": [
            {
                key: value for key, value in compact_artifact(row).items()
                if key not in {"alignment", "reference_pairing", "z_calibration_evidence"}
            }
            for row in artifacts
        ],
    }
    write_json(HERE / "evidence_inventory.json", inventory)

    plan_runs = {}
    plan_summary = []
    latest_by_run = defaultdict(list)
    for row in latest:
        latest_by_run[(row["group"], row["run"])].append(row)
    for spec in RUN_SPECS:
        key = (spec["group"], spec["run"])
        run_root = ARCHIVE / spec["group"] / spec["run"]
        candidate, source_path, source = selected_source(run_root)
        if source is None:
            status = "elevation_only_probe" if spec["group"] == "reader_model_probe" else "no_delivery_selection"
            plan_runs[key] = {"status": status, "facades": {}}
            plan_summary.append({
                "group": spec["group"], "run": spec["run"], "case": spec["case"], "status": status,
                "candidate": candidate, "source_model_path": str(source_path) if source_path else None,
                "counts": {}, "plan_trial_unavailable_count": 0,
                "ink_inconsistent_opening_count": 0, "ink_inconsistency_item_count": 0,
                "width_span_conflict_count": 0,
                "elevation_only_count": 0, "plan_only_count": 0, "other_conflict_count": 0,
            })
            continue
        trials = accepted_plan_trials(run_root)
        lineage_audit = plan_lineage_audit(source, trials)
        facades = {}
        for artifact in latest_by_run[key]:
            facades[artifact["facade"]] = plan_elevation_rows(source, artifact, str(candidate), trials)
        counts = Counter(row["tier"] for report in facades.values() for row in report["rows"])
        trial_unavailable = sum(len(report["plan_trial_unavailable"]) for report in facades.values())
        counts["unavailable"] = trial_unavailable
        elevation_only = sum(len(report["elevation_only"]) for report in facades.values())
        plan_only = sum(len(report["plan_only"]) for report in facades.values())
        other = sum(len(report["other_conflicts"]) for report in facades.values())
        ink_inconsistent_openings = sum(report["ink_inconsistent_opening_count"] for report in facades.values())
        ink_inconsistency_items = sum(report["ink_inconsistency_item_count"] for report in facades.values())
        width_span_conflicts = sum(report["width_span_conflict_count"] for report in facades.values())
        candidate_changes = [
            {
                "facade": facade, "floor_id": row["floor_id"],
                "source_opening_id": row["source_opening_id"],
                "accepted_plan_trial_span_m": row["plan_span_m"],
                "final_candidate_plan_span_m": row["final_candidate_plan_span_m"],
                "difference": row["final_candidate_vs_plan_trial"],
            }
            for facade, report in sorted(facades.items()) for row in report["rows"]
            if row["final_candidate_vs_plan_trial"]["max_difference_m"] > 1e-7
        ]
        trial_sources = [
            {key: value for key, value in trial.items() if key not in {"artifact", "source"}}
            for _, trial in sorted(trials.items())
        ]
        plan_runs[key] = {
            "status": "evaluated", "facades": facades, "candidate": candidate,
            "source_model_path": str(source_path), "accepted_plan_trials": trial_sources,
        }
        plan_summary.append({
            "group": spec["group"], "run": spec["run"], "case": spec["case"], "status": "evaluated",
            "candidate": candidate, "source_model_path": str(source_path), "source_model_sha256": sha256(source_path),
            "plan_comparison_basis": "accepted_plan_reader_trial",
            "accepted_plan_trials": trial_sources,
            "final_candidate_plan_lineage_audit": lineage_audit,
            "final_candidate_vs_plan_trial_changes": candidate_changes,
            "counts": {name: counts[name] for name in ("<=10cm", "10-30cm", ">30cm", "unavailable")},
            "plan_trial_unavailable_count": trial_unavailable,
            "ink_inconsistent_opening_count": ink_inconsistent_openings,
            "ink_inconsistency_item_count": ink_inconsistency_items,
            "width_span_conflict_count": width_span_conflicts,
            "elevation_only_count": elevation_only, "plan_only_count": plan_only, "other_conflict_count": other,
            "facades": facades,
        })

    numeric_changes = numeric_change_audit(artifacts)
    ink_inconsistencies = ink_inconsistency_audit(artifacts)
    width_span_conflicts = width_span_conflict_audit(plan_summary)
    evidence = {
        "schema_version": "q2_offline_replay_v2",
        "constraints": {"work_model_requests": 0, "external_model_requests": 0, "full_test_suite": False},
        "production_functions": [
            {
                "function": "src.agent.runtime_roles.elevation_ink.align_elevation_artifact",
                "path": str(ROOT / "src/agent/runtime_roles/elevation_ink.py"),
                "sha256": sha256(ROOT / "src/agent/runtime_roles/elevation_ink.py"),
            },
            {
                "function": "src.agent.runtime_roles.height_evidence.derive_z_calibration",
                "path": str(ROOT / "src/agent/runtime_roles/height_evidence.py"),
                "sha256": sha256(ROOT / "src/agent/runtime_roles/height_evidence.py"),
            },
            {
                "function": "src.agent.runtime_roles.elevation.match_elevation + compare_opening_positions",
                "path": str(ROOT / "src/agent/runtime_roles/elevation.py"),
                "sha256": sha256(ROOT / "src/agent/runtime_roles/elevation.py"),
            },
        ],
        "inventory": {
            "submission_count": inventory["submission_count"],
            "unique_submission_sha256": inventory["unique_submission_sha256"],
            "latest_facade_submission_count": inventory["latest_facade_submission_count"],
            "duplicate_or_rework_groups": duplicate_groups,
        },
        "run_coverage": coverage,
        "alignment_diagnostics": alignment_diagnostics(artifacts),
        "numeric_change_audit": numeric_changes,
        "ink_inconsistency_audit": ink_inconsistencies,
        "width_span_conflict_audit": width_span_conflicts,
        "reference_tiers": aggregate_tiers(artifacts),
        "reference_tiers_latest_per_facade": aggregate_tiers(latest),
        "plan_elevation_runs": plan_summary,
        "sm25_adjudication": sm25_adjudication(latest, plan_runs),
        "artifact_replays": [compact_artifact(row) for row in artifacts],
    }
    write_json(HERE / "evidence_replay.json", evidence)
    (HERE / "replay_report.md").write_text(markdown_report(evidence), encoding="utf-8", newline="\n")
    print(json.dumps({
        "submissions": len(artifacts), "latest_facades": len(latest),
        "reference_pairs": sum(len(row["reference_pairing"]["pairs"]) for row in artifacts),
        "numeric_changes": numeric_changes["changed_opening_count"],
        "ink_inconsistency_items": ink_inconsistencies["item_count"],
        "width_span_pending_conflicts": width_span_conflicts["pending_conflict_count"],
        "sm25_adjudication": len(evidence["sm25_adjudication"]),
        "outputs": [str(HERE / name) for name in ("evidence_inventory.json", "evidence_replay.json", "replay_report.md")],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
