"""F-17 (2026-08-09): envelope transform chamfers a right angle into a 45deg
edge when TWO axis-orthogonal shared-axis components move in the SAME
transaction (one on x, one on y, both claiming the same corner).

`_apply_components` used to iterate `components.values()` one component at a
time, mutating the ring in place before moving on to the next component.
When the second component was axis-orthogonal to the first, its
`_on_component` predicate tested coordinates the FIRST component had
already moved: a shared corner fell outside the second component's interval
purely because the first move had shifted it off its own axis.
`_materialize_axis_splits` then reinserted a fresh point back at the
original (now legitimately in-interval) location and moved only that new
point -- one right angle split into two points joined by a diagonal edge.
Real trigger: `cell RM1F_01: polygon edge 3 is not orthogonal`, from the
first real correction draw that ever reached this code path (sm21, after
F-16 unblocked the parse layer). Full mechanism, real-data repro and a
15-cell combination matrix (cross-axis <=> diagonal, zero exceptions):
AI_agent/logs/experiments/2026-08-09_f17_envelope_cross_axis_chamfer/README.md

The fix replaces "move while judging" with three phases, all still inside
`_apply_components`:
  Phase 1 materialize -- insert every component's T-junction split points
    against the ring exactly as given; nothing moves yet.
  Phase 2 relocate -- test every vertex against EVERY component using that
    vertex's frozen original coordinates (never a coordinate a previous
    match already wrote), applying every axis that matches independently.
    One corner can be claimed by an x component and a y component at once.
  Phase 3 normalize -- unchanged (canonical CCW / rect fallback / ring
    validation).
This restores, for the vertex-ring representation, the cross-axis
independence the legacy bbox/index representation (`values[edge_idx] =
new_value`) always had for free.

A second, independent bug shared the same three lines of code: the post-move
`validate_cell_polygon` call inside `_apply_components` raised a BARE
`ValueError` -- uncaught anywhere between here and `finalize_correction_draw`
-- so any cell-level ring failure blew straight through the whole flow with
zero attempts archived (the same shape as the F-15 "second wall"). The fix
wraps that call and re-raises as a structured `EnvelopeTransformRejected`
(check_id `correction.envelope_cell_ring_valid`), which
`apply_v3_envelope_transaction`'s existing try/except already turns into a
normal, archived, resample-eligible rejection -- the exact path every OTHER
hard gate in this file already uses (`correction.envelope_ring_valid` for
the footprint-ring case is the direct sibling).

⛔ Every fixture below uses a NONZERO footprint origin (lo != 0) on purpose.
Every pre-existing v3-transform fixture in this repo (`test_c2_b2b_envelope_
transform.py`'s `_geom()` / `_u_geom()`, `test_c2_b5_host_resolution.py`'s
RECT/U_RING/L_RING/PARTIAL_EAST_RING) starts its footprint ring at [0, 0] --
structurally the lo side never needs to move, so no existing fixture can
ever produce a cross-axis component PAIR. That is exactly why 2323 passing
tests never caught this bug; it is also why a fixture that keeps lo == 0
would be a false lock here no matter what it asserts.

Group layout:
  A -- core cross-axis lock: real sm21 F1 layout (footprint + 7 cells,
       verbatim from the run that actually crashed), all four sides move,
       assertions are hand-computed coordinates (not "no exception").
  B -- L-shaped footprint + cross-axis lock: proves `_materialize_axis_
       splits` is still wired in and the notch survives (dispatch's
       required second grid).
  C -- classification lock: a REAL (non-monkeypatched) validate_cell_polygon
       failure reached through _apply_components's own post-move validation
       loop comes back as a structured rejection, not a bare exception.
"""
from __future__ import annotations

import pytest

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.envelope import (
    AuthoritativeEnvelope,
    EnvelopeAxisResolution,
    EnvelopeCandidate,
)
from src.agent.correction.envelope_transform import apply_v3_envelope_transaction
from src.agent.correction.parse import ensure_corrected_geometry

# ---------------------------------------------------------------------------
# Group A -- core cross-axis lock (real sm21 F1 layout)
# ---------------------------------------------------------------------------


