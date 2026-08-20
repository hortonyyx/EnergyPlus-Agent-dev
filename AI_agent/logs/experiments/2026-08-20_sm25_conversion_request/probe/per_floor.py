import sys, shutil, tempfile, json, collections
from pathlib import Path
REPO=Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0,str(REPO))
from src.agent.judge.tarch_converter_schema import (TarchConversionRequestV1,
    resolve_converter_tooling, compute_request_sha256)
from src.agent.judge.tarch_normalize import run_tarch_conversion
base=json.loads((REPO/"AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json").read_text())
tooling=resolve_converter_tooling(REPO/"src/configs/judge_gt.yaml", REPO/"src/configs/correction.yaml")
for vid, fid in (("plan-F1","F1"),("plan-F2","F2")):
    p=dict(base)
    p["plan_views"]=[v for v in base["plan_views"] if v["id"]==vid]
    p["elevation_views"]=[]
    p["raster_overlays"]=[o for o in base["raster_overlays"] if o["view_id"]==vid]
    p["floors"]=[f for f in base["floors"] if f["id"]==fid]
    p["request_sha256"]="0"*64
    r=TarchConversionRequestV1.model_validate(p); p["request_sha256"]=compute_request_sha256(r)
    r=TarchConversionRequestV1.model_validate(p)
    work=Path(tempfile.mkdtemp(prefix=f"sm25_{fid}_"))
    src=work/"source.dxf"; shutil.copyfile(REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf", src)
    res=run_tarch_conversion(src, r, tooling, work)
    rep=res.conversion_report
    bad=[d for d in rep.diagnostics if d.severity.name!="INFO"]
    print(f"=== {vid} ({fid})  augmented={'有' if res.augmented_dxf_path else '无'} "
          f"gates红={[g.id for g in rep.gates if not g.passed]}")
    for d in bad:
        print(f"    {d.severity.name:6s} {d.code} handles={d.source_entity_handles[:8]}")
        c=d.context or {}
        for k in ("cavity_count","expected_count","dangle_count","exterior_openings","outer_skin_gaps","symmetric_diff_m2"):
            if k in c: print(f"          {k} = {c[k]}")
        if "free_end_points_world_m" in c: print("          free ends:", c["free_end_points_world_m"])
        if "cavity_centroids_world_m" in c:
            print("          centroids:", [(round(a,2),round(b,2)) for a,b in c["cavity_centroids_world_m"]])
    print()
