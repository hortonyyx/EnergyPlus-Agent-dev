"""F-13 (2026-08-06): kernel-produced canonical vertex order.

Locks the fix in `AI_agent/logs/reviews/request/
2026-08-06_f13_kernel_canonical_vertex_order_dispatch_claude.md`: the
geometry kernel (`src.agent.geometry.build.build_geometry`) now produces
vertices already in IDF canonical form (outward winding, `UpperLeftCorner`
start), using the SAME shared function
(`src.validator.data_model.canonicalize_ring_vertices`) gate①'s
`GeometrySchema.validate_points_sorting` delegates to — so that validator
becomes an identity transform on real kernel output.

Three locks:
  1. Identity lock (§3.1 of the dispatch) — kernel output fed through the
     REAL production entry points (`SurfaceConverter.validate` /
     `FenestrationConverter.validate`) comes back byte-for-byte unchanged,
     per surface/window name, and the §2.3 change counter reads 0.
  2. Canonicalization-itself lock (§3.2) — for known shapes (vertical wall,
     horizontal floor, ceiling/roof, window), the shared function's output
     starts at the objectively correct top-left corner and winds outward.
  3. Change-counter lock (§3.3) — feeding a non-canonical vertex list
     through the validator increments the counter and logs the surface, and
     the validator still corrects it back to canonical form.
  4. Neuter (§3.4) — with the kernel-side canonicalization call disabled
     (monkeypatched to a no-op, simulating F-13 not having been done), lock
     1's invariant provably fails: real kernel output not entering the
     validator pre-canonicalized causes non-zero changes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.agent._share import IDD_PATH, ensure_schema_initialized
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import correction_target
from src.agent.geometry import build_geometry
from src.agent.geometry import build as build_module
from src.agent.geometry.modelling import BuildingGeometry, Surface, Window, _newell
from src.converters.fenestration_converter import FenestrationConverter
from src.converters.surface_converter import SurfaceConverter
from src.validator.data_model import (
    BaseSchema,
    GeometrySchema,
    canonicalize_ring_vertices,
    top_left_corner_index,
)


@pytest.fixture(autouse=True)
def _init_schema():
    ensure_schema_initialized()


@pytest.fixture()
def _idf():
    BaseSchema.set_idf(IDD_PATH)
    return BaseSchema.get_idf()


def _reset_geometry_schema_class_state() -> None:
    """`GeometrySchema` stashes several caches as class attributes (not
    per-instance) — `_interior_points`, `_surface_to_normal_vector`, and
    (new in F-13 §2.3) `_normalization_change_count`/`_log`. Reset all of
    them so this test's assertions aren't polluted by whatever ran before
    it in the same process (xdist runs each test file in its own worker,
    but within a file tests share the class)."""
    GeometrySchema._interior_points = np.array([])
    GeometrySchema._surface_to_normal_vector = {}
    GeometrySchema.reset_normalization_change_state()


# --------------------------------------------------------------------------- #
# shared fixture building
# --------------------------------------------------------------------------- #
def _build_bg(tmp_path: Path) -> BuildingGeometry:
    """One zone, 4 walls + floor + roof + 1 south window — small enough to
    eyeball, real enough to exercise the full kernel (`build_geometry`,
    unmodified call path used by every real run)."""
    payload = {
        "schema_version": "1",
        "footprint_x": [0.0, 4.0], "footprint_y": [0.0, 3.0],
        "floors": [{
            "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
            "cells": [{"id": "A", "x": [0.0, 4.0], "y": [0.0, 3.0]}],
        }],
        "windows": [{
            "id": "W1", "floor": "F1", "facade": "South",
            "span": [1.0, 2.0], "z": [1.0, 2.0], "room": "A",
        }],
    }
    result = finalize_correction_draw(
        payload,
        vector_dir=tmp_path,
        target=correction_target("rectangular"),
    )
    return build_geometry(result.geom, capability_profile="rectangular")


def _alias_surface_dict(s: Surface) -> dict:
    """Kernel `Surface` -> the IDD-alias dict `SurfaceConverter.validate`
    consumes in real production (this is the shape 4_mep's YAML surfaces
    take once assembled — see `src/converters/surface_converter.py`)."""
    return {
        "Name": s.name,
        "Surface Type": s.stype,
        "Construction Name": "Exterior Wall" if s.stype == "Wall" else "Interior Floor",
        "Zone Name": s.zone,
        "Outside Boundary Condition": s.obc,
        "Outside Boundary Condition Object": s.obc_obj or None,
        "Vertices": [{"X": v[0], "Y": v[1], "Z": v[2]} for v in s.verts],
    }


def _alias_window_dict(w: Window) -> dict:
    return {
        "Name": w.name,
        "Surface Type": "Window",
        "Construction Name": "Exterior Window",
        "Building Surface Name": w.parent,
        "Number of Vertices": len(w.verts),
        "Vertices": [{"X": v[0], "Y": v[1], "Z": v[2]} for v in w.verts],
    }


def _validate_through_real_entry_points(
    bg: BuildingGeometry, idf
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Feed `bg` through the two real production validate() entry points
    named in the dispatch (§3.1), in the same order `ConverterManager`
    calls them (surfaces before fenestrations — the fenestration pass
    reuses the surfaces pass's stashed interior-point cache). Returns
    {name: validated_vertices} for surfaces and windows."""
    zone_to_surfaces: dict[str, list[dict]] = {}
    for s in bg.surfaces:
        zone_to_surfaces.setdefault(s.zone, []).append(_alias_surface_dict(s))
    validated_surfaces = SurfaceConverter(idf).validate(zone_to_surfaces)
    surf_by_name = {s.name: s.vertices for s in validated_surfaces}

    win_by_name: dict[str, np.ndarray] = {}
    if bg.windows:
        fen_data = {
            "fenestrationsurfaces": [_alias_window_dict(w) for w in bg.windows]
        }
        validated = FenestrationConverter(idf).validate(fen_data)
        win_by_name = {f.name: f.vertices for f in validated.fenestrationsurfaces}
    return surf_by_name, win_by_name


