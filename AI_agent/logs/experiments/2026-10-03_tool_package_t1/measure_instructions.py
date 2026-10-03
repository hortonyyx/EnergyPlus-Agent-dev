"""Measure identical MCP-exposed descriptions and guidance at baseline and T1.

Only lists local tool definitions. Does not launch a model or invoke a tool.
"""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts import run_bim_agent as runner
from scripts.tool_scripts import bim_agent_guidance as guidance

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = "e123046d"


def baseline_module(relative, name):
    module = ModuleType(name)
    module.__file__ = str(ROOT / relative)
    sys.modules[name] = module
    content = subprocess.check_output(["git", "show", f"{BASE}:{relative}"], cwd=ROOT, text=True)
    exec(compile(content, module.__file__, "exec"), module.__dict__)
    return module


def measure(server_module, guide_module, run):
    servers = []
    with patch.object(FastMCP, "run", lambda server: servers.append(server)):
        server_module.serve(run)
    tools = asyncio.run(servers[0].list_tools())
    return dict(system_prompt_chars=len(guide_module.build_guide(images="drawings")),
        tool_count=len(tools), tool_description_chars=sum(len(tool.description or "") for tool in tools),
        references_chars={key: len(value) for key, value in guide_module.REFERENCES.items()},
        input_schema_json_chars=sum(len(json.dumps(tool.inputSchema)) for tool in tools))


def main():
    before_guide = baseline_module("scripts/tool_scripts/bim_agent_guidance.py", "t1_baseline_guidance")
    before_runner = baseline_module("scripts/tool_scripts/run_bim_agent.py", "t1_baseline_runner")
    with tempfile.TemporaryDirectory(dir=ROOT / ".tmp_t1", prefix="instructions-") as directory:
        run = Path(directory)
        runner.dump(run / "inputs.json", dict(images={}, scope="local tool catalog only"))
        before = measure(before_runner, before_guide, run)
        after = measure(runner, guidance, run)
    recorded = json.loads((HERE / "instruction_volume_before.json").read_text())
    for key in ("system_prompt_chars", "tool_count", "tool_description_chars", "references_chars"):
        assert before[key] == recorded[key], (key, before[key], recorded[key])
    delta = {key: after[key] - before[key] for key in ("system_prompt_chars", "tool_count", "tool_description_chars", "input_schema_json_chars")}
    delta["references_chars"] = {key: after["references_chars"][key] - value for key, value in before["references_chars"].items()}
    result = dict(baseline_commit=BASE, before=before, after=after, delta=delta, model_calls=0,
        method="Unicode character counts for system prompt and MCP tool descriptions; schemas counted as json.dumps(inputSchema), including all schema fields. References are loaded on demand, not part of the default system prompt.",
        legacy_field_note="instruction_volume_before.tool_schema_description_chars was a schema JSON length, not a sum of descriptions; use input_schema_json_chars for the explicit comparison.")
    runner.dump(HERE / "instruction_volume_final.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
