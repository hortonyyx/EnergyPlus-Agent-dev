"""Offline validation of drawing_differences against frozen original-image references.

Labels come only from developer original-image references recorded before those
runs (sm21, sm24, sm25), never from the checker: for every compiled historical
pixel-plan draft, reference spaces that share one declared space (each needs a
missing divider), reference spaces outside every declared space, declared spaces
holding no reference seed, and interior doors that are missing, misplaced
(<50% overlap), offset (>0.10 m at an end) or declared without a reference door.
``label`` freezes these to labels.json; ``check`` runs the checker and matches its
items to the frozen labels. Unmatched items are listed for manual adjudication.
No model calls; historical runs are read only.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image
from shapely.geometry import LineString, Point, Polygon

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
REFERENCES = {
    "sm21": EXPERIMENTS / "2026-09-26_sm21_whole_building_setup/original_reference.json",
    "sm24": EXPERIMENTS / "2026-09-23_sm24_cold_plan_setup/original_observations.json",
    "sm25": EXPERIMENTS / "2026-09-27_sm25_full_inventory_setup/original_reference.json",
}
DOOR_OFFSET_M = 0.10
CROSS_MATCH_M = 0.30
SEPARATION_MARGIN_M = 0.5
load = lambda path: json.loads(Path(path).read_text())


def references():
    by_image = {}
    for case, path in REFERENCES.items():
        data = load(path)
        for floor in data.get("floors", [data]):
            by_image[floor["source_sha256"]] = dict(case=case, reference_file=str(path.relative_to(ROOT)), **floor)
    return by_image


def drafts():
    for run in sorted(EXPERIMENTS.glob("2026-09-2*_sm2[145]_*")):
        if "setup" in run.name or not (run / "plan_drafts").is_dir():
            continue
        for draft in sorted((run / "plan_drafts").glob("draft_*")):
            if (draft / "compilation.json").is_file():
                yield run, draft


def scale(anchors):
    (p0, w0), (p1, w1) = anchors
    return abs((w1 - w0) / (p1 - p0))


def label(run, draft, reference):
    compilation = load(draft / "compilation.json")
    mpp = scale(compilation["calibration"]["x_anchors"]), scale(compilation["calibration"]["y_anchors"])
    spaces = [(row["space_id"], Polygon(row["pixel_polygon"])) for row in compilation["space_mapping"]]
    holders = {}
    for seed, point in reference["spaces"].items():
        inside = [sid for sid, polygon in spaces if polygon.buffer(0.5).covers(Point(point))]
        holders[seed] = inside[0] if len(inside) == 1 else (None if not inside else "ambiguous:" + "+".join(inside))
    labels = []
    groups = defaultdict(list)
    for seed, holder in holders.items():
        if holder is None:
            labels.append(dict(type="reference_space_without_declared_space", seed=seed))
        else:
            groups[holder].append(seed)
    for holder, seeds in groups.items():
        if len(seeds) < 2:
            continue
        points = {s: reference["spaces"][s] for s in seeds}
        xs, ys = [p[0] for p in points.values()], [p[1] for p in points.values()]
        axis = 0 if (max(xs) - min(xs)) * mpp[0] >= (max(ys) - min(ys)) * mpp[1] else 1
        ordered = sorted(seeds, key=lambda s: points[s][axis])
        for a, b in zip(ordered, ordered[1:]):
            labels.append(dict(type="missing_divider", declared_space=holder, seeds=[a, b],
                               points=[points[a], points[b]]))
    for sid, polygon in spaces:
        if not any(sid == holder for holder in holders.values()):
            labels.append(dict(type="declared_space_without_reference", space_id=sid,
                               area_m2=round(polygon.area * mpp[0] * mpp[1], 2)))
    declared = []
    for row in compilation["opening_hosts"]:
        if row.get("exterior") or row["kind"] == "window":
            continue
        (x0, y0), (x1, y1) = row["p1_pixel"], row["p2_pixel"]
        orient = "v" if x0 == x1 else "h"
        declared.append(dict(id=row["opening_id"], orient=orient, cross=x0 if orient == "v" else y0,
                             span=sorted([y0, y1] if orient == "v" else [x0, x1])))
    used = set()
    for ref in reference["apertures"]:
        if ref["kind"] == "window" or len(ref.get("hosts", [])) != 2:
            continue
        orient = "h" if ref["axis"] == "x" else "v"
        along, across = (mpp[0], mpp[1]) if orient == "h" else (mpp[1], mpp[0])
        lo, hi = sorted(ref["span_pixels"])
        options = []
        for row in declared:
            if row["id"] in used or row["orient"] != orient or abs(row["cross"] - ref["cross_pixel"]) * across > CROSS_MATCH_M:
                continue
            overlap = max(0, min(hi, row["span"][1]) - max(lo, row["span"][0]))
            if overlap > 0:
                options.append((overlap, row))
        entry = dict(reference_door=ref["id"], orient=orient, reference_cross=ref["cross_pixel"], reference_span=[lo, hi])
        if not options:
            labels.append(dict(type="door_missing_or_misplaced", **entry))
            continue
        overlap, row = max(options, key=lambda item: item[0])
        used.add(row["id"])
        offsets = [round((row["span"][0] - lo) * along, 3), round((row["span"][1] - hi) * along, 3)]
        entry.update(declared_opening=row["id"], declared_span=row["span"], end_offsets_m=offsets)
        if overlap < 0.5 * (hi - lo):
            labels.append(dict(type="door_misplaced", **entry))
        elif max(abs(v) for v in offsets) > DOOR_OFFSET_M:
            labels.append(dict(type="door_offset", **entry))
    for row in declared:
        if row["id"] not in used:
            labels.append(dict(type="declared_door_without_reference", declared_opening=row["id"],
                               orient=row["orient"], cross=row["cross"], declared_span=row["span"]))
    return dict(run=run.name, draft=draft.name, case=reference["case"], image=reference["source_image"].split("/")[-1],
                plan_sha256=hashlib.sha256((draft / "plan.json").read_bytes()).hexdigest(),
                compilation_sha256=hashlib.sha256((draft / "compilation.json").read_bytes()).hexdigest(),
                mpp=mpp, labels=labels)


def separates(item, entry, mpp):
    (ax, ay), (bx, by) = entry["points"]
    margin = [SEPARATION_MARGIN_M / mpp[0], SEPARATION_MARGIN_M / mpp[1]]
    if item["axis"] == "vertical":
        lo, hi = item["y_px"]
        return (min(ax, bx) < item["x_px"] < max(ax, bx)
                and all(lo - margin[1] <= y <= hi + margin[1] for y in (ay, by)))
    lo, hi = item["x_px"]
    return (min(ay, by) < item["y_px"] < max(ay, by)
            and all(lo - margin[0] <= x <= hi + margin[0] for x in (ax, bx)))


def line_of(item):
    """(orient, cross coordinate, along span) of an object-level item's own line."""
    if item["axis"] == "vertical":
        return "v", item["x_px"], item["y_px"]
    return "h", item["y_px"], item["x_px"]


