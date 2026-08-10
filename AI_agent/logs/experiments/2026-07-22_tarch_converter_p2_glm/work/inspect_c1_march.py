"""Dump c1 cavity polygon + reproduce the 8000mm march to find the graze point."""
from __future__ import annotations
import hashlib
from pathlib import Path
from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (
    PlanViewIntentV1, TarchConversionRequestV1, TarchDialectRulesV1,
    TarchEntitySelectorV1, ZoneIntentEntryV1, ZoneIntentSpecV1,
    compute_request_sha256, resolve_converter_tooling, ConversionDiagnosticV1)
from shapely.geometry import Point
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[5]
SM24 = Path(__file__).resolve().parent / "sm24_source.dxf"
sha = hashlib.sha256(SM24.read_bytes()).hexdigest()
aff = {"m00": 0.001, "m01": 0.0, "m02": -23.0576, "m10": 0.0, "m11": 0.001, "m12": -26.5652}
clip = {"xmin": 12276.94, "ymin": 18802.14, "xmax": 41994.33, "ymax": 51678.57}
pv = PlanViewIntentV1(id="plan-F1", floor_id="F1", frame_title="1f平面图", clip_box_dxf=clip, world_from_source_m=aff,
    wall_selector=TarchEntitySelectorV1(entity_types=["LINE"], layers=["WALL"]),
    opening_selector=TarchEntitySelectorV1(entity_types=["INSERT"], layers=["WINDOW"]),
    dialect_rules=TarchDialectRulesV1(window_block_names=["$TCHSYS$WIN2D"], door_block_prefixes=["$DorLib2D$"], classifier_version="tarch-dialect-v1"),
    zone_intent=ZoneIntentSpecV1(mode="intent_file", expected_count=8, entries=[ZoneIntentEntryV1(zone_id=f"z{i}", name=f"r{i}", role="unspecified") for i in range(8)]))
req = TarchConversionRequestV1(request_version=1, case="sm24_anchor", source_dxf_label="sm24_source.dxf", source_dxf_sha256=sha,
    normalized_source_id="sm24-anchor-normalized", target_geometry_profile="c2_simple_orthogonal_no_holes", native_units="unitless",
    metres_per_unit=0.001, floors=[{"id": "F1", "name": "1F", "z_floor_m": 0.0, "ceiling_height_m": 4.5}], plan_views=[pv], request_sha256="0" * 64)
req = req.model_copy(update={"request_sha256": compute_request_sha256(req)})
tooling = resolve_converter_tooling(REPO / "src/configs/judge_gt.yaml", REPO / "src/configs/correction.yaml")
tols = tn._tols_from(tooling, 0.001)
p1 = tn.run_p1_plan_view(SM24, req, pv, tooling)
diags: list[ConversionDiagnosticV1] = list(p1.diagnostics)
cavities, wall_region, footprint, near = tn.s5_identify_cavities(p1, req, tols, diags, pv.world_from_source_m)
claims = tn.s6_bind_intent(cavities, pv, tols, diags, pv.world_from_source_m)
# c1 is the cavity claimed as zone 5 (index 5 in claims). Find by bounds y[30065,42445].
c1 = next(c["cavity"] for c in claims if c["cavity_index"] == next(i for i, g in enumerate(cavities) if abs(g.bounds[1]-30065)<1 and abs(g.bounds[3]-42445)<1))
cc = tn._clean_collinear([(p[0], p[1]) for p in list(c1.exterior.coords)[:-1]])
cc = tn._ensure_ccw(cc)
print(f"c1 cleaned cavity verts={len(cc)}:")
for v in cc:
    print(f"  ({v[0]:.1f}, {v[1]:.1f})")
# reproduce march on each cavity edge midpoint
print("\nper-cavity-edge midpoint march:")
n = len(cc)
for i in range(n):
    a, b = cc[i], cc[(i+1) % n]
    nx, ny = tn._outward_normal(a, b)
    mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
    t, ext = tn._march_thickness((mx, my), nx, ny, wall_region, footprint)
    flag = "  <<< HUGE" if t > 600 else ""
    print(f"  edge {i}: ({a[0]:.0f},{a[1]:.0f})->({b[0]:.0f},{b[1]:.0f}) mid=({mx:.0f},{my:.0f}) n=({nx},{ny}) t={t:.1f} ext={ext}{flag}")
