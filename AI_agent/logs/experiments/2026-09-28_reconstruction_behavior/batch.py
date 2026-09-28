"""Prepare offline; execute each cold run only within a user-approved batch.

There is deliberately no loop that starts the next model invocation. Inspect the
real completion receipt in a separate step before running the second command.
"""
import argparse
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch

from scripts.tool_scripts import run_bim_agent as runner
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPE = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.run_cold").SCOPE
RUNS = ["2026-09-28_sm21_behavior_cold_run82", "2026-09-28_sm21_behavior_repeat_run83"]


def arguments(out):
    return SimpleNamespace(command="run", images=ROOT / "case_tests/e2e_tests/sm21_anchor/case_data",
        mesh=None, building_input=None, out=out, scope=SCOPE, timeout=3000,
        provider="claude", exploratory_opus=False, effort="medium", max_candidates=24,
        continuation_rounds=0, resume_candidate=None, resume_plan=None, plan_image=None)


def conditions():
    previous = json.loads((HERE.parent / "2026-09-28_sm21_threshold_current_run80/inputs.json").read_text())
    return dict(scope=SCOPE, images=previous["images"],
        implementation_sha256={name: runner.digest(ROOT / name) for name in previous["implementation_sha256"]},
        method_sha256=hashlib.sha256(runner.REFERENCES["reconstruction"].encode()).hexdigest(),
        guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
        batch_script_sha256=runner.digest(Path(__file__)),
        provider="claude", role="sonnet", effort="medium", timeout_seconds=3000,
        max_candidates=24, continuation_rounds=0)


def completed(run):
    summary = json.loads((run / "summary.json").read_text())
    receipt = json.loads((run / "agent_receipt.json").read_text())
    assert summary.get("agent_response_completed") is True
    assert receipt.get("returncode") == 0 and not receipt.get("result", {}).get("is_error")


async def check_reference(run):
    import sys
    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(run)], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            catalog = await session.list_tools()
            result = await session.call_tool("get_bim_reference", {"topic": "reconstruction"})
            assert not result.isError
            payload = result.structuredContent or json.loads(result.content[0].text)
            assert payload["reference"] == runner.REFERENCES["reconstruction"]
            return dict(tool_count=len(catalog.tools), exact_reference_served=True)


def prepare():
    class StoppedAtModelBoundary(Exception):
        pass

    def prevent_launch(*args, **kwargs):
        # Do not retain the environment or command (which may carry credentials).
        raise StoppedAtModelBoundary()

    with tempfile.TemporaryDirectory(prefix="bim-behavior-preflight-") as folder:
        run = Path(folder) / "run"
        with patch.object(runner.subprocess, "Popen", prevent_launch):
            try:
                runner.run_experiment(arguments(run))
            except StoppedAtModelBoundary:
                pass
            else:
                raise AssertionError("Expected to stop before launching the model")
        request = json.loads((run / "agent_request.json").read_text())
        manifest = json.loads((run / "inputs.json").read_text())
        frozen = conditions()
        assert manifest["images"] == frozen["images"]
        assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
        assert manifest["input_contents"]["saved_generated_proposal"]["included"] is False
        assert request["requested_role"] == "sonnet" and request["effort"] == "medium"
        assert request["system_prompt"] == runner.GUIDE
        mcp = asyncio.run(check_reference(run))
    runner.dump(HERE / "proposed_batch.json", dict(status="prepared_pending_user_decision",
        runs=RUNS, total_primary_invocations=2, sequential=True, conditions=frozen,
        withheld=["saved plans/BIM", "object_traces.json", "developer_replay", "GT/evaluation",
                  "old observations/calibration", "error locations/counts", "correct dimensions"],
        behavior_evaluation=["Reference read is exposure only; check actual object/extent interpretation.",
            "Trace complete endpoints and distinct facade/storey height families into saved source values.",
            "For chain transcription, check spatial segment order and visible frame proportions.",
            "Trace repair or justified unchanged value; preserve incorrect confirmations and early stops.",
            "Audit whole-building partitions/openings/hosts/connections/heights, not just selected windows."],
        limits="Two cold runs test adoption and observed repeatability, not causal proof or cross-case stability. No recovery, continuation, local model, automatic retry or fallback. Stop batch on a failed/interrupted receipt."))
    runner.dump(HERE / "preflight.json", dict(model_calls=0, model_process_blocked=True,
        exact_scope=True, original_images_only=True, manifest_hashes_match=True,
        request_role=request["requested_role"], effort=request["effort"], timeout=request["timeout_seconds"],
        **mcp))
    print(json.dumps({"model_calls": 0, "status": "prepared_pending_user_decision", **mcp}))


def execute(index):
    proposed = json.loads((HERE / "proposed_batch.json").read_text())
    assert proposed["conditions"] == conditions(), "Prepared production/method changed; update the concrete proposal."
    if index == 2:
        completed(HERE.parent / RUNS[0])
    run = HERE.parent / RUNS[index - 1]
    assert not run.exists(), "Never overwrite a run or automatically retry."
    original = runner.subscription
    calls = 0

    def invoke(path, *args, **kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = json.loads((path / "inputs.json").read_text())
        assert manifest["images"] == proposed["conditions"]["images"]
        assert manifest["implementation_sha256"] == proposed["conditions"]["implementation_sha256"]
        runner.dump(path / "experiment_condition.json", proposed["conditions"])
        for name in manifest["implementation_sha256"]:
            target = path / "runtime_snapshot" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        return original(path, *args, **kwargs)

    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(run))
    assert calls == 1
    completed(run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--index", type=int, choices=[1, 2])
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        assert args.index is not None
        execute(args.index)
