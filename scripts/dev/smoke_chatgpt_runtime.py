"""Two-request subscription protocol check in our Runtime; no Codex process.

Default is offline. --live uses only an independently authorized ChatGPT plan,
checks its model catalog, and never falls back to OPENAI_API_KEY or another route.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

from src.agent_runtime.connections import resolve_connection, validate_connection_model
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.providers import CHATGPT_SUBSCRIPTION, provider_parameters
from src.agent_runtime.responses import HttpResponsesAdapter
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import InputMaterialRequirement, ReturnRequirement, RoleDefinition, ToolGrant


class Probe:
    def __init__(self):
        self.calls = 0

    async def list_tools(self):
        return [{"name": "runtime_probe", "description": "Read the value from the local runtime probe.",
                 "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}}]

    def repeatability(self, name):
        return "read_only"

    async def call_tool(self, name, arguments):
        if name != "runtime_probe" or arguments:
            raise ValueError("unexpected probe call")
        self.calls += 1
        return {"content": [{"type": "text", "text": '{"value":7,"source":"local_runtime"}'}]}

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []


async def execute(args):
    output = args.out.resolve()
    if output.exists():
        raise ValueError("use a new output directory; prior evidence is never overwritten")
    connection = resolve_connection(CHATGPT_SUBSCRIPTION, None, chatgpt_auth_dir=args.chatgpt_auth_dir)
    if args.live:
        await validate_connection_model(connection, args.model)
        adapter = connection.create_adapter()
    else:
        count = 0
        async def offline_token():
            return "offline-placeholder-not-a-credential"
        def handle(request):
            nonlocal count
            count += 1
            items = ([{"type": "function_call", "id": "fc_probe", "call_id": "call_probe",
                       "namespace": "runtime", "name": "runtime_probe", "arguments": "{}", "status": "completed"}]
                     if count == 1 else [{"type": "message", "id": "msg_final", "role": "assistant",
                         "status": "completed", "content": [{"type": "output_text", "text": '{"value":7,"source":"local_runtime"}', "annotations": []}]}])
            response = {"object": "response", "id": f"resp_{count}", "model": args.model,
                "status": "completed", "output": items,
                "usage": {"input_tokens": 40, "output_tokens": 10, "total_tokens": 50,
                          "input_tokens_details": {"cached_tokens": 0}}}
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                text="data: " + json.dumps({"type": "response.completed", "response": response}) + "\n\n")
        adapter = HttpResponsesAdapter(token_provider=offline_token, transport=httpx.MockTransport(handle))
    limits = RunLimits(model_calls=2, tool_calls=1, seconds=180, tokens=100000, max_model_retries=0,
                       max_consecutive_truncations=0, max_total_truncations=0)
    tools = Probe()
    role = RoleDefinition(role_id="coordinator", responsibilities=("verify native subscription tool protocol",),
        tool_whitelist=(ToolGrant(tool_name="runtime_probe", access="read"),),
        input_materials=(InputMaterialRequirement(name="task", media_type="text/plain"),),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="probe-result"),),
        budget=limits.ledger_limit(), read_only=True)
    parameters = provider_parameters(CHATGPT_SUBSCRIPTION, output_tokens=32000, reasoning_effort="low")
    guide = "Call runtime_probe exactly once, then return only its JSON result. Do not call other tools."
    try:
        with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
            specs = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                     "parameters": t["inputSchema"]}} for t in await tools.list_tools()]
            route = {**connection.descriptor.model_route(args.model), "verification_mode": "live_subscription" if args.live else "offline_sse_fixture"}
            versions = make_versions(store, root=ROOT, prompt=guide, tools=specs, parameters=parameters, route=route,
                                     code_paths=("scripts/dev/smoke_chatgpt_runtime.py",))
            store.write_json("versions.json", versions.model_dump(mode="json"))
            runtime = Runtime(store=store, adapter=adapter, tools=tools, role=role, model=args.model,
                parameters=parameters, versions=versions, limits=limits, context_policy=ContextPolicy(), strict_model_profile=True)
            receipt = await runtime.run([{"role": "system", "content": guide}, {"role": "user", "content": "Run the local probe now."}])
            store.write_json("receipt.json", receipt)
            try:
                answer_ok = json.loads(receipt.get("answer") or "null") == {"value": 7, "source": "local_runtime"}
            except ValueError:
                answer_ok = False
            summary = {"verification_mode": route["verification_mode"], "status": receipt["status"],
                "passed": receipt["status"] == "completed" and tools.calls == 1 and answer_ok,
                "live_model_requests": receipt["model_calls"] if args.live else 0,
                "fixture_requests": 0 if args.live else receipt["model_calls"],
                "tool_calls": tools.calls, "reported_tokens": receipt["reported_tokens"],
                "billing_mode": "subscription" if args.live else "offline", "paid_api_requests": 0,
                "fallback": receipt["fallback"], "elapsed_seconds": receipt["elapsed_seconds"]}
            store.write_json("smoke_result.json", summary)
            store.validate()
            return summary
    finally:
        await adapter.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", required=True, help="explicit slug from the account's models command")
    parser.add_argument("--chatgpt-auth-dir", type=Path)
    parser.add_argument("--live", action="store_true", help="two requests against the authorized ChatGPT plan; default is offline")
    args = parser.parse_args()
    try:
        summary = asyncio.run(execute(args))
    except (ValueError, RuntimeError) as error:
        # Auth errors are sanitized by the credential module. Never print a
        # traceback containing locals, request headers, or credential objects.
        print(json.dumps({"status": "setup_failed", "error_type": type(error).__name__, "message": str(error)}))
        raise SystemExit(1)
    print(json.dumps(summary, ensure_ascii=False))
    raise SystemExit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
