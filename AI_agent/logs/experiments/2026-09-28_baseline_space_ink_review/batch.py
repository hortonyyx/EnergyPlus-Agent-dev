"""Prepare offline, then run exactly one separately approved historical-base experiment."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from make_variant import BASE, HERE, ROOT, TREE

HISTORY = HERE.parent / "2026-09-27_sm21_whole_building_repeat_claude_run58"
RUN = HERE.parent / "2026-09-28_sm21_baseline_ink_run87"
load = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
save = lambda path, value: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def producer():
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TREE, text=True).strip() == BASE
    assert subprocess.check_output(["git", "diff", "HEAD", "--name-only", "--", "src", "scripts"], cwd=TREE, text=True).splitlines() == ["scripts/tool_scripts/run_bim_agent.py"]
    assert set(subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "--", "src", "scripts"], cwd=TREE, text=True).splitlines()) == {
        "scripts/tool_scripts/bim_space_ink_feedback.py", "src/agent/geometry/space_ink_support.py"}
    assert subprocess.check_output(["git", "diff", "--", "scripts/tool_scripts/run_bim_agent.py"], cwd=TREE) == (HERE / "runtime.patch").read_bytes()
    prior = load(HISTORY / "inputs.json")
    for name, value in prior["implementation_sha256"].items():
        if name != "scripts/tool_scripts/run_bim_agent.py":
            assert sha(TREE / name) == value, name
    assert sha(TREE / "src/agent/geometry/space_ink_support.py") == sha(ROOT / "src/agent/geometry/space_ink_support.py")
    assert sha(TREE / "scripts/tool_scripts/bim_space_ink_feedback.py") == sha(HERE / "feedback.py")
    sys.path.insert(0, str(TREE))
    from scripts.tool_scripts import run_bim_agent as runner
    from src.agent.execution import subscription_json
    from src.agent.geometry import plan_partition, source_bim, space_ink_support
    modules = [runner, subscription_json, plan_partition, source_bim, space_ink_support]
    assert all(Path(m.__file__).resolve().is_relative_to(TREE) for m in modules)
    expected = load(HISTORY / "agent_request.json")
    assert runner.GUIDE == expected["system_prompt"]
    images = TREE / "case_tests/e2e_tests/sm21_anchor/case_data"
    assert {p.name: sha(p) for p in images.glob("*.png")} == {k: v["sha256"] for k, v in prior["images"].items()}
    return runner, prior, expected, modules, images


def args(out, prior, images):
    return SimpleNamespace(command="run", images=images, mesh=None, building_input=None,
        out=out, scope=prior["scope"], timeout=3000, provider="claude", exploratory_opus=False,
        effort="medium", resume_candidate=None, resume_plan=None, plan_image=None)


def dry_inputs(runner, prior, expected, images, folder):
    class Boundary(Exception):
        pass
    def stop(command, **kwargs):
        assert command[0] == "claude"
        assert command[command.index("--system-prompt") + 1] == expected["system_prompt"]
        mcp = json.loads(command[command.index("--mcp-config") + 1])["mcpServers"]["bim"]
        assert Path(mcp["args"][0]).resolve() == Path(runner.__file__).resolve()
        raise Boundary()
    with patch.object(subprocess, "Popen", stop):
        try:
            runner.run_experiment(args(folder, prior, images))
        except Boundary:
            pass
        else:
            raise AssertionError("Model-process boundary was not reached")
    assert load(folder / "agent_request.json") == expected
    return load(folder / "inputs.json")


async def inspect_stdio(runner, folder):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    server = StdioServerParameters(command=sys.executable,
        args=[str(Path(runner.__file__).resolve()), "serve", str(folder)], cwd=str(TREE))
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            actual = {item.name: item.model_dump(mode="json") for item in result.tools}
    expected = load(HERE.parent / "2026-09-27_sm21_runtime_surface_setup/historical_tools.json")
    expected["build_bim"]["description"] = expected["build_bim"]["description"].replace(
        "Six immutable candidates maximum.", "Up to 24 immutable candidates; the run input records its budget.")
    assert actual == expected and len(actual) == 36
    return actual


def prepare():
    runner, prior, expected, modules, images = producer()
    with tempfile.TemporaryDirectory(prefix="baseline-ink-preflight-") as tmp:
        folder = Path(tmp) / "dry_run"
        inputs = dry_inputs(runner, prior, expected, images, folder)
        actual = asyncio.run(inspect_stdio(runner, folder))
    files = dict(inputs["implementation_sha256"])
    files["src/agent/execution/subscription_json.py"] = sha(TREE / "src/agent/execution/subscription_json.py")
    frozen = dict(producer_commit=BASE, worktree=str(TREE), proposed_run=str(RUN),
        mode="historical_base_plus_interior_ink_review", scope=prior["scope"], provider="claude",
        role="sonnet", effort="medium", timeout_seconds=3000, max_candidates=24,
        continuation_rounds=0, primary_invocations=1, local_model_invocations=0,
        implementation_sha256=inputs["implementation_sha256"], execution_sha256=files,
        image_sha256={k: v["sha256"] for k, v in prior["images"].items()},
        guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
        request_sha256=sha(HISTORY / "agent_request.json"),
        package_sha256={name: sha(HERE / name) for name in ("batch.py", "feedback.py", "runtime.patch", "make_variant.py")},
        python_version=platform.python_version(),
        claude_cli_version=subprocess.check_output(["claude", "--version"], text=True).strip(),
        imported_modules={m.__name__: m.__file__ for m in modules},
        limitations=["Historical environment/provider internals are not frozen by Git.",
            "Raw line feedback plus mechanical 6-to-24 budget port; not a causal single-variable A/B.",
            "One run cannot establish stable quality; all geometry/heights still require evaluation."])
    save(HERE / "frozen.json", frozen)
    save(HERE / "preflight.json", dict(model_calls=0, tool_count=len(actual), tools=actual,
        tool_surface_matches_history_except_budget_text=True, request_exactly_matches_run58=True,
        implementation_files=len(inputs["implementation_sha256"]),
        unchanged_historical_implementation_files=len(prior["implementation_sha256"])-1,
        real_stdio=True, model_process_intercepted=True, local_delegation_forbidden_by_frozen_scope=True))
    print(json.dumps(dict(model_calls=0, tool_count=len(actual), implementation_files=len(inputs["implementation_sha256"]), frozen_sha256=sha(HERE / "frozen.json"))))


def run():
    approval = load(HERE / "approval.json")
    assert approval["approved"] is True and approval["frozen_sha256"] == sha(HERE / "frozen.json")
    assert not RUN.exists(), "Never overwrite or retry an existing run"
    runner, prior, expected, modules, images = producer()
    frozen = load(HERE / "frozen.json")
    for name, value in frozen["execution_sha256"].items():
        assert sha(TREE / name) == value, name
    for name, value in frozen["package_sha256"].items():
        assert sha(HERE / name) == value, name
    original = runner.subscription
    calls = 0
    def invoke(run, prompt, **kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        assert prompt == expected["prompt"]
        assert load(run / "inputs.json")["implementation_sha256"] == frozen["implementation_sha256"]
        save(run / "experiment_condition.json", frozen)
        save(run / "batch_approval.json", approval)
        for name, value in frozen["execution_sha256"].items():
            target = run / "runtime_snapshot" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((TREE / name).read_bytes())
            assert sha(target) == value
        return original(run, prompt, **kwargs)
    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(args(RUN, prior, images))
    receipt, summary = load(RUN / "agent_receipt.json"), load(RUN / "summary.json")
    assert calls == 1
    assert summary["agent_response_completed"] and receipt.get("returncode") == 0
    assert not receipt.get("timed_out") and not receipt.get("routing_error")
    assert not (receipt.get("result") or {}).get("is_error"), "Stop; preserve actual failure with no retry"
    assert not list(RUN.glob("detail_*/*receipt.json")), "Unexpected local invocation: stop batch"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "run"])
    prepare() if parser.parse_args().command == "prepare" else run()
