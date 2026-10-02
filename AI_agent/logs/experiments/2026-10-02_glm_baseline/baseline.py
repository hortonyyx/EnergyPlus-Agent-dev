"""GLM Flash cold-start baselines on the frozen baseline (10-02): sm24, then sm25.

Same scope, references, timeout, candidate budget, effort and prohibition of
delegation as the 09-30 instruction-fix batch (run98-101); only the subscription
route changes to the existing GLM plan (glm-5.3-flash through Claude Code).
``prepare`` stops every planned run at the model-process boundary (0 calls).
``run --run ID`` launches exactly one listed run; read its receipt before the next.
"""
import argparse
import asyncio
import importlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
batch = importlib.import_module("AI_agent.logs.experiments.2026-09-30_instruction_fix.batch")
runner, load = batch.runner, batch.load
EXPERIMENTS = HERE.parent
MODEL = "glm-5.3-flash"
TRANSPORT = ("scripts/glm_code.sh", "src/agent/execution/subscription_json.py")
PLAN = {"glm_sm24": ("sm24", "2026-10-02_sm24_glm_baseline"),
        "glm_sm25": ("sm25", "2026-10-02_sm25_glm_baseline")}
# Sonnet runs with the same scope on the same case, for the condition comparison only.
SONNET_REFERENCE = {"sm24": "2026-09-30_sm24_instruction_fix_run100"}


def arguments(case, run):
    args = batch.arguments(case, run)
    args.provider = "glm"
    return args


def conditions(case, names):
    value = batch.conditions(case, names)
    value.update(provider="glm", role="sonnet slot routed to glm-5.3-flash", requested_model=MODEL,
                 baseline_script_sha256=runner.digest(Path(__file__)),
                 transport_sha256={name: runner.digest(ROOT / name) for name in TRANSPORT})
    return value


def prepare():
    class ModelBoundary(Exception):
        pass

    def stop(command, **kwargs):
        assert command[0] == str(ROOT / "scripts/glm_code.sh")
        assert command[command.index("--model") + 1] == MODEL
        assert kwargs["env"]["GLM_MODEL"] == kwargs["env"]["GLM_SMALL_MODEL"] == MODEL
        raise ModelBoundary()

    summary = {}
    for run_id, (case, _) in PLAN.items():
        with tempfile.TemporaryDirectory(prefix="bim-glm-base-") as directory:
            run = Path(directory) / "run"
            with patch.object(runner.subprocess, "Popen", stop):
                try:
                    runner.run_experiment(arguments(case, run))
                except ModelBoundary:
                    pass
                else:
                    raise AssertionError("the model launch must be blocked during preparation")
            manifest, request = load(run / "inputs.json"), load(run / "agent_request.json")
            frozen = conditions(case, sorted(manifest["implementation_sha256"]))
            assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
            assert request["system_prompt"] == batch.GUIDE and request["effort"] == "medium"
            assert request["requested_model"] == MODEL and request["provider"] == "glm"
            assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
            assert not manifest["input_contents"]["ground_truth_or_evaluation"]["included"]
            exposure = asyncio.run(batch.served(run))
            comparison = {}
            if case in SONNET_REFERENCE:
                old = EXPERIMENTS / SONNET_REFERENCE[case]
                old_manifest, old_request = load(old / "inputs.json"), load(old / "agent_request.json")
                old_impl, new_impl = old_manifest["implementation_sha256"], manifest["implementation_sha256"]
                comparison = dict(
                    sonnet_run=old.name,
                    same_prompt=request["prompt"] == old_request["prompt"],
                    same_system_prompt=request["system_prompt"] == old_request["system_prompt"],
                    same_images={k: v["sha256"] for k, v in manifest["images"].items()}
                    == {k: v["sha256"] for k, v in old_manifest["images"].items()},
                    implementation_files_changed=sorted(
                        k for k in set(old_impl) | set(new_impl) if old_impl.get(k) != new_impl.get(k)))
            runner.dump(HERE / f"preflight_{run_id}.json", dict(
                run_id=run_id, case=case, status="prepared", model_calls=0,
                model_process_blocked=True, original_images_only=True,
                image_sha256={k: v["sha256"] for k, v in manifest["images"].items()},
                prompt=request["prompt"], conditions=frozen, comparison=comparison, **exposure))
            summary[run_id] = dict(case=case, tools=len(exposure["tool_names"]), **comparison)
    print(json.dumps(dict(model_calls=0, runs=summary), indent=1, ensure_ascii=False))


def run_one(run_id):
    case, name = PLAN[run_id]
    target = EXPERIMENTS / name
    approval = load(HERE / "approval.json")
    assert run_id in approval["run_now"], "record the user's go-ahead for this exact run first"
    order = list(PLAN)
    for earlier in order[:order.index(run_id)]:
        receipt = load(EXPERIMENTS / PLAN[earlier][1] / "agent_receipt.json")
        assert receipt.get("returncode") == 0 and not (receipt.get("result") or {}).get("is_error"), \
            f"{earlier} did not end normally; stop the batch"
    preflight = load(HERE / f"preflight_{run_id}.json")
    prepared = preflight["conditions"]
    assert prepared == conditions(case, sorted(prepared["implementation_sha256"])), "prepared runtime changed"
    assert not target.exists(), "do not overwrite or retry an experiment"
    original, calls = runner.subscription, []

    def invoke(path, *call_args, **kwargs):
        calls.append(1)
        assert len(calls) == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = load(path / "inputs.json")
        assert manifest["provider"] == "glm"
        assert manifest["implementation_sha256"] == prepared["implementation_sha256"]
        assert {k: v["sha256"] for k, v in manifest["images"].items()} == preflight["image_sha256"]
        runner.dump(path / "experiment_condition.json", dict(run_id=run_id, **prepared))
        for relative in set(manifest["implementation_sha256"]) | set(TRANSPORT):
            destination = path / "runtime_snapshot" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / relative).read_bytes())
        return original(path, *call_args, **kwargs)

    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(case, target))
    assert len(calls) == 1
    receipt = load(target / "agent_receipt.json")
    normal = (receipt.get("returncode") == 0 and receipt.get("actual_model") == MODEL
              and not receipt.get("timed_out") and not receipt.get("routing_error")
              and not (receipt.get("result") or {}).get("is_error"))
    print(json.dumps(dict(run=target.name, actual_model=receipt.get("actual_model"),
        returncode=receipt.get("returncode"), elapsed_seconds=receipt.get("elapsed_seconds"),
        ended_normally=normal)))
    if not normal:
        sys.exit(f"{run_id} did not end normally; keep the evidence and stop, no retry")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--run", choices=tuple(PLAN))
    args = parser.parse_args()
    prepare() if args.action == "prepare" else run_one(args.run)
