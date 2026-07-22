"""只读探针 — 2026-07-21 sm24 天正 DXF → GT v3 转换器方案出稿

产出稿里的数字：§5.2「纯几何续接规则高精度低召回」的 12/21。
  - 加「墙侧线在缺口两侧续接」判据后 → 12 个候选，逐个核对全部是真洞口（零假阳性）
  - 但只覆盖 21 个洞口中的 12 个（漏掉被丁字接头打断侧线连续性的那些）
状态：有效，稿中 §4-S3 与 §5.2 直接引用（12/21、零假阳性）。

原样落盘自会话 scratchpad；除本文件头注外，正文未作任何修改。
只读：不写仓库、不改 DXF。
"""
import ezdxf, itertools, collections
from ezdxf import bbox
D="/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-07-21_sm24_gt_extraction/work/sm24_source.dxf"
doc=ezdxf.readfile(D); msp=doc.modelspace()
PLAN=(12276.94,18802.14,41994.33,51678.57)
def ins(x,y): return PLAN[0]<x<PLAN[2] and PLAN[1]<y<PLAN[3]
V=collections.defaultdict(list); H=collections.defaultdict(list)   # coord -> list of intervals
short=[]
for e in msp:
    if e.dxf.layer=="WALL" and e.dxftype()=="LINE":
        a=(float(e.dxf.start.x),float(e.dxf.start.y)); b=(float(e.dxf.end.x),float(e.dxf.end.y))
        if not(ins(*a) and ins(*b)) or a==b: continue
        if a[0]==b[0]: V[round(a[0],4)].append((min(a[1],b[1]),max(a[1],b[1])))
        else: H[round(a[1],4)].append((min(a[0],b[0]),max(a[0],b[0])))
def cov(d):
    out={}
    for c,iv in d.items():
        iv=sorted(iv); m=[list(iv[0])]
        for lo,hi in iv[1:]:
            if lo<=m[-1][1]+1e-6: m[-1][1]=max(m[-1][1],hi)
            else: m.append([lo,hi])
        out[c]=m
    return out
Vc,Hc=cov(V),cov(H)
EPS=1e-6
def openings(par, perp, orient):
    """par: coord->merged intervals of the two side lines; perp: the cap lines"""
    res=[]
    coords=sorted(par)
    for c1,c2 in itertools.combinations(coords,2):
        t=c2-c1
        if not (60<=t<=500): continue          # plausible wall band thickness range
        for g1 in par[c1]:
            for g2 in par[c2]:
                lo=max(g1[0],g2[0]); hi=min(g1[1],g2[1])
                if hi-lo<EPS: continue
        # find gaps present on BOTH side lines at same interval
        def gaps(iv):
            return [(iv[i][1],iv[i+1][0]) for i in range(len(iv)-1)]
        g1=gaps(par[c1]); g2=gaps(par[c2])
        for a in g1:
            for b in g2:
                if abs(a[0]-b[0])<1e-6 and abs(a[1]-b[1])<1e-6:
                    # caps present at both ends spanning [c1,c2]?
                    def cap(pos):
                        return any(abs(x-pos)<1e-6 and any(l-1e-6<=c1 and h+1e-6>=c2 for l,h in perp[x]) for x in perp)
                    res.append((orient,round(c1,1),round(c2,1),round(a[0],1),round(a[1],1),round(a[1]-a[0],1),cap(a[0]) and cap(a[1])))
    return res
res = openings(Vc,Hc,"V") + openings(Hc,Vc,"H")
print("continuation-rule opening candidates:",len(res))
for r in sorted(res): print("  ",r)
