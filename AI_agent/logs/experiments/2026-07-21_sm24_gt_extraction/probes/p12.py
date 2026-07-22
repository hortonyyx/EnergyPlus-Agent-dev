"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

探索过程：只拿外皮线 + 手写 14 个缺口填充，单独测外皮闭合。
  - faces=0 dangles=48 → 外皮在「已知全部缺口都补上」的情况下**仍不成环**
  - 由此定位真因：坐标带亚微米噪声（角点差 1e-11），未量化则 unary_union 不结点
状态：有效（关键诊断）。稿中 §4-S1「没有量化这一步后面全崩」的实证来源。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf, collections
from shapely.geometry import LineString
from shapely.ops import polygonize_full, unary_union, linemerge
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
def ins(x,y): return PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
X0,X1,Y0,Y1=23057.62328360734,33057.62328360733,26565.23354697024,46565.23354697024
sk=[]
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if not(ins(*a) and ins(*b)) or a==b: continue
        T=1e-3
        if (abs(a[0]-X0)<T and abs(b[0]-X0)<T) or (abs(a[0]-X1)<T and abs(b[0]-X1)<T) \
           or (abs(a[1]-Y0)<T and abs(b[1]-Y0)<T) or (abs(a[1]-Y1)<T and abs(b[1]-Y1)<T):
            sk.append(LineString([a,b]))
fills=[(X0,27105.23354697024,X0,31905.23354697024),(X0,34985.23354697024,X0,36485.23354697024),
       (X0,37705.23354697024,X0,39205.23354697024),(X0,40945.23354697023,X0,42145.23354697023),
       (X0,44525.23354697024,X0,46025.23354697024),
       (X1,32265.23354697024,X1,33865.23354697024),(X1,35405.23354697024,X1,40205.23354697024),
       (X1,40945.23354697023,X1,42145.23354697023),(X1,44525.23354697024,X1,46025.23354697024),
       (23597.62328360734,Y0,25097.62328360734,Y0),(27597.62328360734,Y0,28497.62328360734,Y0),
       (31017.62328360733,Y0,32517.62328360733,Y0),
       (23597.62328360734,Y1,25197.62328360734,Y1),(27717.62328360733,Y1,32517.62328360733,Y1)]
sk+= [LineString([(a,b),(c,d)]) for a,b,c,d in fills]
print("skin segs",len(sk))
u=unary_union(sk)
polys,cuts,dang,inv=polygonize_full(u)
print("skin-only: faces",len(polys.geoms),"dangles",len(dang.geoms),"cuts",len(cuts.geoms))
for g in polys.geoms: print("   area m2",round(g.area/1e6,2),"verts",len(g.exterior.coords)-1)
for g in list(dang.geoms)[:6]: print("   DANGLE",[(round(x,2),round(y,2)) for x,y in g.coords])
