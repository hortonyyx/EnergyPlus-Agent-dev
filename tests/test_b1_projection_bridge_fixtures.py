"""B1 projection bridge — the five-fixture suite (dispatch §六) and the
failure-semantics / discriminating-power acceptances (#3/#4/#4b/#5).

Fixture wall thicknesses are the mandated MIX 90/150/300/370 mm in ONE
drawing (guide §十三 #2: feeding only 120/240 proves only 120/240) — the
synthetic S-mix drawing carries all four at once, and the sm25-based
fixtures exercise the real-data shapes the dispatch names (B-1's 0.1 mm
remainder, the wall removal with no geometric signature).

Every fixture proves "red before, green after" against a mechanism, not a
snapshot: the mutation names the mechanism it turns off, and the assertion
names where the reconciliation goes red.
"""

from __future__ import annotations

import copy
import json

import pytest

import src.agent.correction.projection_bridge as pb
from src.agent.correction.projection_bridge import (
    ProjectionBridgeError,
    close_collinear_gaps,
    cut_lines_from_as_measured_view,
    extend_endpoints,
    partition_lines,
    project_cut_lines,
)

from tests.b1_gt_reconciliation import (
    bound_from_baseline,
    load_gt_zones,
    reconcile_faces_vs_zones,
)
from tests.test_b1_projection_bridge_acceptance import (
    GT,
    _facts,
    bridge_sm25,
)

UPM = 10_000  # the fixture world's own declared units_per_metre (0.1 mm)

# ── the S-mix synthetic drawing: 90/150/300/370 in ONE plan ────────────────── #
# (face_lo, face_hi, along_min, along_max) per wall; thicknesses are the mix.
SMIX_WALLS = {
    "w_bottom": (0, 3000, 900, 369100, 3000),   # 300 mm
    "w_top": (296300, 300000, 900, 369100, 3700),  # 370 mm
    "w_left": (0, 900, 3000, 296300, 900),       # 90 mm
    "w_right": (368500, 370000, 3000, 296300, 1500),  # 150 mm
    # the middle separator wall is TWO segments with the door gap between
    "w_mid_v#1": (150000, 151500, 3000, 50000, 1500),
    "w_mid_v#2": (150000, 151500, 65000, 296300, 1500),
    "w_mid_h": (160000, 160900, 900, 368500, 900),
}
SMIX_DOOR = (150000, 151500, 50000, 65000)  # cross_lo, cross_hi, along lo/hi


def smix_view(*, bottom_t=3000, with_door=True):
    walls = []
    for oid, (flo, fhi, alo, ahi, t) in SMIX_WALLS.items():
        if oid == "w_bottom" and bottom_t != 3000:
            t = bottom_t
        walls.append({
            "axis": "x" if oid in ("w_bottom", "w_top", "w_mid_h") else "y",
            "id": oid.split("#")[0],
            "face_lo": flo, "face_hi": fhi,
            "along_min": alo, "along_max": ahi,
            "thickness": t,
        })
    openings = [{
        "axis": "y", "id": "door_mid",
        "cross_lo": SMIX_DOOR[0], "cross_hi": SMIX_DOOR[1],
        "along_min": SMIX_DOOR[2], "along_max": SMIX_DOOR[3],
    }] if with_door else []
    return {"view_id": "plan-S1", "walls": walls, "openings": openings}


def _mid(lo, hi):
    return (lo + hi) / 2 / UPM


def smix_truth_zones():
    """The 4 rooms in midline terms, derived from the SAME wall numbers
    (single source: no second hand-written copy of the geometry)."""
    m = {
        "bottom": _mid(0, 3000), "top": _mid(296300, 300000),
        "left": _mid(0, 900), "right": _mid(368500, 370000),
        "v": _mid(150000, 151500), "h": _mid(160000, 160900),
    }
    ring = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    return [
        ("S-z0", ring(m["left"], m["bottom"], m["v"], m["h"])),
        ("S-z1", ring(m["v"], m["bottom"], m["right"], m["h"])),
        ("S-z2", ring(m["left"], m["h"], m["v"], m["top"])),
        ("S-z3", ring(m["v"], m["h"], m["right"], m["top"])),
    ]


def smix_envelope(view):
    lines, resolution = cut_lines_from_as_measured_view(view, units_per_metre=UPM)
    return project_cut_lines(
        lines, resolution_m=resolution,
        resolution_source=f"fixture world units_per_metre={UPM} (N-3)",
        source_resolved_sha256="0" * 64, floor_id="S1", floor_name="S1",
        z_floor_m=0.0, ceiling_height_m=3.6, origin_label="plan-S1",
    )


