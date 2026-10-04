"""Score the Claude Code leg with T1's unchanged scorer, pointed at this folder (no model calls).

Also reports the per-round figures used to compare what the model sees: rounds, mean input per
round (input + cache read + cache creation), cache-read share, mean output and mean seconds per round,
taken from the CLI receipt.
"""
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
importlib.import_module(f"AI_agent.logs.experiments.{HERE.name}.claude_code")  # repoints the T1 launcher here
t1_eval = importlib.import_module("AI_agent.logs.experiments.2026-10-03_tool_package_t1.evaluate_t1")
t1_eval.HERE = HERE


def per_round(run):
    receipt = json.loads((run / "agent_receipt.json").read_text())
    result = receipt.get("result") or {}
    usage = next(iter((result.get("modelUsage") or {}).values()), {})
    rounds = result.get("num_turns") or 0
    total_in = usage.get("inputTokens", 0) + usage.get("cacheReadInputTokens", 0) + usage.get("cacheCreationInputTokens", 0)
    return dict(elapsed_seconds=receipt.get("elapsed_seconds"), rounds=rounds,
                mean_input_per_round=round(total_in / rounds) if rounds else None,
                cache_share=round(usage.get("cacheReadInputTokens", 0) / total_in, 4) if total_in else None,
                mean_output_per_round=round(usage.get("outputTokens", 0) / rounds) if rounds else None,
                seconds_per_round=round(receipt["elapsed_seconds"] / rounds, 1) if rounds else None,
                cli_estimate_usd=result.get("total_cost_usd"), model_usage=usage)


if __name__ == "__main__":
    case = sys.argv[1]
    run = HERE.parent / t1_eval.tests.PLAN[case]
    t1_eval.evaluate(case)
    figures = per_round(run)
    (HERE / f"evaluation_{run.name}_rounds.json").write_text(json.dumps(figures, indent=2) + "\n")
    print(json.dumps(figures, indent=2))
