"""One approved small GLM request per invocation; never retries or resumes it."""

import argparse
import asyncio
import hashlib
import json
import secrets
import time
from pathlib import Path
from types import SimpleNamespace

from src.agent_runtime.anthropic import HttpAnthropicAdapter
from src.agent_runtime.call_quota import QuotaAdapter
from src.agent_runtime.failures import ModelServiceError
from src.agent_runtime.providers import (GLM_SUBSCRIPTION_ANTHROPIC as ROUTE,
    provider_parameters, subscription_credentials)
from src.agent_runtime.store import json_bytes

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe"
ORDER = ["without", "with", "with", "without"] * 3


async def main(step, credentials):
    OUT.mkdir(exist_ok=True)
    spec = OUT / "design.json"
    if not spec.exists():
        if step != 0:
            raise ValueError("start at request zero")
        design = {"order": ORDER, "random_user_id": secrets.token_hex(16),
                  "prefix_ids": {arm: secrets.token_hex(16) for arm in ("with", "without")},
                  "rule": "Keep only if post-warmup cache fraction improves by at least 10 percentage points, with no failures. Equal/noisy results are inconclusive; do not enable.",
                  "boundary": "Two equally sized fresh prefixes avoid cross-arm cache warming; six identical requests per arm, interleaved ABBA; no whole-case inference."}
        spec.write_bytes(json_bytes(design))
    design = json.loads(spec.read_bytes())
    if not 0 <= step < 12 or (OUT / f"request_{step:02d}.json").exists():
        raise ValueError("request is outside the batch or already attempted")
    if step:
        previous = json.loads((OUT / f"result_{step-1:02d}.json").read_bytes())
        if previous["status"] != "completed":
            raise ValueError("previous service failure stops this entire batch")
    arm = ORDER[step]
    prefix = "Protocol test " + design["prefix_ids"][arm] + ". Reply only OK.\n"
    prefix += "\n".join(f"Reference {i:03d}: red green blue are colour labels; integers are exact; no action is required for this reference." for i in range(140))
    body = {"model": "glm-5.3-flash", "stream": False,
            **provider_parameters(ROUTE, output_tokens=64),
            "system": [{"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Reply OK.", "cache_control": {"type": "ephemeral"}}]}]}
    if arm == "with":
        body["metadata"] = {"user_id": design["random_user_id"]}
    wire = json_bytes(body)
    (OUT / f"request_{step:02d}.json").write_bytes(wire)
    base, key = subscription_credentials(credentials, provider=ROUTE)
    transport = HttpAnthropicAdapter(base_url=base, api_key=key)
    quota = QuotaAdapter(transport, OUT / "request_quota.jsonl", limit=12, category="a2r-stickiness")
    started = time.monotonic()
    try:
        raw = await quota.send(SimpleNamespace(body=body, wire_bytes=wire), timeout=90)
        (OUT / f"response_{step:02d}.json").write_bytes(json_bytes(raw))
        result = {"step": step, "arm": arm, "status": "completed", "usage": raw.get("usage"),
                  "stop_reason": raw.get("stop_reason"), "content": raw.get("content"),
                  "wire_sha256": hashlib.sha256(wire).hexdigest()}
    except ModelServiceError as error:
        result = {"step": step, "arm": arm, "status": "failed", "failure": error.details}
    except Exception as error:
        result = {"step": step, "arm": arm, "status": "failed", "error_type": type(error).__name__}
    finally:
        await transport.close()
    result["seconds"] = round(time.monotonic() - started, 3)
    (OUT / f"result_{step:02d}.json").write_bytes(json_bytes(result))
    print(json.dumps(result, ensure_ascii=False))
    return result["status"] == "completed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", type=int)
    parser.add_argument("--credentials-file", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(main(args.step, args.credentials_file)) else 1)
