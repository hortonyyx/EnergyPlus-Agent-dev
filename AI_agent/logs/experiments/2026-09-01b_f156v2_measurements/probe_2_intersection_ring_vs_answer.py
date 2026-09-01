import json, sys
from pathlib import Path
from shapely import Polygon
REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))
from src.agent.judge import as_measured as am

SRC = REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor"
REQ = SRC/"request_as_measured.json"
MIN = float(json.loads(REQ.read_text())["min_room_area_m2"])
doc = am.build_as_measured(SRC/"sm25-L_t3_as_received.dxf", REQ)
U = am.UNITS_PER_METRE
rep = json.loads((REPO/"case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json").read_text())

def endcap(groups, axis, const, lo, hi):
    out=[]
    for g in groups.values():
        if g.axis==axis: continue
        for w in g.runs:
            if const in (w.along_min,w.along_max) and min(hi,w.face_hi)-max(lo,w.face_lo)>0:
                out.append(g); break
    return out

for view in doc.views:
    groups = am._boundary_wall_groups(view)
    footprint, ring_records = am._boundary_footprint(view)
    wall_region = am._boundary_wall_region(view)
    face_by_id = {f.id:f for f in view.face_lines}
    geom = footprint.difference(wall_region)
    thr = MIN*U*U
    cavities = [p for p in getattr(geom,"geoms",[geom])
                if p.geom_type=="Polygon" and not p.is_empty and p.area>thr]
    cavities.sort(key=lambda c: tuple(round(v,6) for v in c.bounds))
    cavity_ids = {id(c): am._boundary_cavity_id(view.view_id,c) for c in cavities}
    zones = [z for z in rep["zones"] if z["floor_id"]==view.floor_id]
    for cav in cavities:
        cid = cavity_ids[id(cav)]
        ring=[(int(round(x)),int(round(y))) for x,y in list(cav.exterior.coords)[:-1]]
        repp = cav.representative_point()
        raws=[]
        bad=False
        for a,b in zip(ring, ring[1:]+ring[:1]):
            if a[0]==b[0] and a[1]!=b[1]:
                axis,const,lo,hi="y",a[0],min(a[1],b[1]),max(a[1],b[1])
                side = -1 if repp.x < const else 1
            elif a[1]==b[1] and a[0]!=b[0]:
                axis,const,lo,hi="x",a[1],min(a[0],b[0]),max(a[0],b[0])
                side = -1 if repp.y < const else 1
            else:
                bad=True; break
            ow = am._boundary_owners(groups,axis,const,lo,hi)
            kind="faced" if len(ow)==1 else None
            grp = ow[0] if len(ow)==1 else None
            if kind is None:
                ec = endcap(groups,axis,const,lo,hi)
                if not ow and len(ec)==1:
                    kind, grp = "endcap", ec[0]
                else:
                    kind="AMBIG"
            raws.append(dict(axis=axis,const=const,lo=lo,hi=hi,side=side,kind=kind,grp=grp,p1=a,p2=b))
        if bad: print("NONAXIS",cid); continue
        # merge cyclic collinear on (axis,const)
        start=0
        for i,r in enumerate(raws):
            p=raws[i-1]
            if (p["axis"],p["const"])!=(r["axis"],r["const"]): start=i; break
        rot=raws[start:]+raws[:start]
        merged=[]
        for r in rot:
            if merged and (merged[-1]["axis"],merged[-1]["const"])==(r["axis"],r["const"]):
                m=merged[-1]
                m["lo"]=min(m["lo"],r["lo"]); m["hi"]=max(m["hi"],r["hi"])
                m["parts"].append(r)
            else:
                merged.append(dict(r, parts=[r]))
        # corners
        verts=[]; par=False
        for i,c in enumerate(merged):
            p=merged[i-1]
            if p["axis"]==c["axis"]: par=True; break
            verts.append((p["const"],c["const"]) if p["axis"]=="y" else (c["const"],p["const"]))
        if par: print("PARALLEL",cid); continue
        poly=Polygon(verts)
        nfaced=sum(1 for m in merged if m["kind"]=="faced")
        nend=sum(1 for m in merged if m["kind"]=="endcap")
        namb=sum(1 for m in merged if m["kind"]=="AMBIG")
        # classify each faced merged support (single witness at its midpoint)
        conds=[]
        for m in merged:
            if m["kind"]!="faced": conds.append(None); continue
            g=m["grp"]
            near="lo" if m["side"]<0 else "hi"; far="hi" if near=="lo" else "lo"
            nh,fh=g.handles(near),g.handles(far)
            rn=round(sum(face_by_id[h].const for h in nh)/len(nh))
            rf=round(sum(face_by_id[h].const for h in fh)/len(fh))
            sp=am._BoundarySpan(axis=m["axis"],cavity_const=m["const"],lo=m["lo"],hi=m["hi"],
                                side=m["side"],p1=m["p1"],p2=m["p2"],group=g,boundary_condition="unknown")
            cond,_ev,log = am._classify_boundary_fact(sp,rn,rf,footprint,ring_records,wall_region,cavities,cavity_ids)
            conds.append((cond,log))
        # zone match
        zid=[z["zone_id"] for z in zones
             if Polygon([(round(p[0]*U),round(p[1]*U)) for p in z["polygon_m"]["exterior"]["vertices"]]).covers(poly.representative_point())]
        zedges = {z["zone_id"]:len(z["edges"]) for z in zones}
        zsym=""
        if len(zid)==1:
            zp=Polygon([(round(p[0]*U),round(p[1]*U)) for p in
                        next(z for z in zones if z["zone_id"]==zid[0])["polygon_m"]["exterior"]["vertices"]])
            zsym=f" zone_area={zp.area/U/U:.3f} symdiff={poly.symmetric_difference(zp).area/U/U:.3f}"
        print(f"{view.view_id} {cid} area={cav.area/U/U:8.3f} raw={len(raws)} merged={len(merged)} "
              f"faced={nfaced} endcap={nend} ambig={namb} valid={poly.is_valid} "
              f"zones={zid} zedges={[zedges.get(z) for z in zid]}{zsym}")
        if nend or len(merged)>4:
            print("    conds:", [c if c is None else c[0]+("" if c[1] else "/ILLOGICAL") for c in conds])
