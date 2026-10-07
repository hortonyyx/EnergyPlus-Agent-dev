"""Validate model-read plan dimension chains and apply annotation-first alignment."""
from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from src.agent.geometry.plan_ink_alignment import (
    _attachment_requirements,
    _append_line_reference,
    _axis_scale,
    _finite,
    _footprint_preserves_declarations,
    _orthogonal_ids,
    _segments,
    _set_reading_alignment,
    move_straight_wall,
)


SCHEMA_VERSION = "plan_reading_dimension_alignment_v1"
MAX_ALIGNMENT_WORLD_M = 0.30
MAX_CLOSURE_ERROR_MM = 1.0
MAX_CHAIN_CROSS_CHECK_M = MAX_CLOSURE_ERROR_MM / 1000.0
MAX_CHAIN_SCALE_RELATIVE_ERROR = 0.01


def _world(anchors: list[list[float]], pixel: float) -> float:
    (p0, w0), (p1, w1) = anchors
    return float(w0) + (float(pixel) - float(p0)) * (float(w1) - float(w0)) / (float(p1) - float(p0))


def _chain_shape(raw: object, index: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    path = f"dimension_chains[{index}]"
    if not isinstance(raw, Mapping):
        return None, {"chain_id": f"index:{index}", "reason": f"{path} must be an object"}
    required = {"id", "axis", "segments_mm", "total_mm", "tick_pixels", "source_refs"}
    allowed = required | {"start_world_m"}
    unknown = sorted(set(raw) - allowed)
    missing = sorted(required - set(raw))
    chain_id = raw.get("id", f"index:{index}")
    if unknown or missing:
        return None, {"chain_id": chain_id, "reason": f"fields missing={missing}, unknown={unknown}"}
    if not isinstance(chain_id, str) or not chain_id.strip():
        return None, {"chain_id": f"index:{index}", "reason": "id must be nonempty text"}
    axis = raw.get("axis")
    segments = raw.get("segments_mm")
    ticks = raw.get("tick_pixels")
    total = raw.get("total_mm")
    refs = raw.get("source_refs")
    start_world = raw.get("start_world_m")
    if axis not in {"x", "y"}:
        return None, {"chain_id": chain_id, "reason": "axis must be x or y"}
    if (not isinstance(segments, list) or not segments
            or any(not _finite(value) or float(value) <= 0 for value in segments)):
        return None, {"chain_id": chain_id, "reason": "segments_mm must be positive finite millimetres"}
    if (not isinstance(ticks, list) or len(ticks) != len(segments) + 1
            or any(not _finite(value) for value in ticks)):
        return None, {"chain_id": chain_id,
                      "reason": "tick_pixels must contain one numeric axis pixel more than segments_mm"}
    if not _finite(total) or float(total) <= 0:
        return None, {"chain_id": chain_id, "reason": "total_mm must be positive finite millimetres"}
    if not isinstance(refs, list) or not refs or any(not isinstance(value, str) or not value.strip() for value in refs):
        return None, {"chain_id": chain_id, "reason": "source_refs must contain evidence text"}
    if "start_world_m" in raw and not _finite(start_world):
        return None, {"chain_id": chain_id, "reason": "start_world_m must be a finite world coordinate"}
    if any(float(second) <= float(first) for first, second in zip(ticks, ticks[1:])) and any(
            float(second) >= float(first) for first, second in zip(ticks, ticks[1:])):
        return None, {"chain_id": chain_id, "reason": "tick_pixels must be strictly monotonic"}
    chain = {
        "id": chain_id,
        "axis": axis,
        "segments_mm": [float(value) for value in segments],
        "total_mm": float(total),
        "tick_pixels": [float(value) for value in ticks],
        "source_refs": list(refs),
    }
    if "start_world_m" in raw:
        chain["start_world_m"] = float(start_world)
    return chain, None


def _check_chain(chain: Mapping[str, Any]) -> dict[str, Any]:
    segments = chain["segments_mm"]
    ticks = chain["tick_pixels"]
    total = chain["total_mm"]
    segment_sum = math.fsum(segments)
    closure = segment_sum - total
    cumulative = [0.0]
    for value in segments:
        cumulative.append(math.fsum((cumulative[-1], value)))
    pixel_span = ticks[-1] - ticks[0]
    predicted = [ticks[0] + pixel_span * value / total for value in cumulative]
    residual_px = [ticks[index] - predicted[index] for index in range(len(ticks))]
    mm_per_pixel = total / abs(pixel_span) if pixel_span else math.inf
    residual_mm = [value * mm_per_pixel for value in residual_px]
    segment_pixel_mm = [abs(ticks[index + 1] - ticks[index]) * mm_per_pixel
                        for index in range(len(segments))]
    segment_residual_mm = [segment_pixel_mm[index] - segments[index]
                           for index in range(len(segments))]
    pixel_tolerance = max(2.0, 0.01 * abs(pixel_span))
    closure_ok = abs(closure) <= MAX_CLOSURE_ERROR_MM
    scale_ok = bool(pixel_span) and max(map(abs, residual_px), default=0.0) <= pixel_tolerance
    worst_segment = max(range(len(segments)), key=lambda index: abs(segment_residual_mm[index]))
    return {
        "chain_id": chain["id"],
        "axis": chain["axis"],
        "segment_sum_mm": round(segment_sum, 6),
        "total_mm": total,
        "closure_error_mm": round(closure, 6),
        "pixel_span": round(pixel_span, 6),
        "mm_per_pixel_from_chain": None if not math.isfinite(mm_per_pixel) else round(mm_per_pixel, 6),
        "tick_residual_pixels": [round(value, 6) for value in residual_px],
        "tick_residual_mm": [None if not math.isfinite(value) else round(value, 3) for value in residual_mm],
        "pixel_residual_tolerance": round(pixel_tolerance, 6),
        "segment_pixel_residual_mm": [None if not math.isfinite(value) else round(value, 3)
                                      for value in segment_residual_mm],
        "worst_segment_index": worst_segment,
        "closure_ok": closure_ok,
        "scale_ok": scale_ok,
        "accepted": closure_ok and scale_ok,
    }


def _footprint_span(plan: Mapping[str, Any], axis: str) -> tuple[float, float]:
    index = 0 if axis == "x" else 1
    values = [float(point[index]) for point in plan.get("footprint_pixels", [])
              if isinstance(point, list) and len(point) == 2 and _finite(point[index])]
    if len(values) < 4:
        raise ValueError("dimension alignment needs a numeric footprint_pixels ring")
    return min(values), max(values)


def _overall_direction(chain: Mapping[str, Any], footprint: tuple[float, float],
                       endpoint_tolerance_px: float) -> int | None:
    first, last = chain["tick_pixels"][0], chain["tick_pixels"][-1]
    lo, hi = footprint
    if abs(first - lo) <= endpoint_tolerance_px and abs(last - hi) <= endpoint_tolerance_px:
        return 1
    if abs(first - hi) <= endpoint_tolerance_px and abs(last - lo) <= endpoint_tolerance_px:
        return -1
    return None


def _append_coordinate_references(plan: dict[str, Any], chain: Mapping[str, Any],
                                  coordinates: list[float]) -> None:
    rows = plan.setdefault("regularization_inputs", {}).setdefault("coordinate_references", [])
    for index, coordinate in enumerate(coordinates):
        row = {"axis": chain["axis"], "value_m": round(coordinate, 9), "basis": "dimension",
               "chain_id": chain["id"], "tick_index": index,
               "source_refs": list(chain["source_refs"])}
        if not any(existing.get("axis") == row["axis"]
                   and abs(float(existing.get("value_m", math.inf)) - row["value_m"]) <= 1e-9
                   and existing.get("chain_id") == row["chain_id"]
                   and existing.get("tick_index") == index for existing in rows):
            rows.append(row)


def _snap_partitions(plan: dict[str, Any], *, axis: str, target_pixels: list[float],
                     mpp: float, chain: Mapping[str, Any]) -> list[dict[str, Any]]:
    changes = []
    # A vertical wall has an x coordinate; a horizontal wall has a y coordinate.
    expected_along = "y" if axis == "x" else "x"
    for partition in plan.get("partitions", []):
        segments = list(_segments(partition.get("points", [])))
        if len(segments) != 1:
            continue
        _, along_axis, _, old_cross, span = segments[0]
        if along_axis != expected_along:
            continue
        target = min(target_pixels, key=lambda value: abs(value - old_cross))
        distance_m = abs(target - old_cross) * mpp
        if distance_m >= MAX_ALIGNMENT_WORLD_M:
            continue
        attached = move_straight_wall(
            plan, collection="partitions", identity=str(partition["id"]),
            along_axis=along_axis, old_cross=old_cross, new_cross=target, span=span,
        )
        _append_line_reference(plan, partition_id=str(partition["id"]), basis="dimension",
                               source_refs=[*partition.get("source_refs", []), *chain["source_refs"],
                                            f"dimension_chain:{chain['id']}"])
        changes.append({
            "object": f"partition:{partition['id']}",
            "kind": "partition",
            "axis": axis,
            "from_pixel": round(old_cross, 6),
            "to_pixel": round(target, 6),
            "movement_m": round((target - old_cross) * mpp, 6),
            "chain_id": chain["id"],
            "basis": "dimension",
            "moved_with_wall": attached,
        })
    return changes


def _snap_footprint(plan: dict[str, Any], *, axis: str, target_pixels: list[float],
                    mpp: float, chain: Mapping[str, Any]) -> tuple[list[dict[str, Any]],
                                                                   list[dict[str, Any]]]:
    changes: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    expected_along = "y" if axis == "x" else "x"
    ring = plan.get("footprint_pixels", [])
    if not isinstance(ring, list) or len(ring) < 4:
        return changes, rejections

    # Each edge is considered once against verified ticks on its own axis.
    # A nearby tick on the other axis cannot authorize a move.
    for edge_index in range(len(ring)):
        segment = next(row for row in _segments(plan["footprint_pixels"], closed=True)
                       if row[0] == edge_index)
        _, along_axis, _, old_cross, span = segment
        if along_axis != expected_along:
            continue
        target = min(target_pixels, key=lambda value: abs(value - old_cross))
        distance_m = abs(target - old_cross) * mpp
        if distance_m >= MAX_ALIGNMENT_WORLD_M or abs(target - old_cross) <= 1e-9:
            continue

        before_edge = copy.deepcopy(plan)
        orthogonal_partitions, orthogonal_openings = _orthogonal_ids(plan)
        partition_attachments, opening_hosts = _attachment_requirements(plan)
        attached = move_straight_wall(
            plan, collection="footprint", identity=str(edge_index),
            along_axis=along_axis, old_cross=old_cross, new_cross=target, span=span,
        )
        safe, reason = _footprint_preserves_declarations(
            plan,
            orthogonal_partitions=orthogonal_partitions,
            orthogonal_openings=orthogonal_openings,
            partition_attachments=partition_attachments,
            opening_hosts=opening_hosts,
        )
        base = {
            "object": f"footprint:{edge_index}",
            "kind": "perimeter",
            "axis": axis,
            "from_pixel": round(old_cross, 6),
            "to_pixel": round(target, 6),
            "movement_m": round((target - old_cross) * mpp, 6),
            "chain_id": chain["id"],
            "basis": "dimension",
        }
        if not safe:
            plan.clear()
            plan.update(before_edge)
            rejections.append({**base, "action": "rejected", "reason": reason})
            continue

        for partition_id in attached["walls"]:
            partition = next((row for row in plan.get("partitions", [])
                              if str(row.get("id")) == partition_id), None)
            _append_line_reference(
                plan, partition_id=partition_id, basis="dimension",
                source_refs=[*(partition or {}).get("source_refs", []), *chain["source_refs"],
                             f"dimension_chain:{chain['id']}"],
            )
        changes.append({**base, "action": "moved", "moved_with_wall": attached})
    return changes, rejections


def align_plan_to_dimensions(plan: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate dimension chains, then let accepted overall chains set axis frames.

    A chain can replace an axis calibration only when its first and last ticks
    correspond to the two footprint outer faces.  Internal chains are checked
    and reported but never silently promoted to a whole-axis origin/scale.
    """

    if not isinstance(plan, Mapping):
        raise TypeError("plan must be an object")
    result = copy.deepcopy(dict(plan))
    raw_chains = result.pop("dimension_chains", [])
    if raw_chains is None:
        raw_chains = []
    if not isinstance(raw_chains, list):
        raw_chains = [{"invalid": raw_chains}]
    items: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    accepted_axes: set[str] = set()
    applied_chains = 0
    supplemental_chains = 0

    for index, raw in enumerate(raw_chains):
        chain, error = _chain_shape(raw, index)
        if error is not None:
            rejections.append(error)
            continue
        assert chain is not None
        check = _check_chain(chain)
        if not check["accepted"]:
            check["action"] = "rejected"
            check["reason"] = ("segment sum does not close to total" if not check["closure_ok"]
                               else "tick spacing is inconsistent with the annotated segment ratios")
            rejections.append(check)
            continue

        axis = chain["axis"]
        old_anchors = copy.deepcopy(result[f"{axis}_anchors"])
        mpp_before = _axis_scale(result, axis)
        footprint = _footprint_span(result, axis)
        endpoint_tolerance_px = max(2.0, MAX_ALIGNMENT_WORLD_M / mpp_before)
        direction_px = _overall_direction(chain, footprint, endpoint_tolerance_px)
        if direction_px is None:
            items.append({**check, "action": "checked_not_applied", "overall": False,
                          "reason": "first and last ticks do not correspond to both footprint outer faces",
                          "footprint_pixels": [round(value, 6) for value in footprint],
                          "endpoint_tolerance_pixels": round(endpoint_tolerance_px, 6)})
            continue
        start_px = footprint[0] if direction_px == 1 else footprint[1]
        end_px = footprint[1] if direction_px == 1 else footprint[0]
        old_start_world = _world(old_anchors, start_px)
        old_end_world = _world(old_anchors, end_px)
        old_world_direction = 1 if old_end_world > old_start_world else -1
        origin_basis = "dimension_chain" if "start_world_m" in chain else "legacy_anchor"
        start_world = chain.get("start_world_m", old_start_world)
        end_world = start_world + old_world_direction * chain["total_mm"] / 1000.0
        cumulative = [0.0]
        for value in chain["segments_mm"]:
            cumulative.append(math.fsum((cumulative[-1], value)))
        world_ticks = [start_world + old_world_direction * value / 1000.0 for value in cumulative]
        target_pixels = [start_px + (end_px - start_px) * value / chain["total_mm"] for value in cumulative]

        if axis in accepted_axes:
            start_difference = start_world - old_start_world
            end_difference = end_world - old_end_world
            maximum_difference = max(abs(start_difference), abs(end_difference))
            existing_mpp = _axis_scale(result, axis)
            supplemental_mpp = ((chain["total_mm"] / 1000.0)
                                / abs(chain["tick_pixels"][-1] - chain["tick_pixels"][0]))
            scale_relative_difference = abs(supplemental_mpp - existing_mpp) / existing_mpp
            consistent = (maximum_difference <= MAX_CHAIN_CROSS_CHECK_M
                          and scale_relative_difference <= MAX_CHAIN_SCALE_RELATIVE_ERROR)
            cross_check = {
                "existing_start_world_m": round(old_start_world, 9),
                "supplemental_start_world_m": round(start_world, 9),
                "start_difference_m": round(start_difference, 9),
                "existing_end_world_m": round(old_end_world, 9),
                "supplemental_end_world_m": round(end_world, 9),
                "end_difference_m": round(end_difference, 9),
                "maximum_absolute_difference_m": round(maximum_difference, 9),
                "tolerance_m": MAX_CHAIN_CROSS_CHECK_M,
                "existing_metres_per_pixel": round(existing_mpp, 12),
                "supplemental_metres_per_pixel": round(supplemental_mpp, 12),
                "scale_relative_difference": round(scale_relative_difference, 9),
                "scale_relative_tolerance": MAX_CHAIN_SCALE_RELATIVE_ERROR,
                "status": "consistent" if consistent else "conflict",
            }
            if not consistent:
                rejections.append({
                    **check,
                    "action": "rejected",
                    "reason": "supplemental overall chain conflicts with the accepted axis scale or origin",
                    "axis_cross_check": cross_check,
                })
                continue

            _append_coordinate_references(result, chain, world_ticks)
            edge_changes, edge_rejections = _snap_footprint(
                result, axis=axis, target_pixels=target_pixels,
                mpp=_axis_scale(result, axis), chain=chain,
            )
            snapped = [*edge_changes, *_snap_partitions(
                result, axis=axis, target_pixels=target_pixels,
                mpp=_axis_scale(result, axis), chain=chain,
            )]
            changes.extend(snapped)
            rejections.extend(edge_rejections)
            applied_chains += 1
            supplemental_chains += 1
            items.append({
                **check,
                "action": "supplemental_ticks_applied",
                "overall": True,
                "origin_basis": origin_basis,
                "axis_cross_check": cross_check,
                "exact_tick_world_m": [round(value, 9) for value in world_ticks],
                "exact_tick_pixels": [round(value, 6) for value in target_pixels],
                "snapped_object_count": len(snapped),
            })
            continue

        result[f"{axis}_anchors"] = [[start_px, start_world], [end_px, end_world]]
        _append_coordinate_references(result, chain, world_ticks)
        mpp = abs((end_world - start_world) / (end_px - start_px))
        edge_changes, edge_rejections = _snap_footprint(
            result, axis=axis, target_pixels=target_pixels, mpp=mpp, chain=chain,
        )
        snapped = [*edge_changes, *_snap_partitions(
            result, axis=axis, target_pixels=target_pixels, mpp=mpp, chain=chain,
        )]
        accepted_axes.add(axis)
        applied_chains += 1
        changes.extend(snapped)
        rejections.extend(edge_rejections)
        start_difference = start_world - old_start_world
        end_difference = end_world - old_end_world
        maximum_difference = max(abs(start_difference), abs(end_difference))
        items.append({**check, "action": "axis_calibration_applied", "overall": True,
                      "origin_basis": origin_basis,
                      "outer_face_start": {"pixel": round(start_px, 6), "world_m": round(start_world, 9)},
                      "outer_face_end": {"pixel": round(end_px, 6), "world_m": round(end_world, 9)},
                      "old_anchors": old_anchors,
                      "new_anchors": copy.deepcopy(result[f"{axis}_anchors"]),
                      "anchor_cross_check": {
                          "origin_basis": origin_basis,
                          "old_start_world_m": round(old_start_world, 9),
                          "dimension_start_world_m": round(start_world, 9),
                          "start_difference_m": round(start_difference, 9),
                          "old_end_world_m": round(old_end_world, 9),
                          "dimension_end_world_m": round(end_world, 9),
                          # Retain the former end-only key for report consumers.
                          "difference_m": round(end_difference, 9),
                          "end_difference_m": round(end_difference, 9),
                          "maximum_absolute_difference_m": round(maximum_difference, 9),
                          "tolerance_m": MAX_ALIGNMENT_WORLD_M,
                          "status": "consistent" if maximum_difference < MAX_ALIGNMENT_WORLD_M else "warning",
                          "message": (
                              "legacy anchors supply the origin and agree with the accepted overall chain"
                              if origin_basis == "legacy_anchor" and maximum_difference < MAX_ALIGNMENT_WORLD_M else
                              "legacy anchors supply the origin but disagree with the accepted overall chain scale"
                              if origin_basis == "legacy_anchor" else
                              "legacy anchors agree with the dimension-chain origin and endpoint"
                              if maximum_difference < MAX_ALIGNMENT_WORLD_M else
                              "legacy anchors disagree with the dimension-chain origin or endpoint; the chain sets the axis"
                          ),
                      },
                      "exact_tick_world_m": [round(value, 9) for value in world_ticks],
                      "exact_tick_pixels": [round(value, 6) for value in target_pixels],
                      "snapped_object_count": len(snapped),
                      "snapped_partition_count": sum(row["kind"] == "partition" for row in snapped),
                      "snapped_footprint_edge_count": sum(row["kind"] == "perimeter" for row in snapped)})

    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "applied" if applied_chains or changes else ("rejected" if rejections else "unchanged"),
        "tolerances": {
            "closure_mm": MAX_CLOSURE_ERROR_MM,
            "tick_residual_pixels": "max(2 pixels, 1% of chain pixel span)",
            "wall_to_tick_m": MAX_ALIGNMENT_WORLD_M,
            "overall_endpoint_m": MAX_ALIGNMENT_WORLD_M,
            "supplemental_chain_cross_check_m": MAX_CHAIN_CROSS_CHECK_M,
            "supplemental_chain_scale_relative": MAX_CHAIN_SCALE_RELATIVE_ERROR,
        },
        "summary": {
            "chains_supplied": len(raw_chains),
            "chains_applied": applied_chains,
            "axes_calibrated": len(accepted_axes),
            "supplemental_chains_applied": supplemental_chains,
            "walls_snapped": len(changes),
            "partitions_snapped": sum(row["kind"] == "partition" for row in changes),
            "footprint_edges_snapped": sum(row["kind"] == "perimeter" for row in changes),
            "rejected": len(rejections),
        },
        "items": items,
        "changes": changes,
        "rejections": rejections,
    }
    _set_reading_alignment(result, "dimensions", report)
    return result, report
