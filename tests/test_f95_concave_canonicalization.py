"""F-95: canonicalization must preserve an ordered concave ring's topology."""

from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon

from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry.build import build_geometry
from src.validator.data_model import canonicalize_ring_vertices


UP = np.array([0.0, 0.0, 1.0])
DOWN = np.array([0.0, 0.0, -1.0])
U_RING_2D = [
    [0.0, 0.0],
    [10.0, 0.0],
    [10.0, 10.0],
    [7.0, 10.0],
    [7.0, 4.0],
    [3.0, 4.0],
    [3.0, 10.0],
    [0.0, 10.0],
]


def _u_ring_3d(z: float = 0.0) -> np.ndarray:
    return np.asarray([[x, y, z] for x, y in U_RING_2D], dtype=float)


def _vertex_set(points: np.ndarray) -> set[tuple[float, float, float]]:
    return {tuple(float(value) for value in point) for point in points}


def _edge_set(
    points: np.ndarray,
) -> set[frozenset[tuple[float, float, float]]]:
    vertices = [tuple(float(value) for value in point) for point in points]
    return {
        frozenset((vertices[index], vertices[(index + 1) % len(vertices)]))
        for index in range(len(vertices))
    }


def _independent_ring_normal(points: np.ndarray) -> np.ndarray:
    """Independent Newell-equivalent direction used only by the contract lock."""
    return np.sum(np.cross(points, np.roll(points, -1, axis=0)), axis=0)


def test_discriminating_u_ring_preserves_area_vertices_and_edges():
    """The old centroid-angle sorter changes this U from area 76 to 70."""
    before = _u_ring_3d()

    after = canonicalize_ring_vertices(before, DOWN)

    assert Polygon(after[:, :2]).area == pytest.approx(Polygon(before[:, :2]).area)
    assert _vertex_set(after) == _vertex_set(before)
    assert _edge_set(after) == _edge_set(before)


def test_kernel_floor_and_roof_keep_discriminating_u_shape():
    """Production build path uses the same shared canonicalizer without loss."""
    geometry = CorrectedGeometry(
        schema_version="2",
        footprint_x=[0.0, 10.0],
        footprint_y=[0.0, 10.0],
        floors=[
            {
                "name": "F1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "cells": [
                    {
                        "id": "U",
                        "x": [0.0, 10.0],
                        "y": [0.0, 10.0],
                        "polygon": U_RING_2D,
                    }
                ],
            }
        ],
    )

    built = build_geometry(geometry, capability_profile="orthogonal_polygon")
    horizontal = [
        surface for surface in built.surfaces if surface.stype in {"Floor", "Roof"}
    ]

    assert {surface.stype for surface in horizontal} == {"Floor", "Roof"}
    expected_edges_2d = _edge_set(_u_ring_3d())
    for surface in horizontal:
        points = np.asarray(surface.verts, dtype=float)
        assert len(points) == len(U_RING_2D)
        assert Polygon(points[:, :2]).area == pytest.approx(76.0)
        projected_at_zero = points.copy()
        projected_at_zero[:, 2] = 0.0
        assert _edge_set(projected_at_zero) == expected_edges_2d


def test_non_simple_bowtie_is_rejected_with_named_context():
    bowtie = np.asarray(
        [[0.0, 0.0, 0.0], [2.0, 2.0, 0.0], [0.0, 2.0, 0.0], [2.0, 0.0, 0.0]]
    )

    with pytest.raises(
        ValueError,
        match=r"canonicalize_ring_vertices\.non_simple_ring:.*vertex_count=4.*Self-intersection",
    ):
        canonicalize_ring_vertices(bowtie, UP)


def test_winding_contract_is_independently_observable_on_concave_ring():
    # U_RING_2D is +Z-wound, so requesting DOWN forces a complete reversal.
    canonical = canonicalize_ring_vertices(_u_ring_3d(), DOWN)

    assert float(np.dot(_independent_ring_normal(canonical), DOWN)) > 0.0


def test_upper_left_contract_is_independently_observable_on_concave_ring():
    # For an upward horizontal surface, view-up is world +Y and view-right is
    # world +X, so the hand-derived top-left U vertex is (0, 10, 0).
    different_start = np.roll(_u_ring_3d(), 3, axis=0)

    canonical = canonicalize_ring_vertices(different_start, UP)

    assert np.array_equal(canonical[0], np.array([0.0, 10.0, 0.0]))


def test_winding_and_start_variants_converge_without_changing_edges():
    base = _u_ring_3d()
    variants = [base, base[::-1], np.roll(base, 3, axis=0)]

    canonical = [canonicalize_ring_vertices(variant, DOWN) for variant in variants]

    assert all(np.array_equal(result, canonical[0]) for result in canonical[1:])
    assert all(_edge_set(result) == _edge_set(base) for result in canonical)
