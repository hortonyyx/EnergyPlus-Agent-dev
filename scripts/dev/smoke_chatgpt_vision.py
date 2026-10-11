"""Two-request image and tool smoke in our Runtime, offline unless --live.

Only synthetic colored rectangles are used. Live runs use the explicitly
selected ChatGPT subscription model, with no retries or alternate credentials.
Evidence is restricted to the external development cache.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from PIL import Image, ImageDraw

from src.agent_runtime.connections import (
    ConnectionDescriptor, resolve_connection, validate_connection_model,
)
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.providers import CHATGPT_BASE_URL, CHATGPT_SUBSCRIPTION, provider_parameters
from src.agent_runtime.responses import HttpResponsesAdapter
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import InputMaterialRequirement, ReturnRequirement, RoleDefinition, ToolGrant

CACHE_ROOT = ROOT.parent / "cache"
PALETTE = {"red": (230, 30, 30), "green": (20, 180, 40), "blue": (30, 70, 230)}
GUIDE = (
    "Inspect the attached image. Call vision_probe exactly once with the three "
    "rectangle colors in left-to-right order, using lowercase English color names. "
    "After a successful probe, return only a JSON object with exactly two fields: "
    "colors (the same ordered array) and nonce (the value received from the probe). "
    "If the probe rejects the observation, report failure. Do not guess its nonce."
)


def make_challenge():
    """Return unlabelled synthetic pixels and their private evaluation key."""
    colors = list(PALETTE)
    secrets.SystemRandom().shuffle(colors)
    picture = Image.new("RGB", (480, 180), "white")
    draw = ImageDraw.Draw(picture)
    for index, color in enumerate(colors):
        draw.rectangle((20 + index * 160, 30, 140 + index * 160, 150), fill=PALETTE[color])
    output = io.BytesIO()
    picture.save(output, format="PNG")
    return output.getvalue(), colors


class VisionProbe:
    def __init__(self, expected_colors):
        self.expected_colors = list(expected_colors)
        self.nonce = secrets.token_hex(16)
        self.calls = 0
        self.accepted = 0

    async def list_tools(self):
        return [{"name": "vision_probe", "description": (
            "Validate your observation of the image and read a nonce if correct. "
            "Rejection does not reveal the correct colors or their order."),
            "inputSchema": {"type": "object", "properties": {"colors": {
                "type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3}},
                "required": ["colors"], "additionalProperties": False}}]

    def repeatability(self, name):
        return "read_only"

    async def call_tool(self, name, arguments):
        self.calls += 1
        if (name != "vision_probe" or not isinstance(arguments, dict)
                or set(arguments) != {"colors"}
                or arguments["colors"] != self.expected_colors):
            result = {"accepted": False, "error": "invalid_color_observation"}
        else:
            self.accepted += 1
            result = {"accepted": True, "nonce": self.nonce}
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []


def make_offline_adapter(model, colors):
    """Exercise the real Responses adapter and runtime without network/auth."""
    count = 0

    async def offline_token():
        return "offline-placeholder-not-a-credential"

    def handle(request):
        nonlocal count
        count += 1
        body = json.loads(request.content)
        if count == 1:
            items = [{"type": "function_call", "id": "fc_probe", "call_id": "call_probe",
                "namespace": "runtime", "name": "vision_probe",
                "arguments": json.dumps({"colors": colors}), "status": "completed"}]
        elif count == 2:
            # Read the nonce from the actual tool result carried over the wire.
            result = next(item["output"] for item in body["input"]
                          if item.get("type") == "function_call_output")
            # Responses carries function output as native input_text blocks.
            reply = json.loads(result[0]["text"])
            answer = {"colors": colors, "nonce": reply.get("nonce", "probe-rejected")}
            items = [{"type": "message", "id": "msg_final", "role": "assistant",
                "status": "completed", "content": [{"type": "output_text",
                "text": json.dumps(answer), "annotations": []}]}]
        else:
            raise AssertionError("smoke exceeded its two-request limit")
        response = {"object": "response", "id": f"resp_{count}", "model": model,
            "status": "completed", "output": items,
            "usage": {"input_tokens": 140, "output_tokens": 40, "total_tokens": 180,
                      "input_tokens_details": {"cached_tokens": 0},
                      "output_tokens_details": {"reasoning_tokens": 20}}}
        return httpx.Response(200, headers={"content-type": "text/event-stream"},
            text="data: " + json.dumps({"type": "response.completed", "response": response}) + "\n\n")

    return HttpResponsesAdapter(token_provider=offline_token, transport=httpx.MockTransport(handle))


def evidence_summary(store, image_bytes):
    requests = [event.payload for event in store.events if event.payload.event_type == "adapter_request"]
    responses = [event.payload for event in store.events if event.payload.event_type == "model_response"]
    raw = [store.resolve(response.raw_response) for response in responses]
    image_requests = sum(bool(request.images) and all(
        store.get_bytes(image.sent) == image_bytes for image in request.images)
        for request in requests)
    return {
        "recorded_requests": len(requests), "recorded_responses": len(responses),
        "requests_with_exact_image": image_requests,
        "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "provider_reported_models": [response.get("model") for response in raw],
        "raw_usage": [response.get("usage") for response in raw],
    }


async def execute(args):
    output = args.out.resolve()
    if not output.is_relative_to(CACHE_ROOT.resolve()) or output == CACHE_ROOT.resolve():
        raise ValueError("output must be a new subdirectory of " + str(CACHE_ROOT))
    if output.exists():
        raise ValueError("use a new output directory; prior evidence is never overwritten")
    image_bytes, colors = make_challenge()
    probe = VisionProbe(colors)
    if args.live:
        connection = resolve_connection(CHATGPT_SUBSCRIPTION, None,
                                        chatgpt_auth_dir=args.chatgpt_auth_dir)
        await validate_connection_model(connection, args.model)
        descriptor = connection.descriptor
        adapter = connection.create_adapter()
    else:
        # Do not instantiate subscription credentials or read auth in offline mode.
        descriptor = ConnectionDescriptor(route_id=CHATGPT_SUBSCRIPTION, base_url=CHATGPT_BASE_URL,
            billing_mode="subscription", adapter_kind="openai_responses")
        adapter = make_offline_adapter(args.model, colors)
    limits = RunLimits(model_calls=2, tool_calls=1, seconds=300, tokens=100000,
        max_model_retries=0, max_tool_recovery_retries=0,
        max_consecutive_truncations=0, max_total_truncations=0)
    role = RoleDefinition(role_id="coordinator", responsibilities=("verify image and native subscription tool protocol",),
        tool_whitelist=(ToolGrant(tool_name="vision_probe", access="read"),),
        input_materials=(InputMaterialRequirement(name="task", media_type="text/plain"),
                         InputMaterialRequirement(name="synthetic_image", media_type="image/png")),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="vision-probe-result"),),
        budget=limits.ledger_limit(), read_only=True)
    parameters = provider_parameters(CHATGPT_SUBSCRIPTION, output_tokens=32000,
                                     reasoning_effort=args.reasoning_effort)
    try:
        with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
            specs = [{"type": "function", "function": {"name": tool["name"], "description": tool["description"],
                "parameters": tool["inputSchema"]}} for tool in await probe.list_tools()]
            route = {**descriptor.model_route(args.model),
                "verification_mode": "live_subscription" if args.live else "offline_sse_fixture"}
            versions = make_versions(store, root=ROOT, prompt=GUIDE, tools=specs, parameters=parameters,
                route=route, code_paths=("scripts/dev/smoke_chatgpt_vision.py",))
            store.write_json("versions.json", versions.model_dump(mode="json"))
            image_ref = store.put_bytes(image_bytes, "image/png")
            store.write_json("synthetic_challenge.json", {"image": image_ref.model_dump(mode="json"),
                "expected_colors": colors, "source": "synthetic_unlabelled_rectangles",
                "evaluation_only": True})
            runtime = Runtime(store=store, adapter=adapter, tools=probe, role=role, model=args.model,
                parameters=parameters, versions=versions, limits=limits, context_policy=ContextPolicy(),
                strict_model_profile=True, request_timeout_seconds=300)
            receipt = await runtime.run([{"role": "system", "content": GUIDE},
                {"role": "user", "content": [
                    {"type": "text", "text": "Read these three rectangles from left to right."},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," +
                        base64.b64encode(image_bytes).decode("ascii"), "detail": "high"}}]}])
            store.write_json("receipt.json", receipt)
            try:
                answer_ok = json.loads(receipt.get("answer") or "null") == {
                    "colors": colors, "nonce": probe.nonce}
            except ValueError:
                answer_ok = False
            evidence = evidence_summary(store, image_bytes)
            evidence_ok = (evidence["recorded_requests"] == evidence["recorded_responses"] == 2
                and evidence["requests_with_exact_image"] == 2
                and all(evidence["raw_usage"]) and receipt["usage_complete"])
            summary = {"verification_mode": route["verification_mode"], "status": receipt["status"],
                "requested_model": args.model, "requested_reasoning_effort": args.reasoning_effort,
                "passed": (receipt["status"] == "completed" and probe.calls == probe.accepted == 1
                           and answer_ok and evidence_ok and not receipt["fallback"]),
                "vision_observation_passed": probe.calls == probe.accepted == 1,
                "nonce_round_trip_passed": answer_ok,
                "live_model_requests": receipt["model_calls"] if args.live else 0,
                "fixture_requests": 0 if args.live else receipt["model_calls"],
                "tool_calls": probe.calls, "reported_tokens": receipt["reported_tokens"],
                "billing_mode": "subscription" if args.live else "offline", "paid_api_requests": 0,
                "fallback": receipt["fallback"], "elapsed_seconds": receipt["elapsed_seconds"],
                "evidence": evidence}
            store.write_json("smoke_result.json", summary)
            store.validate()
            return summary
    finally:
        await adapter.close()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--out", type=Path, required=True)
    result.add_argument("--model", required=True, help="explicit slug from the account's models command")
    result.add_argument("--reasoning-effort", choices=("low", "medium", "high"), default="high")
    result.add_argument("--chatgpt-auth-dir", type=Path)
    result.add_argument("--live", action="store_true", help="at most two requests against the authorized ChatGPT plan")
    return result


def main():
    args = parser().parse_args()
    try:
        summary = asyncio.run(execute(args))
    except (ValueError, RuntimeError) as error:
        # No traceback, private object, account identity, or request headers.
        print(json.dumps({"status": "setup_failed", "error_type": type(error).__name__}))
        raise SystemExit(1)
    print(json.dumps(summary, ensure_ascii=False))
    raise SystemExit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
