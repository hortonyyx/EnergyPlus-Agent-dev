"""撞墙探针 · 下游段：把 1_correction 真跑产出的几何【当输入喂给】2/3/4 段，
逐段 try/except，⭐ 一堵墙不挡住后面的墙 —— 一次把清单撞全。

⛔ 不 neuter 任何锁、不改生产代码；这是 memory feed-the-answer-in-to-test-the-code-alone
   的标准用法：真实产物没行使过的能力 = 缺陷躺着的地方。
"""
from __future__ import annotations
import json, sys, traceback
from pathlib import Path
REPO = Path("/tmp/w1_flow_glm"); sys.path.insert(0, str(REPO))

from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.finalize import finalize_as_drawn_chain_geometry
from src.agent.correction.multifloor import (
    assemble_multifloor_geometry, derive_floor_ladder,
    read_plan_calibration_declaration, snap_footprints_to_reference)
from src.agent.correction.parse import correction_target
from src.agent.correction.projection_bridge import CorrectedGeometryProjectionEnvelopeV1
from src.agent.correction.window_sources import build_verified_window_inputs_as_drawn

RUN = REPO / "case_tests/e2e_tests/sm25-L_anchor/run_wallhunt"
raw = {p.stem: p.read_bytes() for p in sorted((RUN / "0_reading").glob("*_view.json"))}

geoms, decls = [], []
for fl, pid in (("floor_1", "1f_view"), ("floor_2", "2f_view")):
    env = CorrectedGeometryProjectionEnvelopeV1.model_validate_json(
        (RUN / "1_correction" / fl / "projection_envelope.json").read_bytes())
    geoms.append(env.geometry)
    decls.append(read_plan_calibration_declaration(json.loads(raw[pid]), input_id=pid))
snapped, _ = snap_footprints_to_reference(geoms, decls)
ladder = derive_floor_ladder(adapt_as_drawn_elevation(
    raw["East_view"], input_id="East_view", facade_ref="East"))
geom = assemble_multifloor_geometry(ladder, snapped)
vwi = build_verified_window_inputs_as_drawn(
    producer_draw=geom, raw_view_manifest_bytes=(RUN / "_run/view_manifest.json").read_bytes(),
    raw_reading_artifacts=raw)
res = finalize_as_drawn_chain_geometry(
    geom, verified_window_inputs=vwi, target=correction_target("orthogonal_polygon"))
G, PROOF = res.geom, res.window_host_claims
print(f"喂入: floors={len(G.floors)} cells={[len(f.cells) for f in G.floors]} "
      f"windows={len(G.windows)} facade_segments={len(G.facade_segments)}\n")

CP = "orthogonal_polygon"; RP = "exploratory"
def show(tag, rep):
    bad = [r for r in rep.results if r.status.value in ("fail", "error")]
    print(f"  {tag}: passed={rep.passed} blocking={len(rep.blocking())} results={len(rep.results)}")
    for r in bad: print(f"    {r.status.value.upper():5} {r.check_id}: {r.message[:180]}")

# ── 2_modelling ──
bg = None
print("=== 2_modelling ===")
try:
    from src.agent.pipeline import materialize_kernel_geometry
    from src.validator.checks.kernel import check_kernel
    s2 = RUN / "2_modelling"; s2.mkdir(parents=True, exist_ok=True)
    bgk, issues = materialize_kernel_geometry(G, s2, capability_profile=CP,
                                              window_host_proof=None)
    if bgk is None:
        print(f"  ⛔ kernel build failed: {'; '.join(issues)[:400]}")
    else:
        show("check_kernel", check_kernel(bgk, window_host_proof=None,
             capability_profile=CP, interzone_issues=issues, run_profile=RP))
except Exception:
    print("  ⛔ 抛异常:"); traceback.print_exc(limit=3)

# ── 3_split_pairing ──
print("\n=== 3_split_pairing ===")
zone_specs = used = zone_names = None
try:
    from src.agent.geometry import build_geometry
    from src.agent.geometry.specs import serialize_geometry
    bg = build_geometry(G, capability_profile=CP, window_host_proof=None)
    zone_specs, surf, fen, used = serialize_geometry(bg)
    zone_names = list(dict.fromkeys(bg.zones))
    print(f"  ✅ zones={len(zone_specs)} surfaces={len(surf)} fen={len(fen)} "
          f"constructions={len(used)}")
except Exception:
    print("  ⛔ 抛异常:"); traceback.print_exc(limit=3)

# ── 4_mep ──
print("\n=== 4_mep ===")
if zone_specs is None:
    print("  ⏭ 跳过：3 段没产出 zone_specs（上一堵墙的下游）")
else:
    try:
        from src.agent.pipeline import run_mep
        from src.validator.checks.mep import check_mep
        td = next((RUN.parent / "case_data").glob("testdata_prompt.json"))
        s4 = RUN / "4_mep"; s4.mkdir(parents=True, exist_ok=True)
        mep = run_mep(zone_specs, used, td.read_text(encoding="utf-8"),
                      zone_names=zone_names, out_dir=s4, feedback=None)
        show("check_mep", check_mep(mep.model_dump(), used_constructions=used,
             zone_names=zone_names, capability_profile=CP, run_profile=RP))
    except Exception:
        print("  ⛔ 抛异常:"); traceback.print_exc(limit=3)
