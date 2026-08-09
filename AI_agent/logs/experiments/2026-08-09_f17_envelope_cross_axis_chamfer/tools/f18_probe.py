import json, sys
from pathlib import Path
REPO = Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0, str(REPO))
RUN = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f17_e2e_verify"

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import correction_target, parse_correction_draw
from src.agent.correction.window_sources import build_verified_window_inputs_from_run
from src.agent.correction import window_host as WH

payload = json.loads((RUN / "1_correction/correction_geometry.json").read_text())
for w in payload.get("windows", []):
    w.pop("floor", None)
target = correction_target("orthogonal_polygon")
geom = parse_correction_draw(payload, target)
tol = load_core_tolerances()
vwi = build_verified_window_inputs_from_run(producer_draw=geom, run_dir=RUN, reading_dir=RUN/"0_reading")
res = finalize_correction_draw(geom, vector_dir=RUN/"0_reading", target=target, verified_window_inputs=vwi)
final = res.geom
print(f"[finalize] ✅ footprint = {final.footprint_x} x {final.footprint_y}")
print(f"[finalize] window_host_claims 有没有: {hasattr(res,'window_host_claims')} · facade_segments={len(final.facade_segments)}")

print("\n=== 在【最终几何】上重算 recompute_window_host_claims（= 写入侧做的事）===")
try:
    claims = WH.recompute_window_host_claims(final, verified_inputs=vwi, tolerances=tol)
    print("✅ 没抛异常 —— 与 flow 表现不一致，需再查")
except Exception as exc:
    print(f"⛔ {type(exc).__name__}: {exc}")
    rows = getattr(exc, "conflicts", None) or []
    print(f"  conflicts: {len(rows)} 条")
    for r in rows:
        d = r.model_dump(mode="json") if hasattr(r, "model_dump") else r
        print("   -", json.dumps({k: v for k, v in d.items() if k in
              ("window_id","conflict_type","claim_type","reason_unresolved","fallback_action","entity_id","evidence")},
              ensure_ascii=False)[:400])
    ctx = getattr(exc, "context", None)
    if ctx:
        print("  context.issues:")
        print(json.dumps(ctx, ensure_ascii=False, indent=2)[:2500])