def _sm21_f1_geom():
    """Single floor, verbatim from the correction draw that actually crashed
    (case_tests/e2e_tests/sm21_anchor/run_2026-08-08_f16_e2e_verify/
    1_correction/correction_geometry.json, floors[0]): a 2x3 room grid plus a
    full-width corridor, footprint 0.12 m inset from the true envelope on
    every side. RM1F_01/03/04/06 each occupy one footprint corner -- exactly
    where the report's F1 evidence showed the chamfer (cell touches corner
    <=> chamfered, verified against all 7 cells, zero exceptions)."""
    return ensure_corrected_geometry({
        "schema_version": "3", "footprint_x": [0.12, 14.88], "footprint_y": [0.12, 7.88],
        "floors": [{
            "id": "f1", "name": "F1", "z_floor": 0, "ceiling_height": 3,
            "footprint": {"vertices": [[0.12, 0.12], [14.88, 0.12], [14.88, 7.88], [0.12, 7.88]]},
            "cells": [
                {"id": "RM1F_01", "x": [0.12, 5.0], "y": [5.0, 7.88]},
                {"id": "RM1F_02", "x": [5.0, 10.0], "y": [5.0, 7.88]},
                {"id": "RM1F_03", "x": [10.0, 14.88], "y": [5.0, 7.88]},
                {"id": "RM1F_04", "x": [0.12, 5.0], "y": [0.12, 3.0]},
                {"id": "RM1F_05", "x": [5.0, 10.0], "y": [0.12, 3.0]},
                {"id": "RM1F_06", "x": [10.0, 14.88], "y": [0.12, 3.0]},
                {"id": "CORR_1F", "x": [0.12, 14.88], "y": [3.0, 5.0]},
            ],
        }],
    })


def _sm21_f1_envelope():
    """Both x and y overall bounds accepted -- the structural precondition
    for a cross-axis component pair (one x component + one y component both
    claiming the same footprint corner)."""
    x = EnvelopeCandidate("x", (0.0, 15.0), 15.0, "dimension", "South", "overall-x", role="overall", confidence=.95)
    y = EnvelopeCandidate("y", (0.0, 8.0), 8.0, "dimension", "East", "overall-y", role="overall", confidence=.95)
    return AuthoritativeEnvelope({
        "x": EnvelopeAxisResolution("x", "accepted", (0.0, 15.0), 15.0, x, candidates=(x,)),
        "y": EnvelopeAxisResolution("y", "accepted", (0.0, 8.0), 8.0, y, candidates=(y,)),
    })


def test_cross_axis_components_move_every_footprint_corner_without_chamfering():
    before = _sm21_f1_geom()
    result = apply_v3_envelope_transaction(before, load_core_tolerances(), _sm21_f1_envelope())
    assert result.committed, result.geom.conflicts
    f1 = result.geom.floors[0]
    assert [tuple(p) for p in f1.footprint.vertices] == [
        (0.0, 0.0), (15.0, 0.0), (15.0, 8.0), (0.0, 8.0),
    ]
    cells = {c.id: c for c in f1.cells}
    # Corner rooms (each occupies one footprint corner): BOTH axes move.
    assert (cells["RM1F_01"].x, cells["RM1F_01"].y) == ([0.0, 5.0], [5.0, 8.0])
    assert (cells["RM1F_03"].x, cells["RM1F_03"].y) == ([10.0, 15.0], [5.0, 8.0])
    assert (cells["RM1F_04"].x, cells["RM1F_04"].y) == ([0.0, 5.0], [0.0, 3.0])
    assert (cells["RM1F_06"].x, cells["RM1F_06"].y) == ([10.0, 15.0], [0.0, 3.0])
    # Edge rooms (touch only one axis's boundary): only that axis moves.
    assert (cells["RM1F_02"].x, cells["RM1F_02"].y) == ([5.0, 10.0], [5.0, 8.0])
    assert (cells["RM1F_05"].x, cells["RM1F_05"].y) == ([5.0, 10.0], [0.0, 3.0])
    # Corridor spans the full x width, touches neither y boundary.
    assert (cells["CORR_1F"].x, cells["CORR_1F"].y) == ([0.0, 15.0], [3.0, 5.0])
    # None were chamfered into an explicit non-rect polygon (the F-17 bug's
    # signature) -- all seven stayed plain axis-aligned rectangles.
    assert all(c.polygon is None for c in f1.cells)
    # Direct evidence a single corner vertex was independently claimed by
    # BOTH the x component and the y component in the same pass: the
    # footprint's corner-0 (0.12, 0.12) ring index appears twice in the
    # move audit, once per axis.
    moved = result.geom.corrections[-1]["moved"]
    assert moved["floor_vertex_refs"].count("f1:0") == 2
    assert moved["cell_vertex_refs"].count("f1:RM1F_04:0") == 2


