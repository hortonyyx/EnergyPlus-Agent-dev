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
from src.agent_runtime.anthropic import HttpAnthropicAdapter
from src.agent_runtime.providers import GLM_SUBSCRIPTION_ANTHROPIC, provider_parameters
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts, VersionManifest
from scripts.tool_scripts.bim_agent_guidance import filter_tool_catalog, tool_capabilities


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


def protocol_report(wire, runtime_run, directory):
    from src.agent_runtime.adapter import prepare_request
    capture_path = HERE.parent / "2026-10-03_migration_comparison/evidence/claude_code_request_capture/request_02.json"
    captured = json.loads(capture_path.read_bytes())["body"]
    parameters = provider_parameters(GLM_SUBSCRIPTION_ANTHROPIC, output_tokens=32000, reasoning_effort="medium")
    versions = VersionManifest.model_validate_json((runtime_run / "versions.json").read_bytes())
    versions = versions.model_copy(update={"remote_model": versions.remote_model.model_copy(
        update={"route_id": GLM_SUBSCRIPTION_ANTHROPIC, "remote_alias": "glm-5.3-flash"})})
    with EventStore(directory / "native-protocol", run_id="parity", task_id="parity",
                    budget_limit=BudgetAmounts(calls=0)) as store:
        prepared = prepare_request(store=store, model="glm-5.3-flash", messages=wire["messages"],
            message_sources=[store.source(f"logical-message-{i}", m) for i, m in enumerate(wire["messages"])],
            tools=wire["tools"], tool_source=store.source("tools", wire["tools"]),
            parameters=parameters, versions=versions)
        native = prepared.body
        assert store.capture_bytes(prepared.event_payload.final_request_body) == prepared.wire_bytes
    return {
        "capture": str(capture_path.relative_to(ROOT)), "capture_sha256": digest(capture_path.read_bytes()),
        "settings": compare(canonical({k: captured[k] for k in parameters}), canonical(parameters)),
        "system_text": compare(wire["messages"][0]["content"].encode(), native["system"][0]["text"].encode()),
        "tool_payloads": compare(canonical([t["function"] for t in wire["tools"]]), canonical([
            {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]} for t in native["tools"]])),
        "native_request_sha256": digest(prepared.wire_bytes),
        "cache_positions": {"system_last_two_substantive_blocks": [i for i, b in enumerate(native["system"]) if b.get("cache_control")],
            "latest_message_last_block": native["messages"][-1]["content"][-1]["cache_control"]},
        "protocol": "Anthropic Messages; logical tool results become native tool_result blocks",
        "thinking": native["thinking"], "output_config": native["output_config"],
        "max_tokens": native["max_tokens"], "context_management": native["context_management"],
        "differences": ["stream=false (CLI capture true)", "one shared Agent guide, no CLI-private system wrappers or client tools",
            "bare tool names (CLI mcp__bim__ prefix)", "MCP images follow tool_result blocks in the same user turn",
            "own client identity; no CLI session/device metadata", "shared deterministic token-threshold compaction still applies"],
        "model_requests": 0,
    }


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
    async with frozen_bim_client(old_run, repository_root=ROOT, enabled_only=True) as client:
        old_catalog = await client.list_tools()
    async with frozen_bim_client(old_run, repository_root=ROOT) as client:
        old_complete_catalog = await client.list_tools()

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
    # Derive the runtime task independently from the archived baseline, not
    # from the Claude request just prepared. A changed task template must fail
    # the comparison instead of silently feeding itself to both sides.
    reference_name = ("2026-09-30_sm21_instruction_fix_glm_trial01" if case == "sm21"
                      else f"2026-10-02_{case}_glm_baseline")
    reference_path = HERE.parent / reference_name / "agent_request.json"
    reference_raw = reference_path.read_bytes()
    runtime_task = json.loads(reference_raw)["prompt"].replace(
        "Budget: 3000 seconds", f"Budget: {timeout} seconds")
    argv = ["--out", str(new_run), "--images", str(old_args.images), "--provider", "scripted",
        "--script", str(script), "--scope", runtime_task, "--seconds", str(timeout),
        "--max-candidates", "24", "--model-calls", "1", "--tokens", "1000000"]
    for name in old_args.floor_plan_images:
        argv += ["--floor-plan-image", name]
    with patch.object(runtime_entry, "ScriptedAdapter", CaptureAdapter), patch.object(HttpChatAdapter, "send", forbid_live), patch.object(HttpAnthropicAdapter, "send", forbid_live):
        receipt = await runtime_entry.execute(runtime_entry.parser().parse_args(argv))
    assert receipt["status"] == "completed" and len(captures) == 1
    wire = captures[0]
    new_manifest = json.loads((new_run / "bim/inputs.json").read_bytes())
    system = [message["content"] for message in wire["messages"] if message["role"] == "system"]
    assert len(system) == 1
    task = next(message["content"] for message in wire["messages"] if message["role"] == "user")
    new_complete_catalog = json.loads((new_run / "frozen/coordinator_tools.json").read_bytes())["tools"]
    assert tool_capabilities(old_manifest) == tool_capabilities(new_manifest)
    new_catalog = filter_tool_catalog(new_complete_catalog, **tool_capabilities(new_manifest))
    # Compare exactly the name, description and input schema. The wire protocol
    # wraps those bytes differently; record that distinction explicitly.
    old_wire_tools = [{"type": "function", "function": {"name": t["name"],
        "description": t.get("description", ""), "parameters": t["inputSchema"]}} for t in old_catalog]
    row = {"case": case, "model_requests": 0, "model_processes_started": 0,
        "claude_model_launches_blocked": len(attempts),
        "agent_version": receipt["agent_version"],
        "system_guidance": compare(old["system_prompt"].encode(), system[0].encode()),
        "tool_catalog": compare(canonical(old_catalog), canonical(new_catalog)),
        "complete_registered_catalog": compare(canonical(old_complete_catalog), canonical(new_complete_catalog)),
        "capabilities": tool_capabilities(new_manifest),
        "tool_names_descriptions_parameters": compare(canonical(old_wire_tools), canonical(wire["tools"])),
        "task_body": compare(old["prompt"].encode(), task.encode()),
        "runtime_task_source": {"path": str(reference_path.relative_to(ROOT)),
            "sha256": digest(reference_raw), "change": f"Budget: 3000 seconds -> Budget: {timeout} seconds"},
        "tool_count": len(old_catalog),
        "protocol_and_thinking": protocol_report(wire, new_run, directory),
        "image_sha256": {name: value["sha256"] for name, value in old_manifest["images"].items()},
        "floor_plan_images": new_manifest["floor_plan_images"],
        "time_budget_seconds": timeout, "max_candidates": 24,
        "additional_runtime_messages": [message for message in wire["messages"]
            if message not in [{"role": "system", "content": system[0]}, {"role": "user", "content": task}]],
        "differences": [
            {"item": "protocol", "reason": "Claude Code uses Anthropic/MCP namespaces (mcp__bim__*); runtime uses OpenAI function wrappers with bare names. The exact shared MCP catalog and wrapped name/description/schema bytes are checked above."},
            {"item": "runtime_state", "reason": "Runtime adds its existing machine-generated current-state user message, retaining the original task and its provenance; it adds no second clock or contradictory time instruction. Full additional messages are retained here."},
            {"item": "service_parameters", "reason": "The preserved OpenAI subscription route uses reasoning_effort=medium without adaptive thinking. The new Anthropic subscription route matches the captured adaptive/medium/32000/keep-all settings; see protocol_and_thinking. This check starts no live model."},
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
