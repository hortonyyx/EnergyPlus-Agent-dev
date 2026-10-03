"""Measure model-facing instructions offline; print JSON unless --output is given.

Only lists local tool definitions. Does not launch a model or invoke a tool.
"""
import argparse
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
COMMON_REFERENCES = ("plan_partition", "claims")


def baseline_module(relative, name, commit):
    module = ModuleType(name)
    module.__file__ = str(ROOT / relative)
    sys.modules[name] = module
    content = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=ROOT, text=True)
    exec(compile(content, module.__file__, "exec"), module.__dict__)
    return module


def measure(server_module, guide_module, run):
    servers = []
    with patch.object(FastMCP, "run", lambda server: servers.append(server)):
        server_module.serve(run)
    tools = asyncio.run(servers[0].list_tools())
    result = dict(system_prompt_chars=len(guide_module.build_guide(images="drawings")),
        tool_count=len(tools), tool_description_chars=sum(len(tool.description or "") for tool in tools),
        references_chars={key: len(value) for key, value in guide_module.REFERENCES.items()},
        input_schema_json_chars=sum(len(json.dumps(tool.inputSchema)) for tool in tools))
    result["common_reference_chars"] = sum(result["references_chars"][key] for key in COMMON_REFERENCES)
    result["instruction_total_chars"] = sum(result[key] for key in (
        "system_prompt_chars", "tool_description_chars", "input_schema_json_chars", "common_reference_chars"))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", help="Optional Git revision for a same-metric comparison")
    parser.add_argument("--output", type=Path, help="Explicit report destination; omitted means stdout only")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(dir=ROOT, prefix=".instructions-") as directory:
        run = Path(directory)
        runner.dump(run / "inputs.json", dict(images={}, scope="local tool catalog only"))
        after = measure(runner, guidance, run)
        result = dict(after=after, model_calls=0, common_reference_topics=COMMON_REFERENCES,
            method="Unicode characters; full registered catalog descriptions; schemas as json.dumps(inputSchema); common references plan_partition + claims. instruction_total_chars sums these four terms. References are loaded on demand.")
        if args.baseline:
            before_guide = baseline_module("scripts/tool_scripts/bim_agent_guidance.py", "instruction_baseline_guidance", args.baseline)
            before_runner = baseline_module("scripts/tool_scripts/run_bim_agent.py", "instruction_baseline_runner", args.baseline)
            before = measure(before_runner, before_guide, run)
            result.update(baseline_commit=args.baseline, before=before,
                delta={key: after[key] - before[key] for key in after if key != "references_chars"})
        capabilities = guidance.tool_capabilities({})
        # Show actual default request volume as well as the conservative full
        # catalog metric used to detect instruction growth across versions.
        servers = []
        with patch.object(FastMCP, "run", lambda server: servers.append(server)):
            runner.serve(run, enabled_only=True)
        enabled = asyncio.run(servers[0].list_tools())
        result["default_enabled_catalog"] = dict(capabilities=capabilities, tool_count=len(enabled),
            tool_description_chars=sum(len(tool.description or "") for tool in enabled),
            input_schema_json_chars=sum(len(json.dumps(tool.inputSchema)) for tool in enabled))
        result["default_enabled_catalog"]["instruction_total_chars"] = (
            after["system_prompt_chars"] + after["common_reference_chars"]
            + result["default_enabled_catalog"]["tool_description_chars"]
            + result["default_enabled_catalog"]["input_schema_json_chars"])
        full_guide_chars = len(guidance.build_guide(images="drawings", review_detail=True, continuation=True))
        result["all_capabilities_enabled"] = dict(system_prompt_chars=full_guide_chars,
            instruction_total_chars=after["instruction_total_chars"] - after["system_prompt_chars"] + full_guide_chars)
    if args.output is not None:
        runner.dump(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
