"""Two separately started tiny GLM checks, under one durable six-request cap.

This never launches the BIM service or any whole-case task. Credentials are
read only from --credentials-file; only the two GLM subscription keys are used.
"""

import argparse
import asyncio
import base64
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

from src.agent_runtime.anthropic import HttpAnthropicAdapter
from src.agent_runtime.call_quota import QuotaAdapter
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.providers import GLM_SUBSCRIPTION_ANTHROPIC as ROUTE, provider_parameters, subscription_credentials
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import RoleDefinition, ToolGrant, InputMaterialRequirement, ReturnRequirement

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def picture(colour):
    output = io.BytesIO()
    Image.new("RGB", (96, 96), colour).save(output, format="PNG")
    return output.getvalue()


class ProbeTools:
    def __init__(self, enabled):
        self.enabled = enabled

    async def list_tools(self):
        return [{"name": "record_reading", "description": "Record the input image colour and computed integer; returns a new image for the final answer.",
                 "inputSchema": {"type": "object", "properties": {"input_colour": {"type": "string"}, "total": {"type": "integer"}},
                                 "required": ["input_colour", "total"], "additionalProperties": False}}] if self.enabled else []

    def repeatability(self, name):
        return "read_only"

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []

    async def call_tool(self, name, arguments):
        if not self.enabled or name != "record_reading":
            raise ValueError("probe tool is unavailable")
        return {"content": [{"type": "text", "text": json.dumps({"recorded": arguments,
            "instruction": "Now inspect the returned image and finish in one short sentence with both image colours and the total; do not call another tool."})},
            {"type": "image", "mimeType": "image/png", "data": base64.b64encode(picture("blue")).decode()}]}


async def run(part, credentials):
    output = HERE / "evidence" / part
    if output.exists():
        raise ValueError("probe output already exists; never overwrite or implicitly retry")
    parameters = provider_parameters(ROUTE, output_tokens=32000 if part == "roundtrip" else 128)
    tools = ProbeTools(part == "roundtrip")
    limits = RunLimits(model_calls=2, tool_calls=1 if part == "roundtrip" else 0,
        seconds=240, tokens=500000, max_model_retries=0,
        max_consecutive_truncations=1 if part == "truncation" else 0,
        max_total_truncations=1 if part == "truncation" else 0)
    role = RoleDefinition(role_id="protocol_probe", responsibilities=("Run the explicitly approved tiny protocol probe",),
        tool_whitelist=(ToolGrant(tool_name="record_reading", access="read"),) if part == "roundtrip" else (),
        input_materials=(InputMaterialRequirement(name="task", media_type="text/plain"),),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="text"),),
        budget=limits.ledger_limit(), read_only=True)
    guide = "You are a protocol-test assistant. Complete only the user's small test, use only the declared tool, and follow output-limit recovery instructions immediately."
    if part == "roundtrip":
        # Stable harmless prefix long enough to observe service caching. It is
        # included in the recorded request and its measured input usage.
        guide += "\nReference labels (background for caching only, no action required):\n" + "\n".join(
            f"Item {i:03d}: blue, red, green, yellow are colour labels; recorded totals are integers; preserve observations exactly." for i in range(140))
        task = "Identify the colour of the attached solid image. Calculate the number of ways to choose 3 objects from 15, then add 18 times 27. Call record_reading exactly once with input_colour and total. After the tool returns, inspect its new image and finish in one short sentence giving both colours and the total."
        messages = [{"role": "system", "content": guide}, {"role": "user", "content": [
            {"type": "text", "text": task}, {"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(picture("red")).decode()}}]}]
    else:
        task = "For the first draft, write a 450-word description of a quiet library with at least 15 numbered paragraphs. If an output-limit recovery instruction arrives, abandon that draft and respond with the single word OK."
        messages = [{"role": "system", "content": guide}, {"role": "user", "content": task}]
    base, key = subscription_credentials(credentials, provider=ROUTE)
    transport = HttpAnthropicAdapter(base_url=base, api_key=key)
    quota = QuotaAdapter(transport, HERE / "evidence/request_quota.jsonl", limit=6, category="a1r-glm-subscription-smoke")
    try:
        with EventStore(output, run_id="a1r-" + part, task_id="protocol_probe", budget_limit=limits.ledger_limit()) as store:
            specs = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}} for t in await tools.list_tools()]
            versions = make_versions(store, root=ROOT, prompt=guide, tools=specs, parameters=parameters,
                route={"route_id": ROUTE, "model": "glm-5.3-flash", "base_url": base, "billing_mode": "subscription"})
            engine = Runtime(store=store, adapter=quota, tools=tools, role=role, model="glm-5.3-flash",
                parameters=parameters, versions=versions, limits=limits, context_policy=ContextPolicy(),
                low_output_limit_reason="A1-R authorized small output-limit recovery probe" if part == "truncation" else None,
                strict_model_profile=True)
            receipt = await engine.run(messages)
            store.validate()
            rows = []
            requests = {e.event_id: e.payload for e in store.events if e.payload.event_type == "adapter_request"}
            for e in store.events:
                if e.payload.event_type != "model_response":
                    continue
                raw = store.resolve(e.payload.raw_response)
                request = requests[e.payload.request_event_id]
                assert hashlib.sha256(store.capture_bytes(request.final_request_body)).hexdigest() == request.wire_sha256
                rows.append({"event_id": e.event_id, "request_id": e.payload.request_event_id,
                    "stop_reason": raw.get("stop_reason"), "usage": raw.get("usage"),
                    "response_block_types": [b["type"] for b in raw.get("content", [])],
                    "thinking_forms": [t.kind for t in e.payload.thinking],
                    "sent_images": len(request.images), "wire_sha256": request.wire_sha256,
                    "visible_text": list(e.payload.visible_text), "tool_calls": [c.model_dump(mode="json") for c in e.payload.tool_calls]})
            summary = {"part": part, "status": receipt["status"], "model_calls": receipt["model_calls"],
                "tool_calls": receipt["tool_calls"], "truncations": receipt["truncations"],
                "reported_tokens": receipt["reported_tokens"], "usage_accounting": receipt["usage_accounting"],
                "responses": rows, "whole_cases": 0, "paratera_calls": 0, "deepseek_calls": 0}
            (HERE / ("smoke_" + part + ".json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps(summary, ensure_ascii=False))
            return receipt["status"] == "completed"
    finally:
        await transport.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("part", choices=("roundtrip", "truncation"))
    p.add_argument("--credentials-file", type=Path, required=True)
    args = p.parse_args()
    raise SystemExit(0 if asyncio.run(run(args.part, args.credentials_file)) else 1)
