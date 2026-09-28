"""Read only public call metadata; never display or analyze reasoning blocks."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import time


def status(run):
    stream = run / "agent_stream.jsonl"
    if not stream.exists():
        stream = stream.with_suffix(".jsonl.gz")
    calls, model = {}, None
    opener = gzip.open if stream.suffix == ".gz" else open
    if stream.exists():
        with opener(stream, "rt") as events:
            for line in events:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue  # The current public event may still be being written.
                if event.get("type") == "system" and event.get("subtype") == "init":
                    model = event.get("model")
                parts = event.get("message", {}).get("content", [])
                for part in parts if isinstance(parts, list) else []:
                    if part.get("type") == "tool_use" and part["id"] not in calls:
                        calls[part["id"]] = dict(tool=part["name"].removeprefix("mcp__bim__"),
                            topic=part.get("input", {}).get("topic"))
    rows = list(calls.values())
    counts = Counter(row["tool"] for row in rows)
    request = run / "agent_request.json"
    result = dict(run=run.name, actual_model=model, elapsed_since_request_s=round(time.time()-request.stat().st_mtime)
        if request.exists() else None, public_calls=len(rows), tools=dict(counts),
        references=[row["topic"] for row in rows if row["tool"] == "get_bim_reference"],
        last_tools=[row["tool"] for row in rows[-4:]],
        saved_candidates=len(list(run.glob("candidate_*/source_model.json"))),
        summary_saved=(run / "summary.json").exists())
    receipt = run / "agent_receipt.json"
    if receipt.exists():
        saved = json.loads(receipt.read_text())
        result["receipt"] = {key:saved.get(key) for key in ("actual_model", "returncode", "timed_out", "elapsed_seconds")}
        result["receipt"]["is_error"] = saved.get("result", {}).get("is_error")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    print(json.dumps(status(parser.parse_args().run), ensure_ascii=False))
