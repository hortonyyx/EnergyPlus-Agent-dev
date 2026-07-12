"""A0 §7 deterministic geometry validation on CorrectedGeometry (M2a / S1).

These are the *data-level* geometry invariants 1_correction must satisfy before
the kernel runs — checked on the corrected primitives (cells/windows/z), not on
the built surface graph (that is kernel.py's job). They are deterministic facts;
the check adapter (validator/checks/correction.py) wraps them into a CheckReport.

Invariants (block — A0 §7):
  - **coverage**: per floor, cells tile the footprint with no holes and no
    overlaps (within tolerance). A hole is unmodelled floor area; an overlap is a
    correction defect (e.g. a corridor laid over the rooms it sits between).
  - **closure / non-degenerate**: every cell rectangle has positive extent on
    both axes; the footprint is non-degenerate.
  - **z-stack continuity**: adjacent floors stack with no gap/overlap beyond
    tolerance (a gap would model a mid-building interface as Roof + exposed Floor).

Cross-checks (flag):
  - **zone-count tripwire**: per-floor cell count vs testdata ``thermal_zones``
    (catches the 2f corridor-over-split class of coarse error).
  - **window-on-wall**: every window's along-facade span lies within its room's
    extent on that facade (catches axis-flip placement / floating windows).

Returns plain ``GeometryFinding`` lists; severity→layer mapping is the adapter's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shapely.ops import unary_union

from src.agent.correction.cell_geometry import (
    cell_bbox,
    cell_facade_span,
    cell_polygon,
    cell_has_polygon,
    validate_cell_polygon,
)
from src.agent.correction.schema import CorrectedGeometry
from src.agent.correction.footprint import floor_footprint
from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.geometry.capability import FEATURE_CELL_POLYGON, schema_supports

_AREA_TOL = 0.05      # m^2 — ignore coverage gaps/overlaps below this
_Z_TOL = 0.02         # m — z-stack contiguity tolerance (matches kernel _Z_TOL)
_MIN_EXTENT = 0.05    # m — degenerate cell threshold
_SPAN_TOL = 0.10      # m — window-span-within-room tolerance


@dataclass
class GeometryFinding:
    check_id: str
    ok: bool
    message: str = ""
    evidence: dict = field(default_factory=dict)


def _cell_box(c) -> object:
    return cell_polygon(c)


def check_cell_polygon_contract(geom: CorrectedGeometry) -> GeometryFinding:
    bad = []
    for fl in geom.floors:
        for c in fl.cells:
            try:
                if cell_has_polygon(c) and not schema_supports(geom, FEATURE_CELL_POLYGON):
                    raise ValueError(
                        f"cell {c.id}: polygon requires schema_version '2' or a schema version with feature '{FEATURE_CELL_POLYGON}'"
                    )
                validate_cell_polygon(c, min_edge_length_m=_MIN_EXTENT)
            except ValueError as exc:
                bad.append({"floor": fl.name, "cell": c.id, "reason": str(exc)})
    if bad:
        return GeometryFinding(
            "correction.cell_polygon_contract",
            False,
            f"{len(bad)} invalid polygon cell contract violation(s)",
            {"offenders": bad},
        )
    return GeometryFinding("correction.cell_polygon_contract", True)


def check_coverage(geom: CorrectedGeometry) -> list[GeometryFinding]:
    """Per floor: cells must tile the footprint — no holes, no overlaps."""
    findings: list[GeometryFinding] = []
    from shapely.geometry import Polygon
    for fl in geom.floors:
        try:
            foot = Polygon(floor_footprint(geom, fl))
            foot_area = foot.area
        except ValueError as exc:
            findings.append(GeometryFinding("correction.coverage", False, str(exc), {"floor": fl.name}))
            continue
        try:
            boxes = [_cell_box(c) for c in fl.cells]
        except ValueError as exc:
            findings.append(
                GeometryFinding(
                    "correction.coverage",
                    False,
                    f"floor '{fl.name}' has invalid cell geometry: {exc}",
                    {"floor": fl.name, "reason": str(exc)},
                )
            )
            continue
        if not boxes:
            findings.append(GeometryFinding(
                "correction.coverage", False,
                f"floor '{fl.name}' has no cells",
                {"floor": fl.name}))
            continue
        union = unary_union(boxes)
        covered = union.area
        sum_areas = sum(b.area for b in boxes)
        overlap_area = sum_areas - covered            # >0 ⇒ cells overlap
        hole_area = foot_area - union.intersection(foot).area  # uncovered footprint
        problems = {}
        if overlap_area > _AREA_TOL:
            problems["overlap_m2"] = round(overlap_area, 3)
        if hole_area > _AREA_TOL:
            problems["hole_m2"] = round(hole_area, 3)
        # cells outside footprint
        outside = union.difference(foot).area
        if outside > _AREA_TOL:
            problems["outside_footprint_m2"] = round(outside, 3)
        if problems:
            findings.append(GeometryFinding(
                "correction.coverage", False,
                f"floor '{fl.name}' cells do not tile the footprint cleanly",
                {"floor": fl.name, **problems}))
        else:
            findings.append(GeometryFinding(
                "correction.coverage", True, "",
                {"floor": fl.name, "covered_m2": round(covered, 3)}))
    return findings


def check_nondegenerate(geom: CorrectedGeometry) -> GeometryFinding:
    bad = []
    for fl in geom.floors:
        for c in fl.cells:
            try:
                minx, miny, maxx, maxy = cell_bbox(c)
            except ValueError:
                bad.append({"floor": fl.name, "cell": c.id})
                continue
            if abs(maxx - minx) < _MIN_EXTENT or abs(maxy - miny) < _MIN_EXTENT:
                bad.append({"floor": fl.name, "cell": c.id})
    if bad:
        return GeometryFinding(
            "correction.nondegenerate", False,
            f"{len(bad)} degenerate cell(s) (near-zero extent)", {"offenders": bad})
    return GeometryFinding("correction.nondegenerate", True)


def check_zstack(geom: CorrectedGeometry) -> GeometryFinding:
    floors = sorted(geom.floors, key=lambda f: float(f.z_floor))
    breaks = []
    for prev, cur in zip(floors, floors[1:]):
        top = float(prev.z_floor) + float(prev.ceiling_height)
        gap = float(cur.z_floor) - top
        if abs(gap) > _Z_TOL:
            breaks.append({"lower": prev.name, "upper": cur.name,
                           "gap_m": round(gap, 3)})
    if breaks:
        return GeometryFinding(
            "correction.zstack_continuity", False,
            f"{len(breaks)} z-stack discontinuity(ies)", {"breaks": breaks})
    return GeometryFinding("correction.zstack_continuity", True)


def check_zone_count(
    geom: CorrectedGeometry, expected_total: int | None
) -> GeometryFinding:
    """Tripwire: total cell count vs testdata thermal_zones (flag)."""
    total = sum(len(fl.cells) for fl in geom.floors)
    if expected_total is None:
        return GeometryFinding(
            "correction.zone_count_tripwire", True, "no expected count provided",
            {"actual": total, "expected": None})
    ok = total == expected_total
    return GeometryFinding(
        "correction.zone_count_tripwire", ok,
        "" if ok else f"cell count {total} != testdata thermal_zones {expected_total}",
        {"actual": total, "expected": expected_total,
         "per_floor": {fl.name: len(fl.cells) for fl in geom.floors}})


def check_windows_on_wall(geom: CorrectedGeometry) -> GeometryFinding:
    """Each window's along-facade span must fall within its room's extent on that
    facade (flag) — catches axis-flip placement and floating windows."""
    cells = {c.id: c for fl in geom.floors for c in fl.cells}
    bad = []
    for w in geom.windows:
        c = cells.get(w.room)
        if c is None:
            bad.append({"window": w.id, "reason": f"room '{w.room}' not found"})
            continue
        # along-facade axis: N/S → x, E/W → y
        try:
            rng = cell_facade_span(c, w.facade)
        except ValueError as exc:
            bad.append({"window": w.id, "reason": str(exc)})
            continue
        s0, s1 = min(w.span), max(w.span)
        if s0 < rng[0] - _SPAN_TOL or s1 > rng[1] + _SPAN_TOL:
            bad.append({"window": w.id, "facade": w.facade, "span": [s0, s1],
                        "room_range": list(rng)})
    if bad:
        return GeometryFinding(
            "correction.window_on_wall", False,
            f"{len(bad)} window(s) fall outside their room's facade extent",
            {"offenders": bad})
    return GeometryFinding("correction.window_on_wall", True,
                           evidence={"windows": len(geom.windows)})


def validate_corrected_geometry(
    geom: CorrectedGeometry, *, expected_zone_total: int | None = None
) -> list[GeometryFinding]:
    """Run all A0 §7 + cross-check geometry validations."""
    geom = ensure_corrected_geometry(geom)
    findings: list[GeometryFinding] = []
    findings.append(check_cell_polygon_contract(geom))
    findings.extend(check_coverage(geom))
    findings.append(check_nondegenerate(geom))
    findings.append(check_zstack(geom))
    findings.append(check_zone_count(geom, expected_zone_total))
    findings.append(check_windows_on_wall(geom))
    return findings
