import sys, shutil, tempfile, json
from pathlib import Path
REPO=Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0,str(REPO))
import src.agent.judge.tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (TarchConversionRequestV1,
    resolve_converter_tooling, compute_request_sha256)
base=json.loads((REPO/"AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json").read_text())
orig=tn._emit_s4_diagnostics
captured={}
def spy(s4, tols, diags):
    captured["s4"]=s4
    return orig(s4, tols, diags)
tn._emit_s4_diagnostics=spy
p=dict(base); p["plan_views"]=[v for v in base["plan_views"] if v["id"]=="plan-F1"]
p["elevation_views"]=[]; p["raster_overlays"]=[o for o in base["raster_overlays"] if o["view_id"]=="plan-F1"]
p["floors"]=[f for f in base["floors"] if f["id"]=="F1"]; p["request_sha256"]="0"*64
r=TarchConversionRequestV1.model_validate(p); p["request_sha256"]=compute_request_sha256(r)
r=TarchConversionRequestV1.model_validate(p)
tooling=resolve_converter_tooling(REPO/"src/configs/judge_gt.yaml", REPO/"src/configs/correction.yaml")
work=Path(tempfile.mkdtemp(prefix="sm25_dg_")); src=work/"source.dxf"
shutil.copyfile(REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf", src)
res=tn.run_tarch_conversion(src, r, tooling, work)
s4=captured.get("s4")
if s4:
    print("dangles:", s4["n_dangles"], " cuts:", s4["n_cuts"], " invalid:", s4["n_invalid"])
    for i,d in enumerate(s4["dangles"]):
        cs=[tuple(c)[:2] for c in d.coords]
        print(f"  dangle {i}: {cs[0]} -> {cs[-1]}  长度 {d.length:.1f}mm")
    print("sum_area_m2 %.2f  footprint_area_m2 %.2f"%(s4["sum_area_m2"], s4["footprint_area_m2"]))
else:
    print("未捕获 s4（可能在更早的门就停了）")