def _reconcile(env, zones, *, bound=None):
    faces = [list(c.polygon) for c in env.geometry.floors[0].cells]
    if bound is None:
        baseline = reconcile_faces_vs_zones(faces, zones, bound_m=float("inf"))
        if not baseline.green:
            return baseline
        return reconcile_faces_vs_zones(faces, zones, bound_m=bound_from_baseline(baseline))
    return reconcile_faces_vs_zones(faces, zones, bound_m=bound)


# ── the mix itself is pinned (guide §十三 #2) ──────────────────────────────── #
def test_smix_thicknesses_are_the_mandated_mix():
    view = smix_view()
    ts = sorted({w["thickness"] / 10 for w in view["walls"]})  # mm
    assert ts == [90.0, 150.0, 300.0, 370.0]
    env = smix_envelope(view)
    assert env.face_count == 4
    assert env.dangling_end_debts == ()
    assert _reconcile(env, smix_truth_zones()).green


# ── fixture 1: the 0.1 mm remainder, defective (52401) AND fixed (52400) ───── #
B1_WALL = "w_x_99430_100630_52401_88800"  # t=120 mm, midline y=100030


def _f1_with_endpoint_remainder(remainder_units: int):
    facts = _facts()
    view = next(v for v in facts["views"] if v["view_id"] == "plan-F1")
    view = copy.deepcopy(view)
    for w in view["walls"]:
        if w["id"] == B1_WALL:
            w["along_min"] = 52400 + remainder_units
            w["id"] = f"w_x_99430_100630_{52400 + remainder_units}_88800"
    return view, facts["units_per_metre"]


@pytest.mark.parametrize("remainder", [1, 0], ids=["defective-52401", "fixed-52400"])
def test_fixture1_remainder_one_unit_both_versions_cut_14(remainder):
    """B-1's shape: the defective endpoint (52401) sits exactly 1 unit
    outside the perpendicular wall's band (|52401−51200| = 1201 > 1200).
    With the data-declared resolution BOTH the defective and the fixed
    version cut F1's signed 14 rooms; ⛔ the fix is NOT owed to the
    tolerance swallowing the registered defect — the tolerance equals the
    input's own quantisation, nothing more."""
    view, upm = _f1_with_endpoint_remainder(remainder)
    lines, resolution = cut_lines_from_as_measured_view(view, units_per_metre=upm)
    env = project_cut_lines(
        lines, resolution_m=resolution,
        resolution_source=f"fixture world units_per_metre={upm} (N-3)",
        source_resolved_sha256="0" * 64, floor_id="F1", floor_name="F1",
        z_floor_m=0.0, ceiling_height_m=3.6, origin_label="plan-F1",
    )
    assert env.face_count == 14
    assert _reconcile(env, load_gt_zones(GT, "F1")).green


def test_fixture1_red_before_tolerance_zero_is_a_loud_zero_face_layer():
    """Red BEFORE: with NO tolerance (exact comparison) the same real data
    fails the WHOLE layer — the quantisation remainders break far more
    than one extension.  The tolerance is what makes the layer runnable at
    all on quantised data, and its width is the data's own resolution."""
    view, upm = _f1_with_endpoint_remainder(1)
    lines, _ = cut_lines_from_as_measured_view(view, units_per_metre=upm)
    with pytest.raises(ProjectionBridgeError) as exc:
        project_cut_lines(
            lines, resolution_m=0.0,
            resolution_source="exact comparison (probe)",
            source_resolved_sha256="0" * 64, floor_id="F1", floor_name="F1",
            z_floor_m=0.0, ceiling_height_m=3.6, origin_label="plan-F1",
        )
    assert exc.value.code == "NO_BOUNDED_FACES_AFTER_EXTENSION"


# ── fixture 2: a 2-unit remainder must STILL be red ────────────────────────── #
def test_fixture2_two_unit_remainder_still_red():
    """|52402 − 51200| = 1202 > 1200 + 1: the tolerance must NOT eat a real
    anomaly — the extension stays off, two signed rooms merge, and the gt
    reconciliation goes red on counts AND on the unmatched pair."""
    assert abs(52402 - 51200) == 1202 > 1200 + 1  # the criterion, mechanically
    view, upm = _f1_with_endpoint_remainder(2)
    lines, resolution = cut_lines_from_as_measured_view(view, units_per_metre=upm)
    env = project_cut_lines(
        lines, resolution_m=resolution,
        resolution_source=f"fixture world units_per_metre={upm} (N-3)",
        source_resolved_sha256="0" * 64, floor_id="F1", floor_name="F1",
        z_floor_m=0.0, ceiling_height_m=3.6, origin_label="plan-F1",
    )
    assert env.face_count == 13
    report = _reconcile(env, load_gt_zones(GT, "F1"))
    assert not report.green
    assert not report.counts_ok
    assert "F1-z4" in report.unmatched_zones


