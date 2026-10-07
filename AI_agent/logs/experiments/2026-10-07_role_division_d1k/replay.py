"""Read-only historical replay, plus two isolated real-tool repairs. No model calls."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.runtime_roles.coordinates import plan_orientation
from src.agent.runtime_roles.guidance import guidance_catalog
from src.agent.runtime_roles.readers import _evidence_targets
from src.agent.runtime_roles.submission import PLAN_SCHEMA, SUBMISSION_TOOLS, ReaderSubmission
from src.agent.runtime_roles.trial import PlanTrial, PlanTrialSession

HERE = Path(__file__).resolve().parent
SOURCE = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\role_debug")
SCRATCH = ROOT / "AI_agent/archive/local_backup/d1k/replay"
RUNS = ("sm24_run3", "sm24_run5", "sm24_run6", "sm24_run7", "sm21_run1", "sm25_run1")
RESOLVE = runpy.run_path(str(HERE.parent / "2026-10-07_cleanup_c4/trial_replay.py"))["_resolve_capture"]
BRIDGE = runpy.run_path(str(HERE.parent / "2026-10-06_role_division_d1b/scoring_bridge.py"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chars(value):
    return len(json.dumps(value, ensure_ascii=False))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def history(run):
    rows = []
    for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        payload = event["payload"]
        if payload.get("event_type") != "tool_execution" or payload.get("tool_name") not in {
            "trial_plan_bim", "submit_plan_reading"
        }:
            continue
        raw = RESOLVE(run, payload["raw_result"])
        rows.append({"id": event["event_id"], "task": event["task_id"], "tool": payload["tool_name"],
                     "arguments": payload["full_arguments"], "result": raw.get("structuredContent", raw)})
    return rows


def trials(run):
    result = {}
    for path in sorted(run.glob("tasks/*/reader_record.json")):
        record = json.loads(path.read_bytes())
        if record["role_id"] != "plan_reader":
            continue
        reader = path.parent / "bim"
        workspace = reader / "trial_workspace"
        trial = PlanTrial(None, image_name=record["image"], workspace=workspace,
                          receipt_directory=workspace / "trial_receipts")
        result[record["task_id"]] = {"trial": trial, "reader": reader, "record": record,
            "saved": json.loads((reader / "reader_submission.json").read_bytes())}
    # Reconstruct only the declared rework lineage; never edit historical records.
    for data in result.values():
        base = data["trial"].receipts[0].get("base_plan_sha256")
        if not base:
            continue
        prior = next((other["trial"] for other in result.values() if other is not data
                      and other["trial"]._successful(base)), None)
        if prior:
            targets = sorted({row["item"] for receipt in data["trial"].receipts
                              for row in receipt.get("changes", [])})
            data["trial"].inherit_reference(prior, base, targets)
    return result


def short_arguments(old, trial, *, keep_extra_notes=True, keep_unneeded_checks=False):
    latest = trial._successful()
    plan, _ = trial.verified_plan(latest["plan_sha256"])
    result = {"trial_id": "latest"}
    extras = [value for value in old.get("unresolved", []) if value not in plan["unresolved"]]
    if keep_extra_notes and extras:
        result["unresolved"] = extras
    overrides = {key: value for key, value in old.get("wall_reference", {}).items()
                 if value["convention"] != {"perimeter": "outer_face", "partitions": "centerline"}[key]}
    if overrides:
        result["wall_reference"] = overrides
    if old.get("topology_decisions"):
        result["topology_decisions"] = old["topology_decisions"]
    if "north_arrow" in old and (keep_unneeded_checks or "check" in plan_orientation(trial.numeric_plan(latest))):
        result["north_arrow"] = old["north_arrow"]
    return result


def submit(data, arguments):
    submission = ReaderSubmission(role_id="plan_reader", image_name=data["record"]["image"],
                                  trial=data["trial"], target=data["record"]["target"])
    manifest = json.loads((data["reader"] / "inputs.json").read_bytes())
    submission.image_size = manifest["images"][submission.image_name]["size"]
    try:
        response = submission.submit(arguments)
        return response, submission.read()
    except ValueError as error:
        return {"status": "rejected", "reason": str(error)}, None


def replay_submissions(run, events, tasks):
    rows = []
    for event in events:
        if event["tool"] != "submit_plan_reading":
            continue
        data = tasks[event["task"]]
        old = event["arguments"]
        short = short_arguments(old, data["trial"])
        response, saved = submit(data, short)
        strict, _ = submit(data, short_arguments(old, data["trial"], keep_unneeded_checks=True))
        row = {"run": run.name, "event": event["id"], "task": event["task"],
               "old_status": event["result"].get("status"), "new_status": response["status"],
               "old_characters": chars(old), "new_characters": chars(short),
               "reference_only_characters": chars({"trial_id": "latest"}),
               "new_arguments": short, "old_reason": event["result"].get("error"),
               "new_reason": response.get("reason"), "explicit_checks_status": strict["status"]}
        if saved:
            artifact = saved["artifact"]
            assert artifact["plan"] == data["saved"]["artifact"]["plan"]
            assert set(artifact["unresolved"]) == set(data["saved"]["artifact"]["unresolved"])
            assert {item["item"] for item in artifact["evidence"]} == _evidence_targets(artifact["plan"])
            trial = data["trial"]
            latest = trial._successful()
            source = trial.workspace / latest["candidate"] / "source_model.json"
            kwargs = dict(case=run.name.split("_")[0], plan_trial_source=source,
                          plan_trial_receipt=latest, plan_image_name=trial.image_name)
            old_neutral = BRIDGE["convert_role_artifacts"](plan_artifact=data["saved"]["artifact"], **kwargs)
            new_neutral = BRIDGE["convert_role_artifacts"](plan_artifact=artifact, **kwargs)
            # Audit metadata changes; the actual neutral questions and source do not.
            assert old_neutral["answer"] == new_neutral["answer"]
            row.update(plan_unchanged=True, unresolved_preserved=True, coverage_complete=True,
                       evidence_count=len(artifact["evidence"]), scoring_answer_unchanged=True)
            write(SCRATCH / run.name / (event["id"] + "_submission.json"), saved)
        rows.append(row)
    return rows


def replay_trial_products(run, tasks):
    rows = []
    for task_id, data in tasks.items():
        trial = data["trial"]
        size = json.loads((trial.workspace / "inputs.json").read_bytes())["images"][trial.image_name]["size"]
        for receipt in trial.receipts:
            row = {"run": run.name, "task": task_id, "receipt": receipt["receipt_file"],
                   "old_status": receipt["status"], "plan_sha256": receipt["plan_sha256"]}
            if receipt.get("compiled_numeric_plan_sha256"):
                numeric = trial.numeric_plan(receipt)
                try:
                    proposal, _ = compile_plan_partition(numeric, image_size=tuple(size), image_name=trial.image_name)
                    row["deterministic_compile"] = "passed"
                    row["rooms"] = sum(len(floor["cells"]) for floor in proposal["geometry"]["floors"])
                except ValueError as error:
                    row.update(deterministic_compile="failed", reason=str(error))
            else:
                row["deterministic_compile"] = "not_resolvable"
            if receipt["status"] == "passed":
                trial.verified_plan(receipt["plan_sha256"])
                assert row["deterministic_compile"] == "passed"
            rows.append(row)
    return rows


def prepare_reader(data, name):
    target = SCRATCH / name
    if list(target.glob("trial_workspace/trial_receipts/trial_*.json")):
        raise ValueError(f"use a fresh replay output directory: {target}")
    (target / "images").mkdir(parents=True, exist_ok=True)
    image = data["record"]["image"]
    old_manifest = json.loads((data["reader"] / "inputs.json").read_bytes())
    write(target / "inputs.json", {"images": {image: old_manifest["images"][image]}, "image_kind": "drawings"})
    shutil.copyfile(data["reader"] / "images" / image, target / "images" / image)
    if (data["reader"] / "pixel_profiles").is_dir() and not (target / "pixel_profiles").exists():
        shutil.copytree(data["reader"] / "pixel_profiles", target / "pixel_profiles")
    return target


async def replay_rejected_operations(all_events, all_tasks):
    # run5: a complete numeric draft existed but had a seed/topology error.
    events, tasks = all_events["sm24_run5"], all_tasks["sm24_run5"]
    rejected = next(row for row in events if row["id"] == "event-000769")
    prior = next(row for row in events if row["id"] == "event-000747")
    data = tasks[rejected["task"]]
    directory = prepare_reader(data, "repair_run5")
    async with PlanTrialSession(directory, data["record"]["image"], root=ROOT) as trial:
        baseline = await trial.run(prior["arguments"]["plan"])
        assert baseline["status"] == "failed"
    async with PlanTrialSession(directory, data["record"]["image"], root=ROOT) as trial:
        with_draft = await trial.run(**rejected["arguments"])
        run5 = {"event": rejected["id"], "old_status": "rejected", "new_status": with_draft["status"],
                "baseline_status": baseline["status"], "base_plan_sha256": with_draft["base_plan_sha256"],
                "reason": with_draft.get("reason"), "changed_items": [row["item"] for row in with_draft["changes"]]}
    # run3: replay the original two operations, not its later stripped workaround.
    events, tasks = all_events["sm24_run3"], all_tasks["sm24_run3"]
    rejected = next(row for row in events if row["id"] == "event-000642")
    data, prior = tasks[rejected["task"]], tasks["plan_F1"]
    directory = prepare_reader(data, "repair_run3")
    async with PlanTrialSession(directory, data["record"]["image"], root=ROOT) as trial:
        trial.inherit_reference(prior["trial"], prior["trial"]._successful()["plan_sha256"], ["plan.y_anchors"])
        receipt = await trial.run(**rejected["arguments"])
        assert receipt["status"] == "passed", receipt.get("reason")
        run3 = {"event": rejected["id"], "old_status": "rejected", "new_status": receipt["status"],
                "changed_items": [row["item"] for row in receipt["changes"]],
                "annotation_changes": [row["item"] for row in receipt["plan_revision"]["annotation_changes"]]}
    return {"sm24_run5": run5, "sm24_run3": run3}


def replay_dispatch_baseline(all_events, all_tasks):
    """Distinguish D1k regressions from checks added before this dispatch."""
    module = types.ModuleType("src.agent.runtime_roles._d1k_dispatch_submission")
    code = subprocess.check_output([
        "git", "show", "f73fbbc8:src/agent/runtime_roles/submission.py"
    ], cwd=ROOT).decode("utf-8")
    exec(compile(code, "<dispatch submission.py>", "exec"), module.__dict__)
    rows = []
    for name, events in all_events.items():
        for event in events:
            if event["tool"] != "submit_plan_reading":
                continue
            data = all_tasks[name][event["task"]]
            submission = module.ReaderSubmission(role_id="plan_reader", image_name=data["record"]["image"],
                                                  trial=data["trial"], target=data["record"]["target"])
            manifest = json.loads((data["reader"] / "inputs.json").read_bytes())
            submission.image_size = manifest["images"][submission.image_name]["size"]
            try:
                result = submission.submit(event["arguments"])
            except ValueError as error:
                result = {"status": "rejected", "reason": str(error)}
            rows.append({"run": name, "event": event["id"], "historic_status": event["result"].get("status"),
                         "dispatch_status": result["status"], "reason": result.get("reason")})
    write(HERE / "dispatch_baseline_replay.json", {
        "scope": "Original arguments against f73fbbc8 submission validator with verified historical trials; no model calls.",
        "cases": rows})


def main():
    all_events, all_tasks, original_hashes = {}, {}, {}
    output = {"model_requests": 0, "paratera_requests": 0, "deepseek_requests": 0,
              "scope": "Saved trial integrity + deterministic compile + real submission validation; two real isolated tool repairs, no new model reading.",
              "submissions": [], "trial_products": []}
    for name in RUNS:
        run = SOURCE / name
        events, tasks = history(run), trials(run)
        all_events[name], all_tasks[name] = events, tasks
        paths = {run / "events.jsonl"}
        for data in tasks.values():
            paths.update(data["trial"].artifacts())
            paths.add(data["reader"] / "reader_submission.json")
        original_hashes.update({str(path): digest(path) for path in paths})
        output["trial_products"].extend(replay_trial_products(run, tasks))
        output["submissions"].extend(replay_submissions(run, events, tasks))
        print(name, "replayed", flush=True)
    replay_dispatch_baseline(all_events, all_tasks)
    output["rejected_operations"] = asyncio.run(replay_rejected_operations(all_events, all_tasks))
    output["original_files_unchanged"] = all(digest(Path(path)) == value for path, value in original_hashes.items())
    assert output["original_files_unchanged"]
    output["original_file_hashes"] = original_hashes
    output["after_metrics"] = {"plan_schema_chars": chars(PLAN_SCHEMA), "guidance": guidance_catalog(),
        "submit_description_chars": len(SUBMISSION_TOOLS["plan_reader"]["description"])}
    write(HERE / "replay_results.json", output)
    print(json.dumps({"submissions": len(output["submissions"]), "trial_products": len(output["trial_products"]),
                      "repairs": output["rejected_operations"], "original_files_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
