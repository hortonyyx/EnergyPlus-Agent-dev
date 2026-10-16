"""Carry per-view wall thickness evidence into source BIM without moving walls.

Targets address authored footprint edges or partition polylines. Face labels use
the positive world normal (+X for a vertical plan line, +Y for a horizontal one),
independent of point order. They are observations, not permission to infer offsets.
"""
from __future__ import annotations

import copy
import math

from src.agent.geometry.component_attributes import thickness_record, validate_component_attributes
from src.agent.geometry.wall_reference import resolve_wall_references


_FIELDS = {"target", "thickness_m", "reference_side", "evidence_status", "basis", "source_refs"}
_SIDES = {"centerline", "negative_face", "positive_face", "unknown"}
_EPS = 1e-7  # Floating-point identity only; never a fitting or snapping tolerance.


def _number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _targets(plan):
    ring = list(plan["footprint_pixels"])
    if ring and ring[0] == ring[-1]:
        ring.pop()
    targets = {f"footprint:{i}": [(a, b)]
               for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1]))}
    defaults = list(targets)
    partitions = {}
    for partition in plan["partitions"]:
        target = f"partition:{partition['id']}"
        points = partition["points"]
        segments = list(zip(points, points[1:]))
        keys = [target, *(f"{target}:{i}" for i in range(len(segments)))]
        if set(keys).intersection(targets):
            raise ValueError("wall target IDs are ambiguous; use distinct partition IDs")
        targets[target] = segments
        for key, segment in zip(keys[1:], segments):
            targets[key] = [segment]
        partitions[target] = keys[1:]
        defaults.append(target)
    return targets, defaults, partitions


def validate_wall_metadata(plan: dict) -> list[dict]:
    """Validate known readings and explicitly fill unprovided walls as unknown.

    ``footprint:0`` is the first authored edge (not a canonical polygon edge).
    ``partition:P01`` covers all segments, while ``partition:P01:0`` covers just
    its first segment. Whole-partition and individual-segment records cannot mix.
    """
    targets, defaults, partitions = _targets(plan)
    records = plan.get("wall_metadata", [])
    if not isinstance(records, list):
        raise ValueError("wall_metadata must be a list")
    supplied = {}
    for record in records:
        if not isinstance(record, dict) or set(record) - _FIELDS:
            raise ValueError("unknown wall_metadata fields")
        target = record.get("target")
        if not isinstance(target, str) or target not in targets:
            raise ValueError(f"unknown wall_metadata target {target!r}")
        if target in supplied:
            raise ValueError(f"duplicate wall_metadata target {target}")
        row = copy.deepcopy(record)
        thickness = row.get("thickness_m")
        status = row.get("evidence_status", "unknown")
        if status not in {"observed", "inferred", "unknown"}:
            raise ValueError("wall thickness evidence_status must be observed, inferred or unknown")
        if thickness is None:
            if status != "unknown":
                raise ValueError("a null thickness must have unknown evidence_status")
        elif _number(thickness, "thickness_m") <= 0 or status == "unknown":
            raise ValueError("a known thickness must be positive with observed or inferred evidence_status")
        side = row.get("reference_side", "unknown")
        if side not in _SIDES:
            raise ValueError("reference_side must be centerline, negative_face, positive_face or unknown")
        basis = row.get("basis", "No wall thickness was supplied for this line.")
        if not isinstance(basis, str) or not basis.strip():
            raise ValueError("wall_metadata basis must be nonempty text")
        refs = row.get("source_refs", [])
        if not isinstance(refs, list) or any(not isinstance(s, str) or not s.strip() for s in refs):
            raise ValueError("wall_metadata source_refs must be a list of nonempty strings")
        if thickness is not None and ("basis" not in row or not refs):
            raise ValueError("a known thickness requires explicit basis and source_refs")
        supplied[target] = {"target": target, "thickness_m": thickness,
                            "reference_side": side, "evidence_status": status,
                            "basis": basis, "source_refs": list(dict.fromkeys(refs))}
    complete = []
    for target in defaults:
        segments = partitions.get(target, [])
        has_segments = any(key in supplied for key in segments)
        if target in supplied and has_segments:
            raise ValueError(f"wall_metadata cannot mix {target} with its segment records")
        for key in segments if has_segments else [target]:
            complete.append(supplied.get(key, {
                "target": key, "thickness_m": None, "reference_side": "unknown",
                "evidence_status": "unknown", "basis": "No wall thickness was supplied for this line.",
                "source_refs": [],
            }))
    return copy.deepcopy(complete)


