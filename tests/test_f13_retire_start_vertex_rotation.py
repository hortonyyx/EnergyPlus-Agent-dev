"""F-13 locks: `_sort_vertices_clockwise` (src/validator/data_model.py) must
stop re-picking each surface's start vertex. It still guarantees outward
winding — reversing when the input's own winding disagrees with the
independently-judged outward normal — but must do so WITHOUT moving the
start vertex ([A, B, C, D] -> [A, D, C, B], never [D, C, B, A]), and must
count + log every REAL reversal.

Background:
AI_agent/logs/reviews/request/2026-08-06_f13_retire_start_vertex_rotation_dispatch_claude.md
+ AI_agent/logs/reviews/execution/2026-08-06_f13_two_vertex_order_conventions_claude.md
(F-13 investigation: the old algorithm re-sorted + re-rolled EVERY real
surface's start point, which is why the B-layer VERTEX_FRAME_DRIFT gate
flagged 104/115 faces as drifted — 100% pure rotation, 0 coordinate errors,
0 winding reversals — even though the deterministic kernel's own vertex
order was never actually wrong; only the sorter's post-processing moved it).

These tests exercise the REAL production entry points
(`SurfaceConverter.validate` / `FenestrationConverter.validate`), not the
private sort method directly — matching the F-13 investigation's decisive
experiment (§2 of the execution log) — so they fail if the fix is undone
anywhere in the real call chain, not just in isolation.

Orchestrator addendum (2026-08-06, same day): the retired algorithm
actually did THREE things, not two — (1) guarantee outward winding
[kept], (2) re-pick the start vertex [retired, see above], and (3)
silently repair vertex orders that weren't a simple loop around their own
centroid (self-intersecting "bowtie" orderings, or points too far from
planar to trust a normal) by re-sorting them into angular order. (3) is
ALSO gone now that re-sorting is retired, and is diagnosed (counted +
logged, never repaired/raised) the same way as the winding counter — see
the `test_*disordered_loop*` tests below.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.agent._share import ensure_schema_initialized
from src.converters.fenestration_converter import FenestrationConverter
from src.converters.surface_converter import SurfaceConverter
from src.validator.data_model import BaseSchema, GeometrySchema

Point = tuple[float, float, float]


@pytest.fixture(autouse=True)
def _reset_geometry_schema_state():
    """GeometrySchema keeps process-wide class-level caches
    (_interior_points, _surface_to_normal_vector) plus the F-13
    winding-reversal counter/log. Reset all of them before AND after each
    test so these tests are order-independent (both within this file and
    relative to other test files sharing the pytest-xdist worker process)."""
    ensure_schema_initialized()
    GeometrySchema._interior_points = np.array([])
    GeometrySchema._surface_to_normal_vector = {}
    GeometrySchema.reset_winding_reversal_state()
    GeometrySchema.reset_disordered_loop_state()
    yield
    GeometrySchema._interior_points = np.array([])
    GeometrySchema._surface_to_normal_vector = {}
    GeometrySchema.reset_winding_reversal_state()
    GeometrySchema.reset_disordered_loop_state()


def _idf():
    return BaseSchema._idf


def _floor(name: str, zone: str, verts: list[Point]) -> dict:
    return {
        "Name": name, "Surface Type": "Floor", "Construction Name": "C",
        "Zone Name": zone, "Outside Boundary Condition": "Ground",
        "Sun Exposure": "NoSun", "Wind Exposure": "NoWind",
        "Vertices": [{"X": x, "Y": y, "Z": z} for x, y, z in verts],
    }


def _wall(name: str, zone: str, verts: list[Point]) -> dict:
    return {
        "Name": name, "Surface Type": "Wall", "Construction Name": "C",
        "Zone Name": zone, "Outside Boundary Condition": "Outdoors",
        "Sun Exposure": "SunExposed", "Wind Exposure": "WindExposed",
        "Vertices": [{"X": x, "Y": y, "Z": z} for x, y, z in verts],
    }


def _window(name: str, host: str, verts: list[Point]) -> dict:
    return {
        "Name": name, "Surface Type": "Window", "Construction Name": "C",
        "Building Surface Name": host, "Number of Vertices": len(verts),
        "Vertices": [{"X": x, "Y": y, "Z": z} for x, y, z in verts],
    }


def _as_lists(verts: list[Point]) -> list[list[float]]:
    return [list(p) for p in verts]


# ---------------------------------------------------------------------------
# Lock 1 — identity through the real production entry point
# ---------------------------------------------------------------------------

# A physically valid box-zone footprint/wall/window whose vertex order is
# ALREADY outward-facing but deliberately does NOT start at the "top-left
# corner" the retired algorithm used to pick — if start-vertex rotation ever
# comes back, this identity assertion is what catches it.
_COMPLIANT_FLOOR: list[Point] = [
    (0.0, 0.0, 0.0), (0.0, 3.0, 0.0), (4.0, 3.0, 0.0), (4.0, 0.0, 0.0),
]
_COMPLIANT_WALL: list[Point] = [
    (0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (4.0, 0.0, 3.0), (0.0, 0.0, 3.0),
]
_COMPLIANT_WINDOW: list[Point] = [
    (1.0, 0.0, 1.0), (2.5, 0.0, 1.0), (2.5, 0.0, 2.0), (1.0, 0.0, 2.0),
]


def test_already_outward_vertices_pass_through_the_real_converters_unchanged():
    """F-13 dispatch §2.1 behavior 1 ("output must have the same start
    vertex as input"): vertices whose winding is already outward must come
    out byte-identical, in the SAME order, starting at the SAME vertex — no
    re-sort, no re-roll to a 'nicer' starting corner. Verified through the
    real SurfaceConverter and FenestrationConverter entry points, asserted
    on named faces + exact vertex tuples — this is the mirror image of the
    F-13 investigation's §2 decisive experiment, where feeding the kernel's
    frozen (already-outward) vertices through this same real path rewrote
    104/115 faces."""
    zone_to_surfaces = {
        "ZL1": [
            _floor("ZL1_Floor", "ZL1", _COMPLIANT_FLOOR),
            _wall("ZL1_Wall_S", "ZL1", _COMPLIANT_WALL),
        ]
    }
    out = SurfaceConverter(_idf()).validate(zone_to_surfaces)
    by_name = {s.name: s for s in out}
    assert by_name["ZL1_Floor"].vertices.tolist() == _as_lists(_COMPLIANT_FLOOR)
    assert by_name["ZL1_Wall_S"].vertices.tolist() == _as_lists(_COMPLIANT_WALL)

    fen_out = FenestrationConverter(_idf()).validate({
        "fenestrationsurfaces": [
            _window("ZL1_Wall_S_Win1", "ZL1_Wall_S", _COMPLIANT_WINDOW),
        ],
    })
    assert fen_out.fenestrationsurfaces[0].vertices.tolist() == _as_lists(
        _COMPLIANT_WINDOW
    )

    # Nothing here disagreed with the outward normal: zero real reversals.
    assert GeometrySchema.winding_reversal_count() == 0
    assert GeometrySchema.winding_reversal_log() == []
    # ...and every fixture here IS a simple loop: zero disorder flags too.
    assert GeometrySchema.disordered_loop_count() == 0
    assert GeometrySchema.disordered_loop_log() == []


# ---------------------------------------------------------------------------
# Lock 2 — winding still corrected, start vertex preserved
# ---------------------------------------------------------------------------

# Same physical wall/window as above, winding reversed (a genuinely
# different, wrong-handed loop over the same 4 points, NOT a relabeling).
_REVERSED_WALL: list[Point] = [
    (0.0, 0.0, 3.0), (4.0, 0.0, 3.0), (4.0, 0.0, 0.0), (0.0, 0.0, 0.0),
]
_REVERSED_WINDOW: list[Point] = [
    (1.0, 0.0, 2.0), (2.5, 0.0, 2.0), (2.5, 0.0, 1.0), (1.0, 0.0, 1.0),
]


def test_reversed_winding_wall_is_flipped_in_place_start_vertex_kept():
    """F-13 dispatch §2.1 behavior 2: a wall whose input winding disagrees
    with the independently-judged outward normal must still be corrected —
    but by [A, B, C, D] -> [A, D, C, B] (start vertex A kept), never
    [D, C, B, A] (start vertex moved — the retired algorithm's behavior)."""
    zone_to_surfaces = {
        "ZL2": [
            _floor("ZL2_Floor", "ZL2", _COMPLIANT_FLOOR),
            _wall("ZL2_Wall_S", "ZL2", _REVERSED_WALL),
        ]
    }
    out = SurfaceConverter(_idf()).validate(zone_to_surfaces)
    got = {s.name: s for s in out}["ZL2_Wall_S"].vertices.tolist()

    a, b, c, d = _REVERSED_WALL
    expected_start_preserved = _as_lists([a, d, c, b])
    expected_full_reverse_forbidden = _as_lists([d, c, b, a])

    assert got == expected_start_preserved
    assert got != expected_full_reverse_forbidden
    assert got[0] == list(a)  # the literal start vertex is untouched

    assert GeometrySchema.winding_reversal_count() == 1
    assert GeometrySchema.winding_reversal_log() == [
        {"name": "ZL2_Wall_S", "surface_type": "Wall", "zone": "ZL2"}
    ]


def test_reversed_winding_window_is_flipped_in_place_start_vertex_kept():
    """Same behavior, through FenestrationConverter.validate — the F-13
    dispatch names both converters explicitly as the real production entry
    points that must be exercised."""
    zone_to_surfaces = {
        "ZL3": [
            _floor("ZL3_Floor", "ZL3", _COMPLIANT_FLOOR),
            _wall("ZL3_Wall_S", "ZL3", _COMPLIANT_WALL),
        ]
    }
    SurfaceConverter(_idf()).validate(zone_to_surfaces)  # establishes ZL3's interior_points
    GeometrySchema.reset_winding_reversal_state()  # isolate the count to the window below

    fen_out = FenestrationConverter(_idf()).validate({
        "fenestrationsurfaces": [
            _window("ZL3_Wall_S_Win2", "ZL3_Wall_S", _REVERSED_WINDOW),
        ],
    })
    got = fen_out.fenestrationsurfaces[0].vertices.tolist()

    a, b, c, d = _REVERSED_WINDOW
    expected_start_preserved = _as_lists([a, d, c, b])
    expected_full_reverse_forbidden = _as_lists([d, c, b, a])

    assert got == expected_start_preserved
    assert got != expected_full_reverse_forbidden
    assert got[0] == list(a)

    assert GeometrySchema.winding_reversal_count() == 1
    assert GeometrySchema.winding_reversal_log() == [
        {"name": "ZL3_Wall_S_Win2", "surface_type": "Window", "zone": "ZL3_Wall_S"}
    ]


# ---------------------------------------------------------------------------
# Lock 3 — counting is real (accumulates across faces, doesn't over/under count)
# ---------------------------------------------------------------------------

def test_winding_reversal_count_accumulates_only_for_real_reversals():
    """One compliant wall (0 reversals) + one reversed wall (1) in a single
    SurfaceConverter.validate call, then one compliant window (0) + one
    reversed window (1) in a single FenestrationConverter.validate call:
    the running counter must land at exactly 2, with a log entry naming
    each reversed face and none for the compliant ones — not '>0', not
    'not None'. This is the number the F-13 dispatch says orchestrator
    wants as real evidence before deciding whether to escalate reversals
    into a hard failure."""
    zone_to_surfaces = {
        "ZL4": [
            _floor("ZL4_Floor", "ZL4", _COMPLIANT_FLOOR),
            _wall("ZL4_Wall_Compliant", "ZL4", _COMPLIANT_WALL),
            _wall("ZL4_Wall_Reversed", "ZL4", _REVERSED_WALL),
        ]
    }
    SurfaceConverter(_idf()).validate(zone_to_surfaces)
    assert GeometrySchema.winding_reversal_count() == 1
    assert [e["name"] for e in GeometrySchema.winding_reversal_log()] == [
        "ZL4_Wall_Reversed"
    ]

    FenestrationConverter(_idf()).validate({
        "fenestrationsurfaces": [
            _window("ZL4_Win_Compliant", "ZL4_Wall_Compliant", _COMPLIANT_WINDOW),
            _window("ZL4_Win_Reversed", "ZL4_Wall_Compliant", _REVERSED_WINDOW),
        ],
    })
    assert GeometrySchema.winding_reversal_count() == 2
    assert [e["name"] for e in GeometrySchema.winding_reversal_log()] == [
        "ZL4_Wall_Reversed", "ZL4_Win_Reversed",
    ]
    # every log entry carries face identity (name / type / zone-or-host),
    # not just a bare count
    reversed_wall_entry, reversed_window_entry = GeometrySchema.winding_reversal_log()
    assert reversed_wall_entry == {
        "name": "ZL4_Wall_Reversed", "surface_type": "Wall", "zone": "ZL4",
    }
    assert reversed_window_entry == {
        "name": "ZL4_Win_Reversed", "surface_type": "Window",
        "zone": "ZL4_Wall_Compliant",
    }


# ---------------------------------------------------------------------------
# Lock 4 (orchestrator addendum) — disordered-loop detector: diagnose only,
# never repairs, never raises
# ---------------------------------------------------------------------------

# A quadrilateral whose points, in THIS order, are not a simple loop around
# their own centroid — a self-intersecting ("bowtie") vertex order. Chosen
# to have a non-degenerate Newell normal (not just collinear/zero-area), so
# this specifically exercises the "self_intersecting_or_shuffled" branch,
# not the "degenerate_normal" one.
_BOWTIE_WALL: list[Point] = [
    (0.0, 0.0, 0.0), (0.0, 0.0, 3.0), (6.0, 0.0, 0.0), (5.0, 0.0, 4.0),
]


def test_self_intersecting_loop_is_counted_and_logged_but_left_untouched():
    """The retired algorithm's full re-sort used to silently repair a
    self-intersecting vertex order into a valid simple loop (angular sort
    around the centroid). That repair is gone and is NOT reinstated here —
    this only detects + counts + logs the condition; the points passed
    through the real production entry point must come out byte-identical
    to the (still-disordered) input."""
    zone_to_surfaces = {
        "ZL5": [
            _floor("ZL5_Floor", "ZL5", _COMPLIANT_FLOOR),
            _wall("ZL5_Wall_Bowtie", "ZL5", _BOWTIE_WALL),
        ]
    }
    out = SurfaceConverter(_idf()).validate(zone_to_surfaces)
    got = {s.name: s for s in out}["ZL5_Wall_Bowtie"].vertices.tolist()

    # diagnose-only: NOT repaired into a simple loop, NOT raised — passed
    # through completely unchanged.
    assert got == _as_lists(_BOWTIE_WALL)

    assert GeometrySchema.disordered_loop_count() == 1
    log = GeometrySchema.disordered_loop_log()
    assert log == [
        {
            "name": "ZL5_Wall_Bowtie",
            "surface_type": "Wall",
            "zone": "ZL5",
            "reason": "self_intersecting_or_shuffled",
        }
    ]


def test_compliant_loops_never_trip_the_disordered_loop_detector():
    """Sanity check in the opposite direction: ordinary, already-simple
    surfaces (the same fixtures Lock 1 proves pass through unchanged) must
    NOT be flagged as disordered — the detector should fire on genuinely
    shuffled/self-intersecting input only, not on every non-'top-left'
    start point."""
    zone_to_surfaces = {
        "ZL6": [
            _floor("ZL6_Floor", "ZL6", _COMPLIANT_FLOOR),
            _wall("ZL6_Wall_S", "ZL6", _COMPLIANT_WALL),
            _wall("ZL6_Wall_Reversed", "ZL6", _REVERSED_WALL),
        ]
    }
    SurfaceConverter(_idf()).validate(zone_to_surfaces)
    assert GeometrySchema.disordered_loop_count() == 0
    assert GeometrySchema.disordered_loop_log() == []
