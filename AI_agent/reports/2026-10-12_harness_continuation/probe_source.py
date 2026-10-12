"""Offline by default; explicit live mode permits at most 20 inference sends.

This probes route/model/image protocol and the Runtime tool loop only. It does
not use the full reader tool set, build BIM, score drawing understanding, or
authorize any retry beyond this one batch. An unsuccessful stage stops later
stages; already started sessions in that stage finish within their own limits.
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

ROOT = Path("D:/Sim-BIM-Agent/repo")
PROBE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import httpx
from PIL import Image

from src.agent_runtime.agent_registry import release_records, source_commit
from src.agent_runtime.connections import ConnectionDescriptor, resolve_connection, validate_connection_model
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.failures import safe_exception_details
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.providers import CHATGPT_BASE_URL, CHATGPT_SUBSCRIPTION, provider_parameters
from src.agent_runtime.responses import HttpResponsesAdapter
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import (InputMaterialRequirement, RemoteModelIdentity, ReturnRequirement,
    RoleDefinition, ToolGrant, VersionManifest, VersionStamp)

GUIDE = (
    "This is a read-only service/tool-loop smoke, not a BIM task. On your first reply, "
    "call view_image exactly once with the assigned image name. Do not call any other tool. "
    "After its result, reply only with a JSON object containing exactly image and nonce, "
    "copied from that tool result. Do not describe, model, measure or evaluate the building."
)
TARGETS = {
    "F1": ("1f_view.png", "gpt-6-sol", "plan_reader"),
    "F2": ("2f_view.png", "gpt-6-sol", "plan_reader"),
    "North": ("North_view.png", "gpt-6-luna", "elevation_reader"),
    "East": ("East_view.png", "gpt-6-luna", "elevation_reader"),
    "South": ("South_view.png", "gpt-6-luna", "elevation_reader"),
    "West": ("West_view.png", "gpt-6-luna", "elevation_reader"),
}
STAGES = [("F1",), ("F1", "F2", "North"), tuple(TARGETS)]


def digest(value):
    return hashlib.sha256(value).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def load_config():
    path = PROBE_ROOT / "probe_config.json"
    config = json.loads(path.read_bytes())
    expected = [(len(stage), [{"target": t, "image": TARGETS[t][0], "model": TARGETS[t][1], "role": TARGETS[t][2]}
                             for t in stage]) for stage in STAGES]
    if [(s["concurrency"], s["sessions"]) for s in config["stages"]] != expected:
        raise ValueError("stage configuration differs from the authorized 1/3/6 plan")
    for key, value in {"repo": str(ROOT).replace("\\", "/"), "route": CHATGPT_SUBSCRIPTION,
        "reasoning_effort": "high", "max_batch_requests": 20, "max_session_requests": 2,
        "max_model_retries": 0, "max_tool_recovery_retries": 0, "tokens": None,
        "session_seconds": 600, "request_timeout_seconds": 300}.items():
        if config[key] != value:
            raise ValueError("configuration differs from the approved probe bounds")
    return config


def load_images(config):
    manifest_path = Path(config["input_manifest"])
    if manifest_path != ROOT / "AI_agent/reports/2026-10-12_sm25_gpt_mix/input_manifest.json":
        raise ValueError("only the reviewed sm25 input manifest is allowed")
    raw = manifest_path.read_bytes()
    if digest(raw) != config["input_manifest_sha256"]:
        raise ValueError("input manifest changed")
    manifest = json.loads(raw)
    directory = Path(manifest["input"]).resolve()
    if directory != Path("D:/Sim-BIM-Agent/cases/sm25-gpt-20261012/input").resolve():
        raise ValueError("unexpected input directory")
    if {x["file"] for x in manifest["images"]} != {x[0] for x in TARGETS.values()}:
        raise ValueError("manifest must contain exactly the six approved images")
    images = {}
    for item in manifest["images"]:
        data = (directory / item["file"]).read_bytes()
        with Image.open(io.BytesIO(data)) as image:
            size, media_type = list(image.size), Image.MIME[image.format]
        if digest(data) != item["sha256"] or len(data) != item["bytes"] or size != item["pixels"] or media_type != "image/png":
            raise ValueError("source image identity changed")
        # Existing Responses image capture/normalization receives original PNG
        # bytes and dimensions. No crop, re-encode or external URL is introduced.
        images[item["file"]] = {**item, "data": data, "media_type": media_type}
    return images


class ImageProbe:
    def __init__(self, image):
        self.image = image
        self.nonce = secrets.token_hex(16)
        self.calls = self.accepted = 0

    async def list_tools(self):
        return [{"name": "view_image", "description": "Read the assigned original image and a one-use probe nonce. No BIM changes.",
            "inputSchema": {"type": "object", "properties": {"image": {"type": "string", "enum": [self.image["file"]]}},
                            "required": ["image"], "additionalProperties": False}}]

    def repeatability(self, name):
        return "read_only"

    async def call_tool(self, name, arguments):
        self.calls += 1
        if name != "view_image" or arguments != {"image": self.image["file"]} or self.calls != 1:
            return {"isError": True, "content": [{"type": "text", "text": "invalid scoped probe call"}]}
        self.accepted += 1
        return {"content": [
            {"type": "text", "text": json.dumps({"image": self.image["file"], "nonce": self.nonce})},
            {"type": "image", "mimeType": self.image["media_type"], "data": base64.b64encode(self.image["data"]).decode("ascii")}]}

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []


class BatchGate:
    def __init__(self):
        self.total = self.in_flight = self.peak = 0
        self.lock = asyncio.Lock()


class CappedAdapter:
    def __init__(self, adapter, gate):
        self.adapter, self.gate, self.calls = adapter, gate, 0

    @property
    def last_received_usage(self):
        return self.adapter.last_received_usage

    @property
    def last_send_timing(self):
        return self.adapter.last_send_timing

    async def send(self, request, *, timeout):
        async with self.gate.lock:
            if self.calls >= 2 or self.gate.total >= 20:
                raise RuntimeError("probe hard request cap reached before transport")
            self.calls += 1
            self.gate.total += 1
            self.gate.in_flight += 1
            self.gate.peak = max(self.gate.peak, self.gate.in_flight)
        try:
            return await self.adapter.send(request, timeout=timeout)
        finally:
            async with self.gate.lock:
                self.gate.in_flight -= 1

    async def close(self):
        await self.adapter.close()


def offline_adapter(model, image, failure=None):
    count = 0
    async def token():
        return "offline-placeholder-not-a-credential"
    async def handle(request):
        nonlocal count
        count += 1
        await asyncio.sleep(0.01)  # Allow fixture concurrency to be observable.
        body = json.loads(request.content)
        if failure == "overload":
            event = {"type": "error", "error": {"type": "service_unavailable_error", "code": "server_is_overloaded",
                "headers": {"x-retry-metadata": "NO_MORE_RETRY"}}}
        else:
            if count == 1 and failure != "no_tool":
                output = [{"type": "function_call", "id": "fc_probe", "call_id": "call_probe", "namespace": "runtime",
                    "name": "view_image", "arguments": json.dumps({"image": image}), "status": "completed"}]
            else:
                result = next((i["output"] for i in body["input"] if i.get("type") == "function_call_output"), [])
                answer = next((b["text"] for b in result if b.get("type") == "input_text"), "{}")
                output = [{"type": "message", "id": "msg_probe", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": answer, "annotations": []}]}]
            raw = {"object": "response", "id": f"resp_{count}", "model": model, "status": "completed", "output": output}
            if failure == "wrong_model":
                raw["model"] = "gpt-6-luna" if model == "gpt-6-sol" else "gpt-6-sol"
            elif failure == "missing_model":
                raw.pop("model")
            elif failure == "unverified_model_suffix":
                raw["model"] = model + "-unverified-suffix"
            if failure != "missing_usage":
                raw["usage"] = {"input_tokens": 1500, "output_tokens": 50, "total_tokens": 1550,
                    "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 25}}
            event = {"type": "response.completed", "response": raw}
        return httpx.Response(200, headers={"content-type": "text/event-stream", "x-request-id": "req-offline"},
                              text="data: " + json.dumps(event) + "\n\n")
    return HttpResponsesAdapter(token_provider=token, transport=httpx.MockTransport(handle))


def offline_versions(model):
    stamp = VersionStamp(identifier="offline-unregistered-probe-fixture")
    return VersionManifest(code_commit=stamp, dependency_lock=stamp, prompt=stamp,
        tool_definitions=stamp, inference_parameters=stamp, model_route=stamp,
        remote_model=RemoteModelIdentity(route_id=CHATGPT_SUBSCRIPTION, remote_alias=model, alias_status="unverified"))


def identity_evidence(store, *, model, effort):
    """Compare exact wire/service identities; no unverified suffix aliases."""
    requests, responses = [], []
    for event in store.events:
        payload = event.payload
        if payload.event_type == "adapter_request":
            body = json.loads(store.capture_bytes(payload.final_request_body))
            reasoning = body.get("reasoning")
            actual_effort = reasoning.get("effort") if isinstance(reasoning, dict) else None
            requests.append({"event_id": event.event_id, "wire_model": body.get("model"),
                "wire_reasoning_effort": actual_effort,
                "matches_configuration": body.get("model") == model and actual_effort == effort})
        elif payload.event_type == "model_response":
            raw = store.resolve(payload.raw_response)
            actual_model = raw.get("model") if isinstance(raw, dict) else None
            responses.append({"event_id": event.event_id, "request_event_id": payload.request_event_id,
                "reported_model": actual_model, "matches_configuration": actual_model == model})
    return {"expected_model": model, "expected_reasoning_effort": effort,
        "comparison": "exact identifiers; missing values and unverified dynamic suffixes fail",
        "requests": requests, "responses": responses,
        "passed": len(requests) == len(responses) == 2 and all(
            item["matches_configuration"] for item in requests + responses)}


async def run_session(args, config, output, session, image, gate, connection, fixture_failure=None):
    name, model = session["session_id"], session["model"]
    tool = ImageProbe(image)
    adapter = CappedAdapter(connection.create_adapter() if args.live else offline_adapter(model, image["file"], fixture_failure), gate)
    limits = RunLimits(model_calls=2, tool_calls=1, seconds=600, tokens=None,
        max_model_retries=0, max_tool_recovery_retries=0, max_consecutive_truncations=0, max_total_truncations=0)
    role = RoleDefinition(role_id=session["role"], responsibilities=("read-only call-chain probe; not full reader duties",),
        tool_whitelist=(ToolGrant(tool_name="view_image", access="read"),),
        input_materials=(InputMaterialRequirement(name="assigned_image", media_type="image/png"),),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="image-nonce-probe"),),
        budget=limits.ledger_limit(), read_only=True)
    parameters = provider_parameters(CHATGPT_SUBSCRIPTION, output_tokens=32000, reasoning_effort="high")
    descriptor = connection.descriptor if connection else ConnectionDescriptor(route_id=CHATGPT_SUBSCRIPTION,
        base_url=CHATGPT_BASE_URL, billing_mode="subscription", adapter_kind="openai_responses")
    try:
        with EventStore(output / name, run_id=name, task_id=name, budget_limit=limits.ledger_limit()) as store:
            specs = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}}
                     for t in await tool.list_tools()]
            versions = (make_versions(store, root=ROOT, prompt=GUIDE, tools=specs, parameters=parameters,
                         route=descriptor.model_route(model)) if args.live else offline_versions(model))
            store.write_json("versions.json", versions.model_dump(mode="json"))
            store.write_json("probe_source.json", {"script_sha256": digest(Path(__file__).read_bytes()),
                "config_sha256": digest((PROBE_ROOT / "probe_config.json").read_bytes()),
                "image": {k: v for k, v in image.items() if k != "data"}, "scope": config["purpose"]})
            runtime = Runtime(store=store, adapter=adapter, tools=tool, role=role, model=model,
                parameters=parameters, versions=versions, limits=limits, context_policy=ContextPolicy(),
                strict_model_profile=True, request_timeout_seconds=300)
            receipt = await runtime.run([{"role": "system", "content": GUIDE}, {"role": "user", "content": [
                {"type": "text", "text": "Assigned image: " + image["file"] + ". Start the read-only probe."},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(image["data"]).decode("ascii"), "detail": "high"}}]}])
            store.write_json("receipt.json", receipt)
            requests = [e.payload for e in store.events if e.payload.event_type == "adapter_request"]
            responses = [e.payload for e in store.events if e.payload.event_type == "model_response"]
            failures = [e.payload.model_failure.model_dump(mode="json") for e in store.events
                        if e.payload.event_type == "run_lifecycle" and e.payload.model_failure]
            raw_usage = [r.usage.raw_usage if r.usage.kind == "reported" else None for r in responses]
            identity = identity_evidence(store, model=model, effort=config["reasoning_effort"])
            exact_images = all(r.images and all(store.get_bytes(i.sent) == image["data"] for i in r.images) for r in requests)
            try:
                answer_ok = json.loads(receipt.get("answer") or "null") == {"image": image["file"], "nonce": tool.nonce}
            except ValueError:
                answer_ok = False
            passed = (receipt["status"] == "completed" and len(requests) == len(responses) == 2
                and tool.calls == tool.accepted == 1 and answer_ok and exact_images
                and identity["passed"] and not receipt["fallback"])
            result = {**session, "status": receipt["status"], "passed": passed, "requests": len(requests),
                "responses": len(responses), "adapter_dispatches": adapter.calls, "tool_calls": tool.calls,
                "nonce_round_trip_passed": answer_ok, "exact_original_images": exact_images,
                "identity": identity,
                "raw_usage": raw_usage, "usage_complete": receipt["usage_complete"],
                "reported_tokens_subtotal": receipt["reported_tokens"],
                "total_tokens": receipt["reported_tokens"] if receipt["usage_complete"] else None,
                "safe_failures": failures, "elapsed_seconds": receipt["elapsed_seconds"],
                "events_sha256": digest(store.path.read_bytes()), "fallback": receipt["fallback"]}
            store.write_json("probe_result.json", result)
            store.validate()
            return result
    except Exception as exc:
        return {**session, "passed": False, "status": "local_probe_error", "adapter_dispatches": adapter.calls,
                "total_tokens": None, "usage_complete": False,
                "diagnostic": safe_exception_details(exc, stage="call_chain_probe")}
    finally:
        await adapter.close()


async def execute(args, *, fixture_failures=None):
    if args.live and fixture_failures:
        raise ValueError("fixture overrides are forbidden live")
    output = args.out.resolve()
    if not output.is_relative_to(PROBE_ROOT) or output == PROBE_ROOT or output.exists():
        raise ValueError("use a new output subdirectory of the probe cache; never overwrite evidence")
    config, gate = load_config(), BatchGate()
    images = load_images(config)
    connection = None
    if args.live:
        if not args.expected_commit or source_commit(ROOT) != args.expected_commit:
            raise ValueError("live probe requires the exact frozen source commit")
        releases = release_records(ROOT)  # Must verify production registry before any network.
    else:
        releases = None
    output.mkdir(parents=True)
    write_new(output / "launch.json", {"mode": "live" if args.live else "offline_mock_sse",
        "purpose": config["purpose"], "expected_commit": args.expected_commit,
        "source_commit": source_commit(ROOT), "script_sha256": digest(Path(__file__).read_bytes()),
        "config_sha256": digest((PROBE_ROOT / "probe_config.json").read_bytes()),
        "registered_versions": {k: v["version_id"] for k, v in releases.items()} if releases else None,
        "image_hashes": {name: image["sha256"] for name, image in images.items()},
        "hard_inference_request_cap": 20, "automatic_retries": 0, "readonly_tools": ["view_image"]})
    stages = []
    try:
        if args.live:
            connection = resolve_connection(CHATGPT_SUBSCRIPTION, None, chatgpt_auth_dir=args.chatgpt_auth_dir)
            for model in ("gpt-6-sol", "gpt-6-luna"):
                await validate_connection_model(connection, model)
        for index, stage in enumerate(config["stages"], 1):
            sessions = [{**s, "session_id": f"stage{index}_{s['target']}"} for s in stage["sessions"]]
            results = await asyncio.gather(*(run_session(args, config, output, session, images[session["image"]],
                gate, connection, (fixture_failures or {}).get(session["session_id"])) for session in sessions))
            record = {"stage": index, "configured_concurrency": stage["concurrency"],
                      "passed": all(r["passed"] for r in results), "sessions": results}
            stages.append(record)
            write_new(output / f"stage-{index}.json", record)
            if not record["passed"]:
                break
        known = sum(r.get("reported_tokens_subtotal", 0) or 0 for stage in stages for r in stage["sessions"])
        usage_complete = bool(stages) and all(r.get("usage_complete") for stage in stages for r in stage["sessions"])
        summary = {"passed": len(stages) == 3 and all(s["passed"] for s in stages), "purpose": config["purpose"],
            "mode": "live" if args.live else "offline_mock_sse", "completed_stages": len(stages),
            "live_model_dispatches": gate.total if args.live else 0, "fixture_dispatches": 0 if args.live else gate.total,
            "peak_adapter_dispatches_in_flight": gate.peak, "hard_request_cap": 20,
            "reported_tokens_subtotal": known, "usage_complete": usage_complete,
            "total_tokens": known if usage_complete else None, "total_cost": None,
            "stages": stages, "scope": "Same subscription route, models, original-image protocol and Runtime tool loop; single scoped read-only tool, not full readers/BIM benchmark."}
    except Exception as exc:
        summary = {"passed": False, "status": "setup_or_batch_failure", "completed_stages": len(stages),
            "live_model_dispatches": gate.total if args.live else 0, "fixture_dispatches": 0 if args.live else gate.total,
            "usage_complete": False, "total_tokens": None, "stages": stages,
            "diagnostic": safe_exception_details(exc, stage="probe_setup_or_batch")}
    write_new(output / "batch_result.json", summary)
    return summary


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--out", type=Path, required=True)
    result.add_argument("--expected-commit", help="required exact frozen Git SHA for --live")
    result.add_argument("--chatgpt-auth-dir", type=Path)
    result.add_argument("--live", action="store_true", help="explicitly use the authorized subscription; maximum 20 inference sends")
    return result


def main():
    try:
        result = asyncio.run(execute(parser().parse_args()))
    except Exception as exc:
        result = {"passed": False, "status": "preflight_failed", "diagnostic": safe_exception_details(exc, stage="probe_preflight")}
    print(json.dumps({key: value for key, value in result.items() if key != "stages"}, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
