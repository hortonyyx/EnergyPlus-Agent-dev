"""Read-only height-coverage replay; historical correct heights can lack location evidence.

No calibration, annotation box, claim or geometry is retrofitted to a history.
The six good Sonnet runs and three Opus development runs are known correct-height
controls; counts of warnings on them are reported, not called new geometry errors.
"""
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from scripts.tool_scripts.bim_agent_facade_checks import located_height_report

HERE = Path(__file__).resolve().parent
helpers = importlib.import_module("AI_agent.logs.experiments.2026-10-03_tool_package_t1.replay_errors")


def main():
    runs = [path.parent.name for path in helpers.selected_records()]
    runs += [f"2026-10-01_opus_dev_{case}" for case in ("sm21", "sm24", "sm25")]
    results = []
    for name in runs:
        run = HERE.parent / name
        delivered = json.loads((run / "delivery.json").read_text())
        candidate = delivered["candidate"]
        report = located_height_report(Toolkit(run), candidate)
        good = any(tag in name for tag in ("run53", "run54", "run55", "run56", "run57", "run58", "opus_dev"))
        results.append(dict(run=name, correct_height_control=good, candidate=candidate,
            source_file_sha256=digest(run / candidate / "source_model.json"),
            report=report,
            warning_on_correct_height_count=len(report["unchecked_opening_ids"]) if good else None,
            priority_warning_on_correct_height_count=len(report["priority_opening_ids"]) if good else None))
        if name == "2026-10-02_sm24_glm_baseline":
            assert set(report["priority_opening_ids"]) == {"W-east-3", "W-west-5"}
            # The first saved geometry is included separately: before height claims,
            # the same two wide windows are already highlighted for checking.
            first = located_height_report(Toolkit(run), "candidate_01")
            assert {"W-east-3", "W-west-5"} <= set(first["distinct_width_opening_ids"])
            results[-1]["first_saved_candidate_report"] = first
        print(name, report["summary"], "priority", report["priority_opening_ids"])
    controls = [row for row in results if row["correct_height_control"]]
    totals = dict(correct_height_control_runs=len(controls),
        correct_exterior_heights=sum(row["report"]["summary"]["exterior_count"] for row in controls),
        warned_correct_heights=sum(row["warning_on_correct_height_count"] for row in controls),
        priority_warned_correct_heights=sum(row["priority_warning_on_correct_height_count"] for row in controls))
    dump(HERE / "height_replay.json", dict(model_calls=0, summary=totals, runs=results,
        limitation="Unlocalized evidence is not a height-error verdict. Count all alerts on correct-height controls; missing calibration and whole-image citations are not silently treated as coverage."))
    print(json.dumps(totals))


if __name__ == "__main__":
    main()
