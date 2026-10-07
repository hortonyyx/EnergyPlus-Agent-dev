"""Carry reader coordinates into the existing located-height report.

No BIM coordinates are fitted here. Level bands and image scale come from the
immutable reading; source regions get the *existing matcher*'s horizontal
tolerance and the level bands' vertical uncertainty, not a box reverse-fitted
to the candidate. The original boxes and every derivation remain in the receipt.
"""

from __future__ import annotations

import hashlib
import json
import math
from itertools import combinations

from src.agent_runtime.store import json_bytes

IMAGE_EVIDENCE = {"annotation", "annotation_and_pixels", "pixels", "visual_estimate"}


def derive_z_calibration(
    elevations,
    *,
    max_residual_m=0.10,
    max_half_band_uncertainty_m=0.35,
):
    """Derive image-Y to absolute-Z from two saved horizontal level bands.

    This consumes only reader image evidence.  It never fits a candidate BIM,
    GT, or opening heights.  Wide horizontal bands provide their vertical
    centre; the pair with the greatest absolute Z span wins after requiring a
    negative pixel/Z slope and bounded half-band uncertainty.  Every other
    saved horizontal level remains an independent residual check.
    """

    points = []
    for row in elevations or ():
        box = row.get("bbox") if isinstance(row, dict) else None
        value = row.get("value_m") if isinstance(row, dict) else None
        evidence_type = row.get("evidence_type") if isinstance(row, dict) else None
        if (evidence_type not in IMAGE_EVIDENCE
                or not isinstance(box, list) or len(box) != 4
                or not isinstance(value, (int, float)) or isinstance(value, bool)):
            continue
        left, top, right, bottom = (float(item) for item in box)
        if not all(math.isfinite(item) for item in (left, top, right, bottom, float(value))):
            continue
        band_height = bottom - top
        if band_height <= 0 or right - left < 4 * band_height:
            continue
        points.append({
            "id": row.get("id"),
            "kind": row.get("kind"),
            "bbox": [left, top, right, bottom],
            "y_px": (top + bottom) / 2,
            "z_m": float(value),
            "half_band_px": band_height / 2,
        })

    choices = []
    for first, second in combinations(points, 2):
        pixel_delta = second["y_px"] - first["y_px"]
        world_delta = second["z_m"] - first["z_m"]
        if pixel_delta == 0 or world_delta == 0 or pixel_delta * world_delta >= 0:
            continue
        slope = world_delta / pixel_delta
        uncertainty = max(first["half_band_px"], second["half_band_px"]) * abs(slope)
        if uncertainty > max_half_band_uncertainty_m + 1e-9:
            continue
        choices.append((abs(world_delta), abs(pixel_delta), first, second, slope, uncertainty))

    evidence = {
        "status": "missing_two_horizontal_level_bands",
        "method": "furthest_absolute_Z_pair_using_horizontal_band_centres",
        "points": points,
        "max_abs_residual_m": None,
    }
    if not choices:
        return evidence

    _, _, first, second, slope, uncertainty = max(
        choices, key=lambda item: (item[0], item[1])
    )
    if first["y_px"] > second["y_px"]:
        first, second = second, first
    calibration = {
        "pixel_start": first["y_px"],
        "pixel_end": second["y_px"],
        "world_start_m": first["z_m"],
        "world_end_m": second["z_m"],
    }
    slope = (
        calibration["world_end_m"] - calibration["world_start_m"]
    ) / (calibration["pixel_end"] - calibration["pixel_start"])
    offset = calibration["world_start_m"] - slope * calibration["pixel_start"]
    residuals = []
    for point in points:
        predicted = slope * point["y_px"] + offset
        residuals.append({
            **point,
            "predicted_z_m": predicted,
            "residual_m": predicted - point["z_m"],
        })
    max_residual = max(abs(row["residual_m"]) for row in residuals)
    evidence.update(
        status="derived_from_saved_level_lines",
        calibration=calibration,
        selected=[first, second],
        points=residuals,
        max_abs_residual_m=max_residual,
        selected_max_half_band_uncertainty_m=uncertainty,
    )
    if max_residual > max_residual_m + 1e-9:
        evidence.update(
            status="rejected_inconsistent_saved_level_lines",
            reason="saved horizontal level residual exceeds the accepted limit",
        )
        evidence.pop("calibration", None)
    return evidence


