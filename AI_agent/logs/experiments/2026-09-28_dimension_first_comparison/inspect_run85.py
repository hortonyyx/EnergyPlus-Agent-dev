"""Preserve interrupted run85; inspect transport and saved state, not final quality."""
from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "2026-09-28_sm21_method_control_run85"
load = lambda path: json.loads(path.read_text())


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    run = RUN
    receipt, summary, delivery, condition, manifest = [load(run / name) for name in
        ("agent_receipt.json", "summary.json", "delivery.json", "experiment_condition.json", "inputs.json")]
    assert receipt["returncode"] == 1 and receipt["result"]["is_error"]
    assert receipt["result"]["api_error_status"] == 429
    assert summary["agent_response_completed"] is False and summary["subscription_invocations"] == 1
    assert delivery["selection_origin"] == "latest_saved_fallback_not_agent_selected"
    assert not manifest["input_contents"]["ground_truth_or_evaluation"]["included"]
    assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
    for name, sha in condition["implementation_sha256"].items():
        assert hashlib.sha256((run / "runtime_snapshot" / name).read_bytes()).hexdigest() == sha
    for name, row in condition["images"].items():
        assert hashlib.sha256((run / "images" / name).read_bytes()).hexdigest() == row["sha256"]
    archive = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_continuation_setup.audit_run")
    transports = archive.archive_streams(run)
    public = importlib.import_module("AI_agent.logs.experiments.2026-09-28_reconstruction_behavior.audit")
    actions = public.calls(run / "agent_stream.jsonl.gz")
    assert not any(row["tool"] in {"review_detail", "finish_bim", "record_claim", "view_claim_evidence", "replace_claim_sources"} for row in actions)
    assert not list((run / "claims").glob("claim_*.json"))
    shared = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
    source, _, _ = shared.replay_final(run, delivery["candidate"])
    assert len(source["floors"]) == 1
    assert not list((run / "plan_assemblies").glob("assembly_*.json"))

    def absent_claims(path):
        assert path == run
        dump(run / "evaluation/claim_crop_audit.json", dict(status="not_applicable", rows=[], reason="Interrupted before any claim."))
        dump(run / "evaluation/claim_transport_audit.json", dict(status="not_applicable", image_count=0, reason="No claim requests; no claim transport verdict."))

    claims = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_claim_regions_setup.claim_crops")
    with patch.object(claims, "audit", absent_claims):
        importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_view_references_setup.audit_views").audit(run)
    plan = load(run / "plan_drafts/draft_001/plan.json")
    assert plan["x_anchors"][-1][1] == 15000 and plan["y_anchors"][-1][1] == 8000
    footprint = source["floors"][0]["footprint"]
    spans = {axis: max(p[i] for p in footprint) - min(p[i] for p in footprint) for i, axis in enumerate("xy")}
    assert spans == dict(x=15000.0, y=8000.0)
    assert not list(run.glob("plan_drafts/*/measurement_bindings.json"))
    result = dict(status="interrupted_429", completed_run_quality="unknown", candidate=delivery["candidate"],
        selection_origin=delivery["selection_origin"], actual_model=receipt["actual_model"],
        elapsed_seconds=receipt["elapsed_seconds"], invocations=1,
        estimated_usd_not_bill=summary["estimated_cost_usd"],
        usage={key: receipt["result"].get("usage", {}).get(key) for key in
            ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")},
        input_and_producer_hashes_verified=True, source_display_replay_exact=True,
        source_model_sha256=source["source_model_sha256"],
        counts={key: len(source[key]) for key in ("floors", "spaces", "boundaries", "openings", "connections")},
        saved_footprint_spans_m=spans, transported_images=sum(row["image_count"] for row in transports),
        public_tool_counts=dict(Counter(row["tool"] for row in actions)),
        measurement_binding_files=[], public_actions=actions,
        intermediate_findings=[
            "First F1 declaration writes15000/8000 as world anchors in a metre-valued interface. Saved footprint is15000x8000m; ceiling remains3m. This is an actual unit error in the intermediate source, not a renderer conversion.",
            "Saved F1 has7spaces/14openings/8connections. It includes SW1_small but no east corridor window. The declaration explicitly leaves east/west inventory unverified.",
            "Saved regular F1 windows usez1.6..2.6m and SW1_small1.5..2.4m; originals show1.0..2.6m and1.5..2.1m. These intermediate heights were not confirmed or finally reviewed before interruption.",
        ],
        limits=["Only one floor was saved; no completed A result or paired method quality comparison.",
                "A 429 interruption does not establish the model would retain these errors after completion.",
                "No full-building GT score is generated for this partial state; no postrun_audit.json is created.",
                "No retry, continuation, fallback, new model call, source repair or hidden reasoning analysis."])
    dump(run / "interrupted_audit.json", result)
    dump(run / "behavior_audit.json", dict(completed=False, quality="unknown_as_completed_run",
        semantic_review="intermediate findings only; see interrupted_audit.json", public_actions=actions))
    print(json.dumps({k:result[k] for k in ("status", "completed_run_quality", "counts", "saved_footprint_spans_m", "transported_images")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
