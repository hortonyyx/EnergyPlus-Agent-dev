"""Score the Qwen3.8-27B sm24 probe with the same-day node-regression scorer (no model calls).

The scorer in 2026-10-04_node_regression_a1/evaluate_runtime.py is reused unchanged, pointed at this
folder's configuration. Usage is OpenAI-style here, so its adapter stays idle. The runtime's own cost
estimate (10-03 bill-derived Paratera prices, images charged twice) is copied from the receipt; it is
an estimate, not the bill.
"""
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
scorer = importlib.import_module("AI_agent.logs.experiments.2026-10-04_node_regression_a1.evaluate_runtime")
scorer.HERE = HERE
scorer.CONFIG = scorer.load(HERE / "configs/sm24_qwen27b.json")
scorer.CASES = {"sm24": "sm24_qwen27b_paratera"}


if __name__ == "__main__":
    scorer.evaluate_case("sm24")
    run = ROOT / scorer.case_config("sm24")["output"]
    receipt = json.loads((run / "receipt.json").read_text())
    output = HERE / f"evaluation_{run.name}.json"
    value = json.loads(output.read_text())
    value["usage_accounting"] = receipt.get("usage_accounting")
    output.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(value["usage_accounting"], indent=2, ensure_ascii=False, default=str)[:3000])
