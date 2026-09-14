"""Check the actual image transport and isolated inputs of a completed local probe."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    audit_path = ROOT / "AI_agent/logs/experiments/2026-09-14_reconstruction_guidance_setup/verify_execution.py"
    spec = importlib.util.spec_from_file_location("prior_transport_audit", audit_path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    child = run / "detail_01"
    manifest = json.loads((run / "inputs.json").read_text())
    selected = json.loads((child / "inputs.json").read_text())
    receipt = json.loads((run / "detail_01_receipt.json").read_text())
    execution = audit.audit_stream(run, "detail_01", child / "images")
    question = (child / "question.txt").read_text()
    readonly_tools = {"get_bim_reference", "inputs", "view_image", "pixel_profile", "map_pixels",
        "map_dimension_chain", "view_pixel_profile", "view_pixel_region", "view_pixel_region_overview",
        "preview_space_trace", "view_space_trace", "select_space_trace"}
    checks = {
        "all_images_match": all(row["pixels_match"] for row in execution["original_views"] + execution["derived_views"]),
        "original_matches_manifest_and_input": all(digest(child / "images" / name) == digest(run / "images" / name)
            == record["sha256"] == manifest["images"][name]["sha256"] for name, record in selected["images"].items()),
        "only_selected_images": {p.name for p in (child / "images").iterdir()} == set(selected["images"]),
        "only_observation_files": {p.name for p in child.iterdir()} <= {"images", "inputs.json", "question.txt",
            "tools.jsonl", "pixel_regions", "pixel_region_overviews", "pixel_profiles", "space_traces", "trace_selection.json"},
        "question_hash": hashlib.sha256(question.encode()).hexdigest() == selected["question_sha256"],
        "receipt_input_hash": receipt["observation_source"]["input_sha256"] == digest(child / "inputs.json"),
        "no_mutation_tools": set(execution["tool_names"]) <= readonly_tools,
    }
    report = {"checks": checks, "all_checks_passed": all(checks.values()), "execution": execution,
              "limits": "Input and tool/image transport only. Region contours and claims must still be checked against the original drawing."}
    dump(run / "execution_audit.json", report)
    assert report["all_checks_passed"], checks
    print(json.dumps({"checks": checks, "tool_names": execution["tool_names"]}, indent=2))


if __name__ == "__main__":
    main()
