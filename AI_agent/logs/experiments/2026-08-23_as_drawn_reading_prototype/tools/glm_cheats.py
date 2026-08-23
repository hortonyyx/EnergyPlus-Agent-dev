"""GLM fourth cross-review: can a REALISTIC wrong product beat reading_grade_v1?

Four product-side mutations, each graded by reading_grade.py AND run through all
eight gt-free gates (checks_as_drawn_v2.py) AND the old gt-side ruler
(reconstruct_check_v2.py), against the honest baseline:

  midline_thin        one THIN line at the centre of every interior wall pair
                      (spacing <= 0.16 m).  The shape a legacy centreline reader
                      produces; the batch guide forbids midlines outright.
  midline_band        one BAND face per interior pair: support columns span BOTH
                      real ink lines, runs = union of both faces' runs, gaps keep
                      their pixel indices with ink profiles HONESTLY recomputed
                      over the widened strip.  Dialect confusion (two-line walls
                      declared as solid bands) with no fabricated number in it.
  band_to_two_edges   (sm24) the honest solid-band faces split into TWO lines at
                      the band's own edges_m -- same ink, different representation.
  skip_unscored_tails trim every graded run back to what denominator targets
                      actually explain (tail pieces only) -- the reader that
                      under-reads whatever the answer does not score.

    python3 tools/glm_cheats.py            # -> out/glm_cheats.json + a table
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
sys.path.insert(0, str(T))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, T / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RG = _load("reading_grade")


def _masks_for(cfg_path: Path):
    from as_drawn_v2 import _family_masks
    from plan_ink import load_rgb
    return _family_masks(load_rgb(json.loads(cfg_path.read_text())["image"]))


def _recompute_gap_profiles(face: dict, masks) -> None:
    """Set every gap's ink_by_family to what the ORIGINAL IMAGE says under THIS
    face's strip -- honest numbers for a wrong representation."""
    from as_drawn_v2 import _profile
    by_axis = {"col": masks, "row": {k: v.T for k, v in masks.items()}}
    fam_t = by_axis[face["axis"]]
    c0, c1 = face["support_cols_px"]
    for g in face.get("gaps", []):
        if g.get("lo_px") is None:
            continue
        lo, hi = int(g["lo_px"]), int(g["hi_px"])
        prof = {}
        for fid in set().union(*(set(g.get("ink_by_family") or {}) for g in [g])):
            if fid in fam_t:
                prof[fid] = _profile(fam_t[fid], lo, hi, c0, c1)
        g["ink_by_family"] = prof


def _along_affine(face: dict):
    """px <-> m along the run axis, fitted from the face's own runs pairs."""
    xs, ys = [], []
    for (a, b), (ma, mb) in zip(face["runs_px"], face["runs_m"]):
        xs += [a, b]
        ys += [ma, mb]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return (lambda px: my + slope * (px - mx)), (lambda m: mx + (m - my) / slope)


def _midline_thin(doc: dict, max_span: float = 0.16) -> str:
    fl = doc["observations"]["face_lines"]
    by_id = {f["id"]: f for f in fl}
    pairs = doc["hypotheses"].get("pairs") or []
    keep_pairs, mids, drop, n = [], [], set(), 0
    for p in pairs:
        a, b = by_id.get(p["face_a"]), by_id.get(p["face_b"])
        if not a or not b or abs(a["pos_m"] - b["pos_m"]) > max_span:
            keep_pairs.append(p)
            continue
        n += 1
        c = json.loads(json.dumps(a))
        c["id"] = f"{a['id']}_{b['id']}_MID"
        c["pos_px"] = round((a["pos_px"] + b["pos_px"]) / 2.0, 3)
        c["pos_m"] = round((a["pos_m"] + b["pos_m"]) / 2.0, 4)
        c["support_cols_px"] = [int(c["pos_px"]), int(c["pos_px"]) + 1]
        m_px = doc["observations"]["calibration"]["mm_per_px"] / 1000.0
        sign = 1.0 if c["constant_world_axis"] == "x" else -1.0
        c["edges_m"] = sorted([round(c["pos_m"] + sign * (c["support_cols_px"][0] - c["pos_px"]) * m_px, 5),
                               round(c["pos_m"] + sign * (c["support_cols_px"][1] - c["pos_px"]) * m_px, 5)])
        c["support_width_m"] = round(c["edges_m"][1] - c["edges_m"][0], 5)
        mids.append(c)
        drop |= {a["id"], b["id"]}
    doc["observations"]["face_lines"] = [f for f in fl if f["id"] not in drop] + mids
    doc["hypotheses"]["pairs"] = keep_pairs
    for c in mids:
        doc["hypotheses"].setdefault("solid_band_walls", {})[c["id"]] = (
            "single centreline per wall -- legacy centreline representation")
    return f"collapsed {n} pairs into one thin midline each"


