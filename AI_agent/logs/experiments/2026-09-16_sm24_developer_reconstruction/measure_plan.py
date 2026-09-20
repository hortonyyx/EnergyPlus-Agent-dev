"""Developer-selected source crops -> auditable measured lines and pixel plan.

No GT, old reading, or old source geometry is read. The semantic selections below
are explicit developer observations, not an autonomous inference algorithm.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
IMAGE = REPO / "case_tests/e2e_tests/sm24_anchor/case_data/1f_view.png"


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def runs(values, offset=0):
    labels, count = label(values)
    return [[int(np.where(labels == i)[0][0]) + offset,
             int(np.where(labels == i)[0][-1]) + offset] for i in range(1, count + 1)]


def main():
    image = Image.open(IMAGE).convert("RGB")
    pixels = np.asarray(image).astype(int)
    gray = ((pixels.max(2) - pixels.min(2) < 12)
            & (pixels.mean(2) > 80) & (pixels.mean(2) < 235))
    green = (pixels[:, :, 1] > 75) & (pixels[:, :, 0] < 30) & (pixels[:, :, 2] < 30)
    cyan = (pixels[:, :, 1] > 70) & (pixels[:, :, 2] > 70) & (pixels[:, :, 0] < 35)
    evidence = {"image": str(IMAGE.relative_to(REPO)),
                "sha256": hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
                "size": list(image.size), "mode": "developer visual selection plus deterministic measurement",
                "calibration": [], "walls": [], "openings": []}
    ticks = {}
    for axis, box, value in [(0, [230, 49, 631, 72], 10), (1, [53, 130, 78, 900], 20)]:
        x0, y0, x1, y1 = box
        bands = runs(green[y0:y1, x0:x1].sum(axis=axis) >= 5, x0 if axis == 0 else y0)
        if len(bands) != 2:
            raise ValueError(f"Expected two visually selected overall-dimension ticks, found {bands}")
        centers = [sum(band) / 2 for band in bands]
        ticks[axis] = centers
        evidence["calibration"].append({"axis": "xy"[axis], "crop": box,
            "tick_bands": bands, "source_tick_centers": centers, "text_verbatim": str(value * 1000),
            "value_m": value, "pixels_per_metre": (centers[1] - centers[0]) / value})
    left, right = ticks[0]
    top, bottom = ticks[1]
    # Each band is selected from a crop inspected on the original. Paired strokes
    # are the two faces of a physical thin partition. Furniture is not extended.
    queries = [
        ("north_cross", [245, 286, 615, 310], 1, 80, [0, 1]),
        ("west_spine", [386, 285, 412, 882], 0, 120, [0, 1]),
        ("east_spine", [445, 285, 470, 601], 0, 100, [0, 1]),
        ("west_upper", [245, 395, 415, 415], 1, 80, [0, 1]),
        ("west_lower", [245, 578, 415, 592], 1, 80, [0, 1]),
        ("east_upper", [445, 357, 614, 379], 1, 80, [0, 1]),
        ("east_lower", [445, 578, 614, 592], 1, 80, [0, 1]),
        ("southeast_step", [395, 744, 464, 760], 1, 30, [0, 1]),
        ("southeast_top", [450, 691, 614, 708], 1, 40, [0, 1]),
        ("southeast_riser", [450, 690, 468, 760], 0, 20, [0, 1]),
    ]
    positions = {}
    for name, box, axis, threshold, chosen in queries:
        x0, y0, x1, y1 = box
        bands = runs(gray[y0:y1, x0:x1].sum(axis=axis) > threshold, x0 if axis == 0 else y0)
        selected = [bands[i] for i in chosen]
        center = (selected[0][0] + selected[-1][1]) / 2
        positions[name] = center
        evidence["walls"].append({"id": name, "crop": box, "axis": "xy"[axis],
            "threshold": threshold, "candidate_bands": bands, "selected_bands": selected,
            "representative_pixel": center,
            "rejected_bands": [band for i, band in enumerate(bands) if i not in chosen],
            "reason": "paired faces of the source partition; representative plane halfway across wall band"})
    xw, xe = positions["west_spine"], positions["east_spine"]
    yn = positions["north_cross"]
    if positions["southeast_riser"] != xe:
        raise ValueError("Southeast return is not aligned with measured east spine; inspect before regularizing")
    paths = {
        "north_cross": [[left, yn], [right, yn]],
        "west_spine": [[xw, yn], [xw, bottom]],
        "east_spine": [[xe, yn], [xe, positions["east_lower"]]],
        "west_upper": [[left, positions["west_upper"]], [xw, positions["west_upper"]]],
        "west_lower": [[left, positions["west_lower"]], [xw, positions["west_lower"]]],
        "east_upper": [[xe, positions["east_upper"]], [right, positions["east_upper"]]],
        "east_lower": [[xe, positions["east_lower"]], [right, positions["east_lower"]]],
        "southeast_return": [[xw, positions["southeast_step"]], [xe, positions["southeast_step"]],
                             [xe, positions["southeast_top"]], [right, positions["southeast_top"]]],
    }
    # Cyan-component choices are semantic observations. Their bounding intervals
    # are measured here, rather than inferred from a room-count target.
    door_queries = [
        ("D_N_external", [260, 120, 335, 162], 0, top),
        ("D_N_internal", [396, 270, 459, 307], 0, yn),
        ("D_W_upper", [358, 350, 405, 402], 1, xw),
        ("D_W_middle", [358, 411, 405, 460], 1, xw),
        ("D_W_lower", [358, 590, 405, 640], 1, xw),
        ("D_E_upper", [453, 312, 496, 370], 1, xe),
        ("D_E_middle", [453, 375, 496, 427], 1, xe),
        ("D_SE_internal", [550, 686, 600, 742], 0, positions["southeast_top"]),
        ("D_E_external", [596, 600, 644, 680], 1, right),
        ("D_S_external", [406, 841, 453, 885], 0, bottom),
    ]
    openings = []
    for name, box, axis, constant in door_queries:
        x0, y0, x1, y1 = box
        bands = runs(cyan[y0:y1, x0:x1].any(axis=axis), x0 if axis == 0 else y0)
        if len(bands) != 1:
            raise ValueError(f"Inspect door {name}: unexpected cyan runs {bands}")
        start, end = bands[0]
        p1, p2 = ([start, constant], [end, constant]) if axis == 0 else ([constant, start], [constant, end])
        openings.append({"id": name, "kind": "door", "p1": p1, "p2": p2, "z": [0, 2.1],
            "state": "unknown", "source_refs": [f"1f_view.png:{name} cyan swing in crop {box}; projected to measured wall plane; internal height assumed until exterior matching"]})
        evidence["openings"].append({"id": name, "kind": "door", "crop": box,
            "cyan_runs": bands, "p1": p1, "p2": p2,
            "reason": "door swing and wall interruption agree; swing is not evidence of operational open/closed state"})
    window_queries = [
        ("N", [247, 149, 613, 160], 0, top, [[417, 592]]),
        ("S", [247, 869, 613, 879], 0, bottom, [[268, 322], [537, 592]]),
        ("W", [247, 150, 258, 879], 1, left, [[171, 225], [312, 355], [418, 473], [517, 572], [684, 858]]),
        ("E", [602, 150, 613, 879], 1, right, [[171, 225], [312, 355], [382, 556]]),
    ]
    for facade, box, axis, constant, selected in window_queries:
        x0, y0, x1, y1 = box
        bands = runs(cyan[y0:y1, x0:x1].any(axis=axis), x0 if axis == 0 else y0)
        for index, (start, end) in enumerate(selected, 1):
            p1, p2 = ([start, constant], [end, constant]) if axis == 0 else ([constant, start], [constant, end])
            name = f"W_{facade}_{index}"
            openings.append({"id": name, "kind": "window", "p1": p1, "p2": p2, "z": [0.9, 2.4],
                "source_refs": [f"1f_view.png:{name} measured cyan window band {start}..{end}; elevation height pending"]})
            evidence["openings"].append({"id": name, "kind": "window", "facade": facade,
                "crop": box, "all_cyan_runs": bands, "selected_span": [start, end], "p1": p1, "p2": p2,
                "reason": "parallel window lines; door symbols excluded. East long window has one pixel occluded by green annotation; retained as one window, not split."})
    plan = {"floor_id": "F1", "z_floor": 0, "ceiling_height": 3,
        "x_anchors": [[left, 0], [right, 10]], "y_anchors": [[top, 20], [bottom, 0]],
        "basis": "Original overall dimension ticks establish outer-perimeter datum; exterior source planes use that datum and interior planes use the mid-band between measured wall faces. Wall thickness is not explicitly modeled. No GT used.",
        "footprint_pixels": [[left, top], [right, top], [right, bottom], [left, bottom]],
        "partitions": [{"id": name, "points": points, "source_refs": [f"1f_view.png:{name}; measured bands in plan_measurements.json; developer verified physical path/door heals"]} for name, points in paths.items()],
        "openings": openings,
        "space_seeds": [
            {"id": "north_room", "point": [350, 220], "role": "office"},
            {"id": "west_upper", "point": [330, 335], "role": "office"},
            {"id": "west_middle", "point": [330, 490], "role": "office"},
            {"id": "west_lower", "point": [330, 700], "role": "meeting"},
            {"id": "east_upper", "point": [535, 325], "role": "office"},
            {"id": "east_middle", "point": [535, 485], "role": "office"},
            {"id": "southeast_room", "point": [510, 790], "role": "office"},
            {"id": "corridor", "point": [430, 500], "role": "corridor"}],
        "assumptions": ["Developer-assisted reconstruction from the original drawing, not target-model autonomous generation.",
            "Room uses inferred from furniture; no textual room names visible.",
            "Outer-perimeter reference and internal mid-wall references intentionally differ; source is a lightweight representative-plane model.",
            "Partition endpoint junctions extended only through visible connecting wall bands to the chosen representative plane.",
            "Interior doors use 2.1m assumed height and unknown operating state.",
            "Doors/windows use raster-measured extents; about one source pixel (0.028m) localization uncertainty.",
            "Exterior wall thickness / roof structural depth are not modeled."],
        "unresolved": ["Draft pending independent original-elevation review for floor, window and exterior-door heights."]}
    dump(HERE / "plan_measurements.json", evidence)
    dump(HERE / "plan_draft.json", plan)
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    for name, points in paths.items():
        draw.line([tuple(p) for p in points], fill=(255, 80, 180), width=2)
        draw.text(tuple(points[0]), name, fill=(255, 190, 230))
    for opening in openings:
        draw.line([tuple(opening["p1"]), tuple(opening["p2"])], fill=(255, 180, 40) if opening["kind"] == "door" else (60, 170, 255), width=3)
    annotated.save(HERE / "measured_plan_overlay.png")
    print(json.dumps({"partitions": len(paths), "openings": len(openings), "anchors": [plan["x_anchors"], plan["y_anchors"]]}))


if __name__ == "__main__":
    main()
