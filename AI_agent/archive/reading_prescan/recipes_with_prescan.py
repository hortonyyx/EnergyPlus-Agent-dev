"""Single source for CV toolbox recipe constants and macro recipes."""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.signal import find_peaks, peak_widths

from .sidecar import evidence_dir, sha256_short


CLEAN_VECTOR_V1 = {
    "recipe_id": "clean_vector_v1",
    "applicability": "clean_vector",
    # Seeded from the sm21 forensics recipe: R ~= G ~= B and 60 < v < 230.
    # The exact inclusive bounds follow the adjudicated mask contract.
    "gray_lo": 60,
    "gray_hi": 230,
    "rgb_tol": 8,
    # Low enough for full-image sm21 plan smoke, high enough to suppress small
    # gray labels/ticks in synthetic fixtures after orthogonal normalization.
    "prominence": 0.04,
    "min_peak_distance_px": 6,
    "min_cc_area_px": 20,
    "merge_gap_px": 2,
    "merge_overlap_ratio": 0.5,
    "merge_iou": 0.2,
    "calibration_warn_residual_px": 2.0,
    "calibration_warn_residual_m": 0.05,
    # Measured clean-vector ceiling: accepted two-axis sidecars top out at
    # 0.138%, while an independently valid 1 px endpoint convention measured
    # 0.28%.  The rounded-up 0.30% ceiling still rejects the confirmed 1.92%
    # wrong-control-point case (execution log, 2026-07-31 G-2).
    "calibration_max_axis_relative_deviation": 0.003,
    "calibration_foreground_delta": 24,
    "calibration_min_line_px": 12,
    "calibration_min_span_px": 30,
    "calibration_intersection_tolerance_px": 2,
    "calibration_intersection_merge_px": 4,
    "prescan_min_run_px": 4,
    "prescan_min_tick_len_px": 6,
    "prescan_max_tick_len_px": 40,
    "prescan_long_line_strength_multiple": 3.0,
    "prescan_long_line_min_px": 100,
    "prescan_long_line_intersection_tolerance_px": 2,
}

_RECIPES = {
    "clean_vector_v1": CLEAN_VECTOR_V1,
}


def get_recipe(recipe_id: str = "clean_vector_v1") -> dict:
    """Return a copy of a known deterministic recipe."""

    try:
        return deepcopy(_RECIPES[recipe_id])
    except KeyError as exc:
        known = ", ".join(sorted(_RECIPES))
        raise ValueError(f"unknown CV recipe {recipe_id!r}; known recipes: {known}") from exc


SUPPORTED_PRESCAN_CAPABILITY_PROFILES = ("rectangular", "orthogonal_polygon")
TOOL_VERSION = "1"


def _load_rgb(image: str | Path | Image.Image) -> Image.Image:
    if isinstance(image, Image.Image):
        img = image
    else:
        img = Image.open(image)
    if img.mode in {"RGBA", "LA"} or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, rgba).convert("RGB")
    return img.convert("RGB")


def _mask_clean_vector(img: Image.Image, recipe: dict[str, Any]) -> np.ndarray:
    arr = np.asarray(_load_rgb(img), dtype=np.int16)
    mean = arr.mean(axis=2)
    spread = arr.max(axis=2) - arr.min(axis=2)
    return (
        (mean >= recipe["gray_lo"])
        & (mean <= recipe["gray_hi"])
        & (spread <= recipe["rgb_tol"])
    )


def _foreground_mask(img: Image.Image, recipe: dict[str, Any]) -> np.ndarray:
    """Clean-vector ink mask relative to the image-border background.

    Dimension ink is chromatic in the CAD anchors but gray in some exports, so
    hue is deliberately not part of the contract.  The median border colour is
    deterministic and handles the two supported clean-vector conventions
    (black canvas with light ink, or white canvas with dark ink).
    """

    arr = np.asarray(_load_rgb(img), dtype=np.int16)
    border = np.concatenate((arr[0], arr[-1], arr[:, 0], arr[:, -1]), axis=0)
    background = np.median(border, axis=0)
    delta = np.max(np.abs(arr - background), axis=2)
    return delta >= int(recipe["calibration_foreground_delta"])


