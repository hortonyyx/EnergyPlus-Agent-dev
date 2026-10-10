"""Bounded GLM subscription smoke test for in-flight correction and pause/resume.

The default is offline and never reads credentials. A live run requires both
``--live`` and an explicit ``--credentials-file``. Every output directory is
created once and never reused.

Offline:
  .venv/Scripts/python.exe -B AI_agent/logs/experiments/2026-10-10_runtime_control_iteration/glm_smoke.py \
    --offline-dry-run --out <new-directory>

Live (run only after runtime/domain version registration):
  .venv/Scripts/python.exe -B AI_agent/logs/experiments/2026-10-10_runtime_control_iteration/glm_smoke.py \
    --live --credentials-file <explicit-env-file> --out <new-directory>
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from src.agent_runtime.adapter import ScriptedAdapter
from src.agent_runtime.call_quota import QuotaAdapter
from src.agent_runtime.connections import resolve_connection
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.control import control_status, submit_command
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.output_limits import validate_output_limit
from src.agent_runtime.providers import GLM_SUBSCRIPTION, provider_parameters
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import (
    InputMaterialRequirement,
    RemoteModelIdentity,
    ReturnRequirement,
    RoleDefinition,
    ToolGrant,
    VersionManifest,
    VersionStamp,
)


ROOT = Path(__file__).resolve().parents[4]
MODEL = "glm-5.3-flash"
TASK_ID = "glm_control_smoke"
OUTPUT_TOKENS = 8_192
WALL_SECONDS = 480.0
OUTPUT_LIMIT_REASON = (
    "Authorized bounded runtime control protocol smoke: the expected output is one tool call "
    "and one compact JSON object, so 8192 tokens provide explicit small-task headroom."
)
CORRECTION_TOKEN = "after-correction"
PAUSE_ID = "pause-after-request-1"
MESSAGE_ID = "correction-after-request-1"
RESUME_ID = "resume-after-safe-boundary"
SYSTEM = (
    "You are executing a runtime control protocol smoke test. On the initial turn, call the "
    "read-only probe tool exactly once with token set exactly to 'before'. Do not give a final "
    "answer before the tool result. After the tool result, obey any later operator correction. "
    "Your final answer must be only one JSON object with exactly these keys: observed, "
    "correction_token, status. Set observed to 'before', status to 'accepted', and "
    "correction_token to the exact value required by the latest operator correction."
)
USER = "Begin the protocol now."
CORRECTION = (
    "Operator correction: in the final JSON, set correction_token exactly to "
    f"'{CORRECTION_TOKEN}'. Keep observed='before' and status='accepted'."
)
EXPECTED_ANSWER = {
    "observed": "before",
    "correction_token": CORRECTION_TOKEN,
    "status": "accepted",
}


def _json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _write_json(path: Path, value) -> None:
    pending = path.with_suffix(path.suffix + ".pending")
    with pending.open("wb") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(path)


class ObservationLog:
    """Small driver-side chronology; runtime events remain authoritative."""

    def __init__(self, path: Path):
        self.path = path
        self.sequence = 0

    def append(self, event: str, **details) -> None:
        row = {"sequence": self.sequence, "event": event,
               "at": datetime.now(UTC).isoformat(),
               "monotonic_seconds": time.monotonic(), **details}
        self.sequence += 1
        with self.path.open("ab") as stream:
            stream.write(_json_bytes(row) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())


class ProbeTools:
    """One deterministic, read-only tool with no BIM or filesystem mutation."""

    def __init__(self):
        self.calls = []

    async def list_tools(self):
        return [{
            "name": "probe",
            "description": "Echo the fixed protocol token. Call exactly once with token='before'.",
            "inputSchema": {
                "type": "object",
                "properties": {"token": {"type": "string", "const": "before"}},
                "required": ["token"],
                "additionalProperties": False,
            },
        }]

    def repeatability(self, name):
        if name != "probe":
            raise ValueError("unknown smoke tool")
        return "read_only"

    def recovery_policy(self, name):
        return "retry_read" if name == "probe" else "manual"

    async def call_tool(self, name, arguments):
        if name != "probe" or arguments != {"token": "before"}:
            raise ValueError("probe requires the exact fixed token")
        if self.calls:
            raise ValueError("probe may be called only once")
        self.calls.append({"name": name, "arguments": arguments})
        return {"isError": False, "content": [{"type": "text", "text":
            "Probe accepted token 'before'. Apply the latest operator correction and return the final JSON."}],
            "structuredContent": {"observed": "before"}}

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []


def _offline_response(*, tool=False):
    if tool:
        message = {"role": "assistant", "content": None, "tool_calls": [{
            "id": "probe-call-1", "type": "function", "function": {
                "name": "probe", "arguments": json.dumps({"token": "before"})}}]}
        finish = "tool_calls"
    else:
        message = {"role": "assistant", "content": json.dumps(
            EXPECTED_ANSWER, ensure_ascii=False, separators=(",", ":"))}
        finish = "stop"
    return {"id": "offline-smoke-response", "model": MODEL,
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150,
                  "completion_tokens_details": {"reasoning_tokens": 5}}}


class ObservedAdapter:
    """Expose the first active send without changing its request or response."""

    def __init__(self, adapter, observations: ObservationLog, *, offline: bool):
        self.adapter = adapter
        self.observations = observations
        self.offline = offline
        self.first_send_started = asyncio.Event()
        self.release_offline_response = asyncio.Event()
        self.attempts = 0

    @property
    def last_send_timing(self):
        return getattr(self.adapter, "last_send_timing", {})

    async def send(self, prepared, *, timeout):
        self.attempts += 1
        if self.attempts == 1:
            self.observations.append("first_adapter_send_started",
                request_sha256=hashlib.sha256(prepared.wire_bytes).hexdigest())
            self.first_send_started.set()
            # The offline adapter has no I/O await, so hold its scripted reply
            # until the controls are durably queued. A live HTTP send naturally
            # yields while the real request is in flight.
            if self.offline:
                await self.release_offline_response.wait()
        raw = await self.adapter.send(prepared, timeout=timeout)
        self.observations.append("adapter_response_received", attempt=self.attempts,
            response_id=raw.get("id") if isinstance(raw, dict) else None,
            usage_present=isinstance(raw, dict) and isinstance(raw.get("usage"), dict))
        return raw


class TimedQuotaAdapter(QuotaAdapter):
    """Preserve inner HTTP timing while enforcing the durable request cap."""

    @property
    def last_send_timing(self):
        return getattr(self.adapter, "last_send_timing", {})


def _offline_versions(store, *, prompt, tools, parameters, route) -> VersionManifest:
    """Version the dry-run without requiring release registration in a dirty tree."""
    script = Path(__file__).resolve()
    lock = ROOT / "uv.lock"
    source = {"script": str(script.relative_to(ROOT).as_posix()),
              "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
              "uv_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest()}

    def stamp(name, value):
        evidence = store.source(name, value)
        return VersionStamp(identifier=evidence.blob.sha256, evidence=evidence)

    return VersionManifest(
        code_commit=stamp("offline-code-manifest", source),
        dependency_lock=stamp("offline-dependency-lock", source["uv_lock_sha256"]),
        prompt=stamp("system-prompt", prompt),
        tool_definitions=stamp("tool-definitions", tools),
        inference_parameters=stamp("inference-parameters", parameters),
        model_route=stamp("model-route", route),
        remote_model=RemoteModelIdentity(route_id=route["route_id"],
            remote_alias=route["model"], alias_status="unverified"),
        mode="single_model",
        role_models={TASK_ID: {"route_id": route["route_id"], "model": route["model"],
            "output_tokens": parameters["max_tokens"],
            "reasoning_effort": parameters.get("reasoning_effort"), "parameters": parameters}},
    )


async def _wait_for_pause_or_stop(engine: Runtime, task: asyncio.Task, timeout: float) -> bool:
    async def wait():
        while not engine._control_paused and not task.done():
            await asyncio.sleep(0.02)
        return engine._control_paused
    return await asyncio.wait_for(wait(), timeout)


async def _wait_for_first_send_or_stop(observed: ObservedAdapter,
                                       task: asyncio.Task, timeout: float) -> None:
    signal = asyncio.create_task(observed.first_send_started.wait())
    done, _ = await asyncio.wait({signal, task}, timeout=timeout,
                                 return_when=asyncio.FIRST_COMPLETED)
    if task in done:
        signal.cancel()
        await asyncio.gather(signal, return_exceptions=True)
        await task
        raise RuntimeError("runtime stopped before its first adapter send")
    if signal in done:
        return
    signal.cancel()
    await asyncio.gather(signal, return_exceptions=True)
    raise TimeoutError("first adapter send was not observed before the deadline")


def _remaining(deadline: float, cap: float | None = None) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("smoke run exceeded its wall-clock deadline")
    return remaining if cap is None else min(remaining, cap)


def _event_rows(store):
    return [{"sequence": event.sequence, "event_id": event.event_id,
             "task_id": event.task_id, "event_type": event.payload.event_type}
            for event in store.events]


async def run_smoke(output: Path, *, live: bool, credentials_file: Path | None) -> dict:
    deadline = time.monotonic() + WALL_SECONDS
    observations = ObservationLog(output / "driver_observations.jsonl")
    observations.append("driver_started", mode="live" if live else "offline_dry_run")
    limits = RunLimits(model_calls=4, tool_calls=1, seconds=WALL_SECONDS, tokens=250_000,
        context_tokens=128_000, max_model_retries=0, retry_backoff_seconds=0,
        max_consecutive_truncations=0, max_total_truncations=0,
        max_tool_recovery_retries=0, summary_every=0)
    parameters = provider_parameters(GLM_SUBSCRIPTION, output_tokens=OUTPUT_TOKENS,
                                     reasoning_effort="low")
    validate_output_limit(MODEL, OUTPUT_TOKENS, reason=OUTPUT_LIMIT_REASON)
    context_policy = ContextPolicy(compact_at_tokens=100_000)
    tools = ProbeTools()
    role = RoleDefinition(role_id=TASK_ID,
        responsibilities=("Verify one bounded runtime control sequence",),
        tool_whitelist=(ToolGrant(tool_name="probe", access="read"),),
        input_materials=(InputMaterialRequirement(name="fixed_prompt", media_type="text/plain"),),
        return_requirements=(ReturnRequirement(name="final_json", schema_ref="glm-control-smoke-v1"),),
        budget=limits.ledger_limit(), read_only=True)

    base_adapter = None
    if live:
        connection = resolve_connection(GLM_SUBSCRIPTION, credentials_file)
        base_adapter = connection.create_adapter()
        route = {**connection.descriptor.model_route(MODEL),
                 "reasoning_history": "all",
                 "context": {"context_tokens": limits.context_tokens,
                             **context_policy.model_dump(mode="json")}}
        adapter = base_adapter
    else:
        fixture = [_offline_response(tool=True), _offline_response()]
        fixture_sha = hashlib.sha256(_json_bytes(fixture)).hexdigest()
        route = {"route_id": "offline-scripted", "model": MODEL,
                 "billing_mode": "offline", "adapter_kind": "scripted",
                 "fixture_sha256": fixture_sha, "intended_live_route": GLM_SUBSCRIPTION,
                 "reasoning_history": "all",
                 "context": {"context_tokens": limits.context_tokens,
                             **context_policy.model_dump(mode="json")}}
        adapter = ScriptedAdapter(fixture)

    observed = ObservedAdapter(adapter, observations, offline=not live)
    guarded = TimedQuotaAdapter(observed, output / "request_quota.jsonl", limit=4,
                                category="2026-10-10_glm_runtime_control_smoke")
    manifest = {"schema_version": 1, "mode": "live" if live else "offline_dry_run",
        "model": MODEL, "provider": GLM_SUBSCRIPTION if live else "scripted",
        "intended_live_provider": GLM_SUBSCRIPTION,
        "limits": limits.model_dump(mode="json"), "parameters": parameters,
        "output_limit_reason": OUTPUT_LIMIT_REASON,
        "route": route, "fixed_inputs": {"system": SYSTEM, "user": USER,
            "correction": CORRECTION, "expected_answer": EXPECTED_ANSWER},
        "control_ids": {"pause": PAUSE_ID, "message": MESSAGE_ID, "resume": RESUME_ID},
        "fallback": False, "credentials_recorded": False}
    _write_json(output / "driver_manifest.json", manifest)

    receipt = None
    try:
        with EventStore(output, run_id="runtime-control-glm-smoke", task_id=TASK_ID,
                        budget_limit=limits.ledger_limit()) as store:
            catalog = await tools.list_tools()
            specs = [{"type": "function", "function": {"name": item["name"],
                "description": item["description"], "parameters": item["inputSchema"]}}
                for item in catalog]
            versions = (make_versions(store, root=ROOT, prompt=SYSTEM, tools=specs,
                parameters=parameters, route=route,
                code_paths=(str(Path(__file__).resolve().relative_to(ROOT).as_posix()),))
                if live else _offline_versions(store, prompt=SYSTEM, tools=specs,
                                               parameters=parameters, route=route))
            _write_json(output / "versions.json", versions.model_dump(mode="json"))
            engine = Runtime(store=store, adapter=guarded, tools=tools, role=role,
                model=MODEL, parameters=parameters, versions=versions, limits=limits,
                context_policy=context_policy, strict_model_profile=True,
                reasoning_history="all", request_timeout_seconds=240,
                low_output_limit_reason=OUTPUT_LIMIT_REASON)
            run_task = asyncio.create_task(engine.run([
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER},
            ]))
            try:
                await _wait_for_first_send_or_stop(
                    observed, run_task, _remaining(deadline, 30))
                request_events = [event for event in store.events
                                  if event.payload.event_type == "adapter_request"]
                if len(request_events) != 1:
                    raise RuntimeError("first send observation lacks exactly one durable request")
                submit_command(output, target_task_id=TASK_ID, action="pause",
                               source="glm_smoke_driver", command_id=PAUSE_ID)
                submit_command(output, target_task_id=TASK_ID, action="message", text=CORRECTION,
                               source="glm_smoke_driver", command_id=MESSAGE_ID)
                observations.append("pause_and_correction_queued",
                    durable_request_event_id=request_events[0].event_id,
                    command_ids=[PAUSE_ID, MESSAGE_ID])
                observed.release_offline_response.set()
                paused = await _wait_for_pause_or_stop(
                    engine, run_task, _remaining(deadline, 300 if live else 10))
                if paused:
                    status_at_pause = control_status(output)
                    observations.append("safe_boundary_paused",
                        model_calls=engine.counts["model_calls"], tool_calls=engine.counts["tool_calls"],
                        response_events=sum(event.payload.event_type == "model_response"
                                            for event in store.events),
                        controls={row["command_id"]: row["status"]
                                  for row in status_at_pause["commands"]})
                    submit_command(output, target_task_id=TASK_ID, action="resume",
                                   source="glm_smoke_driver", command_id=RESUME_ID)
                    observations.append("resume_queued", command_id=RESUME_ID)
                receipt = await asyncio.wait_for(
                    run_task, _remaining(deadline, 20 if not live else None))
            except BaseException:
                if not run_task.done():
                    run_task.cancel()
                await asyncio.gather(run_task, return_exceptions=True)
                raise
            log = store.validate()
            status = control_status(output)
            requests = [event for event in log.events if event.payload.event_type == "adapter_request"]
            responses = [event for event in log.events if event.payload.event_type == "model_response"]
            executions = [event for event in log.events if event.payload.event_type == "tool_execution"]
            controls = [event for event in log.events if event.payload.event_type == "task_control"]
            final_wire = store.resolve(requests[-1].payload.final_request_body) if requests else {}
            correction_count = sum(message.get("content") == CORRECTION
                                   for message in final_wire.get("messages", []))
            try:
                parsed_answer = json.loads(receipt.get("answer") or "")
            except json.JSONDecodeError:
                parsed_answer = None
            control_by_id = {event.payload.command_id: event for event in controls}
            first_response_sequence = responses[0].sequence if responses else None
            pause_sequence = control_by_id[PAUSE_ID].sequence if PAUSE_ID in control_by_id else None
            message_sequence = control_by_id[MESSAGE_ID].sequence if MESSAGE_ID in control_by_id else None
            second_request_sequence = requests[1].sequence if len(requests) > 1 else None
            checks = {
                "completed": receipt.get("status") == "completed",
                "request_bound": receipt.get("model_calls", 99) <= 4,
                "expected_two_requests": receipt.get("model_calls") == 2,
                "single_fixed_probe": tools.calls == [{"name": "probe", "arguments": {"token": "before"}}],
                "paused_after_first_response": paused and first_response_sequence is not None
                    and pause_sequence is not None and first_response_sequence < pause_sequence,
                "message_ack_after_first_response": first_response_sequence is not None
                    and message_sequence is not None and first_response_sequence < message_sequence,
                "resume_before_second_request": RESUME_ID in control_by_id
                    and second_request_sequence is not None
                    and control_by_id[RESUME_ID].sequence < second_request_sequence,
                "correction_sent_once": correction_count == 1,
                "corrected_final_json": parsed_answer == EXPECTED_ANSWER,
                "all_controls_applied": len(status["commands"]) == 3
                    and all(row["status"] == "applied" for row in status["commands"]),
                "no_retry_or_fallback": receipt.get("retries") == 0
                    and receipt.get("truncations") == 0 and receipt.get("fallback") is False,
                "usage_complete": receipt.get("usage_accounting", {}).get("usage_complete") is True,
                "request_response_pairing": len(requests) == len(responses) == 2,
                "single_tool_execution": len(executions) == 1,
            }
            result = {"schema_version": 1, "passed": all(checks.values()),
                "mode": "live" if live else "offline_dry_run", "checks": checks,
                "receipt": {key: receipt.get(key) for key in (
                    "status", "answer", "model_calls", "tool_calls", "reported_tokens",
                    "elapsed_seconds", "timing", "runtime_processing", "usage_accounting",
                    "request_usage_accounting", "limits", "retries", "truncations", "fallback",
                    "runtime_version", "domain_version", "git_commit")},
                "controls": status, "tool_calls": tools.calls,
                "event_index": _event_rows(store),
                "evidence": {"events": "events.jsonl", "receipt": "receipt.json",
                    "checkpoint": "checkpoint.json", "versions": "versions.json",
                    "quota": "request_quota.jsonl", "observations": "driver_observations.jsonl",
                    "manifest": "driver_manifest.json"}}
            _write_json(output / "smoke_result.json", result)
            observations.append("driver_finished", passed=result["passed"],
                                status=receipt.get("status"))
            return result
    finally:
        if base_adapter is not None:
            await base_adapter.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline-dry-run", action="store_true",
                      help="run deterministic scripted responses; this is the default")
    mode.add_argument("--live", action="store_true",
                      help="make the single authorized GLM subscription run")
    parser.add_argument("--credentials-file", type=Path,
                        help="explicit GLM subscription env file; read only with --live")
    parser.add_argument("--out", type=Path, required=True,
                        help="new output directory; existing paths are refused")
    args = parser.parse_args()
    if args.live and args.credentials_file is None:
        parser.error("--live requires --credentials-file")
    if not args.live and args.credentials_file is not None:
        parser.error("offline mode does not accept or read --credentials-file")
    output = args.out.resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"--out already exists: {output}")
    try:
        result = asyncio.run(run_smoke(output, live=args.live,
                                       credentials_file=args.credentials_file))
    except BaseException as error:
        failure = {"schema_version": 1, "passed": False,
            "mode": "live" if args.live else "offline_dry_run",
            "failure_stage": "driver", "exception_type":
                f"{type(error).__module__}.{type(error).__qualname__}",
            "detail": "Inspect durable runtime and driver evidence; no automatic rerun was attempted."}
        _write_json(output / "smoke_result.json", failure)
        print(json.dumps(failure, ensure_ascii=False), flush=True)
        return 1
    print(json.dumps({"passed": result["passed"], "mode": result["mode"],
        "status": result["receipt"]["status"],
        "model_calls": result["receipt"]["model_calls"],
        "tool_calls": result["receipt"]["tool_calls"],
        "output": str(output)}, ensure_ascii=False), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
