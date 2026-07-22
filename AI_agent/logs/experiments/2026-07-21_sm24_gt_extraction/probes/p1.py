"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

产出稿里的数字：D1（墙厚不统一）与 D2（门块 bbox 含开启扇）。
  - 132 墙线 = 67 竖 + 65 横，零斜线
  - 竖墙 x 聚类与相邻差 → 外墙 240 / 内墙 120（推翻 SURVEY §5 线索3「统一 240」）
  - 21 个 WINDOW 层 INSERT 的 bbox：窗 $TCHSYS$WIN2D 恒为 洞宽×240；
    门 $DorLib2D$ 含开启扇（AC3=1600x780、AC9=780x1600、内门 877.5x900）
状态：有效，稿中 §2-D1 / §2-D2 直接引用。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf, collections
from ezdxf import bbox
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
def inside(x,y): return PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
walls=[]
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if inside(*a) and inside(*b): walls.append((a,b,e.dxf.handle))
print("wall lines in plan:",len(walls))
vert=[w for w in walls if abs(w[0][0]-w[1][0])<1e-6]
horz=[w for w in walls if abs(w[0][1]-w[1][1])<1e-6]
print("vert",len(vert),"horz",len(horz),"other",len(walls)-len(vert)-len(horz))
xs=sorted({round(w[0][0],3) for w in vert}); ys=sorted({round(w[0][1],3) for w in horz})
print("x coords:",xs)
print("y coords:",ys)
print("x gaps:",[round(b-a,1) for a,b in zip(xs,xs[1:])])
print("y gaps:",[round(b-a,1) for a,b in zip(ys,ys[1:])])
# opening blocks in plan
for e in msp:
    if e.dxftype()=="INSERT" and e.dxf.layer=="WINDOW":
        ext=bbox.extents([e])
        p=(float(ext.extmin.x),float(ext.extmin.y),float(ext.extmax.x),float(ext.extmax.y))
        if inside(p[0],p[1]):
            print("INSERT",e.dxf.name,e.dxf.handle,[round(v,1) for v in p],"w=",round(p[2]-p[0],1),"h=",round(p[3]-p[1],1))
