"""Persist development review of run86 originals and public object histories."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text())


def summarize(run):
    assert run.name == "2026-09-28_sm21_evidence_feedback_run86"
    audit, behavior, adoption, summary = [load(run / name) for name in
        ("postrun_audit.json", "behavior_audit.json", "feedback_adoption.json", "summary.json")]
    candidate = audit["candidate"]
    source = load(run / candidate / "source_model.json")
    previous = load(run / "candidate_05/source_model.json")
    physical_keys = ("floors", "boundaries", "openings", "connections")
    physical_space = lambda s: {k: s[k] for k in ("id", "floor_id", "polygon", "height", "z_floor")}
    preserved = all(source[k] == previous[k] for k in physical_keys) and (
        [physical_space(s) for s in source["spaces"]] == [physical_space(s) for s in previous["spaces"]])
    assert preserved
    directed = load(run / "evaluation/orientation_diagnostic/original_openings.json")
    merged = []
    for floor in directed["floors"]:
        identities = defaultdict(list)
        for reference_id, ids in floor["space_identity_by_interior_point"].items():
            for sid in ids:
                identities[sid].append(reference_id)
        merged.extend(dict(floor=floor["floor_id"], source_space=sid, reference_spaces=ids)
                      for sid, ids in identities.items() if len(ids) > 1)
    assert merged == [dict(floor="F2", source_space="F2:B2", reference_spaces=["S2", "S3"])]
    frozen = load(HERE / "frozen.json")
    reference_checks = {r["topic"]: hashlib.sha256(r["returned_reference"].encode()).hexdigest() ==
                        frozen["references_sha256"][r["topic"]] for r in adoption["references"]}
    assert all(reference_checks.values())
    openings = {o["id"]: o for o in source["openings"]}
    def dimensions(oid):
        v = openings[oid]["vertices"]
        return dict(width_m=max(max(p[a] for p in v) - min(p[a] for p in v) for a in (0, 1)),
                    z_m=[min(p[2] for p in v), max(p[2] for p in v)])
    height_findings = [dict(id=oid, saved=dimensions(oid), expected_z_m=z, evidence=evidence)
        for oid, z, evidence in (
            ("F1:W_S_small", [1.5, 2.1], "South_view.png: 1500 sill, 600 window, 900 above; 1f_view.png/South_view.png width 1200mm."),
            ("F1:W_east_corridor", [1.0, 2.8], "East_view.png: 1000 sill, 1800 window, 200 above. The 0.2m head error passes the old 0.3m parameter tolerance but uses the wrong family."),
            ("F1:D_south_entry", [0, 2.1], "South_view.png: door top aligns with small-window top at 2100mm, below the 3000mm floor line."),
            ("F1:D_west_entry", [0, 2.1], "West_view.png and unchanged legacy GT: 2100mm exterior door, not full 3000mm storey."))]
    raw = audit["original_openings"]
    metrics = dict(completed=True, quality="not_restored", candidate=candidate,
        counts=audit["counts"], kinds=audit["kinds"], elapsed_seconds=summary["elapsed_seconds"],
        invocations=1, actual_model=audit["actual_models"][0], estimated_usd_not_bill=summary["estimated_cost_usd"],
        strict_partition_status=audit["strict_partition_status"],
        original_score={k: raw[k] for k in ("reference_count", "matched", "positions", "hosts", "door_connections")},
        direction_only_diagnostic={k: directed[k] for k in ("reference_count", "matched", "positions", "hosts", "door_connections")},
        merged_original_spaces=merged,
        direction_diagnostic_limit="Separate diagnosis, not replacement score; host/connection counts collapse two distinct reference rooms into F2:B2 and cannot certify fidelity.",
        actual_feedback=dict(dimensions=sum("geometry_feedback" in r["result"] for r in adoption["returned_feedback"]),
            revisions=sum("geometry_changes" in r["result"] for r in adoption["returned_feedback"]),
            located_plan_reviews=adoption["located_plan_reviews"], unit_bindings=adoption["units_bound"], pixel_bindings=adoption["pixels_bound"]),
        height_coverage=audit["height_coverage"], model_calls_for_evaluation=0)
    dump(run / "comparison_metrics.json", metrics)
    findings = [
        dict(topic="F2 south central partition omitted", actions=[30, 33, 37, 56],
             evidence="The full original and action30 crop contain the central south divider. First F2 declaration has only two south partitions and three south seeds; S2 and S3 remain merged as F2:B2 through delivery. Relation samples check outer-room separation but never the two central original rooms. Final role rationale calls B2 one room with two desks and two doors.",
             outcome="Missing wall and room identity loss, independent of coordinate direction and centimetre tolerances."),
        dict(topic="F1 small window recognized but wrong segment adopted", actions=[21, 22, 23, 43, 48],
             evidence="Initial and final W_S_small use x852..886 pixels, about0.365m, instead of the original cyan opening aroundx745..855 (label1200mm). Its z=[1,2.6] is then confirmed together with six other F1 windows using the North elevation family.",
             outcome="Inventory is present, width/location and height remain wrong; no later geometry correction."),
        dict(topic="Host correction followed by partial original correction", actions=[23, 24, 25, 26, 27],
             evidence="Host failure at P2 x1426 is first cleared by moving P2 to1463 and changing D_N3/D_S3 x1398..1463 to1388..1455 (0.698m to0.719m). Both doors then connect to middle rooms. After a further original crop, the model moves P2 west to1347; source hosts become the eastern rooms. Aperture endpoints stay unchanged and remain short/misplaced against the original. The second revision correctly reports no aperture dimension changes, while source hosts do change.",
             outcome="Useful wall/host correction occurs, but full drawing fidelity is not restored. Feedback exposure is not proof of causal benefit."),
        dict(topic="Height confirmation and harmful door revision", actions=[38, 43, 44, 48, 50, 52],
             evidence="15 windows are confirmed in two floor-wide families. F1 small/east windows require different heights. North claim boxes exclude the vertical chains; the F2 box y0..190 ends above the building. Both exterior doors are changed2.7m to3.0m after a false full-storey interpretation; originals show2.1m. All17 exterior apertures nevertheless have linked height records.",
             outcome="Four semantic height errors, including a0.2m east-window head error hidden by existing0.3m tolerance. Twelve interior door heights remain explicit assumptions."),
        dict(topic="Coordinate convention and evaluation", actions=[23, 33, 34],
             evidence="Both plans use increasing Y down the image, opposite the fixed evaluation frame; scale is15x8m with floor heights3.0/3.6m. Raw original score is6/29. A separate rigid Y reflection with unchanged reference observations/tolerances yields17/29. It still maps both original F2 central south rooms to B2.",
             outcome="Keep raw score and direction diagnostic separate. A coordinate convention cannot explain missing walls, wrong widths or heights."),
        dict(topic="Feature adoption and preserved useful work", actions=[13, 23, 25, 27, 33, 56],
             evidence="Actual plan_partition reference matches frozen content. Dimension feedback returned4times, revision geometry2times. No reconstruction/opening_review reference, explicit length quantity, profile binding or located opening review was used. Two floors,15x8m extents,29apertures,14recorded connections, floor levels and13recorded uses are preserved. Final role-only edit preserves all physical geometry.",
             outcome="No scale explosion in this sample; optional unit/location features are untested by model behavior. No causal package or stable recovery claim."),
        dict(topic="Stale source notes", actions=[52, 56],
             evidence="An unresolved note now claims exterior doors confirmed at3m, while the saved assumptions still say2.7m pending elevation confirmation.",
             outcome="Source notes remain internally contradictory despite partial replacement.")
    ]
    evidence_paths = ["agent_receipt.json", "agent_stream.jsonl.gz", "postrun_audit.json", "feedback_adoption.json",
                      "comparison_metrics.json", "evaluation/orientation_diagnostic/scope.json",
                      f"{candidate}/source_model.json", "images/1f_view.png", "images/2f_view.png",
                      "images/South_view.png", "images/East_view.png", "images/West_view.png"]
    manual = dict(completed=True, quality="not_restored", candidate=candidate,
        source_model_sha256=source["source_model_sha256"], final_role_edit_preserves_physical_geometry=preserved,
        findings=findings, exact_height_findings=height_findings, merged_original_spaces=merged,
        returned_references_match_frozen=reference_checks,
        evidence_sha256={p: digest(run / p) for p in evidence_paths},
        model_calls_by_review=0,
        interpretation="Development review of original images, public calls/results and saved source only. No hidden reasoning, repaired generation result, changed tolerance or new model invocation.")
    dump(run / "manual_review.json", manual)
    behavior["semantic_review"] = dict(file="manual_review.json", sha256=digest(run / "manual_review.json"), quality=manual["quality"])
    dump(run / "behavior_audit.json", behavior)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    summarize(parser.parse_args().run.resolve())
