"""Evaluate a developer reconstruction with the same geometry criteria as the work-model runs.

The work-model audits also check subscription receipts, which developer runs do not have;
everything else is reused unchanged: exact source replay, GT partition comparison, exterior
opening heights against the legacy GT (strict 5 cm), and the original-image positions,
hosts, door connections and room bijection (sm21: audit_original + evaluate.py;
sm24/sm25: the cross-case audits). Run with PYTHONPATH at this worktree root.
"""
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(HERE.parents[3]))
P = "AI_agent.logs.experiments."
load = lambda path: json.loads(Path(path).read_text())
GT = {"sm21": "sm21_anchor", "sm24": "sm24_anchor", "sm25": "sm25-L_anchor"}


def evaluate(case):
    run = EXP / f"2026-10-01_opus_dev_{case}"
    shared = importlib.import_module(P + "2026-09-26_sm25_multifloor_setup.audit_run")
    from scripts.tool_scripts.evaluate_bim_agent import evaluate as gt_evaluate
    from src.agent.judge.gt import load_gt_document
    delivery = load(run / "delivery.json")
    candidate = delivery["candidate"]
    source, _, _ = shared.replay_final(run, candidate)
    assert source["source_model_sha256"] == delivery["source_model_sha256"]
    assemblies = shared.replay_assemblies(run, load(run / "inputs.json"))
    out = run / "evaluation/gt"
    if not (out / "summary.json").exists():
        gt_evaluate(run, GT[case], modelling_task="reconstruction",
                    reference_scope="Developer reconstruction from the six/five original images; GT loaded only after delivery.",
                    out=out)
    partition = load(out / f"{candidate}_partition.json")
    strict = partition["comparison"]
    result = dict(case=case, run=run.name, candidate=candidate, assemblies_replayed=len(assemblies),
                  counts={k: len(source[k]) for k in ("floors", "spaces", "openings", "connections")},
                  strict_partition=strict["status"],
                  partition_findings=[dict(code=f["code"], refs=f.get("reference_ids"), cands=f.get("candidate_ids"),
                                           hausdorff=(f.get("match") or {}).get("boundary_hausdorff_m"))
                                      for f in strict["findings"]])
    if case == "sm21":
        legacy = importlib.import_module(P + "2026-09-26_sm21_whole_building_setup.audit_legacy_openings")
        diagnostic = legacy.diagnostic(source, load_gt_document(GT[case]), partition)
        (out / "final_opening_diagnostic.json").write_text(json.dumps(diagnostic, ensure_ascii=False, indent=1))
        original = importlib.import_module(P + "2026-09-26_sm21_whole_building_setup.audit_original")
        original.audit(run)
        report = load(run / "evaluation/original_openings.json")
        fix = importlib.import_module(P + "2026-09-30_instruction_fix.evaluate")
        heights = fix.strict_heights(run)
        result.update(spaces_one_to_one=fix.spaces_one_to_one(report, source)["pass_"],
                      original_openings={k: report.get(k) for k in ("reference_count", "matched", "positions", "hosts", "door_connections")},
                      position_misses=[c for c in report.get("comparisons", []) if not (c["position_match"] and c["host_match"])],
                      strict_heights={k: heights[k] for k in heights if k not in ("all",)})
    else:
        cross = importlib.import_module(P + "2026-09-30_instruction_fix.evaluate_cross_case")
        inventory = None
        if case == "sm24":
            original = importlib.import_module(P + "2026-09-23_sm24_cold_plan_setup.audit_run")
            original.audit(run)
            plan_partition = load(run / "evaluation/partition.json")
            diagnostic = shared._opening_diagnostic(source, load_gt_document(GT[case]), plan_partition)
            (run / "evaluation/exterior_opening_diagnostic.json").write_text(json.dumps(diagnostic, ensure_ascii=False, indent=1))
        else:
            diagnostic = shared._opening_diagnostic(source, load_gt_document(GT[case]), partition)
            (run / "evaluation/final_opening_diagnostic.json").write_text(json.dumps(diagnostic, ensure_ascii=False, indent=1))
            full = importlib.import_module(P + "2026-09-27_sm25_full_inventory_setup.audit_inventory")
            inventory = full.audit(run, load(full.HERE / "original_reference.json"), output=run / "evaluation/original_inventory")
        assessed = cross.assess_saved(run, case, inventory=inventory)
        heights = assessed["strict_heights"]
        result.update(spaces_one_to_one=assessed["spaces_one_to_one"]["pass_"],
                      room_findings=assessed["spaces_one_to_one"]["findings"],
                      original_openings={k: v for k, v in assessed["original_openings"].items()},
                      strict_heights={k: heights[k] for k in heights if k != "all"})
    (run / "dev_evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return result


if __name__ == "__main__":
    print(json.dumps(evaluate(sys.argv[1]), ensure_ascii=False, indent=1)[:5000])
