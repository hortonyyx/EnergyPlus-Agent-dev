"""Localize the residual pairwise zone overlap on sm24."""
from __future__ import annotations
import hashlib
from pathlib import Path
from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (
    PlanViewIntentV1, TarchConversionRequestV1, TarchDialectRulesV1,
    TarchEntitySelectorV1, ZoneIntentEntryV1, ZoneIntentSpecV1,
    compute_request_sha256, resolve_converter_tooling, ConversionDiagnosticV1)
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
zones = tn.s7_expand_zones(claims, wall_region, footprint, tols, diags)
mpu = 0.001
zp = [z.polygon for z in zones]
total = 0.0
for i in range(len(zp)):
    for j in range(i + 1, len(zp)):
        inter = zp[i].intersection(zp[j])
        a = inter.area * mpu * mpu
        if a > 1e-8:
            total += a
            c = inter.representative_point()
            print(f"zones {i}&{j}: overlap={a:.6f} m² ({a*1e6:.1f} mm²) at world ({c.x*mpu:.2f},{c.y*mpu:.2f}) bounds={tuple(round(v*mpu,2) for v in inter.bounds)}")
print(f"TOTAL pairwise overlap = {total:.6f} m²")
