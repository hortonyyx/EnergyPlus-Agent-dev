"""Prototype (offline, read-only): flag long neutral-ink strokes crossing a declared space's interior.

Generation-side feasible: uses only the original plan image, the run's own last plan
calibration and its delivered spaces (read from the saved evaluation file only for
their already-exported candidate polygons; reference/GT spaces are not used).
A stroke is flagged when a column (row) inside the shrunken space box has neutral
(white/grey) ink over >= COVER of the box height (width). Adjacent columns merge.

Usage: python interior_stroke_audit.py run57 run58 ...
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
COVER = 0.85
MARGIN_M = 0.4  # ignore strokes within 0.4 m of the declared boundary (wall bands, offset partitions)
IMAGES = {"Floor 1": ("F1", "1f_view.png"), "Floor 2": ("F2", "2f_view.png"),
          "F1": ("F1", "1f_view.png"), "F2": ("F2", "2f_view.png")}


def last_plans(run_dir):
    plans = {}
    for path in sorted(glob.glob(os.path.join(run_dir, "plan_drafts", "*", "plan.json"))) + sorted(
        glob.glob(os.path.join(run_dir, "plan_revisions", "*", "plan.json"))
    ):
        try:
            plan = json.load(open(path))
        except ValueError:  # a saved draft with invalid JSON is skipped, not repaired
            continue
        plans[plan.get("floor_id")] = plan
    return plans


def to_pixel(plan, x, y):
    (px0, m0), (px1, m1) = plan["x_anchors"]
    (py0, n0), (py1, n1) = plan["y_anchors"]
    return px0 + (x - m0) * (px1 - px0) / (m1 - m0), py0 + (y - n0) * (py1 - py0) / (n1 - n0)


def groups(indices):
    out, start, prev = [], None, None
    for i in indices:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            out.append((start, prev))
            start = prev = i
    if start is not None:
        out.append((start, prev))
    return out


def audit(run):
    run_dir = glob.glob(os.path.join(EXP, f"*_{run}"))[0]
    summary = json.load(open(os.path.join(run_dir, "summary.json")))
    cand = summary["delivery"]["candidate"]
    for rel in (("gt", f"{cand}_partition.json"), (f"{cand}_partition.json",), ("partition.json",)):
        path = os.path.join(run_dir, "evaluation", *rel)
        if os.path.exists(path):
            break
    part = json.load(open(path))
    plans = last_plans(run_dir)
    flags = []
    for space in part["candidate_spaces"]:
        floor, image_name = IMAGES.get(space["floor_id"], (None, None))
        plan = plans.get(floor)
        if plan is None or abs(plan["x_anchors"][1][1]) > 1000:  # unit-error plans are out of scope here
            continue
        img = np.asarray(Image.open(os.path.join(run_dir, "images", image_name)).convert("RGB")).astype(int)
        pts = [to_pixel(plan, x, y) for x, y in space["polygon"]]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        (px0, m0), (px1, m1) = plan["x_anchors"]
        margin = int(round(MARGIN_M * abs((px1 - px0) / (m1 - m0))))
        x0, x1 = int(min(xs)) + margin, int(max(xs)) - margin
        y0, y1 = int(min(ys)) + margin, int(max(ys)) - margin
        if x1 - x0 < 20 or y1 - y0 < 20:
            continue
        box = img[y0:y1, x0:x1]
        ink = (box.max(axis=2) > 80) & ((box.max(axis=2) - box.min(axis=2)) < 60)
        cols = [x0 + i for i in np.nonzero(ink.mean(axis=0) >= COVER)[0]]
        rows = [y0 + i for i in np.nonzero(ink.mean(axis=1) >= COVER)[0]]
        for a, b in groups(cols):
            flags.append({"space": space["id"], "axis": "vertical", "pixels": [int(a), int(b)]})
        for a, b in groups(rows):
            flags.append({"space": space["id"], "axis": "horizontal", "pixels": [int(a), int(b)]})
    return cand, len(part["candidate_spaces"]), flags


def main():
    results = {}
    for run in sys.argv[1:]:
        cand, n, flags = audit(run)
        results[run] = {"candidate": cand, "spaces": n, "flags": flags}
        print(run, cand, "spaces", n, "flags", len(flags), json.dumps(flags)[:400])
    with open(os.path.join(HERE, "interior_stroke_audit.json"), "w") as handle:
        json.dump(results, handle, indent=1)


if __name__ == "__main__":
    main()
