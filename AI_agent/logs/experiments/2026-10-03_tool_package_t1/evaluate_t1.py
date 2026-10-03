"""Evaluate T1 GLM runs with the 10-02 baseline criteria (no generation, no model calls).

Same audits as ``2026-10-02_glm_baseline/evaluate.py``: the copied GLM sm24/sm25
audits plus the unchanged 09-30 room bijection, original-image opening and 5 cm
exterior height checks, so T1 results compare directly with the 10-02 baseline.
Only normally ended runs are scored here; an interrupted run is reported as such.
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
tests = importlib.import_module(PREFIX + "2026-10-03_tool_package_t1.glm_tests")
base = tests.baseline
cross = importlib.import_module(PREFIX + "2026-09-30_instruction_fix.evaluate_cross_case")
batch, load, dump = base.batch, base.load, base.runner.dump


def evaluate(case):
    run = HERE.parent / tests.PLAN[case]
    receipt, summary = (load(run / f) for f in ("agent_receipt.json", "summary.json"))
    preflight = load(HERE / f"preflight_{case}.json")
    assert load(run / "experiment_condition.json") == preflight["conditions"]
    assert summary["subscription_invocations"] == 1
    assert receipt["actual_model"] == base.MODEL and receipt["provider"] == "glm"
    if (receipt.get("timed_out") or receipt.get("returncode") != 0 or receipt.get("routing_error")
            or not summary["agent_response_completed"]):
        raise SystemExit(f"{run.name}: not a normally ended run; diagnose the saved fallback separately")
    frozen = dict(scope=batch.SCOPE, provider="glm", image_sha256=preflight["image_sha256"])
    frozen_path = HERE / f"{run.name}_frozen.json"
    if frozen_path.exists():
        assert load(frozen_path) == frozen
    else:
        dump(frozen_path, frozen)
    inventory = None
    if case == "sm24":
        importlib.import_module(PREFIX + "2026-10-02_glm_baseline.audit_sm24").audit(run, frozen_method=frozen_path)
    elif case == "sm25":
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
    parser.add_argument("case", choices=("sm24", "sm25"))
    evaluate(parser.parse_args().case)
