"""F-17 组合实测 + 修法方向探针。

A. 组合矩阵：单轴组件（同轴 1 个 / 同轴 2 个）vs 跨轴组件 —— 斜边只在跨轴时出现？
B. 反事实探针：改成「在变换前的原始几何上一次性定位、再统一移动」，斜边是否归零？
   ⛔ 这是方向验证，不是提交修法。
"""
import itertools
import json
import sys
from pathlib import Path

REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))

RUN = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-08_f16_e2e_verify"

from src.agent.correction import envelope_transform as ET
from src.agent.correction.cell_geometry import edge_is_axis_aligned
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.envelope_transform import EnvelopeMoveIntent, build_shared_axis_component
from src.agent.correction.parse import correction_target, parse_correction_draw

payload = json.loads((RUN / "1_correction/correction_geometry.json").read_text())
for w in payload.get("windows", []):
    w.pop("floor", None)
target = correction_target("orthogonal_polygon")
tol = load_core_tolerances()

INTENTS = {
    "x-lo": ("x", 0.12, 0.0, "lo"),
    "x-hi": ("x", 14.88, 15.0, "hi"),
    "y-lo": ("y", 0.12, 0.0, "lo"),
    "y-hi": ("y", 7.88, 8.0, "hi"),
}


def fresh():
    return parse_correction_draw(json.loads(json.dumps(payload)), target)


def make_comp(name):
    axis, old, new, side = INTENTS[name]
    intent = EnvelopeMoveIntent(intent_id=name, claim_kind="footprint_extent", axis=axis,
                               side=side, old_value=old, new_value=new,
                               source_facade="North", source_ids=("repro",))
    return intent, build_shared_axis_component(fresh(), intent, tol)


def pts(cell):
    p = ET.cell_polygon_vertices(cell)
    if p is None:
        return [(cell.x[0], cell.y[0]), (cell.x[1], cell.y[0]),
                (cell.x[1], cell.y[1]), (cell.x[0], cell.y[1])]
    return [tuple(v) for v in p]


def count_diagonals(ring):
    closed = list(ring) + [ring[0]]
    return sum(1 for a, b in zip(closed, closed[1:])
               if not edge_is_axis_aligned(abs(b[0] - a[0]), abs(b[1] - a[1])))


def survey(geom):
    n = 0
    for f in geom.floors:
        n += count_diagonals([tuple(v) for v in f.footprint.vertices])
        for c in f.cells:
            n += count_diagonals(pts(c))
    return n


print("=" * 78)
print("A. 组合矩阵：哪些组件组合会产生斜边")
print("=" * 78)
print(f"{'组合':<26} {'跨轴?':<7} {'斜边总数':<9} 结果")
print("-" * 78)
for size in (1, 2, 3, 4):
    for combo in itertools.combinations(INTENTS, size):
        geom = fresh()
        comps = {}
        for name in combo:
            intent, comp = make_comp(name)
            comps[name] = comp
        axes = {INTENTS[n][0] for n in combo}
        cross = "是" if len(axes) > 1 else "否"
        try:
            ET._apply_components(geom, comps, tol)
            note = "OK"
        except ValueError as exc:
            note = f"ValueError: {exc}"
        print(f"{'+'.join(combo):<26} {cross:<7} {survey(geom):<9} {note}")

print()
print("=" * 78)
print("B. 反事实探针：原始几何上一次性定位 + 统一移动")
print("=" * 78)


def apply_all_at_once(geom, comps, tol):
    """在移动任何东西之前，用原始坐标判定每个顶点属于哪些组件，然后一次性移动。"""
    def relocate(points):
        out = []
        for point in points:
            values = list(point)
            new = list(values)
            for comp in comps.values():
                if ET._on_component(values, comp.axis, comp.old_value, comp.intervals, tol):
                    new[0 if comp.axis == "x" else 1] = comp.new_value
            out.append(tuple(new))
        return out

    for floor in geom.floors:
        floor.footprint = type(floor.footprint)(vertices=relocate(floor.footprint.vertices))
        for cell in floor.cells:
            original_polygon = ET.cell_has_polygon(cell)
            updated = relocate(ET._owner_points(cell))
            xs, ys = {p[0] for p in updated}, {p[1] for p in updated}
            is_rect = len(updated) == 4 and len(xs) == 2 and len(ys) == 2
            if original_polygon or not is_rect:
                ET.set_cell_polygon_vertices(cell, updated)
            else:
                cell.x, cell.y = [min(xs), max(xs)], [min(ys), max(ys)]


geom = fresh()
comps = {name: make_comp(name)[1] for name in INTENTS}
apply_all_at_once(geom, comps, tol)
print(f"斜边总数 = {survey(geom)}")
f1 = geom.floors[0]
print(f"F1 footprint = {[tuple(v) for v in f1.footprint.vertices]}")
for c in f1.cells:
    print(f"  {c.id:<10} {pts(c)}")
try:
    for f in geom.floors:
        for c in f.cells:
            if ET.cell_has_polygon(c):
                ET.validate_cell_polygon(c, min_edge_length_m=tol.min_edge_length_m)
    print("⇒ validate_cell_polygon 全部通过")
except ValueError as exc:
    print(f"⇒ 仍失败: {exc}")
