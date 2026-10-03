"""T1 GLM subscription test launcher. Default 6000 seconds; prepare calls no model.

Original images, task scope, medium effort, 24 candidates, no delegation and no
continuations are inherited from the 10-02 baseline. Only T1 tools/instructions
and the configurable time budget change. Opus launches one explicit run at a
time; existing evidence is never overwritten and no retry/fallback is automatic.
"""
import argparse
import asyncio
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
baseline = importlib.import_module("AI_agent.logs.experiments.2026-10-02_glm_baseline.baseline")
runner, batch, load = baseline.runner, baseline.batch, baseline.load
PLAN = {case: f"2026-10-03_{case}_glm_tools_t1" for case in ("sm24", "sm25", "sm21")}


def arguments(case, run, timeout):
    value = baseline.arguments(case, run)
    value.timeout = timeout
    value.floor_plan_images = ["1f_view.png"] + ([] if case == "sm24" else ["2f_view.png"])
    return value


def conditions(case, names, timeout):
    value = baseline.conditions(case, names)
    value.update(timeout_seconds=timeout, launcher_sha256=runner.digest(Path(__file__)),
                 floor_plan_images=arguments(case, HERE, timeout).floor_plan_images)
    return value


def prepare(timeout):
    class ModelBoundary(Exception):
        pass
    attempts = []
    def stop(command, **kwargs):
        assert command[0] == str(ROOT / "scripts/glm_code.sh")
        assert command[command.index("--model") + 1] == baseline.MODEL
        assert kwargs["env"]["GLM_MODEL"] == kwargs["env"]["GLM_SMALL_MODEL"] == baseline.MODEL
        attempts.append(command[0])
        raise ModelBoundary()
    temp_root = ROOT / ".tmp_t1"
    temp_root.mkdir(exist_ok=True)
    summary = {}
    for case in PLAN:
        with tempfile.TemporaryDirectory(dir=temp_root, prefix="prepare-") as directory:
            run = Path(directory) / "run"
            with patch.object(tempfile, "tempdir", str(temp_root)), patch.object(runner.subprocess, "Popen", stop):
                try:
                    runner.run_experiment(arguments(case, run, timeout))
                except ModelBoundary:
                    pass
                else:
                    raise AssertionError("prepare did not stop at the model-process boundary")
            manifest, request = load(run / "inputs.json"), load(run / "agent_request.json")
            frozen = conditions(case, sorted(manifest["implementation_sha256"]), timeout)
            assert request["requested_model"] == baseline.MODEL and request["effort"] == "medium"
            assert manifest["time_budget_seconds"] == timeout and manifest["max_candidates"] == 24
            assert manifest["continuation_rounds"] == 0
            assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
            assert not manifest["input_contents"]["ground_truth_or_evaluation"]["included"]
            exposure = asyncio.run(batch.served(run))
            reference_name = ({"sm21": "2026-09-30_sm21_instruction_fix_glm_trial01"}.get(case)
                              or f"2026-10-02_{case}_glm_baseline")
            old = HERE.parent / reference_name
            old_manifest, old_request = load(old / "inputs.json"), load(old / "agent_request.json")
            image_hashes = {k: v["sha256"] for k, v in manifest["images"].items()}
            assert image_hashes == {k: v["sha256"] for k, v in old_manifest["images"].items()}
            assert manifest["scope"] == old_manifest["scope"]
            assert request["prompt"] == old_request["prompt"].replace("Budget: 3000 seconds", f"Budget: {timeout} seconds")
            report = dict(case=case, model_calls=0, model_process_blocked=True,
                image_sha256=image_hashes, conditions=frozen, **exposure,
                system_prompt_chars=len(request["system_prompt"]), comparison=dict(
                    baseline_run=reference_name, same_images=True, same_scope=True,
                    prompt_changed_only_budget=True,
                    system_prompt_changed=request["system_prompt"] != old_request["system_prompt"]))
            runner.dump(HERE / f"preflight_{case}.json", report)
            summary[case] = dict(tools=len(exposure["tool_names"]), timeout_seconds=timeout,
                                 **report["comparison"])
    assert len(attempts) == 3
    print(json.dumps(dict(model_calls=0, model_processes_started=0, runs=summary), ensure_ascii=False, indent=2))


def run_one(case, timeout):
    target = HERE.parent / PLAN[case]
    preflight = load(HERE / f"preflight_{case}.json")
    expected = preflight["conditions"]
    assert expected == conditions(case, sorted(expected["implementation_sha256"]), timeout), "runtime changed; prepare again"
    assert not target.exists(), "refusing to overwrite or retry an existing run"
    original, calls = runner.subscription, []
    def invoke(run, *args, **kwargs):
        calls.append(1)
        assert len(calls) == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = load(run / "inputs.json")
        assert manifest["implementation_sha256"] == expected["implementation_sha256"]
        assert {k: v["sha256"] for k, v in manifest["images"].items()} == preflight["image_sha256"]
        runner.dump(run / "experiment_condition.json", expected)
        for relative in set(expected["implementation_sha256"]) | set(baseline.TRANSPORT):
            destination = run / "runtime_snapshot" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        return original(run, *args, **kwargs)
    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(case, target, timeout))
    assert len(calls) == 1
    receipt = load(target / "agent_receipt.json")
    normal = (receipt.get("returncode") == 0 and receipt.get("actual_model") == baseline.MODEL
              and not receipt.get("timed_out") and not receipt.get("routing_error")
              and not (receipt.get("result") or {}).get("is_error"))
    print(json.dumps(dict(run=target.name, ended_normally=normal,
                         actual_model=receipt.get("actual_model"), timed_out=receipt.get("timed_out", False))))
    if not normal:
        raise SystemExit("Run interrupted/failed; evidence retained, no automatic retry or next run")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--run", choices=tuple(PLAN))
    parser.add_argument("--timeout", type=int, default=6000)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.action == "run" and not args.run:
        parser.error("run requires one explicit --run")
    prepare(args.timeout) if args.action == "prepare" else run_one(args.run, args.timeout)