# --------------------------------------------------------------------------- #
# Lock 1 — identity through the real entry points
# --------------------------------------------------------------------------- #
def test_lock1_kernel_output_is_already_canonical_through_real_entry_points(
    tmp_path: Path, _idf
):
    _reset_geometry_schema_class_state()
    bg = _build_bg(tmp_path)
    assert bg.surfaces, "fixture produced no surfaces"
    assert bg.windows, "fixture produced no windows"

    surf_by_name, win_by_name = _validate_through_real_entry_points(bg, _idf)

    for s in bg.surfaces:
        before = np.asarray(s.verts, dtype=float)
        after = surf_by_name[s.name]
        assert np.array_equal(before, after), (
            f"surface {s.name}: gate① changed the kernel's own vertex list "
            f"(before={before.tolist()!r} after={after.tolist()!r})"
        )
    for w in bg.windows:
        before = np.asarray(w.verts, dtype=float)
        after = win_by_name[w.name]
        assert np.array_equal(before, after), (
            f"window {w.name}: gate① changed the kernel's own vertex list "
            f"(before={before.tolist()!r} after={after.tolist()!r})"
        )

    assert GeometrySchema.normalization_change_count() == 0, (
        "§2.3 change counter must be 0 on real kernel output: "
        f"{GeometrySchema.normalization_change_log()!r}"
    )
    assert GeometrySchema.normalization_change_log() == []


# --------------------------------------------------------------------------- #
# Lock 2 — the canonicalization itself: known shapes, top-left + outward
# --------------------------------------------------------------------------- #
def test_lock2_canonicalization_vertical_wall_top_left_and_outward():
    # South-facing wall on the y=0 plane, outward normal (0, -1, 0), fed
    # in an arbitrary (not top-left-first) order.
    ordered_different_start = np.array([
        [1.0, 0.0, 1.0],
        [3.0, 0.0, 1.0],
        [3.0, 0.0, 2.0],
        [1.0, 0.0, 2.0],
    ])
    normal = np.array([0.0, -1.0, 0.0])
    canonical = canonicalize_ring_vertices(ordered_different_start, normal)
    # top-left = highest z, then smallest x, given right=(1,0,0)/up=(0,0,1)
    # for this normal (independently hand-derived in the F-13 execution log).
    assert np.array_equal(canonical[0], np.array([1.0, 0.0, 2.0]))
    assert top_left_corner_index(canonical, normal) == 0
    assert float(np.dot(_newell([tuple(p) for p in canonical]), normal)) > 0.99


