"""Evaluate the GLM baselines with the 09-30 cross-case criteria (no generation, no model calls).

Runs the copied sm24/sm25 audits (GLM receipt and provider checks only) and the
unchanged room bijection, original-image opening and 5 cm exterior height checks
from ``2026-09-30_instruction_fix/evaluate_cross_case.py``.
"""
import argparse
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
PREFIX = "AI_agent.logs.experiments."
base = importlib.import_module(PREFIX + "2026-10-02_glm_baseline.baseline")
cross = importlib.import_module(PREFIX + "2026-09-30_instruction_fix.evaluate_cross_case")
batch, load, dump = base.batch, base.load, base.runner.dump


def evaluate(run_id):
    case, name = base.PLAN[run_id]
    run = HERE.parent / name
    manifest, receipt, summary = (load(run / f) for f in ("inputs.json", "agent_receipt.json", "summary.json"))
    preflight = load(HERE / f"preflight_{run_id}.json")
    assert load(run / "experiment_condition.json") == dict(run_id=run_id, **preflight["conditions"])
    assert summary["agent_response_completed"] and summary["subscription_invocations"] == 1
    assert receipt["actual_model"] == base.MODEL and receipt["provider"] == "glm"
    assert receipt.get("returncode") == 0 and not receipt.get("timed_out")
    assert not receipt.get("routing_error") and not receipt["result"].get("is_error")
    frozen = dict(scope=batch.SCOPE, provider="glm", image_sha256=preflight["image_sha256"])
    frozen_path = HERE / f"{name}_frozen.json"
    if frozen_path.exists():
        assert load(frozen_path) == frozen
    else:
        dump(frozen_path, frozen)
    inventory = None
    if case == "sm24":
        importlib.import_module(PREFIX + "2026-10-02_glm_baseline.audit_sm24").audit(run, frozen_method=frozen_path)
    else:
        audit = importlib.import_module(PREFIX + "2026-10-02_glm_baseline.audit_sm25")
        setup = run / "evaluation_setup"
        setup.mkdir(exist_ok=True)
        dump(setup / "cold_frozen_method.json", frozen)
        with patch.object(audit, "HERE", setup), patch.object(audit, "RUN", run):
            audit.main()
        full = importlib.import_module(PREFIX + "2026-09-27_sm25_full_inventory_setup.audit_inventory")
        inventory = full.audit(run, load(full.HERE / "original_reference.json"),
                               output=run / "evaluation/original_inventory")
    result = cross.assess_saved(run, case, inventory=inventory)
    dump(run / "cross_case_evaluation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", choices=tuple(base.PLAN))
    evaluate(parser.parse_args().run)
