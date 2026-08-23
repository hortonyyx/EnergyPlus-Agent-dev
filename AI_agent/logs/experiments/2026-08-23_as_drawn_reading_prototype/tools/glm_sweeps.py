"""GLM fourth cross-review: verify the README's PARAMETER-SWEEP claims.

Three sweeps, each against the frozen HEAD copy of the reviewed state:

  merge_m   denominator target count vs merge distance (claim: 0.40-0.80 is a
            clean plateau, "85 -> 108", 0.20 splits CAD fragments, 1.20 eats
            real openings).
  pos_tol   honest C1 vs position tolerance on ALL THREE products (claim:
            "0.02-0.20 诚实恒 100" -- stated without naming which product).
  punch     C1/C2 vs middle-punch fraction 5/10/20/30/50% (claim: C1 =
            100/99.1/10.2/10.2/10.2 with a cliff at span_min, C2 =
            93.4/88.5/78.8/69.2/49.8 smooth).  These numbers are NOT in
            RESULTS_v2.json, so they are re-derived here.

    python3 tools/glm_sweeps.py       # -> out/glm_sweeps.json + printed tables
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
T, OUT = EXP / "tools", EXP / "out"
REPO = EXP.parents[3]

DEN = [("sm25_F1", "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf",
        "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json", "plan-F1", "sm25_1f"),
       ("sm25_F2", "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf",
        "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json", "plan-F2", "sm25_2f"),
       ("sm24_F1", "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf",
        "tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json", "plan-F1", "sm24_1f")]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, T / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RG = _load("reading_grade")


def sweep_merge():
    out = {}
    for key, dxf, req, view, _ in DEN:
        row = {}
        for mm in (0.20, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00, 1.20, 1.60):
            r = subprocess.run([sys.executable, str(T / "denominator.py"), dxf, req, view,
                                "/tmp/glm_den.json", str(mm)], capture_output=True, text=True, cwd=REPO)
            d = json.loads(r.stdout)
            row[mm] = {"targets": d["scoreable_targets_after_merge"],
                       "len_m": d["total_scoreable_length_m"]}
        out[key] = row
        print(f"merge_m {key}: " + "  ".join(f"{m}->{v['targets']}" for m, v in row.items()))
    return out


def sweep_postol():
    out = {}
    for _, _, _, _, prod in DEN:
        doc = json.loads((OUT / f"{prod}_v2.json").read_text())
        key = next(k for k, _, _, _, p in DEN if p == prod)
        den = json.loads((OUT / f"denominator_{key}.json").read_text())
        row = {}
        for pt in (0.01, 0.02, 0.04, 0.06, 0.08, 0.12, 0.20):
            g = RG.grade(doc, den, pos_tol=pt)
            row[pt] = g["scores"]["C1_C2_targets_drawn_pct"]
        out[prod] = row
        print(f"pos_tol {prod}: " + "  ".join(f"{m}->{v}" for m, v in row.items()))
    return out


def sweep_punch():
    out = {}
    doc0 = json.loads((OUT / "sm25_1f_v2.json").read_text())
    den = json.loads((OUT / "denominator_sm25_F1.json").read_text())
    for frac in (0.05, 0.10, 0.20, 0.30, 0.50):
        doc = json.loads(json.dumps(doc0))
        for f in doc["observations"]["face_lines"]:
            runs = []
            for a, b in f["runs_m"]:
                lo, hi = sorted((a, b))
                if hi - lo > 0.5:
                    keep = (1.0 - frac) / 2.0 * (hi - lo)
                    runs += [[lo, lo + keep], [hi - keep, hi]]
                else:
                    runs.append([lo, hi])
            f["runs_m"] = runs
        g = RG.grade(doc, den)
        out[str(frac)] = {"C1": g["scores"]["C1_C2_targets_drawn_pct"],
                          "C2": g["scores"]["C2_length_coverage_pct"]}
        print(f"punch {frac:.0%}: C1={out[str(frac)]['C1']}  C2={out[str(frac)]['C2']}")
    return out


def main() -> int:
    res = {"merge_m": sweep_merge(), "pos_tol": sweep_postol(), "punch": sweep_punch()}
    (OUT / "glm_sweeps.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"-> {OUT / 'glm_sweeps.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
