"""Bounded request-estimator calibration: 12 attempts, no retry or fallback.

The durable counter is incremented before each external request. Every request and
response is captured by the production adapter and EventStore. Run from this worktree:

  PYTHONPATH=$PWD PYTHONDONTWRITEBYTECODE=1 TMPDIR=$PWD/.../calibration/tmp \
    python .../calibration/run_calibration.py
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
if Path.cwd().resolve() != ROOT:
    raise RuntimeError("run calibration from the assigned worktree root")
sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values
from PIL import Image, ImageDraw

from src.agent_runtime.adapter import HttpChatAdapter
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore
from src.harness_contracts import (
    InputMaterialRequirement,
    RemoteModelIdentity,
    ReturnRequirement,
    RoleDefinition,
    VersionManifest,
    VersionStamp,
)

HERE = Path(__file__).resolve().parent
PRIVATE_ENV = Path("/workspaces/EnergyPlus-Agent-dev/.env")
MAXIMUM_ATTEMPTS = 12
MODELS = ("Qwen3.8-27B", "Qwen3.8-Flash")


class NoTools:
    async def list_tools(self):
        return []

    def repeatability(self, name):
        raise KeyError(name)

    async def call_tool(self, name, arguments):
        raise AssertionError("calibration exposes no tools")

    def artifacts(self):
        return []

    def snapshot_state(self):
        return {}


def versions(model: str) -> VersionManifest:
    stamp = VersionStamp(identifier="estimation-calibration-v1")
    return VersionManifest(
        code_commit=stamp, dependency_lock=stamp, prompt=stamp,
        tool_definitions=stamp, inference_parameters=stamp, model_route=stamp,
        remote_model=RemoteModelIdentity(route_id="paratera", remote_alias=model,
                                         alias_status="unverified"),
    )


def role(limits: RunLimits) -> RoleDefinition:
    return RoleDefinition(
        role_id="estimation_calibration",
        responsibilities=("Return one fixed short calibration response.",),
        tool_whitelist=(),
        input_materials=(InputMaterialRequirement(name="calibration", media_type="text/plain"),),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="plain-text"),),
        budget=limits.ledger_limit(), read_only=True,
    )


def image_url(width: int, height: int) -> tuple[str, str]:
    # A small deterministic PNG keeps all evidence well below the delivery cap.
    picture = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(picture)
    draw.rectangle((2, 2, width - 3, height - 3), outline="black", width=2)
    draw.line((0, 0, width - 1, height - 1), fill="red", width=2)
    stream = io.BytesIO()
    picture.save(stream, format="PNG", optimize=True)
    raw = stream.getvalue()
    return "data:image/png;base64," + base64.b64encode(raw).decode(), hashlib.sha256(raw).hexdigest()


def cases():
    short = "Reply only OK. Token calibration uses a short English sentence and 中文字符 12345."
    medium = ("Summarize nothing; reply only OK. This input measures approximate token counting "
              "for building geometry, room relations, windows, doors, dimensions, evidence, and uncertainty. ") * 24
    long = ("Calibration record: level=2; object=space; source=view; status=observed; "
            "coordinates=[12.5, 18.75]; note=retain evidence and report uncertainty.\n") * 96
    for model in MODELS:
        for name, text in (("text_short", short), ("text_medium", medium), ("text_long", long)):
            yield model, name, [{"role": "user", "content": text}], None
        for name, dimensions in (("image_224", (224, 224)),
                                 ("image_896", (896, 896)),
                                 ("image_1600x1200", (1600, 1200))):
            url, sha = image_url(*dimensions)
            content = [{"type": "text", "text": "Reply only OK after receiving this synthetic calibration image."},
                       {"type": "image_url", "image_url": {"url": url}}]
            yield model, name, [{"role": "user", "content": content}], {
                "width": dimensions[0], "height": dimensions[1], "sha256": sha,
                "kind": "synthetic calibration image",
            }


def atomic_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_manifest(path: Path) -> dict:
    if path.exists():
        value = json.loads(path.read_bytes())
        if value.get("maximum_attempts") != MAXIMUM_ATTEMPTS:
            raise RuntimeError("calibration attempt ceiling changed")
        return value
    return {"schema_version": 1, "maximum_attempts": MAXIMUM_ATTEMPTS,
            "attempts_reserved": 0, "automatic_retries": 0,
            "automatic_fallback": False, "attempts": []}


async def one(adapter, model: str, name: str, messages: list[dict], index: int) -> dict:
    directory = HERE / "runs" / f"{index:02d}_{model}_{name}"
    limits = RunLimits(model_calls=1, tool_calls=1, seconds=180.0, tokens=2_000_000,
                       context_tokens=None, max_model_retries=0)
    store = EventStore(directory, run_id="stage3-estimation-calibration",
                       task_id=f"calibration-{index:02d}",
                       budget_limit=limits.ledger_limit())
    parameters = {"max_tokens": 8, "temperature": 0.0, "enable_thinking": False}
    runtime = Runtime(store=store, adapter=adapter, tools=NoTools(), role=role(limits),
                      model=model, parameters=parameters, versions=versions(model),
                      limits=limits)
    with store:
        result = await runtime.run(messages)
    response_events = [e for e in store.events if e.payload.event_type == "model_response"]
    usage = (response_events[-1].payload.usage.model_dump(mode="json")
             if response_events else {"kind": "missing", "reason": "no response event"})
    request_events = [e for e in store.events if e.payload.event_type == "adapter_request"]
    estimate = None
    if request_events:
        # Recreate only the deterministic estimate from the exact captured body.
        from src.agent_runtime.estimation import estimate_chat_request
        estimate = estimate_chat_request(store.resolve(request_events[-1].payload.final_request_body), strict=True)
        estimate = {
            "text_tokens": estimate.text_tokens,
            "image_tokens": estimate.image_tokens,
            "input_tokens_estimate": estimate.input_tokens_estimate,
            "input_tokens_upper_bound": estimate.input_tokens_upper_bound,
            "output_token_limit": estimate.output_token_limit,
            "source": estimate.source,
        }
    return {"status": result["status"], "requests_logged": len(request_events),
            "responses_logged": len(response_events), "reported_usage": usage,
            "estimate": estimate, "event_log": str((directory / "events.jsonl").relative_to(HERE))}


async def main() -> None:
    HERE.joinpath("tmp").mkdir(exist_ok=True)
    HERE.joinpath("runs").mkdir(exist_ok=True)
    manifest_path = HERE / "attempts.json"
    manifest = read_manifest(manifest_path)
    values = dotenv_values(PRIVATE_ENV, interpolate=False)
    base_url = values.get("PARATERA_BASE_URL")
    api_key = values.get("PARATERA_API_KEY")
    if not base_url or not api_key:
        raise RuntimeError("the two permitted Paratera fields are unavailable")
    adapter = HttpChatAdapter(base_url=base_url, api_key=api_key)
    try:
        all_cases = list(cases())
        for model, name, messages, image in all_cases[manifest["attempts_reserved"]:]:
            if manifest["attempts_reserved"] >= MAXIMUM_ATTEMPTS:
                break
            index = manifest["attempts_reserved"] + 1
            row = {"index": index, "model": model, "case": name, "image": image,
                   "state": "reserved_before_external_request"}
            manifest["attempts"].append(row)
            manifest["attempts_reserved"] = index
            atomic_json(manifest_path, manifest)
            try:
                row["result"] = await one(adapter, model, name, messages, index)
                row["state"] = "finished"
            except Exception as error:
                # No exception text: provider messages can contain request details.
                row["state"] = "failed_without_retry"
                row["error_type"] = type(error).__name__
            atomic_json(manifest_path, manifest)
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
