"""⭐ EnergyPlus 对【小面】到底怎么反应？—— 用户 2026-08-28 问，orchestrator 实测。

⛔ 探索档诊断，产物不作成绩。

题面：两个相邻热区共用一条墙线，墙线中途有一个 `step` 米的台阶
（= 出模基准切换 或 墙厚不一致 造出来的那种）。台阶那一小片是一对
**真的 InterZone 面**（西侧属 A、东侧属 B），面积 = step x 层高。

  A(北)   x[0,3] y[0,5]  +  x[3,6] y[step,5]
  B(南)   x[0,3] y[-5,0] +  x[3,6] y[-5,step]
  共用    y=0 (x 0..3) · **x=3 (y 0..step)  <- 小面** · y=step (x 3..6)

扫 step = 0.5 / 0.12 / 0.06 / 0.02 / 0.005 m，看 EP 报什么。
⛔ 每档单独一个目录，⛔ 不复用退出码文件（[[exit-code-file-must-not-be-reused-across-runs]]）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path("/workspaces/EnergyPlus-Agent-dev")
EPEXE = "/EnergyPlus-25.1.0-68a4a7c774-Linux-Ubuntu22.04-x86_64/energyplus"
EPW = REPO / "data/weather/Shenzhen.epw"
H = 3.0


def poly_a(s):
    return [(0, 0), (3, 0), (3, s), (6, s), (6, 5), (0, 5)]


def poly_b(s):
    return [(0, -5), (6, -5), (6, s), (3, s), (3, 0), (0, 0)]


def wall(name, zone, p1, p2, obc, obc_obj):
    """一面墙：底边 p1->p2，向上 H。逆时针（从室外看）= 上边先走 p1->p2 的反向。"""
    v = [(p1[0], p1[1], H), (p1[0], p1[1], 0.0), (p2[0], p2[1], 0.0), (p2[0], p2[1], H)]
    sun, wind = ("SunExposed", "WindExposed") if obc == "Outdoors" else ("NoSun", "NoWind")
    out = [f"BuildingSurface:Detailed,\n  {name},\n  Wall,\n  Wall_C,\n  {zone},\n  ,\n"
           f"  {obc},\n  {obc_obj},\n  {sun},\n  {wind},\n  autocalculate,\n  {len(v)},"]
    out += [f"\n  {x},{y},{z}" + ("," if i < len(v) - 1 else ";") for i, (x, y, z) in enumerate(v)]
    return "".join(out) + "\n\n"


def horiz(name, zone, pts, z, kind, obc, obc_obj=""):
    v = [(x, y, z) for x, y in pts]
    sun, wind = ("SunExposed", "WindExposed") if obc == "Outdoors" else ("NoSun", "NoWind")
    out = [f"BuildingSurface:Detailed,\n  {name},\n  {kind},\n  {kind}_C,\n  {zone},\n  ,\n"
           f"  {obc},\n  {obc_obj},\n  {sun},\n  {wind},\n  autocalculate,\n  {len(v)},"]
    out += [f"\n  {x},{y},{zz}" + ("," if i < len(v) - 1 else ";") for i, (x, y, zz) in enumerate(v)]
    return "".join(out) + "\n\n"


def build_idf(step: float) -> str:
    A, B = poly_a(step), poly_b(step)
    # 共用的三段（A 侧的走向；B 侧取反向，保证两面朝向相对）
    shared = [((0, 0), (3, 0)), ((3, 0), (3, step)), ((3, step), (6, step))]
    txt = f"""Version, 25.1.0;
