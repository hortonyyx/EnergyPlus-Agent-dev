"""F-18: the B5 claim self-check must compare binary64 round-trips on B5's own
epsilons, not with exact ``!=``.

Why this file exists (2026-08-09).  ``window_host_claim_issues`` re-derives a
resolution's world span / plan endpoints / vertices from that SAME resolution's
stored parameter interval and compares them to the stored values.  Both sides
describe one already-resolved wall, but they travel different arithmetic
(``t = ((x - p1) * L) / L**2`` then ``p1 + t * L``), so the round trip can land
1-4 ULP away.  With an exact ``!=`` the check called that "tampering" and threw
``invariant_no_geometry_commit`` -- a bare raise that terminates the whole flow.
On the first real v3 product to reach this code (run_2026-08-09_f17_e2e_verify)
6 of 15 windows failed that way, with drifts <= 2.22e-15 m.

⛔ HOW THIS FILE WAS WRONG ON ITS FIRST ATTEMPT (sol cross-review, MAJOR-1) --
read before editing.  The first version picked "awkward decimals" (11.36, 1.24
...) and assumed that was enough to reproduce the bug.  It is not.  Whether the
round trip loses a bit depends on the WHOLE arithmetic path -- the host line's
origin p1, its length L, and the span value together.  The first fixture used
the PRE-transform ring
([0.12, 14.88]) while the real failure happens on the POST-F-17 ring ([0, 15]),
so its headline "real production case" round-tripped bit-exactly and stayed
GREEN even with the old ``!=`` restored.  It was not a lock at all.

⇒ The rule this file now follows: **a regression case must prove its own
premise.**  Every lock below first asserts that the old exact comparison really
would have failed on this fixture (``_round_trip_differs``), and only then
asserts that the tolerant gate lets it through.  ⛔ Never again select fixtures
by "these numbers look awkward" -- measure.

Full investigation:
AI_agent/logs/experiments/2026-08-09_f18_window_host_exact_float_gate/README.md
Cross-review that caught the bad fixture:
AI_agent/logs/reviews/verdict/2026-08-09_f17_f18_crossreview_sol.md
"""
from __future__ import annotations

import pytest

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.window_host import window_host_claim_issues
from src.agent.geometry.modelling import SegmentLine2D

from tests.test_c2_b5_host_resolution import _context, _materialized, _resolve

# The real post-F-17 footprint: the envelope transform moves [0.12, 14.88] x
# [0.12, 7.88] onto [0, 15] x [0, 8], and THAT is the ring the failing windows
# were hosted on -- measured to be discriminating for the spans below.
POST_TRANSFORM_RING = [[0.0, 0.0], [15.0, 0.0], [15.0, 8.0], [0.0, 8.0]]
# Vertical host lines: with a ZERO-origin 8 m wall the round trip was exact for
# every span we measured, so that shape could not discriminate.  7.88 does.
# ⛔ This is an empirical property of (p1, L, span) together -- see
# test_zero_origin_power_of_two_scaling_round_trips_exactly for why it must NOT
# be generalised into "powers of two are always safe".
TALL_RING = [[0.0, 0.0], [15.0, 0.0], [15.0, 7.88], [0.0, 7.88]]


def _south(span):
    return _context(
        ring=POST_TRANSFORM_RING, span=span, facade="South",
        plan_geometry={"x_range_m": list(span), "y_range_m": [0.0, 0.1]},
    )


def _east(span):
    return _context(
        ring=TALL_RING, span=span, facade="East",
        plan_geometry={"x_range_m": [14.9, 15.0], "y_range_m": list(span)},
    )


def _claims(builder, span):
    geom, verified = builder(span)
    return _materialized(geom), _resolve(geom, verified)


def _line_geometry(issues):
    """Only the comparison this file governs.

    ``window_host_claim_issues`` also audits committed identity/audit rows,
    which a pre-commit fixture legitimately lacks; filtering keeps the lock
    pinned to the float comparison under test.
    """
    return [issue for issue in issues if issue.get("reason") == "line_geometry"]


