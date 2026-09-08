"""独立复算：立面洞口 × 平面观测 的全量二部残差表（不走生产配对的单向去重）。

用途：验证派工单病因判断——配对是否单向、互为最近缺在哪一侧。
⛔ 只读产物，不改任何生产代码。
"""
import json
from collections import Counter, defaultdict

from src.agent.correction.facade_convention import (
    project_affine_interval,
    resolve_sign,
)

R = "case_tests/e2e_tests/sm25-L_anchor/run_win_e2e"
ri = json.load(open(f"{R}/1_correction/attempts/001/window_resolver_inputs.json"))
geom = json.load(open(f"{R}/1_correction/correction_geometry_snapped.json"))

rows = ri["inputs"]["source_windows"]
plan = [r for r in rows if r["channel"] == "plan"]
elev = [r for r in rows if r["channel"] == "elevation"]
facade_of = {e["input_id"]: e["resolved_building_direction"]
             for e in ri["inputs"]["elevation_direction_facts"]}

floors = {f["id"]: (float(f["z_floor"]),
                    float(f["z_floor"]) + float(f["ceiling_height"]))
          for f in geom["floors"]}
floor_by_ref = {i + 1: f["id"] for i, f in enumerate(geom["floors"])}
ref_of_floor = {v: k for k, v in floor_by_ref.items()}
segs = defaultdict(list)
for s in geom["facade_segments"]:
    segs[(s["floor_id"], s["facade_family"])].append(s)

widths = {}
for art in ri["raw_reading_artifacts"]:
    if art["input_id"] in facade_of:
        doc = json.loads(art["raw_bytes"])
        widths[art["input_id"]] = float(doc["calibration"]["x"]["overall_mm"]) / 1000.0


def planes_of(floor_id, facade):
    out = set()
    for s in segs[(floor_id, facade)]:
        out.add(float(s["p1"][1]) if facade in ("North", "South") else float(s["p1"][0]))
    return out


ops = []
for r in elev:
    facade = facade_of[r["source_input_id"]]
    sign = resolve_sign(facade, mirrored=False, local_x_positive="image_left_to_right")
    lo, hi = project_affine_interval(
        along_origin=0.0 if sign > 0 else widths[r["source_input_id"]], sign=sign,
        local_lo=float(r["local_along_interval"]["lo"]),
        local_hi=float(r["local_along_interval"]["hi"]))
    z_lo = float(r["local_z_interval"]["lo"])
    z_hi = float(r["local_z_interval"]["hi"])
    fl = [fid for fid, (a, b) in floors.items() if a <= z_lo and z_hi <= b]
    ops.append(dict(oid=f"{r['source_input_id']}/{r['observation_id']}",
                    facade=facade, along_lo=lo, along_hi=hi,
                    floor=fl[0] if len(fl) == 1 else None))

TOL = 0.060
edges = []
for op in ops:
    if op["floor"] is None:
        continue
    fref = ref_of_floor[op["floor"]]
    # ⚠️ 与生产同口径：cross 必须含住该洞口所属段的平面（不是任意平面）
    seg_planes = planes_of(op["floor"], op["facade"])
    for pr in plan:
        if pr["floor_ref"] != fref:
            continue
        if op["facade"] in ("North", "South"):
            along, cross = pr["world_x_interval"], pr["world_y_interval"]
        else:
            along, cross = pr["world_y_interval"], pr["world_x_interval"]
        c_lo, c_hi = float(cross["lo"]), float(cross["hi"])
        crosses = [p for p in seg_planes if c_lo <= p <= c_hi]
        d_lo = abs(float(along["lo"]) - op["along_lo"])
        d_hi = abs(float(along["hi"]) - op["along_hi"])
        edges.append(dict(op=op["oid"], plan=f"{pr['source_input_id']}/{pr['observation_id']}",
                          d_lo=d_lo, d_hi=d_hi, res=d_lo + d_hi,
                          crosses_plane=bool(crosses), facade=op["facade"],
                          floor=op["floor"], along_lo=float(along["lo"]),
                          along_hi=float(along["hi"])))

tol_edges = [e for e in edges if e["d_lo"] <= TOL and e["d_hi"] <= TOL]
by_op = defaultdict(list)
by_plan = defaultdict(list)
for e in tol_edges:
    by_op[e["op"]].append(e)
    by_plan[e["plan"]].append(e)

print("elevation openings on a floor:", len([o for o in ops if o["floor"]]))
print("plan rows:", len(plan), " tolerance edges:", len(tol_edges))
print("per-opening #candidates(within tol):", Counter(len(v) for v in by_op.values()))
print("per-plan-row #openings(within tol):", Counter(len(v) for v in by_plan.values()))

# 平面侧互为最近：每个 plan row 的最近洞口是谁（残差最小）
plan_best = {}
for pid, es in by_plan.items():
    plan_best[pid] = min(es, key=lambda e: e["res"])

# 洞口侧最近（生产口径：先按 source_input_id 去重留最好，但这里直接看全体候选的排序）
print("\n== 洞口侧：按残差排序的前 2 候选 + 反向最近是否指回 ==")
mutual_fail, reuse = [], defaultdict(list)
for op, es in sorted(by_op.items()):
    es_sorted = sorted(es, key=lambda e: e["res"])
    best = es_sorted[0]
    back = plan_best[best["plan"]]
    ok = back["op"] == op
    if not ok:
        mutual_fail.append((op, best["plan"], back["op"], best["res"]))
    for e in es:
        reuse[e["plan"]].append(op)

shared = {p: v for p, v in reuse.items() if len(set(v)) > 1}
print("mutual-nearest 失败的洞口数:", len(mutual_fail))
for m in mutual_fail[:10]:
    print("  ", m)
print("被 ≥2 洞口共用的 plan row 数:", len(shared))
for p, v in list(shared.items())[:10]:
    print("  ", p, "->", v)

json.dump(edges, open("AI_agent/logs/experiments/2026-09-08h_pairing_analysis/edges.json", "w"),
          indent=1)
