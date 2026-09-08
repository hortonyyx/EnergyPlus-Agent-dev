"""S3b probe: the corner-only promotion, read on the REAL chain products.

Two questions (dispatch 2026-09-08a §二 S3b):
  ① the reading — per floor, cell min edges / sub-threshold counts /
    vertex counts before (stored bytes) vs after (the production helper,
    which is exactly what the promoted producer now emits);
  ② the pathway — the S3 CASE B red (validate_final, 4.33 cm min cell
    edge) re-driven with the reduced cells: does gate① clear?

Run: cd /tmp/w1_flow_glm && PYTHONPATH=. python AI_agent/logs/experiments/2026-09-08a_w1_s3b_probe/run_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
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
    _corner_only_ring,
)
from src.agent.correction.window_sources import (
    build_verified_window_inputs_as_drawn,
)

PROBE = REPO / "AI_agent/logs/experiments/2026-09-07h_w1_t1_probe/newleg_probe"
OUT = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
MANIFEST = (
    REPO
    / "case_tests/e2e_tests/sm25-L_anchor/run_t1_probe2/_run/view_manifest.json"
)
PRODUCTS = {
    "1f_view": "sm25_1f_v2.json",
    "2f_view": "sm25_2f_v2.json",
    "East_view": "sm25_east_as_drawn.json",
    "North_view": "sm25_north_as_drawn.json",
    "South_view": "sm25_south_as_drawn.json",
    "West_view": "sm25_west_as_drawn.json",
}
TARGET = correction_target("orthogonal_polygon")


def _min_edge(ring) -> float:
    pts = [tuple(v) for v in ring]
    if pts and pts[0] == pts[-1]:
        pts = pts[:-1]
    return min(
        ((pts[i][0] - pts[(i + 1) % len(pts)][0]) ** 2
         + (pts[i][1] - pts[(i + 1) % len(pts)][1]) ** 2) ** 0.5
        for i in range(len(pts))
    )


def load_reduced(floor: str):
    """Stored envelope → the geometry the PROMOTED producer emits.  These
    artifacts predate BOTH reductions (T1 probe, before S3's :892 footprint
    call): footprint 94 vertices, cells 69/65/… — so BOTH ring families go
    through the production helper here, which is exactly what the promoted
    ``partition_lines`` emits for the same chain input."""
    env = CorrectedGeometryProjectionEnvelopeV1.model_validate_json(
        (PROBE / floor / "projection_envelope.json").read_text("utf-8")
    )
    geom = env.geometry.model_copy(deep=True)
    for fl in geom.floors:
        fl.footprint = fl.footprint.model_copy(
            update={"vertices": [list(v) for v in _corner_only_ring(
                [tuple(p) for p in fl.footprint.vertices])]}
        )
        fl.cells = [
            c.model_copy(
                update={"polygon": [list(v) for v in _corner_only_ring(
                    [tuple(p) for p in c.polygon])]}
            )
            for c in fl.cells
        ]
    return env, geom


def question_1_readings() -> None:
    print("=== ① the reading (real chain, 32 cells over two floors) ===")
    for floor in ("floor_1", "floor_2"):
        env, _ = load_reduced(floor)
        stored = [[tuple(p) for p in c.polygon]
                  for c in env.geometry.floors[0].cells]
        reduced = [_corner_only_ring(r) for r in stored]
        stored_edges = [_min_edge(r) for r in stored]
        reduced_edges = [_min_edge(r) for r in reduced]
        print(f"  {floor}: cells={len(stored)}")
        print(f"    min edge  stored={min(stored_edges) * 100:.2f} cm"
              f"  reduced={min(reduced_edges) * 100:.2f} cm")
        print(f"    <5cm  {sum(e < 0.05 for e in stored_edges)}/{len(stored)}"
              f" → {sum(e < 0.05 for e in reduced_edges)}/{len(stored)}"
              f"   <10cm  {sum(e < 0.10 for e in stored_edges)}/{len(stored)}"
              f" → {sum(e < 0.10 for e in reduced_edges)}/{len(stored)}")
        print(f"    vertices/cell  stored={sorted((len(r) for r in stored), reverse=True)[:6]}…"
              f"  reduced={sorted((len(r) for r in reduced), reverse=True)[:6]}…")


def question_2_pathway() -> None:
    print("\n=== ② the pathway: S3 CASE B re-driven with reduced cells ===")
    geoms = []
    for floor in ("floor_1", "floor_2"):
        _, geom = load_reduced(floor)
        geoms.append(geom)
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
    print(f"  assembled: floors={len(geom.floors)} "
          f"cells={sum(len(f.cells) for f in geom.floors)}")

    raw_manifest = MANIFEST.read_bytes()
    raw_artifacts = {
        input_id: (OUT / name).read_bytes()
        for input_id, name in PRODUCTS.items()
    }
    vwi = build_verified_window_inputs_as_drawn(
        producer_draw=geom,
        raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=raw_artifacts,
    )
    print(f"  vwi built: facts={len(vwi.inputs.elevation_direction_facts)} "
          f"links={len(vwi.inputs.claim_links)}")
    result = finalize_as_drawn_chain_geometry(
        geom, verified_window_inputs=vwi, target=TARGET
    )
    print(f"  finalize: claims={len(result.window_host_claims.resolutions)} "
          f"evidence={len(result.window_evidence_ledger.decisions)} "
          f"facade_segments={len(result.geom.facade_segments)}")

    from src.agent.execution.evidence_preflight import (
        window_evidence_channel_split_debt,
    )
    from src.validator.checks.correction import check_correction

    rep = check_correction(
        result.geom,
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


if __name__ == "__main__":
    question_1_readings()
    question_2_pathway()
