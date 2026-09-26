"""Independent cold-run checks after the model exits; references never feed generation."""
from collections import Counter
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, dump
from src.agent.execution.bim_height_coverage import height_coverage

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "2026-09-26_sm21_whole_building_claude_run57"
load = lambda path: json.loads(path.read_text())


def main():
    assert (RUN / "summary.json").is_file(), "wait for generation completion"
    shared = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
    manifest, receipt, delivery = [load(RUN / name) for name in
                                  ("inputs.json", "agent_receipt.json", "delivery.json")]
    shared.verify_inputs(RUN, load(HERE / "frozen_method.json"), manifest, cold=True)
    candidate = delivery["candidate"]
    assert receipt["actual_model"].startswith("claude-sonnet-")
    source, _, _ = shared.replay_final(RUN, candidate)
    assemblies = shared.replay_assemblies(RUN, manifest)
    toolkit = Toolkit(RUN)
    assert source["source_model_sha256"] == delivery["source_model_sha256"]
    assert height_coverage(toolkit.claims(), candidate) == delivery["height_coverage"]
    assert toolkit.input_view_status() == delivery["input_view_status"]
    actions = [json.loads(line) for line in (RUN / "tools.jsonl").read_text().splitlines()]
    assert not any(row["action"] == "review_detail" for row in actions)
    assert len(list(RUN.glob("*_receipt.json"))) == 1
    from scripts.tool_scripts.evaluate_bim_agent import evaluate
    from src.agent.judge.gt import load_gt_document
    evaluation = RUN / "evaluation" / "gt"
    if not (evaluation / "summary.json").exists():
        evaluate(RUN, "sm21_anchor", modelling_task="reconstruction",
                 reference_scope="Six original images only, no saved plan/calibration/BIM or error hints; GT loaded only after generation.",
                 out=evaluation)
    partition = load(evaluation / f"{candidate}_partition.json")
    legacy = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings")
    openings = legacy.diagnostic(source, load_gt_document("sm21_anchor"), partition)
    dump(evaluation / "final_opening_diagnostic.json", openings)
    strict = partition["comparison"]
    identity_codes = {"source_space_split", "source_spaces_merged", "missing_source_space",
                      "extra_source_space", "floor_assignment_changed", "candidate_spaces_overlap"}
    report = dict(candidate=candidate, actual_model=receipt["actual_model"],
        elapsed_seconds=receipt["elapsed_seconds"], cli_estimate_usd=receipt["result"].get("total_cost_usd"),
        generation_status=delivery["generation_status"], source_display_replay_exact=True,
        implementation_and_input_hashes_match=True, assemblies_replayed=assemblies,
        counts={key: len(source[key]) for key in ("floors", "spaces", "boundaries", "openings", "connections")},
        kinds=dict(Counter(row["kind"] for row in source["openings"])),
        input_view_status=delivery["input_view_status"], height_coverage=delivery["height_coverage"]["summary"],
        claims=[{key: row[key] for key in ("id", "state", "missing_bindings")}
                for row in delivery["current_claim_state"]["claims"]],
        tools=dict(Counter(row["action"] for row in actions)),
        strict_partition_status=strict["status"], matched_spaces=strict["matched_count"],
        space_identity_findings=[row for row in strict["findings"] if row["code"] in identity_codes],
        strict_partition_findings=strict["findings"], topology_findings=partition["topology_findings"],
        matched_exterior=len(openings["matched"]),
        all_parameters_match=sum(all(row.get(field) is True for field in (
            "along_within_judge_tolerance", "width_within_judge_tolerance",
            "z_within_judge_tolerance")) for row in openings["matched"]),
        height_mismatches=[row for row in openings["matched"] if row["z_within_judge_tolerance"] is False],
        unmatched_reference=openings["unmatched_reference"],
        unmatched_built_exterior=openings["unmatched_built_exterior"],
        internal_doors_outside_GT=openings["internal_openings_not_in_exterior_GT"],
        limits=["One original-only run, not repeated stability or cross-case generalization.",
                "Input access feedback plus explicit height-review task guidance were both present; no causal ablation.",
                "Claims link image evidence but do not certify interpretation.",
                "Exterior GT excludes internal door placement/completeness; no EP or human approval."])
    finalizer = importlib.import_module("AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run")
    finalizer.finalize(RUN)
    report["transported_images"] = load(RUN / "transport_audit.json")["image_count"]
    dump(RUN / "postrun_audit.json", report)
    print(json.dumps({key: report[key] for key in ("candidate", "elapsed_seconds", "counts",
        "matched_spaces", "space_identity_findings", "matched_exterior", "all_parameters_match",
        "height_mismatches", "height_coverage")}, indent=2))


if __name__ == "__main__":
    main()