def _midline_band(doc: dict, masks, max_span: float = 0.16) -> str:
    fl = doc["observations"]["face_lines"]
    by_id = {f["id"]: f for f in fl}
    pairs = doc["hypotheses"].get("pairs") or []
    keep_pairs, bands, drop, n = [], [], set(), 0
    for p in pairs:
        a, b = by_id.get(p["face_a"]), by_id.get(p["face_b"])
        if not a or not b or abs(a["pos_m"] - b["pos_m"]) > max_span:
            keep_pairs.append(p)
            continue
        n += 1
        c = json.loads(json.dumps(a))
        c["id"] = f"{a['id']}_{b['id']}_BAND"
        c0 = min(a["support_cols_px"][0], b["support_cols_px"][0])
        c1 = max(a["support_cols_px"][1], b["support_cols_px"][1])
        c["support_cols_px"] = [c0, c1]
        c["pos_px"] = round((c0 + c1) / 2.0, 3)
        c["pos_m"] = round((a["pos_m"] + b["pos_m"]) / 2.0, 4)
        m_px = doc["observations"]["calibration"]["mm_per_px"] / 1000.0
        sign = 1.0 if c["constant_world_axis"] == "x" else -1.0
        c["edges_m"] = sorted([round(c["pos_m"] + sign * (c0 - c["pos_px"]) * m_px, 5),
                               round(c["pos_m"] + sign * (c1 - c["pos_px"]) * m_px, 5)])
        c["support_width_m"] = round(c["edges_m"][1] - c["edges_m"][0], 5)
        rs = sorted([tuple(sorted(r)) for r in a["runs_px"]] +
                    [tuple(sorted(r)) for r in b["runs_px"]])
        merged = []
        for lo, hi in rs:
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        c["runs_px"] = merged
        # ⚠️ runs_m is NOT a global affine of runs_px in this product (verified:
        # L008's px and m run lists are non-monotonic against each other), so the
        # metre intervals are merged independently -- both lists stay honest.
        ms = sorted([tuple(sorted(r)) for r in a["runs_m"]] +
                    [tuple(sorted(r)) for r in b["runs_m"]])
        mergedm = []
        for lo, hi in ms:
            if mergedm and lo <= mergedm[-1][1] + 1e-9:
                mergedm[-1][1] = max(mergedm[-1][1], hi)
            else:
                mergedm.append([lo, hi])
        c["runs_m"] = [[round(lo, 4), round(hi, 4)] for lo, hi in mergedm]
        c["gaps"] = json.loads(json.dumps(a.get("gaps", []) + b.get("gaps", [])))
        bands.append(c)
        drop |= {a["id"], b["id"]}
    doc["observations"]["face_lines"] = [f for f in fl if f["id"] not in drop] + bands
    doc["hypotheses"]["pairs"] = keep_pairs
    for c in bands:
        doc["hypotheses"].setdefault("solid_band_walls", {})[c["id"]] = (
            "one solid band per wall (dialect confusion: two-line wall read as a band)")
        _recompute_gap_profiles(c, masks)
    return f"swallowed {n} pairs into one solid-band face each (profiles honestly recomputed)"


