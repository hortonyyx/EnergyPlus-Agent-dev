import sys, shutil, tempfile, json
from pathlib import Path
REPO=Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0,str(REPO))
import ezdxf
from src.agent.judge.tarch_converter_schema import (TarchConversionRequestV1,
    resolve_converter_tooling, compute_request_sha256)
from src.agent.judge.tarch_normalize import run_tarch_conversion

SRC=REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
REPAIR={   # handle -> (start, end)   吸附到图纸自身已有的精确坐标
 "13AD": ((-25229.022, 38273.464), (-21589.022, 38273.464)),
 "13AE": ((-25229.022, 38153.464), (-21589.022, 38153.464)),
 "13AF": ((-25229.022, 38273.464), (-25229.022, 38153.464)),
 "13AC": ((-21589.022, 38577.464), (-21589.022, 38273.464)),
 "160A": ((-21589.022, 38153.464), (-21589.022, 37857.464)),
}
def repaired(path):
    doc=ezdxf.readfile(str(SRC))
    n=0
    for e in doc.modelspace():
        if e.dxf.handle in REPAIR and e.dxftype()=="LINE":
            s,t=REPAIR[e.dxf.handle]
            e.dxf.start=(s[0],s[1],0.0); e.dxf.end=(t[0],t[1],0.0); n+=1
    doc.saveas(str(path)); return n

base=json.loads((REPO/"AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json").read_text())
tooling=resolve_converter_tooling(REPO/"src/configs/judge_gt.yaml", REPO/"src/configs/correction.yaml")

def run(vid,fid,src_path,a_room):
    import hashlib
    p=json.loads(json.dumps(base))
    p["plan_views"]=[v for v in p["plan_views"] if v["id"]==vid]
    p["elevation_views"]=[]; p["raster_overlays"]=[o for o in p["raster_overlays"] if o["view_id"]==vid]
    p["floors"]=[f for f in p["floors"] if f["id"]==fid]
    p["min_room_area_m2"]=a_room
    p["source_dxf_sha256"]=hashlib.sha256(Path(src_path).read_bytes()).hexdigest()
    p["request_sha256"]="0"*64
    r=TarchConversionRequestV1.model_validate(p); p["request_sha256"]=compute_request_sha256(r)
    r=TarchConversionRequestV1.model_validate(p)
    work=Path(tempfile.mkdtemp(prefix="sm25_probe_")); s=work/"source.dxf"; shutil.copyfile(src_path,s)
    res=run_tarch_conversion(s, r, tooling, work)
    rep=res.conversion_report
    bad=[d for d in rep.diagnostics if d.severity.name!="INFO"]
    red=[g.id for g in rep.gates if not g.passed]
    return res, red, bad

tmp=Path(tempfile.mkdtemp(prefix="sm25_fixed_")); fixed=tmp/"sm25-L_t3_fixed.dxf"
print("修复了 %d 条线 ->"%repaired(fixed), fixed)
for src_label, src_path in (("原图", SRC), ("修复后", fixed)):
    for vid,fid in (("plan-F1","F1"),("plan-F2","F2")):
        for a in (2.0, 5.0):
            res, red, bad = run(vid,fid,src_path,a)
            codes=", ".join(sorted({d.code for d in bad})) or "—"
            print(f"  {src_label:5s} {vid} A_room={a}  augmented={'有' if res.augmented_dxf_path else '无'}  "
                  f"红门={red}  BLOCK={codes}")
