"""Record the developer's post-generation original-drawing review of run88."""
import json
from .audit_run import completed
from .batch import HERE, ROOT, RUN, PRIOR, load, save, sha


def main():
    summary, receipt = completed()
    report, behavior = load(RUN / "postrun_audit.json"), load(RUN / "behavior_audit.json")
    source = load(RUN / report["candidate"] / "source_model.json")
    seed = load(RUN / "seed/source_model.json")
    opening = {o["id"]: o for o in source["openings"]}
    prior_opening = {o["id"]: o for o in seed["openings"]}
    assert all(source[k] == seed[k] for k in ["floors", "spaces", "boundaries", "connections"])
    changed = [key for key in opening if opening[key] != prior_opening[key]]
    assert changed == ["F1:W4"]
    assert all(p[:2] == q[:2] for key in opening for p, q in
               zip(opening[key]["vertices"], prior_opening[key]["vertices"]))
    def z(key):
        values = [p[2] for p in opening[key]["vertices"]]
        return [min(values), max(values)]
    assert z("F1:W4") == [1.50867052, 2.098265896]
    assert z("F1:W7") == [1.007368421, 2.605263158]
    assert report["exterior_parameters_match"] == 17 and not report["height_mismatches"]
    identity = load(RUN / "room_identity_audit.json")
    assert identity["hosts_with_distinct_reference_room_identity"] == 29
    assert identity["connections_with_distinct_reference_room_identity"] == 14
    assert not identity["reference_room_collisions"] and not identity["unresolved_reference_room_seeds"]
    assert not report["space_identity_findings"]
    assert behavior["counts"] == dict(tool_calls=47, errors=6, original_returns=17, elevation_returns=6, paired_returns=6)
    behavior["semantic_review"] = "manual_review.json"
    save(RUN / "behavior_audit.json", behavior)
    delivery = load(RUN / "delivery.json")
    manual = dict(reviewer="development assistant, after generation; not the working model",
        generation_complete=True, complete_quality_restored=False, stable_generation_established=False,
        source_model_sha256=source["source_model_sha256"], mode="saved_proposal_recovery",
        physical_preservation=dict(floors=2, spaces=14, boundaries=84, connections=14,
            unchanged_openings=28, changed_opening="F1:W4", all_29_opening_xy_unchanged=True,
            all_29_hosts_unchanged=True, only_changed_physical_field="F1:W4 vertices z"),
        findings=[
            dict(object="F1:W4", status="repaired_with_minor_pixel_offsets", actual_z_m=z("F1:W4"),
                 original_expected_z_m=[1.5, 2.1], endpoint_delta_m=[0.00867052, -0.001734104],
                 evidence="South original left vertical chain: sill1500, opening600, head-to-floor900; full original and final source elevation visually reviewed.",
                 observed_behavior="Paired source/original calls13/40; own clean crops16/18 and profile23-28; corrected claim37/adopt38/revise39. Saved edit references claim-derived image-axis values."),
            dict(object="F1:W7", status="unchanged_wrong_height_family", actual_z_m=z("F1:W7"),
                 original_expected_z_m=[1.0, 2.8], head_shortfall_m=2.8-z("F1:W7")[1],
                 evidence="East original lower dimension chain is1000/1800/200, not ordinary1000/1600/400. Full original and actual source elevation checked.",
                 observed_behavior="East paired calls14/45 delivered exact full images/table. No East crop/profile/claim/revision followed. Public text aftercall45 asserted the ordinary400/1600/1000 pattern had been validated elsewhere. Viewing did not resolve the wrong cross-facade interpretation.",
                 existing_parameter_tolerance_pass=True),
            dict(scope="partition", status="unchanged_wall_position_offsets",
                 evidence="Run87 physical fields retained exactly; strict2cm score stayssevere because of F2 wall offsets about2.2-5.2cm. No missing/split/merged rooms or connection regression found."),
            dict(scope="claim narrative", status="unsupported_corroboration_retained",
                 evidence="claim0001 mentions measured936mm versus candidate1500mm while claiming door-width agreement. This inconsistent prose did not enter the z computation; source door geometry is unchanged. It is not accepted as independent corroboration."),
            dict(scope="coverage", status="partial_current_run_height_linkage",
                 evidence="Only repaired window has a current image-bound height claim. Old claims were intentionally not imported;1/29 linkage is this run's evidence scope, not a loss of28 physical openings.12 interior door heights remain2.1m explicit assumptions.")],
        result_interpretation="The paired tool was used and the salient small-window mismatch was autonomously repaired in a method-directed saved-proposal task. The East counterexample prevents a claim of complete or stable restoration; changed runtime/task and lack of a control prevent attributing causality to the tool alone.",
        next_offline_scope="Use the remaining East mismatch to test projection against caller-observed original elevation anchors, exposing actual sill/head displacement in one coordinate frame; avoid another uniform-height reminder or same-condition blind rerun. No such production overlay or new model batch is implemented/authorized here.",
        preserved_history="run87 and every prior run remain unchanged; onlyrun88 uses this saved proposal",
        audit_adapter_note="The first post-run delta script assumed every record had id; connections use opening_id. This audit-only adapter was corrected and resumed, without changing generation, reference scores or model calls.",
        evidence_sha256={str(p.relative_to(RUN)):sha(p) for p in [
            RUN / "agent_receipt.json", RUN / "experiment_condition.json", RUN / "candidate_01/source_model.json",
            RUN / "candidate_01/operations.json", RUN / "candidate_01/elevation_South.png",
            RUN / "candidate_01/elevation_East.png", RUN / "images/South_view.png", RUN / "images/East_view.png",
            RUN / "claims/claim_0001.json", RUN / "source_changes.json", RUN / "behavior_audit.json",
            RUN / "postrun_audit.json", RUN / "room_identity_audit.json", RUN / "browser_qa/report.json",
            RUN / "evaluation/claim_transport_audit.json"]})
    save(RUN / "manual_review.json", manual)
    metrics = dict(candidate=report["candidate"], counts=report["counts"],
        original_openings=report["original_openings"], height_coverage=delivery["height_coverage"]["summary"],
        old_tolerance_exterior_matches=17, old_tolerance_exterior_total=17,
        unresolved_semantic_height_errors=["F1:W7"], complete_quality_restored=False,
        actual_mode="saved_candidate_recovery", strict_partition_status=report["strict_partition_status"],
        physical_geometry_preservation=manual["physical_preservation"], paired_tool_returns=6,
        audit_model_calls=0, manual_review_sha256=sha(RUN / "manual_review.json"))
    save(RUN / "comparison_metrics.json", metrics)
    save(HERE / "execution_receipt.json", dict(completed=True, primary_invocations=1, local_model_invocations=0,
        actual_model=receipt["actual_model"], effort="medium", elapsed_seconds=summary["elapsed_seconds"],
        candidates=1, estimated_usd_not_bill=summary["estimated_cost_usd"],
        usage=receipt["result"]["usage"], model_usage=receipt["result"]["modelUsage"],
        automatic_retry=False, continuation_rounds=0, paid_api_or_fallback=False,
        receipt_sha256=sha(RUN / "agent_receipt.json")))
    config = load(HERE.parent / "2026-09-28_baseline_space_ink_review/quality_runs.json")
    assert len(config["runs"]) == 28
    config["scope"] = "29 historical and current records; run88 is one authorized saved-proposal repair. All interrupted, failed and original fixed-frame scores remain; no pooled success or baseline adoption."
    config["runs"].append(dict(case="sm21", condition="完整立面与源立面成对复核（保存稿修复）",
        run=str(RUN.relative_to(ROOT)), feature_count=dict(file="behavior_audit.json", path=["counts", "paired_returns"], name="paired_elevation_returns"),
        notes=["仅一处小窗z修对；其余全部源物理几何保持。东窗头仍低0.195m，旧宽容差17/17不等于完整保真。",
               "六次成对反馈实际送达；方法限定保存稿修复，不是冷启动、独立重复或单变量因果证据。",
               "严格2cm分区severe保持，主要为二层2.2–5.2cm墙位差；无错拆错并或宿主/连接回退。"] ))
    save(HERE / "quality_runs.json", config)
    save(HERE / "postrun_verification.json", dict(status="complete", model_calls=1, audit_model_calls=0,
        targeted_tests_passed=9, producer_and_frozen_execution_verified=True,
        real_original_and_elevation_transport_verified=True, offline_browser="pass",
        generation_outcome="small_window_repaired_east_window_height_still_wrong", stable_quality=False,
        pending_new_batch=False, manual_review_sha256=sha(RUN / "manual_review.json")))
    print(json.dumps(dict(candidate=report["candidate"], repaired="F1:W4", remaining="F1:W7",
        complete_quality_restored=False, historical_records=29)))


if __name__ == "__main__":
    main()
