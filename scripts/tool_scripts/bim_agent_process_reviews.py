"""Local drawing reviews and a separate whole-building judgment.

These are model-reported observations, never independent fidelity certification.
Review reuse is computed from actual physical scope, original image and calibration;
changing an unrelated floor or a height does not erase a plan's XY observations.
"""
from __future__ import annotations

import hashlib
import json


POLICY = "local_drawing_reviews_v1"


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _source(toolkit, candidate):
    from src.agent.geometry.source_image_overlay import _source_hash
    source = json.loads((toolkit.candidate_path(candidate) / "source_model.json").read_bytes())
    _source_hash(source)
    return source


def _read_file(toolkit, relative, folder):
    path = (toolkit.run / relative).resolve()
    root = (toolkit.run / folder).resolve()
    if not path.is_relative_to(root) or path.suffix != ".json" or not path.is_file():
        raise ValueError("review evidence must be an existing admitted " + folder + " record")
    return json.loads(path.read_bytes())


def _image_hash(toolkit, image):
    path = toolkit.image_path(image)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != toolkit.manifest["images"][image]["sha256"]:
        raise ValueError("review original image changed")
    return digest


def _plan_state(toolkit, source, floor_id, image):
    from src.agent.runtime_roles.assembly_review import floor_facts
    if floor_id not in {row["id"] for row in source["floors"]}:
        raise ValueError("unknown review floor_id")
    calibration = next((row for _, row in toolkit.registered_calibrations()
                        if row["image"] == image and row["floor_id"] == floor_id), None)
    if calibration is None:
        raise ValueError("plan review requires the saved original-image calibration")
    return {"geometry": floor_facts(source, floor_id),
            "image_sha256": _image_hash(toolkit, image),
            "calibration": {key: calibration[key] for key in ("x_anchors", "y_anchors")}}


def _building_state(source):
    # Exclude hashes, audit timestamps and generated report state. A new note may
    # be a substantive new assumption, so retain authored assumptions/unresolved.
    return {"floors": source.get("floors"), "spaces": source.get("spaces"),
            "boundaries": source.get("boundaries"), "openings": source.get("openings"),
            "connections": source.get("connections"),
            "boundary_relations": source.get("boundary_relations"),
            "assumptions": source.get("assumptions"),
            "unresolved": source.get("generation", {}).get("unresolved")}


def building_facts(source):
    """Facts for architectural judgment; graph isolation is a question, not failure."""
    graph = {row["id"]: set() for row in source["spaces"]}
    exits = set()
    for opening in source["openings"]:
        if opening["kind"] not in {"door", "open_passage"}:
            continue
        rooms = [key for key in opening.get("space_ids", []) if key in graph]
        if opening.get("exterior"):
            exits.update(rooms)
        for room in rooms:
            graph[room].update(key for key in rooms if key != room)
    seen, components = set(), []
    for room in graph:
        if room in seen:
            continue
        pending, group = [room], []
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            group.append(current)
            pending.extend(graph[current] - seen)
        components.append({"space_ids": sorted(group), "has_exterior_door": bool(set(group) & exits)})
    return {"floors": source.get("floors", []), "door_components": components,
            "spaces_without_declared_door": [key for key in graph if not graph[key] and key not in exits],
            "meaning": "Declared door/open-passage graph only; stairs and other vertical circulation "
                       "may be absent from this representation. Judge against supported building intent, "
                       "not a code-compliance or independent drawing verdict."}


def _overlay(toolkit, candidate, image, floor_id):
    source = _source(toolkit, candidate)
    for path in sorted((toolkit.run / "image_overlays").glob("overlay_*.json"), reverse=True):
        row = json.loads(path.read_bytes())
        if (row.get("mode") == "source_image_overlay" and row.get("candidate") == candidate
                and row.get("image") == image and row.get("floor_id") == floor_id
                and row.get("source_model_sha256") == source["source_model_sha256"]):
            if row.get("box_original_pixels") != [0, 0, *row.get("original_size", [])]:
                continue
            if row.get("image_sha256") != _image_hash(toolkit, image):
                raise ValueError("plan overlay original changed")
            return path.relative_to(toolkit.run).as_posix(), row
    raise ValueError("review needs a full actual-source plan overlay for this candidate/image/floor")