def test_lock2_canonicalization_floor_top_left_and_outward():
    # Floor ring in the z=0 plane, outward normal (0, 0, -1) (faces down).
    #
    # Hand-derivation from `top_left_corner_index`'s own definition (NOT run
    # from the implementation and copied back — see the F-13 followup dispatch
    # 2026-08-07 §1, "手算值的来源纪律"):
    #   normal = (0, 0, -1). world_up starts as (0, 0, 1); |dot(normal,
    #   world_up)| = 1 > 0.99 and dot < 0, so the near-horizontal branch fires
    #   and swaps world_up to (0, -1, 0) — i.e. "up" is taken along -Y, not
    #   +Y, precisely because a floor's outward normal faces DOWN: standing
    #   outside the surface means standing BELOW it and looking UP, which
    #   mirrors the view left-right relative to the standard bird's-eye
    #   (ceiling/roof) convention below. This is the step orchestrator misread
    #   as "same as looking down from above" in the F-13 investigation.
    #   right = cross(world_up, normal) = cross((0,-1,0), (0,0,-1))
    #         = ((-1)*(-1) - 0*0, 0*0 - 0*(-1), 0*0 - (-1)*0) = (1, 0, 0)
    #   up    = cross(normal, right) = cross((0,0,-1), (1,0,0))
    #         = (0*0 - (-1)*0, (-1)*1 - 0*0, 0*0 - 0*1) = (0, -1, 0)
    #   So right = world +X, up = world -Y (viewed-from-below "up" points to
    #   world -Y). "Top" (max up-projection) = point with SMALLEST world Y;
    #   tie-break "left" (min right-projection) = point with SMALLEST world X.
    #   Ring points: (4,3,0) (4,0,0) (0,0,0) (0,3,0) — the two with Y=0 (the
    #   "top" group here, y=0 < y=3) are (4,0,0) and (0,0,0); smaller X of
    #   those is (0,0,0) ⇒ hand-derived top-left = (0.0, 0.0, 0.0).
    ordered_different_start = np.array([
        [4.0, 3.0, 0.0],
        [4.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [0.0, 3.0, 0.0],
    ])
    normal = np.array([0.0, 0.0, -1.0])
    canonical = canonicalize_ring_vertices(ordered_different_start, normal)
    assert np.array_equal(canonical[0], np.array([0.0, 0.0, 0.0]))
    assert top_left_corner_index(canonical, normal) == 0
    assert float(np.dot(_newell([tuple(p) for p in canonical]), normal)) > 0.99


def test_lock2_canonicalization_ceiling_top_left_and_outward():
    # Ceiling/Roof ring in the z=3 plane, outward normal (0, 0, 1) (faces up).
    #
    # Hand-derivation (same method as the floor case above, opposite branch):
    #   normal = (0, 0, 1). world_up starts as (0, 0, 1); |dot| = 1 > 0.99 and
    #   dot > 0 this time, so world_up swaps to (0, 1, 0) — a ceiling's
    #   outward normal faces UP, so standing outside means standing ABOVE it
    #   and looking DOWN: the standard bird's-eye-view convention (north/+Y
    #   is "up" in the view, matching ordinary plan-view drawings).
    #   right = cross(world_up, normal) = cross((0,1,0), (0,0,1))
    #         = (1*1 - 0*0, 0*0 - 0*1, 0*0 - 1*0) = (1, 0, 0)
    #   up    = cross(normal, right) = cross((0,0,1), (1,0,0))
    #         = (0*0 - 1*0, 1*1 - 0*0, 0*0 - 0*1) = (0, 1, 0)
    #   So right = world +X, up = world +Y — the ordinary plan-view sense.
    #   "Top" (max up-projection) = point with LARGEST world Y; tie-break
    #   "left" (min right-projection) = point with SMALLEST world X.
    #   Ring points: (0,0,3) (4,0,3) (4,3,3) (0,3,3) — the two with Y=3 (the
    #   "top" group) are (4,3,3) and (0,3,3); smaller X of those is (0,3,3)
    #   ⇒ hand-derived top-left = (0.0, 3.0, 3.0) — the north-west corner,
    #   consistent with "north up, west left" plan-view convention.
    ordered_different_start = np.array([
        [0.0, 0.0, 3.0],
        [4.0, 0.0, 3.0],
        [4.0, 3.0, 3.0],
        [0.0, 3.0, 3.0],
    ])
    normal = np.array([0.0, 0.0, 1.0])
    canonical = canonicalize_ring_vertices(ordered_different_start, normal)
    assert np.array_equal(canonical[0], np.array([0.0, 3.0, 3.0]))
    assert top_left_corner_index(canonical, normal) == 0
    assert float(np.dot(_newell([tuple(p) for p in canonical]), normal)) > 0.99


def test_lock2_canonicalization_window_top_left_and_outward():
    # South-facing window on the y=0 plane, outward normal (0, -1, 0) — same
    # normal, hence same right/up derivation, as the vertical-wall case above
    # (`test_lock2_canonicalization_vertical_wall_top_left_and_outward`):
    # right = world +X, up = world +Z. "Top" = max z, tie-break "left" = min
    # x. Ring points: (1,0,1) (2,0,1) (2,0,1.5) (1,0,1.5) — the two with
    # z=1.5 (the "top" group) are (2,0,1.5) and (1,0,1.5); smaller x of those
    # is (1,0,1.5) ⇒ hand-derived top-left = (1.0, 0.0, 1.5).
    ordered_different_start = np.array([
        [1.0, 0.0, 1.0],
        [2.0, 0.0, 1.0],
        [2.0, 0.0, 1.5],
        [1.0, 0.0, 1.5],
    ])
    normal = np.array([0.0, -1.0, 0.0])
    canonical = canonicalize_ring_vertices(ordered_different_start, normal)
    assert np.array_equal(canonical[0], np.array([1.0, 0.0, 1.5]))
    assert top_left_corner_index(canonical, normal) == 0
    assert float(np.dot(_newell([tuple(p) for p in canonical]), normal)) > 0.99


# --------------------------------------------------------------------------- #
# Lock 3 — change counter fires + still repairs a non-canonical input
# --------------------------------------------------------------------------- #
def test_lock3_change_counter_fires_and_repairs_noncanonical_input(tmp_path: Path, _idf):
    _reset_geometry_schema_class_state()
    bg = _build_bg(tmp_path)

    # Deliberately de-canonicalize exactly one wall's vertex list (roll its
    # start point by one) before handing it to the real validate() entry
    # point — everything else in the zone stays as the kernel produced it.
    target_name = next(s.name for s in bg.surfaces if s.stype == "Wall")
    zone_to_surfaces: dict[str, list[dict]] = {}
    expected_canonical: dict[str, np.ndarray] = {}
    for s in bg.surfaces:
        alias = _alias_surface_dict(s)
        expected_canonical[s.name] = np.asarray(s.verts, dtype=float)
        if s.name == target_name:
            rolled = np.roll(np.asarray(s.verts, dtype=float), 1, axis=0)
            assert not np.array_equal(rolled, expected_canonical[s.name])
            alias["Vertices"] = [{"X": v[0], "Y": v[1], "Z": v[2]} for v in rolled]
        zone_to_surfaces.setdefault(s.zone, []).append(alias)

    validated_surfaces = SurfaceConverter(_idf).validate(zone_to_surfaces)
    surf_by_name = {s.name: s.vertices for s in validated_surfaces}

    assert GeometrySchema.normalization_change_count() == 1, (
        f"expected exactly one recorded change, got "
        f"{GeometrySchema.normalization_change_log()!r}"
    )
    [entry] = GeometrySchema.normalization_change_log()
    assert entry["name"] == target_name
    assert entry["change"] == "start_vertex_rotated"

    # and the validator still repaired it back to the canonical form.
    assert np.array_equal(surf_by_name[target_name], expected_canonical[target_name])


def test_lock3_classify_helper_distinguishes_all_three_categories():
    before = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ])
    unchanged = before.copy()
    rotated = np.roll(before, -1, axis=0)
    reversed_and_rotated = np.roll(before[::-1], -1, axis=0)
    resorted = before[[0, 2, 1, 3]]  # not a rotation of before or its reverse

    classify = GeometrySchema._classify_normalization_change
    assert classify(before, unchanged) is None
    assert classify(before, rotated) == "start_vertex_rotated"
    assert classify(before, reversed_and_rotated) == "winding_reversed"
    assert classify(before, resorted) == "resorted"


