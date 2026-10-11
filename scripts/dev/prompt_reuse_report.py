"""Read-only Responses request-prefix/cache audit; no model or network access.

The journal already fingerprints the native input items actually prepared for
Responses. Matching items diagnose history changes, not provider cache eligibility.
No image bytes, credentials, model messages or reasoning contents are expanded.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


def fingerprint(capture):
    if not isinstance(capture, dict):
        return None
    if capture.get("kind") in {"json_references", "image_references"}:
        return capture.get("wire_sha256")
    if capture.get("kind") == "blob":
        return capture.get("blob", {}).get("sha256")
    if capture.get("kind") == "inline":
        raw = json.dumps(capture["value"], ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()
    return None


def counters(payload):
    usage = payload.get("usage") or {}
    raw = usage.get("raw_usage") or {}
    if usage.get("kind") != "reported":
        return None, None
    inputs = raw.get("input_tokens")
    cached = (raw.get("input_tokens_details") or {}).get("cached_tokens")
    return (inputs if type(inputs) is int else None,
            cached if type(cached) is int else None)


def analyze(events):
    rows, by_id, previous = [], {}, {}
    compactions = Counter()
    for event in events:
        payload, task = event["payload"], event["task_id"]
        kind = payload["event_type"]
        if kind == "context" and payload.get("action") == "compact":
            compactions[task] += 1
        if kind == "adapter_request":
            if payload.get("adapter") != "openai-responses-http-v1":
                raise ValueError("prompt_reuse_report supports only native Responses journals")
            items, tools = {}, None
            for injected in payload.get("injected_content", []):
                location = injected.get("request_location", "")
                match = re.fullmatch(r"/input/(\d+)", location)
                if match:
                    items[int(match[1])] = fingerprint(injected.get("content"))
                elif location == "/tools":
                    tools = fingerprint(injected.get("content"))
            complete = bool(items) and sorted(items) == list(range(len(items))) and all(items.values())
            model = ((payload.get("versions") or {}).get("remote_model") or {}).get("remote_alias")
            current = [items[index] for index in sorted(items)] if complete else None
            prior = previous.get(task)
            common = None
            same_tools = (None if prior is None or prior["tools"] is None or tools is None
                          else prior["tools"] == tools)
            if prior and prior["items"] is not None and current is not None:
                common = 0
                for old, new in zip(prior["items"], current):
                    if old != new:
                        break
                    common += 1
            row = {"event_id": event["event_id"], "task": task, "model": model,
                   "native_input_items": len(current) if current is not None else None,
                   "previous_request_event": prior["event_id"] if prior else None,
                   "identical_leading_input_items": common,
                   "same_tool_definitions": same_tools,
                   "same_model": (None if prior is None or prior["model"] is None or model is None
                                  else prior["model"] == model),
                   "response_received": False, "input_tokens": None, "cached_input_tokens": None}
            rows.append(row)
            by_id[event["event_id"]] = row
            previous[task] = {"items": current, "tools": tools, "model": model,
                              "event_id": event["event_id"]}
        elif kind == "model_response" and payload.get("request_event_id") in by_id:
            row = by_id[payload["request_event_id"]]
            row["response_received"] = True
            row["input_tokens"], row["cached_input_tokens"] = counters(payload)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["task"]].append(row)
    tasks = {}
    for task, group in grouped.items():
        complete = all(row["input_tokens"] is not None and row["cached_input_tokens"] is not None for row in group)
        inputs = sum(row["input_tokens"] or 0 for row in group)
        cached = sum(row["cached_input_tokens"] or 0 for row in group)
        tasks[task] = {"requests": len(group), "compactions": compactions[task],
            "usage_complete": complete, "input_tokens": inputs if complete else None,
            "cached_input_tokens": cached if complete else None,
            "uncached_input_tokens": inputs - cached if complete else None,
            "cache_fraction": cached / inputs if complete and inputs else None}
    return {"schema_version": 1, "protocol": "responses_v1", "tasks": tasks, "requests": rows,
        "limits": ["Input-item prefix matches are not token counts or guarantees of provider cache hits.",
            "Hidden provider instructions, routing, retention and other request settings can also affect caching.",
            "Cache tokens remain part of input/context size; absent usage is unknown, not zero.",
            "This reads journal captures without expanding or independently verifying every blob."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output exists; preserve prior evidence")
    if args.out.resolve().is_relative_to(args.run.resolve()):
        parser.error("write analysis outside the observed run")
    journal = args.run / "events.jsonl"
    data = journal.read_bytes()
    result = analyze([json.loads(line) for line in data.splitlines() if line.strip()])
    result.update(run=str(args.run.resolve()), events_sha256=hashlib.sha256(data).hexdigest())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.out.resolve()), "tasks": result["tasks"]}))


if __name__ == "__main__":
    main()
