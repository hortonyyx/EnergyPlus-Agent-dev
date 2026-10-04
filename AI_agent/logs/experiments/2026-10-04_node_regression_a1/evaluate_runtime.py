"""Score the new-runtime legs of the absorption-batch-1 node regression (no model calls).

Copied from the C1/C2 regression scorer; the only change is the usage adapter: the
Anthropic-compatible route reports input_tokens (without cache reads/writes),
cache_read_input_tokens, cache_creation_input_tokens and output_tokens instead of the
OpenAI-style prompt/completion fields, so the per-request figures are recomputed here.
The audits, the cross-case scorer and the version checks are unchanged.


Same audits as the Claude Code legs: sm24 uses the 09-23 original-image plan audit plus the typed-GT
exterior diagnostic; sm25 uses the 10-02 evaluator, the multi-floor replay, the full original-image
inventory and the GT exterior diagnostic; both finish with the unchanged 09-30 cross-case scorer.
Unlike the migration scorer this one is version-aware: the run must carry the registered Agent version
and the configured task, and the copied view records the registered implementation hashes. The runtime
now delivers by itself (T1 shared delivery), so the runtime's own delivery.json is used. The run
directory is never modified; results go next to this script.
"""
import argparse
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
PREFIX = "AI_agent.logs.experiments."
migration = importlib.import_module(PREFIX + "2026-10-03_migration_comparison.evaluate_migration")
load, dump, digest = migration.load, migration.dump, migration.digest
CONFIG = load(HERE / "configs/runtime_anthropic.json")
CASES = {"sm24": "sm24_runtime_anthropic", "sm25": "sm25_runtime_anthropic"}


def case_config(case):
    return next(c for c in CONFIG["cases"] if c["case_id"] == CASES[case])


def messages_usage(run):
    """Per-request usage in prompt/cached/completion terms for either route (None if OpenAI-style)."""
    from collections import Counter
    usage, seen = Counter(), False
    for line in (run / "events.jsonl").read_text().splitlines():
        payload = json.loads(line)["payload"]
        if payload.get("event_type") != "model_response":
            continue
        raw = (payload.get("usage") or {}).get("raw_usage") or {}
        if "input_tokens" not in raw:
            continue
        seen = True
        read, write = raw.get("cache_read_input_tokens") or 0, raw.get("cache_creation_input_tokens") or 0
        usage["prompt"] += raw.get("input_tokens", 0) + read + write
        usage["cached"] += read
        usage["cache_write"] += write
        usage["completion"] += raw.get("output_tokens", 0)
        usage["total"] += raw.get("input_tokens", 0) + read + write + raw.get("output_tokens", 0)
    return dict(usage) if seen else None


def facts(run):
    value = migration.runtime_facts(run, subscription=True)
    anthropic = messages_usage(run)
    if anthropic is not None:
        value["usage"] = {**value["usage"], **anthropic, "format": "anthropic_messages"}
        calls = value["model_calls"] or 0
        value["per_round"]["output_tokens"] = round(anthropic["completion"] / calls) if calls else None
    usage, calls = value["usage"], value["model_calls"] or 0
    value["mean_input_per_request"] = round(usage["prompt"] / calls) if calls else None
    value["cache_share"] = round(usage["cached"] / usage["prompt"], 4) if usage.get("prompt") else None
    receipt = load(run / "receipt.json")
    value["agent_version"] = receipt.get("agent_version")
    value["finalization"] = receipt.get("finalization")
    value["retries_recovered"] = [p.get("reason") for p in map(lambda e: json.loads(e)["payload"],
        (run / "events.jsonl").read_text().splitlines()) if p.get("event_type") == "run_lifecycle"
        and p.get("action") == "retry"]
    return value


