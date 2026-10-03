"""Measure GLM-5.3-Flash thinking volume per reasoning setting on fixed migration requests.

Attempt 02 used reasoning_effort=high and averaged about 7.7k output tokens per turn, against about
1.5k per turn in the Claude Code baseline. This resends two recorded attempt-02 request bodies
unchanged except for reasoning_effort (low, omitted, high), once each, and records reasoning tokens,
finish reasons and latency. ``--dry`` prints the plan without sending. Credentials are read through
the runtime's own loader and never printed; responses are saved next to this script.
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
RUN = HERE / "runs/attempt_02_output_32000"
REQUESTS = (5, 8)  # attempt-02 requests that produced 16,612 and 12,228 output tokens at high
VARIANTS = ("low", None, "high")


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
    bodies = recorded_bodies()
    plan = []
    for number, (sha, body) in bodies.items():
        for variant in VARIANTS:
            changed = copy.deepcopy(body)
            changed.pop("reasoning_effort", None)
            if variant:
                changed["reasoning_effort"] = variant
            plan.append((number, sha, variant, changed))
    print(json.dumps([dict(request=n, recorded_body_sha256=s, reasoning_effort=v or "omitted",
                           keys=sorted(b), max_tokens=b.get("max_tokens"), messages=len(b["messages"]))
                      for n, s, v, b in plan], indent=1))
    if args.dry:
        return
    from src.agent.runtime_entry import paratera_credentials
    base_url, key = paratera_credentials(ROOT / ".env")
    endpoint = base_url.rstrip("/") + "/chat/completions"
    out = HERE / "evidence/effort_calibration"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with concurrent.futures.ThreadPoolExecutor(len(plan)) as pool:
        futures = {pool.submit(send, endpoint, key, body): (n, s, v) for n, s, v, body in plan}
        for future in concurrent.futures.as_completed(futures):
            number, sha, variant = futures[future]
            label = f"request{number:02d}_{variant or 'omitted'}"
            try:
                payload, latency = future.result()
            except Exception as exc:  # keep failures as data; no retry
                rows.append(dict(label=label, error=f"{type(exc).__name__}: {exc}"[:300]))
                continue
            (out / f"{label}.json").write_text(json.dumps(payload, ensure_ascii=False) + "\n")
            usage = payload.get("usage") or {}
            choice = (payload.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            rows.append(dict(label=label, request=number, recorded_body_sha256=sha,
                             reasoning_effort=variant or "omitted", latency_seconds=latency,
                             finish_reason=choice.get("finish_reason"),
                             prompt_tokens=usage.get("prompt_tokens"),
                             completion_tokens=usage.get("completion_tokens"),
                             reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                             cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                             tool_calls=len(message.get("tool_calls") or []), model=payload.get("model")))
    rows.sort(key=lambda r: r["label"])
    (HERE / "effort_calibration.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
