"""F-19：把 15 个窗的 built vs fresh 差异逐个归类。

⛔ 纪律（08-06 教训）：「顺序不同」必须再分 循环旋转 / 绕向反 / 坐标真的不同。
   循环旋转 ⇒ 同一多边形、法向不变、EnergyPlus 等价；
   绕向反   ⇒ 法向翻转、内外面反转 ⇒ 窗挂错房间（有害，⛔ 不许豁免）。
只读，零 LLM 成本。
"""
import json
from pathlib import Path

RUN = Path("case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify")

from src.agent.correction.window_host import WindowHostsArtifactV1
from src.agent.geometry.modelling import SegmentLine2D, window_verts_on_line

bg = json.loads((RUN / "2_modelling/building_geometry.json").read_text())
claims = WindowHostsArtifactV1.model_validate_json(
    (RUN / "1_correction/attempts/001/window_hosts.json").read_bytes()
).claims
built_by_id = {w["source_window"]: w for w in bg["windows"]}


def newell_normal(poly):
    nx = ny = nz = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1, z1 = poly[i]
        x2, y2, z2 = poly[(i + 1) % n]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    mag = (nx * nx + ny * ny + nz * nz) ** 0.5
    return (nx / mag, ny / mag, nz / mag) if mag else (0.0, 0.0, 0.0)


def classify(built, fresh):
    b = [tuple(float(c) for c in p) for p in built]
    f = [tuple(float(c) for c in p) for p in fresh]
    if b == f:
        return "identical", 0
    n = len(b)
    if len(f) != n:
        return "length_mismatch", None
    for k in range(n):                                  # 循环旋转？
        if b == f[k:] + f[:k]:
            return "cyclic_rotation", k
    rf = list(reversed(f))
    for k in range(n):                                  # 绕向反？（⛔ 有害）
        if b == rf[k:] + rf[:k]:
            return "REVERSED_WINDING", k
    if sorted(b) == sorted(f):
        return "same_set_other_perm", None
    return "COORDS_DIFFER", None


tally, rows = {}, []
for res in claims.resolutions:
    b = built_by_id[res.window_id]
    fresh = window_verts_on_line(
        host_line=SegmentLine2D((res.segment_p1.x, res.segment_p1.y), (res.segment_p2.x, res.segment_p2.y)),
        parameter_interval=(res.segment_parameter_interval.lo, res.segment_parameter_interval.hi),
        z_interval=(res.z_interval.lo, res.z_interval.hi),
        outward_normal_xy=tuple(float(v) for v in res.segment_outward_normal),
    )
    kind, shift = classify(b["verts"], fresh)
    nb, nf = newell_normal([tuple(float(c) for c in p) for p in b["verts"]]), newell_normal([tuple(float(c) for c in p) for p in fresh])
    dot = sum(a * c for a, c in zip(nb, nf))
    tally[kind] = tally.get(kind, 0) + 1
    rows.append((res.window_id, kind, shift, dot, nb))
    print(f"{res.window_id:<12} {kind:<18} shift={shift}  normal·normal={dot:+.6f}  built_normal={tuple(round(v,6) for v in nb)}")

print("-" * 96)
print("归类汇总:", json.dumps(tally, ensure_ascii=False))
bad = [r for r in rows if r[1] in ("REVERSED_WINDING", "COORDS_DIFFER", "same_set_other_perm", "length_mismatch")]
print(f"有害类（绕向反 / 坐标真不同 / 其它置换）= {len(bad)}")
print(f"法向全部保持（dot≈+1）= {all(r[3] > 0.999999 for r in rows)}")
shifts = sorted({r[2] for r in rows if r[1] == 'cyclic_rotation'})
print(f"循环旋转的位移量集合 = {shifts}")
