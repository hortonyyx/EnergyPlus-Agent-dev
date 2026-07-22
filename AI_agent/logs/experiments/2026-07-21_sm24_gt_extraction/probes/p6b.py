"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

探索过程：p6.py 的补丁版（放宽比较容差 1e-6→1e-3，两轴歧义判定）。
  - openings resolved 16/21，faces=55 dangles=1，仍无房间面
状态：中间态。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf, collections
from ezdxf import bbox
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize_full, unary_union
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
def ins(x,y): return PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
Vl=collections.defaultdict(list); Hl=collections.defaultdict(list); segs=[]
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if not(ins(*a) and ins(*b)) or a==b: continue
        segs.append(LineString([a,b]))
        if a[0]==b[0]: Vl[round(a[0],4)].append((min(a[1],b[1]),max(a[1],b[1])))
        else: Hl[round(a[1],4)].append((min(a[0],b[0]),max(a[0],b[0])))
def band_from_caps(caps, lo, hi):
    """caps: coord->intervals (perpendicular lines). find [c1,c2] covered by a cap at lo and at hi"""
    cands=[]
    for c,ivs in caps.items():
        pass
    A=[iv for c,ivs in caps.items() if abs(c-lo)<1e-3 for iv in ivs]
    B=[iv for c,ivs in caps.items() if abs(c-hi)<1e-3 for iv in ivs]
    for a in A:
        for b in B:
            l=max(a[0],b[0]); h=min(a[1],b[1])
            if 60-1e-3<=h-l<=500+1e-3: cands.append((round(l,4),round(h,4)))
    return sorted(set(cands))
fills=[]; report=[]
for e in msp:
    if e.dxftype()=="INSERT" and e.dxf.layer=="WINDOW":
        ext=bbox.extents([e]); x0,y0,x1,y1=float(ext.extmin.x),float(ext.extmin.y),float(ext.extmax.x),float(ext.extmax.y)
        if not ins(x0,y0): continue
        got=None; hits=[]
        for axis in ("x","y"):
            lo,hi=(round(x0,4),round(x1,4)) if axis=="x" else (round(y0,4),round(y1,4))
            caps = Vl if axis=="x" else Hl
            b=band_from_caps(caps,lo,hi)
            if len(b)==1: hits.append((axis,lo,hi,b[0]))
        got = hits[0] if len(hits)==1 else None
        report.append((e.dxf.name,e.dxf.handle,got if got else ("AMBIG" if hits else None)))
        if got:
            axis,lo,hi,(c1,c2)=got
            r=(lo,c1,hi,c2) if axis=="x" else (c1,lo,c2,hi)
            fills.append(r)
print("openings resolved:",sum(1 for r in report if r[2]),"/",len(report))
for n,h,g in report:
    if not g: print("  UNRESOLVED",n,h)
for x0,y0,x1,y1 in fills:
    c=[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
    segs+= [LineString([c[i],c[i+1]]) for i in range(4)]
polys,cuts,dang,inv=polygonize_full(unary_union(segs))
print("after fill: faces",len(polys.geoms),"dangles",len(dang.geoms),"cuts",len(cuts.geoms))
big=sorted((g for g in polys.geoms if g.area>3e6), key=lambda g:-g.area)
print("faces > 3 m2:",len(big))
for g in big:
    print("   area",round(g.area/1e6,2),"verts",len(g.exterior.coords)-1,"bounds",[round(v) for v in g.bounds])
