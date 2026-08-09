import json, sys
from pathlib import Path
REPO = Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0, str(REPO))
RUN = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f17_e2e_verify"

from src.agent.correction import envelope_transform as ET
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import correction_target, parse_correction_draw
from src.agent.correction.window_sources import build_verified_window_inputs_from_run
from src.agent.correction.envelope import extract_authoritative_envelope

payload = json.loads((RUN / "1_correction/correction_geometry.json").read_text())
n = sum(1 for w in payload.get("windows", []) if w.pop("floor", None) is not None)
print(f"[setup] 剥离派生 floor 的窗: {n}/{len(payload.get('windows',[]))}")
target = correction_target("orthogonal_polygon")
geom = parse_correction_draw(payload, target)
tol = load_core_tolerances()
print(f"[setup] parse OK · floors={len(geom.floors)} · windows={len(geom.windows)}")
print(f"[setup] footprint = {geom.footprint_x} x {geom.footprint_y}")

env = extract_authoritative_envelope(RUN / "0_reading", footprint=geom,
                                     footprint_tolerance_m=tol.envelope_reconcile_tol_m, tol=tol)
print("\n=== authoritative envelope ===")
for axis in ("x", "y"):
    r = env.axis(axis)
    print(f"  {axis}: {None if r is None else (r.status, r.bounds, r.reason)}")
intents = ET.resolve_envelope_move_intents(geom, env, tol)
print(f"\n=== resolve_envelope_move_intents ⇒ {len(intents)} 个 intent ===")
for i in intents:
    print(f"  {i.axis} {i.side} {i.old_value} -> {i.new_value}  ({i.claim_kind})")

calls = {"n": 0}
_orig = ET._apply_components
def traced(c, comps, t):
    calls["n"] += 1
    print(f"\n[TRACE] _apply_components 被调用，组件数={len(comps)}")
    for k, v in comps.items():
        print(f"   axis={v.axis} {v.old_value}->{v.new_value} intervals={[(a.lo,a.hi) for a in v.intervals]}")
    r = _orig(c, comps, t)
    print("[TRACE] _apply_components 返回，无异常")
    return r
ET._apply_components = traced

vwi = build_verified_window_inputs_from_run(producer_draw=geom, run_dir=RUN, reading_dir=RUN/"0_reading")
print("\n[run] finalize_correction_draw ...")
try:
    res = finalize_correction_draw(geom, vector_dir=RUN/"0_reading", target=target, verified_window_inputs=vwi)
    g = res.geom
    print(f"[run] ✅ 成功 · footprint = {g.footprint_x} x {g.footprint_y}")
    print(f"       conflicts={len(g.conflicts)} unsupported={len(g.unsupported)}")
except Exception as exc:
    print(f"[run] ⛔ {type(exc).__name__}: {exc}")
    for attr in ("conflicts", "context"):
        v = getattr(exc, attr, None)
        if v:
            print(f"  --- {attr} ---")
            try:
                rows = [r.model_dump(mode='json') if hasattr(r,'model_dump') else r for r in v] if isinstance(v,(list,tuple)) else v
                print(json.dumps(rows, ensure_ascii=False, indent=2)[:3000])
            except Exception as e:
                print("   (dump 失败)", e)
print(f"\n[结论] _apply_components 调用次数 = {calls['n']}")
