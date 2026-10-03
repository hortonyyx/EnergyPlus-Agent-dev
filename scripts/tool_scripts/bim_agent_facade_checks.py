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


_COUNT_EXAMPLE = {"observation_type": "facade_count", "image": "elevation.png",
    "floor_id": "L1", "facade": "South", "window_count": 4,
    "reason": "Synthetic format only; replace with your own observed facade total"}


def record_facade_count(toolkit, observation):
    """GLM sm25 missed two west windows: save one image/floor/facade total.

    Counts describe the drawing, so can precede any candidate. Separate immutable
    files avoid confusing observational totals with adopted geometric parameters.
    A new record for the same image/scope supersedes its earlier count; counts
    from different images stay separate and conflicts are reported, never added.
    """
    import os
    import tempfile
    import time
    import uuid
    from scripts.tool_scripts.bim_agent_feedback import resolve_image_name

    def reject(reason):
        example = {**_COUNT_EXAMPLE, "image": next(iter(toolkit.manifest["images"]), "elevation.png")}
        raise ValueError("facade_count: " + reason + "; minimal example: " + json.dumps(example))

    allowed = {"observation_type", "image", "floor_id", "floor_plan_image", "facade",
               "window_count", "door_count", "box", "reason"}
    if set(observation) - allowed:
        reject("unknown fields " + str(sorted(set(observation) - allowed)))
    if not isinstance(observation.get("facade"), str) or observation["facade"] not in {"North", "South", "East", "West"}:
        reject("facade must be North/South/East/West")
    if ("floor_id" in observation) == ("floor_plan_image" in observation):
        reject("give exactly one of floor_id or floor_plan_image")
    scope_key = "floor_id" if "floor_id" in observation else "floor_plan_image"
    if not isinstance(observation[scope_key], str) or not observation[scope_key].strip():
        reject(scope_key + " must be a nonempty string")
    for key in ("window_count", "door_count"):
        if key == "door_count" and key not in observation:
            continue
        if type(observation.get(key)) is not int or observation[key] < 0:
            reject(key + " must be a nonnegative integer; zero is an explicit observation")
    if not isinstance(observation.get("reason"), str) or not observation["reason"].strip():
        reject("reason must describe the observed scope")
    image = resolve_image_name(toolkit.manifest["images"], observation.get("image"))
    toolkit.image_path(image)
    info = toolkit.manifest["images"][image]
    box = observation.get("box", [0, 0, *info["size"]])
    if (not isinstance(box, list) or len(box) != 4 or
            not all(type(v) in (int, float) and math.isfinite(v) for v in box) or
            not (0 <= box[0] < box[2] <= info["size"][0] and 0 <= box[1] < box[3] <= info["size"][1])):
        reject("box must be [left,top,right,bottom] within the original image")
    scope = observation[scope_key]
    if scope_key == "floor_plan_image":
        scope = resolve_image_name(toolkit.manifest["images"], scope)
        toolkit.image_path(scope)
    row = {**observation, "image": image, scope_key: scope, "box": box,
           "image_sha256": info["sha256"], "image_size": info["size"],
           "schema_version": "facade_count_observation_v1",
           "id": f"count_{time.time_ns():020d}_{uuid.uuid4().hex[:12]}",
           "drawing_fidelity": "not_evaluated",
           "note": "Observer-reported total for the entire named floor/facade, not a verified count. Re-record this image/scope to correct it; no adoption or geometry confirmation is needed."}
    if scope_key == "floor_plan_image":
        row["floor_plan_sha256"] = toolkit.manifest["images"][scope]["sha256"]
    folder = toolkit.run / "facade_counts"
    folder.mkdir(exist_ok=True)
    # Publish complete records atomically; independent wall/floor calls share no latch.
    with tempfile.NamedTemporaryFile(mode="w", dir=folder, suffix=".tmp", delete=False) as output:
        json.dump(row, output, ensure_ascii=False, indent=2)
        temporary = output.name
    os.replace(temporary, folder / (row["id"] + ".json"))
    return row


def facade_count_report(toolkit, candidate):
    from scripts.tool_scripts.bim_agent_budget import candidate_floor_images
    from src.agent.geometry.opening_review import facade_inventory

    _, source = toolkit.claims().candidate(candidate)
    inventory = facade_inventory(source)
    floor_ids = {row["id"] for row in source["floors"]}
    mapping = candidate_floor_images(toolkit.run, candidate)
    latest = {}
    for path in sorted((toolkit.run / "facade_counts").glob("count_*.json")):
        observation = json.loads(path.read_text())
        key = (observation["image"], observation["facade"],
               observation.get("floor_id"), observation.get("floor_plan_image"))
        latest[key] = observation
    observations, unused = defaultdict(list), []
    for observation in latest.values():
        problem = None
        images = [(observation["image"], observation["image_sha256"])]
        if observation.get("floor_plan_image"):
            images.append((observation["floor_plan_image"], observation["floor_plan_sha256"]))
        for image, expected_hash in images:
            try:
                toolkit.image_path(image)
                if toolkit.manifest["images"][image]["sha256"] != expected_hash:
                    problem = "source_image_changed"
            except (OSError, ValueError, KeyError):
                problem = "source_image_changed"
        matches = ([observation["floor_id"]] if "floor_id" in observation
                   else mapping.get(observation["floor_plan_image"], []))
        if len(matches) != 1 or matches[0] not in floor_ids:
            problem = problem or "floor_not_resolved_in_candidate"
        if problem:
            unused.append(dict(id=observation["id"], reason=problem))
            continue
        observations[(matches[0], observation["facade"])].append(observation)
    rows = []
    classifications = inventory["opening_classifications"]
    for floor in inventory["floors"]:
        for facade in floor["facades"]:
            scope = floor["floor_id"], facade["facade"]
            records = observations.pop(scope, [])
            row = dict(floor_id=scope[0], facade=scope[1], observation_ids=[r["id"] for r in records])
            for kind in ("window", "door"):
                actual = [identity for identity in facade["opening_ids"] if classifications[identity]["kind"] == kind]
                totals = sorted({record[kind + "_count"] for record in records if kind + "_count" in record})
                status = ("not_counted" if not totals else "conflicting_observations" if len(totals) > 1
                          else "matches_observed_total" if totals[0] == len(actual) else "count_mismatch")
                row[kind] = dict(status=status, built_count=len(actual), observed_counts=totals,
                    built_opening_ids=actual, missing_count=(totals[0] - len(actual)) if len(totals) == 1 else None)
            rows.append(row)
    for scope, records in observations.items():
        unused.extend(dict(id=record["id"], reason="facade_not_present_in_candidate", floor_id=scope[0], facade=scope[1])
                      for record in records)
    summary = dict(floor_facade_count=len(rows), window_status_counts=dict(Counter(r["window"]["status"] for r in rows)),
                   door_status_counts=dict(Counter(r["door"]["status"] for r in rows)), unused_observation_count=len(unused))
    return dict(schema_version="facade_count_report_v1", candidate=candidate,
        source_model_sha256=source["source_model_sha256"], delivery_blocked=False,
        summary=summary, scopes=rows, unused_observations=unused,
        unsupported_exterior_boundaries=[dict(floor_id=floor["floor_id"], boundaries=floor["unsupported_exterior_boundaries"])
            for floor in inventory["floors"] if floor["unsupported_exterior_boundaries"]],
        note="Compare observer-reported whole-floor/facade totals with actual source openings. Uncounted facades, zero totals, conflicting evidence and unresolved scopes stay explicit. Equal counts do not prove position or drawing fidelity. Report only.")
