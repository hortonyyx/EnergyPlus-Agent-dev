"""Compare prepared Claude Code and runtime requests; never start a model.

Claude Code is stopped at subprocess.Popen. The new runtime uses an in-memory
scripted adapter through its ordinary entrypoint. Only local MCP servers run.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from src.agent import runtime_entry
from src.agent.runtime_tools import frozen_bim_client
from src.agent_runtime.adapter import HttpChatAdapter, ScriptedAdapter
from src.agent_runtime.agent_registry import agent_version_record


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
T1 = importlib.import_module("AI_agent.logs.experiments.2026-10-03_tool_package_t1.glm_tests")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def compare(left, right):
    assert left == right, "prepared Agent content differs"
    return {"identical_bytes": True, "bytes": len(left), "claude_sha256": digest(left),
            "runtime_sha256": digest(right)}


async def case_report(case, directory, timeout):
    class ModelBoundary(Exception):
        pass

    attempts = []
    def stop(command, **kwargs):
        assert command[0] == str(ROOT / "scripts/glm_code.sh")
        attempts.append(command[0])
        raise ModelBoundary()

    old_run = directory / "claude"
    old_args = T1.arguments(case, old_run, timeout)
    with patch.object(T1.runner.subprocess, "Popen", stop), patch.object(tempfile, "tempdir", str(directory)):
        try:
            T1.runner.run_experiment(old_args)
        except ModelBoundary:
            pass
        else:
            raise AssertionError("Claude Code did not reach the guarded model-process boundary")
    assert len(attempts) == 1
    old = json.loads((old_run / "agent_request.json").read_bytes())
    old_manifest = json.loads((old_run / "inputs.json").read_bytes())
    async with frozen_bim_client(old_run, repository_root=ROOT) as client:
        old_catalog = await client.list_tools()

    captures = []
    class CaptureAdapter(ScriptedAdapter):
        async def send(self, request, *, timeout):
            captures.append(json.loads(request.wire_bytes))
            return await super().send(request, timeout=timeout)

    async def forbid_live(*args, **kwargs):
        raise AssertionError("R3 forbids every live model request")

    script = directory / "responses.json"
    script.write_text(json.dumps([{"choices": [{"message": {"role": "assistant", "content": "Offline preparation only."},
        "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}}]))
    new_run = directory / "runtime"
    argv = ["--out", str(new_run), "--images", str(old_args.images), "--provider", "scripted",
        "--script", str(script), "--scope", old["prompt"], "--seconds", str(timeout),
        "--max-candidates", "24", "--model-calls", "1", "--tokens", "1000000"]
    for name in old_args.floor_plan_images:
        argv += ["--floor-plan-image", name]
    with patch.object(runtime_entry, "ScriptedAdapter", CaptureAdapter), patch.object(HttpChatAdapter, "send", forbid_live):
        receipt = await runtime_entry.execute(runtime_entry.parser().parse_args(argv))
    assert receipt["status"] == "completed" and len(captures) == 1
    wire = captures[0]
    new_manifest = json.loads((new_run / "bim/inputs.json").read_bytes())
    system = [message["content"] for message in wire["messages"] if message["role"] == "system"]
    assert len(system) == 1
    task = next(message["content"] for message in wire["messages"] if message["role"] == "user")
    new_catalog = json.loads((new_run / "frozen/coordinator_tools.json").read_bytes())["tools"]
    # Compare exactly the name, description and input schema. The wire protocol
    # wraps those bytes differently; record that distinction explicitly.
    old_wire_tools = [{"type": "function", "function": {"name": t["name"],
        "description": t.get("description", ""), "parameters": t["inputSchema"]}} for t in old_catalog]
    row = {"case": case, "model_requests": 0, "model_processes_started": 0,
        "claude_model_launches_blocked": len(attempts),
        "agent_version": receipt["agent_version"],
        "system_guidance": compare(old["system_prompt"].encode(), system[0].encode()),
        "tool_catalog": compare(canonical(old_catalog), canonical(new_catalog)),
        "tool_names_descriptions_parameters": compare(canonical(old_wire_tools), canonical(wire["tools"])),
        "task_body": compare(old["prompt"].encode(), task.encode()),
        "tool_count": len(old_catalog),
        "image_sha256": {name: value["sha256"] for name, value in old_manifest["images"].items()},
        "floor_plan_images": new_manifest["floor_plan_images"],
        "time_budget_seconds": timeout, "max_candidates": 24,
        "additional_runtime_messages": [message for message in wire["messages"]
            if message not in [{"role": "system", "content": system[0]}, {"role": "user", "content": task}]],
        "differences": [
            {"item": "protocol", "reason": "Claude Code uses Anthropic/MCP namespaces (mcp__bim__*); runtime uses OpenAI function wrappers with bare names. The exact shared MCP catalog and wrapped name/description/schema bytes are checked above."},
            {"item": "runtime_state", "reason": "Runtime adds its existing machine-generated current-state user message, retaining the original task and its provenance; it adds no second clock or contradictory time instruction. Full additional messages are retained here."},
            {"item": "service_parameters", "reason": "Claude Code effort=medium has an uncaptured service mapping. Live subscription runtime omits unverified thinking parameters and uses max_tokens=32000; this offline capture uses scripted-model and is not a live protocol-equivalence test."},
            {"item": "run_metadata", "reason": "Output paths, timestamps, provider and input_mode are runner-specific. Started/deadline epochs differ between sequential preparations; each runner uses the same configured duration and floor scope."},
        ],
        "boundary": "Prepared model boundary only. Claude Code private HTTP context is not captured; no claim of hidden client or service parameter equality."}
    assert old["agent_version"] == row["agent_version"]
    assert row["image_sha256"] == {name: value["sha256"] for name, value in new_manifest["images"].items()}
    assert new_manifest["floor_plan_images"] == old_manifest["floor_plan_images"]
    assert new_manifest["deadline_epoch"] - new_manifest["started_epoch"] == timeout
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "runner_parity.json")
    parser.add_argument("--timeout", type=int, default=6000)
    args = parser.parse_args()
    rows = []
    with tempfile.TemporaryDirectory(prefix=".r3-parity-", dir=ROOT) as temporary:
        for case in ("sm24", "sm25", "sm21"):
            folder = Path(temporary) / case
            folder.mkdir()
            rows.append(asyncio.run(case_report(case, folder, args.timeout)))
    report = {"agent_version": agent_version_record(ROOT)["version_id"],
        "model_requests": 0, "model_processes_started": 0, "cases": rows}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": [row["case"] for row in rows], "all_identical": True,
        "model_requests": 0, "report": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
