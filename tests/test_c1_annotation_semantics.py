"""MAJOR-C1 locks: nonzero reconcilable displacement is not annotation evidence."""
from __future__ import annotations

import pytest

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.envelope import (
    AuthoritativeEnvelope,
    EnvelopeAxisResolution,
    EnvelopeCandidate,
)
from src.agent.correction.envelope_transform import (
    annotation_basis_report,
    observe_envelope_annotation_basis,
)
from src.agent.correction.parse import ensure_corrected_geometry


def _geom():
    return ensure_corrected_geometry({
        "schema_version": "3", "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{
            "id": "f1", "name": "F1", "z_floor": 0, "ceiling_height": 3,
            "footprint": {"vertices": [[0, 0], [10, 0], [10, 8], [0, 8]]},
            "cells": [{"id": "room", "x": [0, 10], "y": [0, 8]}],
        }],
    })


def _envelope(displacement: float) -> AuthoritativeEnvelope:
    axes = {}
    for axis, lo, hi, facade in (("x", 0.0, 10.0, "South"), ("y", 0.0, 8.0, "West")):
        bounds = (lo - displacement, hi + displacement)
        candidate = EnvelopeCandidate(
            axis, bounds, hi - lo + 2 * displacement, "dimension", facade, f"src-{axis}",
            role="overall", confidence=0.95,
        )
        axes[axis] = EnvelopeAxisResolution(
            axis, "accepted", bounds, hi - lo + 2 * displacement, candidate, candidates=(candidate,),
        )
    return AuthoritativeEnvelope(axes)


def _pre_c1_basis(displacement: float, output_precision_m: float, reconcile_tol_m: float) -> str:
    """The removed partition, kept only to prove this fixture hits its bad band."""
    if displacement <= output_precision_m:
        return "axis_line_annotation"
    if displacement <= reconcile_tol_m:
        return "outer_skin_annotation"
    return "exceeds_tolerance"


@pytest.mark.parametrize("displacement", [0.02, 0.12, 0.29])
def test_reconcilable_nonzero_displacement_reports_number_without_annotation_claim(displacement):
    tol = load_core_tolerances()

    # Regression premise: every representative member of this range actually
    # hit the old ``outer_skin_annotation`` catch-all, not a vacuous fixture.
    assert _pre_c1_basis(displacement, tol.output_precision_m, tol.envelope_reconcile_tol_m) == "outer_skin_annotation"

    observations = observe_envelope_annotation_basis(_geom(), _envelope(displacement), tol)
    assert len(observations) == 4
    assert all(o.basis == "reconcilable_nonzero_displacement" for o in observations)
    assert all(o.displacement_m == pytest.approx(displacement) for o in observations)
    assert all("外包" not in o.basis_label and "外包" not in o.interpretation for o in observations)

    report = annotation_basis_report(observations, tol)
    assert "outer_skin_annotation" not in report["interpretation_rule"]
    assert "按外包标注" not in report["interpretation_rule"]
    assert "reconcilable_nonzero_displacement" in report["interpretation_rule"]