def _opened_line_boxes(
    mask: np.ndarray, *, axis: str, min_line_px: int
) -> list[tuple[int, int, int, int]]:
    structure = (
        np.ones((1, min_line_px), dtype=bool)
        if axis == "row"
        else np.ones((min_line_px, 1), dtype=bool)
    )
    opened = ndimage.binary_opening(mask, structure=structure)
    labels, count = ndimage.label(opened, structure=np.ones((3, 3), dtype=np.uint8))
    boxes: list[tuple[int, int, int, int]] = []
    for component_id in range(1, count + 1):
        ys, xs = np.nonzero(labels == component_id)
        if not len(xs):
            continue
        # Inclusive pixel bounds keep a one-pixel extension line centred on its
        # actual source coordinate and a two-pixel antialiased line at x + 0.5.
        boxes.append((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())))
    return sorted(boxes, key=lambda box: (box[1], box[0], box[3], box[2]))


def _cluster_positions(values: list[float], merge_px: float) -> list[float]:
    groups: list[list[float]] = []
    for value in sorted(values):
        if not groups or value - groups[-1][-1] > merge_px:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [float(sum(group) / len(group)) for group in groups]


def _calibration_span_candidates(
    img: Image.Image, recipe: dict[str, Any]
) -> list[dict[str, Any]]:
    """Find line endpoints at perpendicular extension-line intersections.

    These are mechanically neutral candidates: a reader still verifies that a
    candidate is a dimension chain before supplying its endpoints and text
    value to ``px_m_calibrator``.  No OCR or wall/dimension semantics enter the
    detector.
    """

    mask = _foreground_mask(img, recipe)
    min_line = int(recipe["calibration_min_line_px"])
    min_span = float(recipe["calibration_min_span_px"])
    tolerance = float(recipe["calibration_intersection_tolerance_px"])
    merge_px = float(recipe["calibration_intersection_merge_px"])
    rows = _opened_line_boxes(mask, axis="row", min_line_px=min_line)
    cols = _opened_line_boxes(mask, axis="col", min_line_px=min_line)
    raw: list[dict[str, Any]] = []

    for axis, targets, perpendiculars in (("x", rows, cols), ("y", cols, rows)):
        for x0, y0, x1, y1 in targets:
            target_start, target_end = (x0, x1) if axis == "x" else (y0, y1)
            if target_end - target_start < min_span:
                continue
            line_position = (y0 + y1) / 2.0 if axis == "x" else (x0 + x1) / 2.0
            intersections: list[float] = []
            for px0, py0, px1, py1 in perpendiculars:
                perpendicular_position = (
                    (px0 + px1) / 2.0 if axis == "x" else (py0 + py1) / 2.0
                )
                crosses_line = (
                    py0 - tolerance <= line_position <= py1 + tolerance
                    if axis == "x"
                    else px0 - tolerance <= line_position <= px1 + tolerance
                )
                if (
                    crosses_line
                    and target_start - tolerance
                    <= perpendicular_position
                    <= target_end + tolerance
                ):
                    intersections.append(perpendicular_position)
            intersections = _cluster_positions(intersections, merge_px)
            if len(intersections) < 2:
                continue
            px_a, px_b = intersections[0], intersections[-1]
            if px_b - px_a < min_span:
                continue
            p1 = [px_a, line_position] if axis == "x" else [line_position, px_a]
            p2 = [px_b, line_position] if axis == "x" else [line_position, px_b]
            raw.append(
                {
                    "kind": "calibration_span_candidate",
                    "axis": axis,
                    "p1_px": p1,
                    "p2_px": p2,
                    "px_a": px_a,
                    "px_b": px_b,
                    "span_px": px_b - px_a,
                    "dimension_line_position_px": line_position,
                    "extension_line_intersections_px": intersections,
                }
            )

    # Multiple parallel dimension baselines can carry the same endpoint pair.
    # Keep the first in stable scan order; the endpoint evidence is identical.
    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[str, float, float]] = set()
    for candidate in sorted(
        raw,
        key=lambda item: (
            item["axis"],
            item["dimension_line_position_px"],
            item["px_a"],
            item["px_b"],
        ),
    ):
        key = (candidate["axis"], round(candidate["px_a"], 3), round(candidate["px_b"], 3))
        if key not in seen:
            seen.add(key)
            deduplicated.append(candidate)
    return deduplicated


