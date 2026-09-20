#!/usr/bin/env python3
"""Measure the four sm24 elevation drawings without using GT or prior outputs.

The script locates the grey facade outline and cyan opening outlines.  It uses
the printed overall facade dimensions only as scale anchors; the per-opening
dimension chains are transcribed separately in elevation_observations.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


CASE_DIR = Path("case_tests/e2e_tests/sm24_anchor/case_data")
DRAWINGS = {
    "east": {"file": "East_view.png", "span_mm": 20000, "height_mm": 4500},
    "north": {"file": "North_view.png", "span_mm": 10000, "height_mm": 4500},
    "south": {"file": "South_view.png", "span_mm": 10000, "height_mm": 4500},
    "west": {"file": "West_view.png", "span_mm": 20000, "height_mm": 4500},
}


def _cluster_centres(indices: np.ndarray) -> list[float]:
    """Collapse adjacent antialiased line pixels to one centre coordinate."""
    if not len(indices):
        return []
    groups = np.split(indices, np.where(np.diff(indices) > 1)[0] + 1)
    return [round(float(np.mean(group)), 1) for group in groups]


def _wall_reference(rgb: np.ndarray) -> dict[str, float]:
    # The facade outline is neutral grey. Long-line counts separate it from text.
    neutral = (np.ptp(rgb.astype(int), axis=2) < 5) & (rgb[:, :, 0] > 80)
    row_counts = neutral.sum(axis=1)
    col_counts = neutral.sum(axis=0)
    rows = _cluster_centres(np.flatnonzero(row_counts >= 0.8 * row_counts.max()))
    cols = _cluster_centres(np.flatnonzero(col_counts >= 0.8 * col_counts.max()))
    if len(rows) != 2 or len(cols) != 2:
        raise RuntimeError(f"expected two facade rows/columns, got {rows=} {cols=}")
    return {"left": cols[0], "top": rows[0], "right": cols[1], "bottom": rows[1]}


def _cyan_opening_boxes(rgb: np.ndarray, wall: dict[str, float]) -> list[list[int]]:
    values = rgb.astype(int)
    cyan = (
        (values[:, :, 0] < 50)
        & (values[:, :, 1] > 100)
        & (values[:, :, 2] > 100)
        & (np.abs(values[:, :, 1] - values[:, :, 2]) < 40)
    )
    joined = ndimage.binary_dilation(cyan, iterations=1)
    labels, count = ndimage.label(joined, structure=np.ones((3, 3), dtype=int))
    boxes: list[list[int]] = []
    for label in range(1, count + 1):
        component = labels == label
        if int(component.sum()) < 100:
            continue
        # Report the original cyan pixels, not the one-pixel grouping dilation.
        ys, xs = np.where(component & cyan)
        if not len(xs):
            continue
        box = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        width = box[2] - box[0]
        height = box[3] - box[1]
        if width < 20 or height < 20:
            continue
        if not (
            wall["left"] <= box[0] <= box[2] <= wall["right"]
            and wall["top"] <= box[1] <= box[3] <= wall["bottom"]
        ):
            continue
        boxes.append(box)

    # Door leaves/panels can form separate cyan components inside the assembly.
    top_level = []
    for box in boxes:
        contained = any(
            other != box
            and other[0] <= box[0]
            and other[1] <= box[1]
            and other[2] >= box[2]
            and other[3] >= box[3]
            for other in boxes
        )
        if not contained:
            top_level.append(box)
    return sorted(top_level, key=lambda item: item[0])


def measure(path: Path, span_mm: int, height_mm: int) -> dict:
    rgb = np.asarray(Image.open(path).convert("RGB"))
    wall = _wall_reference(rgb)
    boxes = _cyan_opening_boxes(rgb, wall)
    x_scale = span_mm / (wall["right"] - wall["left"])
    z_scale = height_mm / (wall["bottom"] - wall["top"])
    openings = []
    for index, box in enumerate(boxes, start=1):
        x0, y0, x1, y1 = box
        openings.append(
            {
                "screen_order": index,
                "cyan_bbox_px_inclusive": box,
                "measured_from_wall_base_mm": {
                    "u_start": round((x0 - wall["left"]) * x_scale, 1),
                    "u_end": round((x1 - wall["left"]) * x_scale, 1),
                    "width": round((x1 - x0) * x_scale, 1),
                    "bottom": round((wall["bottom"] - y1) * z_scale, 1),
                    "top": round((wall["bottom"] - y0) * z_scale, 1),
                    "height": round((y1 - y0) * z_scale, 1),
                },
            }
        )
    return {
        "image_size_px": [int(rgb.shape[1]), int(rgb.shape[0])],
        "wall_reference_px": wall,
        "calibration_mm_per_px": {"horizontal": round(x_scale, 6), "vertical": round(z_scale, 6)},
        "openings_left_to_right": openings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = {
        "method": "PIL RGB load; numpy colour masks/line counts; scipy connected components",
        "pixel_coordinates": "image origin at upper-left; x rightward; y downward; bounding boxes inclusive",
        "drawings": {},
    }
    for facade, spec in DRAWINGS.items():
        path = args.repo / CASE_DIR / spec["file"]
        payload["drawings"][facade] = measure(path, spec["span_mm"], spec["height_mm"])
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