def _picture_hash(toolkit, view):
    path = (toolkit.run / view["overlay_image"]).resolve()
    if not path.is_relative_to((toolkit.run / "image_overlays").resolve()) or path.suffix != ".png":
        raise ValueError("overlay picture must stay in image_overlays")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_latest_reading(toolkit, reading):
    for path in (toolkit.run / "drawing_readings").glob("reading_*.json"):
        # Comparison reports share the prefix but are not new observations.
        if path.stem <= reading["reading_id"] or not path.stem.removeprefix("reading_").isdigit():
            continue
        other = json.loads(path.read_bytes())
        if other.get("image") == reading["image"] and other.get("facade") == reading["facade"]:
            return False
    return True


def _records(toolkit):
    result = []
    for path in sorted((toolkit.run / "process_reviews").glob("review_*.json")):
        row = json.loads(path.read_bytes())
        if row.get("record_sha256") != _hash({k: v for k, v in row.items() if k != "record_sha256"}):
            raise ValueError("saved process review changed")
        result.append(row)
    return result


def record_reviews(toolkit, candidate, reviews_json):
    """Save one batch after the model has inspected the returned actual-result views."""
    entries = json.loads(reviews_json)
    if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
        raise ValueError("reviews_json needs 1-32 review objects")
    source = _source(toolkit, candidate) if candidate else None
    prepared = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {
                "kind", "image", "floor_id", "reading_id", "outcome", "summary", "issues", "view_id"}:
            raise ValueError("review fields: kind,image,floor_id,reading_id,outcome,summary,issues,view_id")
        kind, outcome = entry.get("kind"), entry.get("outcome")
        if kind not in {"plan", "elevation", "building", "reference"}:
            raise ValueError("kind must be plan, elevation, building or reference")
        if outcome not in {"consistent", "uncertain", "needs_revision"}:
            raise ValueError("outcome must be consistent, uncertain or needs_revision")
        summary = entry.get("summary")
        issues = entry.get("issues", [])
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000:
            raise ValueError("summary must explain the actual comparison/judgment in 1-2000 characters")
        if (not isinstance(issues, list) or len(issues) > 40
                or any(not isinstance(v, str) or not v.strip() or len(v) > 1000 for v in issues)):
            raise ValueError("issues must be a list of located questions or evidence limits")
        if outcome == "consistent" and issues or outcome != "consistent" and not issues:
            raise ValueError("consistent has no outstanding issues; uncertain/needs_revision must locate them")
        row = {"kind": kind, "outcome": outcome, "summary": summary, "issues": issues,
               "assessment": "model_reported_not_independently_verified"}
        if kind == "plan":
            if source is None:
                raise ValueError("plan review requires candidate")
            image, floor = entry.get("image"), entry.get("floor_id")
            view, metadata = _overlay(toolkit, candidate, image, floor)
            state = _plan_state(toolkit, source, floor, image)
            if metadata.get("anchors") != {axis: state["calibration"][axis + "_anchors"] for axis in ("x", "y")}:
                raise ValueError("overlay does not use the current plan calibration; project it again")
            row.update(image=image, floor_id=floor, candidate=candidate, scope=f"plan:{image}:{floor}",
                       state_sha256=_hash(state), evidence_file=view,
                       picture_sha256=_picture_hash(toolkit, metadata),
                       evidence_sha256=hashlib.sha256((toolkit.run / view).read_bytes()).hexdigest())
        elif kind == "elevation":
            from scripts.tool_scripts.bim_agent_drawing_readings import load_reading
            reading = load_reading(toolkit, entry.get("reading_id"))
            if not _is_latest_reading(toolkit, reading):
                raise ValueError("review the latest reading for this image/facade")
            row.update(reading_id=reading["reading_id"], image=reading["image"], facade=reading["facade"],
                       scope=f"elevation:{reading['image']}:{reading['facade']}",
                       state_sha256=reading["artifact_sha256"])
        elif kind == "building":
            if source is None:
                raise ValueError("building review requires candidate")
            row.update(candidate=candidate, scope="building", state_sha256=_hash(_building_state(source)))
        else:
            image = entry.get("image")
            if image in toolkit.manifest.get("floor_plan_images", []):
                raise ValueError("a required floor plan cannot be marked reference-only")
            view = toolkit.read_image_view(entry.get("view_id"))
            if view.get("name", view.get("image")) != image:
                raise ValueError("reference review requires an issued view of that original")
            row.update(image=image, scope=f"reference:{image}", state_sha256=_image_hash(toolkit, image),
                       view_id=entry["view_id"])
        prepared.append(row)
    folder = toolkit.run / "process_reviews"
    folder.mkdir(exist_ok=True)
    saved = []
    index = len(list(folder.glob("review_*.json")))
    for row in prepared:
        index += 1
        row.update(review_id=f"review_{index:04d}")
        row["record_sha256"] = _hash(row)
        path = folder / (row["review_id"] + ".json")
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(row, stream, ensure_ascii=False, indent=2, allow_nan=False)
        saved.append({key: row[key] for key in ("review_id", "kind", "scope", "outcome", "issues")})
    result = {"saved_reviews": saved, "drawing_fidelity": "not_evaluated"}
    toolkit.log("record_bim_review", result)
    if candidate:
        result["process_review"] = process_status(toolkit, candidate)
    return result


