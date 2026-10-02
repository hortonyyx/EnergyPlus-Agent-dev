"""Measure text returned by tools to the working model, per run (from the public stream)."""
import gzip, json, sys
from collections import Counter
from pathlib import Path

def stream(run):
    p = run / "agent_stream.jsonl.gz"
    return gzip.open(p, "rt") if p.exists() else (run / "agent_stream.jsonl").open()

def measure(run):
    names, per_tool, calls, biggest, truncated, images = {}, Counter(), Counter(), (0, ""), 0, 0
    first_build_chars, seen_build, total = None, False, 0
    usage_in = []
    for line in stream(run):
        e = json.loads(line)
        if e.get("type") == "assistant":
            u = e["message"].get("usage") or {}
            usage_in.append(u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0))
            for c in e["message"]["content"]:
                if c.get("type") == "tool_use":
                    names[c["id"]] = c["name"].replace("mcp__bim__", "")
        if e.get("type") == "user":
            for c in e["message"]["content"]:
                if c.get("type") != "tool_result":
                    continue
                tool = names.get(c["tool_use_id"], "?")
                calls[tool] += 1
                parts = c["content"] if isinstance(c["content"], list) else [{"type": "text", "text": c["content"]}]
                size = 0
                for part in parts:
                    if part.get("type") == "text":
                        size += len(part["text"])
                        truncated += "OUTPUT TRUNCATED" in part["text"]
                    elif part.get("type") == "image":
                        images += 1
                per_tool[tool] += size
                total += size
                if size > biggest[0]:
                    biggest = (size, tool)
                if tool in ("build_plan_bim", "build_bim") and not seen_build:
                    seen_build = True
                    first_build_chars = total
    return dict(run=run.name[-5:], tool_text_chars=total, images_returned=images, truncated_results=truncated,
                largest_result=biggest, peak_context_tokens=max(usage_in) if usage_in else None,
                top=[(k, v, calls[k]) for k, v in per_tool.most_common(5)])

for name in sys.argv[1:]:
    print(json.dumps(measure(Path(name))))
