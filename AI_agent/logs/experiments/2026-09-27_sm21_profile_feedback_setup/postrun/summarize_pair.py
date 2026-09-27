"""Summarize completed, independently audited runs; never invoke a model."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def physical_xy(source):
    return {
        "floors": {f["id"]: f["footprint"] for f in source["floors"]},
        "spaces": {s["id"]: s["polygon"] for s in source["spaces"]},
        "openings": {o["id"]: [v[:2] for v in o["vertices"]] for o in source["openings"]},
    }


def heights(source):
    return {o["id"]: sorted({v[2] for v in o["vertices"]}) for o in source["openings"]}


def main():
    exposure = load(HERE / "intervention_exposure.json")
    rows = []
    for trace in exposure["runs"]:
        run = HERE.parent / trace["run"]
        audit = load(run / "postrun_audit.json")
        final = load(run / audit["candidate"] / "source_model.json")
        assembly = audit["assemblies_replayed"][0]["candidate_replay_matches"][0]
        assembled = load(run / assembly / "source_model.json")
        before, after = heights(assembled), heights(final)
        diagnostic = load(run / "evaluation/gt/final_opening_diagnostic.json")
        browser = load(run / "browser_qa/report.json")
        names = load(run / "browser_qa/room_types.json")
        views = load(run / "evaluation/view_reference_audit.json")
        row = {
            "run": run.name, "variant": trace["variant"], "candidate": audit["candidate"],
            "counts": audit["counts"], "matched_spaces": audit["matched_spaces"],
            "space_identity_findings": audit["space_identity_findings"],
            "strict_partition_status": audit["strict_partition_status"],
            "original_openings": {k: audit["original_openings"][k] for k in
                                  ("reference_count", "matched", "positions", "hosts", "door_connections")},
            "exterior_parameters_match_within_existing_tolerance": audit["exterior_parameters_match"],
            "exterior_parameter_tolerances_m": diagnostic["tolerances_m"],
            "window_heights": {o["id"]: after[o["id"]] for o in final["openings"] if o["kind"] == "window"},
            "first_assembled_candidate": assembly,
            "assembled_to_final_xy_exact": physical_xy(assembled) == physical_xy(final),
            "assembled_to_final_height_changes": {key: {"before": before[key], "after": value}
                                                   for key, value in after.items() if before[key] != value},
            "successful_pixel_profile_replies": len(trace["successful_profiles"]),
            "received_new_profile_feedback": any(p["new_feedback_received"] for p in trace["successful_profiles"]),
            "source_display_replay_exact": audit["source_display_replay_exact"],
            "actual_view_image_count": views["image_count"],
            "actual_view_transport_exact": views["actual_transport_bytes_and_pixels_verified"],
            "offline_browser_status": browser["status"], "browser_names_colors_status": names["status"],
            "invocations": audit["invocations"], "actual_models": audit["actual_models"],
            "elapsed_seconds": audit["elapsed_seconds"], "estimated_usd_not_bill": audit["estimated_usd_not_bill"],
        }
        rows.append(row)
    report = {
        "status": "completed_not_recovered_intervention_not_exercised",
        "runs": rows,
        "primary_invocations": sum(r["invocations"] for r in rows),
        "summed_invocation_seconds_not_wall_clock": sum(r["elapsed_seconds"] for r in rows),
        "estimated_usd_not_bill": sum(r["estimated_usd_not_bill"] for r in rows),
        "same_tool_call_prefix_length": exposure["same_tool_call_prefix_length"],
        "conclusion": "Neither run restores the old baseline. Current arm never received the modified profile reply; this pair cannot establish benefit or harm from that reply, or the historical regression cause.",
        "limits": ["One independent invocation per arm, no controlled sampling seed.",
                   "Existing tolerant GT matches do not replace per-window original-elevation review.",
                   "Strict partition severity includes small offsets; identity and connectivity must be assessed separately.",
                   "All audits happen after generation, without changing submitted models or evaluation tolerances."],
    }
    (HERE / "pair_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"runs": [{k: r[k] for k in ("run", "assembled_to_final_xy_exact", "assembled_to_final_height_changes", "exterior_parameter_tolerances_m")} for r in rows]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
