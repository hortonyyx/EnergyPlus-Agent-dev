"""Reproduce bounded development review of run84's saved public evidence."""
import gzip
import hashlib
import importlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "2026-09-28_sm21_dimension_first_run84"
load = lambda path: json.loads(path.read_text())


def main():
    report = load(RUN / "postrun_audit.json")
    assert report["counts"]["spaces"] == 14 and report["counts"]["openings"] == 28
    assert not report["space_identity_findings"]
    actions = load(RUN / "behavior_audit.json")["public_actions"]
    requests, returns = {}, {}
    with gzip.open(RUN / "agent_stream.jsonl.gz", "rt") as stream:
        for line in stream:
            parts = json.loads(line).get("message", {}).get("content", [])
            for part in parts if isinstance(parts, list) else []:
                if part.get("type") == "tool_use" and part["id"] not in requests:
                    requests[part["id"]] = len(requests) + 1
                elif part.get("type") == "tool_result" and part.get("tool_use_id") in requests:
                    ordinal = requests[part["tool_use_id"]]
                    if ordinal in (26, 28, 29, 32):
                        returns[ordinal] = [json.loads(p["text"]) for p in part.get("content", []) if p.get("type") == "text"]
    small_window = next(row for row in returns[26][0]["runs"] if row["pixels"] == [745, 854])
    drafts = [(p.parent.name, load(p)) for p in sorted(RUN.glob("plan_drafts/*/plan.json"))]
    f1 = [(name, plan) for name, plan in drafts if plan["floor_id"] == "F1"]
    assert all(len([o for o in plan["openings"] if o["kind"] == "window"]) == 6 for _, plan in f1)
    original = report["original_openings"]
    assert original["floors"][0]["unmatched_reference"] == ["S-W"]
    revision = load(RUN / "plan_revisions/revision_001.json")
    broadened = [r for r in revision["changes"] if r["id"] in ("D_room2_corr", "D_room5_corr")]
    assert all(r["before"]["p1"][0] == 975 and r["after"]["p1"][0] == 892 for r in broadened)
    assert all(r["after"]["p2"][0] == 1065 for r in broadened)
    widths = dict(before_m=90 * 15 / 1392, after_m=173 * 15 / 1392,
                  original_reference_m=84 * 15 / 1391)
    physical = importlib.import_module("AI_agent.logs.experiments.2026-09-28_behavior_resume.review_saved").physical
    assert physical(load(RUN / "candidate_05/source_model.json")) == physical(load(RUN / "candidate_06/source_model.json"))
    final = load(RUN / "candidate_06/source_model.json")
    assert not report["height_mismatches"]
    assert not list(RUN.glob("plan_drafts/*/measurement_bindings.json"))
    findings = [
        dict(topic="F1 south small window", first_declaration_action=32, measured_at_action=26,
             outcome="omitted_from_first_declaration_and_all_saved_versions",
             public_return=small_window,
             evidence="Original 1f_view.png and evaluation-only original_reference identify S-W at x745..855. Action26 already returned cyan support x745..854; the first F1 declaration lists six windows and omits this one. Every later F1 draft retains six. Height checks and confirmations operate on existing objects and do not recover the omission.",
             limit="Returned support is evidence available to the model, not proof that it recognized the object. No hidden reasoning was inspected."),
        dict(topic="F1 door correction after host error", actions=[32, 33, 34],
             outcome="successful_compile_but_two_doors_broadened_incorrectly", changes=broadened, widths=widths,
             evidence="The failure concerns D_room1_corr crossing a partition. After inspecting the draft, the model changes five doors while preserving all partitions. D_room2_corr and D_room5_corr expand from x975..1065 to x892..1065 (about0.970m to1.864m, versus original0.906m). Original jamb spans are x922..1006; both the initial and revised spans are misplaced, with final endpoint error about0.6205m. No new original-view/profile call intervenes between draft inspection and revision. Tool success does not establish a faithful correction."),
        dict(topic="Plan coordinates and saved extent", actions=[32, 55, 64, 65],
             outcome="coordinate_discrepancies_survive_inspection",
             evidence="F1 corridor boundaries stay at y600/800 pixels, while original reference centerlines are624/810; this causes about0.263/0.109m perpendicular opening displacement. F2 y-anchor331.75 is assigned8m, but the footprint starts at347, so saved depth is7.835m despite a stated15x8m footprint. These are inspectable numeric discrepancies; no automatic snapping or compiler rewrite caused them.",
             limit="Outer face versus centerline convention also contributes some smaller offsets; not every strict2cm finding is an object error."),
        dict(topic="Successful space and height behaviors", actions=[55, 62, 63, 66, 69, 79, 84, 88],
             outcome="source_room_identity_preserved_and_existing_exterior_heights_repaired",
             evidence="The initial F2 declaration includes the north divider aroundx1120 and two distinct doors, preserving both rooms. Elevation rereading drives actual F1/F2 window height updates and F2 ceiling3.6m before assembly; assembly places F2 atz3m and its doors at3..5.1m. Existing16 exterior apertures match the legacy diagnostic parameters; the missing17th is retained as missing. Final role/note edit preserves all physical geometry.",
             limit="16/16 existing matches is not17/17 completeness. Source relation checks corroborate the declared separation; they do not independently discover missed objects."),
        dict(topic="Method exposure and optional measurement binding", actions=[2],
             outcome="reference_received_but_whole_method_package_not_validated",
             evidence="Actual reconstruction reference hash matches frozenB. Public requests still use manual numeric plan declarations after pixel profiles, with no view_pixel_profile or measurement bindings. Annotations are used for scale and heights, while major planar coordinates and object inventory remain faulty. This is mixed behavior evidence, not a causal conclusion from tool counts.",
             limit="B changes both reference length and method emphasis. One sample cannot establish benefit, harm, stable recovery, server drift, or the separate value of the common binding feature."),
    ]
    evidence = ["agent_receipt.json", "agent_stream.jsonl.gz", "postrun_audit.json", "comparison_metrics.json",
        "candidate_06/source_model.json", "plan_revisions/revision_001.json", "images/1f_view.png", "images/2f_view.png"]
    result = dict(completed=True, quality="not_restored_missing_window_and_plan_geometry_errors",
        candidate=report["candidate"], source_model_sha256=report["source_model_sha256"],
        final_role_edit_preserves_physical_geometry=True, findings=findings,
        public_result_excerpts={str(k): v for k,v in returns.items()},
        evidence_sha256={name: hashlib.sha256((RUN / name).read_bytes()).hexdigest() for name in evidence},
        model_calls_by_review=0, interpretation="Development-side original/result review after generation; no GT feedback, repair, threshold changes or hidden reasoning.")
    (RUN / "manual_review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    public = load(RUN / "behavior_audit.json")
    public["semantic_review"] = "completed; see manual_review.json; quality not restored"
    (RUN / "behavior_audit.json").write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(quality=result["quality"], findings=len(findings), model_calls=0)))


if __name__ == "__main__":
    main()
