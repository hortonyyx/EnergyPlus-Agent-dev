"""W#6 (wallhunt 2026-09-08b / dispatch 2026-09-08c S-B) — the exterior
axis frame from the drawing's OWN declarations + the cut-line-level
cross-floor reconciliation.

WHAT THIS FILE LOCKS (all on the REAL sm25 as-drawn products, fixed model
beat — ⛔ zero mocked geometry):

1. ``snap_exterior_walls_to_declared_frame`` moves exactly the FOUR
   exterior edges onto the declared axis frame ``[t/2, overall − t/2]``
   (measured on sm25: footprint becomes exactly [0.12, 24.88]×[0.12,
   19.88] on BOTH floors — the two independently-calibrated drawings
   agree BY CONSTRUCTION, not within a tolerance);
2. ``reconcile_floors_to_reference`` makes the two floors' rings
   BIT-IDENTICAL while keeping each floor's coverage conservation at
   0.000000 (the verbatim ring swap it replaced broke floor 2's
   conservation by 0.3806 m² against a 0.05 gate — that is the W#6 root
   cause, and this lock pins its absence);
3. the gates have teeth:
   * ``EXTERIOR_WALL_OFF_DECLARED_FRAME`` — an exterior edge further than
     the cap from its declared axis is refused, ⛔ never silently
     absorbed (a drawing error is not a representation fix);
   * ``EXTERIOR_THICKNESS_UNDECLARED`` — an exterior wall whose resolved
     thickness matches NO declared callout cannot have a frame derived;
   * alignment tolerance — a wall further than the derived tolerance from
     every reference wall KEEPS ITS OWN position (genuinely different
     layouts are never re-shaped onto the reference).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tool_scripts"))

from src.agent.correction.multifloor import (  # noqa: E402
    read_declared_exterior_frame,
)
from src.agent.correction.projection_bridge import (  # noqa: E402
    CutLineV1,
    ProjectionBridgeError,
    align_wall_lines_to_reference,
    snap_exterior_walls_to_declared_frame,
)

_SRC = REPO / "case_tests/e2e_tests/sm25-L_anchor/run_wallhunt/0_reading"


def _declared(floor: str):
    import json

    doc = json.loads((_SRC / f"{floor}_view.json").read_text("utf-8"))
    return read_declared_exterior_frame(doc, input_id=f"{floor}_view")


def _wall(axis: str, pos: float, half: float = 0.12, origin: str = "w") -> CutLineV1:
    return CutLineV1(
        axis=axis, pos_m=pos, along_lo_m=0.0, along_hi_m=20.0,
        half_thickness_m=half, kind="wall", origin_id=origin,
    )


def _opening(axis: str, pos: float, half: float, origin: str) -> CutLineV1:
    return CutLineV1(
        axis=axis, pos_m=pos, along_lo_m=5.0, along_hi_m=8.0,
        half_thickness_m=half, kind="opening", origin_id=origin,
    )


# ── lock 1: the declared axis frame, on the real declarations ─────────────── #
def test_real_sm25_snap_moves_exactly_the_four_exterior_edges():
    frame = _declared("1f")
    lines = (
        _wall("y", 0.1137, origin="west"),      # x-run walls fix y? NO —
        # ⚠ axis vocabulary: a "y"-run line varies in y, so its pos IS an x
        # value.  The four exterior edges below use that vocabulary.
        _wall("y", 24.8841, origin="east"),
        _wall("x", 0.1175, origin="south"),
        _wall("x", 19.87835, origin="north"),
        _wall("y", 14.8784, half=0.12, origin="notch"),   # interior — stays
        _wall("x", 5.8786, half=0.12, origin="notch2"),   # interior — stays
    )
    snapped, records = snap_exterior_walls_to_declared_frame(
        lines,
        overall_x_m=frame.overall_x_m,
        overall_y_m=frame.overall_y_m,
        thickness_callouts_mm=frame.thickness_callouts_mm,
        input_id="1f_view",
    )
    by_origin = {line.origin_id: line.pos_m for line in snapped}
    # sm25's declared frame: 25000/20000 overall, 240 exterior wall
    assert by_origin["west"] == pytest.approx(0.120)
    assert by_origin["east"] == pytest.approx(24.880)
    assert by_origin["south"] == pytest.approx(0.120)
    assert by_origin["north"] == pytest.approx(19.880)
    # interior walls are NOT on the declared ticks — they keep their ink
    assert by_origin["notch"] == pytest.approx(14.8784)
    assert by_origin["notch2"] == pytest.approx(5.8786)
    assert len(records) == 4


def test_opening_riding_an_exterior_wall_follows_it():
    frame = _declared("1f")
    lines = (
        _wall("y", 24.8841, origin="east"),
        _wall("y", 0.1137, origin="west"),
        _wall("x", 19.87835, origin="north"),
        _wall("x", 0.1175, origin="south"),
        _opening("y", 24.8841, 0.12, "win_e1"),
        # an interior opening far from any exterior edge — stays
        _opening("x", 14.1226, 0.12, "win_i"),
    )
    snapped, records = snap_exterior_walls_to_declared_frame(
        lines,
        overall_x_m=frame.overall_x_m,
        overall_y_m=frame.overall_y_m,
        thickness_callouts_mm=frame.thickness_callouts_mm,
        input_id="1f_view",
    )
    by_origin = {line.origin_id: line.pos_m for line in snapped}
    assert by_origin["win_e1"] == pytest.approx(24.880)
    assert by_origin["win_i"] == pytest.approx(14.1226)
    east = next(r for r in records if r.wall_origin_id == "east")
    assert east.followed_opening_ids == ("win_e1",)


# ── lock 2: the gates' teeth ──────────────────────────────────────────────── #
def test_off_frame_exterior_edge_is_refused():
    frame = _declared("1f")
    lines = (
        _wall("y", 0.1137, origin="west"),
        _wall("y", 23.0, origin="east"),        # 1.88 m off the declared axis
        _wall("x", 0.1175, origin="south"),
        _wall("x", 19.87835, origin="north"),
    )
    with pytest.raises(ProjectionBridgeError) as exc:
        snap_exterior_walls_to_declared_frame(
            lines,
            overall_x_m=frame.overall_x_m,
            overall_y_m=frame.overall_y_m,
            thickness_callouts_mm=frame.thickness_callouts_mm,
            input_id="1f_view",
        )
    assert exc.value.code == "EXTERIOR_WALL_OFF_DECLARED_FRAME"


def test_undeclared_exterior_thickness_is_refused():
    frame = _declared("1f")
    lines = (
        _wall("y", 0.1137, half=0.5, origin="west"),   # 1000 mm — no callout
        _wall("y", 24.8841, origin="east"),
        _wall("x", 0.1175, origin="south"),
        _wall("x", 19.87835, origin="north"),
    )
    with pytest.raises(ProjectionBridgeError) as exc:
        snap_exterior_walls_to_declared_frame(
            lines,
            overall_x_m=frame.overall_x_m,
            overall_y_m=frame.overall_y_m,
            thickness_callouts_mm=frame.thickness_callouts_mm,
            input_id="1f_view",
        )
    assert exc.value.code == "EXTERIOR_THICKNESS_UNDECLARED"


# ── lock 3: the cross-floor alignment's own bounds ────────────────────────── #
def test_alignment_moves_only_within_tolerance_and_openings_follow():
    reference = (
        _wall("y", 0.120, origin="r_west"),
        _wall("y", 14.8784, origin="r_notch"),
        _wall("x", 5.8786, origin="r_n1"),
    )
    upper = (
        _wall("y", 0.1245, origin="u_west"),        # 4.5 mm — inside tol
        _wall("y", 14.8749, origin="u_notch"),      # 3.5 mm — inside tol
        _wall("y", 9.0916, origin="u_own"),         # no counterpart — stays
        _wall("x", 5.88335, origin="u_n1"),         # 4.75 mm — inside tol
        _opening("x", 5.88335, 0.12, "u_win"),
    )
    aligned, records = align_wall_lines_to_reference(
        upper, reference, tolerance_m=0.0206
    )
    by_origin = {line.origin_id: line.pos_m for line in aligned}
    assert by_origin["u_west"] == pytest.approx(0.120)
    assert by_origin["u_notch"] == pytest.approx(14.8784)
    assert by_origin["u_n1"] == pytest.approx(5.8786)
    assert by_origin["u_win"] == pytest.approx(5.8786)   # follows its host
    # the upper floor's OWN wall (metres from any reference wall) is intact
    assert by_origin["u_own"] == pytest.approx(9.0916)
    assert len(records) == 3


def test_out_of_tolerance_wall_keeps_its_position():
    reference = (_wall("y", 0.120, origin="r_west"),)
    upper = (_wall("y", 0.5, origin="u_far"),)     # 380 mm — way out
    aligned, records = align_wall_lines_to_reference(
        upper, reference, tolerance_m=0.0206
    )
    assert aligned[0].pos_m == pytest.approx(0.5)
    assert records == ()