def _round_trip_differs(claims) -> bool:
    """Does the OLD exact ``!=`` comparison actually fail on this fixture?

    This is the premise every lock in this file must prove about itself.  It
    replays exactly what ``window_host_claim_issues`` does for the world span,
    using only the resolution's own stored values.
    """
    res = claims.resolutions[0]
    line = SegmentLine2D(
        (res.segment_p1.x, res.segment_p1.y), (res.segment_p2.x, res.segment_p2.y),
    )
    dy = res.segment_p2.y - res.segment_p1.y
    q0 = line.point_at(res.segment_parameter_interval.lo)
    q1 = line.point_at(res.segment_parameter_interval.hi)
    projected = (q0[0], q1[0]) if dy == 0 else (q0[1], q1[1])
    lo, hi = sorted(projected)
    return (lo, hi) != (res.clamped_span.lo, res.clamped_span.hi)


def _tampered(claims, channel, delta):
    """Rebuild frozen claims with exactly one coordinate nudged by ``delta``.

    ``model_copy(update=...)`` rather than a dump/re-validate round trip: the
    claim models nest many tuple-typed fields and a JSON round trip would
    silently retype them all -- a tamper fixture must differ from the real
    claims in the one coordinate under test and nothing else.
    """
    res = claims.resolutions[0]
    if channel == "span":
        span = res.clamped_span
        patched = res.model_copy(
            update={"clamped_span": span.model_copy(update={"lo": span.lo + delta})},
        )
    elif channel == "endpoint":
        pts = res.clamped_plan_endpoints_p1_to_p2
        patched = res.model_copy(update={
            "clamped_plan_endpoints_p1_to_p2": (
                pts[0].model_copy(update={"x": pts[0].x + delta}), *pts[1:],
            ),
        })
    else:  # vertex z
        verts = res.clamped_vertices
        patched = res.model_copy(update={
            "clamped_vertices": (
                verts[0].model_copy(update={"z": verts[0].z + delta}), *verts[1:],
            ),
        })
    return claims.model_copy(update={"resolutions": (patched, *claims.resolutions[1:])})


# ---------------------------------------------------------------- the locks --
# Measured 2026-08-09: these four (builder, span) pairs are the ones where the
# exact comparison really fails.  Each test re-proves that before asserting the
# fix, so a future refactor that quietly makes a case non-discriminating fails
# LOUDLY here instead of silently becoming a no-op lock.

DISCRIMINATING = [
    (_south, (11.36, 13.76), "south-11.36-13.76-real-W_F1_SE"),
    (_south, (2.19, 5.55), "south-2.19-5.55"),
    (_east, (2.19, 5.55), "east-vertical-2.19-5.55"),
    (_east, (3.44, 4.64), "east-vertical-3.44-4.64"),
]


@pytest.mark.parametrize(
    "builder,span", [(b, s) for b, s, _ in DISCRIMINATING],
    ids=[i for _, _, i in DISCRIMINATING],
)
def test_binary64_round_trip_noise_is_not_tampering(builder, span):
    """Round-trip noise must pass; the fixture must prove it HAS noise first.

    Neuter direction: restore the exact ``!=`` comparisons in
    ``window_host_claim_issues`` -- every case here turns red, because the
    premise assertion guarantees each one exercises the noisy path.
    """
    geom, claims = _claims(builder, span)
    assert _round_trip_differs(claims), (
        "fixture premise broken: the exact comparison would have PASSED here, "
        "so this case cannot lock the tolerance fix (see module docstring)"
    )
    issues = window_host_claim_issues(
        geom, claims=claims, tolerances=load_core_tolerances(),
    )
    assert _line_geometry(issues) == [], issues


