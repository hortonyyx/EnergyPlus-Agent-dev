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
from shapely.geometry import Point, Polygon

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


def span_of(item):
    return item["y_px"] if item["axis"] == "vertical" else item["x_px"]


def matches(item, entry, mpp):
    kind, label_type = item["type"], entry["type"]
    if kind == "undeclared_wall_line":
        return label_type == "missing_divider" and separates(item, entry, mpp)
    if kind in ("opening_on_continuous_ink", "opening_offset_from_gap"):
        return entry.get("declared_opening") == item["opening"]
    if kind == "wall_gap_without_opening":
        if not label_type.startswith("door_"):
            return False
        lo, hi = span_of(item)
        rlo, rhi = entry["reference_span"]
        orient = "v" if item["axis"] == "vertical" else "h"
        return orient == entry["orient"] and max(0, min(hi, rhi) - max(lo, rlo)) > 0.5 * min(hi - lo, rhi - rlo)
    if kind == "no_dividers_declared":
        return label_type in ("missing_divider", "door_missing_or_misplaced")
    if kind == "declared_divider_with_little_ink":
        return label_type in ("declared_space_without_reference", "missing_divider")
    return False


def run_label(out):
    refs = references()
    rows = []
    for run, draft in drafts():
        record = load(draft / "input.json")
        reference = refs.get(record["image_sha256"])
        if reference is None:
            continue
        rows.append(label(run, draft, reference))
    Path(out).write_text(json.dumps(dict(
        method=__doc__.strip().splitlines()[0], references={k: str(v.relative_to(ROOT)) for k, v in REFERENCES.items()},
        door_offset_m=DOOR_OFFSET_M, cross_match_m=CROSS_MATCH_M, drafts=rows), ensure_ascii=False, indent=1))
    counts = Counter(entry["type"] for row in rows for entry in row["labels"])
    print(json.dumps(dict(drafts=len(rows), labels=dict(counts),
                          clean_drafts=sum(not row["labels"] for row in rows)), indent=1))


def run_check(labels_path, out):
    from src.agent.geometry.plan_drawing_differences import drawing_differences
    frozen = load(labels_path)
    results = []
    for row in frozen["drafts"]:
        run = EXPERIMENTS / row["run"]
        draft = run / "plan_drafts" / row["draft"]
        assert hashlib.sha256((draft / "plan.json").read_bytes()).hexdigest() == row["plan_sha256"]
        plan = load(draft / "plan.json")
        with Image.open(run / "images" / row["image"]) as image:
            report = drawing_differences(image, plan)
        items = report["items"]
        detected = [any(matches(item, entry, row["mpp"]) for item in items) for entry in row["labels"]]
        explained = [any(matches(item, entry, row["mpp"]) for entry in row["labels"]) for item in items]
        results.append(dict(run=row["run"], draft=row["draft"], case=row["case"], image=row["image"],
                            labels=[dict(**entry, detected=hit) for entry, hit in zip(row["labels"], detected)],
                            items=[dict(**item, explained_by_label=hit) for item, hit in zip(items, explained)]))
    label_totals = defaultdict(lambda: [0, 0])
    item_totals = defaultdict(lambda: [0, 0])
    for result in results:
        for entry in result["labels"]:
            label_totals[entry["type"]][0] += 1
            label_totals[entry["type"]][1] += entry["detected"]
        for item in result["items"]:
            item_totals[item["type"]][0] += 1
            item_totals[item["type"]][1] += item["explained_by_label"]
    clean = [r for r in results if not r["labels"]]
    summary = dict(
        drafts=len(results), drafts_by_case=dict(Counter(r["case"] for r in results)),
        labels={k: dict(total=v[0], detected=v[1]) for k, v in sorted(label_totals.items())},
        items={k: dict(total=v[0], explained_by_label=v[1], unexplained=v[0] - v[1]) for k, v in sorted(item_totals.items())},
        clean_drafts=len(clean), clean_drafts_with_items=sum(bool(r["items"]) for r in clean),
        items_on_clean_drafts=sum(len(r["items"]) for r in clean))
    Path(out).write_text(json.dumps(dict(summary=summary, drafts=results), ensure_ascii=False, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["label", "check"])
    parser.add_argument("--labels", default=str(HERE / "drawing_differences_labels.json"))
    parser.add_argument("--out", default=str(HERE / "drawing_differences_results.json"))
    args = parser.parse_args()
    run_label(args.labels) if args.action == "label" else run_check(args.labels, args.out)
