"""F-17 修法探针（三阶段版）：验证要写进派工单的算法本身是对的。

算法 = 把「边移边判」拆成三相：
  相 1 materialize：对每个组件依次插点，**此阶段不移动任何点** ⇒ 坐标全是原始坐标；
  相 2 定位+移动：每个顶点对**全部**组件求 _on_component（坐标仍是原始的），
        命中哪个就改哪个分量，一个角点可同时被 x 与 y 组件命中；
  相 3 规范化：沿用 _canonical_open_ccw / rect 回落。

两格实测：A = 真实 sm21 产物；B = L 形 + 跨轴（报告里标为「未覆盖」的那一格）。
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
from src.agent.correction.envelope_transform import EnvelopeMoveIntent, build_shared_axis_component
from src.agent.correction.parse import correction_target, parse_correction_draw, ensure_corrected_geometry
from src.agent.correction.schema import FootprintRing

tol = load_core_tolerances()


def pts(cell):
    p = ET.cell_polygon_vertices(cell)
    if p is None:
        return [(cell.x[0], cell.y[0]), (cell.x[1], cell.y[0]),
                (cell.x[1], cell.y[1]), (cell.x[0], cell.y[1])]
    return [tuple(v) for v in p]


def diag(ring):
    closed = list(ring) + [ring[0]]
    return [(i, a, b) for i, (a, b) in enumerate(zip(closed, closed[1:]))
            if not edge_is_axis_aligned(abs(b[0] - a[0]), abs(b[1] - a[1]))]


def apply_components_fixed(candidate, components, tol):
    """三阶段实现。返回与原函数同形的 moved 审计字典。"""
    moved = {"floor_vertex_refs": [], "cell_vertex_refs": [],
             "window_span_refs": [], "promoted_rect_cells_to_polygon": []}
    comps = list(components.values())

    def materialize_all(points):
        # 相 1：只插点、不移动 ⇒ 每个组件看到的都还是原始坐标
        for comp in comps:
            points = ET._materialize_axis_splits(points, comp, tol)
        return points

    def relocate(points, ref_prefix, bucket):
        # 相 2：用原始坐标对全部组件定位，命中的分量一起改
        out = []
        for n, point in enumerate(points):
            values = list(point)
            new = list(values)
            for comp in comps:
                if ET._on_component(values, comp.axis, comp.old_value, comp.intervals, tol):
                    new[0 if comp.axis == "x" else 1] = comp.new_value
                    if ref_prefix is not None:
                        moved[bucket].append(f"{ref_prefix}:{n}")
            out.append(tuple(new))
        return out

    for floor in candidate.floors:
        ring = relocate(materialize_all(floor.footprint.vertices), floor.id, "floor_vertex_refs")
        floor.footprint = FootprintRing(vertices=ET._canonical_open_ccw(ring, tol))
        for cell in floor.cells:
            original_polygon = ET.cell_has_polygon(cell)
            before = [tuple(p) for p in ET._owner_points(cell)]
            updated = relocate(materialize_all(ET._owner_points(cell)),
                               f"{floor.id}:{cell.id}", "cell_vertex_refs")
            if [tuple(p) for p in updated] == before:
                continue
            updated = ET._canonical_open_ccw(updated, tol)
            xs, ys = {p[0] for p in updated}, {p[1] for p in updated}
            is_rect = len(updated) == 4 and len(xs) == 2 and len(ys) == 2
            if original_polygon or not is_rect:
                if not original_polygon:
                    moved["promoted_rect_cells_to_polygon"].append(cell.id)
                ET.set_cell_polygon_vertices(cell, updated)
            else:
                cell.x, cell.y = [min(xs), max(xs)], [min(ys), max(ys)]
    for floor in candidate.floors:
        for cell in floor.cells:
            if ET.cell_has_polygon(cell):
                ET.validate_cell_polygon(cell, min_edge_length_m=tol.min_edge_length_m)
    bbox = ET.footprint_bbox(candidate)
    candidate.footprint_x, candidate.footprint_y = list(bbox[0]), list(bbox[1])
    return moved


def mk(axis, old, new, side, name):
    return EnvelopeMoveIntent(intent_id=name, claim_kind="footprint_extent", axis=axis,
                              side=side, old_value=old, new_value=new,
                              source_facade="North", source_ids=("probe",))


def report(tag, geom, expect_ring=None):
    ok = True
    for f in geom.floors:
        ring = [tuple(v) for v in f.footprint.vertices]
        d = diag(ring)
        print(f"  {f.id} footprint = {ring}")
        if d:
            print(f"    ⛔ 斜边 {d}"); ok = False
        for c in f.cells:
            dc = diag(pts(c))
            print(f"    {c.id:<12} {pts(c)}" + ("   ⛔ 斜边" if dc else ""))
            if dc: ok = False
    print(f"  ⇒ {tag}: {'✅ 全正交' if ok else '⛔ 有斜边'}")
    return ok


# ---------------- 格 A：真实 sm21 产物 ----------------
print("=" * 78)
print("格 A · 真实 sm21 产物（矩形 footprint，四条边全要动）")
print("=" * 78)
payload = json.loads((RUN / "1_correction/correction_geometry.json").read_text())
for w in payload.get("windows", []):
    w.pop("floor", None)
target = correction_target("orthogonal_polygon")


def fresh_a():
    return parse_correction_draw(json.loads(json.dumps(payload)), target)


intents_a = [mk("x", 0.12, 0.0, "lo", "x-lo"), mk("x", 14.88, 15.0, "hi", "x-hi"),
             mk("y", 0.12, 0.0, "lo", "y-lo"), mk("y", 7.88, 8.0, "hi", "y-hi")]
comps_a = {i.intent_id: build_shared_axis_component(fresh_a(), i, tol) for i in intents_a}

print("\n-- 现行实现 --")
g = fresh_a()
try:
    ET._apply_components(g, comps_a, tol); print("  没抛异常（意外）")
except ValueError as e:
    print(f"  ⛔ {e}")

print("\n-- 三阶段修法 --")
g = fresh_a()
moved = apply_components_fixed(g, comps_a, tol)
ok_a = report("格 A", g)
print(f"  moved 审计: floor_vertex_refs={len(moved['floor_vertex_refs'])} "
      f"cell_vertex_refs={len(moved['cell_vertex_refs'])} "
      f"promoted={moved['promoted_rect_cells_to_polygon']}")

# ---------------- 格 B：L 形 + 跨轴（报告标为未覆盖的那一格）----------------
print()
print("=" * 78)
print("格 B · L 形 footprint + 跨轴组件（materialize 必须真的插点）")
print("=" * 78)
L = [[0.12, 0.12], [10.0, 0.12], [10.0, 3.0], [4.0, 3.0], [4.0, 7.88], [0.12, 7.88]]


def fresh_b():
    return ensure_corrected_geometry({
        "schema_version": "3", "footprint_x": [0.12, 10.0], "footprint_y": [0.12, 7.88],
        "floors": [{"id": "f1", "name": "F1", "z_floor": 0, "ceiling_height": 3,
                    "footprint": {"vertices": [list(p) for p in L]},
                    "cells": [{"id": "bottom", "x": [0.12, 10.0], "y": [0.12, 3.0]},
                              {"id": "top", "x": [0.12, 4.0], "y": [3.0, 7.88]}]}]})


intents_b = [mk("x", 0.12, 0.0, "lo", "x-lo"), mk("y", 0.12, 0.0, "lo", "y-lo")]
comps_b = {}
for i in intents_b:
    try:
        comps_b[i.intent_id] = build_shared_axis_component(fresh_b(), i, tol)
    except Exception as e:
        print(f"  组件 {i.intent_id} 构造失败: {type(e).__name__}: {e}")
for k, c in comps_b.items():
    print(f"  组件 {k}: axis={c.axis} {c.old_value}->{c.new_value} intervals={[(i.lo,i.hi) for i in c.intervals]}")

print("\n-- 现行实现 --")
g = fresh_b()
try:
    ET._apply_components(g, comps_b, tol); print("  没抛异常"); report("格 B 现行", g)
except ValueError as e:
    print(f"  ⛔ {e}")

print("\n-- 三阶段修法 --")
g = fresh_b()
apply_components_fixed(g, comps_b, tol)
ok_b = report("格 B", g)

print()
print("=" * 78)
print(f"结论：格 A {'✅' if ok_a else '⛔'} · 格 B {'✅' if ok_b else '⛔'}")
