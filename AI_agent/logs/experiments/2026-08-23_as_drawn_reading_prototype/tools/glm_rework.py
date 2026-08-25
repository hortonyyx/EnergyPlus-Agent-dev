"""GLM re-review (2026-08-24c): new cheat shapes against the POST-REWORK ruler set.

The sender's six fixes are all in (D4 opening guard / reverse longest-hole /
grader consumes edges_m / width>=0.5x rule / GROUP_QUANT=1mm / allowed caps).
This tool attacks what they did NOT change:

  band_collapse      Every interior wall pair of the TWO-LINE dialect (sm25)
                    re-represented as ONE self-consistent band observation:
                    support = both real ink lines' columns, runs = union,
                    runs_m via the producer's own affine, gaps and their ink
                    profiles HONESTLY recomputed over the widened strip,
                    opening candidates/naming remapped.  No fabricated number
                    anywhere -- only the representation is wrong (the batch
                    guide forbids band readings of two-line walls).  The 4th
                    review's ``midline_band`` failed the recompute gate only
                    through hand-splicing artifacts (runs_px/runs_m elementwise
                    mispairing); this one is built the way a native band reader
                    would build it.
  band_partial(frac) The minimal band that still reaches the second face
                    within pos_tol: support stops at frac x spacing.  Used to
                    sweep the width-rule coefficient the sender left unswept.
  fabricate_cand     The naming gate reads ``hypotheses.opening_candidates[*].
                    ink_by_family`` -- a quantity NO gate recomputes (the gap
                    gate recomputes face_lines[*].gaps only).  A/B: same lie
                    with the honest profile (gate red) vs a fabricated profile
                    (gate green).
  launder_non_wall   Bucket the top C4-extra faces as non-wall (the grader
                    only charges C4 on positively-graded faces).  Checks
                    whether abstention can zero out C4.

Also measures the two quantities a "band must be ink-filled / contiguous"
gate would need (fill fraction, longest blank column run inside the strip),
for honest sm25 thin lines, honest sm24 filled bands, and the collapsed bands.

    python3 tools/glm_rework.py        # -> out/glm_rework.json + tables
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
T, OUT = EXP / "tools", EXP / "out"
sys.path.insert(0, str(T))

from glm_cheats import RG, _masks_for, run_gt, run_gates  # noqa: E402

CASES = {
    "sm25_1f": ("denominator_sm25_F1", "cfg_1f_full.json", "sm25-L_anchor",
                {"F1": "sm25_1f", "F2": "sm25_2f"}),
    "sm25_2f": ("denominator_sm25_F2", "cfg_2f_full.json", "sm25-L_anchor",
                {"F1": "sm25_1f", "F2": "sm25_2f"}),
    "sm24_1f": ("denominator_sm24_F1", "cfg_sm24.json", "sm24_anchor",
                {"F1": "sm24_1f"}),
}


# ------------------------------------------------------------------ helpers --
def _fit_along(face: dict):
    """px -> m along the run axis, fitted from the face's own runs pairs.

    Elementwise pairing is unreliable (the producer sorts the metre pair), so
    both sign assignments are tried and the consistent one wins.
    """
    pts_pos, pts_neg = [], []
    for (pa, pb), (ma, mb) in zip(face["runs_px"], face["runs_m"]):
        pa, pb, ma, mb = float(pa), float(pb), float(ma), float(mb)
        pts_pos += [(pa, ma), (pb, mb)]
        pts_neg += [(pa, mb), (pb, ma)]

    def _fit(pts):
        n = len(pts)
        mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        if sxx == 0:
            return None, float("inf")
        s = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
        res = sum((p[1] - (my + s * (p[0] - mx))) ** 2 for p in pts)
        return (lambda px: my + s * (px - mx)), res

    f_pos, r_pos = _fit(pts_pos)
    f_neg, r_neg = _fit(pts_neg)
    return f_pos if r_pos <= r_neg else f_neg


def _merge_runs(rs):
    out = []
    for lo, hi in sorted(tuple(sorted(r)) for r in rs):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def _band_gap_profiles(face: dict, masks) -> None:
    from as_drawn_v2 import _profile
    by_axis = {"col": masks, "row": {k: v.T for k, v in masks.items()}}
    fam_t = by_axis[face["axis"]]
    c0, c1 = face["support_cols_px"]
    for g in face.get("gaps", []):
        lo, hi = int(g["lo_px"]), int(g["hi_px"])
        g["ink_by_family"] = {fid: _profile(m, lo, hi, c0, c1)
                              for fid, m in fam_t.items()}


def _rebuild_candidates(doc: dict, drop_ids: set, new_faces: list) -> dict:
    """opening_candidates rebuilt for the new face lines; old kinds carried
    over by span overlap, leftovers named not_opening (their honest profile
    carries no opening ink).  Every name whose candidate died is dropped --
    the naming gate counts dangling references."""
    hyp = doc["hypotheses"]
    old = hyp["opening_candidates"]
    types = dict(hyp.get("opening_types") or {})
    kept = [c for c in old if c["face_line"] not in drop_ids]
    dead = {c["id"] for c in old if c["face_line"] in drop_ids}
    carried = {}
    new_cands = []
    for f in new_faces:
        for gi, g in enumerate(f["gaps"]):
            cid = f"{f['id']}g{gi}"
            lo, hi = g["span_m"]
            new_cands.append({"id": cid, "face_line": f["id"], "gap_index": gi,
                              "span_m": g["span_m"], "len_m": g["len_m"],
                              "len_px": g["len_px"],
                              "ink_by_family": g["ink_by_family"]})
            # carry the naming of any old candidate OF THIS BAND'S OWN FACES
            # whose span sits inside this gap (parallel walls' door spans
            # overlap numerically -- a global match steals names across walls)
            own = set(f.get("_from_faces") or ())
            best = None
            for c in old:
                if c["face_line"] not in (own or drop_ids):
                    continue
                olo, ohi = c["span_m"]
                ov = max(0.0, min(ohi, hi) - max(olo, lo))
                if ov > 0.5 * max(1e-9, hi - lo) and (best is None or ov > best[0]):
                    best = (ov, c)
            if best is not None:
                carried[best[1]["id"]] = cid
    for f in new_faces:
        f.pop("_from_faces", None)
    hyp["opening_candidates"] = kept + new_cands
    nt = {}
    for k, v in types.items():
        if k in carried:
            nt[carried[k]] = v
    for c in new_cands:
        nt.setdefault(c["id"], "not_opening")
    final = {k: v for k, v in types.items() if k not in dead}
    final.update(nt)
    hyp["opening_types"] = final
    return carried


# ----------------------------------------------------------------- fixtures --
def band_collapse(doc: dict, masks, max_span: float = 0.16) -> str:
    """Every interior wall pair re-read as one self-consistent filled band.

    Conflict-aware the way a careful band reader would be: a pair is only
    collapsed when its strip does not overlap any other surviving observation's
    support -- except purely non-wall strokes sitting inside the strip (the
    callout-text strokes), which the band reader never reports as face lines
    in the first place, so they are absorbed."""
    fl = doc["observations"]["face_lines"]
    by_id = {f["id"]: f for f in fl}
    hyp = doc["hypotheses"]
    soft = set(hyp.get("non_wall_face_lines") or {}) | set(hyp.get("ambiguous_face_lines") or {})
    pairs = hyp.get("pairs") or []
    m_px = doc["observations"]["calibration"]["mm_per_px"] / 1000.0

    taken: list[tuple[int, int]] = []      # strips already claimed by a band
    absorbed: set[str] = set()             # soft strokes swallowed by a strip
    chosen: list[tuple] = []               # (pair, a, b)
    for p in pairs:
        a, b = by_id.get(p["face_a"]), by_id.get(p["face_b"])
        if not a or not b or abs(a["pos_m"] - b["pos_m"]) > max_span or a["axis"] != b["axis"]:
            continue
        c0 = min(a["support_cols_px"][0], b["support_cols_px"][0])
        c1 = max(a["support_cols_px"][1], b["support_cols_px"][1])
        if any(min(c1, t1) > max(c0, t0) for t0, t1 in taken):
            continue                       # another band already claims this span
        clash = [f for f in fl
                 if f["id"] not in (a["id"], b["id"]) and f["axis"] == a["axis"]
                 and min(c1, f["support_cols_px"][1]) > max(c0, f["support_cols_px"][0])]
        hard = [f for f in clash if f["id"] not in soft]
        if hard:
            continue                       # would overlap a real neighbouring line
        absorbed |= {f["id"] for f in clash}
        taken.append((c0, c1))
        chosen.append((p, a, b))

    drop, bands = set(), []
    old_cands = doc["hypotheses"]["opening_candidates"]
    old_types = dict(doc["hypotheses"].get("opening_types") or {})
    for p, a, b in chosen:
        f2m = _fit_along(a) or _fit_along(b)
        # invert the along-axis affine so door spans can be cut in pixel space
        pts = sorted((f2m(float(x)), float(x))
                     for r in a["runs_px"] for x in r)
        m2f = lambda mv: pts[0][1] + (mv - pts[0][0]) * (pts[-1][1] - pts[0][1]) / (pts[-1][0] - pts[0][0])
        c = json.loads(json.dumps(a))
        c["id"] = f"BND_{a['id']}_{b['id']}"
        c0 = min(a["support_cols_px"][0], b["support_cols_px"][0])
        c1 = max(a["support_cols_px"][1], b["support_cols_px"][1])
        c["support_cols_px"] = [c0, c1]
        c["pos_px"] = round((a["pos_px"] + b["pos_px"]) / 2.0, 3)
        c["pos_m"] = round((a["pos_m"] + b["pos_m"]) / 2.0, 4)
        sign = 1.0 if c["constant_world_axis"] == "x" else -1.0
        c["edges_m"] = sorted([round(c["pos_m"] + sign * (c0 - c["pos_px"]) * m_px, 5),
                               round(c["pos_m"] + sign * (c1 - c["pos_px"]) * m_px, 5)])
        c["support_width_m"] = round(c["edges_m"][1] - c["edges_m"][0], 5)
        runs = _merge_runs(list(a["runs_px"]) + list(b["runs_px"]))
        # ⭐ a door that breaks only ONE of the two faces is healed by the
        # union; a band reader that sees the door ink cuts it back out
        door_px = []
        for cand in old_cands:
            if cand["face_line"] in (a["id"], b["id"]) and \
                    old_types.get(cand["id"]) in ("door", "window"):
                lo, hi = sorted(cand["span_m"])
                door_px.append(sorted((m2f(lo), m2f(hi))))   # px may run against m
        for dlo, dhi in sorted(door_px):
            dlo, dhi = int(round(dlo)), int(round(dhi))   # pixel indices, as a native reader emits
            cut = []
            for lo, hi in runs:
                if dhi <= lo or dlo >= hi:
                    cut.append([lo, hi])
                    continue
                if dlo > lo:
                    cut.append([lo, dlo])
                if dhi < hi:
                    cut.append([dhi, hi])
            runs = _merge_runs([r for r in cut if r[1] - r[0] > 0])
        c["runs_px"] = runs
        c["runs_m"] = [[round(min(f2m(lo), f2m(hi)), 4), round(max(f2m(lo), f2m(hi)), 4)]
                       for lo, hi in runs]
        c["gaps"] = [{"lo_px": int(runs[i][1]), "hi_px": int(runs[i + 1][0]),
                      "len_px": int(runs[i + 1][0]) - int(runs[i][1])}
                     for i in range(len(runs) - 1)]
        for g in c["gaps"]:
            lo, hi = f2m(g["lo_px"]), f2m(g["hi_px"])
            g["span_m"] = [round(min(lo, hi), 4), round(max(lo, hi), 4)]
            g["len_m"] = round(abs(hi - lo), 4)
        c["covered_px"] = int(sum(b_ - a_ for a_, b_ in runs))
        c["_from_faces"] = [a["id"], b["id"]]
        bands.append(c)
        drop |= {a["id"], b["id"]}

    keep_pairs = [p for p in pairs if id(p) not in {id(q) for q, _, _ in chosen}]
    drop |= absorbed
    for bucket in ("non_wall_face_lines", "ambiguous_face_lines"):
        for k in absorbed:
            (hyp.get(bucket) or {}).pop(k, None)
    doc["observations"]["face_lines"] = [f for f in fl if f["id"] not in drop] + bands
    hyp["pairs"] = keep_pairs
    for c in bands:
        hyp.setdefault("solid_band_walls", {})[c["id"]] = (
            "one solid band per wall: two-line wall read as a filled band "
            "(dialect confusion, sm24 habit applied to sm25)")
        _band_gap_profiles(c, masks)
    _rebuild_candidates(doc, drop, bands)
    return (f"collapsed {len(bands)} interior pairs into one self-consistent band each "
            f"(skipped {sum(1 for p in pairs if abs(by_id[p['face_a']]['pos_m']-by_id[p['face_b']]['pos_m'])<=max_span) - len(bands)} "
            f"for strip conflicts, absorbed {len(absorbed)} text strokes; "
            f"all numbers honestly recomputed)")


def band_partial(doc: dict, masks, frac: float, max_span: float = 0.16) -> str:
    """Minimal band: support runs from face A's stroke to frac x spacing.

    Runs and gaps are inherited unchanged from face A (the strip still covers
    A's whole stroke, so the reverse ledger stays true); only the support
    span -- and therefore edges_m -- is widened towards face B."""
    fl = doc["observations"]["face_lines"]
    by_id = {f["id"]: f for f in fl}
    pairs = doc["hypotheses"].get("pairs") or []
    keep_pairs, bands, drop, n = [], [], set(), 0
    m_px = doc["observations"]["calibration"]["mm_per_px"] / 1000.0
    for p in pairs:
        a, b = by_id.get(p["face_a"]), by_id.get(p["face_b"])
        if not a or not b or abs(a["pos_m"] - b["pos_m"]) > max_span:
            keep_pairs.append(p)
            continue
        n += 1
        c = json.loads(json.dumps(a))
        c["id"] = f"BNDP_{a['id']}_{b['id']}"
        span_px = abs(b["pos_px"] - a["pos_px"])
        c1 = int(round(a["pos_px"] + frac * span_px))
        c["support_cols_px"] = [a["support_cols_px"][0], max(c1, a["support_cols_px"][1])]
        sign = 1.0 if c["constant_world_axis"] == "x" else -1.0
        c["edges_m"] = sorted([round(c["pos_m"] + sign * (c["support_cols_px"][0] - c["pos_px"]) * m_px, 5),
                               round(c["pos_m"] + sign * (c["support_cols_px"][1] - c["pos_px"]) * m_px, 5)])
        c["support_width_m"] = round(c["edges_m"][1] - c["edges_m"][0], 5)
        bands.append(c)
        drop |= {a["id"], b["id"]}
    doc["observations"]["face_lines"] = [f for f in fl if f["id"] not in drop] + bands
    doc["hypotheses"]["pairs"] = keep_pairs
    for c in bands:
        doc["hypotheses"].setdefault("solid_band_walls", {})[c["id"]] = (
            f"partial band, support reaches {frac:.2f} of the wall spacing")
        _band_gap_profiles(c, masks)
    _rebuild_candidates(doc, drop, bands)
    return (f"{n} pairs -> one partial-band each (support = {frac:.2f} x spacing); "
            "runs/gaps inherited unchanged from face A")


def fabricate_candidate(doc: dict, masks, fabricate: bool) -> str:
    """Flip one honestly-named not_opening/ambiguous blank stretch to 'door'.

    fabricate=False: the candidate's ink profile stays honest (no opening ink
    on the stretch) -- the naming gate should go red.  fabricate=True: the
    profile is overwritten with numbers no gate recomputes -- green?"""
    hyp = doc["hypotheses"]
    fen = hyp["family_roles"]["assignment"]["fenestration"]
    victim = None
    for c in hyp["opening_candidates"]:
        prof = (c.get("ink_by_family") or {}).get(fen) or {}
        ink = (prof.get("on_line") or 0) + (prof.get("span_ratio") or 0.0)
        if hyp["opening_types"].get(c["id"]) in ("not_opening", "ambiguous") and ink == 0:
            if victim is None or (c["len_m"] or 0) > victim["len_m"]:
                victim = c
    if victim is None:
        return "no suitable victim stretch found"
    hyp["opening_types"][victim["id"]] = "door"
    if fabricate:
        victim["ink_by_family"][fen] = {"on_line": 500, "span_ratio": 1.0,
                                        "nearest_px": 0, "by_distance_px": {}}
    return (f"named {victim['id']} (len {victim['len_m']} m, honest opening ink "
            f"on_line AND span_ratio both 0) a DOOR; profile "
            f"{'FABRICATED (on_line=500, span_ratio=1.0)' if fabricate else 'left honest'}")


def launder_non_wall(doc: dict, grade_honest: dict) -> str:
    """Bucket the faces carrying the most C4 extra as non_wall (with reasons)."""
    hyp = doc["hypotheses"]
    fl = {f["id"]: f for f in doc["observations"]["face_lines"]}
    extras = grade_honest["extras"]
    hit, tot = set(), 0.0
    for e in extras:
        if tot >= 0.8 * grade_honest["scores"]["C4_extra_length_m"]:
            break
        hit.add(e["face"])
        tot += e["unexplained_m"]
    pairs = []
    for p in hyp["pairs"]:
        if p["face_a"] in hit or p["face_b"] in hit:
            hit |= {p["face_a"], p["face_b"]}
        else:
            pairs.append(p)
    hyp["pairs"] = pairs
    for fid in hit:
        hyp.setdefault("non_wall_face_lines", {})[fid] = (
            "long straight stroke; reader calls it the edge of a fitted unit")
    return (f"{len(hit)} faces ({tot:.2f} m of the honest extra) bucketed non_wall")


# ---------------------------------------------------- band fill / contiguity --
def strip_stats(doc_path: Path, cfg: str) -> dict:
    """For every face line: ink fill fraction, longest blank column run, and
    (mirroring the producer's own grouping definition) how many ink-column
    GROUPS its support strip holds.  The honest producer emits one group per
    face line; a strip that spans two disjoint lines carries two."""
    import numpy as np
    from as_drawn_v2 import _family_masks, vertical_runs_mask
    from plan_ink import load_rgb

    doc = json.loads(doc_path.read_text())
    masks = _family_masks(load_rgb(json.loads((T / cfg).read_text())["image"]))
    st = masks[doc["hypotheses"]["family_roles"]["assignment"]["structure"]]
    by_axis = {"col": st, "row": st.T}
    out = {}
    for f in doc["observations"]["face_lines"]:
        m = by_axis[f["axis"]]
        c0, c1 = f["support_cols_px"]
        rows = sorted({r for a, b in f["runs_px"] for r in range(int(a), int(b))})
        if not rows:
            continue
        sub = m[rows, c0:c1]
        fill = float(sub.mean()) if sub.size else 0.0
        blank = (~sub.any(axis=0))
        longest = cur = 0
        for v in blank:
            cur = 0 if v else cur + 1
            longest = max(longest, cur)
        keep = vertical_runs_mask(m[:, max(0, c0 - 1):c1 + 1], 14)
        sup = keep.sum(0)
        cols = np.flatnonzero(sup >= 10)
        ngroups = 1 if len(cols) else 0
        for x, y in zip(cols, cols[1:]):
            if y - x > 1:
                ngroups += 1
        out[f["id"]] = {"width_m": f.get("support_width_m"),
                        "fill": round(fill, 3), "longest_blank_cols": int(longest),
                        "ink_column_groups": int(ngroups)}
    return out


# --------------------------------------------------------- coefficient sweep --
def _grade_with_coeff(coeff: float):
    # ⭐ 2026-08-25 (debt D-1): tools/reading_grade.py is now a forwarding shim;
    # the live ruler's SOURCE lives at src/agent/judge/as_drawn/reading_grade.py,
    # so the coefficient sweep reads that copy -- the same move run_all.py made
    # at transplant time.  The drift guard below still anchors on the literal
    # rule text, which the src copy carries verbatim (line 175).
    src = (EXP.parents[3] / "src/agent/judge/as_drawn/reading_grade.py").read_text()
    # ⚠️ 2026-08-24 (six审 Finding 2): this guard was anchored on the literal 0.5.
    # When the coefficient became the named constant WIDTH_COEFF the guard fired
    # -- correctly -- but the harness swallowed the failure and shipped a STALE
    # glm_rework.json, so RESULTS_v2 showed the fifth review's two flagship
    # cheats as GREEN.  Re-anchored on the constant; the guard itself stays.
    old = "ln[\"width_m\"] < WIDTH_COEFF * need"
    assert old in src, "width rule source drifted"
    import types
    mod = types.ModuleType(f"rg_c{coeff}")
    mod.__file__ = str(EXP.parents[3] / "src/agent/judge/as_drawn/reading_grade.py")
    exec(compile(src.replace(old, f"ln[\"width_m\"] < {coeff} * need"), "rg_coeff", "exec"),
         mod.__dict__)
    return mod


def sweep_coefficient() -> dict:
    doc0 = json.loads((OUT / "sm25_1f_v2.json").read_text())
    den = json.loads((OUT / "denominator_sm25_F1.json").read_text())
    masks = _masks_for(T / CASES["sm25_1f"][1])
    fixtures = {"honest": doc0}
    for frac in (0.35, 0.45, 0.5, 0.7, 1.0):
        d = json.loads(json.dumps(doc0))
        band_partial(d, masks, frac)
        fixtures[f"band_partial_{frac}"] = d
    d = json.loads(json.dumps(doc0))
    band_collapse(d, masks)
    fixtures["band_collapse"] = d
    # honest sm24: the product the coefficient must not hurt
    d24 = json.loads((OUT / "sm24_1f_v2.json").read_text())
    den24 = json.loads((OUT / "denominator_sm24_F1.json").read_text())

    tbl = {}
    for coeff in (0.3, 0.5, 0.7, 1.0, 1.15):
        rg = _grade_with_coeff(coeff)
        row = {k: rg.grade(json.loads(json.dumps(v)), den)["scores"]["C1_C2_targets_drawn_pct"]
               for k, v in fixtures.items()}
        row["honest_sm24"] = rg.grade(json.loads(json.dumps(d24)), den24)["scores"]["C1_C2_targets_drawn_pct"]
        tbl[coeff] = row
    return tbl


# --------------------------------------------------------------------- main --
def _report(case: str, kind: str, doc, den, cfg, gates_extra=None):
    p = OUT / f"{case}_GLM_{kind}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    g = RG.grade(doc, den)
    gates = run_gates(p, cfg)
    docs_gt = {}
    for k, v in CASES[case][3].items():
        docs_gt[k] = str(p) if v == case else str(OUT / f"{v}_v2.json")
    gt = run_gt(CASES[case][2], docs_gt)
    return {"note": None, "scores": g["scores"], "by_verdict": g["by_verdict"],
            "gates": gates, "gt_side_ok_pct": gt,
            "n_face_lines": len(doc["observations"]["face_lines"])}, p


def main() -> int:
    res = {}

    # ---- 1. band_collapse on sm25 1f + 2f ----
    for case in ("sm25_1f", "sm25_2f"):
        den_key, cfg, _, _ = CASES[case]
        doc0 = json.loads((OUT / f"{case}_v2.json").read_text())
        den = json.loads((OUT / f"{den_key}.json").read_text())
        entry = {"honest": RG.grade(json.loads(json.dumps(doc0)), den)["scores"]}
        masks = _masks_for(T / cfg)
        doc = json.loads(json.dumps(doc0))
        note = band_collapse(doc, masks)
        r, p = _report(case, "band_collapse", doc, den, cfg)
        r["note"] = note
        entry["band_collapse"] = r
        res[case] = entry
        s, gates, gt = r["scores"], r["gates"], r["gt_side_ok_pct"]
        reds = [k.split("_")[0] for k, st in gates.items() if st == "red"] if isinstance(gates, dict) else ["ERR"]
        print(f"== {case} band_collapse ==  faces {r['n_face_lines']} "
              f"(honest {len(doc0['observations']['face_lines'])})")
        print(f"   drawn={s['C1_C2_targets_drawn_pct']} cov={s['C2_length_coverage_pct']} "
              f"split={s['C3_bad_split']} extra={s['C4_extra_length_m']} C5={s['C5_openings_named_right_pct']} "
              f"gt={gt} red_gates={reds or 'NONE'}")

    # ---- 2. candidate profile fabrication A/B ----
    case = "sm25_1f"
    den_key, cfg, _, _ = CASES[case]
    doc0 = json.loads((OUT / f"{case}_v2.json").read_text())
    den = json.loads((OUT / f"{den_key}.json").read_text())
    masks = _masks_for(T / cfg)
    fab = {}
    for tag, flag in (("honest_profile", False), ("fabricated_profile", True)):
        doc = json.loads(json.dumps(doc0))
        note = fabricate_candidate(doc, masks, flag)
        r, p = _report(case, f"fab_{tag}", doc, den, cfg)
        r["note"] = note
        fab[tag] = r
        gates = r["gates"]
        reds = [k for k, st in gates.items() if st == "red"] if isinstance(gates, dict) else ["ERR"]
        print(f"== naming fabrication {tag} ==  {note}")
        print(f"   gt={r['gt_side_ok_pct']} C5={r['scores']['C5_openings_named_right_pct']} "
              f"red_gates={reds or 'NONE'}")
    res["fabrication"] = fab

    # ---- 3. coefficient sweep ----
    print("== width-rule coefficient sweep (C1, sm25_1f fixtures + honest sm24) ==")
    tbl = sweep_coefficient()
    res["coefficient_sweep"] = tbl
    hdr = ["coeff"] + list(next(iter(tbl.values())).keys())
    print("  " + "  ".join(f"{h[:18]:>18}" for h in hdr))
    for coeff, row in tbl.items():
        print("  " + "  ".join(f"{coeff!s:>18}" if i == 0 else f"{row[h]:>18}" for i, h in enumerate(hdr)))

    # ---- 4. launder_non_wall on sm24 ----
    case = "sm24_1f"
    den_key, cfg, _, _ = CASES[case]
    doc0 = json.loads((OUT / f"{case}_v2.json").read_text())
    den = json.loads((OUT / f"{den_key}.json").read_text())
    g_honest = RG.grade(json.loads(json.dumps(doc0)), den)
    doc = json.loads(json.dumps(doc0))
    note = launder_non_wall(doc, g_honest)
    r, p = _report(case, "launder_non_wall", doc, den, cfg)
    r["note"] = note
    res["launder_non_wall"] = {"honest": g_honest["scores"], **r}
    s = r["scores"]
    print(f"== launder_non_wall sm24 ==  {note}")
    print(f"   C1 {g_honest['scores']['C1_C2_targets_drawn_pct']} -> {s['C1_C2_targets_drawn_pct']}; "
          f"C4 {g_honest['scores']['C4_extra_length_m']} -> {s['C4_extra_length_m']}")

    # ---- 5. band fill / contiguity stats (the proposed missing gate) ----
    stats = {}
    for case in ("sm25_1f", "sm24_1f"):
        st = strip_stats(OUT / f"{case}_v2.json", CASES[case][1])
        stats[case] = {
            "n_faces": len(st),
            "ink_column_groups_hist": {n: sum(1 for v in st.values() if v["ink_column_groups"] == n)
                                       for n in sorted({v["ink_column_groups"] for v in st.values()})},
            "wide_faces_fill_minmax": ([min(v["fill"] for v in st.values() if (v["width_m"] or 0) >= 0.06),
                                        max(v["fill"] for v in st.values() if (v["width_m"] or 0) >= 0.06)]
                                       if any((v["width_m"] or 0) >= 0.06 for v in st.values()) else None),
        }
    st = strip_stats(OUT / "sm25_1f_GLM_band_collapse.json", CASES["sm25_1f"][1])
    bnd = {k: v for k, v in st.items() if k.startswith("BND_")}
    stats["band_collapse_bands"] = {
        "n_bands": len(bnd),
        "ink_column_groups_hist": {n: sum(1 for v in bnd.values() if v["ink_column_groups"] == n)
                                   for n in sorted({v["ink_column_groups"] for v in bnd.values()})},
        "fill_minmax": [min(v["fill"] for v in bnd.values()), max(v["fill"] for v in bnd.values())],
    }
    res["strip_stats"] = stats
    print("== strip stats (fill / producer-mirrored ink-column groups) ==")
    for k, v in stats.items():
        print(f"  {k}: {json.dumps(v)[:300]}")

    (OUT / "glm_rework.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"-> {OUT / 'glm_rework.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
