"""Unit tests for the deterministic InterZone surface-pair gate.

Mock-based (no IDF fixture / no EnergyPlus): each test builds a tiny fake IDF
exposing just what `src.validator.interzone` reads — `idfobjects[...]` and, per
surface, `.Name / .Outside_Boundary_Condition / .Outside_Boundary_Condition_Object
/ .Surface_Type / .area / .coords`. Covers the failure classes the gate owns,
including the vertical-wall coplanarity case (review finding #1).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.validator.interzone import (
    audit_interzone_surface_pairs,
    validate_interzone_surface_pairs,
)


@dataclass
class FakeSurface:
    Name: str
    Surface_Type: str
    Outside_Boundary_Condition: str
    Outside_Boundary_Condition_Object: str
    coords: list[tuple[float, float, float]]

    @property
    def area(self) -> float:
        # Newell area for a planar polygon.
        pts = np.asarray(self.coords, dtype=float)
        n = np.zeros(3)
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            n += np.cross(a, b)
        return float(np.linalg.norm(n) / 2.0)


@dataclass
class FakeIDF:
    surfaces: list[FakeSurface] = field(default_factory=list)

    @property
    def idfobjects(self) -> dict[str, list[FakeSurface]]:
        return {"BUILDINGSURFACE:DETAILED": self.surfaces}


# A wall on the plane x=const (y-z plane). `reverse` flips the winding so a
# reciprocal partner gets the opposite normal (as real InterZone pairs do).
def _wall(
    name: str, partner: str, x: float, *, reverse: bool = False
) -> FakeSurface:
    coords = [(x, 0.0, 0.0), (x, 0.0, 3.0), (x, 4.0, 3.0), (x, 4.0, 0.0)]
    if reverse:
        coords = list(reversed(coords))
    return FakeSurface(name, "Wall", "Surface", partner, coords)


def _clean_wall_pair(x_a: float = 0.0, x_b: float = 0.0) -> list[FakeSurface]:
    return [_wall("A", "B", x_a), _wall("B", "A", x_b, reverse=True)]


def _clean_floor_ceiling_pair(z_floor: float = 3.0, z_ceil: float = 3.0):
    floor = FakeSurface(
        "F2_Floor", "Floor", "Surface", "F1_Ceiling",
        [(0, 0, z_floor), (4, 0, z_floor), (4, 4, z_floor), (0, 4, z_floor)],
    )
    ceil = FakeSurface(
        "F1_Ceiling", "Ceiling", "Surface", "F2_Floor",
        [(0, 0, z_ceil), (0, 4, z_ceil), (4, 4, z_ceil), (4, 0, z_ceil)],
    )
    return [floor, ceil]


def test_clean_wall_pair_passes():
    assert validate_interzone_surface_pairs(FakeIDF(_clean_wall_pair())) == []


def test_clean_floor_ceiling_pair_passes():
    assert validate_interzone_surface_pairs(FakeIDF(_clean_floor_ceiling_pair())) == []


def test_missing_target():
    s = _wall("A", "ghost", 0.0)
    issues = validate_interzone_surface_pairs(FakeIDF([s]))
    assert any("missing surface" in i for i in issues)


def test_target_not_surface():
    a = _wall("A", "B", 0.0)
    b = _wall("B", "A", 0.0)
    b.Outside_Boundary_Condition = "Outdoors"
    issues = validate_interzone_surface_pairs(FakeIDF([a, b]))
    assert any("must be 'Surface'" in i for i in issues)


def test_non_reciprocal():
    a = _wall("A", "B", 0.0)
    b = _wall("B", "C", 0.0)  # B points elsewhere
    c = _wall("C", "B", 0.0)
    issues = validate_interzone_surface_pairs(FakeIDF([a, b, c]))
    assert any("not reciprocal" in i for i in issues)


def test_duplicate_incoming_target():
    a = _wall("A", "C", 0.0)
    b = _wall("B", "C", 0.0)
    c = _wall("C", "A", 0.0)
    issues = validate_interzone_surface_pairs(FakeIDF([a, b, c]))
    assert any("targeted by" in i for i in issues)


def test_area_mismatch():
    a = _wall("A", "B", 0.0)
    b = FakeSurface(
        "B", "Wall", "Surface", "A",
        [(0, 0, 0), (0, 0, 3), (0, 2, 3), (0, 2, 0)],  # half width -> half area
    )
    issues = validate_interzone_surface_pairs(FakeIDF([a, b]))
    assert any("area mismatch" in i for i in issues)


def test_same_direction_normals():
    # Both wound the same way -> normals parallel, not opposite.
    a = _wall("A", "B", 0.0)
    b = FakeSurface(
        "B", "Wall", "Surface", "A",
        [(0, 0, 0), (0, 0, 3), (0, 4, 3), (0, 4, 0)],  # identical winding to A
    )
    issues = validate_interzone_surface_pairs(FakeIDF([a, b]))
    assert any("normals not opposite" in i for i in issues)


def test_vertical_wall_plane_offset():
    # Review finding #1: reciprocal, equal-area, opposite-normal walls offset
    # 0.05 m along their normal must be caught as non-coplanar.
    issues = validate_interzone_surface_pairs(FakeIDF(_clean_wall_pair(0.0, 0.05)))
    assert any("not coplanar" in i for i in issues), issues


def test_horizontal_z_mismatch():
    issues = validate_interzone_surface_pairs(
        FakeIDF(_clean_floor_ceiling_pair(3.0, 3.1))
    )
    assert any("not coplanar" in i for i in issues), issues


def test_min_edge_sliver():
    sliver = FakeSurface(
        "Sliver", "Floor", "Surface", "Partner",
        [(0, 0, 3), (0.05, 0, 3), (0.05, 4, 3), (0, 4, 3)],  # 0.05 m short edge
    )
    partner = FakeSurface(
        "Partner", "Ceiling", "Surface", "Sliver",
        [(0, 0, 3), (0, 4, 3), (0.05, 4, 3), (0.05, 0, 3)],
    )
    issues = validate_interzone_surface_pairs(FakeIDF([sliver, partner]))
    assert any("degenerate surface" in i for i in issues)


def test_audit_counts_only_mutual_pairs():
    # One clean mutual pair + one broken (non-reciprocal) reference.
    a = _wall("A", "B", 0.0)
    b = _wall("B", "A", 0.0)
    x = _wall("X", "ghost", 0.0)
    audit = audit_interzone_surface_pairs(FakeIDF([a, b, x]))
    assert audit["reciprocal_interzone_pairs"] == 1  # not 3//2 = 1 by luck; X excluded
    assert audit["obc_surface"] == 3
    assert audit["pair_issues"] >= 1
