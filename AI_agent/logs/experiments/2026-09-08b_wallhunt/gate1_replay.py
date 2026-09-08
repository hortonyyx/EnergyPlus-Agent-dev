"""撞墙探针：拿 run_wallhunt 这次【真跑】产出的两份 projection_envelope，
离线复现 吸附 → assemble → as_drawn 窗输入 → finalize → gate①，
把 gate① 的每一条 fail/error 全部打出来。

⛔ 不重跑模型（用真跑落盘的产物），⛔ 不修改任何生产代码。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REPO = Path("/tmp/w1_flow_glm")
sys.path.insert(0, str(REPO))

from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.finalize import finalize_as_drawn_chain_geometry
from src.agent.correction.multifloor import (
    assemble_multifloor_geometry, derive_floor_ladder,
    read_plan_calibration_declaration, snap_footprints_to_reference)
from src.agent.correction.parse import correction_target
from src.agent.correction.projection_bridge import CorrectedGeometryProjectionEnvelopeV1
from src.agent.correction.window_sources import build_verified_window_inputs_as_drawn
from src.agent.execution.evidence_preflight import window_evidence_channel_split_debt
from src.validator.checks.correction import check_correction

RUN = REPO / "case_tests/e2e_tests/sm25-L_anchor/run_wallhunt"
RD = RUN / "0_reading"
PRODUCTS = {p.stem: p for p in sorted(RD.glob("*_view.json"))}
raw_artifacts = {k: v.read_bytes() for k, v in PRODUCTS.items()}
raw_manifest = (RUN / "_run/view_manifest.json").read_bytes()

geoms, decls = [], []
for fl, pid in (("floor_1", "1f_view"), ("floor_2", "2f_view")):
    env = CorrectedGeometryProjectionEnvelopeV1.model_validate_json(
        (RUN / "1_correction" / fl / "projection_envelope.json").read_bytes())
    geoms.append(env.geometry)
    decls.append(read_plan_calibration_declaration(
        json.loads(raw_artifacts[pid].decode()), input_id=pid))
print(f"载入两层真产物: cells={[len(g.floors[0].cells) for g in geoms]}")

snapped, account = snap_footprints_to_reference(geoms, decls)
print(f"吸附: applied={account.applied} "
      f"actions={[r.action for r in account.records]}")

elev = [adapt_as_drawn_elevation(raw_artifacts[i], input_id=i,
                                 facade_ref=i.split('_')[0])
        for i in ("East_view", "North_view", "South_view", "West_view")]
ladder = derive_floor_ladder(elev[0])
print(f"ladder: 级数={len(tuple(ladder))}")

geom = assemble_multifloor_geometry(ladder, snapped)
print(f"assemble ✅ floors={len(geom.floors)}")

vwi = build_verified_window_inputs_as_drawn(
    producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
    raw_reading_artifacts=raw_artifacts)
res = finalize_as_drawn_chain_geometry(
    geom, verified_window_inputs=vwi, target=correction_target("orthogonal_polygon"))
print(f"finalize ✅ facade_segments={len(res.geom.facade_segments)}")

rep = check_correction(
    res.geom, window_host_proof=res.window_host_claims,
    window_evidence=res.window_evidence_ledger, expected_zone_total=None,
    capability_profile="orthogonal_polygon", run_profile="exploratory",
    evidence_debt=window_evidence_channel_split_debt(chain_profile="exploratory"),
    verified_window_inputs=vwi)
print(f"\n=== gate①: passed={rep.passed} blocking={len(rep.blocking())} "
      f"results={len(rep.results)} ===")
for r in rep.results:
    if r.status.value in ("fail", "error"):
        print(f"  {r.status.value.upper():5} {r.check_id}: {r.message[:200]}")