def height_locations(artifact, match, size):
    calibration = artifact["x_calibration"]
    hs = (calibration["world_end_m"] - calibration["world_start_m"]) / (
        calibration["pixel_end"] - calibration["pixel_start"])
    ho = calibration["world_start_m"] - hs * calibration["pixel_start"]
    tolerance = match["tolerances_m"]

    def inside(box):
        return 0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1]

    bands = [row for row in artifact["elevations"] if row["evidence_type"] in IMAGE_EVIDENCE
             and inside(row["bbox"]) and row["bbox"][2] - row["bbox"][0] >= 4 * (row["bbox"][3] - row["bbox"][1])
             and (row["bbox"][3] - row["bbox"][1]) / 2 * abs(hs) <= tolerance["position"]]
    pairs = [(a, b) for a, b in combinations(bands, 2) if a["value_m"] != b["value_m"]
             and (a["bbox"][3] < b["bbox"][1] or b["bbox"][3] < a["bbox"][1])]
    derived = derive_z_calibration(artifact.get("elevations", ()))
    explicit = artifact.get("z_calibration")
    result = {"artifact_sha256": artifact["artifact_sha256"], "x_calibration": calibration,
              "z_calibration_evidence": derived,
              "status": "missing_vertical_frame", "openings": {}}
    aligned_by_id = {
        row.get("id"): row.get("effective_bbox_px", row.get("aligned_bbox_px"))
        for row in artifact.get("ink_alignment", {}).get("openings", ())
        if isinstance(row, dict)
    }

    def opening_box(row):
        candidate = aligned_by_id.get(row["id"])
        if (isinstance(candidate, list) and len(candidate) == 4
                and all(isinstance(value, (int, float)) for value in candidate)):
            return candidate
        candidate = row.get("opening_bbox")
        if isinstance(candidate, list) and len(candidate) == 4:
            return candidate
        # Read compatibility for immutable pre-Q2 submissions.
        return row["bbox"]

    if explicit is not None:
        anchors = []
        zs = (explicit["world_end_m"] - explicit["world_start_m"]) / (
            explicit["pixel_end"] - explicit["pixel_start"])
        zo = explicit["world_start_m"] - zs * explicit["pixel_start"]

        def uncertainty(z):
            return 2.0

        vertical_method = "explicit_z_calibration"
    else:
        if not bands:
            return result
        anchors = list(max(pairs, key=lambda pair: abs(pair[1]["value_m"] - pair[0]["value_m"]))) if pairs else [min(
            bands, key=lambda row: (row["bbox"][3] - row["bbox"][1], row["id"]))]
        ys = [(row["bbox"][1] + row["bbox"][3]) / 2 for row in anchors]
        zs = ((anchors[1]["value_m"] - anchors[0]["value_m"]) / (ys[1] - ys[0])
              if len(anchors) == 2 else -abs(hs))
        zo = anchors[0]["value_m"] - zs * ys[0]

        def uncertainty(z):
            half = [(row["bbox"][3] - row["bbox"][1]) / 2 for row in anchors]
            if len(anchors) == 1:
                return half[0]
            fraction = (z - anchors[0]["value_m"]) / (
                anchors[1]["value_m"] - anchors[0]["value_m"])
            return abs(1 - fraction) * half[0] + abs(fraction) * half[1]

        vertical_method = ("two_observed_level_bands" if len(anchors) == 2
                           else "horizontal_scale_corroborated_by_opening_regions")

    if zs >= 0:
        result["status"] = "inconsistent_vertical_frame"
        return result

    def vertical_fits(row):
        region = opening_box(row)
        pad = max(uncertainty(row["sill_m"]), uncertainty(row["head_m"]))
        return (region[1] - pad - 2 <= (row["head_m"] - zo) / zs
                and (row["sill_m"] - zo) / zs <= region[3] + pad + 2)

    observed = [row for row in artifact["openings"] if row["evidence_type"] in IMAGE_EVIDENCE]
    if explicit is None and len(anchors) == 1 and (
            len(observed) < 2 or not all(vertical_fits(row) for row in observed)):
        result["status"] = "uncorroborated_vertical_scale"
        return result
    if explicit is None and any(not row["bbox"][1] - uncertainty(row["value_m"]) - 2
            <= (row["value_m"] - zo) / zs
            <= row["bbox"][3] + uncertainty(row["value_m"]) + 2 for row in bands):
        result["status"] = "conflicting_level_bands"
        return result
    result.update(status="prepared", vertical_method=vertical_method,
        level_anchors=anchors, z_calibration=explicit,
        transform={"horizontal_metres_per_pixel": hs, "horizontal_offset_m": ho,
                   "z_metres_per_pixel": zs, "z_offset_m": zo})
    by_id = {row["id"]: row for row in artifact["openings"]}
    for matched in match["matches"]:
        row = by_id[matched["artifact_opening_id"]]
        original = row["bbox"]
        located = opening_box(row)
        item = {"source_opening_id": matched["source_opening_id"], "original_bbox": original,
                "aligned_opening_bbox": located,
                "status": "unlocated_reader_region"}
        result["openings"][row["id"]] = item
        if row["evidence_type"] not in IMAGE_EVIDENCE:
            item["status"] = "non_image_evidence"
            continue
        if not inside(located) or not vertical_fits(row):
            continue
        # These are context crops in the unchanged original, not new observations.
        hp = (tolerance["position"] + tolerance["width"] / 2) / abs(hs)
        vp = max(uncertainty(row["sill_m"]), uncertainty(row["head_m"]))
        box = [max(0, math.floor(located[0] - hp)), max(0, math.floor(located[1] - vp)),
               min(size[0], math.ceil(located[2] + hp)), min(size[1], math.ceil(located[3] + vp))]
        if box == [0, 0, *size] or any(other["id"] != row["id"]
                and box[0] <= opening_box(other)[0] and box[1] <= opening_box(other)[1]
                and box[2] >= opening_box(other)[2] and box[3] >= opening_box(other)[3]
                for other in artifact["openings"]):
            item["status"] = "non_unique_reader_region"
            continue
        item.update(status="prepared", source_box=box,
                    padding_pixels={"horizontal": hp, "vertical": vp},
                    horizontal_tolerances_m=tolerance)
    return result


