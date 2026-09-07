"""W-1 T3 rework S3 — the as_drawn leg's finalize, wired and LOCKED.

WHAT THIS FILE LOCKS (dispatch 2026-09-07p S3 / wip-review BLK-B):

1. the LEGAL EMPTY SET of window sources + the empty-but-verified window
   accounts CLEARS gate① on a clean assembled v3 — the T1/T2 execution's
   "weakest spot" said this was read off code, never exercised; the S3 probe
   (2026-09-07p_w1_s3_probe) measured it on real manifest/product bytes and
   this file makes that reading a permanent rule;
2. ``finalize_as_drawn_chain_geometry`` runs Vg on the chain-final ring (the
   bridge emits ``facade_segments=[]`` and feature-state derivation refuses
   an unpopulated list — the finalize half is NOT legacy-only);
3. the filed channel-split debt (S1) rides along as a FLAG, ⛔ never a block,
   under the exploratory chain profile.

⚠️ Known chain-quality boundary (probe CASE B, recorded not locked): a
DEGRADED chain projection whose cells carry sub-minimum edges reds
``validate_final_corrected_geometry`` — the same ruler the legacy leg applies.
That is a chain-product finding, ⛔ not an empty-proof finding.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.finalize import finalize_as_drawn_chain_geometry
from src.agent.correction.multifloor import (
    assemble_multifloor_geometry,
    derive_floor_ladder,
)
from src.agent.correction.parse import correction_target
from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.correction.window_sources import (
    build_verified_window_inputs_as_drawn,
)
from src.agent.execution.evidence_preflight import (
    window_evidence_channel_split_debt,
)
from src.validator.checks.correction import check_correction

REPO = Path(__file__).resolve().parents[1]
_AS_DRAWN_OUT = (
    REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
# the frozen sm25 view manifest (case provision output) — REAL bytes, so the
# direction-fact derivation runs the production path, not a synthetic stub
_MANIFEST = (
    REPO
    / "case_tests/e2e_tests/sm25-L_anchor/run_t1_probe2/_run/view_manifest.json"
)
_PRODUCTS = {
    "1f_view": "sm25_1f_v2.json",
    "2f_view": "sm25_2f_v2.json",
    "East_view": "sm25_east_as_drawn.json",
    "North_view": "sm25_north_as_drawn.json",
    "South_view": "sm25_south_as_drawn.json",
    "West_view": "sm25_west_as_drawn.json",
}

_RECT = [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]
_TARGET = correction_target("orthogonal_polygon")


def _square_floor(floor_id: str) -> CorrectedGeometryV3:
    return CorrectedGeometryV3(
        schema_version="3",
        footprint_x=[0.0, 6.0],
        footprint_y=[0.0, 4.0],
        floors=[
            {
                "id": floor_id,
                "name": floor_id,
                "z_floor": 999.0,
                "ceiling_height": 999.0,
                "footprint": {"vertices": _RECT},
                "cells": [
                    {
                        "id": f"{floor_id}-c0",
                        "x": [0.0, 6.0],
                        "y": [0.0, 4.0],
                        "polygon": _RECT,
                    }
                ],
            }
        ],
        windows=[],
        facade_segments=[],
    )


def _assembled_two_storey() -> CorrectedGeometryV3:
    evidence = adapt_as_drawn_elevation(
        (_AS_DRAWN_OUT / _PRODUCTS["East_view"]).read_bytes(),
        input_id="East_view",
        facade_ref="East",
    )
    ladder = derive_floor_ladder(evidence)
    assert len(ladder) == 2
    return assemble_multifloor_geometry(ladder, [_square_floor("1f"), _square_floor("2f")])


def _raw_artifacts() -> dict[str, bytes]:
    return {
        input_id: (_AS_DRAWN_OUT / name).read_bytes()
        for input_id, name in _PRODUCTS.items()
    }


def test_empty_window_set_clears_gate1_on_a_clean_assembled_v3():
    """Lock ① (S3 / BLK-B): the whole as_drawn finalize path — legal empty
    window sources, empty-but-verified host accounts, Vg facade segments —
    ends in a gate① report with ZERO blocking findings.  This is the
    stop-and-report question answered NO, permanently."""
    geom = _assembled_two_storey()
    vwi = build_verified_window_inputs_as_drawn(
        producer_draw=geom,
        raw_view_manifest_bytes=_MANIFEST.read_bytes(),
        raw_reading_artifacts=_raw_artifacts(),
    )
    result = finalize_as_drawn_chain_geometry(
        geom, verified_window_inputs=vwi, target=_TARGET
    )
    # the accounts exist and are EMPTY, matching the producer's windows=[]
    assert result.window_host_claims is not None
    assert result.window_host_claims.resolutions == ()
    assert result.window_evidence_ledger is not None
    assert result.window_evidence_ledger.decisions == ()
    rep = check_correction(
        result.geom,
        window_host_proof=result.window_host_claims,
        window_evidence=result.window_evidence_ledger,
        capability_profile="orthogonal_polygon",
        run_profile="exploratory",
        evidence_debt=window_evidence_channel_split_debt(
            chain_profile="exploratory"
        ),
        verified_window_inputs=vwi,
    )
    assert not rep.blocking(), [
        (r.check_id, r.message) for r in rep.blocking()
    ]


def test_finalize_runs_vg_on_the_chain_final_ring():
    """Lock ②: the bridge emits ``facade_segments=[]``; the as_drawn finalize
    is what populates them (Vg's rule — the ONLY writer), and feature-state
    derivation (which refuses an unpopulated list) runs inside it."""
    geom = _assembled_two_storey()
    assert geom.facade_segments == []  # the bridge's starting point
    vwi = build_verified_window_inputs_as_drawn(
        producer_draw=geom,
        raw_view_manifest_bytes=_MANIFEST.read_bytes(),
        raw_reading_artifacts=_raw_artifacts(),
    )
    result = finalize_as_drawn_chain_geometry(
        geom, verified_window_inputs=vwi, target=_TARGET
    )
    assert result.geom.facade_segments  # Vg wrote on the chain-final ring
    assert result.feature_state_claims
    assert result.prepared_candidate_identity is not None


def test_channel_split_debt_flags_but_never_blocks_gate1():
    """Lock ③: the S1 debt rides along to gate① as recorded FLAG evidence —
    present in the report's findings, absent from the blocking set (that is
    the STRICT profile's job, held at the wiring, not gate①'s)."""
    geom = _assembled_two_storey()
    vwi = build_verified_window_inputs_as_drawn(
        producer_draw=geom,
        raw_view_manifest_bytes=_MANIFEST.read_bytes(),
        raw_reading_artifacts=_raw_artifacts(),
    )
    result = finalize_as_drawn_chain_geometry(
        geom, verified_window_inputs=vwi, target=_TARGET
    )
    rep = check_correction(
        result.geom,
        window_host_proof=result.window_host_claims,
        window_evidence=result.window_evidence_ledger,
        capability_profile="orthogonal_polygon",
        run_profile="exploratory",
        evidence_debt=window_evidence_channel_split_debt(
            chain_profile="exploratory"
        ),
        verified_window_inputs=vwi,
    )
    by_id = {r.check_id: r for r in rep.results}
    # the debt IS in the report (recorded, ⛔ never silent)...
    assert "correction.evidence_debt_coverage" in by_id
    # ...and out of the blocking set (FLAG under the exploratory profile)
    assert not rep.blocking()


def test_finalize_requires_v3():
    """The as_drawn finalize is a v3-only transaction: a v1 target (the
    legacy rectangular profile's schema) is a loud ``ValueError`` refusal,
    ⛔ not a legacy-style silent passthrough."""
    geom = _assembled_two_storey()
    vwi = build_verified_window_inputs_as_drawn(
        producer_draw=geom,
        raw_view_manifest_bytes=_MANIFEST.read_bytes(),
        raw_reading_artifacts=_raw_artifacts(),
    )
    with pytest.raises(ValueError):
        finalize_as_drawn_chain_geometry(
            geom,
            verified_window_inputs=vwi,
            target=correction_target("rectangular"),  # schema_version "1"
        )