# ── fixture 3: a mis-reported thickness (criterion off by 2×) ──────────────── #
def test_fixture3_misreported_thickness_goes_red_at_reconciliation():
    """The dispatch's shape (a thickness mis-reported so the extension
    criterion is off by a factor of 2), on the mixed drawing: the bottom
    wall's 3000 reported as 1500 halves every ruler that reaches it.

    ⚠️ Direction note (B-level, reported in the execution doc): the
    dispatch names "120 reported as 240" (doubling).  Measured on BOTH the
    real F1 sweep (0 flip candidates when any wall's thickness doubles)
    and the standard S-mix drawing, doubling has nothing to flip — no
    endpoint sits in the doubling ring band.  Halving flips on the natural
    drawing (the tangent extensions break), so the fixture uses 3000→1500:
    the same wrong-by-2× criterion, in the direction that bites."""
    env = smix_envelope(smix_view(bottom_t=1500))
    assert env.face_count != 4
    report = _reconcile(env, smix_truth_zones())
    assert not report.green
    assert not report.counts_ok


# ── fixture 4: a dropped opening — two redundant closing channels ──────────── #
def test_fixture4_dropped_opening_two_redundant_channels():
    """The door gap is closed by TWO independent channels — the declared
    opening span, and the §9.1① collinear-gap closing of the separator
    wall's own two segments.  Kill EITHER channel and the rooms still
    separate; kill BOTH and they silently merge — the red the channels
    exist to prevent."""
    view = smix_view()
    lines, resolution = cut_lines_from_as_measured_view(view, units_per_metre=UPM)
    walls_only = [l for l in lines if l.kind == "wall"]

    # both channels off: raw segments, no opening, no gap closing
    ext = extend_endpoints(walls_only, resolution_m=resolution)
    part = partition_lines(ext.lines, resolution_m=resolution, origin_label="S1")
    assert len(part.faces) == 3  # the two lower rooms merged

    # opening channel only (skip gap closing)
    opening_lines = [l for l in lines if l.kind != "collinear_gap"]
    ext = extend_endpoints(opening_lines, resolution_m=resolution)
    part = partition_lines(ext.lines, resolution_m=resolution, origin_label="S1")
    assert len(part.faces) == 4

    # collinear-gap channel only (no opening in the input)
    view_no_door = smix_view(with_door=False)
    lines2, _ = cut_lines_from_as_measured_view(view_no_door, units_per_metre=UPM)
    closed, gaps = close_collinear_gaps(lines2, resolution_m=resolution)
    assert len(gaps) == 1 and gaps[0].from_m == 5.0 and gaps[0].to_m == 6.5
    ext = extend_endpoints(closed, resolution_m=resolution)
    part = partition_lines(ext.lines, resolution_m=resolution, origin_label="S1")
    assert len(part.faces) == 4


# ── fixture 5: a removed wall with (at most) no geometric signature ────────── #
def test_fixture5_removed_wall_red_at_reconciliation_only():
    """W2's measured shape: removing w_y_50000_52400_121599_140000 loses a
    room while the probe-era dangling-end detector read ZERO.  This
    bridge's detector is no worse (it may catch more), but the assertion
    that matters is the one the failure semantics hand to the judge: the
    gt reconciliation MUST go red — the bridge alone never certifies
    completeness."""
    env = bridge_sm25(
        "plan-F1",
        mutate=lambda view: {
            **view,
            "walls": [
                w for w in view["walls"]
                if w["id"] != "w_y_50000_52400_121599_140000"
            ],
        },
    )
    assert env.face_count == 13
    report = _reconcile(env, load_gt_zones(GT, "F1"))
    assert not report.green
    assert not report.counts_ok
    assert "F1-z5" in report.unmatched_zones


