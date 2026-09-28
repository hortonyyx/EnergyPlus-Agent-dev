"""Prepare offline, then execute only the explicitly approved single cold run."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from scripts.tool_scripts import run_bim_agent as runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-28_sm21_evidence_feedback_run86"
SCOPE = json.loads((HERE.parent / "2026-09-28_dimension_first_comparison/proposed_batch.json").read_text())["arms"]["A"]["conditions"]["scope"]


def arguments(run):
    return SimpleNamespace(command="run", images=ROOT / "case_tests/e2e_tests/sm21_anchor/case_data",
        mesh=None, building_input=None, out=run, scope=SCOPE, timeout=3000,
        provider="claude", exploratory_opus=False, effort="medium", max_candidates=24,
        continuation_rounds=0, resume_candidate=None, resume_plan=None, plan_image=None)


def sha_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


async def references(run):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(run)], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            catalog = await session.list_tools()
            for topic in ("reconstruction", "plan_partition", "opening_review"):
                result = await session.call_tool("get_bim_reference", dict(topic=topic))
                assert not result.isError
                payload = result.structuredContent or json.loads(result.content[0].text)
                assert payload["reference"] == runner.REFERENCES[topic]
            return dict(tool_names=sorted(t.name for t in catalog.tools), exact_reference_served=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    args = parser.parse_args()
    assert Path(runner.__file__).resolve().is_relative_to(ROOT)
    if args.action == "prepare":
        class ModelBoundary(Exception):
            pass
        def stop(*args, **kwargs):
            raise ModelBoundary()
        with tempfile.TemporaryDirectory(prefix="bim-evidence-preflight-") as folder:
            run = Path(folder) / "run"
            with patch.object(runner.subprocess, "Popen", stop):
                try:
                    runner.run_experiment(arguments(run))
                except ModelBoundary:
                    pass
                else:
                    raise AssertionError("model process was not blocked")
            manifest = json.loads((run / "inputs.json").read_text())
            request = json.loads((run / "agent_request.json").read_text())
            assert request["requested_role"] == "sonnet" and request["effort"] == "medium"
            assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
            assert "src/agent/geometry/plan_feedback.py" in manifest["implementation_sha256"]
            served = asyncio.run(references(run))
        frozen = dict(scope=SCOPE, images=manifest["images"], implementation_sha256=manifest["implementation_sha256"],
            guide_sha256=sha_text(runner.GUIDE), references_sha256={k:sha_text(v) for k,v in runner.REFERENCES.items()},
            batch_script_sha256=runner.digest(Path(__file__)), provider="claude", role="sonnet", effort="medium",
            timeout_seconds=3000, max_candidates=24, continuation_rounds=0, max_calls=1,
            local_model_calls=0, run=RUN.name)
        runner.dump(HERE / "frozen.json", frozen)
        runner.dump(HERE / "preflight.json", dict(status="prepared_pending_user_decision", model_calls=0,
            model_process_blocked=True, original_images_only=True, production_files=len(frozen["implementation_sha256"]), **served))
        print(json.dumps(dict(model_calls=0, status="prepared_pending_user_decision", production_files=len(frozen["implementation_sha256"]))))
        return

    frozen = json.loads((HERE / "frozen.json").read_text())
    approval = json.loads((HERE / "approval.json").read_text())
    assert approval["approved"] is True and approval["frozen_sha256"] == runner.digest(HERE / "frozen.json")
    assert frozen["batch_script_sha256"] == runner.digest(Path(__file__))
    assert frozen["implementation_sha256"] == {name:runner.digest(ROOT / name) for name in frozen["implementation_sha256"]}
    assert frozen["references_sha256"] == {k:sha_text(v) for k,v in runner.REFERENCES.items()}
    assert frozen["guide_sha256"] == sha_text(runner.GUIDE)
    assert not RUN.exists(), "Never overwrite or retry a run"
    original = runner.subscription
    calls = 0
    def invoke(path, *call_args, **kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = json.loads((path / "inputs.json").read_text())
        assert manifest["images"] == frozen["images"] and manifest["implementation_sha256"] == frozen["implementation_sha256"]
        runner.dump(path / "experiment_condition.json", frozen)
        for name in frozen["implementation_sha256"]:
            dest = path / "runtime_snapshot" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / name).read_bytes())
        return original(path, *call_args, **kwargs)
    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(RUN))
    assert calls == 1
    receipt = json.loads((RUN / "agent_receipt.json").read_text())
    summary = json.loads((RUN / "summary.json").read_text())
    completed = (receipt.get("returncode") == 0 and not receipt.get("result", {}).get("is_error")
                 and summary.get("agent_response_completed") is True)
    runner.dump(HERE / "execution_receipt.json", dict(completed=completed, calls=calls,
        receipt_file=str((RUN / "agent_receipt.json").relative_to(ROOT)), retry=False))
    print(json.dumps(dict(completed=completed, calls=calls, retry=False)))


if __name__ == "__main__":
    main()