def _world_converter(plan, metadata):
    calibration = (metadata or {}).get("calibration", plan)
    transforms = []
    for axis in ("x", "y"):
        anchors = calibration[f"{axis}_anchors"]
        if len(anchors) != 2:
            raise ValueError("wall metadata needs two numeric anchors per axis")
        p0, v0 = [_number(v, "anchor") for v in anchors[0]]
        p1, v1 = [_number(v, "anchor") for v in anchors[1]]
        if p0 == p1 or v0 == v1:
            raise ValueError("wall metadata anchors must span a nonzero distance")
        slope = (v1 - v0) / (p1 - p0)
        transforms.append((slope, v0 - slope * p0))
    # Match the compiler's serialized micrometre coordinates exactly. This is
    # decimal representation, not a looser matching tolerance or geometry edit.
    return lambda p: [round(transforms[i][0] * p[i] + transforms[i][1], 6) for i in (0, 1)]


def _span(a, b):
    axes = [i for i in (0, 1) if abs(a[i] - b[i]) <= _EPS]
    if len(axes) != 1:
        raise ValueError("wall metadata requires nonzero orthogonal segments")
    normal = axes[0]
    return normal, (a[normal] + b[normal]) / 2, min(a[1-normal], b[1-normal]), max(a[1-normal], b[1-normal])


def _covered_length(intervals):
    end, length = -math.inf, 0.0
    for lo, hi in sorted(intervals):
        if hi > end:
            length += hi - max(lo, end)
            end = hi
    return length


def wall_reading_input(plan: dict, metadata: dict | None = None) -> dict:
    """Keep a compact, reusable per-floor observation in a generated proposal."""
    rows = validate_wall_metadata(plan)
    targets, _, _ = _targets(plan)
    world = _world_converter(plan, metadata)
    segments = {row["target"]: [_span(world(a), world(b)) for a, b in targets[row["target"]]]
                for row in rows}
    # The compiler's adopted world lines are authoritative after regularization.
    for partition in (metadata or {}).get("partition_mapping", []):
        target = f"partition:{partition['partition_id']}"
        points = partition["world_points_m"]
        spans = [_span(a, b) for a, b in zip(points, points[1:])]
        if target in segments:
            segments[target] = spans
        for i, span in enumerate(spans):
            if f"{target}:{i}" in segments:
                segments[f"{target}:{i}"] = [span]
    return {"floor_id": plan["floor_id"], "walls": [dict(row, segments_m=[
        [[position if axis == 0 else start, start if axis == 0 else position],
         [position if axis == 0 else end, end if axis == 0 else position]]
        for axis, position, start, end in segments[row["target"]]]) for row in rows]}


