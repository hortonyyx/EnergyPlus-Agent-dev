"""Does reasoning_effort change GLM-5.3-Flash thinking volume on the Coding Plan (subscription) endpoint?

Subscription attempt 01 on the new runtime averaged several times the Claude Code baseline's output per
round, with the same subscription. The new runtime sends no reasoning control (service default); Claude
Code sent effort=medium through the Anthropic-compatible endpoint, mapping unknown. Zhipu's model page
documents reasoning_effort (recommending max) and says thinking cannot be disabled.

This resends two recorded attempt-01 request bodies unchanged except for reasoning_effort, and records
output/reasoning tokens, finish reason and latency. Omitted and low are sent twice to gauge resend noise.
Run only when no whole-case run is active on the subscription. ``--dry`` prints the plan without sending.
Credentials come from the runtime's own subscription loader and are never printed; no retry.
"""
import argparse
import concurrent.futures
import copy
import json
from pathlib import Path
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
RUN = HERE / "runs/subscription_01"
REQUESTS = (3, 4)  # attempt-01 requests that produced 6,430 and 8,655 output tokens with no control
VARIANTS = (None, None, "low", "low", "medium", "high")


def recorded_bodies():
    events = [json.loads(line) for line in (RUN / "events.jsonl").read_text().splitlines()]
    requests = [e for e in events if e["payload"].get("event_type") == "adapter_request"]
    bodies = {}
    for number in REQUESTS:
        blob = requests[number - 1]["payload"]["final_request_body"]["blob"]
        bodies[number] = (blob["sha256"], json.loads((RUN / blob["uri"]).read_text()))
    return bodies


def send(endpoint, key, body):
    request = urllib.request.Request(endpoint, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=900) as response:
        payload = json.loads(response.read())
    return payload, round(time.monotonic() - started, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    plan = []
    for number, (sha, body) in recorded_bodies().items():
        seen = {}
        for variant in VARIANTS:
            seen[variant] = seen.get(variant, 0) + 1
            changed = copy.deepcopy(body)
            assert "reasoning_effort" not in changed and "thinking" not in changed
            if variant:
                changed["reasoning_effort"] = variant
            plan.append((number, sha, f"{variant or 'omitted'}_{seen[variant]}", variant, changed))
    print(json.dumps([dict(request=n, recorded_body_sha256=s, label=l, keys=sorted(b),
                           max_tokens=b.get("max_tokens"), messages=len(b["messages"]))
                      for n, s, l, _, b in plan], indent=1))
    if args.dry:
        return
    from src.agent_runtime.providers import subscription_credentials
    base_url, key = subscription_credentials()
    endpoint = base_url.rstrip("/") + "/chat/completions"
    out = HERE / "evidence/subscription_effort_calibration"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        futures = {pool.submit(send, endpoint, key, body): (n, s, l, v) for n, s, l, v, body in plan}
        for future in concurrent.futures.as_completed(futures):
            number, sha, label, variant = futures[future]
            name = f"request{number:02d}_{label}"
            try:
                payload, latency = future.result()
            except Exception as exc:  # keep failures as data; no retry
                rows.append(dict(label=name, reasoning_effort=variant or "omitted", error=f"{type(exc).__name__}: {exc}"[:300]))
                continue
            (out / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False) + "\n")
            usage = payload.get("usage") or {}
            choice = (payload.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            rows.append(dict(label=name, request=number, recorded_body_sha256=sha,
                             reasoning_effort=variant or "omitted", latency_seconds=latency,
                             finish_reason=choice.get("finish_reason"),
                             prompt_tokens=usage.get("prompt_tokens"),
                             completion_tokens=usage.get("completion_tokens"),
                             reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                             cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                             tool_calls=len(message.get("tool_calls") or []), model=payload.get("model")))
    rows.sort(key=lambda r: r["label"])
    (HERE / "subscription_effort_calibration.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
