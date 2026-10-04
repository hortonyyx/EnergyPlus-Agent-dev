"""Recount Claude Code rounds as model requests (no model calls).

The CLI's ``num_turns`` counts conversation turns: it tracks the tool results (one per tool call)
plus the opening prompt, not model requests. One model response often carries thinking, text and
one or two tool calls, all under one message id in the stream. The node-regression scorers divided
by ``num_turns``, which understated Claude Code's seconds, input and output per request. This
script counts distinct assistant message ids instead and writes the corrected figures for the
C1/C2 regression leg and this regression's leg next to this script.
"""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = {
    "2026-10-04_node_regression_c2/sm24_claude_code": HERE.parent / "2026-10-04_node_regression_c2/runs/sm24_claude_code",
    "2026-10-04_node_regression_a1/sm24_claude_code": HERE / "runs/sm24_claude_code",
}


def stream(run):
    plain, packed = run / "agent_stream.jsonl", run / "agent_stream.jsonl.gz"
    lines = plain.read_text().splitlines() if plain.exists() else gzip.open(packed, "rt").read().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def recount(run):
    messages = stream(run)
    responses = {m["message"]["id"] for m in messages if m.get("type") == "assistant"}
    tool_calls = sum(1 for m in messages if m.get("type") == "assistant"
                     for block in m["message"].get("content") or [] if block.get("type") == "tool_use")
    receipt = json.loads((run / "agent_receipt.json").read_text())
    result = receipt["result"]
    usage = next(iter(result["modelUsage"].values()))
    total_in = usage["inputTokens"] + usage["cacheReadInputTokens"] + usage["cacheCreationInputTokens"]
    requests = len(responses)
    return dict(cli_num_turns=result["num_turns"], model_requests=requests, tool_calls=tool_calls,
                elapsed_seconds=receipt["elapsed_seconds"],
                seconds_per_request=round(receipt["elapsed_seconds"] / requests, 1),
                mean_input_per_request=round(total_in / requests),
                mean_output_per_request=round(usage["outputTokens"] / requests),
                cache_share=round(usage["cacheReadInputTokens"] / total_in, 4),
                tool_calls_per_request=round(tool_calls / requests, 2))


if __name__ == "__main__":
    value = {name: recount(run) for name, run in RUNS.items()}
    (HERE / "claude_code_rounds_recount.json").write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value, indent=2))
