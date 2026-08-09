"""F-18: the B5 claim self-check must compare binary64 round-trips on B5's own
epsilons, not with exact ``!=``.

Why this file exists (2026-08-09).  ``window_host_claim_issues`` re-derives a
resolution's world span / plan endpoints / vertices from that SAME resolution's
stored parameter interval and compares them to the stored values.  Both sides
describe one already-resolved wall, but they travel different arithmetic, so a
decimal that binary64 cannot represent exactly (11.36, 1.24, 2.19 ...) lands
1-4 ULP apart.  With an exact ``!=`` the check called that "tampering" and threw
``invariant_no_geometry_commit`` -- a bare raise that terminates the whole flow.
On the first real v3 product to reach this code (run_2026-08-09_f17_e2e_verify)
6 of 15 windows failed that way, with drifts <= 2e-15 m.

The whole repo missed it because every pre-existing B5 fixture uses spans like
0/4/10 -- values binary64 represents exactly, so the round-trip is bit-identical
and the gate never fires.  Hence the deliberate choice of awkward decimals and
an offset footprint origin below: this file's fixtures are shaped like real
production geometry, not like round numbers.

Full investigation:
AI_agent/logs/experiments/2026-08-09_f18_window_host_exact_float_gate/README.md
"""
from __future__ import annotations

import pytest

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.window_host import window_host_claim_issues

from tests.test_c2_b5_host_resolution import _context, _materialized, _resolve

# Real production shape: footprint inset off the origin by 0.12 m and a window
# span on decimals binary64 cannot hold exactly.  These are the literal values
# that failed in run_2026-08-09_f17_e2e_verify (window W_F1_SE).
INSET_RING = [[0.12, 0.12], [14.88, 0.12], [14.88, 7.88], [0.12, 7.88]]
AWKWARD_SPAN = (11.36, 13.76)


def _line_geometry(issues):
    """Only the comparison this file governs.

    ``window_host_claim_issues`` also audits committed identity/audit rows,
    which a pre-commit fixture legitimately lacks; filtering keeps the lock
    pinned to the float comparison under test instead of drifting into
    unrelated checks.
    """
    return [issue for issue in issues if issue.get("reason") == "line_geometry"]


def _tampered(claims, channel, delta):
    """Rebuild frozen claims with exactly one coordinate nudged by ``delta``.

    ``model_copy(update=...)`` rather than a dump/re-validate round trip: the
    claim models nest many tuple-typed fields, and a JSON round trip would
    silently retype them all -- the tamper fixture must differ from the real
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


def _claims_for(span):
    geom, verified = _context(
        ring=INSET_RING,
        span=span,
        plan_geometry={"x_range_m": list(span), "y_range_m": [0.12, 0.22]},
    )
    return _materialized(geom), _resolve(geom, verified)


@pytest.mark.parametrize(
    "span",
    [AWKWARD_SPAN, (1.24, 3.64), (2.19, 5.55), (6.3, 8.7)],
    ids=["11.36-13.76", "1.24-3.64", "2.19-5.55", "6.3-8.7"],
)
def test_binary64_round_trip_noise_is_not_tampering(span):
    """Real-shaped spans must PASS the self-check.

    Neuter direction: restore the exact ``!=`` comparisons in
    ``window_host_claim_issues``.

    ⛔ Measured 2026-08-09 -- only ``1.24-3.64`` and ``2.19-5.55`` actually turn
    red under that neuter on this fixture; ``11.36-13.76`` and ``6.3-8.7``
    happen to round-trip bit-exactly here.  Whether the noise appears depends
    on the exact arithmetic, so discriminating power lives in the SET, not in
    any single case.  ⛔ Do not prune this list to "the ones that matter" --
    that is how the lock silently loses its teeth.
    """
    geom, claims = _claims_for(span)
    issues = window_host_claim_issues(
        geom, claims=claims, tolerances=load_core_tolerances(),
    )
    assert _line_geometry(issues) == [], issues


def test_span_drift_far_above_epsilon_is_still_rejected():
    """Anti-tamper power must survive the tolerance change.

    1e-6 m is a thousand times B5's 1e-9 epsilon and still a thousand times
    below anything geometrically meaningful, so this asserts the gate was
    loosened by exactly the round-trip band and not by a hand-wave.
    """
    geom, claims = _claims_for(AWKWARD_SPAN)
    tol = load_core_tolerances()
    assert _line_geometry(window_host_claim_issues(geom, claims=claims, tolerances=tol)) == []

    issues = _line_geometry(window_host_claim_issues(
        geom, claims=_tampered(claims, "span", 1e-6), tolerances=tol))
    assert [issue["detail"] for issue in issues] == ["world span"], issues


def test_plan_endpoint_drift_far_above_epsilon_is_still_rejected():
    """Same guarantee for the p1->p2 endpoint comparison."""
    geom, claims = _claims_for(AWKWARD_SPAN)
    tol = load_core_tolerances()

    issues = _line_geometry(window_host_claim_issues(
        geom, claims=_tampered(claims, "endpoint", 1e-6), tolerances=tol))
    assert [issue["detail"] for issue in issues] == ["p1->p2 endpoints"], issues


def test_vertex_drift_far_above_epsilon_is_still_rejected():
    """Same guarantee for the clamped-vertex comparison (incl. the z channel)."""
    geom, claims = _claims_for(AWKWARD_SPAN)
    tol = load_core_tolerances()

    issues = _line_geometry(window_host_claim_issues(
        geom, claims=_tampered(claims, "vertex", 1e-6), tolerances=tol))
    assert [issue["detail"] for issue in issues] == ["vertices"], issues
