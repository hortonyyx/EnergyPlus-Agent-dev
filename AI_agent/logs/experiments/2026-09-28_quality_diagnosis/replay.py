"""Offline counterexamples from saved public actions; no model calls or GT input.

Developer identifies one pair of thin wall lines in the original drawing.
These checks locate failure stages; they do not validate autonomous recovery.
"""
import copy
import gzip
import hashlib
import json
from pathlib import Path

from src.agent.geometry.plan_partition import OpeningHostError, compile_plan_partition
from src.agent.geometry.source_space_relations import review_space_relations

HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def main():
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path.relative_to(BASE))] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    runs = {n: next(BASE.glob(f"*_run{n}")) for n in (57, 58, 83)}
    relationships = []
    for number, run in runs.items():
        source = read(run / "candidate_04/source_model.json")
        manifest = read(run / "inputs.json")
        plan = next(value for path in sorted(run.glob("plan_drafts/*/plan.json"))
                    if (value := read(path))["floor_id"] == "F2")
        for expected in ("separate_spaces", "same_space"):
            review = review_space_relations(source, floor_id="F2",
                image_size=manifest["images"]["2f_view.png"]["size"],
                x_anchors=plan["x_anchors"], y_anchors=plan["y_anchors"],
                observations=[dict(id="north_pair", points=[[600, 470], [1500, 470]],
                    expected=expected, evidence="Developer inspects original central partition and two independent doors. same_space is the deliberately incorrect control expectation.")])
            actual = review["observations"][0]["actual_relation"]
            assert actual == ("same_space" if number == 83 else "separate_spaces")
            assert review["conflict_count"] == int(actual != expected)
            relationships.append(dict(run=number, expected=expected,
                actual_relation=actual, conflict_count=review["conflict_count"],
                consistency=review["observations"][0]["consistency"],
                drawing_fidelity=review["drawing_fidelity"],
                source_model_sha256=source["source_model_sha256"]))

    run = runs[83]
    stream = run / "agent_stream.jsonl.gz"
    hashes[str(stream.relative_to(BASE))] = hashlib.sha256(stream.read_bytes()).hexdigest()
    selected_id, measurement = None, None
    with gzip.open(stream, "rt") as data:
        for line in data:
            parts = json.loads(line).get("message", {}).get("content", [])
            for part in parts if isinstance(parts, list) else []:
                if (part.get("type") == "tool_use"
                        and part.get("name") == "mcp__bim__pixel_profile"
                        and part.get("input", {}).get("name") == "2f_view.png"
                        and part.get("input", {}).get("box") == [400, 900, 1820, 920]):
                    selected_id = part["id"]
                elif (part.get("type") == "tool_result" and selected_id
                        and part.get("tool_use_id") == selected_id):
                    for block in part.get("content", []):
                        if block.get("type") == "text":
                            measurement = json.loads(block["text"])
    assert measurement is not None
    peaks = [row for row in measurement["runs"] if row["peak"] in (768, 779)]
    assert len(peaks) == 2 and all(row["max_count"] == 20 for row in peaks)
    midpoint = sum(row["peak"] for row in peaks) / 2
    before = read(run / "plan_drafts/draft_003/plan.json")
    after = copy.deepcopy(before)
    wall = next(row for row in after["partitions"] if row["id"] == "P_O12")
    old_points = copy.deepcopy(wall["points"])
    assert all(point[0] == 727 for point in old_points)
    for point in wall["points"]:
        point[0] = midpoint
    assert before["openings"] == after["openings"]
    # Prove there is exactly one edited partition and no other declaration change.
    restored = copy.deepcopy(after)
    next(row for row in restored["partitions"] if row["id"] == "P_O12")["points"] = old_points
    assert restored == before
    compile_results = []
    for label, plan, expected_error in (("unchanged", before, "W_S1"),
                                        ("one_wall_reobserved", after, "W_S3")):
        try:
            compile_plan_partition(plan, image_size=(2182, 1319), image_name="2f_view.png")
        except OpeningHostError as error:
            assert error.opening_id == expected_error
            compile_results.append(dict(condition=label, first_host_error=error.opening_id,
                                        error=str(error), source_geometry_ready=False))
        else:
            raise AssertionError("Whole floor is still incorrect; expected a remaining host error")
    image = run / "images/2f_view.png"
    hashes[str(image.relative_to(BASE))] = hashlib.sha256(image.read_bytes()).hexdigest()
    assert hashes[str(image.relative_to(BASE))] == manifest["images"]["2f_view.png"]["sha256"]
    assert all(hashlib.sha256((BASE / name).read_bytes()).hexdigest() == value
               for name, value in hashes.items())
    code_files = ["src/agent/geometry/plan_partition.py",
                  "src/agent/geometry/source_space_relations.py"]
    result = dict(model_calls=0, production_changes=0, saved_new_bim_candidates=0,
        production_code_sha256={name: hashlib.sha256((HERE.parents[3] / name).read_bytes()).hexdigest()
                                for name in code_files},
        source_relationship_counterexamples=relationships,
        original_tool_measurement=dict(tool_call_id=selected_id,
            box_original_pixels=measurement["box_original_pixels"], wall_line_peaks=peaks),
        developer_selected_wall_replay=dict(partition_id="P_O12", before=old_points,
            after=wall["points"], all_openings_unchanged=True,
            all_other_declarations_unchanged=True, compiler_results=compile_results),
        original_files_unchanged=True, evidence_sha256=hashes,
        conclusions=[
            "The same relation checker accepts a wrong expectation when the wrong source agrees with it; it checks consistency, not original drawing truth.",
            "Actual measurement already exposed the developer-identified wall at x=768 and779, but the model declared it at727.",
            "Changing this wall alone removes the first window's host failure without shortening any window. Another window still fails; this is not a complete repair."],
        limits=["Developer supplies wall identity; no automatic identification or work-model adoption is demonstrated.",
                "This does not determine why recent runs fail more often, or exclude indirect prompt/tool/context effects.",
                "No GT or historical good coordinates feed the wall edit. Historical sources serve only the separate relationship controls."])
    (HERE / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(relationship_controls=len(relationships), first_host_errors=[
        row["first_host_error"] for row in compile_results], model_calls=0,
        historical_inputs_unchanged=True)))


if __name__ == "__main__":
    main()