def same_wall(item, entry, mpp):
    """The item lies on the wall of the door label: same orientation, cross position
    within CROSS_MATCH_M, and more than half of the shorter span shared."""
    orient, cross, (lo, hi) = line_of(item)
    if orient != entry["orient"]:
        return False
    across = mpp[0] if orient == "v" else mpp[1]
    label_cross = entry.get("reference_cross", entry.get("cross"))
    rlo, rhi = entry.get("reference_span") or entry["declared_span"]
    return (abs(cross - label_cross) * across <= CROSS_MATCH_M
            and max(0, min(hi, rhi) - max(lo, rlo)) > 0.5 * min(hi - lo, rhi - rlo))


def matches(item, entry, mpp, polygons):
    """Object-level items only; floor-level observations are counted separately."""
    kind, label_type = item["type"], entry["type"]
    if kind == "undeclared_wall_line":
        return label_type == "missing_divider" and separates(item, entry, mpp)
    if kind in ("opening_on_continuous_ink", "opening_offset_from_gap"):
        return entry.get("declared_opening") == item["opening"]
    if kind == "wall_gap_without_opening":
        return label_type.startswith("door_") and same_wall(item, entry, mpp)
    if kind == "declared_divider_with_little_ink":
        if label_type == "missing_divider":
            return separates(item, entry, mpp)
        if label_type == "declared_space_without_reference":
            orient, cross, (lo, hi) = line_of(item)
            line = LineString([(cross, lo), (cross, hi)] if orient == "v" else [(lo, cross), (hi, cross)])
            return polygons[entry["space_id"]].exterior.distance(line) <= 5
    return False


def pair_key(entry):
    return (entry["type"], tuple(entry.get("seeds", [])) or entry.get("reference_door")
            or entry.get("declared_opening") or entry.get("space_id"))


