import json
from pathlib import Path

from importlib import import_module

_support = import_module("AI_agent.logs.experiments.2026-10-03_runtime_r1.facade_support")
CHILD_BUDGET = _support.CHILD_BUDGET
build_tasks = _support.build_tasks
evaluate_batches = _support.evaluate_batches
load_json = _support.load_json
validate_protocol = _support.validate_protocol
validate_run_manifest = _support.validate_run_manifest


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "AI_agent/logs/experiments/2026-10-03_runtime_r1"


def _outcome(mode, facade, windows, count, *, status="completed"):
    directly_seen = []
    for row in windows:
        directly_seen.append({
            "observation_id": f"window-{row['order']}",
            "statement": (f"WINDOW floor=F1 order={row['order']} width_mm={row['width_mm']} "
                          f"sill_m={row['sill_m']:.2f} head_m={row['head_m']:.2f}"),
            "location": {"box_original_pixels": row["expected_bbox_px"]},
        })
    directly_seen.append({"observation_id": "count", "statement": f"COUNT floor=F1 windows={count}",
                          "location": {"box_original_pixels": [1, 1, 2, 2]}})
    return {"status": status, "package": {"task_id": f"{mode}_{facade}"},
            "result": {"directly_seen": directly_seen, "interpretations": [], "uncertain": []}}


def test_fixed_facade_assets_and_evaluation_boundary_validate():
    assert validate_run_manifest(ROOT, HERE / "facade_cases.json") == {
        "ok": True, "cases": 4, "errors": []}
    result = validate_protocol(ROOT, HERE / "facade_cases.json", HERE / "facade_references.json")
    assert result == {"ok": True, "cases": 4,
                      "special_4800_windows": [("east", 1), ("west", 5)], "errors": []}
    manifest_text = (HERE / "facade_cases.json").read_text(encoding="utf-8").lower()
    assert "expected_windows" not in manifest_text
    assert "reference_answer" not in manifest_text


def test_batch_tasks_use_one_view_each_and_bounded_two_request_budget():
    manifest = load_json(HERE / "facade_cases.json")
    view_ids = {case["image_name"]: f"view_{index:04d}"
                for index, case in enumerate(manifest["cases"], 1)}
    tasks = build_tasks(manifest, view_ids, "concurrent")
    assert [task["task_id"] for task in tasks] == [
        "concurrent_north", "concurrent_south", "concurrent_east", "concurrent_west"]
    assert all(len(task["view_ids"]) == 1 for task in tasks)
    assert all(task["budget"] == CHILD_BUDGET for task in tasks)
    assert all(task["budget"]["model_calls"] == 2 and task["budget"]["tool_calls"] == 0
               for task in tasks)


def test_evaluator_scores_every_window_counts_localization_and_two_special_windows():
    references = load_json(HERE / "facade_references.json")
    batches = {}
    for mode, seconds in (("concurrent", 10.0), ("sequential", 30.0)):
        outcomes = []
        for ref in references["cases"]:
            outcomes.append(_outcome(mode, ref["facade"], ref["expected_windows"],
                                     ref["expected_count_by_floor"]["F1"]))
        batches[mode] = {"wall_seconds": seconds, "requests": 4,
                         "reported_usage": {"total_tokens": 100}, "results": outcomes}
    evaluated = evaluate_batches(batches, references)
    for mode in ("concurrent", "sequential"):
        row = evaluated["modes"][mode]
        assert row["height_windows_correct"] == row["height_windows_total"] == 11
        assert row["height_within_5cm_ratio"] == 1.0
        assert row["facade_counts_correct"] == row["facade_counts_total"] == 4
        assert row["loose_localizations_correct"] == row["localizations_total"] == 11
        assert len(row["special_4800"]) == 2
        assert all(item["correct"] for item in row["special_4800"])


def test_five_centimetre_boundary_is_inclusive_and_missing_answer_is_wrong():
    references = load_json(HERE / "facade_references.json")
    batches = {}
    for mode in ("concurrent", "sequential"):
        outcomes = []
        for ref in references["cases"]:
            windows = json.loads(json.dumps(ref["expected_windows"]))
            if ref["facade"] == "east":
                windows[0]["head_m"] += 0.05
            if ref["facade"] == "west":
                outcomes.append({"status": "invalid_observation",
                    "package": {"task_id": f"{mode}_west"}, "result": None})
            else:
                outcomes.append(_outcome(mode, ref["facade"], windows,
                                         ref["expected_count_by_floor"]["F1"]))
        batches[mode] = {"wall_seconds": 1.0, "requests": 4,
                         "reported_usage": {"total_tokens": 1}, "results": outcomes}
    evaluated = evaluate_batches(batches, references)
    east = next(row for row in evaluated["modes"]["concurrent"]["cases"] if row["facade"] == "east")
    west = next(row for row in evaluated["modes"]["concurrent"]["cases"] if row["facade"] == "west")
    assert east["windows"][0]["height_within_5cm"]
    assert west["height_windows_correct"] == 0
    assert not west["count_correct"]


def test_count_rejects_duplicate_window_order_extra_floor_and_whole_image_box():
    references = load_json(HERE / "facade_references.json")
    batches = {}
    for mode in ("concurrent", "sequential"):
        outcomes = []
        for ref in references["cases"]:
            outcome = _outcome(mode, ref["facade"], ref["expected_windows"],
                               ref["expected_count_by_floor"]["F1"])
            if ref["facade"] == "north":
                duplicate = json.loads(json.dumps(outcome["result"]["directly_seen"][0]))
                duplicate["observation_id"] = "duplicate-window"
                duplicate["location"]["box_original_pixels"] = [0, 0, 2890, 1651]
                outcome["result"]["directly_seen"].insert(1, duplicate)
                outcome["result"]["directly_seen"].append({
                    "observation_id": "extra-floor", "statement": "COUNT floor=F2 windows=0",
                    "location": {"box_original_pixels": [1, 1, 2, 2]}})
            outcomes.append(outcome)
        batches[mode] = {"wall_seconds": 1.0, "requests": 4,
                         "reported_usage": {"total_tokens": 1}, "results": outcomes}
    evaluated = evaluate_batches(batches, references)
    north = next(row for row in evaluated["modes"]["concurrent"]["cases"] if row["facade"] == "north")
    assert not north["inventory_structure_correct"]
    assert not north["count_correct"]
    assert north["parsed_window_entries"] == 2
    # The duplicate overwrites the order lookup, but its whole-image box is not
    # allowed to pass the separately labelled loose localization check.
    assert not north["windows"][0]["loose_localization_matches_window"]
