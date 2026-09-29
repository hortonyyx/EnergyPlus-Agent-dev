"""Aligned-prompt sm21 run: offline preparation, then one separately approved run.

Compared with run91 only three things change: the runner's cold-start sentence,
one sm21 scope sentence (common origin with x east / y north, scale from overall
dimensions instead of endpoint measurement) and a non-blocking plan-axis
orientation report. ``prepare`` stops at the model-process boundary (0 calls).
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parents[3]
EXPERIMENTS = HERE.parent
PREVIOUS = EXPERIMENTS / "2026-09-29_sm21_whole_drawing_run91"
RUNS = {"run92": "2026-09-29_sm21_aligned_prompt_run92",   # interrupted by 429 at 658 s
        "run93": "2026-09-29_sm21_aligned_prompt_run93"}   # fresh restart, same conditions


def records(run_id):
    suffix = "" if run_id == "run92" else f"_{run_id}"
    return HERE / f"preflight_sm21_aligned{suffix}.json", HERE / f"approval_aligned{suffix}.json"
_SCOPE_CHANGE = json.loads((HERE / "scope_sm21_aligned.json").read_text())
_BASE_SCOPE = json.loads((EXPERIMENTS / "2026-09-27_sm21_whole_building_repeat_claude_run58/inputs.json").read_text())["scope"]
assert _BASE_SCOPE.count(_SCOPE_CHANGE["replaced_sentence"]["old"]) == 1
SCOPE = _BASE_SCOPE.replace(_SCOPE_CHANGE["replaced_sentence"]["old"], _SCOPE_CHANGE["replaced_sentence"]["new"])
assert hashlib.sha256(SCOPE.encode()).hexdigest() == _SCOPE_CHANGE["aligned_scope_sha256"]
EXPECTED_CODE_CHANGES = {"scripts/tool_scripts/run_bim_agent.py", "src/agent/geometry/plan_feedback.py"}

sys.path.insert(0, str(RUNTIME))
os.environ["PYTHONPATH"] = str(RUNTIME)
from scripts.tool_scripts import run_bim_agent as runner  # noqa: E402

assert Path(runner.__file__).resolve().is_relative_to(RUNTIME.resolve()), runner.__file__
load = lambda path: json.loads(Path(path).read_text())


def arguments(run):
    return SimpleNamespace(
        command="run", images=RUNTIME / "case_tests/e2e_tests/sm21_anchor/case_data", mesh=None,
        building_input=None, out=run, scope=SCOPE, timeout=3000, provider="claude",
        exploratory_opus=False, effort="medium", max_candidates=24, continuation_rounds=0,
        resume_candidate=None, resume_plan=None, plan_image=None)


def conditions(names):
    return dict(
        case="sm21", previous_run=PREVIOUS.name, scope_sha256=hashlib.sha256(SCOPE.encode()).hexdigest(),
        image_sha256={k: v["sha256"] for k, v in load(PREVIOUS / "inputs.json")["images"].items()},
        implementation_sha256={name: runner.digest(RUNTIME / name) for name in names},
        guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
        references_sha256={k: hashlib.sha256(v.encode()).hexdigest() for k, v in runner.REFERENCES.items()},
        batch_script_sha256=runner.digest(Path(__file__)), provider="claude", role="sonnet",
        effort="medium", timeout_seconds=3000, max_candidates=24, continuation_rounds=0,
        delegation="prohibited by the scope")


async def served(run):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    params = StdioServerParameters(command=sys.executable, cwd=str(RUNTIME),
        args=[str(RUNTIME / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(run)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = sorted(tool.name for tool in (await session.list_tools()).tools)
            result = await session.call_tool("get_bim_reference", {"topic": "reconstruction"})
            payload = result.structuredContent or json.loads(result.content[0].text)
            assert not result.isError and payload["reference"] == runner.REFERENCES["reconstruction"]
            return dict(tool_names=tools, reconstruction_reference_served_exactly=True)


def prepare(run_id):
    class StoppedAtModelBoundary(Exception):
        pass

    def stop(*args, **kwargs):
        raise StoppedAtModelBoundary()

    with tempfile.TemporaryDirectory(prefix="bim-aligned-") as directory:
        run = Path(directory) / "run"
        with patch.object(runner.subprocess, "Popen", stop):
            try:
                runner.run_experiment(arguments(run))
            except StoppedAtModelBoundary:
                pass
            else:
                raise AssertionError("the model launch must be blocked")
        manifest, request = load(run / "inputs.json"), load(run / "agent_request.json")
        frozen = conditions(sorted(manifest["implementation_sha256"]))
        assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
        assert {k: v["sha256"] for k, v in manifest["images"].items()} == frozen["image_sha256"]
        assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
        assert request["system_prompt"] == runner.GUIDE and request["effort"] == "medium"
        previous_request = load(PREVIOUS / "agent_request.json")
        assert request["system_prompt"] == previous_request["system_prompt"], "guidance must equal run91"
        previous_code = load(PREVIOUS / "inputs.json")["implementation_sha256"]
        changed = {k for k in frozen["implementation_sha256"] if frozen["implementation_sha256"][k] != previous_code.get(k)}
        assert changed == EXPECTED_CODE_CHANGES, changed
        exposure = asyncio.run(served(run))
        prompt_change = dict(previous=previous_request["prompt"], current=request["prompt"])
    runner.dump(records(run_id)[0], dict(case="sm21", run_id=run_id, status="prepared_pending_user_decision",
        model_calls=0, model_process_blocked=True, original_images_only=True,
        guidance_identical_to_run91=True, code_changed_from_run91=sorted(changed),
        prompt_change=prompt_change, conditions=frozen, **exposure))
    print(json.dumps(dict(model_calls=0, code_changed_from_run91=sorted(changed),
                          scope_sha256=frozen["scope_sha256"][:12])))


def run_one(run_id):
    RUN = EXPERIMENTS / RUNS[run_id]
    preflight, approval_file = records(run_id)
    approval = load(approval_file)
    assert approval["approved_runs"] == [RUN.name], "record the user's approval for this exact run first"
    prepared = load(preflight)["conditions"]
    assert prepared == conditions(sorted(prepared["implementation_sha256"])), "prepared runtime changed"
    receipt = load(PREVIOUS / "agent_receipt.json")
    assert receipt.get("returncode") == 0 and not (receipt.get("result") or {}).get("is_error")
    assert not RUN.exists(), "do not overwrite or retry an experiment"
    original, calls = runner.subscription, []

    def invoke(path, *call_args, **kwargs):
        calls.append(1)
        assert len(calls) == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = load(path / "inputs.json")
        assert manifest["implementation_sha256"] == prepared["implementation_sha256"]
        runner.dump(path / "experiment_condition.json", dict(run_id=f"{run_id}_aligned", **prepared))
        for relative in manifest["implementation_sha256"]:
            destination = path / "runtime_snapshot" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((RUNTIME / relative).read_bytes())
        return original(path, *call_args, **kwargs)

    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(RUN))
    assert len(calls) == 1
    receipt = load(RUN / "agent_receipt.json")
    print(json.dumps(dict(run=RUN.name, returncode=receipt.get("returncode"),
        elapsed_seconds=receipt.get("elapsed_seconds"), actual_model=receipt.get("actual_model"),
        is_error=(receipt.get("result") or {}).get("is_error"))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--run", choices=sorted(RUNS), default="run92")
    args = parser.parse_args()
    prepare(args.run) if args.action == "prepare" else run_one(args.run)
