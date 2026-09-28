"""Inspect current cold-start inputs and served plan reference without a model."""
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from scripts.tool_scripts import run_bim_agent as runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
old_batch = importlib.import_module("AI_agent.logs.experiments.2026-09-28_reconstruction_behavior.batch")


async def served(run):
    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(run)], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            catalog = await session.list_tools()
            response = await session.call_tool("get_bim_reference", {"topic": "plan_partition"})
            assert not response.isError
            payload = response.structuredContent or json.loads(response.content[0].text)
            assert payload["reference"] == runner.REFERENCES["plan_partition"]
            assert '"midpoint"' in payload["reference"]
            return dict(tool_count=len(catalog.tools), exact_plan_reference_served=True)


def main():
    class StoppedAtModelBoundary(Exception):
        pass

    def stop(*args, **kwargs):
        raise StoppedAtModelBoundary()

    with tempfile.TemporaryDirectory(prefix="bim-plan-binding-preflight-") as directory:
        run = Path(directory) / "run"
        with patch.object(runner.subprocess, "Popen", stop):
            try:
                runner.run_experiment(old_batch.arguments(run))
            except StoppedAtModelBoundary:
                pass
            else:
                raise AssertionError("The model launch must be blocked")
        request = json.loads((run / "agent_request.json").read_text())
        manifest = json.loads((run / "inputs.json").read_text())
        assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
        assert request["requested_role"] == "sonnet" and request["effort"] == "medium"
        tracked = manifest["implementation_sha256"]
        assert tracked["src/agent/geometry/profile_observation_binding.py"] == runner.digest(
            ROOT / "src/agent/geometry/profile_observation_binding.py")
        report = dict(model_calls=0, model_process_blocked=True, original_images_only=True,
            scope=old_batch.SCOPE, images=manifest["images"], implementation_sha256=tracked,
            request_sha256=runner.digest(run / "agent_request.json"),
            plan_reference_sha256=hashlib.sha256(runner.REFERENCES["plan_partition"].encode()).hexdigest(),
            **asyncio.run(served(run)))
    with (HERE / "runtime_preflight.json").open("x") as output:
        output.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(model_calls=0, implementation_files=len(tracked),
                         exact_plan_reference_served=report["exact_plan_reference_served"])))


if __name__ == "__main__":
    main()
