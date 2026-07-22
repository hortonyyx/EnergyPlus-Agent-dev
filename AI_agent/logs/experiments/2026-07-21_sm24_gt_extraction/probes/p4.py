"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

探索过程：第一版「端头配对」缺口检测（仅按同截面端头配对）。
  - 产出 54 个候选，含大量假阳性（band 0.0 的退化匹配、4800 长的房间跨度）
状态：中间态/死胡同（判据过松）。稿中未直接引数字，但它是 §4-S3「不能只靠端头配对」的由来。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf, itertools
from ezdxf import bbox
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize_full, unary_union
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
def inside(x,y): return PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
W=[]
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if inside(*a) and inside(*b) and a!=b: W.append((a,b))
# jamb candidates = short lines (<=400 long)
def kind(a,b):
    return ("V",a[0],min(a[1],b[1]),max(a[1],b[1])) if a[0]==b[0] else ("H",a[1],min(a[0],b[0]),max(a[0],b[0]))
K=[kind(a,b) for a,b in W]
short=[k for k in K if k[3]-k[2]<=400+1e-6]
print("short(jamb-ish) lines:",len(short), "thicknesses seen:",sorted({round(k[3]-k[2],1) for k in short}))
# facing jamb pairs: same orientation, same span interval (the band), different position, no wall line between along band
fills=[]
for o in ("V","H"):
    ss=[k for k in short if k[0]==o]
    for a,b in itertools.combinations(ss,2):
        if abs(a[2]-b[2])>1e-6 or abs(a[3]-b[3])>1e-6: continue   # same band cross-section
        gap=abs(a[1]-b[1])
        if gap<1e-6 or gap>6000: continue
        lo,hi=sorted((a[1],b[1]))
        # ensure no other jamb of same band strictly inside
        if any(lo-1e-6<c[1]<hi+1e-6 and abs(c[2]-a[2])<1e-6 and abs(c[3]-a[3])<1e-6 and abs(c[1]-lo)>1e-6 and abs(c[1]-hi)>1e-6 for c in ss): continue
        fills.append((o,lo,hi,a[2],a[3]))
print("candidate opening fills:",len(fills))
for f in sorted(fills): print("   ",f[0],"span",round(f[2]-f[1],1),"band",round(f[4]-f[3],1),"at",round(f[1]),round(f[3]))
