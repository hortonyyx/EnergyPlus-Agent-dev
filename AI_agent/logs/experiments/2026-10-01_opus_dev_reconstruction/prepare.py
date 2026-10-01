"""Prepare the developer's own sm21/sm24/sm25 reconstructions (no model is called).

User 10-01: "先还是继续把sm24跑了，然后你来做三个案例，做完之后明早一起汇总给我".
Same runtime as the fix-package regressions (branch dev/opus-guidance-recovery-20260929 at
59f0e9dc), same original images, task text and MCP tool server. The developer (Opus 5.5 in
the Claude Code session) calls the tools through scripts/tool_scripts/bim_agent_bridge.py,
which saves every request, reply and returned image under the run. No deadline is set:
these are development reconstructions, not timed experiments; wall time is still logged.
"""
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
batch = importlib.import_module("AI_agent.logs.experiments.2026-09-30_instruction_fix.batch")
runner = batch.runner
assert Path(runner.__file__).resolve().is_relative_to(ROOT.resolve()), runner.__file__


class StoppedAtModelBoundary(Exception):
    pass


def stop(*args, **kwargs):
    raise StoppedAtModelBoundary()


def prepare(case):
    run = HERE.parent / f"2026-10-01_opus_dev_{case}"
    assert not run.exists(), "never overwrite a developer run"
    arguments = batch.arguments(case, run)
    arguments.max_candidates = 40
    with patch.object(runner.subprocess, "Popen", stop):
        try:
            runner.run_experiment(arguments)
        except StoppedAtModelBoundary:
            pass
        else:
            raise AssertionError("the work-model launch must be blocked")
    manifest = json.loads((run / "inputs.json").read_text())
    manifest.pop("deadline_epoch", None)
    manifest.update(provider="external_development_agent", development_model="claude-opus-5-5",
                    effort="max", execution_channel="Claude Code session via bim_agent_bridge; same MCP tools")
    (run / "inputs.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    request = json.loads((run / "agent_request.json").read_text())
    (run / "task.txt").write_text(request["prompt"])
    (run / "guide.txt").write_text(request["system_prompt"])
    return dict(case=case, run=run.name, images=sorted(manifest["images"]), max_candidates=40,
                files=sorted(p.name for p in run.iterdir()))


if __name__ == "__main__":
    print(json.dumps([prepare(case) for case in ("sm21", "sm24", "sm25")], ensure_ascii=False, indent=1))
