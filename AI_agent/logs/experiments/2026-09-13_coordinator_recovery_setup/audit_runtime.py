"""Post-run usage accounting; never supplied to the generating model."""
import argparse
import json
from pathlib import Path


def audit(run):
    rows = []
    models = {}
    for path in sorted(run.glob("*_receipt.json")):
        receipt = json.loads(path.read_text())
        result = receipt.get("result", {})
        rows.append({"receipt": path.name, "requested_model": receipt.get("requested_model"),
                     "actual_model": receipt.get("actual_model"), "readonly": receipt.get("readonly"),
                     "elapsed_seconds": receipt.get("elapsed_seconds"), "effort": receipt.get("effort"),
                     "timed_out": receipt.get("timed_out", False), "is_error": result.get("is_error"),
                     "estimated_cost_usd": result.get("total_cost_usd"),
                     "model_usage": result.get("modelUsage", {})})
        for model, usage in result.get("modelUsage", {}).items():
            total = models.setdefault(model, {})
            for key in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD"):
                if isinstance(usage.get(key), (int, float)):
                    total[key] = total.get(key, 0) + usage[key]
    parent = next((row for row in rows if row["receipt"] == "agent_receipt.json"), {})
    workers = [row for row in rows if row["receipt"].startswith("detail_")]
    wall = parent.get("elapsed_seconds")
    worker_time = sum(row.get("elapsed_seconds") or 0 for row in workers)
    result = {"mode": "post_generation_receipt_accounting", "invocations": rows,
              "model_usage_summed_once_per_receipt": models,
              "parent_elapsed_including_worker_seconds": wall,
              "serial_worker_elapsed_seconds": worker_time,
              "parent_elapsed_excluding_worker_seconds": round(wall - worker_time, 2) if wall is not None else None,
              "limits": ["CLI estimates are not subscription bills.",
                         "Parent elapsed includes serial workers; do not add it to worker elapsed as total wall time.",
                         "Parent elapsed minus worker duration also includes tool/startup/IO overhead; it is not pure model inference time.",
                         "Each CLI modelUsage may contain auxiliary model calls, counted once here; worker receipts are separate invocations.",
                         "Missing result/modelUsage on an interrupted invocation means usage is incomplete."]}
    (run / "runtime_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run)
