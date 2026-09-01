import json, sys
from pathlib import Path
from shapely import Polygon
REPO = Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0,str(REPO))
from src.agent.judge import as_measured as am
SRC=REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor"; REQ=SRC/"request_as_measured.json"
MIN=float(json.loads(REQ.read_text())["min_room_area_m2"])
doc=am.build_as_measured(SRC/"sm25-L_t3_as_received.dxf",REQ); U=am.UNITS_PER_METRE
rep=json.loads((REPO/"case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json").read_text())
def endcaps(g_,axis,const,lo,hi):
    o=[]
    for g in g_.values():
        if g.axis==axis: continue
        for w in g.runs:
            if const in (w.along_min,w.along_max) and min(hi,w.face_hi)-max(lo,w.face_lo)>0: o.append(g); break
    return o
for view in doc.views:
    groups=am._boundary_wall_groups(view); footprint,rr=am._boundary_footprint(view)
    wall_region=am._boundary_wall_region(view); face_by_id={f.id:f for f in view.face_lines}
    geom=footprint.difference(wall_region); thr=MIN*U*U
    cavs=[p for p in getattr(geom,"geoms",[geom]) if p.geom_type=="Polygon" and not p.is_empty and p.area>thr]
    cavs.sort(key=lambda c: tuple(round(v,6) for v in c.bounds))
    cids={id(c):am._boundary_cavity_id(view.view_id,c) for c in cavs}
    zones=[z for z in rep["zones"] if z["floor_id"]==view.floor_id]
    for cav in cavs:
        if cav.area/U/U < 60: continue
        cid=cids[id(cav)]
        ring=[(int(round(x)),int(round(y))) for x,y in list(cav.exterior.coords)[:-1]]; rp=cav.representative_point()
        raws=[]
        for a,b in zip(ring,ring[1:]+ring[:1]):
            if a[0]==b[0]: ax,c_,lo,hi="y",a[0],min(a[1],b[1]),max(a[1],b[1]); sd=-1 if rp.x<c_ else 1
            else: ax,c_,lo,hi="x",a[1],min(a[0],b[0]),max(a[0],b[0]); sd=-1 if rp.y<c_ else 1
            ow=am._boundary_owners(groups,ax,c_,lo,hi)
            if len(ow)==1: k,g=("faced",ow[0])
            else:
                ec=endcaps(groups,ax,c_,lo,hi); k,g=("endcap",ec[0]) if (not ow and len(ec)==1) else ("AMBIG",None)
            raws.append(dict(axis=ax,const=c_,lo=lo,hi=hi,side=sd,kind=k,grp=g,p1=a,p2=b))
        st=0
        for i,r in enumerate(raws):
            if (raws[i-1]["axis"],raws[i-1]["const"])!=(r["axis"],r["const"]): st=i; break
        rot=raws[st:]+raws[:st]; merged=[]
        for r in rot:
            if merged and (merged[-1]["axis"],merged[-1]["const"])==(r["axis"],r["const"]):
                merged[-1]["lo"]=min(merged[-1]["lo"],r["lo"]); merged[-1]["hi"]=max(merged[-1]["hi"],r["hi"])
            else: merged.append(dict(r))
        proj=[]
        for m in merged:
            if m["kind"]!="faced": continue
            g=m["grp"]; near="lo" if m["side"]<0 else "hi"; far="hi" if near=="lo" else "lo"
            nh,fh=g.handles(near),g.handles(far)
            rn=round(sum(face_by_id[h].const for h in nh)/len(nh)); rf=round(sum(face_by_id[h].const for h in fh)/len(fh))
            sp=am._BoundarySpan(axis=m["axis"],cavity_const=m["const"],lo=m["lo"],hi=m["hi"],side=m["side"],
                                p1=m["p1"],p2=m["p2"],group=g,boundary_condition="unknown")
            cuts=am._boundary_transition_points(sp,rf,footprint,wall_region,cavs)
            th=abs(rf-rn); out=-m["side"]
            for clo,chi in zip(cuts,cuts[1:]):
                ch=am._boundary_subspan(sp,clo,chi)
                cond,_e,log=am._classify_boundary_fact(ch,rn,rf,footprint,rr,wall_region,cavs,cids)
                supp = rn+out*th if cond=="exterior" else rn+out*(th//2)
                proj.append((m["axis"],supp,cond,log))
        d=[]
        for a in proj:
            if not d or (d[-1][0],d[-1][1])!=(a[0],a[1]): d.append(a)
        if len(d)>1 and (d[0][0],d[0][1])==(d[-1][0],d[-1][1]): d.pop()
        vs=[]
        for i,c in enumerate(d):
            p=d[i-1]
            if p[0]==c[0]: vs.append(("PARALLEL",p[:3],c[:3])); continue
            vs.append((p[1],c[1]) if p[0]=="y" else (c[1],p[1]))
        par=[v for v in vs if v and v[0]=="PARALLEL"]
        pts=[v for v in vs if not (v and v[0]=="PARALLEL")]
        dd=[]
        for v in pts:
            if not dd or v!=dd[-1]: dd.append(v)
        if len(dd)>1 and dd[0]==dd[-1]: dd.pop()
        pp=Polygon(dd)
        zid=[z for z in zones if Polygon([(round(q[0]*U),round(q[1]*U)) for q in z["polygon_m"]["exterior"]["vertices"]]).covers(pp.representative_point())]
        z=zid[0] if len(zid)==1 else None
        zp=Polygon([(round(q[0]*U),round(q[1]*U)) for q in z["polygon_m"]["exterior"]["vertices"]]) if z else None
        sdg=pp.symmetric_difference(zp)
        for g_ in getattr(sdg,"geoms",[sdg]):
            b=g_.bounds; print("   DIFF part area_m2=%.4f bounds_m=(%.4f,%.4f)-(%.4f,%.4f)"%(g_.area/U/U,b[0]/U,b[1]/U,b[2]/U,b[3]/U))
        print(f"{view.view_id} {cid} splitproj_edges={len(d)} zone={z['zone_id'] if z else None} zedges={len(z['edges']) if z else None} "
              f"valid={pp.is_valid} area={pp.area/U/U:.6f} zone_area={zp.area/U/U:.6f} "
              f"SYMDIFF={pp.symmetric_difference(zp).area/U/U:.6f} parallel={len(par)}")
        print("   conds:", [(c[2], 'L' if c[3] else 'ILLOGICAL') for c in d])
