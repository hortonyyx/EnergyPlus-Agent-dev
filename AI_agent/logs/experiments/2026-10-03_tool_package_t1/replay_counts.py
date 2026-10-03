"""Developer-assisted count replay; no model observations are invented as history.

Fixed evaluation-only facade totals below agree with the accepted Opus source
controls. They are supplied as explicit new observation fixtures to unchanged
historical sources, never generated from the candidate being checked.
"""
import importlib
import json
from pathlib import Path
import tempfile

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump

HERE = Path(__file__).resolve().parent
helpers = importlib.import_module("AI_agent.logs.experiments.2026-10-03_tool_package_t1.replay_errors")
# Order North, South, East, West. Each tuple is (windows, exterior doors).
TOTALS = {
    "sm21": [[(3, 0), (3, 1), (1, 0), (0, 1)], [(2, 0), (4, 0), (1, 0), (1, 0)]],
    "sm24": [[(1, 1), (2, 1), (3, 1), (5, 0)]],
    "sm25": [[(4, 0), (2, 0), (7, 1), (2, 2)], [(4, 0), (5, 0), (5, 0), (2, 0)]],
}


def main():
    names = [p.parent.name for p in helpers.selected_records()
             if any(t in p.parent.name for t in ("run53", "run54", "run55", "run56", "run57", "run58"))]
    names += [f"2026-10-01_opus_dev_{case}" for case in TOTALS]
    names += ["2026-10-02_sm25_glm_baseline"]
    references = {}
    for case in TOTALS:
        run = HERE.parent / f"2026-10-01_opus_dev_{case}"
        candidate = json.loads((run / "delivery.json").read_text())["candidate"]
        references[case] = dict(path=str(run / candidate / "source_model.json"),
                                sha256=digest(run / candidate / "source_model.json"))
    reports = []
    for name in names:
        original = HERE.parent / name
        candidate = json.loads((original / "delivery.json").read_text())["candidate"]
        source = json.loads((original / candidate / "source_model.json").read_text())
        case = next(case for case in TOTALS if case in name)
        with tempfile.TemporaryDirectory(dir=helpers.ROOT / ".tmp_t1", prefix="counts-") as directory:
            run = Path(directory)
            helpers.copy_run(original, run)
            toolkit = Toolkit(run)
            before = toolkit.facade_counts(candidate)
            fixture_records = []
            floors = sorted(source["floors"], key=lambda row: row["z_floor"])
            for index, floor in enumerate(floors):
                for facade, (windows, doors) in zip(("North", "South", "East", "West"), TOTALS[case][index]):
                    fixture_records.append(toolkit.record_claim(json.dumps(dict(
                        observation_type="facade_count", image=f"{facade}_view.png",
                        floor_id=floor["id"], facade=facade, window_count=windows, door_count=doors,
                        reason="Developer-supplied offline replay count, independently fixed from the accepted reference; not an original model observation."))))
            report = toolkit.facade_counts(candidate)
            mismatches = [dict(floor_id=row["floor_id"], facade=row["facade"], kind=kind, **row[kind])
                for row in report["scopes"] for kind in ("window", "door")
                if row[kind]["status"] != "matches_observed_total"]
            control = "glm" not in name
            if not control:
                assert len(mismatches) == 1
                assert (mismatches[0]["floor_id"], mismatches[0]["facade"], mismatches[0]["kind"], mismatches[0]["missing_count"]) == ("F1", "West", "window", 2)
            reports.append(dict(run=name, candidate=candidate, correct_count_control=control,
                source_file_sha256=digest(original / candidate / "source_model.json"),
                report_before_fixture=before, supplied_fixture_records=fixture_records,
                report=report, mismatches=mismatches,
                false_alert_count=len(mismatches) if control else None))
            print(name, report["summary"], "differences", mismatches)
    controls = [row for row in reports if row["correct_count_control"]]
    summary = dict(correct_count_control_runs=len(controls),
        control_floor_facade_count=sum(row["report"]["summary"]["floor_facade_count"] for row in controls),
        control_false_alert_count=sum(row["false_alert_count"] for row in controls))
    dump(HERE / "count_replay.json", dict(model_calls=0, replay_kind="developer_supplied_count_observations",
        expected_totals=TOTALS, reference_sources=references, summary=summary, runs=reports,
        limitation="This tests comparison against correct supplied counts, not model counting skill. No historical geometry, calibration or original observation is changed."))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
