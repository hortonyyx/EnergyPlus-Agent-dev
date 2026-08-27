"""⭐⭐⭐ F「真 band_collapse」——⛔ 上一版探针的 F 在两个空间里【不是同一个变异】。

上一版只改了像素通道（`pos_px` / `support_cols_px`），米制通道（`pos_m` / `edges_m`）留着旧值
⇒ 米制那边看到的是另一种破坏，两列读数不可比。**那是探针的 bug，不是被测对象的性质。**
（同族：「变异没跑」和「变异没效果」在产物上分不开 ⇒ 变异必须自证生效**且两侧等价**。）

本版：用**产品自己的**逐轴仿射（从产品自己的 (px, m) 配对反解出来，并逐点校验残差）
把变异**同时、一致地**写进两个通道，于是米制列与像素列问的是同一个问题：

  ⭐ 「一条中线冒充一堵墙的两个面」—— 这是本批指南**明令禁止**的读法。
     米制空间 2026-08-24 第四审专门加了 WIDTH_COEFF 规则来拦它。
     ⇒ 像素空间还拦得住吗？
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
OUT = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"

from probe_pixel_grade import JudgeRuler, MANIFEST, VIEW_ID, den_to_px, doc_to_px, SCORE_KEYS  # noqa: E402


def fit_product_axes(doc):
    """从产品自己的 (px, m) 配对反解逐轴仿射。

    ⚠️ **端点配对方向不能假设** —— 世界 y 与像素行是反向的，`runs_px[0]` 对应的是
    `runs_m[1]`。第一版按下标直配，`run:y` 残差 **7.29 m**，把米制那一列彻底污染，
    差点据此写下「像素空间丢了免费的正确性」的结论。
    ⇒ 现在**两种配对都试，取残差小的那个，并硬要求 < 1e-3 m**（自证，不靠我判断方向）。
    """
    const_pts, run_pairs = {}, {}
    for f in doc["observations"]["face_lines"]:
        ax = f["constant_world_axis"]
        const_pts.setdefault(ax, []).append((float(f["pos_px"]), float(f["pos_m"])))
        other = "y" if ax == "x" else "x"
        for rp, rm in zip(f["runs_px"], f["runs_m"]):
            run_pairs.setdefault(other, []).append(
                ((float(rp[0]), float(rp[1])), (float(rm[0]), float(rm[1]))))

    def fit(pp):
        pp = sorted(set(pp))
        (x0, y0), (x1, y1) = pp[0], pp[-1]
        if x1 == x0:
            return None, float("inf")
        k = (y1 - y0) / (x1 - x0)
        b = y0 - k * x0
        return (k, b), max(abs(k * x + b - y) for x, y in pp)

    maps, resid = {}, {}
    for ax, pp in const_pts.items():
        m, r = fit(pp)
        maps[("const", ax)], resid[f"const:{ax}"] = m, round(r, 6)
    for ax, prs in run_pairs.items():
        straight = [(p[0], q[0]) for p, q in prs] + [(p[1], q[1]) for p, q in prs]
        flipped = [(p[0], q[1]) for p, q in prs] + [(p[1], q[0]) for p, q in prs]
        ms, rs = fit(straight)
        mf, rf = fit(flipped)
        maps[("run", ax)], resid[f"run:{ax}"] = ((ms, round(rs, 6)) if rs <= rf
                                                 else (mf, round(rf, 6)))
        maps[("run", ax)], resid[f"run:{ax}"] = maps[("run", ax)][0] if isinstance(
            maps[("run", ax)], tuple) and isinstance(maps[("run", ax)][0], tuple) else (
            ms if rs <= rf else mf), min(round(rs, 6), round(rf, 6))
        resid[f"run:{ax}_orientation"] = "straight" if rs <= rf else "flipped"
    bad = {k: v for k, v in resid.items()
           if isinstance(v, float) and v > 1e-3}
    if bad:
        raise SystemExit(f"⛔ 产品自仿射拟合残差过大，变异不可信：{bad}")
    return maps, resid


def m_band_collapse(doc, maps):
    """每一对面线合成【一条】：位置=两条真面线中点，支撑=横跨整堵墙。两个通道同步写。"""
    d = copy.deepcopy(doc)
    fl = {f["id"]: f for f in d["observations"]["face_lines"]}
    dropped, merged = [], 0
    for p in (d["hypotheses"].get("pairs") or []):
        a, b = fl.get(p["face_a"]), fl.get(p["face_b"])
        if a is None or b is None or a["axis"] != b["axis"]:
            continue
        if a["id"] in dropped or b["id"] in dropped:
            continue
        cols = list(a.get("support_cols_px") or []) + list(b.get("support_cols_px") or [])
        if not cols:
            continue
        lo_px, hi_px = float(min(cols)), float(max(cols))
        mid_px = (lo_px + hi_px) / 2.0
        ax = a["constant_world_axis"]
        kc, bc = maps[("const", ax)]
        runs_px = sorted([[float(r[0]), float(r[1])] for r in a["runs_px"] + b["runs_px"]])
        other = "y" if ax == "x" else "x"
        kr, br = maps[("run", other)]

        a["support_cols_px"] = [lo_px, hi_px]
        a["pos_px"] = mid_px
        a["runs_px"] = runs_px
        # ⭐ 同步写米制通道，用产品自己的仿射 ⇒ 两个空间看到的是同一个变异
        a["pos_m"] = kc * mid_px + bc
        a["edges_m"] = sorted([kc * lo_px + bc, kc * hi_px + bc])
        a["support_width_m"] = abs(a["edges_m"][1] - a["edges_m"][0])
        a["runs_m"] = [sorted([kr * r[0] + br, kr * r[1] + br]) for r in runs_px]
        dropped.append(b["id"])
        merged += 1
    d["observations"]["face_lines"] = [f for f in d["observations"]["face_lines"]
                                       if f["id"] not in set(dropped)]
    d["_collapse"] = {"pairs_merged": merged, "face_lines_dropped": len(dropped)}
    return d


def main() -> int:
    from src.agent.judge.as_drawn.reading_grade import (grade, POS_TOL_M, SPAN_MIN,
                                                        END_TOL_M, EXTRA_MIN_M)
    R = JudgeRuler(json.loads(MANIFEST.read_text()), VIEW_ID)
    doc = json.loads((OUT / "sm25_1f_v2.json").read_text())
    den = json.loads((OUT / "denominator_sm25_F1.json").read_text())
    den_px = den_to_px(den, R)
    tol = {"pos_tol": POS_TOL_M / R.m_per_px, "span_min": SPAN_MIN,
           "end_tol": END_TOL_M / R.m_per_px, "extra_min": EXTRA_MIN_M / R.m_per_px}
    maps, resid = fit_product_axes(doc)
    print("产品自仿射的逐点最大残差（m）:", resid)

    px = lambda d: {k: grade(doc_to_px(d), den_px, **tol)["scores"][k] for k in SCORE_KEYS}
    me = lambda d: {k: grade(d, den)["scores"][k] for k in SCORE_KEYS}

    base_px, base_me = px(doc), me(doc)
    f_doc = m_band_collapse(doc, maps)
    f_px, f_me = px(f_doc), me(f_doc)
    print("合并统计:", f_doc["_collapse"])
    print(f"\n{'':22s} {'C1':>7s} {'C2':>7s} {'C3':>5s} {'C4':>10s} {'C5':>7s}")
    for lbl, s in (("BASE 米制", base_me), ("F    米制", f_me),
                   ("BASE 像素", base_px), ("F    像素", f_px)):
        print(f"{lbl:22s} " + " ".join(f"{s[k]:>7}" if not isinstance(s[k], float)
                                       else f"{s[k]:>7.1f}" for k in SCORE_KEYS[:3]) +
              f" {s['C4_extra_length_m']:>10.3f} {str(s['C5_openings_named_right_pct']):>7s}")

    # ⭐ 判据只看承重的两项（C1 画到率 / C2 覆盖率），⛔ 不拿 C4 的零头当"变红"
    me_caught = (f_me["C1_C2_targets_drawn_pct"] < base_me["C1_C2_targets_drawn_pct"] - 1.0)
    px_caught = (f_px["C1_C2_targets_drawn_pct"] < base_px["C1_C2_targets_drawn_pct"] - 1.0)
    verdict = ("像素空间与米制空间同样拦得住" if px_caught and me_caught else
               "⛔⛔ 像素空间【拦不住】米制空间拦得住的中线读法 —— 换表示丢了免费的正确性"
               if me_caught and not px_caught else
               "两个空间都拦不住（那是判分器本来的缺口，与像素无关）"
               if not me_caught and not px_caught else "像素拦得住而米制拦不住（需复核）")
    out = {"probe": "f_band_collapse_equivalent_in_both_spaces",
           "product_affine_residual_m": resid,
           "merge_stats": f_doc["_collapse"],
           "base": {"metre": base_me, "pixel": base_px},
           "band_collapse": {"metre": f_me, "pixel": f_px},
           "caught": {"metre_space": me_caught, "pixel_space": px_caught},
           "verdict": verdict}
    (HERE / "f_band_collapse.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("\n⇒", verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
