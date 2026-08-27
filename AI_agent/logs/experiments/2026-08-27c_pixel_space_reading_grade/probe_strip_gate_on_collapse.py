"""⭐ 闭环最后一格：band_collapse 到底谁在拦？拦它的那道门吃不吃产品的标定？

`reading_grade.py:174` 自己写着「the full-span ``band_collapse`` is caught by the
**support-strip gate**」⇒ 判分器对我的 F 变异沉默是**预期且正确**的，我跑错了对象。
本探针把真正该开火的那道门 `check_support_strip_is_one_stroke` 拿来跑：

  ① 诚实产物 ⇒ 应当 green（每条面线的墨列组数 = 1）
  ② F 中线读法 ⇒ 应当 red（塌缩带跨两笔墨、中间是白的 ⇒ 组数 = 2）
  ③ ⭐ 这道门读的是什么单位 —— 若它只吃像素，则「描图分挪进像素空间」不会碰它。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
OUT = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
CFG = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/cfg_1f_full.json"

from probe_f_band_collapse import fit_product_axes, m_band_collapse  # noqa: E402


def main() -> int:
    from src.validator.checks.as_drawn import check_support_strip_is_one_stroke
    from src.agent.reading.as_drawn.as_drawn_v2 import _family_masks
    from src.agent.reading.as_drawn._plan_ink import load_rgb

    cfg = json.loads(CFG.read_text())
    doc = json.loads((OUT / "sm25_1f_v2.json").read_text())
    maps, resid = fit_product_axes(doc)
    collapsed = m_band_collapse(doc, maps)
    # 门要拿 support_cols_px 去切片 ⇒ 必须是整数（诚实产物本来就是整数）
    for f in collapsed["observations"]["face_lines"]:
        c = f["support_cols_px"]
        f["support_cols_px"] = [int(round(c[0])), int(round(c[1]))]

    masks = _family_masks(load_rgb(str(REPO / cfg["image"])))
    roles = doc["hypotheses"]["family_roles"]["assignment"]

    rows = {}
    for label, d in (("诚实产物", doc), ("F 中线读法（22 对合成一条）", collapsed)):
        r = check_support_strip_is_one_stroke(d, masks, roles, cfg)
        rows[label] = {"status": r["status"], "violation_count": r["violation_count"],
                       "ink_column_groups_histogram": r["ink_column_groups_histogram"],
                       "mirrors": r["mirrors"],
                       "first_violations": r["violations"][:3]}
        print(f"{label:28s} status={r['status']:5s} 违规 {r['violation_count']:3d} "
              f"墨列组直方图 {r['ink_column_groups_histogram']}")

    honest_green = rows["诚实产物"]["status"] == "green"
    collapse_red = rows["F 中线读法（22 对合成一条）"]["status"] == "red"
    verdict = ("✅ 这道门确实是拦 band_collapse 的那一道：诚实全绿、中线读法变红"
               if honest_green and collapse_red else
               "⛔ 与预期不符，需复核")
    out = {"probe": "support_strip_gate_on_band_collapse",
           "product_affine_residual_m": resid,
           "rows": rows,
           "gate_inputs_are_pixel_only": {
               "reads": ["masks（从 PNG 直接算）", "support_cols_px", "drawing_box_px",
                         "cfg.min_run_px", "cfg.min_support"],
               "reads_any_metre_quantity": False,
               "⇒": "把描图分挪进像素空间不会影响这道门；它本来就与产品标定无关"},
           "verdict": verdict}
    (HERE / "strip_gate_on_collapse.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("\n⇒", verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