# ── acceptance #3: the ring band, not the direction, decides ───────────────── #
def _ring_band_occupied(lines, origin_id, half_old, half_new, *, resolution):
    """The dispatch's mechanical criterion, evaluated on the MUTATED line
    set: does ANY outward endpoint of a perpendicular line sit inside the
    ring band (min, max] of the two half thicknesses?  (In a consistent
    redraw the followed endpoint sits at exactly the NEW half thickness —
    the band's excluded lower end — so a clean redraw reads empty here.)"""
    lo, hi = sorted((half_old, half_new))
    wall = next(l for l in lines if l.origin_id == origin_id)
    for other in lines:
        if other.axis == wall.axis:
            continue
        for end, outward in (
            (other.along_lo_m, wall.pos_m < other.along_lo_m),
            (other.along_hi_m, wall.pos_m > other.along_hi_m),
        ):
            d = abs(end - wall.pos_m)
            # The band edges compare within one declared resolution: a
            # followed endpoint sits at EXACTLY the new half thickness
            # mathematically, but float division lands 1 ulp outside it
            # (measured: 1.09 − 1.0 = 0.09000000000000008 vs 0.09) — a
            # hair outside the excluded lower end must not read as
            # inside the band.
            if outward and lo + resolution < d <= hi + resolution:
                return True
    return False


def _along_buffer_flips(lines, origin_id, half_old, half_new, *, resolution):
    """Does widening the wall's own half thickness flip any perpendicular
    line's cross-band membership (the end-lap buffer)?"""
    wall = next(l for l in lines if l.origin_id == origin_id)
    for other in lines:
        if other.axis == wall.axis:
            continue
        old = (wall.along_lo_m - half_old - resolution <= other.pos_m
               <= wall.along_hi_m + half_old + resolution)
        new = (wall.along_lo_m - half_new - resolution <= other.pos_m
               <= wall.along_hi_m + half_new + resolution)
        if old != new:
            return True
    return False


def _cells_of(env):
    return [tuple(map(tuple, c.polygon)) for c in env.geometry.floors[0].cells]


def test_3a_ring_band_empty_thickening_keeps_cells_vertex_identical():
    """S-mix right wall 150→250 mm: the band (75,125] holds no endpoint
    (the nearest sits at exactly 75, the band's excluded end) and no
    buffer flips — mechanically checked, THEN the cells are asserted
    vertex-identical."""
    view, upm = smix_view(), UPM
    lines, resolution = cut_lines_from_as_measured_view(view, units_per_metre=upm)
    half_old = 1500 / 2 / upm
    half_new = 2500 / 2 / upm
    assert not _ring_band_occupied(lines, "w_right", half_old, half_new, resolution=resolution)
    assert not _along_buffer_flips(lines, "w_right", half_old, half_new, resolution=resolution)
    mutated = smix_view()
    for w in mutated["walls"]:
        if w["id"] == "w_right":
            w["thickness"] = 2500
    assert sorted(_cells_of(smix_envelope(view))) == sorted(
        _cells_of(smix_envelope(mutated))
    )


def test_3b_consistent_redraw_keeps_cells_vertex_identical():
    """The mini-drawing of v6's B3' probe: wall A thinned 2400→1800 with
    the neighbour's endpoint FOLLOWING the face (11200→10900) — the
    followed endpoint stays at exactly the new half thickness (900), so
    the band (900,1200] is empty by construction and the cells are
    vertex-identical.  Shrinking the face WITHOUT following (endpoint left
    at 11200, inside the band) flips the extension off and merges rooms."""
    def wall(axis, pos, lo, hi, t, oid):
        return pb.CutLineV1(
            axis=axis, pos_m=pos / UPM, along_lo_m=lo / UPM, along_hi_m=hi / UPM,
            half_thickness_m=t / 2 / UPM, kind="wall", origin_id=oid,
        )

    def drawing(a_t, b_lo):
        return [
            wall("y", 10000, 0, 20000, a_t, "A"),
            wall("y", 30000, 0, 20000, 2000, "E"),
            wall("x", 20000, b_lo, 29000, 2000, "B"),
            wall("x", 10000, 10000, 30000, 2000, "C"),
            wall("x", 0, 10000, 30000, 2000, "D"),
        ]

    res = 1 / UPM
    baseline = drawing(2400, 11200)
    redrawn = drawing(1800, 10900)  # face 9100–10900, endpoint follows
    lines_base, _ = [baseline], res
    closed, _ = close_collinear_gaps(baseline, resolution_m=res)
    cells_base = partition_lines(
        extend_endpoints(closed, resolution_m=res).lines,
        resolution_m=res, origin_label="m",
    )
    closed, _ = close_collinear_gaps(redrawn, resolution_m=res)
    cells_redrawn = partition_lines(
        extend_endpoints(closed, resolution_m=res).lines,
        resolution_m=res, origin_label="m",
    )
    assert len(cells_base.faces) == 2
    assert sorted(map(tuple, cells_base.faces)) == sorted(map(tuple, cells_redrawn.faces))
    # the band is empty — mechanically, ON THE MUTATED SET (the followed
    # endpoint sits at exactly the new half thickness: 900, excluded)
    assert not _ring_band_occupied(
        redrawn, "A", 2400 / 2 / UPM, 1800 / 2 / UPM, resolution=res
    )
    # and the negative control: shrink without following leaves the
    # endpoint INSIDE the band ⇒ the extension flips off ⇒ cells change
    not_followed = drawing(1800, 11200)
    assert _ring_band_occupied(
        not_followed, "A", 2400 / 2 / UPM, 1800 / 2 / UPM, resolution=res
    )
    closed, _ = close_collinear_gaps(not_followed, resolution_m=res)
    cells_control = partition_lines(
        extend_endpoints(closed, resolution_m=res).lines,
        resolution_m=res, origin_label="m",
    )
    assert len(cells_control.faces) != len(cells_base.faces)


