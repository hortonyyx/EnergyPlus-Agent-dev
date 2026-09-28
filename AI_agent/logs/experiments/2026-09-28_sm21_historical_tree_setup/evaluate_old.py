"""Current independent evaluation, strictly after historical generation/replay."""
from collections import Counter
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "2026-09-28_sm21_historical_tree_run81"
load = lambda path: json.loads(path.read_text())


def audit():
    summary, replay, delivery = [load(RUN / name) for name in
        ("summary.json", "producer_replay.json", "delivery.json")]
    assert summary["agent_response_completed"] and replay["source_display_replay_exact"]
    candidate = delivery["candidate"]
    source = load(RUN / candidate / "source_model.json")
    assert source["source_model_sha256"] == replay["source_model_sha256"]
    from scripts.tool_scripts.evaluate_bim_agent import evaluate
    from src.agent.judge.gt import load_gt_document
    evaluation = RUN / "evaluation/gt"
    if not (evaluation / "summary.json").exists():
        evaluate(RUN, "sm21_anchor", modelling_task="reconstruction", out=evaluation,
            reference_scope="Six original images only. Unmodified historical Git tree. Current evaluation loads GT only after generation.")
    partition = load(evaluation / f"{candidate}_partition.json")
    legacy = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings")
    openings = legacy.diagnostic(source, load_gt_document("sm21_anchor"), partition)
    dump(evaluation / "final_opening_diagnostic.json", openings)
    original = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original")
    original.audit(RUN)
    original_report = load(RUN / "evaluation/original_openings.json")
    identity = importlib.import_module("AI_agent.logs.experiments.2026-09-28_sm21_threshold_feedback_setup.postrun.room_identity")
    dump(RUN / "room_identity_audit.json", identity.review(RUN))
    archive = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_continuation_setup.audit_run")
    transports = archive.archive_streams(RUN)
    strict = partition["comparison"]
    identity_codes = {"source_space_split", "source_spaces_merged", "missing_source_space",
        "extra_source_space", "floor_assignment_changed", "candidate_spaces_overlap"}
    report = dict(**replay, counts={key: len(source[key]) for key in
        ("floors", "spaces", "boundaries", "openings", "connections")},
        kinds=dict(Counter(row["kind"] for row in source["openings"])),
        room_roles=dict(Counter(row["role"] for row in source["spaces"])),
        strict_partition_status=strict["status"], matched_spaces=strict["matched_count"],
        space_identity_findings=[row for row in strict["findings"] if row["code"] in identity_codes],
        topology_findings=partition["topology_findings"], original_openings=original_report,
        matched_exterior=len(openings["matched"]),
        exterior_parameters_match=sum(all(row.get(key) is True for key in
            ("along_within_judge_tolerance", "width_within_judge_tolerance", "z_within_judge_tolerance"))
            for row in openings["matched"]),
        exterior_height_differences=[row for row in openings["matched"]
            if any(delta > 1e-6 for delta in row["z_endpoint_delta_m"])],
        height_mismatches=[row for row in openings["matched"] if not row["z_within_judge_tolerance"]],
        unmatched_reference=openings["unmatched_reference"],
        unmatched_built_exterior=openings["unmatched_built_exterior"],
        transported_images=sum(row["image_count"] for row in transports),
        limits=["One old-tree repeat does not establish stability or isolate individual changes.",
            "Original/GT references and tolerances are unchanged; evaluation never entered generation.",
            "Git does not freeze provider internals or historical Python dependencies.",
            "Coverage and model confirmation do not certify image interpretation.",
            "No EnergyPlus run or user acceptance."])
    dump(RUN / "postrun_audit.json", report)
    print(json.dumps({key: report[key] for key in ("candidate", "counts", "kinds",
        "strict_partition_status", "matched_spaces", "space_identity_findings",
        "exterior_parameters_match", "exterior_height_differences")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    audit()
