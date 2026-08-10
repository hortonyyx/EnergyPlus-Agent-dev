"""Debug G4: why does _outer_skin_gap_count != 14 exterior openings on sm24?"""
from __future__ import annotations
import hashlib
from pathlib import Path
from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (
    PlanViewIntentV1, TarchConversionRequestV1, TarchDialectRulesV1,
    TarchEntitySelectorV1, ZoneIntentEntryV1, ZoneIntentSpecV1,
    compute_request_sha256, resolve_converter_tooling)

REPO = Path(__file__).resolve().parents[5]
GT_CONFIG = REPO / "src/configs/judge_gt.yaml"
SM24 = Path(__file__).resolve().parent / "sm24_source.dxf"
WINDOW_BLOCK = "$TCHSYS$WIN2D"

sha = hashlib.sha256(SM24.read_bytes()).hexdigest()
aff = {"m00": 0.001, "m01": 0.0, "m02": -23.0576, "m10": 0.0, "m11": 0.001, "m12": -26.5652}
clip = {"xmin": 12276.94, "ymin": 18802.14, "xmax": 41994.33, "ymax": 51678.57}
pv = PlanViewIntentV1(
    id="plan-F1", floor_id="F1", frame_title="1f平面图", clip_box_dxf=clip, world_from_source_m=aff,
    wall_selector=TarchEntitySelectorV1(entity_types=["LINE"], layers=["WALL"]),
    opening_selector=TarchEntitySelectorV1(entity_types=["INSERT"], layers=["WINDOW"]),
    dialect_rules=TarchDialectRulesV1(window_block_names=[WINDOW_BLOCK],
                                      door_block_prefixes=["$DorLib2D$"], classifier_version="tarch-dialect-v1"),
    zone_intent=ZoneIntentSpecV1(mode="intent_file", expected_count=8,
                                 entries=[ZoneIntentEntryV1(zone_id=f"z{i}", name=f"r{i}", role="unspecified") for i in range(8)]))
req = TarchConversionRequestV1(
    request_version=1, case="sm24_anchor", source_dxf_label="sm24_source.dxf", source_dxf_sha256=sha,
    normalized_source_id="sm24-anchor-normalized", target_geometry_profile="c2_simple_orthogonal_no_holes",
    native_units="unitless", metres_per_unit=0.001,
    floors=[{"id": "F1", "name": "1F", "z_floor_m": 0.0, "ceiling_height_m": 4.5}],
    plan_views=[pv], request_sha256="0" * 64)
req = req.model_copy(update={"request_sha256": compute_request_sha256(req)})
tooling = resolve_converter_tooling(GT_CONFIG, REPO / "src/configs/correction.yaml")
p1 = tn.run_p1_plan_view(SM24, req, pv, tooling)

# rebuild S5 footprint the same way run_p2_conversion does
from shapely.ops import unary_union
footprint = unary_union(p1.faces)
print("footprint geom_type:", footprint.geom_type)
print("exterior ring coords (rounded):")
ring = list(footprint.exterior.coords)
for x, y in ring:
    print(f"  ({round(x,1)}, {round(y,1)})")

ext_openings = [o for o in p1.openings if o.classification == "exterior"]
print(f"\nexterior openings: {len(ext_openings)}")
print("ext opening rects (rounded):")
for o in ext_openings:
    print(f"  {o.handle} {o.kind} {tuple(round(v,1) for v in o.rect_dxf_mm)}")

gaps = tn._outer_skin_gap_count(p1, footprint)
print(f"\n_outer_skin_gap_count = {gaps}")

# Per-edge gap breakdown
print("\nper ring-edge wall-line span analysis:")
for a, b in zip(ring, ring[1:] + ring[:1]):
    if a[0] != b[0] and a[1] != b[1]:
        print(f"  SKIP diagonal {a}->{b}"); continue
    if a[1] == b[1]:
        yc, lo, hi = a[1], min(a[0], b[0]), max(a[0], b[0])
        segs = sorted((min(x0, x1), max(x0, x1)) for _, x0, y0, x1, y1 in p1.wall_lines
                      if y0 == yc and y1 == yc and not (x1 <= lo or x0 >= hi))
        axis = f"y={yc}"
    else:
        xc, lo, hi = a[0], min(a[1], b[1]), max(a[1], b[1])
        segs = sorted((min(y0, y1), max(y0, y1)) for _, x0, y0, x1, y1 in p1.wall_lines
                      if x0 == xc and x1 == xc and not (y1 <= lo or y0 >= hi))
        axis = f"x={xc}"
    merged = []
    for s in segs:
        if merged and s[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], s[1]))
        else:
            merged.append(list(s))
    gaps_here = 0
    cursor = lo
    for s0, s1 in merged:
        if s0 - cursor > 1.0:
            gaps_here += 1
        cursor = max(cursor, s1)
    if hi - cursor > 1.0:
        gaps_here += 1
    print(f"  {axis} [{lo:.1f},{hi:.1f}] n_lines={len(segs)} gaps={gaps_here}")
    if gaps_here:
        for s in merged:
            print(f"     covered {s[0]:.1f}-{s[1]:.1f}")
