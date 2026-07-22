"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

产出稿里的数字：SURVEY §3.1 的复现 + D3（那个 dangle 是零长度线）。
  - 全 WALL 线直接 polygonize → faces=23 cuts=0 dangles=1 invalid=0
  - 该 dangle 两端点相同：(28817.6, 42565.2) → (28817.6, 42565.2) = 退化 LINE
  - 23 个面的并集只有 12.871 m²、16 个不相连部分 → 证明「直接 polygonize 墙线」拿不到完整墙体域
状态：有效（负面结论），稿中 §2-D3 与 §3.2#4 引用。

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
lines=[]
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if inside(*a) and inside(*b): lines.append(LineString([a,b]))
polys,cuts,dang,inv=polygonize_full(unary_union(lines))
print("raw WALL: faces",len(polys.geoms),"cuts",len(cuts.geoms),"dangles",len(dang.geoms),"invalid",len(inv.geoms))
for g in dang.geoms: print("  DANGLE",[(round(x,1),round(y,1)) for x,y in g.coords])
u=unary_union(list(polys.geoms))
print("union of wall faces: type",u.geom_type,"area m2",round(u.area/1e6,3))
if u.geom_type=="Polygon":
    print("  exterior ring pts",len(u.exterior.coords)-1,"interiors",len(u.interiors))
else:
    for p in u.geoms: print("  part area",round(p.area/1e6,3),"interiors",len(p.interiors))
