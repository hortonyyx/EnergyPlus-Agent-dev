"""CW-winding canonicalization + draw-level polygon guards (2026-07-08).

First real-case exercise of B1 (sm24 L-corridor via DeepSeek) crashed the flow:
the LLM emitted a CW ring and the core's validate raised out of the draw.
Contract fixed here:
  - winding is encoding, not geometry → the deterministic core canonicalizes
    CW→CCW (start vertex preserved) and logs a POLYGON_WINDING_CCW correction;
  - every other polygon crime an LLM can commit must surface as a
    correction_draw_issues entry (blind resample), never a core raise.
"""

from __future__ import annotations

import pytest

from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.correction.cell_geometry import normalized_ccw_polygon
from src.agent.pipeline import correction_draw_issues

CCW_L_RING = [
    [0.0, 0.0],
    [10.0, 0.0],
    [10.0, 6.0],
    [6.0, 6.0],
    [6.0, 10.0],
    [0.0, 10.0],
]
CW_L_RING = [CCW_L_RING[0]] + CCW_L_RING[1:][::-1]


def _geom(polygon: list[list[float]] | None, schema_version: str = "2") -> CorrectedGeometry:
    cell: dict = {
        "id": "L_corridor",
        "role": "corridor",
        "x": [0.0, 10.0],
        "y": [0.0, 10.0],
    }
    if polygon is not None:
        cell["polygon"] = polygon
    return CorrectedGeometry.model_validate(
        {
            "schema_version": schema_version,
            "footprint_x": [0.0, 10.0],
            "footprint_y": [0.0, 10.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [cell],
                }
            ],
            "windows": [],
        }
    )


def test_normalized_ccw_polygon_rewrites_cw_and_preserves_start():
    geom = _geom(CW_L_RING)
    out = normalized_ccw_polygon(geom.floors[0].cells[0])
    assert out == CCW_L_RING


def test_normalized_ccw_polygon_noop_on_ccw_and_rect():
    assert normalized_ccw_polygon(_geom(CCW_L_RING).floors[0].cells[0]) is None
    assert normalized_ccw_polygon(_geom(None).floors[0].cells[0]) is None


def test_core_canonicalizes_cw_ring_and_logs_correction():
    geom = apply_deterministic_core(
        _geom(CW_L_RING), capability_profile="orthogonal_polygon"
    )
    assert geom.floors[0].cells[0].polygon == CCW_L_RING
    assert any(c.get("rule_id") == "POLYGON_WINDING_CCW" for c in geom.corrections)


def test_core_ccw_ring_logs_no_winding_correction():
    geom = apply_deterministic_core(
        _geom(CCW_L_RING), capability_profile="orthogonal_polygon"
    )
    assert not any(c.get("rule_id") == "POLYGON_WINDING_CCW" for c in geom.corrections)


def test_draw_issues_accept_cw_ring():
    assert correction_draw_issues(_geom(CW_L_RING), 0) == []


@pytest.mark.parametrize(
    "bad_polygon, needle",
    [
        # self-intersecting bowtie
        ([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]], "invalid cell polygon"),
        # non-orthogonal edge
        ([[0.0, 0.0], [10.0, 0.0], [10.0, 6.0], [0.0, 10.0]], "invalid cell polygon"),
        # bbox mismatch (x/y say [0,10] but ring only spans [0,5])
        ([[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0]], "invalid cell polygon"),
    ],
)
def test_draw_issues_flag_polygon_crimes_instead_of_raising(bad_polygon, needle):
    issues = correction_draw_issues(_geom(bad_polygon), 0)
    assert issues, "expected a draw issue for a bad polygon"
    assert any(needle in msg for msg in issues)


def test_draw_issues_flag_polygon_on_v1_schema():
    geom = _geom(CCW_L_RING, schema_version="1")
    issues = correction_draw_issues(geom, 0)
    assert any("schema_version" in msg for msg in issues)


CLOSED_CCW_RING = CCW_L_RING + [CCW_L_RING[0]]


def test_normalized_polygon_strips_explicit_closure():
    out = normalized_ccw_polygon(_geom(CLOSED_CCW_RING).floors[0].cells[0])
    assert out == CCW_L_RING


def test_core_canonicalizes_closed_ring():
    geom = apply_deterministic_core(
        _geom(CLOSED_CCW_RING), capability_profile="orthogonal_polygon"
    )
    assert geom.floors[0].cells[0].polygon == CCW_L_RING
    assert any(c.get("rule_id") == "POLYGON_WINDING_CCW" for c in geom.corrections)


def test_draw_issues_accept_closed_ring():
    assert correction_draw_issues(_geom(CLOSED_CCW_RING), 0) == []
