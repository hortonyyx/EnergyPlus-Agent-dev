"""F-17 逐组件单步观测：证明斜边诞生在「第二个正交组件」那一步。

打法 = 用官方 `_apply_components` 一次只喂一个组件，每步后打印 footprint 与 RM1F_01。
"""
import json
import sys
from pathlib import Path

REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))

RUN = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-08_f16_e2e_verify"

from src.agent.correction import envelope_transform as ET
from src.agent.correction.cell_geometry import edge_is_axis_aligned
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.parse import correction_target, parse_correction_draw

payload = json.loads((RUN / "1_correction/correction_geometry.json").read_text())
for w in payload.get("windows", []):
    w.pop("floor", None)
target = correction_target("orthogonal_polygon")
tol = load_core_tolerances()

# 四个 intent 已由复现脚本实测确定，这里直接用官方 builder 重建组件
from src.agent.correction.envelope_transform import EnvelopeMoveIntent, build_shared_axis_component

INTENTS = [
    ("x", 0.12, 0.0, "lo"),
    ("x", 14.88, 15.0, "hi"),
    ("y", 0.12, 0.0, "lo"),
    ("y", 7.88, 8.0, "hi"),
]


def fresh():
    return parse_correction_draw(json.loads(json.dumps(payload)), target)


def pts(cell):
    p = ET.cell_polygon_vertices(cell)
    if p is None:
        return [(cell.x[0], cell.y[0]), (cell.x[1], cell.y[0]),
                (cell.x[1], cell.y[1]), (cell.x[0], cell.y[1])]
    return [tuple(v) for v in p]


def diagonals(ring):
    closed = list(ring) + [ring[0]]
    out = []
    for i, (a, b) in enumerate(zip(closed, closed[1:])):
        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
        if not edge_is_axis_aligned(dx, dy):
            out.append((i, a, b, dx, dy))
    return out


geom = fresh()
intent_objs = []
for axis, old, new, side in INTENTS:
    i = EnvelopeMoveIntent(intent_id=f"{axis}_{side}", claim_kind="footprint_extent",
                           axis=axis, side=side, old_value=old, new_value=new,
                           source_facade="North", source_ids=("repro",))
    intent_objs.append(i)

print("=" * 78)
print("逐组件单步应用（每步用官方 _apply_components，一次一个组件）")
print("=" * 78)

for step, intent in enumerate(intent_objs, 1):
    # 组件必须在「当前」几何上重建，才等价于生产路径的一次性构造？
    # 不 —— 生产路径是在变换前一次性构造全部组件。这里如实照抄：用最初的 geom 构造。
    comp = build_shared_axis_component(fresh(), intent, tol)
    label = f"step {step}: axis={comp.axis} {comp.old_value} -> {comp.new_value} intervals={[(i.lo, i.hi) for i in comp.intervals]}"
    print(f"\n{label}")
    try:
        ET._apply_components(geom, {intent.intent_id: comp}, tol)
        crashed = None
    except ValueError as exc:
        crashed = str(exc)

    f1 = geom.floors[0]
    ring = [tuple(v) for v in f1.footprint.vertices]
    cell = next(c for c in f1.cells if c.id == "RM1F_01")
    print(f"  F1 footprint = {ring}")
    print(f"    斜边: {diagonals(ring) or '无'}")
    print(f"  RM1F_01      = {pts(cell)}")
    print(f"    斜边: {diagonals(pts(cell)) or '无'}")
    if crashed:
        print(f"  ⇒ 本步抛出: {crashed}")
        break
