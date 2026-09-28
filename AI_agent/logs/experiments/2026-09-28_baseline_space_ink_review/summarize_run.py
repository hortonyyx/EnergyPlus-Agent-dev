"""Persist run87 development review without changing its geometry or scores."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from batch import HERE, RUN, load, save, sha


def main():
    summary, receipt, audit, behavior = [load(RUN / p) for p in
        ("summary.json", "agent_receipt.json", "postrun_audit.json", "behavior_audit.json")]
    assert summary["agent_response_completed"] and receipt["returncode"] == 0
    assert not receipt["result"].get("is_error") and summary["subscription_invocations"] == 1
    assert summary["delivery"]["candidate"] == audit["candidate"] == "candidate_06"
    sources = {i:load(RUN / f"candidate_{i:02}/source_model.json") for i in range(1,7)}
    source = sources[6]
    opening_shape = lambda s: [(o["id"], o["kind"], o["vertices"]) for o in s["openings"]]
    opening_xy = lambda s: [(o["id"], [v[:2] for v in o["vertices"]]) for o in s["openings"]]
    assert opening_shape(sources[1]) == opening_shape(sources[2])
    assert opening_xy(sources[4]) == opening_xy(sources[5])
    assert all(sources[5][k] == sources[6][k] for k in ("floors","spaces","boundaries","openings","connections"))
    identity = load(RUN / "room_identity_audit.json")
    assert not identity["reference_room_collisions"] and not identity["unresolved_reference_room_seeds"]
    assert identity["hosts_with_distinct_reference_room_identity"] == 29
    assert identity["connections_with_distinct_reference_room_identity"] == 14
    raw = audit["original_openings"]
    assert [raw[k] for k in ("reference_count","matched","positions","hosts","door_connections")] == [29,29,29,29,14]
    partition = load(RUN / "evaluation/gt/candidate_06_partition.json")
    changes = [r["match"] for r in partition["comparison"]["findings"] if r["code"] == "partition_boundary_changed"]
    assert not audit["space_identity_findings"]
    openings = {o["id"]:o for o in source["openings"]}
    height_findings = []
    for oid, expected, evidence in [
        ("F1:W4", [1.5,2.1], "South_view.png small window: sill1500mm, height600mm, upper900mm; the neighboring ordinary windows have a different 1000/1600/400 chain."),
        ("F1:W7", [1.0,2.8], "East_view.png lower window: sill1000mm, height1800mm, upper200mm; not the North facade's 1000/1600/400 family."),
    ]:
        actual = [min(p[2] for p in openings[oid]["vertices"]),max(p[2] for p in openings[oid]["vertices"])]
        height_findings.append(dict(opening_id=oid, actual_z_m=actual, original_z_m=expected,
            endpoint_error_m=[abs(a-b) for a,b in zip(actual,expected)], evidence=evidence,
            old_gt_height_tolerance_pass=(oid == "F1:W7")))
    reference_checks = {}
    guidance = RUN / "runtime_snapshot/scripts/tool_scripts/bim_agent_guidance.py"
    import ast
    namespace = {}
    # The frozen guidance contains only constants. Read its reference dictionary
    # through the syntax tree rather than importing any current producer.
    for node in ast.parse(guidance.read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "REFERENCES":
                    namespace = ast.literal_eval(node.value)
                elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id == "REFERENCES":
                    namespace[ast.literal_eval(target.slice)] = ast.literal_eval(node.value)
    assert namespace
    for row in behavior["references"]:
        reference_checks[row["topic"]] = row["reference"] == namespace[row["topic"]]
    assert all(reference_checks.values())
    tools = Counter(r["tool"] for r in behavior["public_actions"])
    failed = [r for r in behavior["public_actions"] if r.get("is_error") or r.get("returned_error")]
    feedback = behavior["returned_ink_feedback"]
    assert [(r["ordinal"],r["review"]["stroke_count"]) for r in feedback] == [(86,2),(89,2),(92,0)]
    metrics = dict(completed=True, quality="not_restored_special_window_heights_wrong",
        candidate=audit["candidate"], source_model_sha256=source["source_model_sha256"],
        actual_model=receipt["actual_model"], invocations=1, elapsed_seconds=summary["elapsed_seconds"],
        estimated_usd_not_bill=summary["estimated_cost_usd"], counts=audit["counts"], kinds=audit["kinds"],
        original_score={k:raw[k] for k in ("reference_count","matched","positions","hosts","door_connections")},
        distinct_identity_hosts=29, distinct_identity_connections=14,
        strict_partition_status=audit["strict_partition_status"], strict_partition_tolerance_m=0.02,
        partition_interpretation="14 distinct physical rooms and complete openings/connections. F2 wall offsets, not missing or extra partitions; preserve the raw severe result.",
        f2_boundary_hausdorff_range_m=[min(r["boundary_hausdorff_m"] for r in changes),max(r["boundary_hausdorff_m"] for r in changes)],
        exterior_parameters_in_existing_tolerance=f"{audit['exterior_parameters_match']}/{audit['matched_exterior']}",
        exact_height_findings=height_findings, height_coverage=audit["height_coverage"],
        feedback=dict(responses=len(feedback), image_count=sum(r["returned_review_images"] for r in feedback),
            stroke_counts=[r["review"]["stroke_count"] for r in feedback],
            correct_missing_wall_repair_demonstrated=False,
            interpretation="F1 cues concern interior workstation lines; those rooms remain intact. F2 contained all dividers before its first feedback. Corridor repair used newly requested pixel profiles of declared walls, so its benefit cannot be attributed to the new interior-ink cue."),
        behavior=dict(tool_calls=len(behavior["public_actions"]), failed_calls=len(failed),
            first_source_tool_ordinal=86, original_view_calls=tools["view_image"],
            source_elevation_view_calls=tools["view_elevation_candidate"],
            wall_path_support_calls=tools["view_plan_wall_support"]), model_calls_for_review=0)
    save(RUN / "comparison_metrics.json", metrics)
    findings = [
        dict(topic="Initial coordinate misuse caught, wrong window family substituted", actions=[84,85,86],
            evidence="First F1 declaration uses plan Y3.4..4.61 as W7 Z and is rejected outside storey0..3. The model fixes the coordinate slot but substitutes the North ordinary-window family1.0..2.6, retaining an East-window interpretation error."),
        dict(topic="Corridor false partitions actually repaired", actions=[86,87,88,89,90],
            evidence="First saved F1 has full-depth pA/pB, splitting the corridor and producing9spaces. Two new original pixel profiles show no wall in the corridor band; local revision replaces the full paths with office-band segments. F1 becomes7spaces, all15aperture geometries stay exact, corridor relation samples then agree with the original."),
        dict(topic="New automatic feedback exposed but causal repair unproven", actions=[86,89,92],
            evidence="Three returned reports and four full-room comparison images exactly match saved files and deterministic replay. Two F1 workstation/fixture lines remain flagged before/after corridor correction; the model does not turn them into walls. F2 first declaration already contains all seven rooms and has zero strokes. No public statement identifies an interior-ink cue as the reason for a missing-wall repair."),
        dict(topic="Window-family overgeneralization survives evidence confirmation", actions=[96,98,99,100,101,102,106,110,111,112],
            evidence="claim_0001 attaches all7F1windows to one North/East strip and states the family is identical on every facade. South small-window evidence is absent from that claim, and the East crop ends above the lower sill and excludes the window rectangle. All17exterior heights become image-linked despite the two semantic errors. confirm_claims first rejects the millimetre differences, then revise_bim applies the same mistaken family."),
        dict(topic="Geometry and notes preserved during final review", actions=[95,111,113,115],
            evidence="Assembly replays exactly. Height application preserves all opening XY; the final note edit preserves floors/spaces/boundaries/openings/connections exactly. Interior12door heights remain explicit2.1m assumptions. No source-elevation view was requested, although automatic plan/overlay images were returned."),
        dict(topic="Final narrative overstates cross-facade agreement", actions=[115],
            evidence="The final public answer says the elevation height chains are consistent across all four facades. Originals contradict this for the F1Southsmall and East windows. The source report remains not_evaluated; evidence linkage is not semantic confirmation."),
    ]
    evidence = ["agent_receipt.json","agent_stream.jsonl.gz","behavior_audit.json","postrun_audit.json",
        "producer_replay.json","ink_producer_replay.json","comparison_metrics.json","room_identity_audit.json",
        "evaluation/original_openings.json","evaluation/gt/candidate_06_partition.json",
        "evaluation/claim_crop_audit.json","evaluation/claim_transport_audit.json",
        "candidate_06/source_model.json","images/1f_view.png","images/2f_view.png","images/South_view.png","images/East_view.png"]
    # behavior_audit gains a link below; exclude it from the circular evidence hash.
    evidence.remove("behavior_audit.json")
    manual = dict(candidate=audit["candidate"], source_model_sha256=source["source_model_sha256"],
        quality=metrics["quality"], reviewer="Development assistant; complete original South/East elevations and both original-plan overlays inspected after generation.",
        findings=findings, exact_height_findings=height_findings,
        returned_references_match_frozen=reference_checks,
        all_apertures_preserved_by_corridor_repair=True, xy_preserved_by_height_application=True,
        all_physical_source_fields_preserved_by_note_edit=True,
        raw_strict_partition_preserved=True, direction_diagnostic_needed=False,
        evidence_sha256={p:sha(RUN / p) for p in evidence}, model_calls=0,
        limits=["One changed-condition run, not stable recovery or a causal feature ablation.",
            "No GT/old answers entered generation and no source model was repaired during review.",
            "F1East height passes existing0.3m tolerance but still uses the wrong family.",
            "No historical claim-preview images were returned; saved claim crops are developer review only."])
    save(RUN / "manual_review.json", manual)
    behavior["semantic_review"] = dict(file="manual_review.json", sha256=sha(RUN / "manual_review.json"), quality=metrics["quality"])
    save(RUN / "behavior_audit.json", behavior)
    save(HERE / "execution_receipt.json", dict(approved_frozen_sha256=load(HERE / "approval.json")["frozen_sha256"],
        run=RUN.name, actual_model=receipt["actual_model"], effort=receipt["effort"],
        returncode=receipt["returncode"], provider_result_is_error=False,
        elapsed_seconds=receipt["elapsed_seconds"], primary_invocations=1, local_invocations=0,
        auto_retries=0, continuation_rounds=0, candidate_count=6,
        estimate_usd_not_bill=summary["estimated_cost_usd"], usage=receipt["result"]["usage"],
        model_receipt_sha256=sha(RUN / "agent_receipt.json"), batch_state="completed_no_further_invocation_authorized"))
    print(json.dumps({k:metrics[k] for k in ("quality","original_score","behavior","feedback")},ensure_ascii=False))


if __name__ == "__main__":
    main()
