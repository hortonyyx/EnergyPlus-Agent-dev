"""Render one validated draft for adjudication: declaration, checker items and reference.

Magenta: declared dividers and perimeter. Cyan: declared interior doors. Green:
reference seeds and interior door spans. Yellow: undeclared-line items. Red boxes:
other checker items. Output is a PNG crop for manual review only.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
load = lambda path: json.loads(Path(path).read_text())


def render(run_name, draft_name, out, box=None):
    results = load(HERE / "drawing_differences_results.json")
    row = next(r for r in results["drafts"] if r["run"] == run_name and r["draft"] == draft_name)
    labels = next(r for r in load(HERE / "drawing_differences_labels.json")["drafts"]
                  if r["run"] == run_name and r["draft"] == draft_name)
    run = EXPERIMENTS / run_name
    plan = load(run / "plan_drafts" / draft_name / "plan.json")
    image = Image.open(run / "images" / row["image"]).convert("RGB")
    draw = ImageDraw.Draw(image)
    ring = [tuple(p) for p in plan["footprint_pixels"]]
    draw.line(ring + ring[:1], fill=(255, 0, 255), width=2)
    for wall in plan.get("partitions", []):
        draw.line([tuple(p) for p in wall["points"]], fill=(255, 0, 255), width=3)
    for opening in plan.get("openings", []):
        if opening.get("kind") != "window":
            draw.line([tuple(opening["p1"]), tuple(opening["p2"])], fill=(0, 255, 255), width=5)
    reference = None
    for path in (EXPERIMENTS / "2026-09-26_sm21_whole_building_setup/original_reference.json",
                 EXPERIMENTS / "2026-09-23_sm24_cold_plan_setup/original_observations.json",
                 EXPERIMENTS / "2026-09-27_sm25_full_inventory_setup/original_reference.json"):
        data = load(path)
        for floor in data.get("floors", [data]):
            if floor["source_image"].endswith(row["image"]) and path.parent.name.split("_")[1] == row["case"]:
                reference = floor
    if reference:
        for seed, (x, y) in reference["spaces"].items():
            draw.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(0, 255, 0), width=2)
            draw.text((x + 8, y - 8), seed, fill=(0, 255, 0))
        for ref in reference["apertures"]:
            if ref["kind"] == "window":
                continue
            lo, hi = ref["span_pixels"]
            c = ref["cross_pixel"]
            points = [(lo, c + 6), (hi, c + 6)] if ref["axis"] == "x" else [(c + 6, lo), (c + 6, hi)]
            draw.line(points, fill=(0, 200, 0), width=3)
    for item in row["items"]:
        if item["type"] == "undeclared_wall_line":
            if item["axis"] == "vertical":
                draw.line([(item["x_px"], item["y_px"][0]), (item["x_px"], item["y_px"][1])], fill=(255, 255, 0), width=3)
            else:
                draw.line([(item["x_px"][0], item["y_px"]), (item["x_px"][1], item["y_px"])], fill=(255, 255, 0), width=3)
        else:
            draw.rectangle(item["look_box"], outline=(255, 60, 60), width=2)
    if box:
        image = image.crop(box)
    image.save(out)
    print(json.dumps(dict(labels=[l["type"] for l in labels["labels"]],
                          items=[(i["type"], i.get("opening") or i.get("divider") or i.get("x_px"), i["explained_by_label"]) for i in row["items"]]),
                     ensure_ascii=False)[:3000])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run"); parser.add_argument("draft"); parser.add_argument("out")
    parser.add_argument("--box", type=int, nargs=4)
    args = parser.parse_args()
    render(args.run, args.draft, args.out, args.box)
