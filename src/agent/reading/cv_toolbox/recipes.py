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
    "prescan_min_run_px": 4,
    "prescan_min_tick_len_px": 6,
    "prescan_max_tick_len_px": 40,
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

    prescan_dir = evidence_dir(out_dir, source) / label
    candidates_path = prescan_dir / "candidates.json"
    overlay_path = prescan_dir / "combined_overlay.png"
    _draw_prescan_overlay(img, candidates, overlay_path)

    payload = {
        "cv_schema": "1",
        "source_image": {"name": source.name, "sha256": source_hash},
        "crop_chain": [],
        "overlay_path": str(overlay_path),
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
            "axis_summary": _axis_summary(peaks, candidates),
        },
    }
    payload_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    if candidates_path.exists():
        if candidates_path.read_text(encoding="utf-8") != payload_text:
            raise FileExistsError(f"prescan candidates already exist with different content: {candidates_path}")
    else:
        candidates_path.write_text(payload_text, encoding="utf-8")
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