def _bind_wall_reading(source, reading):
    if not isinstance(reading, dict) or set(reading) != {"floor_id", "walls"}:
        raise ValueError("wall_readings require floor_id and walls")
    floor_id = reading["floor_id"]
    if not isinstance(floor_id, str) or not floor_id.strip():
        raise ValueError("wall_readings floor_id must be nonempty text")
    rows = reading["walls"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("wall_readings walls must be a nonempty list")
    segments = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != _FIELDS | {"segments_m"}:
            raise ValueError("invalid wall_readings wall record")
        target = row["target"]
        if not isinstance(target, str) or not target or target in segments:
            raise ValueError("wall_readings targets must be unique nonempty strings")
        raw_segments = row["segments_m"]
        if not isinstance(raw_segments, list) or not raw_segments:
            raise ValueError("wall_readings segments_m must be nonempty")
        parsed = []
        for segment in raw_segments:
            if (not isinstance(segment, list) or len(segment) != 2
                    or any(not isinstance(p, list) or len(p) != 2 for p in segment)):
                raise ValueError("wall_readings segments_m need two 2D points each")
            parsed.append(_span(*[[_number(v, "wall coordinate") for v in p] for p in segment]))
        segments[target] = parsed
        thickness = row["thickness_m"]
        if row["reference_side"] not in _SIDES or row["evidence_status"] not in {"observed", "inferred", "unknown"}:
            raise ValueError("invalid wall reading side or evidence_status")
        if thickness is None:
            if row["evidence_status"] != "unknown":
                raise ValueError("a null thickness must have unknown evidence_status")
        elif _number(thickness, "thickness_m") <= 0 or row["evidence_status"] == "unknown":
            raise ValueError("a known thickness must have positive observed or inferred evidence")
        if not isinstance(row["basis"], str) or not row["basis"].strip():
            raise ValueError("wall_readings basis must be nonempty")
        refs = row["source_refs"]
        if (not isinstance(refs, list) or any(not isinstance(r, str) or not r.strip() for r in refs)
                or (thickness is not None and not refs)):
            raise ValueError("known wall_readings require source_refs")
    spaces = {row["id"]: row for row in source["spaces"]}
    boundaries = {row["id"]: row for row in source["boundaries"]}
    matched, raw_references, attributes, used = set(), [], [], set()
    for boundary in source["boundaries"]:
        bid = boundary["id"]
        if (bid in used or boundary["geometry_type"] != "wall" or boundary["kind"] != "physical"
                or spaces[boundary["space_id"]]["floor_id"] != floor_id):
            continue
        points = sorted({tuple(p[:2]) for p in boundary["vertices"]})
        if len(points) != 2:
            raise ValueError(f"wall metadata requires a straight source wall: {bid}")
        axis, coordinate, lo, hi = _span(*points)
        covers = []
        intervals = []
        for row in rows:
            overlaps = [(max(lo, start), min(hi, end))
                        for normal, position, start, end in segments[row["target"]]
                        if normal == axis and abs(position-coordinate) <= _EPS
                        and min(hi, end) - max(lo, start) > _EPS]
            if overlaps:
                intervals.extend(overlaps)
                covers.append(row)
        if abs(_covered_length(intervals) - (hi-lo)) > _EPS:
            raise ValueError(f"source wall {bid} is not fully covered by this plan's wall lines")
        kinds = {(r["thickness_m"], r["reference_side"], r["evidence_status"]) for r in covers}
        if len(kinds) != 1:
            raise ValueError(f"source wall {bid} spans different wall metadata; explicit source segmentation is required")
        matched.update(r["target"] for r in covers)
        thickness, side, status = kinds.pop()
        basis = "; ".join(dict.fromkeys(r["basis"] for r in covers))
        refs = list(dict.fromkeys(ref for r in covers for ref in r["source_refs"]))
        refs.extend(f"plan-wall:{floor_id}/{r['target']}" for r in covers)
        congruent = all({tuple(p) for p in boundaries[other]["vertices"]}
                        == {tuple(p) for p in boundary["vertices"]}
                        for other in boundary.get("counterpart_ids", []))
        scope = "component" if congruent else "boundary"
        ids = [bid, *boundary.get("counterpart_ids", [])] if congruent else [bid]
        used.update(ids)
        reference = {"id": f"reader-wall:{bid}", "boundary_id": bid,
                     "offsets_m": None, "thickness_m": thickness,
                     "reference_basis": basis, "reference_side": side,
                     "thickness_scope": "entire declared plan line at this floor",
                     "evidence_status": status, "source_refs": refs}
        if scope == "boundary":
            reference["host_scope"] = "boundary"
        raw_references.append(reference)
        if thickness is not None:
            attributes.append(thickness_record(source, bid, thickness, basis=basis,
                                               source_refs=refs, host_scope=scope))
    if missing := set(segments) - matched:
        raise ValueError(f"wall metadata targets have no source wall on this floor: {sorted(missing)}")
    return {"wall_references": resolve_wall_references(source, raw_references),
            "component_attributes": validate_component_attributes(source, attributes)}


def bind_wall_readings(source: dict, readings: list[dict]) -> dict:
    """Bind saved per-floor evidence to regenerated source identities.

    Physical walls need an exact collinear cover. Different values within one
    unsplit source boundary are rejected. Partial contacts bind independently;
    no cross-floor wall recognition or geometric modification occurs.
    """
    if not isinstance(readings, list):
        raise ValueError("wall_readings must be a list")
    result = {"component_attributes": [], "wall_references": []}
    seen = set()
    for reading in readings:
        patch = _bind_wall_reading(source, reading)
        floor = reading["floor_id"]
        if floor in seen:
            raise ValueError(f"duplicate wall_readings floor {floor}")
        seen.add(floor)
        for field in result:
            result[field].extend(patch[field])
    return result


def bind_wall_metadata(source: dict, plan: dict, metadata: dict | None = None) -> dict:
    """Return a source-field patch without mutating source, plan or metadata."""
    return bind_wall_readings(source, [wall_reading_input(plan, metadata)])
