"""F-19 根因决定性验证：
  假设 = built.verts 走过 F-13 的规范化（build.py:80-85），
         而 kernel gate 的 fresh_vertices 没走 ⇒ 起笔点不同 ⇒ `!=` 恒红。
  验证 = 把【同一个】规范化函数施加到 fresh 上，是否 15/15 逐位相等。
只读，零 LLM 成本。
"""
import json
import numpy as np
from pathlib import Path

RUN = Path("case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify")

from src.agent.correction.window_host import WindowHostsArtifactV1
from src.agent.geometry.modelling import SegmentLine2D, window_verts_on_line
from src.agent.geometry.build import _newell
from src.validator.data_model import canonicalize_ring_vertices

bg = json.loads((RUN / "2_modelling/building_geometry.json").read_text())
claims = WindowHostsArtifactV1.model_validate_json(
    (RUN / "1_correction/attempts/001/window_hosts.json").read_bytes()
).claims
built_by_id = {w["source_window"]: w for w in bg["windows"]}

raw_eq = canon_eq = 0
for res in claims.resolutions:
    built = [tuple(float(c) for c in p) for p in built_by_id[res.window_id]["verts"]]
    fresh = window_verts_on_line(
        host_line=SegmentLine2D((res.segment_p1.x, res.segment_p1.y), (res.segment_p2.x, res.segment_p2.y)),
        parameter_interval=(res.segment_parameter_interval.lo, res.segment_parameter_interval.hi),
        z_interval=(res.z_interval.lo, res.z_interval.hi),
        outward_normal_xy=tuple(float(v) for v in res.segment_outward_normal),
    )
    fresh = [tuple(float(c) for c in p) for p in fresh]
    if built == fresh:
        raw_eq += 1
    normal = _newell(fresh)
    canon = [tuple(float(x) for x in row)
             for row in canonicalize_ring_vertices(np.asarray(fresh, dtype=float), normal)]
    if built == canon:
        canon_eq += 1
    else:
        print(f"  ⚠️ {res.window_id} 规范化后仍不等：built={built[0]} canon={canon[0]}")

n = len(claims.resolutions)
print("=" * 78)
print(f"直接比（门现在的做法）  逐位相等 : {raw_eq}/{n}")
print(f"两边都过同一个规范化后  逐位相等 : {canon_eq}/{n}")
print("=" * 78)
print("⇒ 根因坐实" if canon_eq == n and raw_eq == 0 else "⇒ ⛔ 假设不成立，另查")
