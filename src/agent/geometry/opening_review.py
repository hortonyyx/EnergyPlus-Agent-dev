"""Deterministic reconciliation of supplied drawing opening observations.

This module deliberately does not inspect pixels or infer openings.  A model (or
person) supplies compact, reviewable marks from a named input image; the code
only checks whether those marks correspond one-to-one with the explicit
openings already present in a source BIM.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter


_SOURCE_TO_REVIEW_KIND = {"door": "door", "window": "window", "open": "passage"}
_REVIEW_KINDS = frozenset(_SOURCE_TO_REVIEW_KIND.values())
_REVIEW_FIELDS = frozenset({"floor_id", "kind", "image", "coverage", "marks"})
_MARK_FIELDS = frozenset({"mark_id", "box", "opening_ids", "space_ids", "basis", "note"})


def _canonical_sha256(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode()).hexdigest()


def _source_hash(source: dict) -> str:
    if not isinstance(source, dict):
        raise ValueError("source must be a source_model.json object")
    payload = {key: value for key, value in source.items() if key != "source_model_sha256"}
    digest = _canonical_sha256(payload)
    declared = source.get("source_model_sha256")
    if declared is not None and declared != digest:
        raise ValueError("source_model_sha256 does not match source content")
    return digest


def _source_index(source: dict) -> tuple[str, dict, dict, dict]:
    """Return immutable-source indexes needed by both public functions."""
    source_hash = _source_hash(source)
    if not isinstance(source.get("floors"), list) or not isinstance(source.get("spaces"), list):
        raise ValueError("source requires floors and spaces lists")
    if not isinstance(source.get("openings"), list):
        raise ValueError("source requires an openings list")

    floors: dict[str, dict] = {}
    for row in source["floors"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError("source floor requires a nonempty id")
        if row["id"] in floors:
            raise ValueError(f"duplicate source floor id: {row['id']}")
        floors[row["id"]] = row
    spaces: dict[str, dict] = {}
    for row in source["spaces"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not isinstance(row.get("floor_id"), str):
            raise ValueError("source space requires id and floor_id")
        if row["id"] in spaces or row["floor_id"] not in floors:
            raise ValueError("source space ids and floor references must be unique and valid")
        spaces[row["id"]] = row

    openings: dict[str, dict] = {}
    for row in source["openings"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError("source opening requires a nonempty id")
        if row["id"] in openings or row.get("kind") not in _SOURCE_TO_REVIEW_KIND:
            raise ValueError("source opening ids and kinds must be unique and supported")
        space_ids = row.get("space_ids")
        if not isinstance(space_ids, list) or not space_ids or any(sid not in spaces for sid in space_ids):
            raise ValueError(f"source opening {row['id']} has invalid space_ids")
        floor_ids = {spaces[sid]["floor_id"] for sid in space_ids}
        if len(floor_ids) != 1:
            raise ValueError(f"source opening {row['id']} spans multiple floors")
        vertices = row.get("vertices")
        if not isinstance(vertices, list) or len(vertices) < 2:
            raise ValueError(f"source opening {row['id']} requires vertices")
        try:
            xy_points = [[float(vertex[0]), float(vertex[1])] for vertex in vertices]
        except (IndexError, TypeError, ValueError) as exc:
            raise ValueError(f"source opening {row['id']} has invalid vertices") from exc
        if not all(math.isfinite(value) for point in xy_points for value in point):
            raise ValueError(f"source opening {row['id']} has non-finite vertices")
        endpoints = []
        for point in xy_points:
            if point not in endpoints:
                endpoints.append(point)
            if len(endpoints) == 2:
                break
        if len(endpoints) != 2:
            raise ValueError(f"source opening {row['id']} requires two distinct plan endpoints")
        openings[row["id"]] = {
            "id": row["id"],
            "kind": _SOURCE_TO_REVIEW_KIND[row["kind"]],
            "space_ids": list(row["space_ids"]),
            "floor_id": next(iter(floor_ids)),
            "plan_endpoints": endpoints,
            "vertices": copy.deepcopy(vertices),
        }
    return source_hash, floors, spaces, openings


def opening_inventory(source: dict) -> dict:
    """Expose actual explicit source openings by floor and source space.

    The inventory is evidence for a later visual review, never a count inferred
    from room names, free text, or the review itself.
    """
    source_hash, floors, spaces, openings = _source_index(source)
    by_floor = {floor_id: [] for floor_id in floors}
    by_space = {space_id: [] for space_id in spaces}
    for opening in openings.values():
        by_floor[opening["floor_id"]].append(opening)
        for space_id in opening["space_ids"]:
            by_space[space_id].append(opening)

    def summarize(rows: list[dict], *, include_openings: bool) -> dict:
        ordered = sorted(rows, key=lambda row: row["id"])
        counts = Counter(row["kind"] for row in ordered)
        summary = {
            "opening_count": len(ordered),
            "counts": {kind: counts[kind] for kind in sorted(_REVIEW_KINDS)},
            "opening_ids": [row["id"] for row in ordered],
        }
        if include_openings:
            summary["openings"] = [copy.deepcopy(row) for row in ordered]
        return summary

    unbuilt = source.get("unbuilt_openings", [])
    unsupported = source.get("unsupported", [])
    if not isinstance(unbuilt, list) or not isinstance(unsupported, list):
        raise ValueError("source unbuilt_openings and unsupported must be lists when present")

    return {
        "schema_version": "opening_inventory_v1",
        "source_model_sha256": source_hash,
        "opening_count": len(openings),
        "counts": {kind: sum(row["kind"] == kind for row in openings.values()) for kind in sorted(_REVIEW_KINDS)},
        "floors": [
            {"floor_id": floor_id, **summarize(by_floor[floor_id], include_openings=True)}
            for floor_id in sorted(floors)
        ],
        "spaces": [
            {"space_id": space_id, "floor_id": spaces[space_id]["floor_id"],
             **summarize(by_space[space_id], include_openings=False)}
            for space_id in sorted(spaces)
        ],
        "scope": {
            "actual_openings": "only explicit built source openings are inventoried",
            "unbuilt_opening_ids": [row.get("id") for row in unbuilt if isinstance(row, dict) and row.get("id")],
            "unbuilt_opening_count": len(unbuilt),
            "unsupported_observation_count": len(unsupported),
        },
    }


def _reject(message: str) -> None:
    raise ValueError(f"invalid opening review: {message}")


def _image_info(images: dict, image_name: str) -> tuple[int, int, str]:
    if not isinstance(images, dict) or image_name not in images:
        _reject(f"unknown image: {image_name}")
    row = images[image_name]
    if not isinstance(row, dict) or set(row) != {"size", "sha256"}:
        _reject(f"image {image_name} requires only size and sha256")
    size = row["size"]
    if (not isinstance(size, list) or len(size) != 2 or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in size)):
        _reject(f"image {image_name} has invalid size")
    if any(float(v) != int(v) for v in size) or not isinstance(row["sha256"], str) or not row["sha256"]:
        _reject(f"image {image_name} has invalid metadata")
    return int(size[0]), int(size[1]), row["sha256"]


def _validate_review(review: dict, images: dict) -> tuple[int, int, str]:
    if not isinstance(review, dict) or set(review) != _REVIEW_FIELDS:
        _reject("review fields must be floor_id, kind, image, coverage, and marks")
    if not isinstance(review["floor_id"], str) or not review["floor_id"]:
        _reject("floor_id must be a nonempty string")
    if review["kind"] not in _REVIEW_KINDS or review["coverage"] not in {"complete", "partial"}:
        _reject("kind or coverage is invalid")
    if not isinstance(review["image"], str) or not isinstance(review["marks"], list):
        _reject("image and marks have invalid types")
    width, height, image_hash = _image_info(images, review["image"])
    mark_ids: set[str] = set()
    for mark in review["marks"]:
        if not isinstance(mark, dict) or set(mark) != _MARK_FIELDS:
            _reject("mark has unsupported or missing fields")
        mark_id = mark["mark_id"]
        if not isinstance(mark_id, str) or not mark_id or mark_id in mark_ids:
            _reject("mark_id must be nonempty and unique")
        mark_ids.add(mark_id)
        if (not isinstance(mark["box"], list) or len(mark["box"]) != 4 or
                any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in mark["box"])):
            _reject(f"mark {mark_id} has a non-finite box")
        x0, y0, x1, y1 = map(float, mark["box"])
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height or x0 >= x1 or y0 >= y1:
            _reject(f"mark {mark_id} box is outside image bounds")
        if (not isinstance(mark["opening_ids"], list) or
                not all(isinstance(value, str) and value for value in mark["opening_ids"])):
            _reject(f"mark {mark_id} opening_ids must be a list of nonempty strings")
        if (not isinstance(mark["space_ids"], list) or not mark["space_ids"] or
                not all(isinstance(value, str) and value for value in mark["space_ids"])):
            _reject(f"mark {mark_id} space_ids must be a nonempty list of strings")
        if mark["basis"] not in {"visible", "inferred", "uncertain"} or not isinstance(mark["note"], str):
            _reject(f"mark {mark_id} basis or note is invalid")
    return width, height, image_hash


def review_openings(source: dict, review: dict, images: dict) -> dict:
    """Check one floor/kind image review against explicit source openings.

    A ``complete`` review is a completeness claim only for its stated floor and
    kind.  A ``partial`` review is retained as useful evidence but never gets a
    full-coverage verdict.  Neither verdict evaluates drawing fidelity.
    """
    source_hash, floors, spaces, openings = _source_index(source)
    width, height, image_hash = _validate_review(review, images)
    findings: list[dict] = []
    def finding(code: str, **evidence) -> None:
        findings.append({"code": code, **evidence})

    if review["floor_id"] not in floors:
        finding("unknown_floor", floor_id=review["floor_id"])
    scope = {opening_id for opening_id, opening in openings.items()
             if opening["floor_id"] == review["floor_id"] and opening["kind"] == review["kind"]}
    matched_ids: set[str] = set()
    referenced_ids: set[str] = set()
    reused_ids: set[str] = set()
    seen_ids: set[str] = set()

    mark_boxes: dict[tuple[float, float, float, float], str] = {}
    for mark in review["marks"]:
        mark_id = mark["mark_id"]
        box = tuple(map(float, mark["box"]))
        if box in mark_boxes:
            finding("duplicate_mark_box", mark_id=mark_id, other_mark_id=mark_boxes[box], box=list(box))
        else:
            mark_boxes[box] = mark_id
        ids = mark["opening_ids"]
        if not ids:
            finding("unmodeled_observed_mark", mark_id=mark_id, space_ids=list(mark["space_ids"]))
            if mark["basis"] in {"inferred", "uncertain"}:
                finding("observation_pending", mark_id=mark_id, basis=mark["basis"], opening_ids=[])
            continue
        if len(ids) != 1:
            finding("mark_multiple_opening_ids", mark_id=mark_id, opening_ids=list(ids))
        valid_mark = len(ids) == 1
        for opening_id in ids:
            if opening_id in seen_ids:
                reused_ids.add(opening_id)
            seen_ids.add(opening_id)
            opening = openings.get(opening_id)
            if opening is None:
                finding("unknown_opening_id", mark_id=mark_id, opening_id=opening_id)
                valid_mark = False
                continue
            referenced_ids.add(opening_id)
            if opening["floor_id"] != review["floor_id"]:
                finding("mark_floor_mismatch", mark_id=mark_id, opening_id=opening_id,
                        actual_floor_id=opening["floor_id"], review_floor_id=review["floor_id"])
                valid_mark = False
            if opening["kind"] != review["kind"]:
                finding("mark_kind_mismatch", mark_id=mark_id, opening_id=opening_id,
                        actual_kind=opening["kind"], review_kind=review["kind"])
                valid_mark = False
            if set(mark["space_ids"]) != set(opening["space_ids"]) or len(mark["space_ids"]) != len(opening["space_ids"]):
                finding("mark_space_ids_mismatch", mark_id=mark_id, opening_id=opening_id,
                        actual_space_ids=list(opening["space_ids"]), marked_space_ids=list(mark["space_ids"]))
                valid_mark = False
        if valid_mark:
            matched_ids.add(ids[0])
        if mark["basis"] in {"inferred", "uncertain"}:
            finding("observation_pending", mark_id=mark_id, basis=mark["basis"], opening_ids=list(ids))

    for opening_id in sorted(reused_ids):
        finding("opening_id_reused", opening_id=opening_id)
        matched_ids.discard(opening_id)

    if review["coverage"] == "complete":
        for opening_id in sorted(scope - matched_ids):
            finding("unaccounted_model_opening", opening_id=opening_id)
    else:
        finding("partial_review_not_complete", floor_id=review["floor_id"], kind=review["kind"])

    room_coverage = []
    for space_id, space in sorted(spaces.items()):
        if space["floor_id"] != review["floor_id"]:
            continue
        actual_ids = sorted(opening_id for opening_id in scope if space_id in openings[opening_id]["space_ids"])
        matched = sorted(opening_id for opening_id in actual_ids if opening_id in matched_ids)
        room_coverage.append({
            "space_id": space_id,
            "actual_opening_ids": actual_ids,
            "actual_opening_count": len(actual_ids),
            "matched_opening_ids": matched,
            "matched_opening_count": len(matched),
            "missing_opening_ids": sorted(set(actual_ids) - set(matched)),
        })

    conclusion = "consistent_with_supplied_observations" if not findings else "observations_require_follow_up"
    return {
        "schema_version": "opening_review_v1",
        "source_model_sha256": source_hash,
        "image": {"name": review["image"], "sha256": image_hash, "size": [width, height]},
        "review_scope": {"floor_id": review["floor_id"], "kind": review["kind"], "coverage": review["coverage"]},
        "model_opening_ids": sorted(scope),
        "matched_opening_ids": sorted(matched_ids),
        "referenced_opening_ids": sorted(referenced_ids),
        "room_coverage": room_coverage,
        "findings": findings,
        "conclusion": conclusion,
        "drawing_fidelity": "not_evaluated",
        "source_scope": {
            "actual_openings": "only explicit built source openings were reviewed",
            "unbuilt_opening_count": len(source.get("unbuilt_openings", [])),
            "unsupported_observation_count": len(source.get("unsupported", [])),
        },
    }
