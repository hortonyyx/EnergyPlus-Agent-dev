"""⛔ 上一支探针刚让像素空间判别实验全绿 —— 本探针的存在理由就是**不许信那个绿**。

> 「一个能自己重算却选择信任的检查不是检查」·「变红 ≠ 有分辨力」·
> 「刚变全绿的判据须当场证明还能变红，**且变异方向要对**」

一个**什么都不看**的判分器，在「只改产品标定」下同样会纹丝不动 ⇒ 那个 PASS 单独没有意义。
本探针在**像素通道本身**（= 像素模式真正读的东西）上造真实的读图错误，要求它**变红**。

⭐ 判据（两条同时成立才算像素模式合格）：
  ① 标定扰动 ⇒ 分数**逐位不动**（上一支探针，PASS）
  ② 像素观测错 ⇒ 分数**明显变红**，且**方向对**（漏画伤 C2、多画伤 C4、切错伤 C3）
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
HERE = Path(__file__).resolve().parent
OUT = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"

from probe_pixel_grade import (JudgeRuler, MANIFEST, VIEW_ID, den_to_px,  # noqa: E402
                               doc_to_px, SCORE_KEYS)


def m_shift_all(doc, px):
    """A 全局平移：产品把整张图量偏了 px 个像素（≠ 标定错，是观测错）。"""
    d = copy.deepcopy(doc)
    for f in d["observations"]["face_lines"]:
        f["pos_px"] += px
        f["support_cols_px"] = [c + px for c in (f.get("support_cols_px") or [])]
        f["runs_px"] = [[a + px, b + px] for a, b in f["runs_px"]]
        for g in (f.get("gaps") or []):
            g["lo_px"] += px
            g["hi_px"] += px
    return d


def m_scale_all(doc, k):
    """B 全局缩放：观测尺度错了 k 倍。"""
    d = copy.deepcopy(doc)
    for f in d["observations"]["face_lines"]:
        f["pos_px"] *= k
        f["support_cols_px"] = [c * k for c in (f.get("support_cols_px") or [])]
        f["runs_px"] = [[a * k, b * k] for a, b in f["runs_px"]]
        for g in (f.get("gaps") or []):
            g["lo_px"] *= k
            g["hi_px"] *= k
    return d


def m_drop_runs(doc, n):
    """C 漏画：把 n 条面线各自最长的那段整段删掉。方向应当伤 C2。"""
    d = copy.deepcopy(doc)
    hit = 0
    for f in d["observations"]["face_lines"]:
        if hit >= n or len(f["runs_px"]) < 2:
            continue
        longest = max(f["runs_px"], key=lambda r: r[1] - r[0])
        f["runs_px"] = [r for r in f["runs_px"] if r is not longest]
        hit += 1
    return d


def m_draw_through(doc):
    """D 画穿：每条面线的多段合成一段（把门洞/空档一笔画过去）。应当伤 C3/C4。"""
    d = copy.deepcopy(doc)
    for f in d["observations"]["face_lines"]:
        if len(f["runs_px"]) >= 2:
            lo = min(r[0] for r in f["runs_px"])
            hi = max(r[1] for r in f["runs_px"])
            f["runs_px"] = [[lo, hi]]
    return d


def m_collapse_width(doc):
    """E 塌成中线：把每条支撑列压成一列（细线冒充整堵墙的两个面）。
    应当被 WIDTH_COEFF 规则拦住 ⇒ 一条观测不能同时回答两个面 ⇒ 伤 C1。"""
    d = copy.deepcopy(doc)
    for f in d["observations"]["face_lines"]:
        cols = f.get("support_cols_px") or []
        if len(cols) >= 2:
            mid = (min(cols) + max(cols)) / 2.0
            f["support_cols_px"] = [mid, mid]
            f["pos_px"] = mid
    return d


MUTATIONS = (
    ("对照：不变异", lambda d: copy.deepcopy(d), "⛔ 必须与 BASE 逐位相同"),
    ("A 观测整体偏 4.62 px（=0.10 m）", lambda d: m_shift_all(d, 4.62), "C1/C2 应崩"),
    ("A′ 观测整体偏 2.0 px", lambda d: m_shift_all(d, 2.0), "应有可见损失"),
    ("B 观测尺度 ×1.005", lambda d: m_scale_all(d, 1.005), "C1/C2 应崩"),
    ("C 漏画：5 条面线各删最长一段", lambda d: m_drop_runs(d, 5), "⭐ 应伤 C2"),
    ("D 画穿：每条面线合成一段", m_draw_through, "⭐ 应伤 C3/C4"),
    ("E 塌成中线：支撑列压成一列", m_collapse_width, "⭐ 应伤 C1"),
)


def main() -> int:
    from src.agent.judge.as_drawn.reading_grade import (grade, POS_TOL_M, SPAN_MIN,
                                                        END_TOL_M, EXTRA_MIN_M)
    R = JudgeRuler(json.loads(MANIFEST.read_text()), VIEW_ID)
    doc = json.loads((OUT / "sm25_1f_v2.json").read_text())
    den_px = den_to_px(json.loads((OUT / "denominator_sm25_F1.json").read_text()), R)
    tol = {"pos_tol": POS_TOL_M / R.m_per_px, "span_min": SPAN_MIN,
           "end_tol": END_TOL_M / R.m_per_px, "extra_min": EXTRA_MIN_M / R.m_per_px}

    base = grade(doc_to_px(doc), den_px, **tol)["scores"]
    print(f"{'BASE':38s} {[base[k] for k in SCORE_KEYS]}")
    rows = []
    for label, fn, expect in MUTATIONS:
        mutated = fn(doc)
        # ⛔ 变异真的落到像素通道上了吗？（「变异没跑」和「变异没效果」在产物上分不开）
        live = sum(1 for a, b in zip(doc["observations"]["face_lines"],
                                     mutated["observations"]["face_lines"])
                   if a["pos_px"] != b["pos_px"] or a["runs_px"] != b["runs_px"]
                   or a.get("support_cols_px") != b.get("support_cols_px"))
        s = grade(doc_to_px(mutated), den_px, **tol)["scores"]
        moved = {k: [base[k], s[k]] for k in SCORE_KEYS if s[k] != base[k]}
        rows.append({"mutation": label, "expectation": expect,
                     "face_lines_actually_mutated": live,
                     "scores": {k: s[k] for k in SCORE_KEYS},
                     "moved_vs_base": moved, "went_red": bool(moved)})
        print(f"{label:38s} {[s[k] for k in SCORE_KEYS]}"
              f"   {'✅变红' if moved else '⛔没反应'}  (变异命中 {live} 条)")

    control_clean = not rows[0]["moved_vs_base"]
    real_errors = rows[1:]
    all_red = all(r["went_red"] for r in real_errors)
    verdict = "PASS" if control_clean and all_red else "FAIL"
    out = {"probe": "pixel_grade_discriminating_power", "view": VIEW_ID,
           "base": {k: base[k] for k in SCORE_KEYS},
           "pixel_tolerances": tol, "rows": rows,
           "verdict": verdict,
           "criteria": {"control_unchanged": control_clean,
                        "every_real_error_went_red": all_red,
                        "silent_mutations": [r["mutation"] for r in real_errors if not r["went_red"]]}}
    (HERE / "discriminating_power.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"\n⇒ 分辨力：{verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
