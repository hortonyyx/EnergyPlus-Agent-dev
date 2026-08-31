"""F-155: discriminate endpoint stitching from support-line intersections.

This probe never writes production inputs.  The F-154 reproduction temporarily
replaces two module callables in memory, restores them in ``finally``, and then
the actual experiment derives support spans from the facts-layer wall bands.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal

from shapely import Polygon
from shapely.validation import explain_validity

from src.agent.judge import as_measured as am


REPO = Path(__file__).resolve().parents[4]
SOURCE_DIR = REPO / "case_tests" / "test_baseline" / "gt_sources" / "sm25-L_anchor"
DXF = SOURCE_DIR / "sm25-L_t3_as_received.dxf"
REQUEST = SOURCE_DIR / "request_as_measured.json"
MIN_ROOM_AREA_M2 = float(json.loads(
    REQUEST.read_text(encoding="utf-8"))["min_room_area_m2"])
TARGET_AREAS_M2 = {
    "plan-F1": 88.27,
    "plan-F2": 70.34,
}
MISALIGNED_AREA_M2 = 28.68


@dataclass(frozen=True)
class SupportSpan:
    """One finite part of an infinite axis-aligned support line."""

    axis: Literal["x", "y"]
    const: int
    lo: int
    hi: int


def cavities_for(view: Any) -> list[Any]:
    footprint, _ = am._boundary_footprint(view)
    wall_region = am._boundary_wall_region(view)
    threshold = MIN_ROOM_AREA_M2 * am.UNITS_PER_METRE**2
    geometry = footprint.difference(wall_region)
    cavities = [
        part
        for part in getattr(geometry, "geoms", [geometry])
        if part.geom_type == "Polygon" and not part.is_empty and part.area > threshold
    ]
    return sorted(cavities, key=lambda item: tuple(round(v, 6) for v in item.bounds))


def cavity_id(view: Any, cavity: Any) -> str:
    return am._boundary_cavity_id(view.view_id, cavity)


def raw_supports(cavity: Any) -> list[SupportSpan]:
    points = [(int(round(x)), int(round(y))) for x, y in cavity.exterior.coords[:-1]]
    supports: list[SupportSpan] = []
    for first, second in zip(points, points[1:] + points[:1]):
        if first[0] == second[0] and first[1] != second[1]:
            supports.append(SupportSpan(
                axis="y", const=first[0], lo=min(first[1], second[1]),
                hi=max(first[1], second[1])))
        elif first[1] == second[1] and first[0] != second[0]:
            supports.append(SupportSpan(
                axis="x", const=first[1], lo=min(first[0], second[0]),
                hi=max(first[0], second[0])))
        else:
            raise AssertionError(f"non_axis_cavity_segment:{first}:{second}")
    return supports


def rectangle_supports(axis: str, face_lo: int, face_hi: int,
                       along_lo: int, along_hi: int) -> list[SupportSpan]:
    if axis == "x":
        return [
            SupportSpan("x", face_lo, along_lo, along_hi),
            SupportSpan("x", face_hi, along_lo, along_hi),
            SupportSpan("y", along_lo, face_lo, face_hi),
            SupportSpan("y", along_hi, face_lo, face_hi),
        ]
    return [
        SupportSpan("y", face_lo, along_lo, along_hi),
        SupportSpan("y", face_hi, along_lo, along_hi),
        SupportSpan("x", along_lo, face_lo, face_hi),
        SupportSpan("x", along_hi, face_lo, face_hi),
    ]


def facts_support_catalog(view: Any) -> list[SupportSpan]:
    """Finite supports available from facts, including exact wall endcaps."""
    catalog: list[SupportSpan] = []
    for wall in view.walls:
        catalog.extend(rectangle_supports(
            wall.axis, wall.face_lo, wall.face_hi,
            wall.along_min, wall.along_max))
    for opening in view.openings:
        catalog.extend(rectangle_supports(
            opening.axis, opening.cross_lo, opening.cross_hi,
            opening.along_min, opening.along_max))
    for ring in view.footprint.rings:
        points = [tuple(point) for point in ring.points]
        if len(points) > 1 and points[0] == points[-1]:
            points.pop()
        for first, second in zip(points, points[1:] + points[:1]):
            if first[0] == second[0] and first[1] != second[1]:
                catalog.append(SupportSpan(
                    "y", first[0], min(first[1], second[1]),
                    max(first[1], second[1])))
            elif first[1] == second[1] and first[0] != second[0]:
                catalog.append(SupportSpan(
                    "x", first[1], min(first[0], second[0]),
                    max(first[0], second[0])))
    return catalog


def facts_backed_supports(view: Any, cavity: Any) -> list[SupportSpan]:
    """Use the cavity only for cyclic topology; source every line from facts."""
    catalog = facts_support_catalog(view)
    selected: list[SupportSpan] = []
    for boundary in raw_supports(cavity):
        intervals = sorted(
            (item.lo, item.hi) for item in catalog
            if (item.axis, item.const) == (boundary.axis, boundary.const)
            and min(item.hi, boundary.hi) - max(item.lo, boundary.lo) > 0
        )
        if not intervals:
            raise AssertionError(f"support_not_in_facts:{boundary}")
        cursor = boundary.lo
        for lo, hi in intervals:
            if hi <= cursor:
                continue
            if lo > cursor:
                break
            cursor = max(cursor, hi)
            if cursor >= boundary.hi:
                break
        if cursor < boundary.hi:
            raise AssertionError(
                f"support_interval_not_covered:{boundary}:covered_to={cursor}")
        selected.append(SupportSpan(
            boundary.axis, boundary.const,
            min(lo for lo, _ in intervals), max(hi for _, hi in intervals)))
    return selected


def merge_cyclic_collinear(supports: list[SupportSpan]) -> list[SupportSpan]:
    """Collapse consecutive fragments that propagate one support line."""
    if not supports:
        return []
    start = next(
        (index for index, item in enumerate(supports)
         if (supports[index - 1].axis, supports[index - 1].const)
         != (item.axis, item.const)),
        0,
    )
    rotated = supports[start:] + supports[:start]
    merged: list[SupportSpan] = []
    for item in rotated:
        if merged and (merged[-1].axis, merged[-1].const) == (item.axis, item.const):
            previous = merged[-1]
            merged[-1] = SupportSpan(
                axis=item.axis, const=item.const,
                lo=min(previous.lo, item.lo), hi=max(previous.hi, item.hi))
        else:
            merged.append(item)
    return merged


def intersection_ring(view: Any, cavity: Any) -> tuple[
        list[SupportSpan], list[tuple[int, int]], Any, int]:
    supports = merge_cyclic_collinear(facts_backed_supports(view, cavity))
    vertices: list[tuple[int, int]] = []
    interval_misses = 0
    for index, current in enumerate(supports):
        previous = supports[index - 1]
        if previous.axis == current.axis:
            raise AssertionError(
                f"adjacent_supports_parallel:{previous}:{current}")
        if previous.axis == "y":
            vertex = (previous.const, current.const)
            previous_along, current_along = vertex[1], vertex[0]
        else:
            vertex = (current.const, previous.const)
            previous_along, current_along = vertex[0], vertex[1]
        interval_misses += int(not (previous.lo <= previous_along <= previous.hi))
        interval_misses += int(not (current.lo <= current_along <= current.hi))
        vertices.append(vertex)
    return supports, vertices, Polygon(vertices), interval_misses


def exact_endcap_groups(
    groups: dict[Any, Any], face_by_id: dict[str, Any], axis: str,
    const: int, lo: int, hi: int,
) -> list[Any]:
    """Independently resolve exact perpendicular wall ends for the F-154 control.

    A candidate wall must end at ``const``, cross this span with positive
    transverse overlap, and have both of its measured faces terminate on the
    two faces of one continuing wall band.  There is no distance tolerance.
    """
    found: dict[tuple[str, int, int], Any] = {}
    continuing = [group for group in groups.values() if group.axis == axis]
    for candidate in groups.values():
        if candidate.axis == axis:
            continue
        for wall in candidate.runs:
            if const == wall.along_min:
                endpoint = "along_min"
            elif const == wall.along_max:
                endpoint = "along_max"
            else:
                continue
            if min(hi, wall.face_hi) - max(lo, wall.face_lo) <= 0:
                continue
            for junction in continuing:
                if const not in (junction.face_lo, junction.face_hi):
                    continue
                if not any(
                    min(hi, run_hi) - max(lo, run_lo) >= 0
                    for run_lo, run_hi in junction.coverage()
                ):
                    continue
                junction_faces = {junction.face_lo, junction.face_hi}
                lo_proof = any(
                    getattr(face_by_id[handle], endpoint) in junction_faces
                    for handle in wall.face_line_ids_lo if handle in face_by_id
                )
                hi_proof = any(
                    getattr(face_by_id[handle], endpoint) in junction_faces
                    for handle in wall.face_line_ids_hi if handle in face_by_id
                )
                if lo_proof and hi_proof:
                    found[candidate.key] = candidate
                    break
    return [found[key] for key in sorted(found)]


def reproduce_f154(view: Any) -> tuple[list[Any], list[Any]]:
    """Run the old endpoint-ring construction with exact endcaps, in memory."""
    original_owners = am._boundary_owners
    original_classifier = am._classify_boundary_fact
    groups = am._boundary_wall_groups(view)
    face_by_id = {face.id: face for face in view.face_lines}
    target_area = TARGET_AREAS_M2[view.view_id]
    target_cavities = [
        cavity for cavity in cavities_for(view)
        if abs(cavity.area / am.UNITS_PER_METRE**2 - target_area) < 0.01
    ]
    assert len(target_cavities) == 1, (view.view_id, len(target_cavities))
    target_spans = {
        (span.axis, span.const, span.lo, span.hi)
        for span in raw_supports(target_cavities[0])
    }

    def owners(
        live_groups: dict[Any, Any], axis: str, const: int, lo: int, hi: int,
    ) -> list[Any]:
        ordinary = original_owners(live_groups, axis, const, lo, hi)
        if ordinary:
            return ordinary
        if (axis, const, lo, hi) not in target_spans:
            return []
        return exact_endcap_groups(groups, face_by_id, axis, const, lo, hi)

    def classifier(span: Any, raw_near: int, raw_far: int, footprint: Any,
                   ring_records: Any, wall_region: Any, cavities: Any,
                   cavity_ids: Any) -> tuple[str, Any, bool]:
        if span.group.axis == span.axis:
            return original_classifier(
                span, raw_near, raw_far, footprint, ring_records,
                wall_region, cavities, cavity_ids)
        outward = -span.side
        midpoint = (span.lo + span.hi) // 2
        exit_point = ([span.cavity_const + outward, midpoint]
                      if span.axis == "y"
                      else [midpoint, span.cavity_const + outward])
        near_side = "lo" if span.side < 0 else "hi"
        far_side = "hi" if near_side == "lo" else "lo"
        evidence = am.BoundaryConditionEvidenceV1(
            raw_face_const=raw_near,
            opposite_face_const=raw_far,
            thickness_units=abs(raw_far - raw_near),
            outward_normal=([outward, 0] if span.axis == "y" else [0, outward]),
            exit_point=exit_point,
            footprint_ring_id=ring_records[0][0],
            cavity_side_face_line_ids=span.group.handles(near_side),
            far_side_face_line_ids=span.group.handles(far_side),
        )
        return "interzone", evidence, True

    am._boundary_owners = owners
    am._classify_boundary_fact = classifier
    try:
        derivation = am._derive_boundary_facts(
            view, min_room_area_m2=MIN_ROOM_AREA_M2)
    finally:
        am._boundary_owners = original_owners
        am._classify_boundary_fact = original_classifier
    return derivation.edges, derivation.losses


def print_endpoint_control(view: Any, edges: list[Any], losses: list[Any]) -> None:
    by_cavity: dict[str, list[Any]] = defaultdict(list)
    for edge in edges:
        by_cavity[edge.cavity_id].append(edge)
    print(f"CONTROL {view.view_id} total_edges={len(edges)} losses={len(losses)}")
    for cid, group in sorted(by_cavity.items()):
        ordered = sorted(group, key=lambda edge: edge.sequence)
        polygon = Polygon([edge.p1 for edge in ordered])
        print(
            f"CONTROL_RING {view.view_id} {cid} edges={len(ordered)} "
            f"valid={polygon.is_valid} explain={explain_validity(polygon)}"
        )
    for loss in sorted(losses, key=lambda item: item.cavity_id):
        print(
            f"CONTROL_LOSS {view.view_id} {loss.cavity_id} "
            f"area_m2={loss.area_units2 / am.UNITS_PER_METRE**2:.6f}"
        )


def main() -> None:
    document = am.build_as_measured(DXF, REQUEST)
    all_rows: dict[str, dict[str, tuple[Any, list[SupportSpan], Any, int]]] = {}
    baseline_edge_counts: dict[str, dict[str, int]] = {}

    print("=== F154_ENDPOINT_CONTROL ===")
    for view in document.views:
        baseline_edges = am.derive_boundary_edges(
            view, min_room_area_m2=MIN_ROOM_AREA_M2)
        counts: dict[str, int] = defaultdict(int)
        for edge in baseline_edges:
            counts[edge.cavity_id] += 1
        baseline_edge_counts[view.view_id] = dict(counts)
        reproduced_edges, reproduced_losses = reproduce_f154(view)
        print_endpoint_control(view, reproduced_edges, reproduced_losses)

    print("=== SUPPORT_INTERSECTION_EXPERIMENT ===")
    for view in document.views:
        rows: dict[str, tuple[Any, list[SupportSpan], Any, int]] = {}
        for cavity in cavities_for(view):
            cid = cavity_id(view, cavity)
            supports, vertices, rebuilt, interval_misses = intersection_ring(view, cavity)
            symdiff_m2 = rebuilt.symmetric_difference(cavity).area / am.UNITS_PER_METRE**2
            rows[cid] = (cavity, supports, rebuilt, interval_misses)
            print(
                f"REBUILT {view.view_id} {cid} supports={len(supports)} "
                f"vertices={len(vertices)} valid={rebuilt.is_valid} "
                f"explain={explain_validity(rebuilt)} "
                f"area_m2={rebuilt.area / am.UNITS_PER_METRE**2:.6f} "
                f"source_symdiff_m2={symdiff_m2:.6f} "
                f"interval_misses={interval_misses}"
            )
        all_rows[view.view_id] = rows

    print("=== REQUIRED_SUMMARY ===")
    for view_id, target_area in TARGET_AREAS_M2.items():
        matches = [
            (cid, data) for cid, data in all_rows[view_id].items()
            if abs(data[0].area / am.UNITS_PER_METRE**2 - target_area) < 0.01
        ]
        assert len(matches) == 1, (view_id, target_area, len(matches))
        cid, (source, supports, rebuilt, misses) = matches[0]
        print(
            f"TARGET {view_id} {cid} valid={rebuilt.is_valid} "
            f"explain={explain_validity(rebuilt)} vertices={len(supports)} "
            f"area_m2={rebuilt.area / am.UNITS_PER_METRE**2:.6f} "
            f"expected_m2={target_area:.2f} "
            f"delta_m2={rebuilt.area / am.UNITS_PER_METRE**2 - target_area:+.6f} "
            f"interval_misses={misses}"
        )
        print(
            f"TARGET_SUPPORTS {view_id} {cid} "
            + " ".join(
                f"{item.axis}:{item.const}[{item.lo},{item.hi}]"
                for item in supports)
        )

    healthy = []
    for view_id, counts in baseline_edge_counts.items():
        for cid, edge_count in counts.items():
            source, supports, rebuilt, misses = all_rows[view_id][cid]
            healthy.append((view_id, cid, edge_count, len(supports), rebuilt.is_valid, misses))
    print(
        f"HEALTHY count={len(healthy)} all_baseline_edges_4="
        f"{all(item[2] == 4 for item in healthy)} "
        f"all_rebuilt_vertices_4={all(item[3] == 4 for item in healthy)} "
        f"all_valid={all(item[4] for item in healthy)} "
        f"all_interval_misses_0={all(item[5] == 0 for item in healthy)}"
    )

    misaligned = []
    for view_id, rows in all_rows.items():
        for cid, data in rows.items():
            area_m2 = data[0].area / am.UNITS_PER_METRE**2
            if abs(area_m2 - MISALIGNED_AREA_M2) < 0.01:
                misaligned.append((view_id, cid, data))
    assert len(misaligned) == 1, len(misaligned)
    view_id, cid, (_source, supports, rebuilt, misses) = misaligned[0]
    print(
        f"MISALIGNED_0P1MM {view_id} {cid} alive={rebuilt.is_valid} "
        f"explain={explain_validity(rebuilt)} vertices={len(supports)} "
        f"area_m2={rebuilt.area / am.UNITS_PER_METRE**2:.6f} "
        f"interval_misses={misses}"
    )


if __name__ == "__main__":
    main()
