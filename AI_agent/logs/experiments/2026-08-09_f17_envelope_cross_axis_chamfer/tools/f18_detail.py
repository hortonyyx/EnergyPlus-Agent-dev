import json, sys
from pathlib import Path
REPO = Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0, str(REPO))
RUN = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f17_e2e_verify"

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import correction_target, parse_correction_draw
from src.agent.correction.window_sources import build_verified_window_inputs_from_run
from src.agent.correction.window_host import resolve_window_hosts
from src.agent.geometry.modelling import SegmentLine2D

target = correction_target("orthogonal_polygon"); tol = load_core_tolerances()
raw = json.loads((RUN / "1_correction/correction_geometry.json").read_text())
for w in raw.get("windows", []):
    w.pop("floor", None)
geom = parse_correction_draw(raw, target)
vwi = build_verified_window_inputs_from_run(producer_draw=geom, run_dir=RUN, reading_dir=RUN/"0_reading")
final = finalize_correction_draw(geom, vector_dir=RUN/"0_reading", target=target, verified_window_inputs=vwi).geom

cand = final.model_copy(deep=True)
for w in cand.windows:
    w.facade_segment_id = None
claims = resolve_window_hosts(cand, verified_inputs=vwi, tolerances=tol, commit=False)

BAD = {'W_F1_N','W_F1_NW','W_F1_SE','W_F2_NW','W_F2_SW','W_F2_W'}
print(f"{'window':<10} {'ok':<4} {'重算 (lo,hi)':<34} {'声明 clamped_span':<34} 差值")
print("-" * 110)
for r in claims.resolutions:
    line = SegmentLine2D((r.segment_p1.x, r.segment_p1.y), (r.segment_p2.x, r.segment_p2.y))
    dx = r.segment_p2.x - r.segment_p1.x; dy = r.segment_p2.y - r.segment_p1.y
    t = (r.segment_parameter_interval.lo, r.segment_parameter_interval.hi)
    q0, q1 = line.point_at(t[0]), line.point_at(t[1])
    proj = (q0[0], q1[0]) if dy == 0 else (q0[1], q1[1])
    lo, hi = (proj[0], proj[1]) if proj[0] < proj[1] else (proj[1], proj[0])
    dec = (r.clamped_span.lo, r.clamped_span.hi)
    ok = (lo, hi) == dec
    mark = "✅" if ok else "⛔"
    print(f"{r.window_id:<10} {mark:<4} {str((lo,hi)):<34} {str(dec):<34} "
          f"({lo-dec[0]:+.3e}, {hi-dec[1]:+.3e})")
