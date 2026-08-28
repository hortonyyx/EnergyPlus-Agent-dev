"""放宽搜索：任意【近共线 + 厚度不同】的墙对，报对齐关系。⛔ 探索档。"""
import sys
from pathlib import Path
REPO = Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0, str(REPO))
from src.agent.judge.as_drawn.denominator import denominator
def walls(d):
    ts, used, out = d["targets"], set(), []
    for i, a in enumerate(ts):
        if i in used: continue
        best=None
        for j, b in enumerate(ts):
            if j<=i or j in used or a["axis"]!=b["axis"]: continue
            ov=min(a["hi_m"],b["hi_m"])-max(a["lo_m"],b["lo_m"]); gap=abs(a["const_m"]-b["const_m"])
            if ov<=0 or gap<1e-9: continue
            if best is None or gap<best[0]: best=(gap,j,b,ov)
        if best:
            gap,j,b,ov=best; used|={i,j}; f0,f1=sorted((a["const_m"],b["const_m"]))
            out.append({"axis":a["axis"],"f0":f0,"f1":f1,"mid":(f0+f1)/2,"t":gap,
                        "lo":max(a["lo_m"],b["lo_m"]),"hi":min(a["hi_m"],b["hi_m"])})
    return out
for case, dxfname, views in (("sm25-L_anchor","sm25-L_t3.dxf",("plan-F1","plan-F2")),
                             ("sm24_anchor",None,None)):
    SRC = REPO/"case_tests/test_baseline/gt_sources"/case
    if dxfname is None:
        dxfs=list(SRC.glob("*.dxf")); dxfname=[p.name for p in dxfs if "as_received" not in p.name][0]
        import json as J; r=J.loads((SRC/"request.json").read_text()); views=tuple(v["id"] for v in r["plan_views"])
    for view in views:
        W = walls(denominator(SRC/dxfname, SRC/"request.json", view))
        print(f"\n######## {case} / {view}: {len(W)} 段墙")
        found=0
        for i,a in enumerate(W):
            for b in W[i+1:]:
                if a["axis"]!=b["axis"] or abs(a["t"]-b["t"])<1e-6: continue
                ov = min(a["f1"],b["f1"]) - max(a["f0"],b["f0"])     # 墙带横向重叠
                if ov <= 1e-9: continue
                gap_along = max(a["lo"],b["lo"]) - min(a["hi"],b["hi"])
                found+=1
                dmid=(b["mid"]-a["mid"])*1000; d0=(b["f0"]-a["f0"])*1000; d1=(b["f1"]-a["f1"])*1000
                v = ("中轴对齐" if abs(dmid)<1e-6 else "低侧持平" if abs(d0)<1e-6
                     else "高侧持平" if abs(d1)<1e-6 else "都不齐")
                print(f"   {a['axis']} t={a['t']*1000:5.1f}↔{b['t']*1000:5.1f}  沿向间隙={gap_along:+7.3f}m  "
                      f"Δ中轴={dmid:+7.1f} Δ低={d0:+7.1f} Δ高={d1:+7.1f} ⇒ {v}")
                print(f"       A 带[{a['f0']:.3f},{a['f1']:.3f}] 沿[{a['lo']:.3f},{a['hi']:.3f}] | "
                      f"B 带[{b['f0']:.3f},{b['f1']:.3f}] 沿[{b['lo']:.3f},{b['hi']:.3f}]")
        if not found: print("   （无任何厚度不同且墙带横向重叠的墙对）")
