"""Read-only facade evidence checks for T1; never approve or edit geometry.

GLM sm24 linked every opening to its facade but spread one height chain over
different window widths. A whole-image citation or missing calibration cannot
establish per-opening location. Report those limits separately from a measured
source-region miss; all remain advisory, including on delivery.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from statistics import median

from src.agent.execution.bim_height_coverage import height_coverage


def _calibrations(toolkit):
    """Latest explicit original-image/facade transform; no inference from names."""
    latest, problems = {}, []
    for path in sorted((toolkit.run / "elevation_reviews").glob("review_*.json")):
        row = json.loads(path.read_text())
        if "transform" not in row or "image" not in row:
            continue
        key = row["image"], row["facade"]
        latest[key] = row
    for key, row in list(latest.items()):
        info = toolkit.manifest.get("images", {}).get(row["image"], {})
        if info.get("sha256") != row.get("image_sha256"):
            problems.append(dict(image=key[0], facade=key[1], reason="calibration_image_changed"))
            del latest[key]
            continue
        try:
            toolkit.image_path(row["image"])
            transform = row["transform"]
            values = [transform[k] for k in ("horizontal_metres_per_pixel", "horizontal_offset_m", "z_metres_per_pixel", "z_offset_m")]
            if not all(math.isfinite(v) for v in values) or values[0] == 0 or values[2] == 0:
                raise ValueError("invalid transform")
        except (OSError, ValueError, KeyError, TypeError) as error:
            problems.append(dict(image=key[0], facade=key[1], reason=str(error)))
            del latest[key]
    return latest, problems


def _pixel_box(opening, facade, transform):
    axis = 0 if facade in {"North", "South"} else 1
    points = [((v[axis] - transform["horizontal_offset_m"]) / transform["horizontal_metres_per_pixel"],
               (v[2] - transform["z_offset_m"]) / transform["z_metres_per_pixel"])
              for v in opening["vertices"]]
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def located_height_report(toolkit, candidate, current_state=None):
    store = toolkit.claims()
    _, source = store.candidate(candidate)
    coverage = height_coverage(store, candidate, current_state)
    openings = {o["id"]: o for o in source.get("openings", [])}
    claims = {row["id"]: row for row in store.status()["claims"]}
    calibrations, calibration_problems = _calibrations(toolkit)
    rows, groups, binding_widths = [], defaultdict(list), defaultdict(list)
    for item in coverage["openings"]:
        identity, facade = item["opening_id"], item.get("facade")
        opening = openings[identity]
        if not opening.get("exterior") or opening.get("kind") not in {"window", "door"}:
            continue
        vertices = opening["vertices"]
        width = math.hypot(max(v[0] for v in vertices) - min(v[0] for v in vertices),
                           max(v[1] for v in vertices) - min(v[1] for v in vertices))
        row = dict(opening_id=identity, kind=opening["kind"], facade=facade,
                   floor_ids=item["floor_ids"], width_m=round(width, 3),
                   status="no_height_observation", claim_ids=[], covered_by=[])
        attempts = []
        for link in item["retained_image_evidence"]:
            record = claims.get(link["claim_id"])
            if record is None:
                continue
            row["claim_ids"].append(link["claim_id"])
            binding_widths[(link["claim_id"], link["value"], facade, tuple(item["floor_ids"]))].append((identity, width))
            for ref in record["sources"]:
                # Validate the current bytes against both the input manifest and claim.
                info = toolkit.manifest.get("images", {}).get(ref["image"], {})
                if ref.get("sha256") != info.get("sha256"):
                    attempts.append("source_image_changed")
                    continue
                calibrated = calibrations.get((ref["image"], facade))
                if calibrated is None:
                    attempts.append("no_elevation_calibration")
                    continue
                box = ref["box"]
                if box == [0, 0, *ref["size"]]:
                    attempts.append("whole_image_only")
                    continue
                projected = _pixel_box(opening, facade, calibrated["transform"])
                # Two original pixels absorb drawing/rounding noise, not a facade-wide inference.
                if (box[0] - 2 <= projected[0] and box[1] - 2 <= projected[1]
                        and box[2] + 2 >= projected[2] and box[3] + 2 >= projected[3]):
                    row["covered_by"].append(dict(claim_id=link["claim_id"], image=ref["image"],
                        source_box=box, opening_box=[round(v, 2) for v in projected],
                        calibration=calibrated.get("review_file")))
                    attempts.append("covered")
                else:
                    attempts.append("outside_source_region")
        if row["covered_by"]:
            row["status"] = "covered"
        elif attempts:
            row["status"] = next((state for state in ("outside_source_region", "whole_image_only", "no_elevation_calibration", "source_image_changed")
                                  if state in attempts), "no_height_observation")
        row["claim_ids"] = sorted(set(row["claim_ids"]))
        if row["kind"] == "window" and facade:
            groups[(tuple(row["floor_ids"]), facade)].append(row)
        rows.append(row)
    shared_risks = set()
    for values in binding_widths.values():
        if len(values) < 2:
            continue
        typical = median(width for _, width in values)
        shared_risks.update(identity for identity, width in values
                            if typical > 0 and abs(width - typical) >= .5
                            and (width >= typical * 1.5 or width <= typical / 1.5))
    for grouped in groups.values():
        typical = median(row["width_m"] for row in grouped)
        for row in grouped:
            width = row["width_m"]
            row["distinct_width_on_facade"] = (len(grouped) > 1 and typical > 0 and abs(width - typical) >= .5
                                                and (width >= typical * 1.5 or width <= typical / 1.5))
    for row in rows:
        row["shared_height_across_widths"] = row["opening_id"] in shared_risks
    uncovered = [row for row in rows if row["status"] != "covered"]
    return dict(schema_version="located_opening_heights_v1", candidate=candidate,
        source_model_sha256=source["source_model_sha256"], delivery_blocked=False,
        summary=dict(exterior_count=len(rows), located_count=len(rows) - len(uncovered),
                     status_counts=dict(Counter(row["status"] for row in rows))),
        openings=rows, unchecked_opening_ids=[row["opening_id"] for row in uncovered],
        priority_opening_ids=[row["opening_id"] for row in uncovered if row["shared_height_across_widths"]],
        distinct_width_opening_ids=[row["opening_id"] for row in rows if row.get("distinct_width_on_facade")],
        calibration_problems=calibration_problems,
        note="No height error is asserted. Each height needs its own source-region coverage in an explicitly calibrated elevation. Whole-image citations and absent calibration remain unverified; a shared height on different widths deserves a local check. Report only.")


def compact_located_heights(report):
    result = {key: value for key, value in report.items() if key != "openings"}
    result["unchecked_openings"] = [{key: row[key] for key in (
        "opening_id", "facade", "floor_ids", "width_m", "status", "shared_height_across_widths")}
        for row in report["openings"] if row["status"] != "covered"]
    return result
