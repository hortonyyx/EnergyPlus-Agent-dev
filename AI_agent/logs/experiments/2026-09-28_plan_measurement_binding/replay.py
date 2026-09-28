"""Apply selected real measurements through the plan API; developer replay only."""
import copy
import json
import shutil
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.geometry.plan_partition import compile_plan_partition

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "2026-09-28_sm21_behavior_repeat_run83"


def main():
    run = HERE / "developer_replay"
    run.mkdir(exist_ok=False)
    image = OLD / "images/2f_view.png"
    original_plan_path = OLD / "plan_drafts/draft_003/plan.json"
    hashes = {str(p): digest(p) for p in [image, original_plan_path]}
    (run / "images").mkdir()
    shutil.copy2(image, run / "images/2f_view.png")
    metadata = json.loads((OLD / "inputs.json").read_text())["images"]["2f_view.png"]
    dump(run / "inputs.json", dict(images={"2f_view.png": metadata}, max_candidates=3,
        scope="Developer-selected wall coordinate binding from the original; no model invocation or GT.",
        input_mode="developer_selected_measurement_replay", model_calls=0))
    toolkit = Toolkit(run)
    original = original_plan_path.read_text()
    initial = toolkit.build_plan("2f_view.png", original)
    assert initial["status"] == "error" and "opening W_S1 " in initial["error"]
    profile = json.loads(toolkit.view_profile("2f_view.png", [400, 900, 1820, 920],
        "x", [140]*3, 80, 0.5)[1])
    selected = [row for row in profile["candidates"] if row["pixels"] in ([768,768], [779,779])]
    assert len(selected) == 2, profile["candidates"]
    midpoint = {"midpoint": [dict(profile=profile["profile_id"], candidate=c["id"]) for c in selected]}
    saved = toolkit.inspect_plan("draft_001")
    plan_before = copy.deepcopy(saved["declaration"])
    wall = next(row for row in plan_before["partitions"] if row["id"] == "P_O12")
    points = [[copy.deepcopy(midpoint), point[1]] for point in wall["points"]]
    changed = toolkit.revise_plan("draft_001", saved["plan_sha256"], json.dumps([dict(
        op="update", collection="partitions", id="P_O12", changes={"points": points},
        reason="Developer identifies the paired thin lines as this partition and selects their midpoint; no window shortening.",
        source_refs=[f"2f_view.png: {profile['profile_id']} candidates {selected[0]['id']}/{selected[1]['id']}"])]))
    assert changed["status"] == "error" and "opening W_S3 " in changed["error"]
    resolved = toolkit.inspect_plan("draft_002")["declaration"]
    revised_wall = next(row for row in resolved["partitions"] if row["id"] == "P_O12")
    assert revised_wall["points"] == [[773.5,800], [773.5,1071]]
    expected = copy.deepcopy(plan_before)
    next(row for row in expected["partitions"] if row["id"] == "P_O12")["points"] = revised_wall["points"]
    assert resolved == expected
    assert not list(run.glob("candidate_*"))
    record = changed["plan_input"]
    bindings = json.loads((run / record["measurement_bindings"]["file"]).read_text())
    assert len(bindings["bindings"]) == 2
    assert all(b["resolved_pixel"] == 773.5 for b in bindings["bindings"])
    for binding in bindings["bindings"]:
        assert all(e["profile_sha256"] == digest(run / profile["profile_record"]) for e in binding["endpoints"])
    # Numeric historical plans still use identical compiler inputs and outcomes.
    compatibility = []
    for number in (57, 58, 83):
        old_run = next(HERE.parent.glob(f"*_run{number}"))
        for old_plan in sorted(old_run.glob("plan_drafts/*/plan.json")):
            from src.agent.geometry.profile_observation_binding import resolve_plan_pixels
            raw = json.loads(old_plan.read_text())
            input_record = json.loads((old_plan.parent / "input.json").read_text())
            image_name = input_record["image"]
            inventory = json.loads((old_run / "inputs.json").read_text())["images"][image_name]
            resolved_numeric, bound = resolve_plan_pixels(raw, image=image_name,
                image_sha256=inventory["sha256"], load_profile=lambda _: (_ for _ in ()).throw(AssertionError("Unexpected load")))
            assert raw == resolved_numeric and not bound
            outcomes = []
            for declaration in (raw, resolved_numeric):
                try:
                    proposal, mapping = compile_plan_partition(declaration,
                        image_size=tuple(inventory["size"]), image_name=image_name)
                    outcomes.append(dict(proposal=proposal, mapping=mapping))
                except (ValueError, TypeError) as error:
                    outcomes.append(dict(error=str(error), kind=type(error).__name__))
            assert outcomes[0] == outcomes[1]
            compatibility.append(dict(run=number, draft=old_plan.parent.name,
                                      identical=True, compiled="proposal" in outcomes[0]))
    assert all(digest(Path(p)) == sha for p, sha in hashes.items())
    dump(HERE / "report.json", dict(model_calls=0, autonomous_recovery=False,
        selected_measurement=profile["profile_id"], midpoint=773.5,
        initial_error=initial["error"], next_error=changed["error"],
        actual_binding_record=record["measurement_bindings"],
        all_windows_and_other_declarations_preserved=True,
        numeric_historical_compatibility=compatibility, original_sha256=hashes,
        limits="Developer supplies object identity and selected candidates. W_S3 and the omitted north partition remain wrong; no whole-floor BIM or quality-restoration claim."))
    print(json.dumps(dict(bound_coordinates=2, midpoint=773.5,
        numeric_drafts_preserved=len(compatibility), model_calls=0)))


if __name__ == "__main__":
    main()
