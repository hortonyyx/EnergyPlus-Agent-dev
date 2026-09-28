"""Read saved source + caller calibrations only; no evaluation/GT/model input."""
from collections import Counter
import json
from pathlib import Path

from PIL import Image
from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.geometry.space_ink_support import measure_space_ink, render_space_ink

HERE = Path(__file__).resolve().parent
EXP = HERE.parent


def main():
    out = HERE / "replay"
    out.mkdir(exist_ok=False)
    summary, protected = [], {}
    for number in (53, 54, 55, 56, 57, 58, 75, 83, 86):
        run, = EXP.glob(f"*_run{number}")
        delivery = json.loads((run / "delivery.json").read_text())
        source_path = run / delivery["candidate"] / "source_model.json"
        source = json.loads(source_path.read_text())
        protected[str(source_path)] = digest(source_path)
        latest = {}
        for p in sorted((run / "overlay_calibrations").glob("calibration_*.json")):
            c = json.loads(p.read_text())
            latest[c["floor_id"], c["image"]] = (p, c)
        result = dict(run=run.name, candidate=delivery["candidate"], floors=[], total_strokes=0)
        for index, (key, (calibration_path, calibration)) in enumerate(latest.items()):
            floor_id, image_name = key
            spaces = [s for s in source["spaces"] if s["floor_id"] == floor_id]
            if not spaces:
                continue
            image_path = run / "images" / image_name
            protected[str(calibration_path)] = digest(calibration_path)
            protected[str(image_path)] = digest(image_path)
            assert digest(image_path) == calibration["image_sha256"]
            def pixel(point):
                coordinates = []
                for a, axis in enumerate("xy"):
                    (p0, v0), (p1, v1) = calibration[axis+"_anchors"]
                    coordinates.append(p0+(point[a]-v0)*(p1-p0)/(v1-v0))
                return coordinates
            pixel_spaces = [dict(space_id=s["id"], pixel_polygon=[pixel(p) for p in s["polygon"]]) for s in spaces]
            folder = out / run.name / f"floor_{index+1}"
            folder.mkdir(parents=True)
            with Image.open(image_path) as image:
                report = measure_space_ink(image, pixel_spaces)
                report.update(source_model_sha256=source["source_model_sha256"], source_file_sha256=digest(source_path),
                    image=image_name, image_sha256=digest(image_path), calibration=calibration,
                    calibration_file_sha256=digest(calibration_path))
                for i, space in enumerate(s for s in report["spaces"] if s["stroke_ids"]):
                    view, mapping = render_space_ink(image, report, space["space_id"])
                    view.save(folder / f"room_{i+1}.png")
                    dump(folder / f"room_{i+1}.json", mapping)
            dump(folder / "report.json", report)
            result["floors"].append(dict(floor_id=floor_id, image=image_name, strokes=report["strokes"],
                space_statuses=dict(Counter(s["status"] for s in report["spaces"]))))
            result["total_strokes"] += len(report["strokes"])
        assert result["floors"], run.name
        summary.append(result)
    assert protected == {p: digest(Path(p)) for p in protected}
    dump(out / "summary.json", dict(model_calls=0, production_entry_changed=False,
        source_and_original_files_unchanged=len(protected), runs=summary,
        parameters_note="Defaults frozen before this replay: inset0.12, support0.85, span20pixels, neutral chroma60, contrast80. No tuning to clear furniture flags.",
        limits="Flagged ink is not a wall finding. Manual original review distinguishes furniture and partition evidence. No result is repaired or used as autonomous generation."))
    dump(out / "protected_sha256.json", protected)
    print(json.dumps([dict(run=r["run"], strokes=r["total_strokes"]) for r in summary]))


if __name__ == "__main__":
    main()