def test_zero_origin_power_of_two_scaling_round_trips_exactly():
    """Documents WHY fixture choice is not free -- with the correct scope.

    ⛔ NARROWED after sol cross-review round 2 (MINOR-1).  The first version of
    this test claimed "a power-of-two host line NEVER produces round-trip
    noise".  That is false: the real path is ``t = ((x - p1) * L) / L**2`` then
    ``p1 + t * L``, so the subtraction and the final addition can round even
    when the L scaling is exact.  sol's counterexample, re-verified here by
    hand: p1=2.6317878, L=8, x=7.877522392 round-trips to 7.8775223919999995
    (-8.88e-16, 1 ULP).

    What survives is the narrow, measured statement below: on a ZERO-origin
    8 m wall the spans we tried all round-trip bit-exactly, which is why the
    original East fixture could not discriminate no matter how awkward its
    decimals were.  ⛔ Do not restate this as a law about powers of two --
    discriminating power is a property of (p1, L, span) together, which is
    exactly why every lock in this file proves its own premise instead of
    reasoning about the arithmetic.
    """
    ring = [[0.0, 0.0], [15.0, 0.0], [15.0, 8.0], [0.0, 8.0]]
    geom, verified = _context(
        ring=ring, span=(2.19, 5.55), facade="East",
        plan_geometry={"x_range_m": [14.9, 15.0], "y_range_m": [2.19, 5.55]},
    )
    _, claims = _materialized(geom), _resolve(geom, verified)
    assert not _round_trip_differs(claims)


# ------------------------------------------------------- anti-tamper is kept --

def test_span_drift_far_above_epsilon_is_still_rejected():
    geom, claims = _claims(_south, (11.36, 13.76))
    tol = load_core_tolerances()
    issues = _line_geometry(window_host_claim_issues(
        geom, claims=_tampered(claims, "span", 1e-6), tolerances=tol))
    assert [issue["detail"] for issue in issues] == ["world span"], issues


def test_plan_endpoint_drift_far_above_epsilon_is_still_rejected():
    geom, claims = _claims(_south, (11.36, 13.76))
    tol = load_core_tolerances()
    issues = _line_geometry(window_host_claim_issues(
        geom, claims=_tampered(claims, "endpoint", 1e-6), tolerances=tol))
    assert [issue["detail"] for issue in issues] == ["p1->p2 endpoints"], issues


@pytest.mark.parametrize("delta", [1e-6, 1e-12], ids=["1e-6", "1e-12-exact"])
def test_vertex_z_is_compared_exactly(delta):
    """z gets NO tolerance (sol cross-review MINOR-2).

    ``window_verts_on_line`` copies ``z_interval`` straight into each vertex,
    so z never travels the round trip that produces F-18's noise.  Even a
    1e-12 m nudge -- far below the 1e-9 epsilon the xy channels use -- must
    still be rejected.  Neuter direction: give z a non-zero epsilon and the
    1e-12 case turns green.
    """
    geom, claims = _claims(_south, (11.36, 13.76))
    tol = load_core_tolerances()
    issues = _line_geometry(window_host_claim_issues(
        geom, claims=_tampered(claims, "vertex", delta), tolerances=tol))
    assert [issue["detail"] for issue in issues] == ["vertices"], issues


@pytest.mark.parametrize(
    "delta,rejected",
    [(5e-10, False), (5e-9, True)],
    ids=["just-inside-epsilon", "just-outside-epsilon"],
)
def test_span_tolerance_threshold_sits_at_b5_epsilon(delta, rejected):
    """Pin the threshold itself, not just "small passes / large fails".

    sol cross-review Q1: the 1e-6 reverse lock proves a big drift is still
    caught, but it does NOT prove the band was widened to exactly B5's 1e-9.
    These two cases straddle it.
    """
    geom, claims = _claims(_south, (11.36, 13.76))
    tol = load_core_tolerances()
    assert tol.window_host_span_epsilon_m == 1.0e-9
    issues = _line_geometry(window_host_claim_issues(
        geom, claims=_tampered(claims, "span", delta), tolerances=tol))
    assert bool(issues) is rejected, issues
