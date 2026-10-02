"""Offline sm24/sm25 evaluation entry for the pending Sonnet regressions.

Reuse existing original-image/GT audits and add the room bijection and 5 cm height
criteria. The history command reads saved audits without changing historical runs.
No generation, model calls, repairs, or approval changes occur here.
"""
import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
PREFIX = "AI_agent.logs.experiments."
batch = importlib.import_module(PREFIX + "2026-09-30_instruction_fix.batch")
load, dump = batch.load, batch.runner.dump
CASES = {"sm24": ("sm24_anchor", 1), "sm25": ("sm25-L_anchor", 2)}


def room_bijection(source, reports, references):
    """Check both directions on all reference floors, independent of generated IDs."""
    findings = []
    ordered = sorted(source["floors"], key=lambda floor: floor["z_floor"])
    if len(ordered) != len(references) or len(reports) != len(references):
        findings.append(dict(issue="floor count mismatch", expected=len(references),
                             source=len(ordered), audited=len(reports)))
    if len({row["floor_id"] for row in reports}) != len(reports):
        findings.append(dict(issue="duplicate audited floor"))
    by_floor = {row["floor_id"]: row for row in reports}
    expected_ids = {floor["id"] for floor in ordered}
    if set(by_floor) != expected_ids:
        findings.append(dict(issue="audited floors differ from source floors"))
    for floor, reference in zip(ordered, references):
        report = by_floor.get(floor["id"], {})
        mapping = report.get("space_identity_by_interior_point", {})
        if not mapping or set(mapping) != set(reference["spaces"]):
            findings.append(dict(floor=floor["id"], issue="missing or extra reference seeds"))
        holders = Counter(ids[0] for ids in mapping.values() if len(ids) == 1)
        candidates = {s["id"] for s in source["spaces"] if s["floor_id"] == floor["id"]}
        for seed, ids in mapping.items():
            if len(ids) != 1 or holders[ids[0]] != 1 or ids[0] not in candidates:
                findings.append(dict(floor=floor["id"], seed=seed, candidate_spaces=ids,
                                     issue="seed does not have its own unique source space"))
        for space in sorted(candidates - set(holders)):
            findings.append(dict(floor=floor["id"], candidate_space=space, issue="no reference seed"))
    orphaned = [s["id"] for s in source["spaces"] if s["floor_id"] not in expected_ids]
    if orphaned:
        findings.append(dict(issue="spaces on unknown floors", spaces=orphaned))
    return dict(pass_=not findings, reference_rooms=sum(len(r["spaces"]) for r in references),
                findings=findings)


def strict_heights(diagnostic, expected_count):
    rows = []
    for row in diagnostic.get("matched", []):
        ref, built = row.get("reference_z_m"), row.get("candidate_z_m")
        delta = ([round(abs(a - b), 3) for a, b in zip(ref, built)]
                 if ref is not None and built is not None and len(ref) == len(built) == 2 else None)
        rows.append(dict(opening_id=row["opening_id"], reference_id=row["reference_id"],
                         reference_z_m=ref, candidate_z_m=built, z_delta_m=delta,
                         within_strict=delta is not None and max(delta) <= 0.05))
    within = sum(row["within_strict"] for row in rows)
    unique = (len({r["opening_id"] for r in rows}) == len(rows)
              and len({r["reference_id"] for r in rows}) == len(rows))
    reference_missing = diagnostic.get("unmatched_reference", [])
    built_extra = diagnostic.get("unmatched_built_exterior", [])
    unclassified = diagnostic.get("source_exposed_edge_unclassified", [])
    return dict(tolerance_m=0.05, expected=expected_count, matched=len(rows), within=within,
                pass_=(expected_count > 0 and within == len(rows) == expected_count and unique
                       and not reference_missing and not built_extra and not unclassified),
                mismatches=[row for row in rows if not row["within_strict"]],
                unmatched_reference=reference_missing, unmatched_built_exterior=built_extra,
                unclassified_exterior=unclassified, all=rows)


def references(case):
    if case == "sm24":
        return [load(HERE.parent / "2026-09-23_sm24_cold_plan_setup/original_observations.json")]
    return load(HERE.parent / "2026-09-27_sm25_full_inventory_setup/original_reference.json")["floors"]


