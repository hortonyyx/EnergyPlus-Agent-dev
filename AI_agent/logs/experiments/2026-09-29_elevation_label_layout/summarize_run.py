"""Post-generation interpretation/accounting of the unchanged run90 delivery."""
from collections import Counter
from datetime import datetime, timezone
import json

from PIL import Image

from .audit_run import completed
from .batch import HERE, ROOT, RUN, load, save, sha


def main():
    summary, receipt = completed()
    delivery, behavior, report = (load(RUN / n) for n in
                                 ["delivery.json", "behavior_audit.json", "postrun_audit.json"])
    report["height_coverage"] = delivery["height_coverage"]["summary"]
    save(RUN / "postrun_audit.json", report)
    assert delivery["candidate"] == "seed" and delivery["selection_origin"] == "agent_selected"
    assert not list(RUN.glob("candidate_*")) and not list((RUN / "claims").glob("claim_*.json"))
    source = load(RUN / "seed/source_model.json")
    previous_seed = load(HERE.parent / "2026-09-29_sm21_calibrated_elevation_recovery_run89/seed/source_model.json")
    assert source == previous_seed
    assert load(RUN / "source_changes.json")["sequence"] == []
    assert behavior["counts"] == dict(tool_calls=53, errors=2, original_returns=37,
                                      elevation_returns=4, paired_returns=4, calibrated_returns=4)
    assert not any(a["tool"] in {"record_claim", "revise_bim", "build_bim", "confirm_claims"}
                   for a in behavior["public_actions"])
    assert all(e["candidate"] == "seed" for e in behavior["elevation_transport"])
    assert report["original_openings"]["positions"] == report["original_openings"]["hosts"] == 29
    assert report["original_openings"]["door_connections"] == 14
    assert report["exterior_parameters_match"] == 17 and not report["height_mismatches"]
    identity = load(RUN / "room_identity_audit.json")
    assert identity["hosts_with_distinct_reference_room_identity"] == 29
    assert identity["connections_with_distinct_reference_room_identity"] == 14
    assert not identity["reference_room_collisions"] and not identity["unresolved_reference_room_seeds"]
    assert not report["space_identity_findings"]
    heights = []
    for row in source["openings"]:
        if row["kind"] != "window":
            continue
        key = row["id"]
        actual = [min(v[2] for v in row["vertices"]), max(v[2] for v in row["vertices"])]
        expected = ([4.0, 5.8] if key.startswith("F2:") else [1.5, 2.1] if key == "F1:W4"
                    else [1.0, 2.8] if key == "F1:W7" else [1.0, 2.6])
        heights.append(dict(id=key, actual_z_m=actual, original_nominal_z_m=expected,
                            delta_m=[a - b for a, b in zip(actual, expected)]))
    east = next(r for r in heights if r["id"] == "F1:W7")
    head_shortfall = -east["delta_m"][1]
    assert abs(head_shortfall - 0.194736842) < 1e-8
    other_max_error = max(abs(d) for r in heights if r["id"] != "F1:W7" for d in r["delta_m"])
    assert other_max_error < 0.013 and len(heights) == 15
    east_review = load(RUN / "elevation_reviews/review_0003.json")
    assert east_review["facade"] == "East" and east_review["reference_background"] == "grayscale_copy_original_file_unchanged"
    label = next(r for r in east_review["opening_labels"] if r["id"] == "F1:W7")
    assert label["status"] == "placed" and label["side"] == "right"
    projected = next(r for r in east_review["projected_openings"] if r["id"] == "F1:W7")
    pixel_head = min(p[1] for p in projected["pixel_vertices"])
    observed_head = 393  # Developer reads the original after generation only.
    assert 13 < pixel_head - observed_head < 14
    with Image.open(RUN / east_review["elevation_image"]) as im:
        im.crop((450, 370, 645, 520)).resize((780, 600), Image.Resampling.NEAREST).save(
            RUN / "evaluation/actual_east_detail.png")
    save(RUN / "evaluation/east_head_review.json", dict(
        actual_returned_overlay=east_review["elevation_image"], review="elevation_reviews/review_0003.json",
        original_outer_head_y=observed_head, projected_head_y=pixel_head,
        original_pixel_residual=pixel_head - observed_head,
        original_nominal_sill_head_m=east["original_nominal_z_m"], source_sill_head_m=east["actual_z_m"],
        source_head_shortfall_m=head_shortfall, label=label,
        calibration_note="Model used ground y=558; original outer wall base is about554. Pixel residual includes calibration offset; do not convert it directly into source height error.",
        crop_original_pixels=[450, 370, 645, 520], displayed_scale=4,
        scope="Post-generation developer review only; never returned to the working model."))
    relations = []
    for line in (RUN / "tools.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event["action"] == "check_source_space_relation":
            data = event["data"]
            relations.append(dict(floor=data["floor_id"], calibration=data["calibration"],
                outcomes=dict(Counter(r["consistency"] for r in data["observations"]))))
    save(RUN / "evaluation/claim_crop_audit.json", dict(status="not_exercised", rows=[], sheets=[],
        reason="No claim was created in this run; original-image returns are verified in behavior_audit.json."))
    save(RUN / "evaluation/claim_transport_audit.json", dict(status="not_exercised", image_count=0,
        actual_transport_pixels_match_saved_regions=None, reason="No claim preview was requested or returned."))
    behavior["semantic_review"] = "manual_review.json"
    save(RUN / "behavior_audit.json", behavior)
    preservation = dict(all_source_fields_unchanged=True, floors=2, spaces=14, boundaries=84,
        openings=29, connections=14, revised_candidates=0, selected_candidate="seed")
    manual = dict(reviewer="development assistant after generation, not working-model feedback",
        source_model_sha256=source["source_model_sha256"], generation_complete=True,
        complete_quality_restored=False, stable_generation_established=False,
        physical_preservation=preservation, original_window_height_review=heights,
        other_14_windows_max_nominal_endpoint_error_m=other_max_error,
        findings=[
            dict(object="F1:W7", status="existing_height_error_not_revised", actual_z_m=east["actual_z_m"],
                original_expected_z_m=east["original_nominal_z_m"], head_shortfall_m=head_shortfall,
                evidence="East lower chain is1000/1800/200mm. Call21 received the full colour original and gray reference overlay; label is at the right, clear of both head lines. A13.42px gap remains visible in the actual returned image."),
            dict(scope="decision", status="unsupported_no_revision_conclusion",
                evidence="After four seed elevation views, model checks plans then declares all heights matched and finishes seed at call53. No height claims or geometry revisions exist. Final prose again describes ordinary F1 windows as1600mm, overlooking the1800mm East opening.",
                distinction_from_run89="This run has no North-to-East formal claim binding; do not import run89's specific claim error into this trace."),
            dict(scope="display", status="delivered_but_no_observed_repair_benefit",
                evidence="All four grayscale overlays and37 clean original returns match saved pixels. Side labels and purple doors were actually delivered. Removing these display defects was insufficient in this single run; cannot infer internal perception, unique root cause or a general absence of colour effects."),
            dict(scope="calibration_and_plan_checks", status="self_corrected_f2_axis_direction", relations=relations,
                evidence="Model corrected F2 y direction after conflicting sampled relations, without changing source partitions. Two tool errors (unregistered frame, malformed observation JSON) are retained. Correct sampled plan checks do not certify elevation heights."),
            dict(scope="partition", status="unchanged_old_wall_position_offsets",
                evidence="14 room identities,29 positions/hosts and14 connections match independently. Strict2cm partition severity remains inherited F2 wall offsets about2.2–5.2cm, with no new split/merge/missing room."),
            dict(scope="coverage_and_limits", status="all29_heights_unlinked_in_this_run",
                evidence="No current height claim bindings; geometry and legacy notes preserved.12 interior door heights remain2.1m assumptions; exterior doors were not newly bound.14 roles exist but structured role_evidence remains unrecorded; porch/notch simplifications remain."),
        ],
        result_interpretation="Display package was used, but no geometry was changed and the known East head error persists. Same input/task/model conditions as run89 reduce some differences; one combined display change and uncontrolled generation do not establish causality or stability.",
        next_offline_scope="Inspect how a concrete local sill/head or dimension-chain discrepancy becomes an object-level correction and final decision. Reuse this unchanged-source counterexample; no automatic next batch or further cosmetic-only sampling.",
        evidence_sha256={str(p.relative_to(RUN)):sha(p) for p in [
            RUN/"agent_receipt.json", RUN/"experiment_condition.json", RUN/"seed/source_model.json",
            RUN/"elevation_reviews/review_0003.json", RUN/east_review["elevation_image"], RUN/"images/East_view.png",
            RUN/"behavior_audit.json", RUN/"postrun_audit.json", RUN/"source_changes.json",
            RUN/"room_identity_audit.json", RUN/"browser_qa/report.json", RUN/"evaluation/east_head_review.json"]})
    save(RUN / "manual_review.json", manual)
    save(RUN / "comparison_metrics.json", dict(candidate="seed", counts=report["counts"],
        original_openings=report["original_openings"], height_coverage=delivery["height_coverage"]["summary"],
        old_tolerance_exterior_matches=17, old_tolerance_exterior_total=17,
        unresolved_semantic_height_errors=["F1:W7"], source_head_shortfall_m=head_shortfall,
        complete_quality_restored=False, actual_mode="saved_candidate_recovery",
        strict_partition_status=report["strict_partition_status"], physical_geometry_preservation=preservation,
        calibrated_tool_returns=4, audit_model_calls=0, manual_review_sha256=sha(RUN/"manual_review.json")))
    save(HERE / "execution_receipt.json", dict(completed=True, primary_invocations=1, local_model_invocations=0,
        actual_model=receipt["actual_model"], effort="medium", elapsed_seconds=summary["elapsed_seconds"],
        revised_candidates=0, selected_candidate="seed", estimated_usd_not_bill=summary["estimated_cost_usd"],
        usage=receipt["result"]["usage"], model_usage=receipt["result"]["modelUsage"], automatic_retry=False,
        continuation_rounds=0, paid_api_or_fallback=False, receipt_sha256=sha(RUN/"agent_receipt.json")))
    config = load(HERE.parent / "2026-09-29_calibrated_elevation_review/quality_runs.json")
    assert len(config["runs"]) == 30
    config["scope"] = "31 saved records including run90 display-package review; all prior failures and interrupted/unknown outcomes preserved."
    config["runs"].append(dict(case="sm21", condition="侧面编号与灰底橙窗紫门（保存稿复核）", run=str(RUN.relative_to(ROOT)),
        feature_count=dict(file="behavior_audit.json", path=["counts", "calibrated_returns"], name="calibrated_elevation_returns"),
        notes=["四次新叠图确实送达，原保存稿未改，东窗顶仍低约19.5厘米；完整质量未恢复。",
               "原图位置/宿主29/29、连接14/14；旧宽容差17/17不能证明高度语义正确，无新增高度claims。",
               "与run89同六原图/保存稿/任务/模型配置，仅改显示包；单次复核不证明因果、冷启动或稳定恢复。"]))
    save(HERE / "quality_runs.json", config)
    save(HERE / "postrun_verification.json", dict(status="complete", model_calls=1, audit_model_calls=0,
        reused_targeted_checks=16, producer_and_44_frozen_execution_files_verified=True,
        real_original_and_elevation_transport_verified=True, claim_transport="not_exercised_no_claims",
        offline_browser="pass", generation_outcome="unchanged_seed_east_head_still_low",
        stable_quality=False, pending_new_batch=False, manual_review_sha256=sha(RUN/"manual_review.json")))
    save(HERE / "batch_status.json", dict(state="closed", completed=True, user_approval="启动",
        closed_at_utc=datetime.now(timezone.utc).isoformat(), run=RUN.name, actual_model=receipt["actual_model"],
        primary_invocations=1, automatic_retry=False, additional_batch_approved=False, complete_quality_restored=False))
    print(dict(completed=True, source_hash=source["source_model_sha256"], revised_candidates=0,
               remaining_error="F1:W7", head_shortfall_m=head_shortfall, historical_records=31))


if __name__ == "__main__":
    main()