def process_status(toolkit, candidate):
    source = _source(toolkit, candidate)
    latest = {row["scope"]: row for row in _records(toolkit)}
    rows, covered, pending = [], set(), []
    floor_coverage = set()
    for row in latest.values():
        valid, reason = False, None
        try:
            if row["kind"] == "plan":
                view = _read_file(toolkit, row["evidence_file"], "image_overlays")
                if hashlib.sha256((toolkit.run / row["evidence_file"]).read_bytes()).hexdigest() != row["evidence_sha256"]:
                    raise ValueError("reviewed overlay record changed")
                if _picture_hash(toolkit, view) != row["picture_sha256"]:
                    raise ValueError("reviewed overlay picture changed")
                valid = row["state_sha256"] == _hash(_plan_state(toolkit, source, row["floor_id"], row["image"]))
                if valid:
                    floor_coverage.add(row["floor_id"])
            elif row["kind"] == "elevation":
                from scripts.tool_scripts.bim_agent_drawing_readings import load_reading, compare_reading
                reading = load_reading(toolkit, row["reading_id"])
                valid = reading["artifact_sha256"] == row["state_sha256"] and _is_latest_reading(toolkit, reading)
                if valid:
                    comparison = compare_reading(toolkit, row["reading_id"], candidate)
                    if not comparison["current_consistent"]:
                        pending.append({"scope": row["scope"], "reason": "reading_source_conflict",
                                        "details": comparison})
            elif row["kind"] == "building":
                valid = row["state_sha256"] == _hash(_building_state(source))
            else:
                valid = row["state_sha256"] == _image_hash(toolkit, row["image"])
        except (OSError, ValueError, KeyError, TypeError) as error:
            reason = str(error)
        status = row["outcome"] if valid else "stale"
        item = {key: row[key] for key in ("review_id", "kind", "scope", "summary", "issues")}
        item.update(status=status)
        if reason:
            item["reason"] = reason
        rows.append(item)
        if valid and row["kind"] != "building" and status != "needs_revision":
            covered.add(row["image"])
        if status in {"stale", "needs_revision"}:
            pending.append({"scope": row["scope"], "reason": status, "issues": row["issues"]})
    missing_images = sorted(set(toolkit.manifest.get("images", {})) - covered)
    missing_floors = sorted({row["id"] for row in source["floors"]} - floor_coverage)
    building = next((row for row in rows if row["kind"] == "building"), None)
    ready = not (pending or missing_images or missing_floors) and building is not None and building["status"] in {"consistent", "uncertain"}
    return {"policy": toolkit.manifest.get("drawing_review_policy"),
            "status": "ready" if ready else "needs_attention", "ready": ready,
            "missing_images": missing_images, "missing_plan_floors": missing_floors,
            "building_review": building, "reviews": rows, "pending": pending,
            "meaning": "Local comparisons are model-reported. Reused unchanged physical scopes remain current; "
                       "cross-drawing matching and the architectural judgment are separate. This is not independent quality approval."}


