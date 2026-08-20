import sys, shutil, tempfile, json, hashlib
from pathlib import Path
REPO=Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0,str(REPO))
import ezdxf
from src.agent.judge.tarch_converter_schema import (TarchConversionRequestV1,
    resolve_converter_tooling, compute_request_sha256)
from src.agent.judge.tarch_normalize import run_tarch_conversion
SRC=REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
REPAIR={"13AD":((-25229.022,38273.464),(-21589.022,38273.464)),
        "13AE":((-25229.022,38153.464),(-21589.022,38153.464)),
        "13AF":((-25229.022,38273.464),(-25229.022,38153.464)),
        "13AC":((-21589.022,38577.464),(-21589.022,38273.464)),
        "160A":((-21589.022,38153.464),(-21589.022,37857.464))}
tmp=Path(tempfile.mkdtemp()); fixed=tmp/"fixed.dxf"
doc=ezdxf.readfile(str(SRC))
for e in doc.modelspace():
    if e.dxf.handle in REPAIR and e.dxftype()=="LINE":
        s,t=REPAIR[e.dxf.handle]; e.dxf.start=(s[0],s[1],0.0); e.dxf.end=(t[0],t[1],0.0)
doc.saveas(str(fixed))
base=json.loads((REPO/"AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json").read_text())
tooling=resolve_converter_tooling(REPO/"src/configs/judge_gt.yaml", REPO/"src/configs/correction.yaml")
p=json.loads(json.dumps(base))
p["plan_views"]=[v for v in p["plan_views"] if v["id"]=="plan-F2"]
p["elevation_views"]=[]; p["raster_overlays"]=[o for o in p["raster_overlays"] if o["view_id"]=="plan-F2"]
p["floors"]=[f for f in p["floors"] if f["id"]=="F2"]
p["min_room_area_m2"]=5.0
p["source_dxf_sha256"]=hashlib.sha256(fixed.read_bytes()).hexdigest(); p["request_sha256"]="0"*64
r=TarchConversionRequestV1.model_validate(p); p["request_sha256"]=compute_request_sha256(r)
r=TarchConversionRequestV1.model_validate(p)
work=Path(tempfile.mkdtemp()); s=work/"source.dxf"; shutil.copyfile(fixed,s)
res=run_tarch_conversion(s,r,tooling,work)
MPU2=1e-6
print("footprint      %.2f m2"%(res.footprint.area*MPU2))
print("cavities 合计   %.2f m2  (%d 个)"%(sum(c.area for c in res.cavities)*MPU2, len(res.cavities)))
print("wall_region    %.2f m2"%(res.wall_region.area*MPU2))
print("三者对账        %.2f m2 (应为 0)"%((res.footprint.area-sum(c.area for c in res.cavities)-res.wall_region.area)*MPU2))
print("\n涉事墙线几何：")
d2=ezdxf.readfile(str(fixed))
for h in ("1453","1454","14A5","1449","146D"):
    for e in d2.modelspace().query(f'*[handle=="{h}"]'):
        a=tuple(e.dxf.start)[:2]; b=tuple(e.dxf.end)[:2]
        print(f"  {h:>5s} {e.dxf.layer:6s} ({a[0]:10.2f},{a[1]:10.2f})->({b[0]:10.2f},{b[1]:10.2f})  长 {((b[0]-a[0])**2+(b[1]-a[1])**2)**.5:8.1f}")
print("\n腔体面积排序：")
for i,c in enumerate(sorted(res.cavities,key=lambda g:-g.area)):
    b=c.bounds
    print(f"  {i:2d} {c.area*MPU2:7.2f} m2  ({b[0]:9.1f},{b[1]:9.1f})-({b[2]:9.1f},{b[3]:9.1f})  顶点{len(c.exterior.coords)-1}")