# ---------------------------------------------------------------------------
# Group B -- L-shaped footprint + cross-axis lock (materialize wiring)
# ---------------------------------------------------------------------------


_L_RING = [[0.12, 0.12], [10.0, 0.12], [10.0, 3.0], [4.0, 3.0], [4.0, 7.88], [0.12, 7.88]]


def _l_shape_geom():
    """L-shaped footprint (notch in the top-right) with two cells that share
    the x=0.12 wall via a T-junction (`bottom` covers the full width at the
    low y range, `top` covers only the left arm at the high y range) -- the
    scenario dispatch flags as needing `_materialize_axis_splits` for real,
    combined with the same cross-axis (x-lo AND y-lo) component pair."""
    return ensure_corrected_geometry({
        "schema_version": "3", "footprint_x": [0.12, 10.0], "footprint_y": [0.12, 7.88],
        "floors": [{
            "id": "f1", "name": "F1", "z_floor": 0, "ceiling_height": 3,
            "footprint": {"vertices": [list(p) for p in _L_RING]},
            "cells": [
                {"id": "bottom", "x": [0.12, 10.0], "y": [0.12, 3.0]},
                {"id": "top", "x": [0.12, 4.0], "y": [3.0, 7.88]},
            ],
        }],
    })


def _l_shape_envelope():
    """Only the lo side of each axis is resolved (hi stays put) -- the notch
    corners (10.0, 3.0), (4.0, 3.0), (4.0, 7.88) must survive untouched."""
    x = EnvelopeCandidate("x", (0.0, 10.0), 10.0, "dimension", "South", "l-shape-x", role="overall", confidence=.95)
    y = EnvelopeCandidate("y", (0.0, 7.88), 7.88, "dimension", "East", "l-shape-y", role="overall", confidence=.95)
    return AuthoritativeEnvelope({
        "x": EnvelopeAxisResolution("x", "accepted", (0.0, 10.0), 10.0, x, candidates=(x,)),
        "y": EnvelopeAxisResolution("y", "accepted", (0.0, 7.88), 7.88, y, candidates=(y,)),
    })


def test_l_shape_footprint_with_cross_axis_components_preserves_notch():
    before = _l_shape_geom()
    result = apply_v3_envelope_transaction(before, load_core_tolerances(), _l_shape_envelope())
    assert result.committed, result.geom.conflicts
    f1 = result.geom.floors[0]
    # Only the (0.12, 0.12) origin corner moves; the notch corners (which
    # never sit on x=0.12 or y=0.12) are untouched -- the L-shape is not
    # flattened into a rectangle and no diagonal edge appears anywhere.
    assert [tuple(p) for p in f1.footprint.vertices] == [
        (0.0, 0.0), (10.0, 0.0), (10.0, 3.0), (4.0, 3.0), (4.0, 7.88), (0.0, 7.88),
    ]
    cells = {c.id: c for c in f1.cells}
    assert (cells["bottom"].x, cells["bottom"].y) == ([0.0, 10.0], [0.0, 3.0])
    assert (cells["top"].x, cells["top"].y) == ([0.0, 4.0], [3.0, 7.88])
    assert all(c.polygon is None for c in f1.cells)


# ---------------------------------------------------------------------------
# Group C -- classification lock: structured rejection, not a bare exception
# ---------------------------------------------------------------------------