def require_process_reviews(toolkit, candidate):
    if toolkit.manifest.get("drawing_review_policy") != POLICY:
        return None
    result = process_status(toolkit, candidate)
    if not result["ready"]:
        summary = {key: result[key] for key in ("missing_images", "missing_plan_floors")}
        summary["pending"] = [{key: item[key] for key in ("scope", "reason") if key in item}
                              for item in result["pending"][:32]]
        summary["building_status"] = (result["building_review"] or {}).get("status", "missing")
        raise ValueError("Complete the pending local/cross-drawing/building judgments before finish_bim; "
                         "inspect_candidate contains details: " + json.dumps(summary, ensure_ascii=False))
    return result


def apply_readings(toolkit, candidate, reading_ids):
    """Apply the existing conservative matching/claim path in one batched tool call."""
    from scripts.tool_scripts.bim_agent_drawing_readings import load_reading, compare_reading
    from src.agent.runtime_roles.elevation import match_elevation, height_application
    from scripts.tool_scripts.bim_agent_role_heights import build_role_height_batch_entry
    if not isinstance(reading_ids, list) or not 1 <= len(reading_ids) <= 32 or len(set(reading_ids)) != len(reading_ids):
        raise ValueError("reading_ids needs 1-32 distinct saved readings")
    source = _source(toolkit, candidate)
    latest = {row["scope"]: row for row in _records(toolkit)}
    entries, evidence_types, selected, seen = [], [], [], set()
    for identity in reading_ids:
        reading = load_reading(toolkit, identity)
        review = latest.get(f"elevation:{reading['image']}:{reading['facade']}")
        if (not _is_latest_reading(toolkit, reading) or not review or review.get("reading_id") != identity
                or review["state_sha256"] != reading["artifact_sha256"]
                or review["outcome"] == "needs_revision"):
            raise ValueError("inspect the adopted-reading overlay and record its local review before applying " + identity)
        artifact = reading["artifact"]
        match = match_elevation(source, artifact, candidate=candidate)
        if match["can_apply"]:
            application = height_application(artifact, match, source, {"candidate": candidate})
            by_id = {row["id"]: row for row in artifact["openings"]}
            for entry, correspondence in zip(application["entries"], match["matches"]):
                target = correspondence["source_opening_id"]
                if target in seen:
                    raise ValueError("multiple readings target the same source opening; resolve that conflict first")
                seen.add(target)
                entries.append(entry)
                evidence_types.append(by_id[correspondence["artifact_opening_id"]]["evidence_type"])
        selected.append(identity)
    applied = None
    if entries:
        batch = build_role_height_batch_entry(entries, evidence_types=evidence_types)
        applied = toolkit.claim_transaction(candidate, batch["entries_json"])
        # A partially/failed application must retain its real saved candidate.
        candidate = applied.get("saved_candidate") or applied.get("result_candidate") or candidate
    comparisons = [compare_reading(toolkit, identity, candidate) for identity in selected]
    result = {**(applied or {}), "candidate": candidate, "matched_openings": len(seen),
              "comparisons": comparisons, "all_readings_consistent": all(row["current_consistent"] for row in comparisons),
              "comparison_summary": [{key: row[key] for key in ("reading_id", "facade", "current_consistent",
                  "matched_count", "issue_count", "height_difference_count")} for row in comparisons],
              "drawing_fidelity": "not_evaluated"}
    toolkit.log("apply_elevation_readings", result)
    return result
