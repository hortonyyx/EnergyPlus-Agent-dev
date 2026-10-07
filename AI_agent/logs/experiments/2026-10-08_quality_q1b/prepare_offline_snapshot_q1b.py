"""Freeze the Q1b offline replay inputs without writing any source run.

The source paths are deliberately fixed to the two authorised read-only trees.
Only plan/result JSON files are copied.  Image bytes are not needed by the
pre-compile junction replay; their size and SHA256 are verified and recorded.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DESTINATION = ROOT / "AI_agent/archive/local_backup/q1b/replay_inputs"
RUN_SOURCE = Path(
    r"D:\EnergyPlus-Agent-worktrees\runs-q\AI_agent\archive\local_backup\quality\sm25_role_q"
)
MAIN_ROOT = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev")
MERGED_SOURCE = MAIN_ROOT / "AI_agent/archive/local_backup/merged/sm25_role_n1"
Q1_REPORT = HERE.parent / "2026-10-07_quality_q1/replay_report.json.gz"
MANIFEST_PATH = HERE / "snapshot_manifest.json"

FAILURE_TASKS = {
    "3946ca64ff78d93ca61090a437cbb6b3d2ca0d488f5f9ccf3059608368b27693": 14,
    "f64551fcd6f07823cb87971cfb91446425da18286b3ab1ef935e0cbd7a69f68a": 13,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def augment_reader_images() -> None:
    manifest = read_json(MANIFEST_PATH)
    image_root = DESTINATION / "_reader_images"
    image_root.mkdir(parents=True, exist_ok=True)
    copied = 0
    copied_bytes = 0
    for row in manifest["items"]:
        if row["group"] != "q1_historical_reader_inputs":
            continue
        record = row["image"]
        source = Path(record["source_path"])
        actual = sha256(source)
        if actual != record["source_sha256"]:
            raise ValueError(f"reader image hash drift: {source}")
        target = image_root / f"{actual[:16]}_{source.name}"
        if not target.is_file():
            shutil.copyfile(source, target)
            copied += 1
            copied_bytes += target.stat().st_size
        if sha256(target) != actual:
            raise ValueError(f"copied reader image hash mismatch: {target}")
        record.update({
            "copied": True,
            "local_path": str(target.relative_to(ROOT)).replace("\\", "/"),
            "local_sha256": actual,
            "bytes": target.stat().st_size,
        })
        record.pop("reason_not_copied", None)
    manifest["source_boundaries"]["images"] = (
        "seven Q1 reader inputs use hash-verified local image copies; other image bytes remain omitted"
    )
    manifest["reader_image_copy"] = {
        "unique_files_copied_this_run": copied,
        "bytes_copied_this_run": copied_bytes,
        "local_image_files": len(list(image_root.glob("*"))),
        "local_image_bytes": sum(path.stat().st_size for path in image_root.glob("*") if path.is_file()),
    }
    write_json(MANIFEST_PATH, manifest)
    print(json.dumps({
        "manifest": str(MANIFEST_PATH),
        "reader_images": manifest["reader_image_copy"],
        "model_requests": 0,
    }, ensure_ascii=False))


def local_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in value)


def resolve_q1_source(raw: str) -> Path:
    path = Path(raw)
    if path.is_file():
        return path
    marker = "AI_agent"
    parts = list(path.parts)
    if marker not in parts:
        raise FileNotFoundError(path)
    candidate = MAIN_ROOT.joinpath(*parts[parts.index(marker):])
    if not candidate.is_file():
        raise FileNotFoundError(f"Q1 input missing in main tree: {candidate}")
    return candidate


def image_record(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    actual = sha256(path)
    if expected_sha256 and actual != expected_sha256:
        raise ValueError(f"image hash drift: {path}: {actual} != {expected_sha256}")
    with Image.open(path) as image:
        size = [int(image.width), int(image.height)]
    return {
        "source_path": str(path),
        "source_sha256": actual,
        "size": size,
        "copied": False,
        "reason_not_copied": "pre-compile junction replay uses image dimensions, not pixels",
    }


def copy_record(
    *,
    group: str,
    run: str,
    item: str,
    source_plan: Path,
    source_result: Path | None,
    image_name: str,
    image: dict[str, Any],
    expected_plan_sha256: str | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    relative = Path(group) / local_name(run) / local_name(item)
    target = DESTINATION / relative
    target.mkdir(parents=True, exist_ok=True)
    plan_sha = sha256(source_plan)
    if expected_plan_sha256 and plan_sha != expected_plan_sha256:
        raise ValueError(f"plan hash drift: {source_plan}: {plan_sha} != {expected_plan_sha256}")
    local_plan = target / "plan.json"
    shutil.copyfile(source_plan, local_plan)
    row: dict[str, Any] = {
        "group": group,
        "run": run,
        "item": item,
        "floor_id": str(read_json(source_plan).get("floor_id")),
        "plan": {
            "source_path": str(source_plan),
            "source_sha256": plan_sha,
            "local_path": str(local_plan.relative_to(ROOT)).replace("\\", "/"),
            "local_sha256": sha256(local_plan),
            "bytes": local_plan.stat().st_size,
        },
        "image_name": image_name,
        "image": image,
        "baseline": baseline or {},
    }
    if source_result is not None:
        local_result = target / "result.json"
        shutil.copyfile(source_result, local_result)
        row["result"] = {
            "source_path": str(source_result),
            "source_sha256": sha256(source_result),
            "local_path": str(local_result.relative_to(ROOT)).replace("\\", "/"),
            "local_sha256": sha256(local_result),
            "bytes": local_result.stat().st_size,
        }
    return row


def result_image(result: dict[str, Any]) -> str:
    name = (result.get("plan_input") or {}).get("image")
    if not name:
        raise ValueError("result.json does not identify its source image")
    return str(name)


def classify_error(error: str) -> str:
    if "polygonize produced dangles" in error:
        return "dangle"
    if "physical partition overlaps footprint boundary" in error:
        return "partition_overlaps_footprint"
    if "occupy the same space" in error:
        return "duplicate_space_seed"
    if "requires one exterior or two interior full-boundary hosts" in error:
        return "opening_missing_host"
    if "has only one full space host" in error:
        return "opening_partial_host"
    if "line is outside footprint" in error:
        return "partition_outside_footprint"
    if "is degenerate" in error:
        return "degenerate_partition"
    return "other"


def freeze_failure_trials(rows: list[dict[str, Any]]) -> None:
    for task, expected_count in FAILURE_TASKS.items():
        base = RUN_SOURCE / "tasks" / task / "bim"
        draft_root = base / "trial_workspace/plan_drafts"
        drafts = sorted(draft_root.glob("draft_*/plan.json"))
        if len(drafts) != expected_count:
            raise ValueError(f"authorised failure task {task} changed: {len(drafts)} != {expected_count}")
        for plan_path in drafts:
            result_path = plan_path.with_name("result.json")
            result = read_json(result_path)
            image_name = result_image(result)
            image_path = base / "images" / image_name
            error = str(result.get("error", ""))
            rows.append(copy_record(
                group="failure_trials_earliest_two_tasks",
                run=task,
                item=plan_path.parent.name,
                source_plan=plan_path,
                source_result=result_path,
                image_name=image_name,
                image=image_record(image_path),
                baseline={
                    "status": result.get("status"),
                    "error_stage": result.get("error_stage"),
                    "error": error,
                    "failure_type": classify_error(error),
                },
            ))


def freeze_merged(rows: list[dict[str, Any]]) -> None:
    for task_root in sorted((MERGED_SOURCE / "tasks").iterdir()):
        if not task_root.is_dir():
            continue
        base = task_root / "bim"
        for plan_path in sorted(base.glob("trial_workspace/plan_drafts/draft_*/plan.json")):
            result_path = plan_path.with_name("result.json")
            result = read_json(result_path)
            image_name = result_image(result)
            rows.append(copy_record(
                group="merged_sm25_role_n1_trials",
                run=task_root.name,
                item=plan_path.parent.name,
                source_plan=plan_path,
                source_result=result_path,
                image_name=image_name,
                image=image_record(base / "images" / image_name),
                baseline={"status": result.get("status"), "error": result.get("error")},
            ))
    for plan_path in sorted((MERGED_SOURCE / "bim/plan_drafts").glob("draft_*/plan.json")):
        result_path = plan_path.with_name("result.json")
        result = read_json(result_path)
        image_name = result_image(result)
        rows.append(copy_record(
            group="merged_sm25_role_n1_delivery_plans",
            run="sm25_role_n1",
            item=plan_path.parent.name,
            source_plan=plan_path,
            source_result=result_path,
            image_name=image_name,
            image=image_record(MERGED_SOURCE / "bim/images" / image_name),
            baseline={"status": result.get("status"), "error": result.get("error")},
        ))


def freeze_q1_history(rows: list[dict[str, Any]], expected_runs: dict[str, Any]) -> str:
    report_sha = sha256(Q1_REPORT)
    with gzip.open(Q1_REPORT, "rt", encoding="utf-8") as handle:
        report = json.load(handle)
    outcomes = {row["run"]: row for row in report["regularization_replay"]}
    for group in report["manifest"]["groups"]:
        target_group = (
            "three_case_comparison_delivery_plans"
            if group["evidence_class"] == "real_work_model_delivery"
            else "q1_historical_regularization_inputs"
        )
        outcome = outcomes[group["run"]]
        expected_runs[group["run"]] = {
            "source_q1_status": outcome["status"],
            "source_q1_applied_change_count": len(outcome["items"]["applied_changes"]),
            "source_q1_report_sha256": report_sha,
        }
        for index, plan_row in enumerate(group["plans"], start=1):
            source_plan = resolve_q1_source(plan_row["plan_path"])
            image_path = resolve_q1_source(plan_row["image_path"])
            rows.append(copy_record(
                group=target_group,
                run=group["run"],
                item=f"{index:02d}_{plan_row['floor_id']}",
                source_plan=source_plan,
                source_result=None,
                image_name=plan_row["image_name"],
                image=image_record(image_path, expected_sha256=plan_row["image_sha256"]),
                expected_plan_sha256=plan_row["plan_sha256"],
                baseline={
                    "q1_group_status": outcome["status"],
                    "q1_group_applied_change_count": len(outcome["items"]["applied_changes"]),
                },
            ))
    reader_outcomes = {row["run"]: row for row in report["reader_alignment_replay"]}
    for group in report["manifest"]["reader_trials"]:
        outcome = reader_outcomes[group["run"]]
        floor_outcomes = {row["floor_id"]: row for row in outcome["floors"]}
        expected_runs[group["run"]] = {
            "source_q1_reader_statuses": {
                floor: value["ink_status"] for floor, value in floor_outcomes.items()
            },
            "source_q1_report_sha256": report_sha,
        }
        for index, plan_row in enumerate(group["plans"], start=1):
            source_plan = resolve_q1_source(plan_row["plan_path"])
            image_path = resolve_q1_source(plan_row["image_path"])
            floor_outcome = floor_outcomes[plan_row["floor_id"]]
            rows.append(copy_record(
                group="q1_historical_reader_inputs",
                run=group["run"],
                item=f"{index:02d}_{plan_row['floor_id']}",
                source_plan=source_plan,
                source_result=None,
                image_name=plan_row["image_name"],
                image=image_record(image_path, expected_sha256=plan_row["image_sha256"]),
                expected_plan_sha256=plan_row["plan_sha256"],
                baseline={"q1_ink_status": floor_outcome["ink_status"]},
            ))
    return report_sha


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--augment-reader-images", action="store_true")
    args = parser.parse_args()
    if args.augment_reader_images:
        augment_reader_images()
        return
    allowed = (ROOT / "AI_agent/archive/local_backup/q1b").resolve()
    destination = DESTINATION.resolve()
    if not destination.is_relative_to(allowed) or destination == allowed:
        raise ValueError("snapshot destination must remain inside the Q1b scratch directory")
    if DESTINATION.exists() and any(DESTINATION.iterdir()):
        raise FileExistsError(f"refusing to overwrite frozen snapshot: {DESTINATION}")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    expected_runs: dict[str, Any] = {}
    freeze_failure_trials(rows)
    freeze_merged(rows)
    q1_report_sha = freeze_q1_history(rows, expected_runs)
    counts: dict[str, int] = {}
    bytes_by_group: dict[str, int] = {}
    for row in rows:
        counts[row["group"]] = counts.get(row["group"], 0) + 1
        bytes_by_group[row["group"]] = bytes_by_group.get(row["group"], 0) + row["plan"]["bytes"]
        if row.get("result"):
            bytes_by_group[row["group"]] += row["result"]["bytes"]
    manifest = {
        "schema": "q1b_snapshot_manifest_v1",
        "model_requests": 0,
        "paratera_requests": 0,
        "deepseek_requests": 0,
        "source_boundaries": {
            "runs_q": str(RUN_SOURCE),
            "main_tree": str(MAIN_ROOT),
            "runs_q_selection": {
                "rule": "exactly the earliest two authorised plan-reader tasks",
                "tasks": FAILURE_TASKS,
                "later_reassignments_included": False,
            },
            "images": "hash and dimensions verified; bytes omitted because this replay does not inspect pixels",
        },
        "q1_source_report": {"path": str(Q1_REPORT), "sha256": q1_report_sha},
        "counts": counts,
        "bytes_by_group": bytes_by_group,
        "copied_bytes": sum(bytes_by_group.values()),
        "expected_q1_runs": expected_runs,
        "items": rows,
    }
    write_json(MANIFEST_PATH, manifest)
    print(json.dumps({
        "manifest": str(MANIFEST_PATH),
        "snapshot": str(DESTINATION),
        "items": len(rows),
        "copied_bytes": manifest["copied_bytes"],
        "model_requests": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
