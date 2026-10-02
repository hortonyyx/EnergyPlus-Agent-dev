"""Authorized stage-1 interface probe, at most 20 attempts across this batch.

Only a synthetic color card is sent. No whole-building task, retry, provider
fallback or delegated model is available. Credentials are never printed.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw
from src.agent.runtime_entry import execute, parser
from src.agent_runtime.store import EventStore


HERE = Path(__file__).resolve().parent


def main():
    # A separate lock serializes this one expressly authorized batch.
    (HERE / ".tmp").mkdir(exist_ok=True)
    with (HERE / ".tmp/probe.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        existing = sorted(HERE.glob("paratera_probe_*/events.jsonl"))
        previous = sum(sum(e.payload.event_type == "adapter_request" for e in EventStore.read_events(p)) for p in existing)
        if previous >= 20:
            raise RuntimeError("authorized 20-request batch is exhausted")
        inputs = HERE / "probe_inputs"
        inputs.mkdir(exist_ok=True)
        picture = Image.new("RGB", (180, 80), "white")
        draw = ImageDraw.Draw(picture)
        for x, color in ((10, "red"), (70, "green"), (130, "blue")):
            draw.rectangle((x, 15, x + 39, 64), fill=color)
        picture.save(inputs / "protocol.png")
        number = 1
        while (HERE / f"paratera_probe_{number:02d}").exists():
            number += 1
        out = HERE / f"paratera_probe_{number:02d}"
        scope = ("This is only a small interface probe, not a building task. The attached protocol.png "
            "is a synthetic color card. Inspect it, then call view_image exactly once with "
            "name=protocol.png and coordinate_grid=false. After receiving the tool image, "
            "reply in Chinese naming the three square colors from left to right and confirming "
            "receipt of the tool image. No other tool or BIM generation is needed.")
        args = parser().parse_args(["--provider", "paratera", "--model", "Qwen3.8-27B",
            "--credentials-file", "/workspaces/EnergyPlus-Agent-dev/.env",
            "--images", str(inputs), "--out", str(out), "--role", "local_observer",
            "--scope", scope, "--attach-image", "protocol.png", "--thinking",
            "--model-calls", str(min(3, 20 - previous)), "--tool-calls", "2",
            "--output-tokens", "2048", "--seconds", "180", "--tokens", "2000000"])
        receipt = asyncio.run(execute(args))
        events = EventStore.read_events(out / "events.jsonl")
        requests = [e for e in events if e.payload.event_type == "adapter_request"]
        responses = [e for e in events if e.payload.event_type == "model_response"]
        delivered = [e for e in events if e.payload.event_type == "tool_presentation"]
        summary = {"run": out.name, "status": receipt["status"],
            "attempted_requests": len(requests), "batch_attempted_requests": previous + len(requests),
            "authorized_batch_limit": 20, "raw_usage": [e.payload.usage.model_dump(mode="json") for e in responses],
            "reported_total_tokens": receipt["reported_tokens"] if receipt["usage_complete"] else None,
            "billed_usd": None, "billed_usd_status": "not reported by service",
            "thinking_kinds": [list(p.kind for p in e.payload.thinking) for e in responses],
            "requests_with_images": sum(bool(e.payload.images) for e in requests),
            "tool_results_accepted_by_service": len(delivered), "answer": receipt["answer"],
            "whole_case_calls": 0, "deepseek_calls": 0, "glm_subscription_calls": 0}
        assert summary["batch_attempted_requests"] <= 20
        (out / "probe_receipt.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