def _band_to_two_edges(doc: dict, masks) -> str:
    fl = doc["observations"]["face_lines"]
    bands = doc["hypotheses"].get("solid_band_walls") or {}
    if not bands:
        return "no solid_band_walls in this product"
    m_px = doc["observations"]["calibration"]["mm_per_px"] / 1000.0
    out, n = [], 0
    for f in fl:
        if f["id"] not in bands:
            out.append(f)
            continue
        e0, e1 = f["edges_m"]
        sign = 1.0 if f["constant_world_axis"] == "x" else -1.0
        for tag, e, inward in (("_E0", e0, +2), ("_E1", e1, -2)):
            c = json.loads(json.dumps(f))
            c["id"] = f["id"] + tag
            c["pos_m"] = float(e)
            c["pos_px"] = round(f["pos_px"] + (e - f["pos_m"]) / (sign * m_px), 3)
            # nudge the 1-2 px support strip inward, off the band's own outline
            c["pos_px"] = round(c["pos_px"] + inward, 3)
            c["pos_m"] = round(c["pos_m"] + sign * inward * m_px, 5)
            c["support_cols_px"] = [int(c["pos_px"]), int(c["pos_px"]) + 1]
            c["edges_m"] = sorted([round(c["pos_m"] + sign * (c["support_cols_px"][0] - c["pos_px"]) * m_px, 5),
                                   round(c["pos_m"] + sign * (c["support_cols_px"][1] - c["pos_px"]) * m_px, 5)])
            c["support_width_m"] = round(c["edges_m"][1] - c["edges_m"][0], 5)
            out.append(c)
            n += 1
        doc["hypotheses"].setdefault("pairs", []).append(
            {"id": f"PB_{f['id']}", "face_a": f["id"] + "_E0", "face_b": f["id"] + "_E1",
             "spacing_m": round(e1 - e0, 4)})
    doc["observations"]["face_lines"] = out
    doc["hypotheses"]["solid_band_walls"] = {}
    for f in doc["observations"]["face_lines"]:
        if f["id"].endswith(("_E0", "_E1")):
            _recompute_gap_profiles(f, masks)
    return f"split {n // 2} solid bands into two edge faces each (same ink, other representation)"


def _skip_unscored_tails(doc: dict, den: dict, pos_tol: float = 0.08) -> str:
    hyp = doc["hypotheses"]
    graded = ({x for p in (hyp.get("pairs") or []) for x in (p["face_a"], p["face_b"])}
              | set(hyp.get("solid_band_walls") or {}) | set(hyp.get("unpaired_wall_faces") or {}))
    trimmed = 0
    for f in doc["observations"]["face_lines"]:
        if f["id"] not in graded or not f["runs_m"]:
            continue
        axis = "x" if f["constant_world_axis"] == "x" else "y"
        tgt = RG._union([(t["lo_m"], t["hi_m"]) for t in den["targets"]
                         if t["axis"] == axis and abs(t["const_m"] - f["pos_m"]) <= pos_tol])
        if not tgt:
            continue
        runs = [sorted(r) for r in f["runs_m"]]
        changed = False
        # trim the LOW overall extreme if it is not covered by any target
        i_low = min(range(len(runs)), key=lambda i: runs[i][0])
        lo = runs[i_low][0]
        if not any(t0 <= lo < t1 for t0, t1 in tgt):
            nxt = min([t0 for t0, _ in tgt if t0 >= lo], default=None)
            if nxt is not None and lo < nxt < runs[i_low][1]:
                runs[i_low][0] = nxt
                changed = True
        # trim the HIGH overall extreme if it is not covered by any target
        i_hi = max(range(len(runs)), key=lambda i: runs[i][1])
        hi = runs[i_hi][1]
        if not any(t0 < hi <= t1 for t0, t1 in tgt):
            prv = max([t1 for _, t1 in tgt if t1 <= hi], default=None)
            if prv is not None and runs[i_hi][0] < prv < hi:
                runs[i_hi][1] = prv
                changed = True
        new_runs = [r for r in runs if r[1] - r[0] >= 0.05]
        if changed or len(new_runs) != len(runs):
            trimmed += 1
            # per-run local px map (the product's own elementwise pairing); a
            # global affine is invalid here (see _midline_band note)
            px_of = {}
            for (pa, pb), (ma, mb) in zip(f["runs_px"], f["runs_m"]):
                lo_m, hi_m = sorted((ma, mb))
                lo_p, hi_p = sorted((pa, pb))
                px_of[(round(lo_m, 4), round(hi_m, 4))] = (lo_p, hi_p)
            new_px = []
            for lo, hi in new_runs:
                src = min(px_of, key=lambda k: abs(k[0] - lo) + abs(k[1] - hi))
                lo_p, hi_p = px_of[src]
                t0, t1 = src
                a_ = lo_p + (lo - t0) * (hi_p - lo_p) / max(1e-9, t1 - t0)
                b_ = lo_p + (hi - t0) * (hi_p - lo_p) / max(1e-9, t1 - t0)
                new_px.append([round(min(a_, b_), 1), round(max(a_, b_), 1)])
            f["runs_m"] = new_runs
            f["runs_px"] = new_px
            lo2 = min(r[0] for r in new_runs)
            hi2 = max(r[1] for r in new_runs)
            f["gaps"] = [g for g in f.get("gaps", [])
                         if g.get("span_m") and g["span_m"][1] > lo2 and g["span_m"][0] < hi2]
    return f"trimmed unexplained tails on {trimmed} graded faces"


