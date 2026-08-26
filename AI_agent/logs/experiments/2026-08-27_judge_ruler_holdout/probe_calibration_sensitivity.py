"""⭐⭐⭐ sol's discriminating experiment, run for real: perturb ONLY the product's
calibration and watch what the reading grade does.

sol 2026-08-27: "产品自报的标定不能用来换算它自己的答案 —— 那是自证回路。
判别实验：故意改产品标定 ⇒ 标定分该变、描图分不该变。"

`reading_grade.py` today consumes ``pos_m`` / ``runs_m`` / ``edges_m`` — all of which
the product produced by applying ITS OWN calibration to its pixel observations.  So a
calibration change is exactly an affine change on those numbers, and that is what this
sweep applies.  ⛔ Nothing else about the answer is touched: same face lines, same runs,
same hypotheses, same openings.

If the tracing score were calibration-independent, every row below would be identical.
"""
from __future__ import annotations
import copy, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
OUT = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
CASES = (("BASE", {}), ("scale +0.05%", {"scale": 1.0005}), ("scale +0.1%", {"scale": 1.001}),
         ("scale +0.5%", {"scale": 1.005}), ("shift +0.02m", {"shift": 0.02}),
         ("shift +0.05m", {"shift": 0.05}), ("shift +0.10m", {"shift": 0.10}))


def perturb(doc, scale=1.0, shift=0.0):
    doc = copy.deepcopy(doc)
    f = lambda v: v * scale + shift
    for fl in doc["observations"]["face_lines"]:
        fl["pos_m"] = f(fl["pos_m"])
        if fl.get("edges_m"):
            fl["edges_m"] = [f(e) for e in fl["edges_m"]]
        fl["runs_m"] = [[f(a), f(b)] for a, b in fl["runs_m"]]
    return doc


def main() -> int:
    from src.agent.judge.as_drawn.reading_grade import grade
    doc = json.loads((OUT / "sm25_1f_v2.json").read_text())
    den = json.loads((OUT / "denominator_sm25_F1.json").read_text())
    rows = []
    for label, kw in CASES:
        s = grade(perturb(doc, **kw), den)["scores"]
        rows.append({"perturbation": label, **{k: s[k] for k in
                     ("C1_C2_targets_drawn_pct", "C2_length_coverage_pct", "C3_bad_split",
                      "C4_extra_length_m", "C5_openings_named_right_pct")}})
        print(json.dumps(rows[-1], ensure_ascii=False))
    Path(__file__).with_name("calibration_sensitivity.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
