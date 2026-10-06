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


def height_locations(artifact, match, size):
    calibration = artifact["x_calibration"]
    hs = (calibration["world_end_m"] - calibration["world_start_m"]) / (
        calibration["pixel_end"] - calibration["pixel_start"])
    ho = calibration["world_start_m"] - hs * calibration["pixel_start"]
    tolerance = match["tolerances_m"]

    def inside(box):
        return 0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1]

    # A vertical dimension-chain crop is not a pixel anchor for its top label.
    bands = [row for row in artifact["elevations"] if row["evidence_type"] in IMAGE_EVIDENCE
             and inside(row["bbox"]) and row["bbox"][2] - row["bbox"][0] >= 4 * (row["bbox"][3] - row["bbox"][1])
             and (row["bbox"][3] - row["bbox"][1]) / 2 * abs(hs) <= tolerance["position"]]
    pairs = [(a, b) for a, b in combinations(bands, 2) if a["value_m"] != b["value_m"]
             and (a["bbox"][3] < b["bbox"][1] or b["bbox"][3] < a["bbox"][1])]
    result = {"artifact_sha256": artifact["artifact_sha256"], "x_calibration": calibration,
              "status": "missing_vertical_frame", "openings": {}}
    if not bands:
        return result
    anchors = list(max(pairs, key=lambda pair: abs(pair[1]["value_m"] - pair[0]["value_m"]))) if pairs else [min(
        bands, key=lambda row: (row["bbox"][3] - row["bbox"][1], row["id"]))]
    ys = [(row["bbox"][1] + row["bbox"][3]) / 2 for row in anchors]
    zs = ((anchors[1]["value_m"] - anchors[0]["value_m"]) / (ys[1] - ys[0])
          if len(anchors) == 2 else -abs(hs))
    if zs >= 0:
        result["status"] = "inconsistent_vertical_frame"
        return result
    zo = anchors[0]["value_m"] - zs * ys[0]

    def uncertainty(z):
        half = [(row["bbox"][3] - row["bbox"][1]) / 2 for row in anchors]
        if len(anchors) == 1:
            return half[0]
        fraction = (z - anchors[0]["value_m"]) / (anchors[1]["value_m"] - anchors[0]["value_m"])
        return abs(1 - fraction) * half[0] + abs(fraction) * half[1]

    def vertical_fits(row):
        pad = max(uncertainty(row["sill_m"]), uncertainty(row["head_m"]))
        return (row["bbox"][1] - pad - 2 <= (row["head_m"] - zo) / zs
                and (row["sill_m"] - zo) / zs <= row["bbox"][3] + pad + 2)

    observed = [row for row in artifact["openings"] if row["evidence_type"] in IMAGE_EVIDENCE]
    if len(anchors) == 1 and (len(observed) < 2 or not all(vertical_fits(row) for row in observed)):
        # One level alone cannot establish scale. Permit a square-pixel scale
        # estimate only when at least two independently located opening readings
        # corroborate it within the supplied anchor band. Never fit their BIM Z.
        result["status"] = "uncorroborated_vertical_scale"
        return result
    if any(not row["bbox"][1] - uncertainty(row["value_m"]) - 2 <= (row["value_m"] - zo) / zs
           <= row["bbox"][3] + uncertainty(row["value_m"]) + 2 for row in bands):
        result["status"] = "conflicting_level_bands"
        return result
    result.update(status="prepared", vertical_method=("two_observed_level_bands" if len(anchors) == 2
        else "horizontal_scale_corroborated_by_opening_regions"), level_anchors=anchors,
        transform={"horizontal_metres_per_pixel": hs, "horizontal_offset_m": ho,
                   "z_metres_per_pixel": zs, "z_offset_m": zo})
    by_id = {row["id"]: row for row in artifact["openings"]}
    for matched in match["matches"]:
        row = by_id[matched["artifact_opening_id"]]
        original = row["bbox"]
        item = {"source_opening_id": matched["source_opening_id"], "original_bbox": original,
                "status": "unlocated_reader_region"}
        result["openings"][row["id"]] = item
        if row["evidence_type"] not in IMAGE_EVIDENCE:
            item["status"] = "non_image_evidence"
            continue
        if (not inside(original) or original[0] - 2 > row["x_px"][0]
                or original[2] + 2 < row["x_px"][1] or not vertical_fits(row)):
            continue
        # These are context crops in the unchanged original, not new observations.
        hp = (tolerance["position"] + tolerance["width"] / 2) / abs(hs)
        vp = max(uncertainty(row["sill_m"]), uncertainty(row["head_m"]))
        box = [max(0, math.floor(original[0] - hp)), max(0, math.floor(original[1] - vp)),
               min(size[0], math.ceil(original[2] + hp)), min(size[1], math.ceil(original[3] + vp))]
        if box == [0, 0, *size] or any(other["id"] != row["id"]
                and box[0] <= other["bbox"][0] and box[1] <= other["bbox"][1]
                and box[2] >= other["bbox"][2] and box[3] >= other["bbox"][3]
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