def run_gates(doc_path: Path, cfg: str) -> dict:
    outp = doc_path.with_name(doc_path.stem + "_checks.json")
    r = subprocess.run([sys.executable, str(T / "checks_as_drawn_v2.py"),
                        str(doc_path), str(T / cfg), str(outp)],
                       capture_output=True, text=True, cwd=REPO)
    if r.returncode:
        return {"ERROR": r.stderr.strip()[-200:]}
    d = json.loads(outp.read_text())
    return {c["check"]: c["status"] for c in d["checks"]}


def run_gt(case: str, docs: dict) -> object:
    argmap = json.dumps(docs)
    r = subprocess.run([sys.executable, str(T / "reconstruct_check_v2.py"), case, argmap,
                        "/tmp/glm_gt_out.json"], capture_output=True, text=True, cwd=REPO)
    if r.returncode:
        return "ERROR"
    return json.loads(r.stdout)["overall_ok_pct"]


def main() -> int:
    cases = [("sm25_1f", "denominator_sm25_F1", "cfg_1f_full.json", "sm25-L_anchor",
              {"F1": "sm25_1f", "F2": "sm25_2f"}),
             ("sm25_2f", "denominator_sm25_F2", "cfg_2f_full.json", "sm25-L_anchor",
              {"F1": "sm25_1f", "F2": "sm25_2f"}),
             ("sm24_1f", "denominator_sm24_F1", "cfg_sm24.json", "sm24_anchor",
              {"F1": "sm24_1f"})]
    res = {}
    for prod, den_key, cfg, case, whole in cases:
        doc0 = json.loads((OUT / f"{prod}_v2.json").read_text())
        den = json.loads((OUT / f"{den_key}.json").read_text())
        entry = {"honest": RG.grade(json.loads(json.dumps(doc0)), den)["scores"]}
        masks = None
        kinds = ["midline_thin", "skip_unscored_tails"]
        if prod != "sm24_1f":
            kinds.append("midline_band")
        else:
            kinds.append("band_to_two_edges")
        for kind in kinds:
            doc = json.loads(json.dumps(doc0))
            if kind == "midline_thin":
                note = _midline_thin(doc)
            elif kind == "midline_band":
                if masks is None:
                    masks = _masks_for(T / cfg)
                note = _midline_band(doc, masks)
            elif kind == "band_to_two_edges":
                if masks is None:
                    masks = _masks_for(T / cfg)
                note = _band_to_two_edges(doc, masks)
            else:
                note = _skip_unscored_tails(doc, den)
            p = OUT / f"{prod}_GLM_{kind}.json"
            p.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
            g = RG.grade(doc, den)
            gates = run_gates(p, cfg)
            # gt-side with the whole-case honest partners where the case has two floors
            docs_gt = {}
            for k, v in whole.items():
                docs_gt[k] = str(p) if v == prod else str(OUT / f"{v}_v2.json")
            gt = run_gt(case, docs_gt)
            entry[kind] = {"note": note, "scores": g["scores"], "by_verdict": g["by_verdict"],
                           "perception": g["perception"], "gates": gates, "gt_side_ok_pct": gt,
                           "n_face_lines": len(doc["observations"]["face_lines"])}
        res[prod] = entry
        print(f"== {prod} (honest faces={len(doc0['observations']['face_lines'])}) ==")
        for kind, v in entry.items():
            if kind == "honest":
                s = v
                print(f"  {'honest':22s} drawn={s['C1_C2_targets_drawn_pct']:>6} "
                      f"cov={s['C2_length_coverage_pct']:>6} split={s['C3_bad_split']:>3} "
                      f"extra={s['C4_extra_length_m']:>8}")
                continue
            s, gates, gt = v["scores"], v["gates"], v["gt_side_ok_pct"]
            reds = [k.split("_")[0] for k, st in gates.items() if st == "red"] if isinstance(gates, dict) else ["ERR"]
            print(f"  {kind:22s} drawn={s['C1_C2_targets_drawn_pct']:>6} "
                  f"cov={s['C2_length_coverage_pct']:>6} split={s['C3_bad_split']:>3} "
                  f"extra={s['C4_extra_length_m']:>8} gt={gt} red_gates={reds or 'NONE'}")
    (OUT / "glm_cheats.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"-> {OUT / 'glm_cheats.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