def _sliver_geom():
    """A single cell carrying an EXPLICIT `polygon` (not a bbox) that is
    valid before the transform (0.13 m wide, `min_edge_length_m` is 0.10 m)
    and collapses to 0.07 m after an inward x-lo correction (0.12 -> 0.18) --
    a genuine, non-monkeypatched `validate_cell_polygon` failure reached
    through `_apply_components`'s own post-move validation loop. Nothing
    about this fixture touches the cross-axis mechanism in Groups A/B; it
    exists purely to prove the classification fix (any ring failure this
    loop finds becomes a structured rejection) independently of what caused
    the ring to become invalid."""
    return ensure_corrected_geometry({
        "schema_version": "3", "footprint_x": [0.12, 10.0], "footprint_y": [0.0, 3.0],
        "floors": [{
            "id": "f1", "name": "F1", "z_floor": 0, "ceiling_height": 3,
            "footprint": {"vertices": [[0.12, 0.0], [10.0, 0.0], [10.0, 3.0], [0.12, 3.0]]},
            "cells": [{
                "id": "sliver", "x": [0.12, 0.25], "y": [0.0, 3.0],
                "polygon": [[0.12, 0.0], [0.25, 0.0], [0.25, 3.0], [0.12, 3.0]],
            }],
        }],
    })


def _sliver_envelope():
    x = EnvelopeCandidate("x", (0.18, 10.0), 9.82, "dimension", "South", "sliver-x", role="overall", confidence=.95)
    return AuthoritativeEnvelope({
        "x": EnvelopeAxisResolution("x", "accepted", (0.18, 10.0), 9.82, x, candidates=(x,)),
    })


def test_cell_ring_failure_is_a_structured_rejection_not_a_bare_exception():
    tol = load_core_tolerances()
    assert tol.min_edge_length_m == 0.1  # the fixture's 0.07 m collapse depends on this
    before = _sliver_geom()
    # No pytest.raises: a regression back to the pre-fix behaviour would
    # surface as an uncaught ValueError escaping this call, failing the test
    # with an error rather than an assertion -- exactly the "blows through
    # the flow" shape this lock exists to catch.
    result = apply_v3_envelope_transaction(before, tol, _sliver_envelope())
    assert not result.committed
    assert result.failed_gate_id == "correction.envelope_cell_ring_valid"
    conflict = result.geom.conflicts[-1]
    assert conflict["conflict_type"] == "unsupported_geometry"
    assert conflict["claim_type"] == "topology_identity"
    assert conflict["fallback_action"] == "rollback_keep_original_geometry"
    assert "below min_edge_length_m" in conflict["reason_unresolved"]
    assert conflict["evidence"] == {"floor_id": "f1", "cell_id": "sliver"}
    # Rollback contract: the returned geometry is the pre-transform input,
    # not a half-applied candidate.
    assert result.geom.floors[0].cells[0].x == [0.12, 0.25]


def _components_for(geom, envelope):
    """Build the component set exactly as the transaction does."""
    from src.agent.correction import envelope_transform as transform

    tol = load_core_tolerances()
    return [
        transform.build_shared_axis_component(geom, intent, tol)
        for intent in transform.resolve_envelope_move_intents(geom, envelope, tol)
    ]


@pytest.mark.parametrize(
    "builder,envelope_builder",
    [(_sm21_f1_geom, _sm21_f1_envelope), (_l_shape_geom, _l_shape_envelope)],
    ids=["rect-sm21", "l-shape"],
)
def test_component_application_is_order_independent(builder, envelope_builder):
    """Order-independence is the PROPERTY the F-17 fix restores -- lock it.

    sol cross-review 2026-08-09 (MINOR-4): the other tests only ever exercise
    the one ordering ``resolve_envelope_move_intents`` happens to emit, so a
    future refactor could quietly reintroduce order-dependence without any
    test objecting.  The pre-fix implementation FAILS this outright (it
    chamfers, so the two orderings do not even both survive validation).

    Neuter direction: restore the per-component "move while judging" loop and
    this turns red.
    """
    from src.agent.correction import envelope_transform as transform

    tol = load_core_tolerances()
    components = _components_for(builder(), envelope_builder())
    assert len(components) >= 2, "fixture premise: need >=2 components to permute"
    assert len({c.axis for c in components}) == 2, "fixture premise: need a cross-axis pair"

    def apply(order):
        geom = builder()
        moved = transform._apply_components(
            geom, {str(i): comp for i, comp in enumerate(order)}, tol,
        )
        rings = [[tuple(p) for p in f.footprint.vertices] for f in geom.floors]
        cells = [
            (f.id, c.id, transform.cell_polygon_vertices(c), tuple(c.x), tuple(c.y))
            for f in geom.floors for c in f.cells
        ]
        return rings, cells, {k: sorted(v) for k, v in moved.items()}

    forward = apply(components)
    reverse = apply(list(reversed(components)))
    assert forward == reverse
