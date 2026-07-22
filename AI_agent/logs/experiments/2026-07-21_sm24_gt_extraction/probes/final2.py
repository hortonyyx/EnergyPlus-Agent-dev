"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

★ 主脚本之二（依赖 final.py，先 exec 它复用其结果）。产出稿里 §0 表的后两行：
  - footprint 200.0 m² / wall region 20.84 m²   → §0「墙体材料域 20.84 m²」
  - zones: 8，∑面积 200.000 m²
  - union area 200.000 m² / symmetric diff vs footprint 0.000000 m² → §0「对称差 0」
  - pairwise overlap 0.0 m²                     → §0「两两重叠 0」
  - 区顶点数 4/4/8/6/4/4/4/4（两个非矩形区 = L 形走廊与另一凹形区）
实现的是稿中 §4-S7「逐边测厚 → 远端分类 → 外扩 → 相邻支撑线求交」。
注意：测厚在本探针里用 1mm 步进 + 二分求精（近似）；稿中 §4-S7-1 规定生产实现改为
精确事件计算（无采样参数）。这是探针与方案的已知差异，不影响本轮数字。

【本文件是全部 17 个脚本中唯一有正文改动的一个】
原第 1 行是 exec 一个 scratchpad 绝对路径；落盘后该路径不存在，故改为按 __file__ 定位同目录的
final.py。原行原样保留在下方注释里。除此之外无任何改动。

原样落盘自会话 scratchpad；除本文件头注与上述 exec 路径修正外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
# 【落盘时唯一的正文改动】原行（scratchpad 绝对路径，落盘后不存在）：
# exec(open("/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/777db20f-4da4-4093-bbb3-ec03888153ad/scratchpad/probe/final.py").read())
import pathlib as _pl
exec(open(_pl.Path(__file__).with_name("final.py")).read())
from shapely.geometry import Polygon, Point
faces=list(polys.geoms)
cav=[g for g in faces if g.area>2e6]; wall=unary_union([g for g in faces if g.area<=2e6])
foot=unary_union(faces)
print("\n--- offset step ---")
print("footprint area m2",round(foot.area/1e6,2),"wall area",round(wall.area/1e6,2))
def clean(p):
    c=[(x,y) for x,y in list(p.exterior.coords)[:-1]]
    ch=True
    while ch:
        ch=False
        for i in range(len(c)):
            a,b,d=c[i-1],c[i],c[(i+1)%len(c)]
            if (a[0]==b[0]==d[0]) or (a[1]==b[1]==d[1]): c.pop(i); ch=True; break
    return c
def thickness(mid,nx,ny):
    """march outward from mid until leaving wall region; returns (dist, exit_on_footprint_boundary)"""
    step=1.0; d=step
    while d<2000:
        p=Point(mid[0]+nx*d, mid[1]+ny*d)
        if not wall.covers(p): break
        d+=step
    # refine
    lo,hi=d-step,d
    for _ in range(40):
        m=(lo+hi)/2
        if wall.covers(Point(mid[0]+nx*m, mid[1]+ny*m)): lo=m
        else: hi=m
    ex=Point(mid[0]+nx*hi, mid[1]+ny*hi)
    return hi, foot.exterior.distance(ex)<1.0
zones=[]
for g in cav:
    c=clean(g)
    if not Polygon(c).exterior.is_ccw: c=c[::-1]
    n=len(c); off=[]
    for i in range(n):
        a,b=c[i],c[(i+1)%n]
        mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
        nx,ny=(0,-1) if (a[1]==b[1] and b[0]>a[0]) else (0,1) if a[1]==b[1] else ((1,0) if b[1]>a[1] else (-1,0))
        t,ext=thickness(mid,nx,ny)
        d = t if ext else t/2.0
        off.append((a,b,nx,ny,d))
    verts=[]
    for i in range(n):
        pa,_,nax,nay,da=off[i-1]; _,_,nbx,nby,db=off[i]
        v=c[i]
        vx=v[0]+ (nax*da if nax else 0) + (nbx*db if nbx else 0)
        vy=v[1]+ (nay*da if nay else 0) + (nby*db if nby else 0)
        verts.append((round(vx,3),round(vy,3)))
    zones.append(Polygon(verts))
tot=unary_union(zones)
print("zones:",len(zones),"sum area m2",round(sum(z.area for z in zones)/1e6,3))
print("union area m2",round(tot.area/1e6,3))
print("symmetric diff vs footprint (m2):",round(tot.symmetric_difference(foot).area/1e6,6))
ov=sum(zones[i].intersection(zones[j]).area for i in range(len(zones)) for j in range(i+1,len(zones)))
print("pairwise overlap m2:",round(ov/1e6,6))
for z in sorted(zones,key=lambda z:-z.area): print("   zone area",round(z.area/1e6,2),"verts",len(z.exterior.coords)-1)
