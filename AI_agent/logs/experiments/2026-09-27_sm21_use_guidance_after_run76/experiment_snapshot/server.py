"""Experiment-only switch for use-guidance placement; all capabilities retained."""
import asyncio
from contextlib import contextmanager
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
from src.agent import roles

BASELINE = importlib.import_module(f"{__package__ or 'AI_agent.logs.experiments.' + HERE.name}.baseline_review")
CURRENT_REVIEW = roles.room_use_review
CURRENT_GUIDE = runner.GUIDE
BEFORE_GUIDE = json.loads((HERE / "baseline_guide.json").read_text())["guide"]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def baseline_feedback(source, *, include_next_action=True):
    return BASELINE.room_use_review(source)


@contextmanager
def condition(variant):
    assert variant in {"before", "after"}
    method = baseline_feedback if variant == "before" else CURRENT_REVIEW
    guide = BEFORE_GUIDE if variant == "before" else CURRENT_GUIDE
    with patch.object(roles, "room_use_review", method), patch.object(runner, "GUIDE", guide):
        yield


def serve(run, readonly=False):
    variant = json.loads((run / "experiment_condition.json").read_text())["variant"]
    original_run = FastMCP.run

    def start(server, *args, **kwargs):
        runner.dump(run / "runtime_use_guidance.json", {
            "variant": variant, "guide_sha256": sha(runner.GUIDE),
            "review_method_sha256": sha(inspect.getsource(roles.room_use_review)),
            "references_sha256": sha(json.dumps(runner.REFERENCES, sort_keys=True)),
            "tools": [t.model_dump(mode="json") for t in asyncio.run(server.list_tools())],
        })
        return original_run(server, *args, **kwargs)

    def no_nested_calls(*args, **kwargs):
        raise RuntimeError("This batch allows one primary invocation per arm and no nested model calls")

    with condition(variant), patch.object(FastMCP, "run", start), \
            patch.object(runner, "subscription", no_nested_calls):
        runner.serve(run, readonly)


if __name__ == "__main__":
    assert len(sys.argv) == 3 and sys.argv[1] == "serve"
    serve(Path(sys.argv[2]).resolve())
