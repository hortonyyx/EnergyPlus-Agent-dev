import sys, shutil, tempfile, json
from pathlib import Path
REPO=Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0,str(REPO))
from src.agent.judge.tarch_converter_schema import (TarchConversionRequestV1,
    resolve_converter_tooling, compute_request_sha256)
from src.agent.judge.tarch_normalize import run_tarch_conversion
base=json.loads((REPO/"AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json").read_text())
def run(vid,fid):
    p=dict(base); p["plan_views"]=[v for v in base["plan_views"] if v["id"]==vid]
    p["elevation_views"]=[]; p["raster_overlays"]=[o for o in base["raster_overlays"] if o["view_id"]==vid]
    p["floors"]=[f for f in base["floors"] if f["id"]==fid]; p["request_sha256"]="0"*64
    r=TarchConversionRequestV1.model_validate(p); p["request_sha256"]=compute_request_sha256(r)
    r=TarchConversionRequestV1.model_validate(p)
    tooling=resolve_converter_tooling(REPO/"src/configs/judge_gt.yaml", REPO/"src/configs/correction.yaml")
    work=Path(tempfile.mkdtemp(prefix="sm25_cav_")); src=work/"source.dxf"
    shutil.copyfile(REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf", src)
    return run_tarch_conversion(src, r, tooling, work)
res=run("plan-F2","F2")
cavs=sorted(res.cavities, key=lambda p:-p.area)
print(f"{'#':>2} {'面积m2':>8}  {'外包框 (x0,y0)-(x1,y1)':<34} 质心")
for i,c in enumerate(cavs):
    b=c.bounds; ct=c.centroid
    print(f"{i:2d} {c.area:8.2f}  ({b[0]:5.2f},{b[1]:5.2f})-({b[2]:5.2f},{b[3]:5.2f})   ({ct.x:5.2f},{ct.y:5.2f})  顶点{len(c.exterior.coords)-1}")
print("\n总腔体面积 %.2f m2"%sum(c.area for c in cavs))
print("footprint 面积 %.2f m2"%res.footprint.area)
