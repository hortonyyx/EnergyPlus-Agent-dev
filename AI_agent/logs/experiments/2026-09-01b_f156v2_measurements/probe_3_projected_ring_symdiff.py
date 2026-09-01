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

def endcaps(groups, axis, const, lo, hi):
    out=[]
    for g in groups.values():
        if g.axis==axis: continue
        for w in g.runs:
            if const in (w.along_min,w.along_max) and min(hi,w.face_hi)-max(lo,w.face_lo)>0:
                out.append(g); break
    return out

def parallel_face_at(groups, axis, const):
    """Is the segment's const also a measured face of a band parallel to the segment?"""
    return [g.key for g in groups.values() if g.axis==axis and const in (g.face_lo,g.face_hi)]

tot=0; ok=0
for view in doc.views:
    groups = am._boundary_wall_groups(view)
    footprint, ring_records = am._boundary_footprint(view)
    wall_region = am._boundary_wall_region(view)
    face_by_id = {f.id:f for f in view.face_lines}
    geom = footprint.difference(wall_region); thr = MIN*U*U
    cavities=[p for p in getattr(geom,"geoms",[geom]) if p.geom_type=="Polygon" and not p.is_empty and p.area>thr]
    cavities.sort(key=lambda c: tuple(round(v,6) for v in c.bounds))
    cids={id(c):am._boundary_cavity_id(view.view_id,c) for c in cavities}
    zones=[z for z in rep["zones"] if z["floor_id"]==view.floor_id]
    for cav in cavities:
        cid=cids[id(cav)]
        ring=[(int(round(x)),int(round(y))) for x,y in list(cav.exterior.coords)[:-1]]
        rp=cav.representative_point(); raws=[]
        for a,b in zip(ring,ring[1:]+ring[:1]):
            if a[0]==b[0]: axis,const,lo,hi="y",a[0],min(a[1],b[1]),max(a[1],b[1]); side=-1 if rp.x<const else 1
            else: axis,const,lo,hi="x",a[1],min(a[0],b[0]),max(a[0],b[0]); side=-1 if rp.y<const else 1
            ow=am._boundary_owners(groups,axis,const,lo,hi)
            if len(ow)==1: kind,grp="faced",ow[0]
            else:
                ec=endcaps(groups,axis,const,lo,hi)
                kind,grp=("endcap",ec[0]) if (not ow and len(ec)==1) else ("AMBIG",None)
            raws.append(dict(axis=axis,const=const,lo=lo,hi=hi,side=side,kind=kind,grp=grp,p1=a,p2=b))
        st=0
        for i,r in enumerate(raws):
            if (raws[i-1]["axis"],raws[i-1]["const"])!=(r["axis"],r["const"]): st=i; break
        rot=raws[st:]+raws[:st]; merged=[]
        for r in rot:
            if merged and (merged[-1]["axis"],merged[-1]["const"])==(r["axis"],r["const"]):
                merged[-1]["lo"]=min(merged[-1]["lo"],r["lo"]); merged[-1]["hi"]=max(merged[-1]["hi"],r["hi"])
            else: merged.append(dict(r))
        # endcap admissibility probe
        bad_end=[(m["axis"],m["const"],m["lo"],m["hi"]) for m in merged
                 if m["kind"]=="endcap" and not parallel_face_at(groups,m["axis"],m["const"])]
        # project faced supports
        proj=[]; skip=False
        for m in merged:
            if m["kind"]!="faced": continue
            g=m["grp"]; near="lo" if m["side"]<0 else "hi"; far="hi" if near=="lo" else "lo"
            nh,fh=g.handles(near),g.handles(far)
            rn=round(sum(face_by_id[h].const for h in nh)/len(nh)); rf=round(sum(face_by_id[h].const for h in fh)/len(fh))
            sp=am._BoundarySpan(axis=m["axis"],cavity_const=m["const"],lo=m["lo"],hi=m["hi"],side=m["side"],
                                p1=m["p1"],p2=m["p2"],group=g,boundary_condition="unknown")
            cond,_e,log=am._classify_boundary_fact(sp,rn,rf,footprint,ring_records,wall_region,cavities,cids)
            th=abs(rf-rn); out=-m["side"]
            supp = rn+out*th if cond=="exterior" else rn+out*(th//2)
            proj.append((m["axis"],supp))
        # dedupe consecutive same support, then intersect
        d=[]
        for a in proj:
            if not d or d[-1]!=a: d.append(a)
        if len(d)>1 and d[0]==d[-1]: d.pop()
        vs=[]; par=False
        for i,c in enumerate(d):
            p=d[i-1]
            if p[0]==c[0]: par=True; break
            vs.append((p[1],c[1]) if p[0]=="y" else (c[1],p[1]))
        dd=[]
        for v in vs:
            if not dd or v!=dd[-1]: dd.append(v)
        if len(dd)>1 and dd[0]==dd[-1]: dd.pop()
        pp=Polygon(dd) if (not par and len(dd)>=3) else None
        raw_poly=None
        # zone via raw clear-span ring rep point
        rv=[]
        for i,c in enumerate(merged):
            p=merged[i-1]
            if p["axis"]==c["axis"]: rv=[]; break
            rv.append((p["const"],c["const"]) if p["axis"]=="y" else (c["const"],p["const"]))
        raw_poly=Polygon(rv) if len(rv)>=3 else None
        zid=[z for z in zones if raw_poly is not None and Polygon([(round(q[0]*U),round(q[1]*U)) for q in z["polygon_m"]["exterior"]["vertices"]]).covers(raw_poly.representative_point())]
        line=f"{view.view_id} {cid} area={cav.area/U/U:8.3f} merged={len(merged)} faced={sum(1 for m in merged if m['kind']=='faced')} endcap={sum(1 for m in merged if m['kind']=='endcap')} projedges={len(d)}"
        if len(zid)==1:
            z=zid[0]; zp=Polygon([(round(q[0]*U),round(q[1]*U)) for q in z["polygon_m"]["exterior"]["vertices"]])
            sd = pp.symmetric_difference(zp).area/U/U if pp is not None and pp.is_valid else float('nan')
            tot+=1; ok+= (sd==0.0)
            line+=f" zone={z['zone_id']} zedges={len(z['edges'])} PROJ_SYMDIFF={sd:.6f} projvalid={pp.is_valid if pp is not None else None}"
        else:
            line+=f" zones={[z['zone_id'] for z in zid]}"
        if bad_end: line+=f" ⛔BAD_ENDCAP={bad_end}"
        print(line)
print(f"\nprojected symdiff == 0 : {ok}/{tot}")
