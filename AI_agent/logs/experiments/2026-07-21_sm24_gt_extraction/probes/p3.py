"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

探索过程：只补窗洞（不补门洞）后 polygonize。
  - faces=48 dangles=1，最大面 1.486 m²，>5 m² 的面 0 个 → 房间仍未围出
状态：中间态/死胡同。保留用于说明「只补窗不补门不够」。稿中未直接引数字。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf
from ezdxf import bbox
from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize_full, unary_union
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
def inside(x,y): return PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
lines=[]; degen=0
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if not(inside(*a) and inside(*b)): continue
        if a==b: degen+=1; continue
        lines.append(LineString([a,b]))
print("degenerate zero-length WALL lines dropped:",degen,"kept:",len(lines))
# opening fill rects: windows = exact bbox; doors = along-span x wall band (approximate via bbox clipped to wall coords)
fills=[]
for e in msp:
    if e.dxftype()=="INSERT" and e.dxf.layer=="WINDOW":
        ext=bbox.extents([e]); p=(float(ext.extmin.x),float(ext.extmin.y),float(ext.extmax.x),float(ext.extmax.y))
        if not inside(p[0],p[1]): continue
        fills.append((e.dxf.name,e.dxf.handle,p))
# add window fills as rect outlines
segs=list(lines)
def rect_lines(x0,y0,x1,y1):
    c=[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
    return [LineString([c[i],c[i+1]]) for i in range(4)]
wins=[f for f in fills if f[0]=="$TCHSYS$WIN2D"]
for n,h,p in wins: segs+=rect_lines(*p)
polys,cuts,dang,inv=polygonize_full(unary_union(segs))
print("WALL+window rects: faces",len(polys.geoms),"cuts",len(cuts.geoms),"dangles",len(dang.geoms))
ar=sorted(((round(g.area/1e6,3),round(g.bounds[0]),round(g.bounds[1])) for g in polys.geoms),reverse=True)
print("top face areas m2:",ar[:14])
print("n faces >5 m2:",sum(1 for a in ar if a[0]>5))
