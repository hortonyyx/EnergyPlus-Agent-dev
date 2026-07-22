"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

★ 主脚本之一。产出稿里 §0 表的前六行：
  - degenerate wall lines: 0（量化后）| kept 132 | 端头 V/H = 34/39
  - openings: resolved 21 / unresolved 0        → §0「洞口解析 21/21」
  - polygonize: faces 51 dangles 0 cuts 0 invalid 0 → §0「拓扑三项全 0」
  - total face area 200.0 m²                    → §0「面域守恒 200.00 m²」
  - CAVITIES(>2m2): 8，合计 179.16 m²            → §0「腔体 8 个」
  - 其中 area 30.82 / bounds x[27298,32818] y[30065,42445] → §0「L 走廊天然单面 30.82 m²」
与前面探针的差别：量化（Q=0.1mm）贯穿墙线与端头两侧 —— 这是唯一让拓扑闭合的改动。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf
from ezdxf import bbox
from shapely.geometry import LineString
from shapely.ops import polygonize_full, unary_union
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
ins=lambda x,y: PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
Q=lambda v: round(v*10)/10.0
segs=[]; capV=[]; capH=[]; ndeg=0
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if not(ins(*a) and ins(*b)): continue
        a=(Q(a[0]),Q(a[1])); b=(Q(b[0]),Q(b[1]))
        if a==b: ndeg+=1; continue
        segs.append(LineString([a,b]))
        if a[0]==b[0]:
            L=abs(a[1]-b[1])
            if 60<=L<=500: capV.append((a[0],min(a[1],b[1]),max(a[1],b[1])))
        else:
            L=abs(a[0]-b[0])
            if 60<=L<=500: capH.append((a[1],min(a[0],b[0]),max(a[0],b[0])))
print("degenerate wall lines:",ndeg,"| kept:",len(segs),"| jamb caps V/H:",len(capV),len(capH))
def resolve(x0,y0,x1,y1):
    out=set(); nrm={"x":(y0,y1),"y":(x0,x1)}
    for axis,(lo,hi),caps in (("x",(x0,x1),capV),("y",(y0,y1),capH)):
        A=[c for c in caps if c[0]==lo]; B=[c for c in caps if c[0]==hi]
        for a in A:
            for b in B:
                if a[1]==b[1] and a[2]==b[2]:
                    n0,n1=nrm[axis]
                    if min(a[2],n1)-max(a[1],n0) > 0: out.add((axis,lo,hi,a[1],a[2]))
    return sorted(out)
fills=[]; unres=[]
for e in msp:
    if e.dxftype()=="INSERT" and e.dxf.layer=="WINDOW":
        ext=bbox.extents([e]); p=[Q(float(v)) for v in (ext.extmin.x,ext.extmin.y,ext.extmax.x,ext.extmax.y)]
        if not ins(p[0],p[1]): continue
        r=resolve(*p)
        if len(r)!=1: unres.append((e.dxf.name,e.dxf.handle,r)); continue
        ax,lo,hi,c1,c2=r[0]
        fills.append((e.dxf.handle,e.dxf.name,(lo,c1,hi,c2) if ax=="x" else (c1,lo,c2,hi)))
print("openings: resolved",len(fills),"unresolved",len(unres))
for u in unres: print("   UNRES",u)
for h,n,(x0,y0,x1,y1) in fills:
    c=[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
    segs+=[LineString([c[i],c[i+1]]) for i in range(4)]
polys,cuts,dang,inv=polygonize_full(unary_union(segs))
print("polygonize: faces",len(polys.geoms),"dangles",len(dang.geoms),"cuts",len(cuts.geoms),"invalid",len(inv.geoms))
print("total face area m2",round(sum(g.area for g in polys.geoms)/1e6,2))
big=sorted((g for g in polys.geoms if g.area>2e6),key=lambda g:-g.area)
print("CAVITIES(>2m2):",len(big),"sum",round(sum(g.area for g in big)/1e6,2))
for g in big:
    print("   area",round(g.area/1e6,2),"verts",len(g.exterior.coords)-1,"bounds",[round(v) for v in g.bounds])
