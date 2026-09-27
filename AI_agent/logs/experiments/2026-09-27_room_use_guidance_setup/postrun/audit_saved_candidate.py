"""Inspect run76's saved fallback after quota interruption; no completed-run score."""
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.evaluate_bim_agent import evaluate
from scripts.tool_scripts.run_bim_agent import dump
from src.agent.judge.gt import load_gt_document


def main():
    run = Path(__file__).resolve().parents[2] / "2026-09-27_sm21_use_guidance_after_run76"
    load = lambda name: json.loads((run / name).read_text())
    summary, delivery = load("summary.json"), load("delivery.json")
    assert not summary["agent_response_completed"]
    assert summary["delivery"]["selection_origin"] == "latest_saved_fallback_not_agent_selected"
    assert load("postrun_audit.json")["input_and_producer_hashes_verified"]
    candidate = delivery["candidate"]
    shared = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
    source, _, _ = shared.replay_final(run, candidate)
    assemblies = shared.replay_assemblies(run, load("inputs.json"))
    target = run / "evaluation/gt"
    if not (target / "summary.json").exists():
        evaluate(run, "sm21_anchor", modelling_task="reconstruction",
                 reference_scope="Post-interruption diagnostic of saved artifacts only; not an agent-selected final delivery.", out=target)
    partition = json.loads((target / f"{candidate}_partition.json").read_text())
    legacy = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings")
    openings = legacy.diagnostic(source, load_gt_document("sm21_anchor"), partition)
    dump(target / "final_opening_diagnostic.json", openings)
    importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original").audit(run)
    importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_view_references_setup.audit_views").audit(run)
    original = load("evaluation/original_openings.json")
    report = dict(status="interrupted_saved_candidate_diagnostic_only", candidate=candidate,
        source_model_sha256=source["source_model_sha256"], source_display_replay_exact=True,
        assemblies_replayed=assemblies,
        counts={key: len(source[key]) for key in ("floors", "spaces", "openings", "connections")},
        original_openings={key: original[key] for key in ("reference_count", "matched", "positions", "hosts", "door_connections")},
        strict_partition_status=partition["comparison"]["status"],
        partition_findings=partition["comparison"]["findings"],
        missing_exterior=openings["unmatched_reference"],
        height_mismatches=[r for r in openings["matched"] if not r["z_within_judge_tolerance"]],
        room_use=delivery["room_use_review"], height_coverage=delivery["height_coverage"]["summary"],
        limits=["A 429 quota interruption prevented final model selection and completion.",
                "These saved-artifact measurements must not enter the completed before/after quality comparison.",
                "No recovery, regeneration, candidate substitution, input changes, or model calls."])
    dump(run / "saved_candidate_audit.json", report)
    print(json.dumps({k: report[k] for k in ("status", "candidate", "counts", "original_openings", "strict_partition_status")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
