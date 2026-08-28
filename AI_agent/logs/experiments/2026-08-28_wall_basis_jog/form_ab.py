"""把现有 gt 多边形（形式 B）逐边重解释成形式 A，数两种形式各自的转折。⛔ 探索档。"""
import sys, json, math
from pathlib import Path
REPO = Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0, str(REPO))
from src.agent.judge.as_drawn.denominator import denominator
EPS = 1e-6
SRC = REPO/"case_tests/test_baseline/gt_sources/sm25-L_anchor"

def walls(d):
    ts, used, out = d["targets"], set(), []
    for i,a in enumerate(ts):
        if i in used: continue
        best=None
        for j,b in enumerate(ts):
            if j<=i or j in used or a["axis"]!=b["axis"]: continue
            ov=min(a["hi_m"],b["hi_m"])-max(a["lo_m"],b["lo_m"]); gap=abs(a["const_m"]-b["const_m"])
            if ov<=0 or gap<1e-9: continue
            if best is None or gap<best[0]: best=(gap,j,b)
        if best:
            gap,j,b=best; used|={i,j}; f0,f1=sorted((a["const_m"],b["const_m"]))
            out.append({"axis":a["axis"],"f0":f0,"f1":f1,"mid":(f0+f1)/2,"t":gap,
                        "lo":max(a["lo_m"],b["lo_m"]),"hi":min(a["hi_m"],b["hi_m"])})
    return out

def classify(edge_axis, const, lo, hi, W):
    """这条多边形边走的是哪堵墙的哪条线？返回 (basis, wall)。"""
    # 多边形边沿 edge_axis 方向常数为 const；墙的 axis 用 denominator 的口径
    cands=[]
    for w in W:
        if w["axis"]!=edge_axis: continue
        ov = min(hi,w["hi"]) - max(lo,w["lo"])
        if ov <= 1e-4: continue
        if not (w["f0"]-1e-4 <= const <= w["f1"]+1e-4): continue
        cands.append((ov,w))
    if not cands: return ("no_wall", None)
    ov,w = max(cands, key=lambda t:t[0])
    if abs(w["mid"]-const) < 1e-4: return ("centerline", w)
    if abs(w["f0"]-const) < 1e-4 or abs(w["f1"]-const) < 1e-4: return ("face", w)
    return ("inside_band", w)

gt = json.load(open(REPO/"case_tests/test_baseline/gt/sm25-L_anchor/gt.json", encoding="utf-8"))
for fl, view in zip(gt["floors"], ("plan-F1","plan-F2")):
    W = walls(denominator(SRC/"sm25-L_t3.dxf", SRC/"request.json", view))
    print(f"\n{'='*78}\n{fl['id']}   墙 {len(W)} 段")
    tot_short_B = tot_short_A = 0
    basis_hist = {}
    for z in fl["zones"]:
        V = z["polygon"]["exterior"]["vertices"]; n=len(V)
        # 每条边：axis + const + [lo,hi]
        edges=[]
        for i in range(n):
            a,b = V[i], V[(i+1)%n]
            if abs(a[1]-b[1])<EPS:   # 水平边 → 常数是 y，denominator 里这类墙 axis 记什么？
                edges.append(("y", a[1], min(a[0],b[0]), max(a[0],b[0])))
            else:
                edges.append(("x", a[0], min(a[1],b[1]), max(a[1],b[1])))
        newc=[]
        for (ax,c,lo,hi) in edges:
            basis,w = classify(ax,c,lo,hi,W)
            basis_hist[basis]=basis_hist.get(basis,0)+1
            newc.append(w["mid"] if (basis=="face" and w) else c)
        # 重建顶点：顶点 i 由边 i-1 与边 i 相交
        newV=[]
        for i in range(n):
            e_prev, e_cur = edges[i-1], edges[i]
            cp, cc = newc[i-1], newc[i]
            x = cp if e_prev[0]=="x" else cc
            y = cp if e_prev[0]=="y" else cc
            newV.append((x,y))
        def shorts(P):
            out=[]
            for i in range(len(P)):
                a,b=P[i],P[(i+1)%len(P)]
                L=math.hypot(b[0]-a[0],b[1]-a[1])
                if L < 0.30: out.append(round(L*1000,1))
            return out
        sB, sA = shorts([tuple(v) for v in V]), shorts(newV)
        tot_short_B += len(sB); tot_short_A += len(sA)
        if sB or sA:
            print(f"   {z['id']:8s} 形式B短边 {sB}   形式A短边 {sA}")
    print(f"   ── 合计：形式 B 短边 {tot_short_B} 条 · 形式 A 短边 {tot_short_A} 条")
    print(f"   ── 边的基准分布：{basis_hist}")
