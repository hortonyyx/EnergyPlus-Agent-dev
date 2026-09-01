import json, sys
from pathlib import Path
REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))
from src.agent.judge import as_measured as am

SRC = REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor"
REQ = SRC/"request_as_measured.json"
MIN = float(json.loads(REQ.read_text())["min_room_area_m2"])
doc = am.build_as_measured(SRC/"sm25-L_t3_as_received.dxf", REQ)
U = am.UNITS_PER_METRE

for view in doc.views:
    groups = am._boundary_wall_groups(view)
    footprint, ring_records = am._boundary_footprint(view)
    wall_region = am._boundary_wall_region(view)
    geom = footprint.difference(wall_region)
    thr = MIN*U*U
    cavities = [p for p in getattr(geom,"geoms",[geom])
                if p.geom_type=="Polygon" and not p.is_empty and p.area>thr]
    cavities.sort(key=lambda c: tuple(round(v,6) for v in c.bounds))
    for cav in cavities:
        cid = am._boundary_cavity_id(view.view_id, cav)
        area = cav.area/U/U
        if area < 60: continue   # only the two corridors
        ring=[(int(round(x)),int(round(y))) for x,y in list(cav.exterior.coords)[:-1]]
        print(f"=== {view.view_id} {cid} area={area:.4f} segs={len(ring)}")
        for i,(a,b) in enumerate(zip(ring, ring[1:]+ring[:1])):
            if a[0]==b[0]:
                axis,const,lo,hi="y",a[0],min(a[1],b[1]),max(a[1],b[1])
            else:
                axis,const,lo,hi="x",a[1],min(a[0],b[0]),max(a[0],b[0])
            ow = am._boundary_owners(groups,axis,const,lo,hi)
            # endcap candidates: bands whose END plane is this line
            end=[]
            for g in groups.values():
                if g.axis==axis: continue
                for w in g.runs:
                    if const in (w.along_min,w.along_max) and min(hi,w.face_hi)-max(lo,w.face_lo)>0:
                        end.append((g.key,w.id,w.along_min,w.along_max)); break
            print(f"  s{i:02d} {axis}={const} [{lo},{hi}] len={hi-lo} owners={len(ow)}"
                  f"{'' if ow else ' ENDCAPS='+str(len(end))+str([e[0] for e in end])}")
