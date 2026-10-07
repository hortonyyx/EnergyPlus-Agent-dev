"""Post-hoc outputs for each delivered candidate, drawn after the run (no model calls, run files untouched).

Usage: python posthoc.py <run> [<run> ...]   (run names under AI_agent/archive/local_backup/cmp3).
- posthoc_overlays/: the candidate drawn back over the original plans and elevations. Calibrations come from
  the run itself: per floor the latest plan calibration (overlay_calibrations/*.json); per facade the latest
  elevation record carrying anchors or a pixel-to-metre transform (elevation_reviews/*.json).
- posthoc_display/: plan images and the BIM viewer redrawn with the current public names (bim_names_v3,
  N1); geometry is the saved candidate, unchanged.
The model did not see these images. index.json in each folder records the sources used.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402
from src.agent.execution.source_proposal import build_source_viewer_html  # noqa: E402
from src.agent.geometry.source_bim import source_view_geometry  # noqa: E402
from src.agent.geometry.source_elevation_overlay import render_elevation_overlay  # noqa: E402
from src.agent.geometry.source_image_overlay import render_source_overlay  # noqa: E402
from src.agent.geometry.source_naming import public_names_for_display  # noqa: E402
from src.agent.geometry.source_plan_view import render_source_plan  # noqa: E402

RUNS = ROOT / "AI_agent/archive/local_backup/cmp3"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def transform_anchors(scale, offset, size):
    """Two in-image pixels and their metres from a recorded linear pixel-to-metre transform."""
    pixels = (round(size * 0.1), round(size * 0.9))
    return [[float(p), scale * p + offset] for p in pixels]


def elevation_calibration(record, size):
    if record.get("anchors"):
        return record["anchors"]["horizontal"], record["anchors"]["absolute_z"]
    t = record["transform"]
    return (transform_anchors(t["horizontal_metres_per_pixel"], t["horizontal_offset_m"], size[0]),
            transform_anchors(t["z_metres_per_pixel"], t["z_offset_m"], size[1]))


def overlays(bim, candidate, source, out):
    out.mkdir(exist_ok=True)
    index = {"candidate": candidate, "note": "drawn after the run from the run's own calibrations",
             "plans": [], "elevations": []}
    public = public_names_for_display(source)["floors"]  # file names use public floor names (F1, F2)
    calibrations = {}
    for path in sorted((bim / "overlay_calibrations").glob("*.json")):
        record = load(path)
        calibrations[record["floor_id"]] = (path.name, record)  # later files win
    for floor in (f["id"] for f in source["floors"]):
        if floor not in calibrations:
            index["plans"].append({"floor_id": floor, "status": "no calibration"})
            continue
        file_name, record = calibrations[floor]
        image = Image.open(bim / "images" / record["image"])
        overlay, _ = render_source_overlay(source, image, floor_id=floor, x_anchors=record["x_anchors"],
                                           y_anchors=record["y_anchors"], basis=record["basis"],
                                           image_name=record["image"])
        overlay.save(out / f"plan_{public[floor]}.png")
        index["plans"].append({"floor_id": floor, "floor": public[floor], "image": record["image"],
                               "calibration": file_name, "overlay": f"plan_{public[floor]}.png"})
    reviews = {}
    for path in sorted((bim / "elevation_reviews").glob("*.json")):
        record = load(path)
        if record.get("anchors") or record.get("transform"):
            reviews[record["facade"]] = (path.name, record)  # later files win
    for facade in ("North", "South", "East", "West"):
        if facade not in reviews:
            index["elevations"].append({"facade": facade, "status": "no calibration"})
            continue
        file_name, record = reviews[facade]
        image_name = record.get("image") or f"{facade}_view.png"
        original = Image.open(bim / "images" / image_name)
        horizontal, vertical = elevation_calibration(record, original.size)
        overlay, _ = render_elevation_overlay(source, original, facade=facade, horizontal_anchors=horizontal,
                                              z_anchors=vertical,
                                              basis=record.get("basis") or "run calibration record " + file_name)
        overlay.save(out / f"elevation_{facade}.png")
        index["elevations"].append({"facade": facade, "image": image_name, "calibration": file_name,
                                    "overlay": f"elevation_{facade}.png"})
    write(out / "index.json", index)
    return index


def display(bim, candidate, source, out):
    out.mkdir(exist_ok=True)
    names = public_names_for_display(source)
    report = load(bim / candidate / "report.json")
    viewer = build_source_viewer_html(source_view_geometry(source), source_geometry_ready=report["source_geometry_ready"],
                                     assumptions=report["agent_assumptions"], unresolved=report["unresolved"])
    (out / "viewer.html").write_text(viewer, encoding="utf-8", newline="\n")
    plans = []
    for floor_id, floor_name in names["floors"].items():
        image, _ = render_source_plan(source, floor_id)
        image.save(out / f"plan_{floor_name}.png")
        plans.append(f"plan_{floor_name}.png")
    write(out / "public_names.json", names)
    index = {"candidate": candidate, "naming_scheme": names["scheme_version"], "viewer": "viewer.html",
             "plans": plans, "source_model_sha256": source.get("source_model_sha256"),
             "note": "redrawn after the run with current public names; geometry unchanged"}
    write(out / "index.json", index)
    return index


def run(name):
    bim = RUNS / name / "bim"
    candidate = load(bim / "delivery.json")["candidate"]
    source_path = bim / candidate / "source_model.json"
    before = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source = load(source_path)
    shown = overlays(bim, candidate, source, RUNS / name / "posthoc_overlays")
    redrawn = display(bim, candidate, source, RUNS / name / "posthoc_display")
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == before, "a run file changed"
    print(name, candidate, [p.get("overlay", p.get("status")) for p in shown["plans"]],
          [e.get("overlay", e.get("status")) for e in shown["elevations"]], redrawn["naming_scheme"], redrawn["plans"])


if __name__ == "__main__":
    for run_name in sys.argv[1:]:
        run(run_name)
