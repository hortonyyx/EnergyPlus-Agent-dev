import json, sys
from pathlib import Path
REPO = Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0, str(REPO))
RUN = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f17_e2e_verify"

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import correction_target, parse_correction_draw
from src.agent.correction.window_sources import build_verified_window_inputs_from_run
from src.agent.correction import window_host as WH
from src.agent.correction import envelope_transform as ET

target = correction_target("orthogonal_polygon"); tol = load_core_tolerances()
raw = json.loads((RUN / "1_correction/correction_geometry.json").read_text())

def fresh():
    p = json.loads(json.dumps(raw))
    for w in p.get("windows", []):
        w.pop("floor", None)
    return parse_correction_draw(p, target)

def trial(tag, suppress_intents):
    geom = fresh()
    vwi = build_verified_window_inputs_from_run(producer_draw=geom, run_dir=RUN, reading_dir=RUN/"0_reading")
    orig = ET.resolve_envelope_move_intents
    if suppress_intents:
        ET.resolve_envelope_move_intents = lambda *a, **k: ()
    try:
        res = finalize_correction_draw(geom, vector_dir=RUN/"0_reading", target=target, verified_window_inputs=vwi)
        g = res.geom
        print(f"\n### {tag}")
        print(f"  finalize ✅ footprint = {g.footprint_x} x {g.footprint_y} · facade_segments={len(g.facade_segments)}")
        try:
            WH.recompute_window_host_claims(g, verified_inputs=vwi, tolerances=tol)
            print("  写入侧 recompute_window_host_claims ✅ 通过")
        except Exception as e:
            rows = getattr(e, "conflicts", []) or []
            ctx = (getattr(e, "context", {}) or {}).get("issues", [])
            print(f"  写入侧 recompute ⛔ {type(e).__name__} · conflicts={len(rows)} · issues={len(ctx)}")
            print(f"     窗: {sorted({i['window_id'] for i in ctx})}")
            print(f"     reason: {sorted({i['reason'] for i in ctx})} · detail: {sorted({i['detail'] for i in ctx})}")
    except Exception as e:
        print(f"\n### {tag}\n  finalize ⛔ {type(e).__name__}: {str(e)[:200]}")
    finally:
        ET.resolve_envelope_move_intents = orig

trial("A · 正常（envelope 变换生效，4 个跨轴 intent）", suppress_intents=False)
trial("B · 对照（抑制 intent ⇒ 不做 envelope 变换）", suppress_intents=True)
