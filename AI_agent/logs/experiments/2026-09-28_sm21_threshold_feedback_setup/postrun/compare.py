"""Summarize the completed pair from preserved evaluation artifacts only."""
import argparse
from collections import Counter
import json
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
load = lambda path: json.loads(path.read_text())


def arm(run):
    summary = load(run / "summary.json")
    receipt = load(run / "agent_receipt.json")
    assert summary["agent_response_completed"] and receipt["returncode"] == 0
    assert not receipt.get("timed_out") and not receipt.get("routing_error")
    assert not receipt["result"]["is_error"]
    audit = load(run / "postrun_audit.json")
    source = load(run / audit["candidate"] / "source_model.json")
    identity = load(run / "room_identity_audit.json")
    browser = load(run / "browser_qa/report.json")
    names = load(run / "browser_qa/room_types.json")
    assert browser["status"] == names["status"] == "pass"
    assert browser["source_sha256"] == names["source_sha256"] == audit["source_model_sha256"]
    assert identity["candidate"] == audit["candidate"]
    original = audit["original_openings"]
    feedback = audit["threshold_feedback"]
    parsed = feedback["parsed_replies"]
    parsed_ids = {row["profile_id"] for row in parsed}
    profile_uses = []
    for line in (run / "tools.jsonl").read_text().splitlines():
        row = json.loads(line)
        data = row.get("data", {})
        result = data.get("result", {})
        if row["action"] == "view_pixel_profile" and result.get("profile_id") in parsed_ids:
            profile_uses.append({k: result.get(k) for k in
                ("profile_id", "name", "axis", "box_original_pixels", "rgb", "minimum_count")})
    opening_diagnostic = load(run / "evaluation/gt/final_opening_diagnostic.json")
    return dict(run=run.name, variant=feedback["variant"], candidate=audit["candidate"],
        source_model_sha256=audit["source_model_sha256"], completed=True,
        actual_model=receipt["actual_model"], invocations=audit["invocations"],
        elapsed_seconds=audit["elapsed_seconds"],
        estimated_usd_not_subscription_bill=audit["estimated_usd_not_bill"],
        candidate_budget=audit["candidate_budget"], counts=audit["counts"], kinds=audit["kinds"],
        room_roles=dict(Counter(space["role"] for space in source["spaces"])),
        structured_room_use=audit["room_use"]["summary"],
        matched_rooms=audit["matched_spaces"], room_identity_findings=audit["space_identity_findings"],
        room_seed_collisions=identity["reference_room_collisions"],
        unresolved_room_seeds=identity["unresolved_reference_room_seeds"],
        strict_partition_status=audit["strict_partition_status"],
        boundary_findings=audit["topology_findings"],
        openings={k: original[k] for k in ("reference_count", "matched", "positions", "hosts", "door_connections")},
        hosts_with_distinct_room_identity=identity["hosts_with_distinct_reference_room_identity"],
        connections_with_distinct_room_identity=identity["connections_with_distinct_reference_room_identity"],
        opening_position_failures=[row for row in original["comparisons"] if not row["position_match"]],
        exterior_parameters_within_existing_tolerance=audit["exterior_parameters_match"],
        exterior_height_differences=[row for row in opening_diagnostic["matched"]
            if any(delta > 1e-6 for delta in row["z_endpoint_delta_m"])],
        height_coverage=audit["height_coverage"],
        profile_replies=len(parsed),
        actual_profile_uses=profile_uses,
        profile_unparsed_or_failed_calls=feedback["unparsed_or_failed_calls"],
        replies_with_positive_excluded_support=sum(
            (row.get("excluded_coordinates") or 0) > 0 or
            (row.get("cross_axis_excluded_coordinates") or 0) > 0 for row in parsed),
        source_display_replay_exact=audit["source_display_replay_exact"],
        input_and_producer_hashes_verified=audit["input_and_producer_hashes_verified"],
        browser_status=browser["status"],
        tools=audit["tools"], manual_review="manual_review.json")


def compare(legacy, current):
    frozen = [load(HERE / f"{run.name}_frozen.json") for run in (legacy, current)]
    assert [item["variant"] for item in frozen] == ["legacy", "current"]
    common = [{k: v for k, v in item.items() if k != "variant"} for item in frozen]
    assert common[0] == common[1], "The pair's frozen conditions differ"
    rows = [arm(run) for run in (legacy, current)]
    assert [row["variant"] for row in rows] == ["legacy", "current"]
    assert sum(row["invocations"] for row in rows) == 2
    report = dict(status="two_authorized_invocations_completed", same_frozen_conditions_except_variant=True,
        same_actual_model=rows[0]["actual_model"] == rows[1]["actual_model"],
        model_calls_for_evaluation=0, arms=rows,
        limits=["One sample per arm does not establish stability or causal improvement.",
            "Feedback delivery is not evidence that the model understood or used it.",
            "Raw partition and opening tolerances are unchanged; semantic height-family differences are preserved separately.",
            "Original/GT evaluation and developer review were not sent to the generator.",
            "No EnergyPlus run or user acceptance."])
    (HERE / "pair_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "arms"}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("legacy", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    compare(args.legacy.resolve(), args.current.resolve())