def test_3c_ring_band_occupied_thickening_MAY_change_cells():
    """v6's B2' shape (truth-consistent thickening that swallows an
    endpoint): baseline B.lo=13000 is 3000 units outside A's midline
    (beyond the old half 1200, inside the new half 4500) — band non-empty
    ⇒ cells change, and ⚠️ that is NOT a defect (dispatch §五 #3: the
    ring band, not the direction, decides)."""
    def wall(axis, pos, lo, hi, t, oid):
        return pb.CutLineV1(
            axis=axis, pos_m=pos / UPM, along_lo_m=lo / UPM, along_hi_m=hi / UPM,
            half_thickness_m=t / 2 / UPM, kind="wall", origin_id=oid,
        )

    def drawing(a_t):
        return [
            wall("y", 10000, 0, 20000, a_t, "A"),
            wall("y", 30000, 0, 20000, 2000, "E"),
            wall("x", 20000, 13000, 29000, 2000, "B"),
            wall("x", 10000, 10000, 30000, 2000, "C"),
            wall("x", 0, 10000, 30000, 2000, "D"),
        ]

    res = 1 / UPM
    base = drawing(2400)
    assert _ring_band_occupied(
        base, "A", 2400 / 2 / UPM, 9000 / 2 / UPM, resolution=res
    )
    cells = []
    for lines in (base, drawing(9000)):
        closed, _ = close_collinear_gaps(lines, resolution_m=res)
        part = partition_lines(
            extend_endpoints(closed, resolution_m=res).lines,
            resolution_m=res, origin_label="m",
        )
        cells.append(part.faces)
    assert len(cells[0]) != len(cells[1])  # 1 → 2: band occupied ⇒ may change


# ── acceptance #4: the loud layer failure and the dangling end ─────────────── #
def test_4a_zero_bounded_faces_is_the_loud_layer_failure():
    def wall(axis, pos, lo, hi, t, oid):
        return pb.CutLineV1(
            axis=axis, pos_m=pos / UPM, along_lo_m=lo / UPM, along_hi_m=hi / UPM,
            half_thickness_m=t / 2 / UPM, kind="wall", origin_id=oid,
        )

    two_parallels = [
        wall("y", 10000, 0, 20000, 2400, "A"),
        wall("y", 30000, 0, 20000, 2000, "E"),
    ]
    res = 1 / UPM
    with pytest.raises(ProjectionBridgeError) as exc:
        partition_lines(two_parallels, resolution_m=res, origin_label="m")
    assert exc.value.code == "NO_BOUNDED_FACES_AFTER_EXTENSION"


def test_4b_dangling_end_is_debt_and_degraded_not_layer_failure():
    """A dangling end unrelated to quantisation (the endpoint reaches far
    past every band): the layer still delivers, the end is a NAMED debt,
    completion is degraded — and the FACE COUNT is judged by the
    reconciliation, which stays green (the stub changes no room)."""
    view = smix_view()
    for w in view["walls"]:
        if w["id"] == "w_mid_h":
            w["along_max"] = 500000  # reaches 13 m past the right wall
    env = smix_envelope(view)
    assert env.completion == "degraded"
    assert len(env.dangling_end_debts) == 1
    assert env.dangling_end_debts[0].origin_id == "w_mid_h"
    assert env.face_count == 4
    assert _reconcile(env, smix_truth_zones()).green


