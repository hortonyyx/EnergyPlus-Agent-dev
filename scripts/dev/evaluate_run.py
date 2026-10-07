"""Score one finished run and draw its review pictures (no model calls; run files and GT are hashed before/after).

Usage: python scripts/dev/evaluate_run.py <run directory> --case sm21|sm24|sm25 [--out DIR]

Works for both runtimes (a new-runtime run root with bim/, or a Claude Code run directory).
Writes into DIR (default <run>/dev_evaluation, must not exist):
- evaluation/            the independent evaluator's reports (GT stays on the evaluation side);
- overlays/              the delivered candidate drawn over the original plans and elevations, from the
                         run's own calibrations (the model did not see these);
- display/               plan images and the BIM viewer with the current public names;
- summary.json           substantive findings and the user's 5/10/30 cm tiers, with the review addresses.
Same evaluator and tiers as the 10-07 three-case comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402
from scripts.tool_scripts.evaluate_bim_agent import evaluate  # noqa: E402
from src.agent.execution.source_proposal import build_source_viewer_html  # noqa: E402
from src.agent.geometry.source_bim import source_view_geometry  # noqa: E402
from src.agent.geometry.source_elevation_overlay import render_elevation_overlay  # noqa: E402
from src.agent.geometry.source_image_overlay import render_source_overlay  # noqa: E402
from src.agent.geometry.source_naming import public_names_for_display  # noqa: E402
from src.agent.geometry.source_plan_view import render_source_plan  # noqa: E402

CASES = {"sm21": "sm21_anchor", "sm24": "sm24_anchor", "sm25": "sm25-L_anchor"}
TIERS_M = (0.05, 0.10, 0.30)  # user 10-07: <=5 cm, 5-10 cm, 10-30 cm, >30 cm needs dedicated work
SUBSTANTIVE = {"space_missing", "space_extra", "space_split", "space_merged", "partition_split", "partition_merged",
               "false_floor", "connection_changed", "floor_assignment_changed", "extra_opening", "missing_opening",
               "extra_source_space", "missing_source_space", "source_space_split", "source_spaces_merged"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tiers(values) -> dict:
    counts = {"<=5cm": 0, "5-10cm": 0, "10-30cm": 0, ">30cm": 0}
    for value in values:
        key = ("<=5cm" if value <= TIERS_M[0] + 1e-9 else "5-10cm" if value <= TIERS_M[1] + 1e-9
               else "10-30cm" if value <= TIERS_M[2] + 1e-9 else ">30cm")
        counts[key] += 1
    return counts


def overlays(bim: Path, source: dict, out: Path) -> dict:
    out.mkdir()
    index = {"plans": [], "elevations": []}
    public = public_names_for_display(source)["floors"]
    calibrations = {}
    for path in sorted((bim / "overlay_calibrations").glob("*.json")):
        record = load(path)
        calibrations[record["floor_id"]] = (path.name, record)  # later files win
    for floor in (f["id"] for f in source["floors"]):
        if floor not in calibrations:
            index["plans"].append({"floor_id": floor, "status": "no calibration"})
            continue
        name, record = calibrations[floor]
        overlay, _ = render_source_overlay(source, Image.open(bim / "images" / record["image"]), floor_id=floor,
                                           x_anchors=record["x_anchors"], y_anchors=record["y_anchors"],
                                           basis=record["basis"], image_name=record["image"])
        overlay.save(out / f"plan_{public[floor]}.png")
        index["plans"].append({"floor": public[floor], "calibration": name, "overlay": f"plan_{public[floor]}.png"})
    reviews = {}
    for path in sorted((bim / "elevation_reviews").glob("*.json")):
        record = load(path)
        if record.get("anchors") or record.get("transform"):
            reviews[record["facade"]] = (path.name, record)
    for facade in ("North", "South", "East", "West"):
        if facade not in reviews:
            index["elevations"].append({"facade": facade, "status": "no calibration"})
            continue
        name, record = reviews[facade]
        original = Image.open(bim / "images" / (record.get("image") or f"{facade}_view.png"))
        if record.get("anchors"):
            horizontal, vertical = record["anchors"]["horizontal"], record["anchors"]["absolute_z"]
        else:
            t, (w, h) = record["transform"], original.size
            horizontal = [[float(p), t["horizontal_metres_per_pixel"] * p + t["horizontal_offset_m"]]
                          for p in (round(w * .1), round(w * .9))]
            vertical = [[float(p), t["z_metres_per_pixel"] * p + t["z_offset_m"]] for p in (round(h * .1), round(h * .9))]
        overlay, _ = render_elevation_overlay(source, original, facade=facade, horizontal_anchors=horizontal,
                                              z_anchors=vertical, basis=record.get("basis") or "run record " + name)
        overlay.save(out / f"elevation_{facade}.png")
        index["elevations"].append({"facade": facade, "calibration": name, "overlay": f"elevation_{facade}.png"})
    write(out / "index.json", index)
    return index


def display(bim: Path, candidate: str, source: dict, out: Path) -> dict:
    out.mkdir()
    names = public_names_for_display(source)
    report = load(bim / candidate / "report.json")
    (out / "viewer.html").write_text(build_source_viewer_html(
        source_view_geometry(source), source_geometry_ready=report["source_geometry_ready"],
        assumptions=report["agent_assumptions"], unresolved=report["unresolved"]), encoding="utf-8", newline="\n")
    plans = []
    for floor_id, floor_name in names["floors"].items():
        render_source_plan(source, floor_id)[0].save(out / f"plan_{floor_name}.png")
        plans.append(f"plan_{floor_name}.png")
    write(out / "public_names.json", names)
    return {"viewer": "viewer.html", "plans": plans, "naming_scheme": names["scheme_version"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.run.resolve()
    bim = root / "bim" if (root / "bim/inputs.json").is_file() else root
    out = (args.out or root / "dev_evaluation").resolve()
    out.mkdir(parents=True, exist_ok=False)
    case = CASES[args.case]
    candidate = load(bim / "delivery.json")["candidate"]
    guarded = [bim / "inputs.json", bim / "delivery.json", ROOT / "case_tests/test_baseline/gt" / case / "gt.json",
               *sorted(bim.glob("candidate_*/source_model.json"))]
    before = {str(p): digest(p) for p in guarded}
    evaluate(root, case, modelling_task="reconstruction", out=out / "evaluation",
             reference_scope=f"{case}; scored by the dev model after the run ended, GT unchanged.")
    quality = load(out / "evaluation" / f"{candidate}_delivery_quality.json")
    comparison = load(out / "evaluation" / f"{candidate}_partition.json")["comparison"]
    source = load(bim / candidate / "source_model.json")
    shown = overlays(bim, source, out / "overlays")
    redrawn = display(bim, candidate, source, out / "display")
    assert before == {str(p): digest(p) for p in guarded}, "evaluation changed a run or GT file"
    matches = [m for m in comparison.get("matches", []) if isinstance(m, dict)]
    severe = [f for f in quality["retained_findings"] if f["severity"] == "severe"]
    opening_rows = quality["opening_inventory"].get("comparisons") or []
    height_rows = quality["exterior_heights"].get("comparisons") or []
    summary = {
        "run": str(root), "case": case, "candidate": candidate,
        "candidates_saved": len(list(bim.glob("candidate_*"))),
        "spaces_reference_candidate_matched": [comparison.get("reference_count"), comparison.get("candidate_count"),
                                               comparison.get("matched_count")],
        "substantive_findings": [f["code"] for f in severe if f["code"] in SUBSTANTIVE
                                 or (f["code"] == "opening_position_host_or_connection_changed"
                                     and (f.get("host_match") is False or f.get("connection_match") is False))],
        "openings": {k: quality["opening_inventory"].get(k)
                     for k in ("reference_count", "matched", "positions", "hosts", "door_connections")},
        "heights": {k: quality["exterior_heights"].get(k) for k in ("expected", "matched", "within")},
        "tiers_opening_along_wall": tiers(r["max_endpoint_error_m"] for r in opening_rows),
        "openings_off_wall_over_30cm": sum(1 for r in opening_rows if r["perpendicular_error_m"] > TIERS_M[2]),
        "tiers_room_boundary": tiers(m["boundary_hausdorff_m"] for m in matches
                                     if isinstance(m.get("boundary_hausdorff_m"), (int, float))),
        "tiers_exterior_height": tiers(r["max_z_delta_m"] for r in height_rows
                                       if isinstance(r.get("max_z_delta_m"), (int, float))),
        "partition_finding_codes": sorted({f.get("code") for f in comparison.get("findings", []) if isinstance(f, dict)}),
        "review": {"plans": [str(out / "display" / p) for p in redrawn["plans"]],
                   "overlays": [str(out / "overlays" / r["overlay"]) for r in shown["plans"] + shown["elevations"]
                                if r.get("overlay")],
                   "missing_overlays": [r.get("floor_id") or r.get("facade") for r in shown["plans"] + shown["elevations"]
                                        if not r.get("overlay")],
                   "viewer": str(out / "display" / "viewer.html"), "run_delivery_page": str(bim / "delivery.html"),
                   "evaluation_report": str(out / "evaluation" / "index.html")},
        "model_requests": 0}
    write(out / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "review"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