# --------------------------------------------------------------------------- #
# Neuter — disable the kernel-side call, prove lock 1 breaks
# --------------------------------------------------------------------------- #
def test_neuter_disabling_kernel_canonicalization_breaks_lock1(
    tmp_path: Path, _idf, monkeypatch
):
    """Simulates the pre-fix defect: `build_geometry` no longer calls
    `_canonicalize_bg_vertices` (as if F-13 §2.2 had not been done). Proves
    lock 1's invariant is not vacuous — with the wiring cut, real kernel
    output disagrees with what gate① canonicalizes it to, and the §2.3
    counter goes non-zero."""
    monkeypatch.setattr(build_module, "_canonicalize_bg_vertices", lambda out: None)

    _reset_geometry_schema_class_state()
    bg = _build_bg(tmp_path)
    assert bg.surfaces and bg.windows

    surf_by_name, win_by_name = _validate_through_real_entry_points(bg, _idf)

    mismatches = [
        s.name
        for s in bg.surfaces
        if not np.array_equal(np.asarray(s.verts, dtype=float), surf_by_name[s.name])
    ]
    assert mismatches, (
        "neuter did not reproduce the defect: with kernel-side "
        "canonicalization disabled, gate① should have rewritten at least "
        "one surface's start vertex, but none differed"
    )
    assert GeometrySchema.normalization_change_count() > 0, (
        "neuter did not reproduce the defect: §2.3 counter should be > 0 "
        "with kernel-side canonicalization disabled"
    )
