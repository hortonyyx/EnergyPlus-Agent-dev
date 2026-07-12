"""C2 B3 — coverage gate v2 area-conservation regressions."""
from __future__ import annotations

from src.agent.correction.geometry_validator import check_coverage
from src.agent.correction.parse import ensure_corrected_geometry


def _legacy(cells: list[dict], *, fx: tuple[float, float] = (0, 10), fy: tuple[float, float] = (0, 8)):
    return ensure_corrected_geometry(
        {
            "footprint_x": list(fx),
            "footprint_y": list(fy),
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0,
                    "ceiling_height": 3,
                    "cells": cells,
                }
            ],
        }
    )


def _v3(ring: list[list[float]], cells: list[dict]):
    return ensure_corrected_geometry(
        {
            "schema_version": "3",
            # B2 derives these projections from Floor.footprint in finalization;
            # B3 must nevertheless obtain the actual ring through floor_footprint.
            "footprint_x": [0, 10],
            "footprint_y": [0, 8],
            "floors": [
                {
                    "id": "f1",
                    "name": "F1",
                    "z_floor": 0,
                    "ceiling_height": 3,
                    "footprint": {"vertices": ring},
                    "cells": cells,
                }
            ],
        }
    )


def test_v1_legacy_bbox_ring_area_conservation_passes():
    findings = check_coverage(
        _legacy(
            [
                {"id": "west", "x": [0, 4], "y": [0, 8]},
                {"id": "east", "x": [4, 10], "y": [0, 8]},
            ]
        )
    )

    assert len(findings) == 1 and findings[0].ok
    assert findings[0].evidence == {
        "floor": "F1",
        "coverage_gate_version": "v2",
        "footprint_source": "floor_footprint",
        "footprint_area_m2": 80.0,
        "cells_union_area_m2": 80.0,
        "area_delta_m2": 0.0,
        "coverage_area_tol_m2": 0.05,
        "overlap_m2": 0.0,
        "hole_m2": 0.0,
        "outside_footprint_m2": 0.0,
    }


def test_area_delta_over_named_tolerance_blocks():
    findings = check_coverage(
        _legacy([{"id": "short", "x": [0, 10], "y": [0, 7.9]}])
    )

    assert not findings[0].ok
    assert findings[0].check_id == "correction.coverage"
    assert findings[0].evidence["area_delta_m2"] == 1.0
    assert findings[0].evidence["coverage_area_tol_m2"] == 0.05


def test_overlapping_cells_block_even_when_union_area_is_conserved():
    findings = check_coverage(
        _legacy(
            [
                {"id": "west", "x": [0, 6], "y": [0, 8]},
                {"id": "east", "x": [4, 10], "y": [0, 8]},
            ]
        )
    )

    assert not findings[0].ok
    assert findings[0].evidence["area_delta_m2"] == 0.0
    assert findings[0].evidence["overlap_m2"] == 16.0


def test_v3_nonrectangular_footprint_uses_ring_area_for_pass_and_fail():
    ring = [[0, 0], [10, 0], [10, 3], [4, 3], [4, 8], [0, 8]]
    tiled = [
        {"id": "south", "x": [0, 10], "y": [0, 3]},
        {"id": "north_west", "x": [0, 4], "y": [3, 8]},
    ]
    passed = check_coverage(_v3(ring, tiled))
    failed = check_coverage(_v3(ring, [{"id": "bbox", "x": [0, 10], "y": [0, 8]}]))

    assert passed[0].ok
    assert passed[0].evidence["footprint_area_m2"] == 50.0
    assert passed[0].evidence["cells_union_area_m2"] == 50.0
    assert not failed[0].ok
    assert failed[0].evidence["footprint_area_m2"] == 50.0
    assert failed[0].evidence["cells_union_area_m2"] == 80.0
    assert failed[0].evidence["outside_footprint_m2"] == 30.0


def test_v3_self_intersecting_footprint_blocks_on_invalid_footprint():
    # Bow-tie ring: (0,0)->(10,8)->(10,0)->(0,8) crosses itself, so the
    # Polygon is geometrically invalid (Shapely reports is_valid=False,
    # area=0.0) even though it satisfies the schema's min_length=4 vertices.
    bowtie_ring = [[0, 0], [10, 8], [10, 0], [0, 8]]
    findings = check_coverage(
        _v3(bowtie_ring, [{"id": "whatever", "x": [0, 10], "y": [0, 8]}])
    )

    assert len(findings) == 1
    assert not findings[0].ok
    assert findings[0].check_id == "correction.coverage"
    assert "footprint" in findings[0].message
    assert "invalid" in findings[0].message


def test_hole_area_exactly_at_tolerance_passes_strictly_above_blocks():
    # width=1 keeps the area arithmetic exact in double precision, so the
    # hole area lands bit-exact on coverage_area_tol_m2 (0.05): footprint
    # 1 x 0.1 = 0.1 m^2, cell 1 x 0.05 = 0.05 m^2, hole = 0.05 m^2 == tol.
    at_tol = check_coverage(
        _legacy(
            [{"id": "c1", "x": [0, 1], "y": [0, 0.05]}],
            fx=(0, 1), fy=(0, 0.1),
        )
    )
    assert at_tol[0].ok
    assert at_tol[0].evidence["hole_m2"] == 0.05
    assert at_tol[0].evidence["coverage_area_tol_m2"] == 0.05

    # Shrink the cell a hair further (0.049 vs 0.05) so hole = 0.051 > tol.
    over_tol = check_coverage(
        _legacy(
            [{"id": "c1", "x": [0, 1], "y": [0, 0.049]}],
            fx=(0, 1), fy=(0, 0.1),
        )
    )
    assert not over_tol[0].ok
    assert over_tol[0].evidence["hole_m2"] == 0.051
    assert "coverage" in over_tol[0].message


def test_v3_l_shape_footprint_internal_hole_blocks_distinct_from_outside_path():
    # Same L-shape ring as the pass/fail test above, but instead of a cell
    # escaping the footprint (outside path), leave an internal gap that is
    # fully inside the L (hole path): north_west cell stops at y=7 instead
    # of y=8, leaving a 4 m^2 strip uncovered with zero outside area.
    ring = [[0, 0], [10, 0], [10, 3], [4, 3], [4, 8], [0, 8]]
    cells = [
        {"id": "south", "x": [0, 10], "y": [0, 3]},
        {"id": "north_west", "x": [0, 4], "y": [3, 7]},
    ]
    findings = check_coverage(_v3(ring, cells))

    assert not findings[0].ok
    assert findings[0].evidence["footprint_area_m2"] == 50.0
    assert findings[0].evidence["cells_union_area_m2"] == 46.0
    assert findings[0].evidence["hole_m2"] == 4.0
    assert findings[0].evidence["outside_footprint_m2"] == 0.0
