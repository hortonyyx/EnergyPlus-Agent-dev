"""Authorized subscription-only protocol probe; at most six durable attempts."""

import argparse
import asyncio
import base64
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw

from src.agent_runtime.adapter import HttpChatAdapter
from src.agent_runtime.call_quota import QuotaAdapter
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.providers import provider_parameters, subscription_credentials
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import InputMaterialRequirement, ReturnRequirement, RoleDefinition, ToolGrant

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent


class ProbeTools:
    def __init__(self, enabled):
        self.enabled, self.calls = enabled, []

    async def list_tools(self):
        return [{"name": "report_color", "description": "Record the observed color and return an acknowledgement.",
            "inputSchema": {"type": "object", "properties": {"color": {"type": "string", "enum": ["red", "green", "blue"]}},
                "required": ["color"], "additionalProperties": False}}] if self.enabled else []

    def repeatability(self, name):
        return "read_only"

    async def call_tool(self, name, arguments):
        self.calls.append({"name": name, "arguments": arguments})
        return {"isError": False, "content": [{"type": "text", "text": "Color received: " + arguments["color"] + ". Reply OK now."}]}

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []


async def phase(guarded, base_url, *, name, visual, cap):
    directory = HERE / "live" / name
    if directory.exists():
        raise ValueError("probe phase already exists; inspect its evidence instead of replaying it")
    limits = RunLimits(model_calls=3, tool_calls=1 if visual else 0, seconds=180,
        tokens=200000, max_consecutive_truncations=2, max_total_truncations=2)
    tools = ProbeTools(visual)
    role = RoleDefinition(role_id="subscription_probe", responsibilities=("Test subscription protocol only",),
        tool_whitelist=(ToolGrant(tool_name="report_color", access="read"),) if visual else (),
        input_materials=(InputMaterialRequirement(name="task", media_type="text/plain"),),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="text"),), budget=limits.ledger_limit(), read_only=True)
    system = (
        "Protocol test. Inspect the central colored rectangle in the image. First call report_color with its color. "
        "After the tool acknowledges it, reply only OK. Do not describe the image in prose."
        if visual else
        "This is an output-limit protocol test. First write every integer from 1 to 1000, separated by spaces, "
        "without preamble or abbreviations. If a later runtime message says the previous response exceeded the output limit, "
        "immediately answer only OK. Do not repeat the number list in that case."
    )
    parameters = provider_parameters("glm-subscription", output_tokens=cap)
    with EventStore(directory, run_id="r2c-" + name, task_id="subscription_probe", budget_limit=limits.ledger_limit()) as store:
        catalog = await tools.list_tools()
        specs = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}} for t in catalog]
        versions = make_versions(store, root=ROOT, prompt=system, tools=specs, parameters=parameters,
            route={"route_id": "glm-subscription", "model": "glm-5.3-flash", "base_url": base_url, "billing_mode": "subscription"})
        originals, content = {}, "Start the number list now."
        if visual:
            image = Image.new("RGB", (256, 256), "white")
            ImageDraw.Draw(image).rectangle((32, 32, 224, 224), fill=(0, 180, 0))
            output = io.BytesIO()
            image.save(output, format="PNG")
            raw = output.getvalue()
            reference = store.put_bytes(raw, "image/png")
            originals[reference.sha256] = reference
            content = [{"type": "text", "text": "Report the central rectangle color using the tool."},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw).decode()}}]
        engine = Runtime(store=store, adapter=guarded, tools=tools, role=role, model="glm-5.3-flash",
            parameters=parameters, versions=versions, limits=limits, strict_model_profile=True,
            low_output_limit_reason=None if visual else "R2c authorized protocol probe: 512-token cap deliberately forces truncation.")
        receipt = await engine.run([{"role": "system", "content": system}, {"role": "user", "content": content}], image_originals=originals)
        store.validate()
        requests = [e.payload for e in store.events if e.payload.event_type == "adapter_request"]
        responses = [e.payload for e in store.events if e.payload.event_type == "model_response"]
        wire = [store.resolve(p.final_request_body) for p in requests]
        raw_responses = [store.resolve(p.raw_response) for p in responses]
        success = receipt["status"] == "completed" and receipt["answer"].strip() == "OK"
        success &= (tools.calls == [{"name": "report_color", "arguments": {"color": "green"}}]) if visual else receipt["truncations"] >= 1
        result = {"phase": name, "passed": success, "tools": tools.calls,
            "sent_parameters": [{k: v for k, v in body.items() if k not in {"messages", "tools"}} for body in wire],
            "response_fields": [sorted(r["choices"][0]["message"]) for r in raw_responses],
            "finish_reasons": [r["choices"][0]["finish_reason"] for r in raw_responses],
            "thinking_characters": [len(r["choices"][0]["message"].get("reasoning_content") or "") for r in raw_responses],
            "images_per_request": [len(p.images) for p in requests],
            **{k: receipt[k] for k in ("status", "answer", "model_calls", "tool_calls", "reported_tokens", "image_tokens_estimate",
                "estimated_cost_cny", "usage_accounting", "elapsed_seconds", "truncations", "agent_version")}}
        (HERE / (name + "_result.json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return result


async def main():
    base_url, key = subscription_credentials()
    adapter = HttpChatAdapter(base_url=base_url, api_key=key)
    guarded = QuotaAdapter(adapter, HERE / "subscription_requests.jsonl", limit=6, category="r2c_subscription_protocol_only")
    try:
        visual = await phase(guarded, base_url, name="visual_tool", visual=True, cap=32000)
        truncation = await phase(guarded, base_url, name="truncation", visual=False, cap=512)
        result = {"passed": visual["passed"] and truncation["passed"], "maximum_attempts": 6,
            "requests": visual["model_calls"] + truncation["model_calls"], "whole_building_run": False,
            "reasoning_field_observed": any(visual["thinking_characters"] + truncation["thinking_characters"])}
        (HERE / "subscription_probe_result.json").write_text(json.dumps(result, indent=2) + "\n")
    finally:
        await adapter.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-authorized-probe", action="store_true", required=True)
    parser.parse_args()
    asyncio.run(main())