def _runs(flags: np.ndarray, *, min_len: int) -> list[tuple[int, int]]:
    padded = np.concatenate(([False], flags.astype(bool), [False]))
    starts = np.flatnonzero(~padded[:-1] & padded[1:])
    ends = np.flatnonzero(padded[:-1] & ~padded[1:])
    return [(int(s), int(e)) for s, e in zip(starts, ends, strict=True) if int(e - s) >= min_len]


def _projection_peaks(mask: np.ndarray, axis: str, recipe: dict[str, Any]) -> list[dict[str, Any]]:
    if axis not in {"row", "col"}:
        raise ValueError("axis must be 'row' or 'col'")
    orthogonal_len = mask.shape[1] if axis == "row" else mask.shape[0]
    projection = mask.sum(axis=1 if axis == "row" else 0).astype(float) / float(orthogonal_len)
    peaks, props = find_peaks(
        projection,
        prominence=float(recipe["prominence"]),
        distance=int(recipe.get("min_peak_distance_px", 1)),
    )
    widths = peak_widths(projection, peaks, rel_height=0.5) if len(peaks) else ([], [], [], [])
    prominences = props.get("prominences", np.zeros(len(peaks), dtype=float))
    found = []
    for idx, peak_idx in enumerate(peaks):
        left = float(widths[2][idx])
        right = float(widths[3][idx])
        lo = max(0, int(math.floor(left)))
        hi = min(len(projection) - 1, int(math.ceil(right)))
        xs = np.arange(lo, hi + 1, dtype=float)
        weights = projection[lo : hi + 1]
        centroid = float(np.average(xs, weights=weights)) if float(weights.sum()) > 0 else float(peak_idx)
        found.append(
            {
                "axis": axis,
                "position_px": centroid,
                "peak_index_px": int(peak_idx),
                "strength": float(prominences[idx]),
                "fwhm_px": float(widths[0][idx]),
                "fwhm_support_px": [left, right],
            }
        )
    return found


def _line_band_candidates(mask: np.ndarray, recipe: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    min_run = int(recipe["prescan_min_run_px"])
    candidates: list[dict[str, Any]] = []
    peaks: list[dict[str, Any]] = []
    for axis in ("row", "col"):
        for peak in _projection_peaks(mask, axis, recipe):
            left, right = peak["fwhm_support_px"]
            lo = max(0, int(math.floor(left)))
            if axis == "row":
                hi = min(mask.shape[0] - 1, int(math.ceil(right)))
                line_flags = mask[lo : hi + 1, :].any(axis=0)
                line_coord = float(peak["position_px"])
                for start, end in _runs(line_flags, min_len=min_run):
                    candidates.append(
                        {
                            "kind": "line_band_candidate",
                            "axis": axis,
                            "p1_px": [float(start), line_coord],
                            "p2_px": [float(end), line_coord],
                            "strength": peak["strength"],
                            "fwhm_px": peak["fwhm_px"],
                        }
                    )
            else:
                hi = min(mask.shape[1] - 1, int(math.ceil(right)))
                line_flags = mask[:, lo : hi + 1].any(axis=1)
                line_coord = float(peak["position_px"])
                for start, end in _runs(line_flags, min_len=min_run):
                    candidates.append(
                        {
                            "kind": "line_band_candidate",
                            "axis": axis,
                            "p1_px": [line_coord, float(start)],
                            "p2_px": [line_coord, float(end)],
                            "strength": peak["strength"],
                            "fwhm_px": peak["fwhm_px"],
                        }
                    )
            peaks.append(peak)
    candidates.sort(key=lambda c: (c["kind"], c["axis"], c["p1_px"][1], c["p1_px"][0], c["p2_px"][1], c["p2_px"][0]))
    return candidates, peaks


def _cc_box_candidates(mask: np.ndarray, recipe: dict[str, Any]) -> list[dict[str, Any]]:
    labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    boxes = []
    min_area = int(recipe["min_cc_area_px"])
    for comp_id in range(1, count + 1):
        ys, xs = np.nonzero(labels == comp_id)
        area = int(len(xs))
        if area < min_area:
            continue
        boxes.append(
            {
                "kind": "cc_box_candidate",
                "bbox_px": [float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1)],
                "area_px": area,
                "source_component_ids": [int(comp_id)],
            }
        )
    boxes.sort(key=lambda c: (c["bbox_px"][1], c["bbox_px"][0], c["bbox_px"][3], c["bbox_px"][2]))
    return boxes


