"""Post-generation audit adapter: existing geometry checks plus public behavior.

No generation/repair, changed tolerance, or automatic semantic/causal judgment.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
from unittest.mock import patch

from scripts.tool_scripts.run_bim_agent import dump
from .audit import calls

HERE = Path(__file__).resolve().parent
load = lambda path: json.loads(path.read_text())


def audit(run):
    summary, receipt = load(run / "summary.json"), load(run / "agent_receipt.json")
    if not summary.get("agent_response_completed") or receipt.get("returncode") != 0 or (receipt.get("result") or {}).get("is_error"):
        dump(run / "behavior_audit.json", dict(completed=False, quality="unknown_as_completed_run",
            saved_delivery=summary.get("delivery"), instruction="Stop batch; inspect interruption. No automatic retry."))
        return
    condition, request = load(run / "experiment_condition.json"), load(run / "agent_request.json")
    assert hashlib.sha256(request["system_prompt"].encode()).hexdigest() == condition["guide_sha256"]
    assert request["effort"] == condition["effort"] and request["timeout_seconds"] == condition["timeout_seconds"]
    frozen = {**condition, "mode": "behavior_method_original_only_cold",
        "image_sha256": {k: v["sha256"] for k, v in condition["images"].items()}}
    target = HERE / f"{run.name}_frozen.json"
    if target.exists():
        assert load(target) == frozen
    else:
        dump(target, frozen)
    base = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm21_current_tools_setup.audit_run")
    with patch.object(base, "HERE", HERE):
        base.audit(run)
    importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_view_references_setup.audit_views").audit(run)
    actions = calls(run / "agent_stream.jsonl.gz")
    reports = load(run / "postrun_audit.json")
    assert reports["invocations"] == 1
    dump(run / "behavior_audit.json", dict(completed=True, candidate=reports["candidate"],
        source_model_sha256=reports["source_model_sha256"],
        reference_reads=[a for a in actions if a["tool"] == "get_bim_reference"],
        interpretation="Reference access is exposure only. Inspect object interpretation, source changes and independent result before attributing benefit.",
        semantic_review="pending_development_review_of_originals_and_object_histories",
        public_actions=actions, limits="Preserve all failures. No automated behavior score or claim that confirming values proves drawing truth."))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run.resolve())
