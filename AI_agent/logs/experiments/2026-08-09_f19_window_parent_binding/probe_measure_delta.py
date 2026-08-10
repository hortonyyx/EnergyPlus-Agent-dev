"""F-19 候选：量 kernel.window_parent_binding 的 built_vertices 偏差到底是多大。

判据（⛔ 先量再定性，不许照 F-18 的形状直接归并）：
  ~1e-15 m  ⇒ 浮点噪声，与 F-18 同族（门用了精确相等）
  ~0.12 m   ⇒ 真实几何错（envelope 变换后宿主线没更新）
  其它      ⇒ 第三种，另查
只读，零 LLM 成本。
"""
import json, sys
from pathlib import Path

RUN = Path("case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify")

from src.agent.correction.window_host import WindowHostsArtifactV1
from src.agent.geometry.modelling import SegmentLine2D, window_verts_on_line

bg = json.loads((RUN / "2_modelling/building_geometry.json").read_text())
claims = WindowHostsArtifactV1.model_validate_json(
    (RUN / "1_correction/attempts/001/window_hosts.json").read_bytes()
).claims

built_by_id = {w["source_window"]: w for w in bg["windows"]}

print(f"{'window_id':<12} {'max|Δ|':>12}  {'per-axis max Δ (x,y,z)':<34} verdict")
print("-" * 92)
overall = 0.0
rows = []
for res in claims.resolutions:
    b = built_by_id.get(res.window_id)
    if b is None:
        print(f"{res.window_id:<12} {'MISSING':>12}")
        continue
    fresh = window_verts_on_line(
        host_line=SegmentLine2D(
            (res.segment_p1.x, res.segment_p1.y),
            (res.segment_p2.x, res.segment_p2.y),
        ),
        parameter_interval=(res.segment_parameter_interval.lo, res.segment_parameter_interval.hi),
        z_interval=(res.z_interval.lo, res.z_interval.hi),
        outward_normal_xy=tuple(float(v) for v in res.segment_outward_normal),
    )
    built = b["verts"]
    if len(built) != len(fresh):
        print(f"{res.window_id:<12} {'LEN MISMATCH':>12}  built={len(built)} fresh={len(fresh)}")
        continue
    axis_max = [0.0, 0.0, 0.0]
    for pb, pf in zip(built, fresh):
        for i in range(3):
            axis_max[i] = max(axis_max[i], abs(float(pb[i]) - float(pf[i])))
    m = max(axis_max)
    overall = max(overall, m)
    verdict = ("bit-identical" if m == 0.0 else
               "float noise (<=1e-12)" if m <= 1e-12 else
               "SUB-MM (<=1e-3)" if m <= 1e-3 else
               "REAL geometry delta")
    rows.append((res.window_id, m, axis_max, verdict))
    print(f"{res.window_id:<12} {m:>12.3e}  ({axis_max[0]:.3e},{axis_max[1]:.3e},{axis_max[2]:.3e})  {verdict}")

print("-" * 92)
print(f"全局最大偏差 = {overall:.6e} m")
print()
# 附：把第一条不一致的窗逐顶点打出来，供人核
for wid, m, _a, _v in rows:
    if m > 0.0:
        res = next(r for r in claims.resolutions if r.window_id == wid)
        b = built_by_id[wid]
        fresh = window_verts_on_line(
            host_line=SegmentLine2D((res.segment_p1.x, res.segment_p1.y), (res.segment_p2.x, res.segment_p2.y)),
            parameter_interval=(res.segment_parameter_interval.lo, res.segment_parameter_interval.hi),
            z_interval=(res.z_interval.lo, res.z_interval.hi),
            outward_normal_xy=tuple(float(v) for v in res.segment_outward_normal),
        )
        print(f"逐顶点样本 · {wid}   宿主线 p1={(res.segment_p1.x, res.segment_p1.y)} p2={(res.segment_p2.x, res.segment_p2.y)}")
        print(f"  参数区间 = [{res.segment_parameter_interval.lo!r}, {res.segment_parameter_interval.hi!r}]")
        for i, (pb, pf) in enumerate(zip(b["verts"], fresh)):
            print(f"   v{i}  built={tuple(float(x) for x in pb)}")
            print(f"       fresh={tuple(float(x) for x in pf)}")
        break