def assess_saved(run, case, *, inventory=None):
    delivery = load(run / "delivery.json")
    source = load(run / delivery["candidate"] / "source_model.json")
    refs = references(case)
    for ref in refs:
        assert batch.runner.digest(run / "images" / Path(ref["source_image"]).name) == ref["source_sha256"]
    if case == "sm24":
        original = load(run / "evaluation/original_openings.json")
        reports = [dict(original, floor_id=source["floors"][0]["id"])] if source["floors"] else []
        openings = load(run / "evaluation/exterior_opening_diagnostic.json")
    else:
        original = inventory or load(HERE.parent / "2026-09-27_sm25_full_inventory_setup" / run.name / "report.json")
        reports = original["floors"]
        openings = load(run / "evaluation/final_opening_diagnostic.json")
    from src.agent.judge.gt import load_gt_document
    expected = len(load_gt_document(CASES[case][0]).openings)
    comparisons = original["comparisons"]
    return dict(run=run.name, case=case, candidate=delivery["candidate"],
                counts={k: len(source[k]) for k in ("floors", "spaces", "openings", "connections")},
                spaces_one_to_one=room_bijection(source, reports, refs),
                original_openings=dict(reference_count=sum(len(r["apertures"]) for r in refs),
                    matched=len(comparisons), positions=sum(r["position_match"] for r in comparisons),
                    hosts=sum(r["host_match"] for r in comparisons),
                    door_connections=sum(r["connection_match"] is True for r in comparisons),
                    unmatched_reference=[x for r in reports for x in r.get("unmatched_reference", [])],
                    unmatched_actual=[x for r in reports for x in r.get("unmatched_actual", [])]),
                strict_heights=strict_heights(openings, expected))


def evaluate(run_id):
    case, name = batch.PLAN[run_id]
    assert case in CASES
    run = HERE.parent / name
    manifest, receipt, summary = (load(run / name) for name in
                                 ("inputs.json", "agent_receipt.json", "summary.json"))
    condition = load(run / "experiment_condition.json")
    assert condition == dict(run_id=run_id, **load(HERE / f"preflight_{run_id}.json")["conditions"])
    assert condition == dict(run_id=run_id, **batch.conditions(case, sorted(condition["implementation_sha256"])))
    assert summary["agent_response_completed"] and summary["subscription_invocations"] == 1
    assert receipt["actual_model"] == "claude-sonnet-5" and receipt["provider"] == "claude"
    assert receipt.get("returncode") == 0 and not receipt.get("timed_out")
    assert not receipt.get("routing_error") and not receipt["result"].get("is_error")
    frozen = dict(scope=batch.SCOPE, provider="claude", image_sha256=load(
        HERE / f"preflight_{run_id}.json")["image_sha256"])
    frozen_path = HERE / f"{name}_frozen.json"
    if frozen_path.exists():
        assert load(frozen_path) == frozen
    else:
        dump(frozen_path, frozen)
    inventory = None
    if case == "sm24":
        base = importlib.import_module(PREFIX + "2026-09-26_sm24_whole_building_setup.audit_run")
        base.audit(run, frozen_method=frozen_path)
    else:
        base = importlib.import_module(PREFIX + "2026-09-26_sm25_height_review_setup.audit_cold")
        # audit_cold expects this fixed filename beneath HERE. Keep it under this
        # run's evaluation folder instead of altering historical setup files.
        setup = run / "evaluation_setup"
        setup.mkdir(exist_ok=True)
        dump(setup / "cold_frozen_method.json", frozen)
        with patch.object(base, "HERE", setup), patch.object(base, "RUN", run):
            base.main()
        full = importlib.import_module(PREFIX + "2026-09-27_sm25_full_inventory_setup.audit_inventory")
        inventory = full.audit(run, load(full.HERE / "original_reference.json"),
                               output=run / "evaluation/original_inventory")
    result = assess_saved(run, case, inventory=inventory)
    dump(run / "cross_case_evaluation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def history():
    selected = {"sm24": ["2026-09-26_sm24_whole_building_claude_run55",
                           "2026-09-26_sm24_whole_building_repeat_claude_run56"],
                "sm25": ["2026-09-26_sm25_height_cold_claude_run53",
                           "2026-09-26_sm25_height_repeat_claude_run54"]}
    results = [assess_saved(HERE.parent / name, case) for case, names in selected.items() for name in names]
    dump(HERE / "cross_case_historical_checks.json", dict(model_calls=0, historical_runs_modified=False,
        checks=results, limits="Saved-audit replay validates added criteria; pending new-run audits remain unexecuted."))
    print(json.dumps([dict(run=r["run"], rooms=r["spaces_one_to_one"]["pass_"],
                          openings=r["original_openings"],
                          heights=f'{r["strict_heights"]["within"]}/{r["strict_heights"]["expected"]}')
                      for r in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", choices=["history", "run100", "run101", "run102", "run103"])
    args = parser.parse_args()
    history() if args.run == "history" else evaluate(args.run)
