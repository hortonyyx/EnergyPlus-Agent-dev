"""Post-run audit only: preserve horizontal geometry, replay source and compare GT."""
from collections import Counter
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.execution.bim_claims import geometry_state

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-26_sm25_height_review_claude_run52"
load = lambda path: json.loads(path.read_text())


def main():
    assert (RUN / "summary.json").is_file(), "wait for generation completion"
    manifest, receipt, delivery = [load(RUN / name) for name in
                                  ("inputs.json", "agent_receipt.json", "delivery.json")]
    frozen = load(HERE / "frozen_method.json")
    assert manifest["scope"] == frozen["scope"]
    assert receipt["actual_model"].startswith("claude-sonnet-")
    assert manifest["provider"] == "claude"
    assert not manifest["input_contents"]["ground_truth_or_evaluation"]["included"]
    assert not manifest["input_contents"]["building_declaration"]["included"]
    assert digest(RUN / "seed/proposal.json") == frozen["seed_proposal_sha256"]
    assert all(digest(ROOT / name) == sha for name, sha in manifest["implementation_sha256"].items())
    assert all(digest(RUN / "images" / name) == sha == manifest["images"][name]["sha256"]
               for name, sha in frozen["image_sha256"].items())
    candidate = delivery["candidate"]
    shared = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
    source, proposal, _ = shared.replay_final(RUN, candidate)
    old_source = load(RUN / "seed/source_model.json")
    old = geometry_state(load(RUN / "seed/proposal.json"))
    new = geometry_state(proposal)
    changes = []
    for kind in ("windows", "openings"):
        before, after = [{row["id"]: row for row in geom.get(kind, [])} for geom in (old, new)]
        assert before.keys() == after.keys()
        for identity in before:
            if before[identity]["z"] != after[identity]["z"]:
                changes.append({"id": identity, "before_z": before[identity]["z"],
                                "after_z": after[identity]["z"]})
            before[identity].pop("z")
            after[identity].pop("z")
    assert old == new, "non-height proposal geometry changed"
    for key in ("floors", "spaces", "boundaries", "connections", "unbuilt_openings"):
        assert old_source[key] == source[key], f"source {key} changed"
    source_before = {row["id"]: row for row in old_source["openings"]}
    source_after = {row["id"]: row for row in source["openings"]}
    assert source_before.keys() == source_after.keys()
    for identity, row in source_before.items():
        other = source_after[identity]
        for key in ("kind", "exterior", "host_boundary_id", "space_ids", "connectivity"):
            assert row[key] == other[key]
        assert [v[:2] for v in row["vertices"]] == [v[:2] for v in other["vertices"]]

    from src.agent.execution.bim_height_coverage import height_coverage
    coverage = height_coverage(Toolkit(RUN).claims(), candidate)
    assert coverage == delivery["height_coverage"]
    assert Toolkit(RUN).input_view_status() == delivery["input_view_status"]
    assert source["source_model_sha256"] == delivery["source_model_sha256"]
    actions = [json.loads(line) for line in (RUN / "tools.jsonl").read_text().splitlines()]
    assert not any(row["action"] == "review_detail" for row in actions)
    assert len(list(RUN.glob("*_receipt.json"))) == 1

    # Generation is complete and immutable; evaluation data is first loaded here.
    from scripts.tool_scripts.evaluate_bim_agent import evaluate
    from src.agent.judge.gt import load_gt_document
    evaluation = RUN / "evaluation"
    if not (evaluation / "summary.json").exists():
        evaluate(RUN, "sm25-L_anchor", modelling_task="reconstruction",
                 reference_scope="Six original images and run51 proposal, bounded height continuation; no GT or error hints supplied.",
                 out=evaluation)
    diagnostics = {}
    for name, model in (("seed", old_source), (candidate, source)):
        partition = load(evaluation / f"{name}_partition.json")
        report = shared._opening_diagnostic(model, load_gt_document("sm25-L_anchor"), partition)
        dump(evaluation / f"{name}_opening_diagnostic.json", report)
        diagnostics[name] = {
            "matched_exterior": len(report["matched"]),
            "all_parameters_and_host_match": sum(all(row.get(field) is True for field in (
                "along_within_judge_tolerance", "width_within_judge_tolerance",
                "z_within_judge_tolerance", "host_zone_match")) for row in report["matched"]),
            "height_mismatches": [row for row in report["matched"] if row["z_within_judge_tolerance"] is False],
            "unmatched_reference": report["unmatched_reference"],
            "unmatched_built_exterior": report["unmatched_built_exterior"],
            "internal_doors_outside_GT": report["internal_openings_not_in_exterior_GT"],
            "strict_partition_status": partition["comparison"]["status"],
            "matched_spaces": partition["comparison"]["matched_count"],
        }
    finalizer = importlib.import_module("AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run")
    finalizer.finalize(RUN)
    report = dict(candidate=candidate, actual_model=receipt["actual_model"],
        elapsed_seconds=receipt["elapsed_seconds"], cli_estimate_usd=receipt["result"].get("total_cost_usd"),
        generation_status=delivery["generation_status"],
        source_display_replay_exact=True, implementation_and_input_hashes_match=True,
        horizontal_geometry_hosts_connections_preserved=True, height_changes=changes,
        counts={key: len(source[key]) for key in ("spaces", "boundaries", "openings", "connections")},
        kinds=dict(Counter(row["kind"] for row in source["openings"])),
        input_view_status=delivery["input_view_status"], height_coverage=coverage["summary"],
        claims=[{key: row[key] for key in ("id", "state", "missing_bindings")}
                for row in delivery["current_claim_state"]["claims"]],
        tools=dict(Counter(row["action"] for row in actions)), independent_GT=diagnostics,
        transported_images=load(RUN / "transport_audit.json")["image_count"],
        limits=["Bounded continuation, not cold start or autonomous topic selection.",
                "Image-linked claims are not independently certified image interpretations.",
                "Exterior GT excludes internal door placement/completeness.",
                "No independent repetition, user approval or EP run."])
    dump(RUN / "postrun_audit.json", report)
    print(json.dumps({k: report[k] for k in ("candidate", "elapsed_seconds", "height_changes", "counts", "height_coverage")}, indent=2))


if __name__ == "__main__":
    main()
