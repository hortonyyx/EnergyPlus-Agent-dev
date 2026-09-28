"""Offline diagnosis of run82's saved intermediate model, never a completed run.

Keep the failed receipt and completion verdict intact. No model invocation,
repair, tolerance change, or claim about what a completed continuation would do.
"""
import importlib
import json
from pathlib import Path
from unittest.mock import patch

from scripts.tool_scripts.run_bim_agent import digest, dump
from .audit import calls, extent

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "2026-09-28_sm21_behavior_cold_run82"
load = lambda path: json.loads(path.read_text())


def main():
    run = RUN
    summary, receipt, condition, manifest, delivery, request = [load(run / name) for name in
        ("summary.json", "agent_receipt.json", "experiment_condition.json", "inputs.json", "delivery.json", "agent_request.json")]
    assert summary["agent_response_completed"] is False
    assert receipt["returncode"] == 1 and receipt["result"]["api_error_status"] == 429
    assert summary["subscription_invocations"] == len(list(run.glob("*_receipt.json"))) == 1
    assert delivery["selection_origin"] == "latest_saved_fallback_not_agent_selected"
    assert request["effort"] == condition["effort"] == "medium"
    assert request["timeout_seconds"] == condition["timeout_seconds"] == 3000
    import hashlib
    assert hashlib.sha256(request["system_prompt"].encode()).hexdigest() == condition["guide_sha256"]
    assert manifest["scope"] == condition["scope"]
    assert manifest["continuation_rounds"] == 0 and manifest["max_candidates"] == 24
    assert not manifest["input_contents"]["ground_truth_or_evaluation"]["included"]
    assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
    assert not manifest["input_contents"]["building_declaration"]["included"]
    for name, row in condition["images"].items():
        assert digest(run / "images" / name) == row["sha256"] == manifest["images"][name]["sha256"]
    for name, sha in manifest["implementation_sha256"].items():
        assert digest(run / "runtime_snapshot" / name) == sha

    archive = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_continuation_setup.audit_run")
    transports = archive.archive_streams(run)
    actions = calls(run / "agent_stream.jsonl.gz")
    assert not any(a["tool"] in {"review_detail", "finish_bim"} for a in actions)
    shared = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
    candidate = delivery["candidate"]
    source, _, _ = shared.replay_final(run, candidate)
    assemblies = shared.replay_assemblies(run, manifest)
    original = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original")
    original.audit(run)

    # These checks describe the saved intermediate geometry, not final quality.
    from scripts.tool_scripts.evaluate_bim_agent import evaluate
    from src.agent.judge.gt import load_gt_document
    evaluation = run / "evaluation/gt"
    if not (evaluation / "summary.json").exists():
        evaluate(run, "sm21_anchor", modelling_task="reconstruction",
            reference_scope="Interrupted original-only run. Evaluate saved intermediate candidates only; no final response or autonomous acceptance. GT first loaded after the 429 stop.",
            out=evaluation)
    partition = load(evaluation / f"{candidate}_partition.json")
    legacy = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings")
    openings = legacy.diagnostic(source, load_gt_document("sm21_anchor"), partition)
    dump(evaluation / "intermediate_opening_diagnostic.json", openings)
    # The historical adapter requires at least one claim preview. This run was
    # interrupted before any claim; only that absent branch is not applicable.
    claim_tools = {"record_claim", "view_claim_evidence", "replace_claim_sources"}
    assert not any(a["tool"] in claim_tools for a in actions)
    assert not list((run / "claims").glob("claim_*.json"))
    def no_claim_previews(path):
        assert path == run
        dump(run / "evaluation/claim_crop_audit.json", dict(status="not_applicable", rows=[],
            reason="Interrupted before any claim request or saved claim; no claim previews to check."))
        dump(run / "evaluation/claim_transport_audit.json", dict(status="not_applicable", image_count=0,
            reason="No claim requests; this is not a transport pass for claims."))
    claim_module = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_claim_regions_setup.claim_crops")
    with patch.object(claim_module, "audit", no_claim_previews):
        importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_view_references_setup.audit_views").audit(run)

    drafts = []
    for path in sorted(run.glob("plan_drafts/*/plan.json")):
        try:
            plan = load(path)
        except ValueError as error:
            drafts.append(dict(draft=path.parent.name, sha256=digest(path), parse_error=str(error)))
        else:
            drafts.append(dict(draft=path.parent.name, sha256=digest(path), plan=plan))
    versions = []
    for path in sorted(run.glob("candidate_*/source_model.json")):
        model = load(path)
        versions.append(dict(candidate=path.parent.name, source_model_sha256=model["source_model_sha256"],
            counts={k: len(model[k]) for k in ("floors", "spaces", "openings", "connections")},
            openings=[dict(id=o["id"], extent=extent(o), host=o["host_boundary_id"], spaces=o["space_ids"]) for o in model["openings"]]))
    dump(run / "interrupted_object_history.json", dict(public_actions=actions, drafts=drafts, versions=versions,
        status="interrupted_intermediate_observations_only", hidden_reasoning_read=False))
    result = dict(status="interrupted_429", completed_run_quality="unknown", candidate=candidate,
        selection_origin=delivery["selection_origin"], actual_model=receipt["actual_model"],
        invocations=1, elapsed_seconds=summary["elapsed_seconds"],
        estimated_usd_not_subscription_bill=summary["estimated_cost_usd"],
        input_and_producer_hashes_verified=True, source_display_replay_exact=True,
        assemblies_replayed=assemblies, transported_images=sum(r["image_count"] for r in transports),
        counts={k: len(source[k]) for k in ("floors", "spaces", "boundaries", "openings", "connections")},
        reference_reads=[a for a in actions if a["tool"] == "get_bim_reference"],
        intermediate_original_openings=load(run / "evaluation/original_openings.json"),
        intermediate_partition=partition["comparison"], topology_findings=partition["topology_findings"],
        intermediate_exterior_parameters_match=sum(all(r.get(k) is True for k in
            ("along_within_judge_tolerance", "width_within_judge_tolerance", "z_within_judge_tolerance")) for r in openings["matched"]),
        limits=["429 occurred before claims or final review. Do not infer the model would have left these errors after completion.",
                "No finished run, method success/failure rate, new baseline, or causal comparison.",
                "Developer observations describe saved states and observable requests/results only."])
    dump(run / "interrupted_audit.json", result)
    print(json.dumps({k:result[k] for k in ("status", "completed_run_quality", "candidate", "counts", "intermediate_exterior_parameters_match")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
