"""Adversarial checks of added evaluation criteria using saved good-run audits."""
from copy import deepcopy
import importlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
evaluation = importlib.import_module("AI_agent.logs.experiments.2026-09-30_instruction_fix.evaluate_cross_case")
load = evaluation.load


def main():
    checked = []
    cases = {"sm24": "2026-09-26_sm24_whole_building_claude_run55",
             "sm25": "2026-09-26_sm25_height_cold_claude_run53"}
    for case, name in cases.items():
        run = HERE.parent / name
        source = load(run / load(run / "delivery.json")["candidate"] / "source_model.json")
        refs = evaluation.references(case)
        if case == "sm24":
            reports = [dict(load(run / "evaluation/original_openings.json"), floor_id=source["floors"][0]["id"])]
            diagnostic = load(run / "evaluation/exterior_opening_diagnostic.json")
        else:
            reports = load(HERE.parent / "2026-09-27_sm25_full_inventory_setup" / name / "report.json")["floors"]
            diagnostic = load(run / "evaluation/final_opening_diagnostic.json")
        count = len(diagnostic["matched"])

        def check(label, passes):
            assert passes, (case, label)
            checked.append(f"{case}: {label}")

        check("saved complete room correspondence passes", evaluation.room_bijection(source, reports, refs)["pass_"])
        check("absent audit fails", not evaluation.room_bijection(source, [], refs)["pass_"])
        changed = deepcopy(reports)
        mapping = changed[0]["space_identity_by_interior_point"]
        keys = list(mapping)
        mapping[keys[1]] = mapping[keys[0]]
        check("two reference rooms merged fails", not evaluation.room_bijection(source, changed, refs)["pass_"])
        changed = deepcopy(reports)
        changed[0]["space_identity_by_interior_point"].pop(keys[0])
        check("missing reference seed fails", not evaluation.room_bijection(source, changed, refs)["pass_"])
        changed = deepcopy(source)
        extra = deepcopy(source["spaces"][0]); extra["id"] = "unexpected_room"
        changed["spaces"].append(extra)
        check("extra source space fails", not evaluation.room_bijection(changed, reports, refs)["pass_"])
        changed = deepcopy(source)
        changed["floors"] = changed["floors"][1:]
        check("missing floor fails", not evaluation.room_bijection(changed, reports, refs)["pass_"])
        changed = deepcopy(reports)
        changed.append(deepcopy(changed[0]))
        check("duplicate floor audit fails", not evaluation.room_bijection(source, changed, refs)["pass_"])
        renamed_source, renamed_reports = deepcopy(source), deepcopy(reports)
        old = source["floors"][0]["id"]
        renamed_source["floors"][0]["id"] = "arbitrary_floor_label"
        for space in renamed_source["spaces"]:
            if space["floor_id"] == old:
                space["floor_id"] = "arbitrary_floor_label"
        for report in renamed_reports:
            if report["floor_id"] == old:
                report["floor_id"] = "arbitrary_floor_label"
        check("floor naming does not change identity result", evaluation.room_bijection(renamed_source, renamed_reports, refs)["pass_"])
        check("saved complete heights pass", evaluation.strict_heights(diagnostic, count)["pass_"])
        check("empty height audit fails", not evaluation.strict_heights({}, count)["pass_"])
        changed = deepcopy(diagnostic)
        changed["matched"][0]["candidate_z_m"][1] += 0.06
        check("six centimetre height error fails", not evaluation.strict_heights(changed, count)["pass_"])
        changed = deepcopy(diagnostic)
        changed["matched"][0]["reference_z_m"] = None
        check("unknown reference height fails", not evaluation.strict_heights(changed, count)["pass_"])
        changed = deepcopy(diagnostic)
        changed["matched"].pop()
        check("missing matched opening fails", not evaluation.strict_heights(changed, count)["pass_"])
        for field in ("unmatched_reference", "unmatched_built_exterior", "source_exposed_edge_unclassified"):
            changed = deepcopy(diagnostic)
            changed[field] = ["unexpected"]
            check(f"{field} fails", not evaluation.strict_heights(changed, count)["pass_"])
    evaluation.dump(HERE / "cross_case_validation.json", dict(model_calls=0, passed=len(checked), checks=checked))
    print(f"{len(checked)} offline adversarial checks passed; 0 model calls")


if __name__ == "__main__":
    main()
