"""Per-request and overhead figures for the new-runtime legs, read from events.jsonl (no model calls).

Input per request = uncached input + cache reads (+ cache writes); cache share = cache reads / input.
Model time = adapter_request -> model_response; tool time = tool_invocation -> tool_execution;
base overhead = run span (first to last event) - model time - tool time. Same definitions as the
second full review (Opus section 5.1), so the 10-04 figures (14.5-23.3%) are comparable.
Usage: python metrics.py <run dir> [...]
"""
from datetime import datetime
import json
from pathlib import Path
import sys


def ts(event):
    value = event["occurred_at"]
    value = value["value"] if isinstance(value, dict) else value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def usage_numbers(raw):
    if "prompt_tokens" in raw:  # OpenAI-compatible
        cached = (raw.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        return raw["prompt_tokens"], cached, raw.get("completion_tokens", 0)
    cached = raw.get("cache_read_input_tokens") or 0
    total = raw.get("input_tokens", 0) + cached + (raw.get("cache_creation_input_tokens") or 0)
    return total, cached, raw.get("output_tokens", 0)


def measure(run):
    events = [json.loads(line) for line in (run / "events.jsonl").open()]
    by_id = {e["event_id"]: e for e in events}
    model = tool = 0.0
    inputs, cached, outputs = [], 0, 0
    starts = {}
    for e in events:
        p = e["payload"]
        kind = p["event_type"]
        if kind == "model_response":
            request = by_id.get(p["request_event_id"])
            if request:
                model += ts(e) - ts(request)
            usage = p.get("usage") or {}
            if usage.get("kind") == "reported":
                i, c, o = usage_numbers(usage["raw_usage"])
                inputs.append(i)
                cached += c
                outputs += o
        elif kind == "tool_invocation":
            starts[p["call_id"]] = ts(e)
        elif kind == "tool_execution" and p["call_id"] in starts:
            tool += ts(e) - starts.pop(p["call_id"])
    span = ts(events[-1]) - ts(events[0])
    total_in = sum(inputs)
    return dict(run=run.name, requests=len(inputs), span_s=round(span),
                mean_input=round(total_in / len(inputs)) if inputs else None,
                max_input=max(inputs) if inputs else None,
                cache_share=round(cached / total_in, 4) if total_in else None,
                mean_output=round(outputs / len(inputs)) if inputs else None,
                model_s=round(model), tool_s=round(tool),
                base_overhead_s=round(span - model - tool),
                base_overhead_share=round((span - model - tool) / span, 4),
                mean_model_s_per_request=round(model / len(inputs), 1) if inputs else None)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(json.dumps(measure(Path(arg)), ensure_ascii=False))
