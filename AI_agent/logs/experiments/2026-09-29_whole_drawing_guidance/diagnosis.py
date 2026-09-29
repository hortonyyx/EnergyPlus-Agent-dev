"""Reproduce the offline checks behind the whole-drawing guidance diagnosis (0 model calls).

Reads only saved public streams, requests and receipts of earlier runs and writes
diagnosis_checks.json next to this file.
"""
import glob
import gzip
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
GOOD, SAME_REQUEST_LATER = "2026-09-27_sm21_whole_building_repeat_claude_run58", "2026-09-28_sm21_historical_tree_run81"
RUN_DIRS = {int(m.group(1)): Path(d) for d in glob.glob(str(EXPERIMENTS / "*run[0-9]*"))
            if (m := re.search(r"run(\d+)$", d))}


def events(run):
    with gzip.open(EXPERIMENTS / run / "agent_stream.jsonl.gz", "rt") as stream:
        for line in stream:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def init_event(run):
    event = next(e for e in events(run) if e.get("type") == "system" and e.get("subtype") == "init")
    return {k: v for k, v in event.items() if k not in {"cwd", "session_id", "uuid", "memory_paths",
                                                        "messaging_socket_path"}}


def api_calls(run):
    """One row per API response: total context tokens and the tool uses it issued."""
    calls, by_id = [], {}
    for event in events(run):
        if event.get("type") != "assistant":
            continue
        message = event["message"]
        usage = message.get("usage", {})
        if message["id"] not in by_id:
            by_id[message["id"]] = dict(context=usage.get("input_tokens", 0)
                                        + usage.get("cache_creation_input_tokens", 0)
                                        + usage.get("cache_read_input_tokens", 0), uses=[])
            calls.append(by_id[message["id"]])
        by_id[message["id"]]["uses"] += [(block["name"].replace("mcp__bim__", ""), block.get("input") or {})
                                          for block in message.get("content", []) if block.get("type") == "tool_use"]
    return calls


def full_plan_view_cost(run):
    """Context increase after the first turn that viewed exactly the full 1F and 2F plans."""
    calls = api_calls(run)
    for current, following in zip(calls, calls[1:]):
        names = sorted(u[1].get("name") for u in current["uses"] if u[0] == "view_image" and not u[1].get("box"))
        if names == ["1f_view.png", "2f_view.png"] and len(current["uses"]) == 2:
            return following["context"] - current["context"]
    return None


def thinking_per_call(number):
    run = RUN_DIRS[number]
    receipt = json.loads((run / "agent_receipt.json").read_text())
    usage = (receipt.get("result") or {}).get("usage") or {}
    thinking = (usage.get("output_tokens_details") or {}).get("thinking_tokens")
    calls = len(api_calls(run.name))
    return dict(run=number, api_calls=calls, thinking_tokens=thinking,
                thinking_per_call=round(thinking / calls) if thinking and calls else None)


def main():
    good, later = init_event(GOOD), init_event(SAME_REQUEST_LATER)
    request_good = json.loads((EXPERIMENTS / GOOD / "agent_request.json").read_text())
    request_later = json.loads((EXPERIMENTS / SAME_REQUEST_LATER / "agent_request.json").read_text())
    report = dict(
        model_calls=0,
        same_request_bytes_run58_run81=(request_good["prompt"] == request_later["prompt"]
                                        and request_good["system_prompt"] == request_later["system_prompt"]),
        init_event_identical_except_session_fields=good == later,
        init_event_run58=good,
        full_plan_view_context_increase={run: full_plan_view_cost(run) for run in (
            "2026-09-26_sm21_whole_building_claude_run57", GOOD, SAME_REQUEST_LATER)},
        thinking_per_call=[thinking_per_call(n) for n in (53, 54, 55, 56, 57, 58, 59, 61, 62,
                                                          69, 71, 73, 74, 75, 79, 80, 81, 83, 84, 86, 87)],
        interpretation=("Identical client-side request, init configuration and image token cost; the change is in "
                        "which references the model reads and how many steps it takes before the first build."),
    )
    (HERE / "diagnosis_checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps({k: report[k] for k in ("same_request_bytes_run58_run81",
                                             "init_event_identical_except_session_fields",
                                             "full_plan_view_context_increase")}, indent=1))


if __name__ == "__main__":
    main()
