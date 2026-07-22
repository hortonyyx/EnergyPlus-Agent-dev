"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

产出稿里的数字：D5 的「外皮缺口 14 处」与 §7-G4 的守恒式。
  - 外皮八条线（四外皮 + 四内皮）逐条覆盖分析
  - 缺口：西 5 / 东 4 / 南 3 / 北 2 = 14，位置与门窗精确对应
  - 内皮线两端各短 240（在角部与垂直内皮线相交，正常）
状态：有效，稿中 §2-D5 与 §7-G4 引用（14 == 14）。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf, collections
from ezdxf import bbox
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
def ins(x,y): return PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
V=collections.defaultdict(list); H=collections.defaultdict(list)
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if not(ins(*a) and ins(*b)) or a==b: continue
        if abs(a[0]-b[0])<1e-9: V[round(a[0],3)].append((min(a[1],b[1]),max(a[1],b[1])))
        else: H[round(a[1],3)].append((min(a[0],b[0]),max(a[0],b[0])))
def merged(iv):
    iv=sorted(iv); m=[list(iv[0])]
    for lo,hi in iv[1:]:
        if lo<=m[-1][1]+1e-6: m[-1][1]=max(m[-1][1],hi)
        else: m.append([lo,hi])
    return m
SKIN={"x=23057.6(W outer)":("V",23057.623,26565.234,46565.234),
      "x=23297.6(W inner)":("V",23297.623,26565.234,46565.234),
      "x=33057.6(E outer)":("V",33057.623,26565.234,46565.234),
      "x=32817.6(E inner)":("V",32817.623,26565.234,46565.234),
      "y=26565.2(S outer)":("H",26565.234,23057.623,33057.623),
      "y=26805.2(S inner)":("H",26805.234,23057.623,33057.623),
      "y=46565.2(N outer)":("H",46565.234,23057.623,33057.623),
      "y=46325.2(N inner)":("H",46325.234,23057.623,33057.623)}
for name,(o,c,lo,hi) in SKIN.items():
    d = V if o=="V" else H
    key=round(c,3)
    if key not in d: print(name,"NO LINES"); continue
    m=merged(d[key])
    gaps=[(round(m[i][1],1),round(m[i+1][0],1),round(m[i+1][0]-m[i][1],1)) for i in range(len(m)-1)]
    head=round(m[0][0]-lo,1); tail=round(hi-m[-1][1],1)
    print(f"{name}: pieces={len(m)} head_missing={head} tail_missing={tail} gaps={gaps}")
