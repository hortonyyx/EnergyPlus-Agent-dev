#!/usr/bin/env python3
"""Summarize Lite regularization evidence from one manual-dispatch run.

This is intentionally a read-only, run-local report. It does not import the
agent, open source drawings, consult ground truth, or infer use from guidance.
Actual use is counted only when it is present in accepted artifacts or trial
receipts created by the supplied run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_file(run: Path, relative: str) -> Path:
    path = (run / relative).resolve()
    try:
        path.relative_to(run)
    except ValueError as error:
        raise ValueError(f"artifact path leaves run directory: {relative}") from error
    if not path.is_file():
        raise ValueError(f"artifact does not exist: {relative}")
    return path


def regularization_summary(report: Any, *, failed_trial: bool = False) -> dict[str, Any]:
    if not isinstance(report, dict) or report.get("schema") != "lite_bim_regularization_v1":
        return {"measurement_status": "not_observed"}
    items = report.get("items") if isinstance(report.get("items"), list) else []
    shifts = [abs(float(row["movement_m"])) for row in items
              if isinstance(row, dict) and isinstance(row.get("movement_m"), (int, float))]
    changed = sum(shift > 1e-9 for shift in shifts)
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    topology = report.get("topology") if isinstance(report.get("topology"), dict) else {}
    grid = report.get("compiled_grid") if isinstance(report.get("compiled_grid"), dict) else {}
    coordinate_stage_reached = bool(items) or report.get("status") == "pass"
    return {
        "measurement_status": (
            "rejected_before_coordinate_regularization"
            if failed_trial and not coordinate_stage_reached
            else "observed_in_failed_trial" if failed_trial
            else "observed_in_trial"
        ),
        "schema": report.get("schema"),
        "status": report.get("status"),
        "grid_step_m": report.get("grid_step_m"),
        "checked_count": len(items) if coordinate_stage_reached else None,
        "changed_count": changed if coordinate_stage_reached else None,
        "reported_changed_count": summary.get("moved_coordinates"),
        "max_abs_shift_m": max(shifts, default=0.0) if coordinate_stage_reached else None,
        "topology_status": topology.get("status"),
        "compiled_grid_status": grid.get("status"),
    }


def dimensions_summary(report: Any, *, failed_trial: bool = False) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {"measurement_status": "not_observed"}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    supplied = summary.get("chains_supplied")
    applied = summary.get("chains_applied")
    rejected = summary.get("rejected")
    observed = any(value is not None for value in (supplied, applied, rejected))
    result = {
        "measurement_status": (
            "observed_in_failed_trial" if observed and failed_trial
            else "observed_in_trial" if observed
            else "not_observed"
        ),
        "status": report.get("status"),
        "chains_supplied": supplied,
        "chains_applied": applied,
        "chains_rejected": rejected,
        "axes_calibrated": summary.get("axes_calibrated"),
        "supplemental_chains_applied": summary.get("supplemental_chains_applied"),
    }
    if isinstance(report.get("items"), list):
        result["actions"] = sorted({row.get("action") for row in report["items"]
                                    if isinstance(row, dict) and isinstance(row.get("action"), str)})
    return result


def trial_rows(task_dir: Path, task_id: str) -> list[dict[str, Any]]:
    receipts = sorted(task_dir.glob("bim/trial_workspace/trial_receipts/trial_*.json"))
    # Exclude aligned/unaligned inputs and profile sidecars that share the prefix.
    receipts = [path for path in receipts if path.stem.removeprefix("trial_").isdigit()]
    rows = []
    for path in receipts:
        receipt = read_json(path)
        alignment = receipt.get("reading_alignment")
        alignment = alignment if isinstance(alignment, dict) else {}
        failed_trial = receipt.get("status") == "failed"
        failure = receipt.get("regularization_failure")
        failure = failure if isinstance(failure, dict) else {}
        dimension_report = alignment.get("dimensions")
        if not isinstance(dimension_report, dict) and failure.get("schema_version") == "plan_reading_dimension_alignment_v1":
            dimension_report = failure
        lite_report = alignment.get("lite_bim")
        if not isinstance(lite_report, dict) and failure.get("schema") == "lite_bim_regularization_v1":
            lite_report = failure
        rows.append({
            "task_id": task_id,
            "receipt_file": str(path.relative_to(task_dir)).replace("\\", "/"),
            "receipt_sha256": sha256_file(path),
            "trial_id": receipt.get("trial_id"),
            "status": receipt.get("status"),
            "plan_sha256": receipt.get("plan_sha256"),
            "dimension_chains": dimensions_summary(dimension_report, failed_trial=failed_trial),
            "regularization_0_1m": regularization_summary(lite_report, failed_trial=failed_trial),
        })
    return rows


def elevation_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    report = artifact.get("regularization")
    if not isinstance(report, dict) or report.get("schema") != "elevation_lite_regularization_v1":
        return {"measurement_status": "not_observed"}
    readings = report.get("readings") if isinstance(report.get("readings"), list) else []
    changes = report.get("changes") if isinstance(report.get("changes"), list) else []
    retained = [row for row in readings if isinstance(row, dict)
                and isinstance(row.get("original_m"), (int, float))
                and isinstance(row.get("adopted_m"), (int, float))]
    shifts = [abs(float(row["shift_m"])) for row in retained
              if isinstance(row.get("shift_m"), (int, float))]
    return {
        "measurement_status": "observed_in_accepted_artifact",
        "schema": report.get("schema"),
        "status": report.get("status"),
        "grid_step_m": report.get("grid_step_m"),
        "readings_count": len(readings),
        "originals_retained_count": len(retained),
        "adopted_values_count": len(retained),
        "changed_count": len(changes),
        "unchanged_count": len(readings) - len(changes),
        "max_abs_shift_m": max(shifts, default=0.0),
        "elevation_value_count": sum(row.get("item_kind") == "elevation" for row in readings
                                     if isinstance(row, dict)),
        "opening_value_count": sum(row.get("item_kind") == "opening" for row in readings
                                   if isinstance(row, dict)),
    }


def manifest_capabilities(run: Path) -> dict[str, Any]:
    path = run / "manual_dispatch_manifest.json"
    if not path.is_file():
        return {"measurement_status": "manifest_missing"}
    manifest = read_json(path)
    agent = manifest.get("agent") if isinstance(manifest.get("agent"), dict) else {}
    files = agent.get("files") if isinstance(agent.get("files"), dict) else {}
    wanted = {
        "plan_0_1m_regularization": "src/agent/geometry/lite_bim_regularization.py",
        "dimension_chain_alignment": "src/agent/geometry/plan_dimension_alignment.py",
        "elevation_0_1m_regularization": "src/agent/runtime_roles/elevation_regularization.py",
        "rework_context_projection": "src/agent/runtime_roles/reader_context.py",
    }
    return {
        "measurement_status": "configured_capability_only",
        "agent_version_id": agent.get("version_id"),
        "source_commit": agent.get("source_commit"),
        "features": {
            name: {
                "available_in_frozen_agent": source in files,
                "source_manifest_path": source,
                "source_sha256": files.get(source, {}).get("sha256")
                if isinstance(files.get(source), dict) else None,
            }
            for name, source in wanted.items()
        },
    }


def summarize(run_path: Path) -> dict[str, Any]:
    run = run_path.resolve()
    tasks_dir = run / "tasks"
    if not tasks_dir.is_dir():
        raise ValueError(f"run has no tasks directory: {run}")

    task_statuses: dict[str, int] = {}
    plan_trials: list[dict[str, Any]] = []
    elevations: list[dict[str, Any]] = []
    rework: list[dict[str, Any]] = []
    plan_tasks = 0
    plan_artifacts = 0

    for task_dir in sorted(path for path in tasks_dir.iterdir() if path.is_dir()):
        task_path = task_dir / "reader_task.json"
        record_path = task_dir / "reader_record.json"
        if not task_path.is_file() or not record_path.is_file():
            continue
        task = read_json(task_path)
        record = read_json(record_path)
        task_id = task.get("task_id") or task_dir.name
        status = str(record.get("status", "unknown"))
        task_statuses[status] = task_statuses.get(status, 0) + 1

        if task.get("previous_task_id"):
            rework.append({
                "task_id": task_id,
                "role_id": task.get("role_id"),
                "previous_task_id": task.get("previous_task_id"),
                "rework_target_count": len(task.get("rework_targets", []))
                if isinstance(task.get("rework_targets"), list) else None,
                "projection_measurement_status": (
                    "rework_task_observed; prompt byte reduction is not persisted in reader_task.json"
                ),
            })

        if task.get("role_id") == "plan_reader":
            plan_tasks += 1
            plan_trials.extend(trial_rows(task_dir, str(task_id)))
            if record.get("artifact"):
                plan_artifacts += 1

        if task.get("role_id") != "elevation_reader" or not record.get("artifact"):
            continue
        artifact_ref = record["artifact"]
        relative = artifact_ref.get("path") if isinstance(artifact_ref, dict) else None
        if not isinstance(relative, str):
            continue
        artifact_path = relative_file(run, relative)
        artifact = read_json(artifact_path)
        actual_sha = sha256_file(artifact_path)
        expected_sha = artifact_ref.get("sha256")
        elevations.append({
            "task_id": task_id,
            "status": status,
            "orientation": artifact.get("orientation"),
            "artifact_file": relative.replace("\\", "/"),
            "artifact_sha256": actual_sha,
            "artifact_sha256_matches_record": expected_sha == actual_sha,
            "regularization": elevation_summary(artifact),
        })

    elevation_regs = [row["regularization"] for row in elevations
                      if row["regularization"].get("measurement_status") == "observed_in_accepted_artifact"]
    observed_plan_regs = [row["regularization_0_1m"] for row in plan_trials
                          if row["regularization_0_1m"].get("measurement_status")
                          in {"observed_in_trial", "observed_in_failed_trial"}]
    observed_dimensions = [row["dimension_chains"] for row in plan_trials
                           if row["dimension_chains"].get("measurement_status")
                           in {"observed_in_trial", "observed_in_failed_trial"}]
    return {
        "schema": "sm25_lite_adoption_report_v1",
        "run": str(run),
        "scope": {
            "run_only": True,
            "old_replays_included": False,
            "ground_truth_read": False,
            "source_images_read": False,
            "network_or_model_calls": False,
        },
        "completeness": {
            "task_statuses": task_statuses,
            "plan_task_count": plan_tasks,
            "plan_trial_receipt_count": len(plan_trials),
            "plan_accepted_artifact_count": plan_artifacts,
            "elevation_accepted_artifact_count": len(elevations),
            "final_plan_metrics_ready": plan_tasks > 0 and plan_artifacts == plan_tasks,
        },
        "configured_capability": manifest_capabilities(run),
        "actual_use": {
            "plan_trials": plan_trials,
            "elevations": elevations,
            "rework_context": {
                "actual_rework_task_count": len(rework),
                "tasks": rework,
                "claim": "not_triggered_in_this_run" if not rework else "triggered; byte reduction not measured here",
            },
        },
        "totals": {
            "plan_trials_with_dimension_chain_report": len(observed_dimensions),
            "plan_trial_observations_dimension_chains_supplied": (
                sum(int(row.get("chains_supplied") or 0) for row in observed_dimensions)
                if observed_dimensions else None
            ),
            "plan_trial_observations_dimension_chains_applied": (
                sum(int(row.get("chains_applied") or 0) for row in observed_dimensions)
                if observed_dimensions else None
            ),
            "plan_trials_rejected_before_coordinate_regularization": sum(
                row["regularization_0_1m"].get("measurement_status")
                == "rejected_before_coordinate_regularization"
                for row in plan_trials
            ),
            "plan_trials_with_0_1m_regularization": len(observed_plan_regs),
            # These are observations across receipts. A coordinate may occur in
            # more than one attempt, so they are not final unique-coordinate
            # counts. The run's source audit owns that separate measurement.
            "plan_trial_observations_coordinates_checked": (
                sum(int(row.get("checked_count") or 0) for row in observed_plan_regs)
                if observed_plan_regs else None
            ),
            "plan_trial_observations_coordinates_changed": (
                sum(int(row.get("changed_count") or 0) for row in observed_plan_regs)
                if observed_plan_regs else None
            ),
            "plan_trial_observations_max_abs_shift_m": max(
                (float(row.get("max_abs_shift_m") or 0.0) for row in observed_plan_regs),
                default=None,
            ),
            "elevation_readings": sum(int(row.get("readings_count") or 0) for row in elevation_regs),
            "elevation_originals_retained": sum(int(row.get("originals_retained_count") or 0)
                                                for row in elevation_regs),
            "elevation_values_changed": sum(int(row.get("changed_count") or 0) for row in elevation_regs),
            "elevation_max_abs_shift_m": max((float(row.get("max_abs_shift_m") or 0.0)
                                              for row in elevation_regs), default=None),
        },
        "interpretation": {
            "configured_capability": "presence in the frozen run manifest; it is not counted as actual use",
            "actual_plan_use": "immutable trial receipt reports only",
            "plan_totals": (
                "trial observations; repeated attempts may repeat coordinates and do not measure final unique coordinates"
            ),
            "actual_elevation_use": "accepted artifact audit only",
            "actual_rework_context_use": "new task with previous_task_id only; zero means no benefit claimed",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="manual-dispatch run directory")
    parser.add_argument("--output", type=Path, help="optional JSON output path outside the run")
    args = parser.parse_args()
    report = summarize(args.run)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