# ── acceptance #4b: the two extension failure modes go red at the judge ────── #
def _f1_ghost():
    facts = _facts()
    view = copy.deepcopy(
        next(v for v in facts["views"] if v["view_id"] == "plan-F1")
    )
    view["walls"].append({
        "axis": "y", "id": "ghost_probe",
        "face_lo": 91000, "face_hi": 93400,
        "along_min": 39400, "along_max": 160600,
        "thickness": 2400,
    })
    return view, facts["units_per_metre"]


def _f1_bound():
    zones = load_gt_zones(GT, "F1")
    env = bridge_sm25("plan-F1")
    faces = [list(c.polygon) for c in env.geometry.floors[0].cells]
    return bound_from_baseline(
        reconcile_faces_vs_zones(faces, zones, bound_m=float("inf"))
    )


def _bridge(view, upm, *, mutate_extra=None):
    if mutate_extra is not None:
        view = mutate_extra(view)
    lines, resolution = cut_lines_from_as_measured_view(view, units_per_metre=upm)
    return project_cut_lines(
        lines, resolution_m=resolution,
        resolution_source=f"fixture world units_per_metre={upm} (N-3)",
        source_resolved_sha256="0" * 64, floor_id="F1", floor_name="F1",
        z_floor_m=0.0, ceiling_height_m=3.6, origin_label="plan-F1",
    )


def test_4b_ghost_wall_red_where():
    """S3-family, extra-cut shape: a phantom wall chords the largest room.
    RED on ① (counts) and ③ (an ownerless face) — the two-directional
    clauses doing their work."""
    view, upm = _f1_ghost()
    env = _bridge(view, upm)
    zones = load_gt_zones(GT, "F1")
    report = _reconcile(env, zones, bound=_f1_bound())
    assert not report.green
    assert not report.counts_ok and env.face_count == 15
    assert report.ownerless_faces


def test_4b_counts_equalised_attack_red_only_on_2_and_3():
    """The sharper shape: phantom wall PLUS a killed extension equalises
    the counts (14 = 14) — ① alone passes, and the red lands on ② (zones
    whose face is a merged/phantom shape, beyond the derived bound) and ③
    (ownerless faces).  ⭐ The one-directional UNBOUNDED version (every
    zone matched to its nearest face, no ③) reads GREEN on exactly this
    input — pinned here so the blindness is measured, not asserted."""
    def kill_extension(view):
        view = copy.deepcopy(view)
        for w in view["walls"]:
            if w["id"] == B1_WALL:
                w["along_min"] = 52402  # 2 units out: extension stays off
        return view

    view, upm = _f1_ghost()
    env = _bridge(view, upm, mutate_extra=kill_extension)
    zones = load_gt_zones(GT, "F1")
    report = _reconcile(env, zones, bound=_f1_bound())
    assert report.counts_ok and env.face_count == 14  # ① passes: the trap
    assert not report.green
    assert report.unmatched_zones and report.ownerless_faces
    # the one-directional unbounded version is blind on exactly this input
    faces = [list(c.polygon) for c in env.geometry.floors[0].cells]
    one_way = reconcile_faces_vs_zones(faces, zones, bound_m=float("inf"))
    assert one_way.counts_ok and not one_way.unmatched_zones  # GREEN: blind


# ── acceptance #5: the judge discriminates this bridge's defects ───────────── #
def test_5_dropping_a_room_changes_the_verdict(monkeypatch):
    """Design §三 路 C's rejection reason, verified: a defect IN the bridge
    (one face silently dropped) must be VISIBLE to the reconciliation —
    same-source judge and product would score it zero-difference."""
    real_partition = pb.partition_lines

    def drop_last_face(lines, *, resolution_m, origin_label=""):
        outcome = real_partition(
            lines, resolution_m=resolution_m, origin_label=origin_label
        )
        return pb.PartitionOutcome(
            faces=outcome.faces[:-1],
            footprint_ring=outcome.footprint_ring,
            dangling_ends=outcome.dangling_ends,
        )

    monkeypatch.setattr(pb, "partition_lines", drop_last_face)
    env = bridge_sm25("plan-F1")
    assert env.face_count == 13  # the mutation took: a room is gone
    report = _reconcile(env, load_gt_zones(GT, "F1"))
    assert not report.green
    assert not report.counts_ok
