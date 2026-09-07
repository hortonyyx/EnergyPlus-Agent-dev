"""S3 probe: drive an ASSEMBLED as_drawn V3 through gate① (check_correction).

W-1 T3 rework S3 (dispatch 2026-09-07p): the T1/T2 execution's "weakest
spot" said the empty-proof-passes-gate① judgement was read off code + offline
adapters, never exercised with a real assembled V3.  This probe IS that
exercise, in TWO deliberately separated halves:

  CASE A (synthetic, clean): a synthetic two-storey square V3 through the
    FULL as_drawn finalize (build_verified_window_inputs_as_drawn →
    finalize_as_drawn_chain_geometry → check_correction).  Clean cells ⇒ any
    red here is about the EMPTY PROOF PATH itself — the dispatch's stop-and-
    report trigger asks exactly this question.

  CASE B (real T1 probe products): the two probe envelopes' geometry (each a
    DEGRADED chain projection — 16 dangling ends) through the same path.
    Reds here are CHAIN-PRODUCT QUALITY findings, recorded as-is; they do
    not answer the empty-proof question (that is CASE A's job).

Run: cd /tmp/w1_flow_glm && PYTHONPATH=. python AI_agent/logs/experiments/2026-09-07p_w1_s3_probe/run_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from src.agent.correction.evidence_adapters import (
    adapt_as_drawn_elevation,
    adapt_as_drawn_plan,
)
from src.agent.correction.finalize import finalize_as_drawn_chain_geometry
from src.agent.correction.multifloor import (
    assemble_multifloor_geometry,
    derive_floor_ladder,
    read_plan_calibration_declaration,
    snap_footprints_to_reference,
)
from src.agent.correction.parse import correction_target
from src.agent.correction.projection_bridge import (
    CorrectedGeometryProjectionEnvelopeV1,
)
from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.correction.window_sources import (
    build_verified_window_inputs_as_drawn,
)

PROBE = REPO / "AI_agent/logs/experiments/2026-09-07h_w1_t1_probe/newleg_probe"
OUT = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
MANIFEST = (
    REPO
    / "case_tests/e2e_tests/sm25-L_anchor/run_t1_probe2/_run/view_manifest.json"
)

# manifest input_id -> as_drawn product file in the 08-23 prototype dir
PRODUCTS = {
    "1f_view": "sm25_1f_v2.json",
    "2f_view": "sm25_2f_v2.json",
    "East_view": "sm25_east_as_drawn.json",
    "North_view": "sm25_north_as_drawn.json",
    "South_view": "sm25_south_as_drawn.json",
    "West_view": "sm25_west_as_drawn.json",
}

TARGET = correction_target("orthogonal_polygon")


def _gate1(geom, vwi, result) -> None:
    from src.agent.execution.evidence_preflight import (
        window_evidence_channel_split_debt,
    )
    from src.validator.checks.correction import check_correction

    rep = check_correction(
        geom,
        window_host_proof=result.window_host_claims,
        window_evidence=result.window_evidence_ledger,
        expected_zone_total=None,
        capability_profile="orthogonal_polygon",
        run_profile="exploratory",
        evidence_debt=window_evidence_channel_split_debt(
            chain_profile="exploratory"
        ),
        verified_window_inputs=vwi,
    )
    blocking = rep.blocking()
    print(f"  gate①: passed={rep.passed} blocking={len(blocking)} "
          f"results={len(rep.results)}")
    for r in rep.results:
        if r.status.value in ("fail", "error"):
            print(f"    {r.status.value.upper():5} {r.check_id}: {r.message[:150]}")


def _drive(tag: str, geom) -> bool:
    print(f"\n=== CASE {tag} ===")
    raw_manifest = MANIFEST.read_bytes()
    raw_artifacts = {
        input_id: (OUT / name).read_bytes()
        for input_id, name in PRODUCTS.items()
    }
    try:
        vwi = build_verified_window_inputs_as_drawn(
            producer_draw=geom,
            raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=raw_artifacts,
        )
        print(f"  vwi built: rows=0 facts="
              f"{len(vwi.inputs.elevation_direction_facts)} links="
              f"{len(vwi.inputs.claim_links)}")
        result = finalize_as_drawn_chain_geometry(
            geom, verified_window_inputs=vwi, target=TARGET
        )
        print(f"  finalize: claims={len(result.window_host_claims.resolutions)} "
              f"evidence={len(result.window_evidence_ledger.decisions)} "
              f"facade_segments={len(result.geom.facade_segments)}")
    except Exception as exc:
        print(f"  FINALIZE RED: {type(exc).__name__}: {str(exc)[:300]}")
        return False
    _gate1(result.geom, vwi, result)
    return True


def case_a_synthetic() -> None:
    """Clean two-storey square — the empty-proof question in isolation."""
    rect = [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]

    def floor(fid: str) -> CorrectedGeometryV3:
        return CorrectedGeometryV3(
            schema_version="3",
            footprint_x=[0.0, 6.0],
            footprint_y=[0.0, 4.0],
            floors=[{
                "id": fid, "name": fid, "z_floor": 999.0,
                "ceiling_height": 999.0,
                "footprint": {"vertices": rect},
                "cells": [{
                    "id": f"{fid}-c0", "x": [0.0, 6.0], "y": [0.0, 4.0],
                    "polygon": rect,
                }],
            }],
            windows=[],
            facade_segments=[],
        )

    east_raw = (OUT / PRODUCTS["East_view"]).read_bytes()
    evidence = adapt_as_drawn_elevation(
        east_raw, input_id="East_view", facade_ref="East"
    )
    ladder = derive_floor_ladder(evidence)
    geom = assemble_multifloor_geometry(ladder, [floor("1f"), floor("2f")])
    print(f"  synthetic assembled: floors={len(geom.floors)} cells="
          f"{sum(len(f.cells) for f in geom.floors)}")
    ok = _drive("A (synthetic clean → the empty-proof question)", geom)
    print("\nCASE A VERDICT:",
          "empty proof CLEARS gate① (no stop-and-report)" if ok else "see red")


def case_b_probe_products() -> None:
    """The real T1 probe chain products — quality findings land as-is."""
    geoms = []
    for floor in ("floor_1", "floor_2"):
        env = CorrectedGeometryProjectionEnvelopeV1.model_validate_json(
            (PROBE / floor / "projection_envelope.json").read_text("utf-8")
        )
        print(f"  {floor}: completion={env.completion} faces={env.face_count} "
              f"windows={len(env.geometry.windows)}")
        geoms.append(env.geometry)
    east_raw = (OUT / PRODUCTS["East_view"]).read_bytes()
    evidence = adapt_as_drawn_elevation(
        east_raw, input_id="East_view", facade_ref="East"
    )
    ladder = derive_floor_ladder(evidence)
    docs = {
        fid: json.loads((OUT / PRODUCTS[f"{fid}_view"]).read_bytes())
        for fid in ("1f", "2f")
    }
    decls = [
        read_plan_calibration_declaration(docs["1f"], input_id="1f_view"),
        read_plan_calibration_declaration(docs["2f"], input_id="2f_view"),
    ]
    geoms, account = snap_footprints_to_reference(geoms, decls)
    for rec in account.records:
        print(f"  snap {rec.floor_id}: {rec.action} "
              f"sym={max(rec.hausdorff_upper_to_reference_m, rec.hausdorff_reference_to_upper_m) * 1000:.1f}mm "
              f"tol={rec.tolerance_m * 1000:.1f}mm")
    geom = assemble_multifloor_geometry(ladder, geoms)
    print(f"  probe assembled: floors={len(geom.floors)} cells="
          f"{sum(len(f.cells) for f in geom.floors)} windows={len(geom.windows)}")
    _drive("B (real probe chain products)", geom)


if __name__ == "__main__":
    case_a_synthetic()
    case_b_probe_products()
