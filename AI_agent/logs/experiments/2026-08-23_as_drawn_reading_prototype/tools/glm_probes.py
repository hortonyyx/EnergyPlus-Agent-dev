"""GLM fourth cross-review: one-command repro for every probe cited in the verdict.

  P1 bridge_the_window   draw the wall straight through the real 0.6 m window
                         (with and without keeping the gap declaration) --
                         grade + all gates + old gt-side ruler.
  P2 sm24_decomposition  regrade sm24 with EVERY face line positively claimed,
                         isolating how much of honest 44.3% the 78 abstentions
                         actually explain (answer: none).
  P3 spacing_and_err     pair-spacing distribution + honest const_err stats --
                         the two numbers that bound pos_tol from both sides.
  P4 merge_step          denominator targets at merge_m 0.5 vs 0.6 + the real
                         opening that the 0.6 merge swallows, + the bridged
                         product graded against both denominators.

    python3 tools/glm_probes.py      # -> out/glm_probes.json
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


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, T / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RG = _load("reading_grade")


def _gates(doc_path: Path, cfg: str) -> dict:
    outp = doc_path.with_name(doc_path.stem + "_checks.json")
    r = subprocess.run([sys.executable, str(T / "checks_as_drawn_v2.py"),
                        str(doc_path), str(T / cfg), str(outp)],
                       capture_output=True, text=True, cwd=REPO)
    if r.returncode:
        return {"ERROR": r.stderr.strip()[-200:]}
    d = json.loads(outp.read_text())
    return {c["check"]: c["status"] for c in d["checks"]}


def _gt(case: str, docs: dict) -> object:
    r = subprocess.run([sys.executable, str(T / "reconstruct_check_v2.py"), case,
                        json.dumps(docs), "/tmp/glm_probe_gt.json"],
                       capture_output=True, text=True, cwd=REPO)
    return json.loads(r.stdout)["overall_ok_pct"] if r.returncode == 0 else "ERROR"


def p1_bridge_window(res: dict) -> None:
    doc = json.loads((OUT / "sm25_1f_v2.json").read_text())
    den = json.loads((OUT / "denominator_sm25_F1.json").read_text())
    for variant, keep_gap in (("bridge_window", True), ("bridge_window_nogap", False)):
        d = json.loads(json.dumps(doc))
        for f in d["observations"]["face_lines"]:
            if f["axis"] == "row" and (abs(f["pos_m"] - 19.76) < 0.1 or abs(f["pos_m"] - 20.0) < 0.1):
                mr = [sorted(r) for r in f["runs_m"]]
                pr = [sorted(r) for r in f["runs_px"]]
                for i in range(len(mr) - 1):
                    if mr[i][1] <= 10.3 and mr[i + 1][0] >= 10.9 and mr[i + 1][0] - mr[i][1] <= 0.7:
                        f["runs_m"] = mr[:i] + [[mr[i][0], mr[i + 1][1]]] + mr[i + 2:]
                        f["runs_px"] = pr[:i] + [[pr[i][0], pr[i + 1][1]]] + pr[i + 2:]
                        if not keep_gap:
                            f["gaps"] = []
                        break
        p = OUT / f"sm25_1f_GLM_{variant}.json"
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        res[variant] = {"grade": RG.grade(d, den)["scores"], "gates": _gates(p, "cfg_1f_full.json"),
                        "gt_side": _gt("sm25-L_anchor", {"F1": str(p), "F2": str(OUT / "sm25_2f_v2.json")})}
        print(variant, res[variant]["grade"], "gt:", res[variant]["gt_side"],
              "red:", [k for k, v in res[variant]["gates"].items() if v == "red"])


def p2_sm24_decomposition(res: dict) -> None:
    doc = json.loads((OUT / "sm24_1f_v2.json").read_text())
    den = json.loads((OUT / "denominator_sm24_F1.json").read_text())
    d = json.loads(json.dumps(doc))
    for f in d["observations"]["face_lines"]:
        d["hypotheses"].setdefault("unpaired_wall_faces", {}).setdefault(
            f["id"], "decomposition probe: graded anyway")
    res["sm24_all_graded"] = RG.grade(d, den)["scores"]
    print("sm24 all-graded:", res["sm24_all_graded"])


def p3_spacing_and_err(res: dict) -> None:
    for prod, key in (("sm25_1f", "sm25_F1"), ("sm25_2f", "sm25_F2"), ("sm24_1f", "sm24_F1")):
        doc = json.loads((OUT / f"{prod}_v2.json").read_text())
        den = json.loads((OUT / f"denominator_{key}.json").read_text())
        byid = {f["id"]: f for f in doc["observations"]["face_lines"]}
        sp = sorted(round(abs(byid[p["face_a"]]["pos_m"] - byid[p["face_b"]]["pos_m"]), 4)
                    for p in (doc["hypotheses"].get("pairs") or []))
        hyp = doc["hypotheses"]
        graded = ({x for p in (hyp.get("pairs") or []) for x in (p["face_a"], p["face_b"])}
                  | set(hyp.get("solid_band_walls") or {}) | set(hyp.get("unpaired_wall_faces") or {}))
        lines = []
        for f in doc["observations"]["face_lines"]:
            if f["id"] not in graded:
                continue
            axis = "x" if f["constant_world_axis"] == "x" else "y"
            lines.append({"axis": axis, "const": float(f["pos_m"]),
                          "runs": RG._union([tuple(r) for r in f["runs_m"]])})
        cerr = []
        for t in den["targets"]:
            cands = [ln for ln in lines if ln["axis"] == t["axis"]
                     and abs(ln["const"] - t["const_m"]) <= 0.08]
            if cands:
                best = max(cands, key=lambda ln: RG._covered(ln["runs"], t["lo_m"], t["hi_m"]))
                cerr.append(round(abs(best["const"] - t["const_m"]), 4))
        cerr.sort()
        res[f"stats_{prod}"] = {
            "pairs": len(sp), "spacing_min_med_max": [sp[0], sp[len(sp) // 2], sp[-1]] if sp else None,
            "pairs_within_0.16": sum(1 for s in sp if s <= 0.16),
            "const_err_max": cerr[-1] if cerr else None}
        print(f"stats_{prod}:", res[f"stats_{prod}"])


def p4_merge_step(res: dict) -> None:
    dxf = "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
    req = "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json"
    dens = {}
    for mm in ("0.5", "0.6"):
        r = subprocess.run([sys.executable, str(T / "denominator.py"), dxf, req, "plan-F1",
                            f"/tmp/glm_den_{mm}.json", mm], capture_output=True, cwd=REPO)
        dens[mm] = json.load(open(f"/tmp/glm_den_{mm}.json"))
    a = {(t["axis"], t["const_m"], t["lo_m"], t["hi_m"]) for t in dens["0.5"]["targets"]}
    b = {(t["axis"], t["const_m"], t["lo_m"], t["hi_m"]) for t in dens["0.6"]["targets"]}
    doc = json.loads((OUT / "sm25_1f_GLM_bridge_window.json").read_text())
    res["merge_step"] = {
        "targets_0.5": len(a), "targets_0.6": len(b),
        "only_in_0.5": sorted(a - b), "only_in_0.6": sorted(b - a),
        "bridge_graded_vs_0.5": RG.grade(json.loads(json.dumps(doc)), dens["0.5"])["scores"],
        "bridge_graded_vs_0.6": RG.grade(json.loads(json.dumps(doc)), dens["0.6"])["scores"]}
    print("merge_step: 0.5 ->", len(a), "targets; 0.6 ->", len(b),
          "; bridge vs 0.5:", res["merge_step"]["bridge_graded_vs_0.5"]["C1_C2_targets_drawn_pct"],
          "vs 0.6:", res["merge_step"]["bridge_graded_vs_0.6"]["C1_C2_targets_drawn_pct"])


def main() -> int:
    res = {}
    p1_bridge_window(res)
    p2_sm24_decomposition(res)
    p3_spacing_and_err(res)
    p4_merge_step(res)
    (OUT / "glm_probes.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"-> {OUT / 'glm_probes.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
