"""Compile the recorded developer observations into a new independent source BIM."""
from pathlib import Path
import hashlib
import json
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))

from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.source_plan_view import render_source_plan
from src.agent.geometry.source_image_overlay import render_source_overlay
from src.agent.geometry.source_elevation_view import render_source_elevation


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_inputs():
    case = REPO / "case_tests/e2e_tests/sm24_anchor/case_data"
    dump(HERE / "inputs.json", {
        "input_mode": "developer_assisted_original_drawing_reconstruction",
        "scope": "Original five drawings and building declaration; explicit developer semantic selections",
        "images": {p.name: {"path": str(p.relative_to(REPO)), "sha256": sha(p),
                             "size": list(Image.open(p).size)} for p in sorted(case.glob("*.png"))},
        "building_declaration": {"path": str((case / "testdata_prompt.json").relative_to(REPO)),
                                 "sha256": sha(case / "testdata_prompt.json")},
        "ground_truth_in_generation": False,
        "prior_geometry_in_generation_script": False,
        "development_context": "Developer has historical case knowledge; not a blind independent run",
    })


def main():
    record_inputs()
    plan = json.loads((HERE / "plan_draft.json").read_text())
    # Developer and independent development subagent both checked these literal
    # height chains on the four original elevations. These are observed heights,
    # not a generic office default. The lower facade line is the selected datum.
    plan["ceiling_height"] = 4.5
    large_windows = {"W_N_1", "W_W_5", "W_E_3"}
    exterior_doors = {"D_N_external", "D_E_external", "D_S_external"}
    for opening in plan["openings"]:
        if opening["kind"] == "window":
            opening["z"] = [1.0, 3.4 if opening["id"] in large_windows else 2.8]
            facade = {"N": "North", "S": "South", "E": "East", "W": "West"}[opening["id"].split("_")[1]]
            opening["source_refs"] = [r.replace("; elevation height pending", "") for r in opening["source_refs"]]
            opening["source_refs"].append(f"{facade}_view.png: literal vertical dimension chain; see elevation_observations.json")
        elif opening["id"] in exterior_doors:
            opening["z"] = [0.2, 2.6]
            opening["source_refs"] = [r.replace("; internal height assumed until exterior matching", "") for r in opening["source_refs"]]
            opening["source_refs"].append("Original corresponding elevation: 200 mm base offset + 2400 mm door opening + 1900 mm upper wall = 4500 mm")
        else:
            opening["source_refs"] = [r.replace("; internal height assumed until exterior matching", "; internal door height 2.1m is an explicit assumption") for r in opening["source_refs"]]
    plan["unresolved"] = [
        "The elevations do not label finished floor level. Source floor z=0 is the lower facade outline; observed exterior door sill z=0.2 is retained without inventing a physical step.",
        "Interior door heights and operating state are not supplied; 2.1m and unknown are explicit assumptions.",
        "Window/door widths use the plan's measured pixels with about 0.03m uncertainty; elevation dimensions cross-check category and matching, not hidden endpoint replacement.",
        "Developer example needs user review and independent working-model transfer; no autonomous or stability claim.",
    ]
    plan["assumptions"].append("4.5m source height follows the external elevation envelope. Ceiling/slab construction thickness and net clear height are unspecified.")
    dump(HERE / "plan_final.json", plan)
    image_path = REPO / "case_tests/e2e_tests/sm24_anchor/case_data/1f_view.png"
    image = Image.open(image_path).convert("RGB")
    proposal, metadata = compile_plan_partition(plan, image_size=image.size, image_name="1f_view.png")
    unseeded_plan = dict(plan, space_seeds=[])
    unseeded, unseeded_metadata = compile_plan_partition(unseeded_plan, image_size=image.size, image_name="1f_view.png")
    dump(HERE / "compilation.json", metadata)
    dump(HERE / "unseeded_compilation.json", unseeded_metadata)
    report = export_source_proposal(proposal, HERE / "candidate_01", provenance={
        "mode": "developer_assisted_original_drawing_reconstruction",
        "generator": "Astra developer plan selection + Sol developer elevation measurement + deterministic compilation",
        "input_plan_sha256": sha(HERE / "plan_final.json"),
        "plan_measurements_sha256": sha(HERE / "plan_measurements.json"),
        "ground_truth_supplied_to_generation": False,
        "prior_reading_or_bim_loaded_by_generation_script": False,
        "important_limit": "Developer knows historical case context; this is not a blind target-model run.",
    })
    dump(HERE / "build_report.json", report)
    if not report["source_geometry_ready"]:
        raise RuntimeError(f"Source failed validation: {report}")
    source = json.loads((HERE / "candidate_01/source_model.json").read_text())
    plan_image, plan_meta = render_source_plan(source, "F1")
    plan_image.save(HERE / "source_plan.png")
    dump(HERE / "source_plan.json", plan_meta)
    overlay, overlay_meta = render_source_overlay(source, image, floor_id="F1",
        x_anchors=plan["x_anchors"], y_anchors=plan["y_anchors"],
        basis=plan["basis"], image_name="1f_view.png")
    overlay.save(HERE / "source_overlay.png")
    dump(HERE / "source_overlay.json", overlay_meta)
    for facade in ("North", "South", "East", "West"):
        drawing, detail = render_source_elevation(source, facade)
        drawing.save(HERE / f"source_{facade}.png")
        dump(HERE / f"source_{facade}.json", detail)
    dump(HERE / "summary.json", {"generation_finished": True,
        "mode": "developer_assisted_original_drawing_reconstruction",
        "selected_candidate": "candidate_01", "source_model_sha256": source["source_model_sha256"],
        "counts": report["counts"], "source_self_consistency": source["validation"],
        "working_model_success": False, "human_confirmation": "not_evaluated"})
    print(json.dumps(report["counts"]))


if __name__ == "__main__":
    main()