SimulationControl, No, No, No, No, Yes, No, 1;
Building, SliverProbe, 0, Suburbs, 0.04, 0.4, FullExterior, 25, 1;
Timestep, 4;
GlobalGeometryRules, UpperLeftCorner, Counterclockwise, World, Relative, Relative;
Site:Location, Shenzhen, 22.55, 114.1, 8.0, 5.0;
RunPeriod, P, 1, 1, , 1, 2, , , Yes, Yes, No, Yes, Yes, No, Hour24;
Material:NoMass, M, Rough, 2.0, 0.9, 0.7, 0.7;
Construction, Wall_C, M;
Construction, Floor_C, M;
Construction, Roof_C, M;
Zone, ZA, 0, 0, 0, 0, 1, 1, autocalculate, autocalculate, autocalculate, TARP, DOE-2, Yes;
Zone, ZB, 0, 0, 0, 0, 1, 1, autocalculate, autocalculate, autocalculate, TARP, DOE-2, Yes;

"""
    # 地板 / 屋顶（顺时针 = 从室外看逆时针，EP 的 floor 要顺时针俯视）
    txt += horiz("ZA_Floor", "ZA", A[::-1], 0.0, "Floor", "Ground")
    txt += horiz("ZA_Roof", "ZA", A, H, "Roof", "Outdoors")
    txt += horiz("ZB_Floor", "ZB", B[::-1], 0.0, "Floor", "Ground")
    txt += horiz("ZB_Roof", "ZB", B, H, "Roof", "Outdoors")

    for zn, poly in (("ZA", A), ("ZB", B)):
        for i in range(len(poly)):
            p1, p2 = poly[i], poly[(i + 1) % len(poly)]
            key = tuple(sorted([p1, p2]))
            match = next((s for s in shared if tuple(sorted(list(s))) == key), None)
            nm = f"{zn}_W{i}"
            if match:
                other = "ZB" if zn == "ZA" else "ZA"
                oi = next(j for j in range(len(poly_a(step) if other == "ZA" else poly_b(step)))
                          if tuple(sorted([(poly_a(step) if other == "ZA" else poly_b(step))[j],
                                           (poly_a(step) if other == "ZA" else poly_b(step))[(j + 1) % 6]])) == key)
                txt += wall(nm, zn, p1, p2, "Surface", f"{other}_W{oi}")
            else:
                txt += wall(nm, zn, p1, p2, "Outdoors", "")
    return txt


def run(step: float, tag: str) -> dict:
    d = REPO / "AI_agent/logs/experiments/2026-08-28_wall_basis_jog/ep_runs" / tag
    d.mkdir(parents=True, exist_ok=True)
    idf = d / "in.idf"
    idf.write_text(build_idf(step), encoding="utf-8")
    r = subprocess.run([EPEXE, "-w", str(EPW), "-d", str(d), "-r", str(idf)],
                       capture_output=True, text=True, timeout=600)
    err = (d / "eplusout.err")
    lines = err.read_text(encoding="utf-8", errors="replace").splitlines() if err.exists() else []
    return {"step": step, "tag": tag, "rc": r.returncode,
            "area_m2": round(step * H, 4),
            "severe": [l.strip() for l in lines if "** Severe  **" in l],
            "fatal": [l.strip() for l in lines if "**  Fatal  **" in l],
            "warn_small": [l.strip() for l in lines
                           if any(k in l.lower() for k in
                                  ("small", "degenerate", "collinear", "vertices", "area"))],
            "summary": [l.strip() for l in lines if "EnergyPlus Completed" in l or "Terminated" in l],
            "n_warning": sum(1 for l in lines if "** Warning **" in l)}


if __name__ == "__main__":
    import json
    out = []
    for s, tag in ((0.50, "step_500mm"), (0.12, "step_120mm"), (0.06, "step_060mm"),
                   (0.02, "step_020mm"), (0.005, "step_005mm")):
        res = run(s, tag)
        out.append(res)
        print(f"\n{'='*70}\nstep={s*1000:.0f} mm  面积={res['area_m2']} m2  rc={res['rc']}  warnings={res['n_warning']}")
        for k in ("fatal", "severe", "summary"):
            for l in res[k][:4]:
                print(f"   [{k}] {l}")
        for l in res["warn_small"][:6]:
            print(f"   [hit] {l}")
    (REPO / "AI_agent/logs/experiments/2026-08-28_wall_basis_jog/ep_sliver_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
