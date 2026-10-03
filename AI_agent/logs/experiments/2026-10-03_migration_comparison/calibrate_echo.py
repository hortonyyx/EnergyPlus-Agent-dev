"""Test whether echoing earlier reasoning makes GLM-5.3-Flash think longer on fixed migration requests.

The runtime resends every earlier assistant ``reasoning_content`` (attempt-02 request 8 carried about
109k characters of it). This resends two recorded attempt-02 request bodies with all earlier
``reasoning_content`` removed and nothing else changed, twice each, and records reasoning tokens.
Compare with effort_calibration.json (same bodies with the echo kept). ``--dry`` prints the plan only.
Credentials are read through the runtime's loader and never printed.
"""
import argparse
import concurrent.futures
import copy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from importlib import import_module  # noqa: E402

effort = import_module("AI_agent.logs.experiments.2026-10-03_migration_comparison.calibrate_effort")
REQUESTS = (8, 17)
SAMPLES = 2


def bodies():
    events = [json.loads(line) for line in (effort.RUN / "events.jsonl").read_text().splitlines()]
    requests = [e for e in events if e["payload"].get("event_type") == "adapter_request"]
    result = {}
    for number in REQUESTS:
        blob = requests[number - 1]["payload"]["final_request_body"]["blob"]
        body = json.loads((effort.RUN / blob["uri"]).read_text())
        stripped = copy.deepcopy(body)
        removed = 0
        for message in stripped["messages"]:
            if message.get("role") == "assistant" and "reasoning_content" in message:
                removed += len(message.pop("reasoning_content") or "")
        result[number] = (blob["sha256"], stripped, removed)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    plan = bodies()
    print(json.dumps({n: dict(recorded_body_sha256=s, removed_reasoning_chars=r,
                              reasoning_effort=b.get("reasoning_effort"), max_tokens=b.get("max_tokens"))
                      for n, (s, b, r) in plan.items()}, indent=1))
    if args.dry:
        return
    from src.agent.runtime_entry import paratera_credentials
    base_url, key = paratera_credentials(ROOT / ".env")
    endpoint = base_url.rstrip("/") + "/chat/completions"
    out = HERE / "evidence/echo_calibration"
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(n, i) for n in plan for i in range(1, SAMPLES + 1)]
    rows = []
    with concurrent.futures.ThreadPoolExecutor(len(jobs)) as pool:
        futures = {pool.submit(effort.send, endpoint, key, plan[n][1]): (n, i) for n, i in jobs}
        for future in concurrent.futures.as_completed(futures):
            number, sample = futures[future]
            label = f"request{number:02d}_no_echo_{sample}"
            try:
                payload, latency = future.result()
            except Exception as exc:  # keep failures as data; no retry
                rows.append(dict(label=label, error=f"{type(exc).__name__}: {exc}"[:300]))
                continue
            (out / f"{label}.json").write_text(json.dumps(payload, ensure_ascii=False) + "\n")
            usage = payload.get("usage") or {}
            choice = (payload.get("choices") or [{}])[0]
            rows.append(dict(label=label, request=number, recorded_body_sha256=plan[number][0],
                             removed_reasoning_chars=plan[number][2], latency_seconds=latency,
                             finish_reason=choice.get("finish_reason"),
                             prompt_tokens=usage.get("prompt_tokens"),
                             completion_tokens=usage.get("completion_tokens"),
                             reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                             tool_calls=len((choice.get("message") or {}).get("tool_calls") or [])))
    rows.sort(key=lambda r: r["label"])
    (HERE / "echo_calibration.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
