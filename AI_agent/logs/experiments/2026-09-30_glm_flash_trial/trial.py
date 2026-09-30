"""One isolated GLM Flash subscription trial; production runtime stays unchanged."""
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
runner = batch.runner
RUN = HERE.parent / "2026-09-30_sm21_instruction_fix_glm_trial01"
BASELINE = HERE.parent / batch.PLAN["run98"][1]
MODEL = "glm-5.3-flash"
TRANSPORT = ("scripts/glm_code.sh", "src/agent/execution/subscription_json.py")
load = batch.load


def arguments(run):
    args = batch.arguments("sm21", run)
    args.provider = "glm"
    return args


def conditions(names):
    value = batch.conditions("sm21", names)
    value.update(provider="glm", requested_model=MODEL,
                 trial_script_sha256=runner.digest(Path(__file__)),
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

    with tempfile.TemporaryDirectory(prefix="bim-glm-preflight-") as directory:
        run = Path(directory) / "run"
        with patch.object(runner.subprocess, "Popen", stop):
            try:
                runner.run_experiment(arguments(run))
            except ModelBoundary:
                pass
            else:
                raise AssertionError("Model launch must be blocked during preparation")
        manifest, request = load(run / "inputs.json"), load(run / "agent_request.json")
        old_manifest, old_request = load(BASELINE / "inputs.json"), load(BASELINE / "agent_request.json")
        assert manifest["implementation_sha256"] == old_manifest["implementation_sha256"]
        image_hashes = {k: v["sha256"] for k, v in manifest["images"].items()}
        assert image_hashes == {k: v["sha256"] for k, v in old_manifest["images"].items()}
        assert request["prompt"] == old_request["prompt"]
        assert request["system_prompt"] == old_request["system_prompt"]
        assert request["requested_model"] == MODEL and request["provider"] == "glm"
        assert request["effort"] == "medium"
        assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
        assert not manifest["input_contents"]["ground_truth_or_evaluation"]["included"]
        exposure = asyncio.run(batch.served(run))
        assert len(exposure["tool_names"]) == 39
        prepared = conditions(sorted(manifest["implementation_sha256"]))
        runner.dump(HERE / "preflight.json", dict(
            model_calls=0, model_process_blocked=True, baseline=BASELINE.name,
            same_prompt_system_images_and_runtime_as_run98=True,
            image_sha256=image_hashes, request=request, conditions=prepared, **exposure))
        print(json.dumps(dict(model_calls=0, baseline=BASELINE.name,
            same_prompt_system_images_and_runtime_as_run98=True,
            production_files=len(prepared["implementation_sha256"]), tools=len(exposure["tool_names"]),
            provider="glm", requested_model=MODEL)))


def run_once():
    approval, preflight = load(HERE / "approval.json"), load(HERE / "preflight.json")
    assert approval["run_now"] == [RUN.name]
    prepared = preflight["conditions"]
    assert prepared == conditions(sorted(prepared["implementation_sha256"]))
    assert not RUN.exists(), "Never overwrite or automatically retry this trial"
    original, calls = runner.subscription, []

    def invoke(path, *args, **kwargs):
        calls.append(1)
        assert len(calls) == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = load(path / "inputs.json")
        assert manifest["provider"] == "glm"
        assert manifest["implementation_sha256"] == prepared["implementation_sha256"]
        assert {k: v["sha256"] for k, v in manifest["images"].items()} == preflight["image_sha256"]
        runner.dump(path / "experiment_condition.json", dict(run_id="glm_trial01", **prepared))
        for name in set(manifest["implementation_sha256"]) | set(TRANSPORT):
            target = path / "runtime_snapshot" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        return original(path, *args, **kwargs)

    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(RUN))
    assert len(calls) == 1
    receipt = load(RUN / "agent_receipt.json")
    normal = (receipt.get("returncode") == 0 and receipt.get("actual_model") == MODEL
              and not receipt.get("timed_out") and not receipt.get("routing_error")
              and not (receipt.get("result") or {}).get("is_error"))
    print(json.dumps(dict(run=RUN.name, actual_model=receipt.get("actual_model"),
        returncode=receipt.get("returncode"), elapsed_seconds=receipt.get("elapsed_seconds"),
        ended_normally=normal)))
    if not normal:
        sys.exit("Trial did not complete normally; retain evidence and stop, no retry")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    prepare() if args.action == "prepare" else run_once()
