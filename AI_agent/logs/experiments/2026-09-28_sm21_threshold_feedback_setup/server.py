"""Experiment-only MCP entry: one legacy/current view_pixel_profile threshold feedback switch."""
import asyncio
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts import run_bim_agent as runner

LEGACY = importlib.import_module(f"{__package__ or 'AI_agent.logs.experiments.' + HERE.name}.legacy_view_profile")


def method_hash(method):
    return hashlib.sha256(inspect.getsource(method).encode()).hexdigest()


def serve(run, readonly=False):
    condition = json.loads((run / "experiment_condition.json").read_text())
    variant = condition["variant"]
    assert variant in {"legacy", "current"}
    method = LEGACY.view_profile if variant == "legacy" else runner.Toolkit.view_profile
    original_run = FastMCP.run

    def start(server, *args, **kwargs):
        # Save the actual exposed catalog and active method before stdio starts.
        runner.dump(run / ("runtime_threshold_readonly.json" if readonly else "runtime_threshold.json"), {
            "variant": variant, "method_sha256": method_hash(method),
            "tools": [t.model_dump(mode="json") for t in asyncio.run(server.list_tools())],
            "guide_sha256": hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
            "references_sha256": hashlib.sha256(json.dumps(runner.REFERENCES, sort_keys=True).encode()).hexdigest(),
        })
        return original_run(server, *args, **kwargs)

    def no_nested_calls(*args, **kwargs):
        raise RuntimeError("This experiment permits the primary invocation only; nested model calls are disabled")

    with patch.object(runner.Toolkit, "view_profile", method), patch.object(FastMCP, "run", start), \
            patch.object(runner, "subscription", no_nested_calls):
        runner.serve(run, readonly)


if __name__ == "__main__":
    assert len(sys.argv) in {3, 4} and sys.argv[1] == "serve"
    assert len(sys.argv) == 3 or sys.argv[3] == "--readonly"
    serve(Path(sys.argv[2]).resolve(), readonly="--readonly" in sys.argv)
