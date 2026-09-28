"""Sensitivity check for interior_stroke_audit: merge adjacent correct spaces and see if the erased divider is flagged.

For each delivered candidate of the given runs, every pair of same-floor spaces whose
union is an axis-aligned rectangle is merged (a synthetic 'missed partition'); the audit
rule is applied to that merged rectangle only. Offline, read-only.
Usage: python interior_stroke_mutation.py run57 run53 ...
"""
import glob
import json
import os
import sys
from itertools import combinations

import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from interior_stroke_audit import COVER, EXP, IMAGES, MARGIN_M, last_plans, to_pixel  # noqa: E402


def flagged(img, plan, poly):
    pts = [to_pixel(plan, x, y) for x, y in poly.exterior.coords]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    (px0, m0), (px1, m1) = plan["x_anchors"]
    margin = int(round(MARGIN_M * abs((px1 - px0) / (m1 - m0))))
    x0, x1 = int(min(xs)) + margin, int(max(xs)) - margin
    y0, y1 = int(min(ys)) + margin, int(max(ys)) - margin
    if x1 - x0 < 20 or y1 - y0 < 20:
        return None
    crop = img[y0:y1, x0:x1]
    ink = (crop.max(axis=2) > 80) & ((crop.max(axis=2) - crop.min(axis=2)) < 60)
    return bool((ink.mean(axis=0) >= COVER).any() or (ink.mean(axis=1) >= COVER).any())


def main():
    out = {}
    for run in sys.argv[1:]:
        run_dir = glob.glob(os.path.join(EXP, f"*_{run}"))[0]
        cand = json.load(open(os.path.join(run_dir, "summary.json")))["delivery"]["candidate"]
        for rel in (("gt", f"{cand}_partition.json"), (f"{cand}_partition.json",), ("partition.json",)):
            path = os.path.join(run_dir, "evaluation", *rel)
            if os.path.exists(path):
                break
        spaces = json.load(open(path))["candidate_spaces"]
        plans = last_plans(run_dir)
        hit = miss = skip = 0
        missed = []
        for a, b in combinations(spaces, 2):
            if a["floor_id"] != b["floor_id"]:
                continue
            pa, pb = Polygon(a["polygon"]), Polygon(b["polygon"])
            if pa.intersection(pb).length < 1.0 and pa.buffer(0.05).intersection(pb).area < 0.05:
                continue  # not sharing a wall
            union = unary_union([pa, pb])
            if union.geom_type != "Polygon" or abs(union.area - box(*union.bounds).area) > 0.02 * union.area:
                continue  # merged shape is not a rectangle; out of this simple rule's scope
            floor, image_name = IMAGES[a["floor_id"]]
            plan = plans.get(floor)
            if plan is None:
                skip += 1
                continue
            img = np.asarray(Image.open(os.path.join(run_dir, "images", image_name)).convert("RGB")).astype(int)
            res = flagged(img, plan, box(*union.bounds))
            if res is None:
                skip += 1
            elif res:
                hit += 1
            else:
                miss += 1
                missed.append([a["id"], b["id"]])
        out[run] = {"merged_pairs_flagged": hit, "not_flagged": miss, "skipped": skip, "not_flagged_pairs": missed}
        print(run, out[run])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "interior_stroke_mutation.json"), "w") as handle:
        json.dump(out, handle, indent=1)


if __name__ == "__main__":
    main()
