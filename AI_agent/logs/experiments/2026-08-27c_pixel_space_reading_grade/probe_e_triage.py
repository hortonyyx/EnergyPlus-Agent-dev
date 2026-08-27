"""⛔ 分诊：像素模式对「塌成中线」没反应 —— 三种可能，必须分开，⛔ 不许猜。

  ① 是我换到像素空间【引入】的盲区（换表示让免费的正确性蒸发）
  ② 判分器本来就有这个盲区（与像素无关，⛔ 不能记到本次改动头上）
  ③ ⭐ 我的变异形状对这份 case 根本不成立（sm25 是【成对两条线】方言，
     而 WIDTH_COEFF 规则只在「一条观测想回答第二个面」时才开火）

判别法：
  - 把同一个变异也在【米制空间】跑一遍 ⇒ 若米制也沉默，排除 ①
  - 造一个**形状正确**的变异 F「真正的 band_collapse」：把成对的两条面线合成一条、
    支撑列横跨整堵墙 ⇒ 它必须去回答两个面 ⇒ 宽度规则应当开火
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"

from probe_pixel_grade import JudgeRuler, MANIFEST, VIEW_ID, den_to_px, doc_to_px, SCORE_KEYS  # noqa: E402
from probe_discriminating_power import m_collapse_width  # noqa: E402


def m_band_collapse(doc):
    """F ⭐ 形状正确的中线读法：每一对面线合成【一条】，支撑列横跨整堵墙。

    这条线因此必须去回答那堵墙的**两个**面 ⇒ WIDTH_COEFF 规则的正靶心。
    ⛔ 它不伪造任何数：位置是两条真面线的中点，宽度是两条真面线的真实跨度。
    """
    d = copy.deepcopy(doc)
    fl = {f["id"]: f for f in d["observations"]["face_lines"]}
    pairs = d["hypotheses"].get("pairs") or []
    merged, dropped = 0, []
    for p in pairs:
        a, b = fl.get(p["face_a"]), fl.get(p["face_b"])
        if a is None or b is None or a["axis"] != b["axis"]:
            continue
        if a["id"] in dropped or b["id"] in dropped:
            continue
        ca = list(a.get("support_cols_px") or []) + list(b.get("support_cols_px") or [])
        if not ca:
            continue
        lo, hi = min(ca), max(ca)
        a["support_cols_px"] = [lo, hi]          # 横跨整堵墙的"带"
        a["pos_px"] = (lo + hi) / 2.0            # 中线
        a["runs_px"] = sorted([[float(r[0]), float(r[1])] for r in a["runs_px"] + b["runs_px"]])
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

    def px(d):
        return {k: grade(doc_to_px(d), den_px, **tol)["scores"][k] for k in SCORE_KEYS}

    def me(d):
        return {k: grade(d, den)["scores"][k] for k in SCORE_KEYS}

    base_px, base_me = px(doc), me(doc)
    e_doc = m_collapse_width(doc)
    f_doc = m_band_collapse(doc)
    print("pairs 数 =", len(doc["hypotheses"].get("pairs") or []),
          "| F 合并了", f_doc["_collapse"])
    print("BASE 像素", [base_px[k] for k in SCORE_KEYS])
    print("BASE 米制", [base_me[k] for k in SCORE_KEYS])

    rows = []
    for label, d in (("E 支撑列压成一列", e_doc), ("F ⭐ 真 band_collapse（成对合成一条）", f_doc)):
        p, m = px(d), me(d)
        rows.append({"mutation": label, "pixel": p,
                     "pixel_moved": {k: [base_px[k], p[k]] for k in SCORE_KEYS if p[k] != base_px[k]},
                     "metre": m,
                     "metre_moved": {k: [base_me[k], m[k]] for k in SCORE_KEYS if m[k] != base_me[k]}})
        print(f"\n{label}")
        print(f"   像素 {[p[k] for k in SCORE_KEYS]}  {'✅变红' if rows[-1]['pixel_moved'] else '⛔沉默'}")
        print(f"   米制 {[m[k] for k in SCORE_KEYS]}  {'✅变红' if rows[-1]['metre_moved'] else '⛔沉默'}")

    e, f = rows
    if not e["pixel_moved"] and not e["metre_moved"]:
        e_diag = "排除① —— 像素与米制【同样沉默】⇒ 不是换表示引入的盲区"
    elif not e["pixel_moved"] and e["metre_moved"]:
        e_diag = "⛔① 换到像素空间【引入】了盲区 —— 本次改动的真缺陷"
    else:
        e_diag = "E 在像素空间会变红，之前的读数需复核"
    out = {"probe": "e_triage", "view": VIEW_ID,
           "base": {"pixel": base_px, "metre": base_me},
           "band_collapse_merge_stats": f_doc["_collapse"],
           "rows": rows, "E_diagnosis": e_diag,
           "F_caught_in_pixel_space": bool(f["pixel_moved"]),
           "F_caught_in_metre_space": bool(f["metre_moved"])}
    (HERE / "e_triage.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("\n⇒ E 分诊：", e_diag)
    print("⇒ F（形状正确的中线读法）像素抓到:", bool(f["pixel_moved"]),
          "| 米制抓到:", bool(f["metre_moved"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