def compat_view(run, target, case, value):
    from scripts.tool_scripts.run_bim_agent import Toolkit
    from src.agent_runtime.agent_registry import agent_version_record
    config = case_config(case)
    assert (run / "task.txt").read_text() == config["scope"]
    record = agent_version_record(ROOT, verify=True)
    assert value["agent_version"] == record["version_id"], (value["agent_version"], record["version_id"])
    view = target / run.name
    shutil.copytree(run / "bim", view, ignore=shutil.ignore_patterns(".harness_tmp"))
    manifest = load(view / "inputs.json")
    manifest.update(implementation_sha256={p: row["sha256"] for p, row in record["files"].items()},
                    input_contents={"ground_truth_or_evaluation": {"included": False},
                                    "building_declaration": {"included": False}},
                    evaluation_adapter_note="implementation_sha256 (registered Agent version) and input_contents "
                                            "added by the node-regression scorer; the runtime's inputs.json is unchanged")
    dump(view / "inputs.json", manifest)
    if (view / "delivery.json").exists():
        delivery = load(view / "delivery.json")
        chosen, origin = delivery["candidate"], delivery.get("selection_origin", "runtime_delivery")
    else:
        saved = sorted(view.glob("candidate_*/source_model.json"))
        if not saved:
            return view, None, "no_saved_candidate"
        chosen, origin = saved[-1].parent.name, "latest_saved_fallback_not_agent_selected"
        completed = value["status"] == "completed" and value["answer_present"]
        Toolkit(view).delivery(chosen, selection_origin=origin, generation_status=dict(
            state="completed" if completed else "interrupted", agent_response_completed=completed,
            elapsed_seconds=value["receipt_elapsed_seconds"], runtime_status=value["status"]))
    dump(view / "summary.json", dict(written_by="node-regression scorer, not the runtime",
                                     agent_response_completed=value["status"] == "completed",
                                     delivery=dict(candidate=chosen, selection_origin=origin)))
    return view, chosen, origin


def quality(view, case, chosen):
    from src.agent.judge.gt import load_gt_document
    shared = importlib.import_module(PREFIX + "2026-09-26_sm25_multifloor_setup.audit_run")
    cross = importlib.import_module(PREFIX + "2026-09-30_instruction_fix.evaluate_cross_case")
    if case == "sm24":
        importlib.import_module(PREFIX + "2026-09-23_sm24_cold_plan_setup.audit_run").audit(view)
        source, _, _ = shared.replay_final(view, chosen)
        opening = shared._opening_diagnostic(source, load_gt_document("sm24_anchor"),
                                             load(view / "evaluation/partition.json"))
        dump(view / "evaluation/exterior_opening_diagnostic.json", opening)
        return cross.assess_saved(view, "sm24")
    from scripts.tool_scripts.evaluate_bim_agent import evaluate
    evaluation = view / "evaluation"
    evaluate(view, "sm25-L_anchor", modelling_task="reconstruction",
             reference_scope="Six original images only, no saved plan/calibration/BIM or error hints; GT loaded only after generation.",
             out=evaluation)
    source, _, _ = shared.replay_final(view, chosen)
    partition = load(evaluation / f"{chosen}_partition.json")
    dump(evaluation / "final_opening_diagnostic.json",
         shared._opening_diagnostic(source, load_gt_document("sm25-L_anchor"), partition))
    full = importlib.import_module(PREFIX + "2026-09-27_sm25_full_inventory_setup.audit_inventory")
    inventory = full.audit(view, load(full.HERE / "original_reference.json"), output=evaluation / "original_inventory")
    result = cross.assess_saved(view, "sm25", inventory=inventory)
    result["strict_partition"] = {k: partition["comparison"][k] for k in ("status", "matched_count")}
    return result


def evaluate_case(case):
    run = ROOT / case_config(case)["output"]
    value = facts(run)
    with tempfile.TemporaryDirectory(prefix="node-regression-eval-") as tmp:
        view, chosen, origin = compat_view(run, Path(tmp), case, value)
        result = None
        if chosen:
            result = quality(view, case, chosen)
            evidence = HERE / "evaluation" / run.name
            evidence.mkdir(parents=True, exist_ok=True)
            for path in sorted((view / "evaluation").glob("*.json")):
                shutil.copyfile(path, evidence / path.name)
    output = dict(case=case, run=str(run.relative_to(ROOT)), delivered_candidate=chosen, selection_origin=origin,
                  runtime=value, quality=result)
    dump(HERE / f"evaluation_{run.name}.json", output)
    print(json.dumps({k: v for k, v in output.items() if k != "quality"} | {"quality": result and {
        k: result[k] for k in ("counts", "spaces_one_to_one", "original_openings", "strict_heights")}},
        ensure_ascii=False, indent=2, default=str)[:6000])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=tuple(CASES))
    evaluate_case(parser.parse_args().case)
