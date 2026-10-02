"""Whole-drawing-first guidance regression: offline preparation, then one approved run per call.

``prepare`` stops every case at the model-process boundary (0 model calls) and
checks that only the guidance module differs from main, that scope/images are
byte-identical to the earlier good cold starts, and what the MCP server serves.
``run --id runNN`` launches exactly one planned run after the previous planned
run's real receipt shows a completed response. It never retries or overwrites.
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
CASES = {
    "sm21": dict(images="case_tests/e2e_tests/sm21_anchor/case_data",
                 baseline="2026-09-27_sm21_whole_building_repeat_claude_run58"),
    "sm24": dict(images="case_tests/e2e_tests/sm24_anchor/case_data",
                 baseline="2026-09-26_sm24_whole_building_repeat_claude_run56"),
    "sm25": dict(images="case_tests/e2e_tests/sm25-L_anchor/case_data",
                 baseline="2026-09-26_sm25_height_repeat_claude_run54"),
}
PLAN = [
    ("run91", "sm21", "2026-09-29_sm21_whole_drawing_run91"),
    ("run92", "sm21", "2026-09-29_sm21_whole_drawing_repeat_run92"),
    ("run93", "sm24", "2026-09-29_sm24_whole_drawing_run93"),
    ("run94", "sm25", "2026-09-29_sm25_whole_drawing_run94"),
]

sys.path.insert(0, str(RUNTIME))
os.environ["PYTHONPATH"] = str(RUNTIME)
from scripts.tool_scripts import run_bim_agent as runner  # noqa: E402

assert Path(runner.__file__).resolve().is_relative_to(RUNTIME.resolve()), runner.__file__
load = lambda path: json.loads(Path(path).read_text())


def baseline(case):
    return load(EXPERIMENTS / CASES[case]["baseline"] / "inputs.json")


def arguments(case, run):
    return SimpleNamespace(
        command="run", images=RUNTIME / CASES[case]["images"], mesh=None, building_input=None,
        out=run, scope=baseline(case)["scope"], timeout=3000, provider="claude",
        exploratory_opus=False, effort="medium", max_candidates=24, continuation_rounds=0,
        resume_candidate=None, resume_plan=None, plan_image=None)


def conditions(case, names):
    scope = baseline(case)["scope"]
    return dict(
        case=case, baseline_run=CASES[case]["baseline"],
        scope_sha256=hashlib.sha256(scope.encode()).hexdigest(),
        image_sha256={k: v["sha256"] for k, v in baseline(case)["images"].items()},
        implementation_sha256={name: runner.digest(RUNTIME / name) for name in names},
        guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
        references_sha256={k: hashlib.sha256(v.encode()).hexdigest() for k, v in runner.REFERENCES.items()},
        batch_script_sha256=runner.digest(Path(__file__)), provider="claude", role="sonnet",
        effort="medium", timeout_seconds=3000, max_candidates=24, continuation_rounds=0,
        delegation="prohibited by the unchanged scope")


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
            assert not result.isError
            payload = result.structuredContent or json.loads(result.content[0].text)
            assert payload["reference"] == runner.REFERENCES["reconstruction"]
            return dict(tool_names=tools, reconstruction_reference_served_exactly=True)


def prepare(case):
    class StoppedAtModelBoundary(Exception):
        pass

    def stop(*args, **kwargs):
        raise StoppedAtModelBoundary()

    with tempfile.TemporaryDirectory(prefix="bim-whole-drawing-") as directory:
        run = Path(directory) / "run"
        with patch.object(runner.subprocess, "Popen", stop):
            try:
                runner.run_experiment(arguments(case, run))
            except StoppedAtModelBoundary:
                pass
            else:
                raise AssertionError("the model launch must be blocked")
        manifest, request = load(run / "inputs.json"), load(run / "agent_request.json")
        frozen = conditions(case, sorted(manifest["implementation_sha256"]))
        assert manifest["scope"] == baseline(case)["scope"]
        assert {k: v["sha256"] for k, v in manifest["images"].items()} == frozen["image_sha256"]
        assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
        assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
        assert request["requested_role"] == "sonnet" and request["effort"] == "medium"
        assert request["system_prompt"] == runner.GUIDE
        old = load(EXPERIMENTS / CASES[case]["baseline"] / "agent_request.json")
        assert request["prompt"].split("\nBudget:")[0] == old["prompt"].split("\nBudget:")[0]
        prompt_identical = request["prompt"] == old["prompt"]
        old_guide = hashlib.sha256(old["system_prompt"].encode()).hexdigest()
        exposure = asyncio.run(served(run))
    runner.dump(HERE / f"preflight_{case}.json", dict(case=case, status="prepared_pending_user_decision",
        model_calls=0, model_process_blocked=True, original_images_only=True,
        scope_identical_to_baseline=True, full_prompt_identical_to_baseline=prompt_identical,
        baseline_guide_sha256=old_guide, conditions=frozen, **exposure))
    print(json.dumps(dict(case=case, model_calls=0, guide_sha256=frozen["guide_sha256"][:12])))


def completed(run):
    summary, receipt = load(run / "summary.json"), load(run / "agent_receipt.json")
    assert summary.get("agent_response_completed") is True, "previous run did not complete"
    assert receipt.get("returncode") == 0 and not (receipt.get("result") or {}).get("is_error")
    assert receipt.get("actual_model") == "claude-sonnet-5" and not receipt.get("routing_error")


def run_one(run_id):
    index = [item[0] for item in PLAN].index(run_id)
    _, case, name = PLAN[index]
    prepared = load(HERE / f"preflight_{case}.json")["conditions"]
    current = conditions(case, sorted(prepared["implementation_sha256"]))
    assert prepared == current, "prepared runtime changed; prepare again before any run"
    if index:
        completed(EXPERIMENTS / PLAN[index - 1][2])
    run = EXPERIMENTS / name
    assert not run.exists(), "do not overwrite or retry an experiment"
    original, calls = runner.subscription, []

    def invoke(path, *call_args, **kwargs):
        calls.append(1)
        assert len(calls) == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = load(path / "inputs.json")
        assert manifest["implementation_sha256"] == prepared["implementation_sha256"]
        runner.dump(path / "experiment_condition.json", dict(run_id=run_id, **prepared))
        for relative in manifest["implementation_sha256"]:
            destination = path / "runtime_snapshot" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((RUNTIME / relative).read_bytes())
        return original(path, *call_args, **kwargs)

    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(case, run))
    assert len(calls) == 1
    receipt = load(run / "agent_receipt.json")
    print(json.dumps(dict(run=name, returncode=receipt.get("returncode"),
        elapsed_seconds=receipt.get("elapsed_seconds"), actual_model=receipt.get("actual_model"),
        is_error=(receipt.get("result") or {}).get("is_error"))))
    completed(run)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--case", choices=sorted(CASES))
    parser.add_argument("--id", choices=[item[0] for item in PLAN])
    args = parser.parse_args()
    if args.action == "prepare":
        for case in ([args.case] if args.case else sorted(CASES)):
            prepare(case)
    else:
        if not args.id:
            parser.error("run requires --id")
        run_one(args.id)


if __name__ == "__main__":
    main()