def carry_height_evidence(session, saved_match, artifact, entries):
    """Persist an idempotent calibration before the single atomic height write."""
    name = artifact["image"]
    info = session.manifest["images"][name]
    task = session.registry.task(saved_match["task_id"])
    raw = (session.run_directory / "images" / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != info["sha256"] or task["input_sha256"] != info["sha256"]:
        raise ValueError("height evidence original changed since reader admission")
    location = height_locations(artifact, saved_match["result"], info["size"])
    if location["status"] != "prepared":
        return location
    record = {"schema_version": "role_height_calibration_v1", "image": name,
        "image_sha256": info["sha256"], "facade": artifact["orientation"],
        "transform": location["transform"], "role_height_evidence": location,
        "reader_task_id": saved_match["task_id"],
        "reader_artifact_sha256": session.registry.records[saved_match["task_id"]]["artifact"]["sha256"],
        "basis": "Reader coordinate transfer; level-band uncertainty and existing horizontal matching tolerance. "
                 "Original regions retained; no source-geometry fit and no new visual observation."}
    identity = hashlib.sha256(json_bytes(record)).hexdigest()
    folder = session.run_directory / "elevation_reviews"
    folder.mkdir(exist_ok=True)
    existing = [json.loads(path.read_bytes()) for path in sorted(folder.glob("review_*.json"))]
    prior = next((row for row in existing if row.get("role_evidence_id") == identity), None)
    if prior is not None:
        if {k: v for k, v in prior.items() if k != "role_evidence_id"} != record:
            raise ValueError("saved role height calibration changed")
    else:
        # Share the existing chronological namespace so a later explicit overlay
        # can supersede this calibration normally. A retry reuses this record.
        index = len(existing) + 1
        while True:
            try:
                with (folder / f"review_{index:04d}.json").open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(json.dumps({**record, "role_evidence_id": identity}, ensure_ascii=False, indent=2) + "\n")
                break
            except FileExistsError:
                index += 1
    for entry, matched in zip(entries, saved_match["result"]["matches"], strict=True):
        item = location["openings"][matched["artifact_opening_id"]]
        if item["status"] != "prepared":
            continue
        entry["claim"]["sources"][0]["box"] = item["source_box"]
        reason = entry["reason"] + " Located reader context: " + json.dumps({
            "calibration_id": identity, **item}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        entry["reason"] = entry["claim"]["reason"] = entry["operations"][0]["reason"] = reason
    return {**location, "calibration_id": identity}