def _tick_candidates(line_candidates: list[dict[str, Any]], recipe: dict[str, Any]) -> list[dict[str, Any]]:
    min_len = float(recipe["prescan_min_tick_len_px"])
    max_len = float(recipe["prescan_max_tick_len_px"])
    ticks = []
    seen = set()
    for cand in line_candidates:
        x0, y0 = cand["p1_px"]
        x1, y1 = cand["p2_px"]
        length = math.hypot(x1 - x0, y1 - y0)
        if not (min_len <= length <= max_len):
            continue
        key = (round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3))
        if key in seen:
            continue
        seen.add(key)
        ticks.append(
            {
                "kind": "tick_candidate",
                "axis": cand["axis"],
                "p1_px": cand["p1_px"],
                "p2_px": cand["p2_px"],
                "strength": cand["strength"],
                "fwhm_px": cand["fwhm_px"],
            }
        )
    ticks.sort(key=lambda c: (c["axis"], c["p1_px"][1], c["p1_px"][0], c["p2_px"][1], c["p2_px"][0]))
    return ticks


def _geometry(candidate: dict[str, Any]) -> dict[str, Any]:
    if candidate["kind"] == "cc_box_candidate":
        return {"kind": "bbox", "bbox_px": candidate["bbox_px"]}
    return {"kind": "segment", "p1_px": candidate["p1_px"], "p2_px": candidate["p2_px"]}


def _draw_prescan_overlay(image: Image.Image, candidates: list[dict[str, Any]], overlay_path: Path) -> None:
    out = image.copy()
    draw = ImageDraw.Draw(out)
    colors = {
        "line_band_candidate": "orange",
        "cc_box_candidate": "cyan",
        "tick_candidate": "magenta",
        "calibration_span_candidate": "lime",
        "long_line_candidate": "red",
    }
    for idx, candidate in enumerate(candidates, start=1):
        color = colors[candidate["kind"]]
        if candidate["kind"] == "cc_box_candidate":
            x0, y0, x1, y1 = candidate["bbox_px"]
            draw.rectangle((x0, y0, x1, y1), outline=color, width=2)
            label_at = (x0 + 2, y0 + 2)
        else:
            x0, y0 = candidate["p1_px"]
            x1, y1 = candidate["p2_px"]
            width = 3 if candidate["kind"] == "tick_candidate" else 2
            draw.line((x0, y0, x1, y1), fill=color, width=width)
            label_at = ((x0 + x1) / 2 + 2, (y0 + y1) / 2 + 2)
        draw.text(label_at, str(idx), fill=color)
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(overlay_path)


_PRESCAN_CANDIDATE_FILES = {
    "line_band_candidate": "structural_candidates.json",
    "cc_box_candidate": "cc_box_candidates.json",
    "tick_candidate": "tick_candidates.json",
}
_PRESCAN_OVERLAY_FILES = {
    "line_band_candidate": "combined_overlay.png",
    "cc_box_candidate": "cc_box_overlay.png",
    "tick_candidate": "tick_overlay.png",
}
_PRESCAN_ALL_OVERLAY_FILE = "all_candidates_overlay.png"
_CALIBRATION_SPAN_FILE = "calibration_span_candidates.json"
_CALIBRATION_SPAN_OVERLAY_FILE = "calibration_span_overlay.png"
_LONG_STRUCTURAL_FILE = "long_structural_lines.json"
_LONG_STRUCTURAL_OVERLAY_FILE = "long_structural_overlay.png"


def _write_reproducible_json(path: Path, payload: dict[str, Any]) -> None:
    """Append-once JSON writer used by every prescan presentation.

    A repeated run at the same landing may reuse byte-identical evidence, but
    never overwrite a differing document.  ``sort_keys`` plus relative
    presentation paths makes the same image/configuration byte-identical even
    when two runs use different output roots.
    """
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise FileExistsError(
                f"prescan candidates already exist with different content: {path}"
            )
        return
    path.write_text(text, encoding="utf-8")


