"""C1's authorized tiny GLM Coding Plan probe, capped at four real sends.

One local synthetic 503 is injected after the first real response. That failure
never reaches the service; the subsequent request confirms the retry path and
new tool-message representation are accepted by the actual endpoint.
"""

import argparse
import asyncio
import json
from pathlib import Path

import httpx

from src.agent_runtime.adapter import HttpChatAdapter
from src.agent_runtime.call_quota import QuotaAdapter
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.failures import http_failure
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.providers import subscription_credentials, provider_parameters
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import InputMaterialRequirement, ReturnRequirement, RoleDefinition, ToolGrant

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


class ProbeTools:
    def __init__(self):
        self.calls = []

    async def list_tools(self):
        return [{"name": "report_color", "description": "Record the requested color; returns color and count.",
            "inputSchema": {"type": "object", "properties": {"color": {"type": "string", "enum": ["blue"]}},
                "required": ["color"], "additionalProperties": False}}]

    def repeatability(self, name):
        return "read_only"

    async def call_tool(self, name, arguments):
        self.calls.append({"name": name, "arguments": arguments})
        result = {"color": arguments["color"], "count": 2}
        return {"isError": False, "content": [{"type": "text", "text":
            json.dumps(result, separators=(",", ":")) + "\nTime remaining: enough for a short answer."}],
            "structuredContent": {**result, "acknowledgement": "ACK:blue:2"}}

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []


async def run(credentials):
    base_url, key = subscription_credentials(credentials)
    limits = RunLimits(model_calls=4, tool_calls=1, seconds=180, tokens=100000,
        max_total_truncations=0, max_consecutive_truncations=0)
    tools = ProbeTools()
    role = RoleDefinition(role_id="c1_protocol_probe", responsibilities=("Check protocol acceptance only",),
        tool_whitelist=(ToolGrant(tool_name="report_color", access="read"),),
        input_materials=(InputMaterialRequirement(name="task", media_type="text/plain"),),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="text"),),
        budget=limits.ledger_limit(), read_only=True)
    directory = HERE / "subscription_probe"
    if directory.exists() or (HERE / "subscription_probe.json").exists():
        raise ValueError("existing probe must be inspected, never overwritten or automatically rerun")
    live = HttpChatAdapter(base_url=base_url, api_key=key)
    guarded = QuotaAdapter(live, HERE / "subscription_quota.jsonl", limit=4, category="c1-glm-subscription")

    class OneLocalFailure:
        calls = 0
        async def send(self, request, *, timeout):
            self.calls += 1
            if self.calls == 2:
                raise http_failure(httpx.Response(503, headers={"x-request-id": "local-c1-fault-injection"},
                    json={"error": {"type": "temporary_server_error", "message": "Synthetic offline failure, no service call."},
                          "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}), secret="")
            return await guarded.send(request, timeout=timeout)

    system = "Protocol test: call report_color exactly once with color blue, then reply only the acknowledgement from the tool result."
    parameters = provider_parameters("glm-subscription", output_tokens=2048, reasoning_effort="medium")
    try:
        with EventStore(directory, run_id="c1-subscription-probe", task_id="protocol", budget_limit=limits.ledger_limit()) as store:
            catalog = await tools.list_tools()
            versions = make_versions(store, root=ROOT, prompt=system, tools=catalog, parameters=parameters,
                route={"route_id": "glm-subscription", "model": "glm-5.3-flash", "base_url": base_url, "billing_mode": "subscription"})
            engine = Runtime(store=store, adapter=OneLocalFailure(), tools=tools, role=role,
                model="glm-5.3-flash", parameters=parameters, versions=versions, limits=limits,
                context_policy=ContextPolicy(), strict_model_profile=True,
                low_output_limit_reason="Authorized C1 tiny tool-message/retry probe; no building generation.")
            receipt = await engine.run([{"role": "system", "content": system},
                {"role": "user", "content": "Run the short protocol test now."}])
            quota = [json.loads(line) for line in (HERE / "subscription_quota.jsonl").read_text().splitlines()]
            attempts = sum(row["event"] == "attempt" for row in quota)
            usages = [row["usage"] for row in quota if row["event"] == "response"]
            requests = [store.resolve(e.payload.final_request_body) for e in store.events if e.payload.event_type == "adapter_request"]
            summary = {"status": receipt["status"], "answer": receipt["answer"], "tool_calls": tools.calls,
                "real_subscription_requests": attempts, "paratera_requests": 0, "deepseek_requests": 0,
                "synthetic_local_503_count": int(len(requests) >= 2),
                "retry_body_identical": len(requests) >= 3 and requests[1] == requests[2],
                "service_usage": usages, "service_total_tokens": sum(u.get("total_tokens", 0) for u in usages),
                "boundary": "The injected 503 is local. Only quota-journal sends reached GLM Coding Plan; no whole-case test."}
            (HERE / "subscription_probe.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps(summary, ensure_ascii=False))
            return summary
    finally:
        await live.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.credentials_file))


if __name__ == "__main__":
    main()
