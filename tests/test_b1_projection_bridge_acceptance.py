"""B1 projection bridge — acceptance tests against the dispatch's §五 table.

Acceptances covered here:
  #1  cells do not overlap and their union IS the footprint (zero threshold)
  #2  rooms sharing an inner wall share it vertex-for-vertex
  #6  two-directional reconciliation against the SIGNED gt zones,
      per view (F1=14, F2=15 — the baseline pinned to the frozen gt.json,
      ⛔ never a judge-side reading)
plus gate① on the single-view product (acceptance #7's product half).

The five-fixture suite (§六) and the failure semantics (#4/#4b) live in
``test_b1_projection_bridge_fixtures.py``; the pipeline wiring lock rewrite
lives with the o22m7 tests.

gt iron rule: ``gt.json`` is read HERE (test side) only — the bridge never
imports it; the reconciliation helper is test tooling, not production code.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

from src.agent.correction.geometry_validator import validate_corrected_geometry
from src.agent.correction.projection_bridge import (
    cut_lines_from_as_measured_view,
    project_cut_lines,
)

from tests.b1_gt_reconciliation import (
    bound_from_baseline,
    load_gt_zones,
    reconcile_faces_vs_zones,
)

REPO = Path(__file__).resolve().parents[1]
FACTS = REPO / "case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json"
GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json"

#: the two views the dispatch pins (F1 once, F2 once — ⛔ no two-floor
#: assembly here, that is B2)
SM25_VIEWS = [("plan-F1", "F1", 14), ("plan-F2", "F2", 15)]


def _facts() -> dict:
    return json.loads(FACTS.read_text(encoding="utf-8"))


def _gt_floor_meta(floor_id: str) -> tuple[float, float]:
    """z_floor / ceiling_height FROM THE DATA (the bridge takes no z source
    of its own — B2's wiring; the fixture world's source is the signed gt)."""
    data = json.loads(GT.read_text(encoding="utf-8"))
    for floor in data["floors"]:
        if floor["id"] == floor_id:
            return float(floor["z_floor_m"]), float(floor["ceiling_height_m"])
    raise KeyError(floor_id)


def bridge_sm25(view_id: str, *, mutate=None):
    """Run the bridge on one real sm25 facts view (optionally mutated)."""
    import copy

    facts = _facts()
    view = next(v for v in facts["views"] if v["view_id"] == view_id)
    if mutate is not None:
        view = mutate(copy.deepcopy(view))
    lines, resolution = cut_lines_from_as_measured_view(
        view, units_per_metre=facts["units_per_metre"]
    )
    floor_id = view_id.removeprefix("plan-")
    z_floor, ceiling = _gt_floor_meta(floor_id)
    return project_cut_lines(
        lines,
        resolution_m=resolution,
        resolution_source=(
            "fixture world: gt facts units_per_metre="
            f"{facts['units_per_metre']} (N-3: production must redeclare)"
        ),
        source_resolved_sha256="0" * 64,
        floor_id=floor_id,
        floor_name=view_id,
        z_floor_m=z_floor,
        ceiling_height_m=ceiling,
        view_id=view_id,
        origin_label=view_id,
    )


def _cell_polygons(envelope) -> list[Polygon]:
    return [Polygon(c.polygon) for c in envelope.geometry.floors[0].cells]


# ── acceptance #6 (pinned baseline) ────────────────────────────────────────── #
@pytest.mark.parametrize("view_id,floor_id,expected", SM25_VIEWS)
def test_6_signed_gt_reconciliation_two_directional(view_id, floor_id, expected):
    """F1 14 / F2 15 against the SIGNED gt.json, both directions.

    ① counts equal · ② every zone one-to-one onto a face within the
    DERIVED bound · ③ every face owned — an ownerless face is red.
    The area difference is a READOUT (systematic midline-vs-skin bias),
    ⛔ it does not gate: this test asserts green WHILE the area delta is
    measurably non-zero, pinning that separation.
    """
    envelope = bridge_sm25(view_id)
    assert envelope.face_count == expected
    zones = load_gt_zones(GT, floor_id)
    assert len(zones) == expected  # the pinned gt baseline itself
    faces = [list(c.polygon) for c in envelope.geometry.floors[0].cells]

    baseline = reconcile_faces_vs_zones(faces, zones, bound_m=float("inf"))
    assert baseline.green, baseline.failures()
    bound = bound_from_baseline(baseline)
    report = reconcile_faces_vs_zones(faces, zones, bound_m=bound)
    assert report.green, report.failures()
    # area delta is real and non-zero (midline < skin systematically) —
    # and the report above is green anyway: readout, not gate.
    deltas = [abs(f - z) for f, z in (p.area_readout_m2 for p in report.pairs)]
    assert deltas and all(d > 0 for d in deltas)


# ── acceptance #1 (zero threshold) ─────────────────────────────────────────── #
@pytest.mark.parametrize("view_id,floor_id,expected", SM25_VIEWS)
def test_1_cells_tile_the_footprint_zero_threshold(view_id, floor_id, expected):
    """hole_area == 0 and overlap_area == 0 — ⛔ no coverage_area_tol_m2.

    The zero is asserted through BOOLEANS and exact pairwise-intersection
    areas, not through ``sum(areas) − union.area``: that subtraction is
    exactly where IEEE summation noise appears (measured −5.7e-14 on F1)
    while every geometric predicate here reads a clean, exact zero.  A
    tolerance on the subtraction would be a tolerance on float addition,
    not on geometry — the wrong thing to license.
    """
    envelope = bridge_sm25(view_id)
    cells = _cell_polygons(envelope)
    footprint = Polygon(
        envelope.geometry.floors[0].footprint.vertices
    )
    union = unary_union(cells)
    assert union.area > 0
    # overlap: pairwise intersections have exactly zero area
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            inter = cells[i].intersection(cells[j])
            assert inter.area == 0, (
                f"cells {i}/{j} overlap with area {inter.area}"
            )
    # holes: nothing of the footprint is left uncovered
    hole = footprint.difference(union)
    assert hole.is_empty and hole.area == 0
    # step ④ literally: the footprint IS the union of the bounded faces
    symdiff = footprint.symmetric_difference(union)
    assert symdiff.is_empty and symdiff.area == 0


# ── acceptance #2 (shared inner walls, vertex for vertex) ──────────────────── #
@pytest.mark.parametrize("view_id,floor_id,expected", SM25_VIEWS)
def test_2_rooms_share_inner_walls_vertex_for_vertex(view_id, floor_id, expected):
    """Any two rooms that touch along an inner wall share it VERTEX for
    VERTEX — asserted on the vertices (⛔ never a hash of the whole)."""
    envelope = bridge_sm25(view_id)
    cells = _cell_polygons(envelope)
    shared_found = 0
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            if not cells[i].touches(cells[j]):
                continue
            shared = cells[i].boundary.intersection(cells[j].boundary)
            if shared.is_empty or shared.length == 0:
                continue
            shared_found += 1
            lines = (
                list(shared.geoms)
                if shared.geom_type == "MultiLineString"
                else [shared]
            )
            ring_i = {
                (round(x, 9), round(y, 9))
                for x, y in cells[i].exterior.coords
            }
            ring_j = {
                (round(x, 9), round(y, 9))
                for x, y in cells[j].exterior.coords
            }
            for line in lines:
                for x, y in line.coords:
                    assert (round(x, 9), round(y, 9)) in ring_i
                    assert (round(x, 9), round(y, 9)) in ring_j
    assert shared_found > 0, "no adjacent rooms found — fixture degenerated"


# ── acceptance #7's product half: gate① on the single-view product ─────────── #
@pytest.mark.parametrize("view_id,floor_id,expected", SM25_VIEWS)
def test_7_gate1_green_on_single_view_product(view_id, floor_id, expected):
    envelope = bridge_sm25(view_id)
    findings = validate_corrected_geometry(envelope.geometry)
    bad = [f for f in findings if not f.ok]
    assert not bad, [(f.check_id, f.message) for f in bad]
    # B3 is true BY CONSTRUCTION on this chain — readable in the product
    assert envelope.footprint_provenance == "derived_from_walls"
    assert envelope.completion == "complete"
    assert envelope.dangling_end_debts == ()
