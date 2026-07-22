"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

探索过程：p9.py 加 FILL 明细与总面积打印。
  - 21 个补洞矩形逐个打印，全部与墙带精确贴合（例 AC3 → 23597.6,46325.2–25197.6,46565.2）
  - 但 total face area 20.84 m²、rooms 0 → 补洞正确、拓扑仍不闭合
状态：有效（关键诊断）。稿中 §5.2 引用的 AC3 修正后矩形出自这里。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf, collections
from ezdxf import bbox
from shapely.geometry import LineString
from shapely.ops import polygonize_full, unary_union
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
def ins(x,y): return PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
segs=[]; capV=[]; capH=[]   # cap = short line (60..500) : (coord, lo, hi)
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if not(ins(*a) and ins(*b)) or a==b: continue
        segs.append(LineString([a,b]))
        if abs(a[0]-b[0])<1e-9:
            L=abs(a[1]-b[1])
            if 60<=L<=500: capV.append((a[0],min(a[1],b[1]),max(a[1],b[1])))
        else:
            L=abs(a[0]-b[0])
            if 60<=L<=500: capH.append((a[1],min(a[0],b[0]),max(a[0],b[0])))
T=1e-3
def resolve(x0,y0,x1,y1):
    nrm={'x':(y0,y1),'y':(x0,x1)}
    out=[]
    for axis,(lo,hi),caps in (("x",(x0,x1),capV),("y",(y0,y1),capH)):
        A=[c for c in caps if abs(c[0]-lo)<T]; B=[c for c in caps if abs(c[0]-hi)<T]
        for a in A:
            for b in B:
                if abs(a[1]-b[1])<T and abs(a[2]-b[2])<T:
                    n0,n1=nrm[axis]
                    if min(a[2],n1)-max(a[1],n0) > T: out.append((axis,lo,hi,a[1],a[2]))
    return sorted(set(out))
fills=[]; unres=[]
for e in msp:
    if e.dxftype()=="INSERT" and e.dxf.layer=="WINDOW":
        ext=bbox.extents([e]); x0,y0,x1,y1=float(ext.extmin.x),float(ext.extmin.y),float(ext.extmax.x),float(ext.extmax.y)
        if not ins(x0,y0): continue
        r=resolve(x0,y0,x1,y1)
        if len(r)!=1: unres.append((e.dxf.name,e.dxf.handle,len(r),r)); continue
        axis,lo,hi,c1,c2=r[0]
        fills.append((e.dxf.handle,e.dxf.name,(lo,c1,hi,c2) if axis=="x" else (c1,lo,c2,hi)))
print("resolved",len(fills),"unresolved",len(unres))
for h,n,r in sorted(fills,key=lambda t:t[0]): print("   FILL",h,n,[round(v,1) for v in r])
for u in unres: print("  UNRES",u[0],u[1],"cands",u[2],u[3])
for h,n,(x0,y0,x1,y1) in fills:
    c=[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
    segs+=[LineString([c[i],c[i+1]]) for i in range(4)]
polys,cuts,dang,inv=polygonize_full(unary_union(segs))
print("faces",len(polys.geoms),"dangles",len(dang.geoms),"cuts",len(cuts.geoms))
print("total face area m2",round(sum(g.area for g in polys.geoms)/1e6,2))
big=sorted((g for g in polys.geoms if g.area>2e6),key=lambda g:-g.area)
print("rooms(>2m2):",len(big),"sum m2",round(sum(g.area for g in big)/1e6,2))
for g in big: print("   area",round(g.area/1e6,2),"verts",len(g.exterior.coords)-1,"bounds",[round(v) for v in g.bounds])