def _kind_payload(
    payload: dict[str, Any], kind: str, candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    """Small, independently readable view over one candidate kind."""
    return {
        "cv_schema": payload["cv_schema"],
        "source_image": payload["source_image"],
        "tool": payload["tool"],
        "tool_version": payload["tool_version"],
        "recipe_id": payload["recipe_id"],
        "applicability": payload["applicability"],
        "advisory_only": True,
        "candidate_kind": kind,
        "candidate_count": len(candidates),
        "source_candidates": "candidates.json",
        "overlay_path": _PRESCAN_OVERLAY_FILES[kind],
        "results": candidates,
    }


def _derived_candidate_payload(
    payload: dict[str, Any], kind: str, candidates: list[dict[str, Any]], overlay_path: str
) -> dict[str, Any]:
    return {
        "cv_schema": payload["cv_schema"],
        "source_image": payload["source_image"],
        "tool": payload["tool"],
        "tool_version": payload["tool_version"],
        "recipe_id": payload["recipe_id"],
        "applicability": payload["applicability"],
        "advisory_only": True,
        "candidate_kind": kind,
        "candidate_count": len(candidates),
        "derived_from": "source_image_orthogonal_ink_intersections",
        "source_candidates": None,
        "overlay_path": overlay_path,
        "results": candidates,
    }


_PRESCAN_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _candidate_len_px(candidate: dict[str, Any]) -> float:
    x0, y0 = candidate["p1_px"]
    x1, y1 = candidate["p2_px"]
    return math.hypot(x1 - x0, y1 - y0)


def _axis_summary(
    peaks: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Per projection-peak triage summary over the emitted line-band candidates.

    Lets a reader verify one axis band per peak instead of one crop per segment;
    purely derived from the payload, adds no new detection."""
    summary = []
    for peak in sorted(peaks, key=lambda p: (p["axis"], p["position_px"])):
        coord_idx = 1 if peak["axis"] == "row" else 0
        members = [
            c for c in candidates
            if c["kind"] == "line_band_candidate"
            and c["axis"] == peak["axis"]
            and c["p1_px"][coord_idx] == float(peak["position_px"])
        ]
        summary.append(
            {
                "axis": peak["axis"],
                "position_px": float(peak["position_px"]),
                "strength": peak["strength"],
                "fwhm_px": peak["fwhm_px"],
                "run_count": len(members),
                "coverage_px": round(sum(_candidate_len_px(c) for c in members), 1),
                "candidate_ids": [c["candidate_id"] for c in members],
            }
        )
    return summary


def _line_interval(candidate: dict[str, Any]) -> tuple[float, float]:
    if candidate["axis"] == "row":
        return float(candidate["p1_px"][0]), float(candidate["p2_px"][0])
    return float(candidate["p1_px"][1]), float(candidate["p2_px"][1])


def _covers_position(
    candidates: list[dict[str, Any]], position: float, tolerance: float
) -> bool:
    return any(
        start - tolerance <= position <= end + tolerance
        for start, end in (_line_interval(candidate) for candidate in candidates)
    )


def _clipped_interval_union(
    candidates: list[dict[str, Any]], start: float, end: float
) -> list[tuple[float, float]]:
    intervals = sorted(
        (max(start, lo), min(end, hi))
        for lo, hi in (_line_interval(candidate) for candidate in candidates)
        if hi > start and lo < end
    )
    merged: list[tuple[float, float]] = []
    for lo, hi in intervals:
        if not merged or lo > merged[-1][1]:
            merged.append((lo, hi))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
    return merged


def _merged_long_line_candidates(
    line_candidates: list[dict[str, Any]], recipe: dict[str, Any]
) -> list[dict[str, Any]]:
    """Bridge fragmented strong bands between reciprocal line intersections.

    Endpoint support is deliberately two-sided: a row band and a column band
    must each reach their shared intersection.  This clamps the merged segment
    to structural junctions instead of extending it through nearby annotation
    fragments.  Source candidates remain untouched and addressable.
    """

    min_strength = (
        float(recipe["prominence"])
        * float(recipe["prescan_long_line_strength_multiple"])
    )
    min_length = float(recipe["prescan_long_line_min_px"])
    tolerance = float(recipe["prescan_long_line_intersection_tolerance_px"])
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = {}
    for candidate in line_candidates:
        if float(candidate["strength"]) < min_strength:
            continue
        position = (
            float(candidate["p1_px"][1])
            if candidate["axis"] == "row"
            else float(candidate["p1_px"][0])
        )
        grouped.setdefault((candidate["axis"], position), []).append(candidate)

    rows = {
        position: candidates
        for (axis, position), candidates in grouped.items()
        if axis == "row"
    }
    cols = {
        position: candidates
        for (axis, position), candidates in grouped.items()
        if axis == "col"
    }
    row_intersections: dict[float, list[float]] = {position: [] for position in rows}
    col_intersections: dict[float, list[float]] = {position: [] for position in cols}
    for row_position, row_candidates in sorted(rows.items()):
        for col_position, col_candidates in sorted(cols.items()):
            if _covers_position(
                row_candidates, col_position, tolerance
            ) and _covers_position(col_candidates, row_position, tolerance):
                row_intersections[row_position].append(col_position)
                col_intersections[col_position].append(row_position)

    merged_candidates: list[dict[str, Any]] = []
    for axis, groups, intersections in (
        ("row", rows, row_intersections),
        ("col", cols, col_intersections),
    ):
        for position, source_group in sorted(groups.items()):
            supports = sorted(set(intersections[position]))
            if len(supports) < 2:
                continue
            start, end = supports[0], supports[-1]
            if end - start < min_length:
                continue
            source_candidates = [
                candidate
                for candidate in source_group
                if _line_interval(candidate)[1] > start
                and _line_interval(candidate)[0] < end
            ]
            intervals = _clipped_interval_union(source_candidates, start, end)
            coverage = sum(hi - lo for lo, hi in intervals)
            gaps = [
                [intervals[index][1], intervals[index + 1][0]]
                for index in range(len(intervals) - 1)
                if intervals[index + 1][0] > intervals[index][1]
            ]
            p1 = [start, position] if axis == "row" else [position, start]
            p2 = [end, position] if axis == "row" else [position, end]
            merged_candidates.append(
                {
                    "kind": "long_line_candidate",
                    "axis": axis,
                    "p1_px": p1,
                    "p2_px": p2,
                    "length_px": end - start,
                    "strength": float(source_group[0]["strength"]),
                    "fwhm_px": float(source_group[0]["fwhm_px"]),
                    "source_candidate_ids": [
                        candidate["candidate_id"] for candidate in source_candidates
                    ],
                    "source_fragment_count": len(source_candidates),
                    "support_coverage_px": coverage,
                    "support_ratio": coverage / (end - start),
                    "bridged_gaps_px": gaps,
                    "orthogonal_intersections_px": supports,
                    "merge_method": "reciprocal_orthogonal_intersections_v1",
                }
            )
    return sorted(
        merged_candidates,
        key=lambda candidate: (
            candidate["axis"],
            candidate["p1_px"][1],
            candidate["p1_px"][0],
            candidate["p2_px"][1],
            candidate["p2_px"][0],
        ),
    )


def _prescan(
    image: str | Path,
    *,
    out_dir: str | Path,
    tool: str,
    recipe_id: str = "clean_vector_v1",
    capability_profile: str = "orthogonal_polygon",
    include_cc: bool = True,
    min_strength: float | None = None,
    min_line_len_px: float | None = None,
    label: str = "prescan",
) -> tuple[Path, Path]:
    if capability_profile not in SUPPORTED_PRESCAN_CAPABILITY_PROFILES:
        supported = ", ".join(SUPPORTED_PRESCAN_CAPABILITY_PROFILES)
        raise NotImplementedError(
            f"prescan capability_profile {capability_profile!r} is not implemented; supported: {supported}"
        )
    if not _PRESCAN_LABEL_RE.match(label):
        raise ValueError(f"prescan label must match {_PRESCAN_LABEL_RE.pattern}, got {label!r}")
    recipe = get_recipe(recipe_id)
    source = Path(image)
    img = _load_rgb(source)
    mask = _mask_clean_vector(img, recipe)
    line_candidates, peaks = _line_band_candidates(mask, recipe)
    cc_candidates = _cc_box_candidates(mask, recipe) if include_cc else []
    calibration_spans = _calibration_span_candidates(img, recipe)
    # Ticks are calibration anchors: always derived from the unfiltered line
    # candidates so a triage filter can never drop dimension ticks.
    tick_candidates = _tick_candidates(line_candidates, recipe)
    prefilter_line_count = len(line_candidates)
    if min_strength is not None:
        line_candidates = [c for c in line_candidates if c["strength"] >= float(min_strength)]
    if min_line_len_px is not None:
        line_candidates = [
            c for c in line_candidates if _candidate_len_px(c) >= float(min_line_len_px)
        ]
    raw_candidates = line_candidates + cc_candidates + tick_candidates

    candidates = []
    source_hash = sha256_short(source)
    for idx, candidate in enumerate(raw_candidates, start=1):
        item = dict(candidate)
        item["candidate_id"] = f"{source.stem}:{tool}:{idx:03d}"
        item["coord_space"] = "source_px"
        item["geometry"] = _geometry(candidate)
        item["provenance"] = {
            "tool": tool,
            "tool_version": TOOL_VERSION,
            "recipe_id": recipe["recipe_id"],
            "source_image_sha256": source_hash,
            "crop_chain_id": "root",
        }
        candidates.append(item)

    for idx, candidate in enumerate(calibration_spans, start=1):
        candidate["candidate_id"] = f"{source.stem}:{tool}:calibration_span:{idx:03d}"
        candidate["coord_space"] = "source_px"
        candidate["geometry"] = _geometry(candidate)
        candidate["provenance"] = {
            "tool": tool,
            "tool_version": TOOL_VERSION,
            "recipe_id": recipe["recipe_id"],
            "source_image_sha256": source_hash,
            "crop_chain_id": "root",
        }

    long_structural_lines = _merged_long_line_candidates(
        [
            candidate
            for candidate in candidates
            if candidate["kind"] == "line_band_candidate"
        ],
        recipe,
    )
    for idx, candidate in enumerate(long_structural_lines, start=1):
        candidate["candidate_id"] = f"{source.stem}:{tool}:long_line:{idx:03d}"
        candidate["coord_space"] = "source_px"
        candidate["geometry"] = _geometry(candidate)
        candidate["provenance"] = {
            "tool": tool,
            "tool_version": TOOL_VERSION,
            "recipe_id": recipe["recipe_id"],
            "source_image_sha256": source_hash,
            "crop_chain_id": "root",
        }

    prescan_dir = evidence_dir(out_dir, source) / label
    candidates_path = prescan_dir / "candidates.json"
    overlay_path = prescan_dir / _PRESCAN_OVERLAY_FILES["line_band_candidate"]
    all_overlay_path = prescan_dir / _PRESCAN_ALL_OVERLAY_FILE
    candidates_by_kind = {
        kind: [candidate for candidate in candidates if candidate["kind"] == kind]
        for kind in _PRESCAN_CANDIDATE_FILES
    }

    payload = {
        "cv_schema": "1",
        "source_image": {"name": source.name, "sha256": source_hash},
        "crop_chain": [],
        # Presentation paths are relative to this document.  Besides being
        # portable inside staging, this is what makes output bytes independent
        # of the caller's absolute out_dir.
        "overlay_path": overlay_path.name,
        "candidate_files": {
            "all": candidates_path.name,
            "structural": _PRESCAN_CANDIDATE_FILES["line_band_candidate"],
            "cc_boxes": _PRESCAN_CANDIDATE_FILES["cc_box_candidate"],
            "ticks": _PRESCAN_CANDIDATE_FILES["tick_candidate"],
        },
        "derived_candidate_files": {
            "calibration_spans": _CALIBRATION_SPAN_FILE,
            "long_structural_lines": _LONG_STRUCTURAL_FILE,
        },
        "overlay_paths": {
            "default_structural": overlay_path.name,
            "all": all_overlay_path.name,
            "cc_boxes": _PRESCAN_OVERLAY_FILES["cc_box_candidate"],
            "ticks": _PRESCAN_OVERLAY_FILES["tick_candidate"],
        },
        "derived_overlay_paths": {
            "calibration_spans": _CALIBRATION_SPAN_OVERLAY_FILE,
            "long_structural_lines": _LONG_STRUCTURAL_OVERLAY_FILE,
        },
        "tool": tool,
        "tool_version": TOOL_VERSION,
        "recipe_id": recipe["recipe_id"],
        "applicability": recipe["applicability"],
        "capability_profile": {
            "requested": capability_profile,
            "supported": list(SUPPORTED_PRESCAN_CAPABILITY_PROFILES),
        },
        "params": {
            "capability_profile": capability_profile,
            "include_cc": include_cc,
            "advisory_only": True,
            "min_strength": min_strength,
            "min_line_len_px": min_line_len_px,
            "label": label,
        },
        "results": candidates,
        "diagnostics": {
            "image_size_px": list(img.size),
            "mask_pixels": int(mask.sum()),
            "projection_peak_count": len(peaks),
            "line_band_candidate_count": len(line_candidates),
            "line_band_candidate_count_prefilter": prefilter_line_count,
            "cc_box_candidate_count": len(cc_candidates),
            "tick_candidate_count": len(tick_candidates),
            "calibration_span_candidate_count": len(calibration_spans),
            "long_structural_line_count": len(long_structural_lines),
            "axis_summary": _axis_summary(peaks, candidates),
        },
    }
    # The legacy candidates.json remains the lossless all-candidate source.
    # Kind views only change addressability; their concatenated IDs are exactly
    # the master IDs (locked in tests).  The old all-candidate overlay likewise
    # remains reachable under a precise name, while combined_overlay.png now
    # defaults to structural line bands only.
    _write_reproducible_json(candidates_path, payload)
    for kind, filename in _PRESCAN_CANDIDATE_FILES.items():
        _write_reproducible_json(
            prescan_dir / filename,
            _kind_payload(payload, kind, candidates_by_kind[kind]),
        )
    _write_reproducible_json(
        prescan_dir / _CALIBRATION_SPAN_FILE,
        _derived_candidate_payload(
            payload,
            "calibration_span_candidate",
            calibration_spans,
            _CALIBRATION_SPAN_OVERLAY_FILE,
        ),
    )
    _write_reproducible_json(
        prescan_dir / _LONG_STRUCTURAL_FILE,
        _derived_candidate_payload(
            payload,
            "long_line_candidate",
            long_structural_lines,
            _LONG_STRUCTURAL_OVERLAY_FILE,
        ),
    )

    _draw_prescan_overlay(img, candidates_by_kind["line_band_candidate"], overlay_path)
    _draw_prescan_overlay(img, candidates, all_overlay_path)
    for kind in ("cc_box_candidate", "tick_candidate"):
        _draw_prescan_overlay(
            img,
            candidates_by_kind[kind],
            prescan_dir / _PRESCAN_OVERLAY_FILES[kind],
        )
    _draw_prescan_overlay(
        img,
        calibration_spans,
        prescan_dir / _CALIBRATION_SPAN_OVERLAY_FILE,
    )
    _draw_prescan_overlay(
        img,
        long_structural_lines,
        prescan_dir / _LONG_STRUCTURAL_OVERLAY_FILE,
    )
    return candidates_path, overlay_path


def prescan_plan(
    image: str | Path,
    *,
    out_dir: str | Path,
    recipe_id: str = "clean_vector_v1",
    capability_profile: str = "orthogonal_polygon",
    include_cc: bool = True,
    min_strength: float | None = None,
    min_line_len_px: float | None = None,
    label: str = "prescan",
) -> tuple[Path, Path]:
    """Write deterministic plan prescan candidates and a combined overlay."""

    return _prescan(
        image,
        out_dir=out_dir,
        tool="prescan-plan",
        recipe_id=recipe_id,
        capability_profile=capability_profile,
        include_cc=include_cc,
        min_strength=min_strength,
        min_line_len_px=min_line_len_px,
        label=label,
    )


def prescan_elevation(
    image: str | Path,
    *,
    out_dir: str | Path,
    recipe_id: str = "clean_vector_v1",
    capability_profile: str = "rectangular",
    include_cc: bool = True,
    min_strength: float | None = None,
    min_line_len_px: float | None = None,
    label: str = "prescan",
) -> tuple[Path, Path]:
    """Write deterministic elevation prescan candidates and a combined overlay."""

    return _prescan(
        image,
        out_dir=out_dir,
        tool="prescan-elevation",
        recipe_id=recipe_id,
        capability_profile=capability_profile,
        include_cc=include_cc,
        min_strength=min_strength,
        min_line_len_px=min_line_len_px,
        label=label,
    )
