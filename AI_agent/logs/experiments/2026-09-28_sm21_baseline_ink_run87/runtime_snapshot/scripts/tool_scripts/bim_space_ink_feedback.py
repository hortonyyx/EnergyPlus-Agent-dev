"""Experimental adapter copied into the isolated historical runtime only."""
import hashlib
import json

from PIL import Image
from src.agent.geometry.space_ink_support import measure_space_ink, render_space_ink


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_space_ink_feedback(toolkit, result):
    if not result.get("source_geometry_ready") or "plan_input" not in result:
        return
    record = result["plan_input"]
    compilation_file = toolkit.run / record["compilation_file"]
    if digest(compilation_file) != record["compilation_sha256"]:
        raise ValueError("space-ink feedback compilation changed")
    compilation = json.loads(compilation_file.read_text())
    source_path = toolkit.run / result["candidate"] / "source_model.json"
    source = json.loads(source_path.read_text())
    folder = compilation_file.parent
    with Image.open(toolkit.image_path(record["image"])) as image:
        report = measure_space_ink(image, compilation["space_mapping"])
        report.update(image=record["image"], image_sha256=record["image_sha256"],
            candidate=result["candidate"], source_model_sha256=source["source_model_sha256"],
            plan_sha256=record["plan_sha256"], compilation_sha256=record["compilation_sha256"])
        pictures = []
        flagged = [s for s in report["spaces"] if s["stroke_ids"]]
        for index, space in enumerate(flagged[:3], 1):
            picture, mapping = render_space_ink(image, report, space["space_id"])
            target = folder / f"interior_ink_room_{index}.png"
            picture.save(target)
            pictures.append(dict(file=str(target.relative_to(toolkit.run)), sha256=digest(target), **mapping))
    path = folder / "interior_ink.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    result["space_ink_review"] = dict(file=str(path.relative_to(toolkit.run)), sha256=digest(path),
        image=report["image"], floor_id=compilation["floor_id"], source_model_sha256=source["source_model_sha256"],
        parameters=report["parameters"], space_count=len(report["spaces"]),
        sampled_space_count=sum(s["status"] == "sampled" for s in report["spaces"]),
        stroke_count=len(report["strokes"]), strokes=report["strokes"][:24],
        strokes_truncated=len(report["strokes"]) > 24,
        flagged_rooms=[dict(space_id=s["space_id"], stroke_ids=s["stroke_ids"],
                            original_box=s["box_original_pixels"]) for s in flagged],
        images_returned=len(pictures), images_truncated=len(flagged) > len(pictures),
        interpretation=report["interpretation"], limits=report["limits"],
        follow_up="Use view_image with the original image name and a flagged room's original_box for additional clean context. Recheck whether the original has one physical space or separate rooms; revise the saved plan only when supported. Preserve real apertures and other rooms. Zero strokes is not a fidelity pass.",
        drawing_fidelity="not_evaluated")
    result["space_ink_views"] = pictures
    toolkit.log("space_ink_feedback", dict(candidate=result["candidate"], file=str(path.relative_to(toolkit.run)),
        source_model_sha256=source["source_model_sha256"], stroke_count=len(report["strokes"])))
