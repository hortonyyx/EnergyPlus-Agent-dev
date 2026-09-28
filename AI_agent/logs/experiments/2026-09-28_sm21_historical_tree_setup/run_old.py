"""Run the unmodified historical producer in its detached worktree, once."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TREE = ROOT.parent / "EnergyPlus-Agent-dev-worktrees/sm21-baseline-468d83f7"
BASE = "468d83f7626e5af630fb3f4de47d2af904d9a834"
HISTORY = HERE.parent / "2026-09-27_sm21_whole_building_repeat_claude_run58"
RUN = HERE.parent / "2026-09-28_sm21_historical_tree_run81"
load = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
save = lambda path, value: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def producer():
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TREE, text=True).strip() == BASE
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "src", "scripts"], cwd=TREE, check=True)
    sys.path.insert(0, str(TREE))
    from scripts.tool_scripts import run_bim_agent as runner
    from src.agent.execution import subscription_json
    from src.agent.geometry import plan_partition, source_bim
    modules = [runner, subscription_json, plan_partition, source_bim]
    assert all(Path(m.__file__).resolve().is_relative_to(TREE) for m in modules)
    prior = load(HISTORY / "inputs.json")
    assert all(sha(TREE / name) == value for name, value in prior["implementation_sha256"].items())
    expected = load(HISTORY / "agent_request.json")
    assert runner.GUIDE == expected["system_prompt"]
    images = TREE / "case_tests/e2e_tests/sm21_anchor/case_data"
    assert {p.name: sha(p) for p in images.glob("*.png")} == {
        name: value["sha256"] for name, value in prior["images"].items()}
    return runner, prior, expected, modules, images


def args(out, prior, images):
    return SimpleNamespace(command="run", images=images, mesh=None, building_input=None,
        out=out, scope=prior["scope"], timeout=3000, provider="claude",
        exploratory_opus=False, effort="medium", resume_candidate=None,
        resume_plan=None, plan_image=None)


async def inspect_stdio(runner, folder):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    save(folder / "inputs.json", {"images": {}})
    server = StdioServerParameters(command=sys.executable,
        args=[str(Path(runner.__file__).resolve()), "serve", str(folder)], cwd=str(TREE))
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            actual = {item.name: item.model_dump(mode="json") for item in result.tools}
    expected = load(HERE.parent / "2026-09-27_sm21_runtime_surface_setup/historical_tools.json")
    assert actual == expected and len(actual) == 36
    return actual


def prepare():
    runner, prior, expected, modules, images = producer()
    request = {}
    class Boundary(Exception):
        pass
    def stop(command, **kwargs):
        assert command[0] == "claude"
        assert command[command.index("--system-prompt") + 1] == expected["system_prompt"]
        mcp = json.loads(command[command.index("--mcp-config") + 1])["mcpServers"]["bim"]
        assert Path(mcp["args"][0]).resolve() == Path(runner.__file__).resolve()
        request.update(mcp_producer=mcp["args"][0], shell_and_repository_tools_disabled=True)
        raise Boundary()
    with tempfile.TemporaryDirectory(prefix="old-tree-preflight-") as tmp:
        folder = Path(tmp)
        (folder / "server").mkdir()
        actual_tools = asyncio.run(inspect_stdio(runner, folder / "server"))
        with patch.object(subprocess, "Popen", stop):
            try:
                runner.run_experiment(args(folder / "dry_run", prior, images))
            except Boundary:
                pass
            else:
                raise AssertionError("Expected stop before the model process")
        dry = load(folder / "dry_run/agent_request.json")
        assert dry == expected, "Historical primary request changed"
        request["request_exactly_matches_run58"] = True
    frozen = dict(producer_commit=BASE, worktree=str(TREE), mode="unmodified_historical_tree_original_only",
        scope=prior["scope"], provider="claude", role="sonnet", effort="medium", timeout_seconds=3000,
        max_candidates=6, continuation_rounds=0, primary_invocations=1,
        implementation_sha256=prior["implementation_sha256"],
        image_sha256={k: v["sha256"] for k, v in prior["images"].items()},
        guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
        request_sha256=sha(HISTORY / "agent_request.json"),
        python_version=platform.python_version(),
        claude_cli_version=subprocess.check_output(["claude", "--version"], text=True).strip(),
        imported_modules={m.__name__: m.__file__ for m in modules},
        limitations=["Provider internals and historical dependency environment cannot be frozen by Git.",
            "The old six-candidate cap and all old guidance/tools remain; this is a whole-version diagnostic, not a single-feature ablation.",
            "One repeat cannot establish stability or identify every useful change."])
    save(HERE / "frozen.json", frozen)
    save(HERE / "preflight.json", {"model_calls": 0, "real_stdio_tools_match_history": True,
        "tool_count": len(actual_tools), "tools": actual_tools, **request})
    print(json.dumps({"model_calls": 0, "source_files_match": len(prior["implementation_sha256"]),
        "tool_count": len(actual_tools), **request}))


def run():
    assert not RUN.exists(), "Never overwrite a run"
    runner, prior, expected, modules, images = producer()
    frozen = load(HERE / "frozen.json")
    assert frozen["implementation_sha256"] == prior["implementation_sha256"]
    original = runner.subscription
    calls = 0
    def invoke(run, prompt, **kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        assert prompt == expected["prompt"]
        assert load(run / "inputs.json")["implementation_sha256"] == frozen["implementation_sha256"]
        save(run / "experiment_condition.json", frozen)
        paths = set(frozen["implementation_sha256"])
        current = load(HERE.parent / "2026-09-28_sm21_threshold_current_run80/inputs.json")
        paths.update(current["implementation_sha256"])
        paths.add("src/agent/execution/subscription_json.py")
        snapshots = {}
        for name in sorted(paths):
            source = TREE / name
            if not source.is_file():
                continue
            target = run / "runtime_snapshot" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            snapshots[name] = sha(target)
        save(run / "producer_snapshot.json", snapshots)
        # No change to prompts, tools, producer methods, or MCP entry point.
        return original(run, prompt, **kwargs)
    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(args(RUN, prior, images))
    receipt, summary = load(RUN / "agent_receipt.json"), load(RUN / "summary.json")
    assert calls == 1
    assert summary["agent_response_completed"] and receipt.get("returncode") == 0
    assert not receipt.get("timed_out") and not receipt.get("routing_error")
    assert not (receipt.get("result") or {}).get("is_error"), "Stop on actual model failure; no retry"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "run"])
    command = parser.parse_args().command
    prepare() if command == "prepare" else run()
