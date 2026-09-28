"""Offline preparation by arm; run only the separately user-approved two-call pilot."""
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
ROOT = HERE.parents[3]
RUNS = {"B": "2026-09-28_sm21_dimension_first_run84", "A": "2026-09-28_sm21_method_control_run85"}
SCOPE = json.loads((HERE.parent / "2026-09-28_reconstruction_behavior/proposed_batch.json").read_text())["conditions"]["scope"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--arm", choices=["A", "B"], required=True)
    args = parser.parse_args()
    runtime = ROOT if args.arm == "A" else ROOT / ".worktrees/dimension-first-20260928"
    sys.path.insert(0, str(runtime))
    os.environ["PYTHONPATH"] = str(runtime)
    from scripts.tool_scripts import run_bim_agent as runner
    assert Path(runner.__file__).resolve().is_relative_to(runtime.resolve())

    def arguments(run):
        return SimpleNamespace(command="run", images=ROOT / "case_tests/e2e_tests/sm21_anchor/case_data",
            mesh=None, building_input=None, out=run, scope=SCOPE, timeout=3000,
            provider="claude", exploratory_opus=False, effort="medium", max_candidates=24,
            continuation_rounds=0, resume_candidate=None, resume_plan=None, plan_image=None)

    def conditions():
        previous = json.loads((HERE.parent / "2026-09-28_plan_measurement_binding/runtime_preflight.json").read_text())
        return dict(scope=SCOPE, images=previous["images"],
            implementation_sha256={name: runner.digest(runtime / name) for name in previous["implementation_sha256"]},
            references_sha256={name: hashlib.sha256(value.encode()).hexdigest() for name, value in runner.REFERENCES.items()},
            guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
            batch_script_sha256=runner.digest(Path(__file__)), provider="claude", role="sonnet",
            effort="medium", timeout_seconds=3000, max_candidates=24, continuation_rounds=0)

    async def reference_check(run):
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client
        params = StdioServerParameters(command=sys.executable,
            args=[str(runtime / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(run)], cwd=str(runtime))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                catalog = await session.list_tools()
                result = await session.call_tool("get_bim_reference", {"topic": "reconstruction"})
                assert not result.isError
                payload = result.structuredContent or json.loads(result.content[0].text)
                assert payload["reference"] == runner.REFERENCES["reconstruction"]
                return dict(tool_names=sorted(tool.name for tool in catalog.tools), exact_reference_served=True)

    def completed(run):
        summary = json.loads((run / "summary.json").read_text())
        receipt = json.loads((run / "agent_receipt.json").read_text())
        assert summary.get("agent_response_completed") is True
        assert receipt.get("returncode") == 0 and not receipt.get("result", {}).get("is_error")

    if args.action == "prepare":
        class StoppedAtModelBoundary(Exception):
            pass

        def stop(*args, **kwargs):
            raise StoppedAtModelBoundary()

        with tempfile.TemporaryDirectory(prefix="bim-method-comparison-") as directory:
            run = Path(directory) / "run"
            with patch.object(runner.subprocess, "Popen", stop):
                try:
                    runner.run_experiment(arguments(run))
                except StoppedAtModelBoundary:
                    pass
                else:
                    raise AssertionError("The model launch must be blocked")
            manifest = json.loads((run / "inputs.json").read_text())
            request = json.loads((run / "agent_request.json").read_text())
            frozen = conditions()
            assert manifest["images"] == frozen["images"]
            assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
            assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
            assert request["requested_role"] == "sonnet" and request["effort"] == "medium"
            assert request["system_prompt"] == runner.GUIDE
            served = asyncio.run(reference_check(run))
        runner.dump(HERE / f"preflight_{args.arm}.json", dict(arm=args.arm, run=RUNS[args.arm],
            status="prepared_pending_user_decision", conditions=frozen, model_calls=0,
            model_process_blocked=True, original_images_only=True, **served))
        (HERE / f"method_{args.arm.lower()}_served.txt").write_text(runner.REFERENCES["reconstruction"])
        print(json.dumps(dict(arm=args.arm, model_calls=0, exact_reference_served=True)))
        return

    proposed = json.loads((HERE / "proposed_batch.json").read_text())
    assert proposed["arms"][args.arm]["conditions"] == conditions(), "Prepared runtime changed"
    if args.arm == "A":
        completed(HERE.parent / RUNS["B"])
    run = HERE.parent / RUNS[args.arm]
    assert not run.exists(), "Do not overwrite or retry an experiment"
    original = runner.subscription
    calls = 0

    def invoke(path, *call_args, **kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = json.loads((path / "inputs.json").read_text())
        assert manifest["implementation_sha256"] == conditions()["implementation_sha256"]
        assert manifest["images"] == conditions()["images"]
        runner.dump(path / "experiment_condition.json", dict(arm=args.arm, **conditions()))
        for name in manifest["implementation_sha256"]:
            destination = path / "runtime_snapshot" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((runtime / name).read_bytes())
        return original(path, *call_args, **kwargs)

    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(run))
    assert calls == 1
    completed(run)


if __name__ == "__main__":
    main()