def run_check(labels_path, out):
    from src.agent.geometry.plan_drawing_differences import drawing_differences
    frozen = load(labels_path)
    results = []
    for row in frozen["drafts"]:
        run = EXPERIMENTS / row["run"]
        draft = run / "plan_drafts" / row["draft"]
        assert hashlib.sha256((draft / "plan.json").read_bytes()).hexdigest() == row["plan_sha256"]
        plan = load(draft / "plan.json")
        polygons = {r["space_id"]: Polygon(r["pixel_polygon"]) for r in load(draft / "compilation.json")["space_mapping"]}
        with Image.open(run / "images" / row["image"]) as image:
            report = drawing_differences(image, plan)
        objects = [item for item in report["items"] if item.get("scope") != "floor"]
        floor_level = [item for item in report["items"] if item.get("scope") == "floor"]
        detected = [any(matches(item, entry, row["mpp"], polygons) for item in objects) for entry in row["labels"]]
        explained = [any(matches(item, entry, row["mpp"], polygons) for entry in row["labels"]) for item in objects]
        results.append(dict(run=row["run"], draft=row["draft"], case=row["case"], image=row["image"],
                            status=report["status"], reason=report.get("reason"),
                            labels=[dict(**entry, detected=hit) for entry, hit in zip(row["labels"], detected)],
                            items=[dict(**item, explained_by_label=hit) for item, hit in zip(objects, explained)],
                            floor_level=floor_level))
    checked = [r for r in results if r["status"] == "reported"]
    label_totals = defaultdict(lambda: [0, 0])
    item_totals = defaultdict(lambda: [0, 0])
    for result in checked:
        for entry in result["labels"]:
            label_totals[entry["type"]][0] += 1
            label_totals[entry["type"]][1] += entry["detected"]
        for item in result["items"]:
            item_totals[item["type"]][0] += 1
            item_totals[item["type"]][1] += item["explained_by_label"]
    pairs = []
    by_image = defaultdict(list)
    for result in checked:
        by_image[(result["run"], result["image"])].append(result)
    mpps = {(r["run"], r["draft"]): r["mpp"] for r in frozen["drafts"]}
    for (run_name, _), rows in by_image.items():
        rows.sort(key=lambda r: r["draft"])
        for before, after in zip(rows, rows[1:]):
            later = {pair_key(entry) for entry in after["labels"]}
            polygons = {r["space_id"]: Polygon(r["pixel_polygon"]) for r in
                        load(EXPERIMENTS / run_name / "plan_drafts" / after["draft"] / "compilation.json")["space_mapping"]}
            for entry in before["labels"]:
                if not entry["detected"] or entry["type"] not in ("missing_divider", "door_misplaced",
                                                                  "door_missing_or_misplaced", "door_offset"):
                    continue
                if pair_key(entry) in later:
                    outcome = "not fixed"
                else:
                    still = any(matches(item, entry, mpps[(run_name, after["draft"])], polygons) for item in after["items"])
                    outcome = "fixed, report still matches" if still else "fixed, report gone"
                pairs.append(dict(run=run_name, before=before["draft"], after=after["draft"],
                                  label=entry["type"], key=str(pair_key(entry)[1]), outcome=outcome))
    clean = [r for r in checked if not r["labels"]]
    summary = dict(
        drafts=len(results), drafts_by_case=dict(Counter(r["case"] for r in results)),
        not_checked=[dict(run=r["run"], draft=r["draft"], reason=r["reason"],
                          labels=len(r["labels"])) for r in results if r["status"] != "reported"],
        object_labels_in_checked_drafts={k: dict(total=v[0], detected=v[1]) for k, v in sorted(label_totals.items())},
        object_items={k: dict(total=v[0], explained_by_label=v[1], unexplained=v[0] - v[1])
                      for k, v in sorted(item_totals.items())},
        floor_level_observations=[dict(run=r["run"], draft=r["draft"], ink_lines=item["ink_lines"],
                                       missing_divider_labels=sum(e["type"] == "missing_divider" for e in r["labels"]))
                                  for r in results for item in r["floor_level"]],
        clean_checked_drafts=len(clean), clean_drafts_with_items=sum(bool(r["items"] or r["floor_level"]) for r in clean),
        items_on_clean_drafts=sum(len(r["items"]) + len(r["floor_level"]) for r in clean),
        next_draft_outcomes=dict(Counter(p["outcome"] for p in pairs)))
    Path(out).write_text(json.dumps(dict(summary=summary, next_draft_pairs=pairs, drafts=results),
                                    ensure_ascii=False, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["label", "check"])
    parser.add_argument("--labels", default=str(HERE / "drawing_differences_labels.json"))
    parser.add_argument("--out", default=str(HERE / "drawing_differences_results.json"))
    args = parser.parse_args()
    run_label(args.labels) if args.action == "label" else run_check(args.labels, args.out)
