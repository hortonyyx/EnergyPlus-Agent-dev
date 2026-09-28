"""Offline reproduction from immutable failed runs; no model or GT input."""
import argparse
import copy
import json
from pathlib import Path
import shutil

from PIL import Image

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.geometry.plan_feedback import resolve_plan_lengths, plan_geometry_feedback
from src.agent.geometry.profile_observation_binding import resolve_plan_pixels
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.geometry.opening_review import review_openings

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
RUN84 = EXPERIMENTS / "2026-09-28_sm21_dimension_first_run84"
RUN85 = EXPERIMENTS / "2026-09-28_sm21_method_control_run85"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "replay")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tracked = [p for root in (RUN84, RUN85) for p in root.rglob("*") if p.is_file()]
    hashes = {str(p): digest(p) for p in tracked}

    def toolkit(name, original):
        run = out / name
        (run / "images").mkdir(parents=True)
        image = "1f_view.png"
        shutil.copy2(original / "images" / image, run / "images" / image)
        metadata = json.loads((original / "inputs.json").read_text())["images"][image]
        dump(run / "inputs.json", dict(images={image: metadata}, max_candidates=8,
            scope="Developer deterministic feedback replay, no model call, no GT"))
        return Toolkit(run)

    units = toolkit("units_run85", RUN85)
    raw = (RUN85 / "plan_drafts/draft_001/plan.json").read_text()
    original = json.loads(raw)
    size = units.manifest["images"]["1f_view.png"]["size"]
    wrong = plan_geometry_feedback(original, size)
    assert all(abs(a - b) < 1e-8 for a, b in zip(wrong["footprint_span_m"], [15000, 8000]))
    tagged = copy.deepcopy(original)
    for axis in ("x", "y"):
        for anchor in tagged[f"{axis}_anchors"]:
            anchor[1] = dict(value=anchor[1], unit="mm")
    converted = units.build_plan("1f_view.png", json.dumps(tagged))
    assert converted["source_geometry_ready"], converted
    dimensions = converted["plan_input"]["geometry_feedback"]
    assert abs(dimensions["footprint_span_m"][0] - 15) < 1e-8
    assert abs(dimensions["footprint_span_m"][1] - 8) < 1e-8
    saved = json.loads((units.run / converted["plan_input"]["plan_file"]).read_text())
    for key in original.keys() - {"x_anchors", "y_anchors"}:
        assert saved[key] == original[key]
    dump(out / "unit_result.json", dict(original_effective_span_m=wrong["footprint_span_m"],
        explicit_mm_effective_span_m=dimensions["footprint_span_m"],
        unchanged_fields=sorted(original.keys() - {"x_anchors", "y_anchors"}),
        development_intervention="Developer tags the four original anchor world values as mm; heights/pixels/objects are untouched. This is not autonomous correction.",
        remaining="Original omitted east window and wrong heights are not repaired."))

    repair = toolkit("revision_run84", RUN84)
    failed = repair.build_plan("1f_view.png", (RUN84 / "plan_drafts/draft_001/plan.json").read_text())
    assert not failed["source_geometry_ready"]
    revision = json.loads((RUN84 / "plan_revisions/revision_001.json").read_text())
    revised = repair.revise_plan("draft_001", failed["plan_input"]["plan_sha256"], revision["operations_json"])
    assert revised["source_geometry_ready"]
    changes = revised["plan_revision"]["geometry_changes"]
    widened = [r for r in changes["changed_openings"] if r["after"]["width_m"] > r["before"]["width_m"]]
    assert {r["id"] for r in widened} == {"D_room2_corr", "D_room5_corr"}
    dump(out / "revision_result.json", dict(compile_success=True, changes=changes,
        widened_ids=[r["id"] for r in widened],
        note="The exact historical bad revision is replayed, not accepted as a repair; feedback now exposes both enlargements."))

    source = json.loads((RUN84 / "candidate_06/source_model.json").read_text())
    images = json.loads((RUN84 / "inputs.json").read_text())["images"]
    calibration = json.loads((RUN84 / "overlay_calibrations/calibration_005.json").read_text())
    opening = next(r for r in source["openings"] if r["id"] == "F1:D_room2_corr")
    observation = dict(floor_id="F1", kind="door", image="1f_view.png", coverage="partial", marks=[
        dict(mark_id="north-middle-door", box=[915, 536, 1014, 637], opening_ids=[opening["id"]],
             space_ids=opening["space_ids"], basis="visible", note="Developer original-image box contains the whole door including its jambs/arc; not copied from the candidate.")])
    old = review_openings(source, observation, images)
    new = review_openings(source, observation, images, plan_calibration=calibration)
    assert not any(r["code"] == "mark_source_location_mismatch" for r in old["findings"])
    assert any(r["code"] == "mark_source_location_mismatch" for r in new["findings"])
    missing = dict(floor_id="F1", kind="window", image="1f_view.png", coverage="partial", marks=[
        dict(mark_id="south-small-window", box=[739, 1060, 860, 1095], opening_ids=[],
             space_ids=["F1:room4"], basis="visible", note="Developer observed complete small south window, not present in saved source.")])
    missing_report = review_openings(source, missing, images, plan_calibration=calibration)
    assert any(r["code"] == "unmodeled_observed_mark" for r in missing_report["findings"])
    dump(out / "observation_result.json", dict(door_observation=observation, old=old, current=new,
        missing_window_observation=missing, missing_window_report=missing_report,
        development_intervention="Original-image marks selected by developer after generation; existing unmodeled-mark support reused. No automatic detection of omitted observations."))

    compatibility = []
    for number in (53, 54, 55, 56, 57, 58, 83, 84, 85):
        roots = list(EXPERIMENTS.glob(f"*run{number}"))
        assert len(roots) == 1, (number, roots)
        root = roots[0]
        for path in sorted((root / "plan_drafts").glob("*/plan.json")):
            raw_plan = json.loads(path.read_text())
            record = json.loads(path.with_name("input.json").read_text())
            converted_plan, lengths = resolve_plan_lengths(raw_plan)
            converted_plan, pixels = resolve_plan_pixels(converted_plan, image=record["image"],
                image_sha256=record["image_sha256"], load_profile=lambda _: (_ for _ in ()).throw(AssertionError("unexpected reference")))
            assert converted_plan == raw_plan and not lengths and not pixels
            with Image.open(root / "images" / record["image"]) as picture:
                image_size = picture.size
            def compile(value):
                try:
                    return dict(result=compile_plan_partition(value, image_size=image_size, image_name=record["image"]))
                except (ValueError, TypeError, KeyError) as error:
                    return dict(error_type=type(error).__name__, error=str(error))
            baseline, current = compile(raw_plan), compile(converted_plan)
            assert baseline == current
            compatibility.append(dict(plan=str(path.relative_to(EXPERIMENTS)), unchanged=True,
                compilation="same_error" if "error" in current else "same_proposal", error=current.get("error")))
    dump(out / "compatibility.json", compatibility)
    assert hashes == {str(p): digest(p) for p in tracked}
    dump(out / "summary.json", dict(model_calls=0, original_files_unchanged=len(tracked),
        numeric_plans_checked=len(compatibility), compile_successes=sum(r["compilation"] == "same_proposal" for r in compatibility),
        compile_errors_preserved=sum(r["compilation"] == "same_error" for r in compatibility),
        unit_conversion_verified=True, collateral_enlargements_exposed=2,
        wrong_mark_location_exposed=True, supplied_missing_observation_exposed=True,
        whole_building_quality_restored=False))
    print((out / "summary.json").read_text())


if __name__ == "__main__":
    main()
