"""⭐⭐⭐ ①-2′ 第 4+5 步：把描图分挪进【像素空间】，再重跑 sol 的判别实验。

背景（2026-08-27 上一轮实测，`../2026-08-27_judge_ruler_holdout/`）：
  判别实验**不通过** —— 只动产品自己的标定，描图分就动（scale +0.5% ⇒ 画到率 100→92.7%，
  C4 多画在两把尺子的分歧量级上直接翻倍）⇒ 自证回路是**实测存在**的，不是理论担忧。
  那份 README §九 的结论：「描图分改到像素空间判**不是可选优化，是判别实验的通过条件**」。

本探针要回答的就是那一句能不能兑现：

  ⭐ 判分两侧都换成【像素】之后，动产品的标定，描图分还动不动？

## 方法（⛔ 三条纪律）

1. ⛔ **不重写判分器。** 复用 `reading_grade.grade()` 一个字不改，只把**两侧一起**换成像素单位
   （[[recompute-gate-must-mirror-producer-definition]]：重算必须复刻生产者的定义，
   自己重写一个"像素版判分器"就是又发明了一套定义）。
2. **产品侧只取原始像素观测** —— `pos_px` / `runs_px` / `support_cols_px` / `gaps[].{lo,hi}_px`。
   这些是尺子在图上量到的，**产品的标定碰不到它们**。
3. **答案侧用【判分方自己的】尺子换算** —— manifest 的 `pixel_to_source_m` ∘ 视图的
   `world_from_source_m`，⛔ 一个字节都不来自产品。这把尺子 2026-08-27 过了真 holdout。

## ⚠️ 显式声明的降级（⛔ 不许当成没有）

`_lands_here()` 用的 `TJ_ALONG_TOL_M` / `TJ_REACH_TOL_M` / `TJ_MAX_WALL_M` 是**写死的米制常量**。
判分器自己声明它们 "ANNOTATION ONLY -- these two never touch a score"，
⇒ **分数不受影响**，但像素模式下 `uncovered_at_tjunction` 这个**标注**会失去意义。
⛔ 本探针不读那个字段，也不许下游读它。
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

HERE = Path(__file__).resolve().parent
OUT = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
MANIFEST = REPO / "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/manifest.json"
VIEW_ID = "plan-F1"

# 与上一轮判别实验逐字相同的七行扰动，⛔ 不许换（换了就不是同一个实验）
CASES = (("BASE", {}), ("scale +0.05%", {"scale": 1.0005}), ("scale +0.1%", {"scale": 1.001}),
         ("scale +0.5%", {"scale": 1.005}), ("shift +0.02m", {"shift": 0.02}),
         ("shift +0.05m", {"shift": 0.05}), ("shift +0.10m", {"shift": 0.10}))
SCORE_KEYS = ("C1_C2_targets_drawn_pct", "C2_length_coverage_pct", "C3_bad_split",
              "C4_extra_length_m", "C5_openings_named_right_pct")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class JudgeRuler:
    """世界米 → 像素。⛔ 只吃 manifest，⛔ 不碰产品的任何字段。"""

    def __init__(self, manifest: dict, view_id: str):
        ov = next(o for o in manifest["raster_overlays"] if o["view_id"] == view_id)
        vw = next(v for v in manifest["views"] if v["id"] == view_id)
        p2s, w2s = ov["pixel_to_source_m"], vw["world_from_source_m"]
        for name, mat in (("pixel_to_source_m", p2s), ("world_from_source_m", w2s)):
            if abs(mat["m01"]) > 1e-12 or abs(mat["m10"]) > 1e-12:
                raise SystemExit(f"⛔ {name} 有旋转/斜切项，本探针的逐轴换算不成立：{mat}")
        # world = w2s ∘ p2s  ⇒  wx = a*px + bx ; wy = c*py + by
        self.ax, self.bx = p2s["m00"] * w2s["m00"], w2s["m00"] * p2s["m02"] + w2s["m02"]
        self.ay, self.by = p2s["m11"] * w2s["m11"], w2s["m11"] * p2s["m12"] + w2s["m12"]
        self.png_sha256 = ov["source_sha256"]
        self.m_per_px = abs(p2s["m00"])

    def px_x(self, wx: float) -> float:
        return (wx - self.bx) / self.ax

    def px_y(self, wy: float) -> float:
        return (wy - self.by) / self.ay

    def const_px(self, axis: str, v: float) -> float:
        return self.px_x(v) if axis == "x" else self.px_y(v)

    def span_px(self, axis: str, lo: float, hi: float) -> list[float]:
        """target 的 span 沿【另一根】轴；世界 y 与像素行反向 ⇒ 必须重新排序。"""
        f = self.px_y if axis == "x" else self.px_x
        a, b = f(lo), f(hi)
        return [min(a, b), max(a, b)]


def den_to_px(den: dict, R: JudgeRuler) -> dict:
    d = copy.deepcopy(den)
    for t in d["targets"]:
        ax = t["axis"]
        t["const_m"] = R.const_px(ax, t["const_m"])
        lo, hi = R.span_px(ax, t["lo_m"], t["hi_m"])
        t["lo_m"], t["hi_m"] = lo, hi
        t["length_m"] = hi - lo
        t["holes"] = [R.span_px(ax, a, b) for a, b in (t.get("holes") or [])]
        # required = span 减去 holes（复刻 denominator 自己的定义）
        t["required_length_m"] = (hi - lo) - sum(b - a for a, b in t["holes"])
    for a in d.get("allowed_not_required", []):
        ax = a["axis"]
        a["const_m"] = R.const_px(ax, a["const_m"])
        a["lo_m"], a["hi_m"] = R.span_px(ax, a["lo_m"], a["hi_m"])
    for o in d.get("opening_targets", []):
        ax = o["axis"]
        c = sorted(R.const_px(ax, v) for v in o["const_range_m"])
        o["const_range_m"] = c
        lo, hi = R.span_px(ax, o["lo_m"], o["hi_m"])
        o["lo_m"], o["hi_m"] = lo, hi
        o["width_m"] = hi - lo
    return d


def doc_to_px(doc: dict) -> dict:
    """产品侧换成原始像素观测。⛔ 不经过产品的标定 —— 这正是判别实验要切断的那条腿。"""
    d = copy.deepcopy(doc)
    gaps_by_face = {}
    for f in d["observations"]["face_lines"]:
        f["pos_m"] = float(f["pos_px"])
        f["runs_m"] = [[float(min(r)), float(max(r))] for r in f["runs_px"]]
        cols = f.get("support_cols_px") or []
        f["edges_m"] = [float(min(cols)), float(max(cols))] if len(cols) >= 2 else []
        f["support_width_m"] = (max(cols) - min(cols)) if len(cols) >= 2 else 0.0
        gaps_by_face[f["id"]] = f.get("gaps") or []
    # ⭐ opening_candidates 只发布 span_m，没有 span_px；但它引用的 gap 自己带 lo_px/hi_px
    #    ⇒ 像素区间是【存在】的，只是没被发布到候选那一层。本探针从 gap 取回。
    recovered, missing = 0, 0
    for c in (d["hypotheses"].get("opening_candidates") or []):
        gs = gaps_by_face.get(c["face_line"]) or []
        gi = c.get("gap_index")
        if isinstance(gi, int) and 0 <= gi < len(gs) and "lo_px" in gs[gi]:
            g = gs[gi]
            c["span_m"] = [float(g["lo_px"]), float(g["hi_px"])]
            c["len_m"] = float(g["hi_px"]) - float(g["lo_px"])
            recovered += 1
        else:
            c["span_m"] = None
            missing += 1
    d["_opening_span_px"] = {"recovered": recovered, "missing": missing}
    return d


def perturb_calibration(doc: dict, scale: float = 1.0, shift: float = 0.0) -> dict:
    """⭐ 与上一轮逐字相同：只动【标定派生的米制通道】，⛔ 像素通道一个字节不碰。"""
    d = copy.deepcopy(doc)
    f = lambda v: v * scale + shift
    for fl in d["observations"]["face_lines"]:
        fl["pos_m"] = f(fl["pos_m"])
        if fl.get("edges_m"):
            fl["edges_m"] = [f(e) for e in fl["edges_m"]]
        fl["runs_m"] = [[f(a), f(b)] for a, b in fl["runs_m"]]
    for c in (d["hypotheses"].get("opening_candidates") or []):
        if c.get("span_m"):
            c["span_m"] = [f(v) for v in c["span_m"]]
    return d


def main() -> int:
    from src.agent.judge.as_drawn.reading_grade import (grade, POS_TOL_M, SPAN_MIN,
                                                        END_TOL_M, EXTRA_MIN_M)
    manifest = json.loads(MANIFEST.read_text())
    R = JudgeRuler(manifest, VIEW_ID)
    doc = json.loads((OUT / "sm25_1f_v2.json").read_text())
    den = json.loads((OUT / "denominator_sm25_F1.json").read_text())

    # ---- 信任根自检：产品读的 PNG 必须就是 manifest 绑定的那张 ----
    png = REPO / doc["image"]
    got = _sha256(png) if png.is_file() else None
    if got != R.png_sha256:
        raise SystemExit(f"⛔ 产品读的图与 manifest 绑定的不是同一张：{got} vs {R.png_sha256}")

    px_tol = {"pos_tol": POS_TOL_M / R.m_per_px, "span_min": SPAN_MIN,
              "end_tol": END_TOL_M / R.m_per_px, "extra_min": EXTRA_MIN_M / R.m_per_px}

    den_px = den_to_px(den, R)
    doc_px_base = doc_to_px(doc)

    rows, mutation_live = [], []
    for label, kw in CASES:
        # ⭐⭐ 组合次序是本实验的要害：**先扰动原始文档的米制通道，再转像素**。
        # ⛔ 反过来（先转像素、再按字段名扰动）扰动的是像素通道本身 —— 那是探针的 bug，
        #    不是被测对象的性质。我第一版就是这么写的，读数全错。
        m_doc = perturb_calibration(doc, **kw)     # 只动标定派生的米制通道
        p_doc = doc_to_px(m_doc)                   # 像素模式只读 *_px ⇒ 上面那步应当【看不见】
        # ⛔ 「变异没效果」和「变异没跑」在产物上分不开 ⇒ 每一行都单独证明扰动真的落到了文档上
        moved = sum(1 for a, b in zip(doc["observations"]["face_lines"],
                                      m_doc["observations"]["face_lines"])
                    if a["pos_m"] != b["pos_m"])
        mutation_live.append({"perturbation": label, "face_lines_whose_pos_m_changed": moved,
                              "of_total": len(doc["observations"]["face_lines"])})
        m_s = grade(m_doc, den)["scores"]
        p_s = grade(p_doc, den_px, **px_tol)["scores"]
        rows.append({"perturbation": label,
                     "metre_space": {k: m_s[k] for k in SCORE_KEYS},
                     "pixel_space": {k: p_s[k] for k in SCORE_KEYS}})
        print(f"{label:14s} 米制 {[m_s[k] for k in SCORE_KEYS]}")
        print(f"{'':14s} 像素 {[p_s[k] for k in SCORE_KEYS]}")

    base_m, base_px = rows[0]["metre_space"], rows[0]["pixel_space"]
    base_agreement = {
        "C1_C2": [base_m["C1_C2_targets_drawn_pct"], base_px["C1_C2_targets_drawn_pct"]],
        "C2": [base_m["C2_length_coverage_pct"], base_px["C2_length_coverage_pct"]],
        "C3": [base_m["C3_bad_split"], base_px["C3_bad_split"]],
        "C5": [base_m["C5_openings_named_right_pct"], base_px["C5_openings_named_right_pct"]],
        "C4_metre_vs_pixel_converted_m": [base_m["C4_extra_length_m"],
                                          round(base_px["C4_extra_length_m"] * R.m_per_px, 4)],
    }
    drift = [{"perturbation": r["perturbation"],
              "moved": {k: [base_px[k], r["pixel_space"][k]]
                        for k in SCORE_KEYS if r["pixel_space"][k] != base_px[k]}}
             for r in rows[1:]]
    verdict = "PASS" if all(not d["moved"] for d in drift) else "FAIL"

    result = {
        "probe": "pixel_space_reading_grade",
        "view": VIEW_ID,
        "trust_roots": {
            "manifest": str(MANIFEST.relative_to(REPO)),
            "manifest_file_sha256": _sha256(MANIFEST),
            "png": doc["image"], "png_sha256": got,
            "product": "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_1f_v2.json",
        },
        "judge_ruler": {"m_per_px": R.m_per_px,
                        "world_x_px": [R.ax, R.bx], "world_y_px": [R.ay, R.by]},
        "pixel_tolerances": px_tol,
        "base_agreement_metre_vs_pixel": base_agreement,
        "opening_span_px_recovery": doc_px_base["_opening_span_px"],
        "mutation_liveness": mutation_live,
        "rows": rows,
        "discriminating_experiment": {
            "question": "只改产品标定 ⇒ 描图分该不该动",
            "metre_space": "上一轮已实测 FAIL（分数随标定动）",
            "pixel_space_verdict": verdict,
            "pixel_space_drift": drift,
        },
    }
    (HERE / "pixel_grade.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(f"\n⇒ 像素空间判别实验：{verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
