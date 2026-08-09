"""F-17 离线复现：拿 run_2026-08-08_f16_e2e_verify 的真实 correction_geometry.json
走官方 finalize_correction_draw，复现 `cell RM1F_01: polygon edge 3 is not orthogonal`，
并把 envelope 组件 + 每个 cell 的 before/after 顶点全部打出来。

零 LLM 成本、只读、不改生产码（只在本进程内 monkeypatch 做观测）。
"""
import json
import sys
from pathlib import Path

REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))

RUN = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-08_f16_e2e_verify"
DRAW = RUN / "1_correction/correction_geometry.json"
READING = RUN / "0_reading"

from src.agent.correction import envelope_transform as ET
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import correction_target, parse_correction_draw
from src.agent.correction.window_sources import build_verified_window_inputs_from_run

# ---- 1. 载入落盘 draw；剥掉派生的 `floor`（= plan.md 登记的「重放姿势」问题） ----
payload = json.loads(DRAW.read_text())
popped = 0
for w in payload.get("windows", []):
    if w.pop("floor", None) is not None:
        popped += 1
print(f"[setup] 剥掉派生 floor 的窗数 = {popped}/{len(payload.get('windows', []))}")

target = correction_target("orthogonal_polygon")
geom = parse_correction_draw(payload, target)
print(f"[setup] parse OK · schema_version={geom.schema_version} · floors={len(geom.floors)} · windows={len(geom.windows)}")

tol = load_core_tolerances()
print(f"[setup] envelope_axis_attach_tol_m = {tol.envelope_axis_attach_tol_m}")
print(f"[setup] envelope_reconcile_tol_m   = {tol.envelope_reconcile_tol_m}")
print(f"[setup] min_edge_length_m          = {tol.min_edge_length_m}")

vwi = build_verified_window_inputs_from_run(
    producer_draw=geom, run_dir=RUN, reading_dir=READING,
)
print("[setup] verified_window_inputs 构造成功")

# ---- 2. 观测钩子：包住 _apply_components，逐组件打印 + 逐 cell before/after ----
_orig_apply = ET._apply_components


def _pts(cell):
    p = ET.cell_polygon_vertices(cell)
    if p is None:
        return [(cell.x[0], cell.y[0]), (cell.x[1], cell.y[0]),
                (cell.x[1], cell.y[1]), (cell.x[0], cell.y[1])]
    return [tuple(v) for v in p]


def traced_apply(candidate, components, tol):
    print("\n" + "=" * 78)
    print(f"[_apply_components] 组件数 = {len(components)}")
    for key, c in components.items():
        print(f"  · key={key!r}  axis={c.axis}  old={c.old_value}  new={c.new_value}")
        print(f"    intervals = {[(i.lo, i.hi) for i in c.intervals]}")
    print("=" * 78)

    snap_before = {
        (f.id, cell.id): _pts(cell) for f in candidate.floors for cell in f.cells
    }
    ring_before = {f.id: [tuple(v) for v in f.footprint.vertices] for f in candidate.floors}

    # 逐组件单步：把每个组件应用后的状态都留下来
    for key, comp in components.items():
        print(f"\n---- 应用组件 {key} ----")
        for floor in candidate.floors:
            for cell in floor.cells:
                before_pts = _pts(cell)
                mat = ET._materialize_axis_splits(ET._owner_points(cell), comp, tol)
                on = [ET._on_component(p, comp.axis, comp.old_value, comp.intervals, tol) for p in mat]
                if any(on) or len(mat) != len(before_pts):
                    print(f"  {floor.id}/{cell.id}")
                    print(f"    before      = {before_pts}")
                    print(f"    materialize = {[tuple(p) for p in mat]}  (插点 {len(mat) - len(before_pts)} 个)")
                    print(f"    on_component= {on}")

    try:
        return _orig_apply(candidate, components, tol)
    except ValueError as exc:
        print(f"\n[CRASH] {exc}")
        print("\n---- 崩溃时刻各 cell 的最终顶点 ----")
        for f in candidate.floors:
            for cell in f.cells:
                after = _pts(cell)
                has_poly = ET.cell_has_polygon(cell)
                if after != snap_before[(f.id, cell.id)]:
                    print(f"  {f.id}/{cell.id}  has_polygon={has_poly}")
                    print(f"    before = {snap_before[(f.id, cell.id)]}")
                    print(f"    after  = {after}")
                    closed = after + [after[0]]
                    for i, (a, b) in enumerate(zip(closed, closed[1:])):
                        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
                        ortho = ET_edge_axis_aligned(dx, dy)
                        mark = "" if ortho else "   <== 斜边"
                        print(f"      edge {i}: {a} -> {b}  dx={dx:.6f} dy={dy:.6f}{mark}")
        for f in candidate.floors:
            print(f"  {f.id} footprint before = {ring_before[f.id]}")
            print(f"  {f.id} footprint after  = {[tuple(v) for v in f.footprint.vertices]}")
        raise


from src.agent.correction.cell_geometry import edge_is_axis_aligned as ET_edge_axis_aligned

ET._apply_components = traced_apply

# ---- 3. 跑官方入口 ----
print("\n[run] finalize_correction_draw ...")
try:
    result = finalize_correction_draw(
        geom, vector_dir=READING, target=target, verified_window_inputs=vwi,
    )
    print("[run] 没崩 —— 未复现")
except Exception as exc:  # noqa: BLE001
    print(f"\n[run] 抛出 {type(exc).__name__}: {exc}")
