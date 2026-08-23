"""As-drawn plan transcription, **v2 schema** — three layers, no domain classification.

⭐ Why this file exists (2026-08-23): two cross-family reviews rejected the v1
prototype, and the second one's headline was that the DESIGN DOCUMENT described
a shape the CODE did not implement -- so every number quoted in support of it
had actually been produced by the v1 shape.  This module is that shape, for
real, so the numbers can be re-measured on the thing being proposed.

The product is split into three layers, and the split is the whole point:

  ``observations``   what a ruler measured on pixels.  ⭐ The only scorable
                     layer, and the only one a downstream consumer may treat
                     as fact.
  ``declarations``   what the drawing or its config ASSERTS, transcribed
                     verbatim.  Compared by text, never by meaning.
  ``hypotheses``     everything derived from the first two.  ⛔ Not scored and
                     droppable in one piece.

The property that makes the split worth having: **``observations`` +
``declarations`` must be enough to re-derive every hypothesis.**  A field that
fails that test is smuggling a judgement.

What changed from v1, and why each one was forced:

  * **No bridging.**  v1 merged blank stretches shorter than 0.60 m into the
    run and labelled the rest ``break``.  The first review showed the same
    0.60 m does opposite work on the two ink layers (closing dropouts in wall
    lines, swallowing piers between windows).  Runs here are RAW maximal
    continuous stretches and every blank is reported.
  * **No ``class`` on a gap.**  A gap carries measurements; naming it is
    1_correction's job.
  * **Re-computable opening evidence.**  v1 emitted two aggregate cyan-pixel
    counts at one fixed window, and a consumer who disliked the window could
    not recompute.  Worse, the check built on it could be satisfied by ONE
    pixel.  Each gap now carries a distance PROFILE plus the along-gap span
    that actually has opening ink, and the components themselves are emitted.
  * ⭐ **No colour is called a wall.**  ``plan_ink.ink_families`` hard-codes
    ``neutral -> structure`` / ``cyan -> fenestration`` / ``magenta ->
    furniture``.  That is a drawing convention, and inventing it in code makes
    every unfamiliar drawing style a silent failure -- which is exactly how
    F-69 happened (windows lived on a colour layer the one mask could not see,
    and it returned a confident zero).  Ink families are now DISCOVERED by
    measurement (``ink_palette``) and left unnamed; which family carries walls
    and which carries openings is **perception, so it comes in from outside**
    (the model; here, the config stands in for it) and is recorded as a
    hypothesis with the measured evidence beside it.  ⛔ An assignment naming a
    family the drawing does not have is a LOUD failure, never a quiet zero.
  * **Pairing is a hypothesis with every admissible partner listed.**  v1 took
    the first admissible partner and broke.  (Measured: that greedy order was
    not what mis-paired sm24 -- 0 of its 98 lines had more than one admissible
    partner -- but enumerating costs nothing and removes the question.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from plan_ink import (  # noqa: E402
    Axis, INK_MIN, dump, fit_chain, load_rgb, vertical_runs_mask, witness_ticks,
)
from ink_palette import MERGE_DIST, _chroma_key, _merge_cells, MIN_SHARE, palette

SCHEMA = "as_drawn_plan_v2"

# Distance bins (px) for the per-gap opening-ink profile. A profile, not a
# single windowed count, is what makes the evidence re-computable: a consumer
# who wants a 0.10 m window sums the near bins, one who wants 0.30 m sums more.
PROFILE_BINS_PX = (2, 5, 10, 15, 25)

# A position along a line counts as inked when at least this fraction of the
# group's own columns carry ink there. Same value and same reason as v1: a
# solid band is ~9 px wide and "any column" would call it present wherever only
# its edge is drawn.
FILL_RATIO = 0.5


def _raw_runs(flags: np.ndarray) -> tuple[list[list[int]], list[list[int]]]:
    """Maximal continuous runs of True, and every blank between them.

    ⛔ No bridging, no threshold, no classification -- that is the v2 change.
    """
    idx = np.flatnonzero(flags)
    if idx.size == 0:
        return [], []
    edges = np.flatnonzero(np.diff(idx) > 1)
    runs, start = [], idx[0]
    for e in edges:
        runs.append([int(start), int(idx[e]) + 1])
        start = idx[e + 1]
    runs.append([int(start), int(idx[-1]) + 1])
    gaps = [[a[1], b[0]] for a, b in zip(runs, runs[1:])]
    return runs, gaps


def _profile(mask: np.ndarray, lo: int, hi: int, c0: int, c1: int) -> dict[str, Any]:
    """Distance profile of one ink family across a blank stretch of a line.

    ``on_line`` is the group's own columns; each further bin adds a ring of
    columns at that distance.  ``span_ratio`` is the fraction of the stretch's
    LENGTH that has any such ink within the widest bin -- the quantity a single
    stray pixel cannot move, which is exactly what the v1 evidence lacked.
    """
    if hi <= lo:
        return {"on_line": 0, "by_distance_px": {}, "span_ratio": 0.0, "nearest_px": None}
    out: dict[str, int] = {}
    prev_lo, prev_hi = c0, c1
    for d in PROFILE_BINS_PX:
        w_lo, w_hi = max(0, c0 - d), c1 + d
        ring = int(mask[lo:hi, w_lo:w_hi].sum()) - int(mask[lo:hi, prev_lo:prev_hi].sum())
        out[str(d)] = ring
        prev_lo, prev_hi = w_lo, w_hi
    on_line = int(mask[lo:hi, c0:c1].sum())
    widest = slice(max(0, c0 - PROFILE_BINS_PX[-1]), c1 + PROFILE_BINS_PX[-1])
    rows = mask[lo:hi, widest].any(axis=1)
    nearest = None
    for d in (0,) + PROFILE_BINS_PX:
        if int(mask[lo:hi, max(0, c0 - d):c1 + d].sum()) > 0:
            nearest = d
            break
    return {"on_line": on_line, "by_distance_px": out,
            "span_ratio": round(float(rows.mean()), 4), "nearest_px": nearest}


def _family_masks(a: np.ndarray, merge_dist: float = MERGE_DIST) -> dict[str, np.ndarray]:
    """Pixel mask per DISCOVERED ink family. ⛔ None of them is named."""
    ink = a.max(2) >= INK_MIN
    idx = np.flatnonzero(ink.ravel())
    px = a.reshape(-1, 3)[idx]
    keys = _chroma_key(px)
    from collections import Counter
    counts, total = Counter(keys.tolist()), len(keys)
    cells = []
    for k, n in counts.most_common():
        if n / total < MIN_SHARE:
            continue
        rep = px[keys == k]
        mx = rep.max(axis=1, keepdims=True)
        mx[mx == 0] = 1
        cells.append((k, n, (rep / mx).mean(axis=0)))
    merged = _merge_cells(cells, merge_dist)
    if not merged:
        return {}
    centres = np.array([f["centre"] for f in merged])
    mx = px.max(axis=1, keepdims=True).astype(float)
    mx[mx == 0] = 1
    # ⭐ nearest-centre assignment, ⛔ no pixel dropped for being rare
    nearest = np.abs((px / mx)[:, None, :] - centres[None, :, :]).max(axis=2).argmin(axis=1)
    out = {}
    for i in range(len(merged)):
        m = np.zeros(a.shape[:2], dtype=bool)
        m.ravel()[idx[nearest == i]] = True
        out[f"F{i}"] = m
    return out


def _ink_groups(structure: np.ndarray, others: dict[str, np.ndarray], *, axis: Axis,
                min_run_px: int, min_support: int) -> list[dict[str, Any]]:
    """Every column group of one family's ink that behaves like a drawn line.

    ⛔ This is an OBSERVATION, not a wall face: a group may be one thin line or
    a whole solid band.  Which it is, and whether two of them are one wall, is
    decided in ``hypotheses``.
    """
    m = structure if axis == "col" else structure.T
    fam_t = {k: (v if axis == "col" else v.T) for k, v in others.items()}
    keep = vertical_runs_mask(m, min_run_px)
    support = keep.sum(0)
    cols = np.flatnonzero(support >= min_support)
    groups: list[list[int]] = []
    for c in cols:
        if groups and c - groups[-1][-1] <= 1:
            groups[-1].append(int(c))
        else:
            groups.append([int(c)])

    out = []
    for g in groups:
        c0, c1 = g[0], g[-1] + 1
        along = keep[:, g].mean(1) >= FILL_RATIO
        runs, gaps = _raw_runs(along)
        if not runs:
            continue
        per_run = []
        for a, b in runs:
            strip = m[a:b, max(0, c0 - 1):c1 + 1]
            per_run.append(round(float(strip.any(axis=1).mean()), 4))
        gap_rows = []
        for lo, hi in gaps:
            gap_rows.append({
                "lo_px": lo, "hi_px": hi, "len_px": int(hi - lo),
                # ⛔ no class, and ⛔ no family called "opening": every
                # discovered family's ink across this blank is measured and
                # keyed by the family's own neutral id.
                "ink_by_family": {k: _profile(v, lo, hi, c0, c1)
                                  for k, v in fam_t.items()},
            })
        out.append({
            "pos_px": round(float(np.average(g, weights=support[g])), 2),
            "support_cols_px": [c0, c1],
            "width_px": int(c1 - c0),
            "runs_px": runs,
            "gaps": gap_rows,
            "ink_coverage_per_run": per_run,
            "covered_px": int(sum(b - a for a, b in runs)),
            "support_px": int(support[g].sum()),
        })
    return out


def _components(mask: np.ndarray, min_area_px: int) -> list[dict[str, Any]]:
    """Opening-colour connected components, emitted so any window is re-computable."""
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    if n == 0:
        return []
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        area = int((lab[sl] == i).sum())
        if area < min_area_px:
            continue
        out.append({"bbox_px": [int(sl[1].start), int(sl[0].start),
                                int(sl[1].stop), int(sl[0].stop)],
                    "area_px": area})
    out.sort(key=lambda d: -d["area_px"])
    return out


def _chain_zero_px(fit, chain: dict) -> float:
    return fit.origin_px - chain["world_start_mm"] / (chain["direction"] * fit.mm_per_px)


class AssignmentError(SystemExit):
    """⭐ A role assignment the drawing cannot support is a LOUD failure.

    F-69's whole shape was a confident zero: the only mask could not see the
    layer the windows were on, returned no windows, and nothing reported it.
    An assignment that names a family this drawing does not have must stop the
    run, never quietly produce an empty product.
    """


def build(cfg: dict) -> dict:
    # ⭐ 2026-08-24: perception now arrives as its OWN FILE, produced by whoever
    # did the recognising (today the orchestrator by hand, tomorrow the reading
    # model).  It carries the role naming AND the wall pairing -- both are "认",
    # and neither is something a ruler settles.  The config only points at it.
    percept = {}
    if cfg.get("perception"):
        percept = json.loads(Path(cfg["perception"]).read_text())
        cfg = dict(cfg)
        cfg.setdefault("family_roles", percept.get("family_roles"))
        cfg.setdefault("wall_pairs", percept.get("wall_pairs"))
        cfg["family_roles_source"] = percept.get("_produced_by", cfg["perception"])

    a = load_rgb(cfg["image"])
    pal = palette(a)
    masks = _family_masks(a)

    # ⭐ PERCEPTION COMES IN FROM OUTSIDE. Which discovered family carries the
    # walls is not something a ruler settles, so this module does not decide it
    # -- the model does (invariant #1: LLM does perception, code does geometry).
    # The config supplies it here only because there is no model in this
    # prototype's loop; the INTERFACE is the point.
    roles = dict(cfg.get("family_roles") or {})
    if not roles:
        raise AssignmentError(
            f"{cfg['image']}: no family_roles supplied. Discovered families = "
            + json.dumps({f["id"]: {"chromaticity": f["chromaticity"],
                                    "pct_of_ink": f["pct_of_ink"],
                                    "shape": f["shape"]} for f in pal["families"]},
                         ensure_ascii=False)
            + " -- name them (perception) and pass family_roles.")
    for role, fid in roles.items():
        if fid not in masks:
            raise AssignmentError(
                f"{cfg['image']}: role {role!r} was assigned to family {fid!r}, "
                f"which this drawing does not have. Discovered: {sorted(masks)}. "
                f"⛔ Refusing to return an empty product for a role nobody can see.")
    for need in ("structure", "annotation"):
        if need not in roles:
            raise AssignmentError(
                f"{cfg['image']}: no family assigned the {need!r} role. "
                f"⛔ Without it there is no ruler: the dimension chains are read "
                f"off the annotation family and every coordinate depends on them.")
    ann = masks[roles["annotation"]]

    st = masks[roles["structure"]].copy()
    r0, r1, c0, c1 = cfg["drawing_box"]
    st[:r0, :] = False
    st[r1:, :] = False
    st[:, :c0] = False
    st[:, c1:] = False

    chains = cfg["chains"]
    fits, tick_map = {}, {"x": {}, "y": {}}
    for cid, c in chains.items():
        f = fit_chain(witness_ticks(ann, axis=c["axis"], strip=tuple(c["strip"])),
                      c["values_mm"], axis=c["axis"], overall_mm=sum(c["values_mm"]))
        fits[cid] = f
        world = "x" if c["axis"] == "row" else "y"
        for px, cum in zip(f.matched_px, f.cum_mm):
            if px != px:
                continue
            tick_map[world][str(round(px, 1))] = c["world_start_mm"] + c["direction"] * cum
    fx, fy = fits[cfg["primary_x_chain"]], fits[cfg["primary_y_chain"]]
    mmpx = (fx.mm_per_px + fy.mm_per_px) / 2.0
    x_zero = _chain_zero_px(fx, chains[cfg["primary_x_chain"]])
    y_zero = _chain_zero_px(fy, chains[cfg["primary_y_chain"]])

    def to_x(px: float) -> float:
        return round((px - x_zero) * fx.mm_per_px / 1000.0, 4)

    def to_y(px: float) -> float:
        return round((y_zero - px) * fy.mm_per_px / 1000.0, 4)

    face_lines: list[dict[str, Any]] = []
    for axis in ("col", "row"):
        pos_w = to_x if axis == "col" else to_y
        along_w = to_y if axis == "col" else to_x
        for grp in _ink_groups(st, masks, axis=axis,
                               min_run_px=cfg.get("min_run_px", 14),
                               min_support=cfg.get("min_support", 10)):
            for gap in grp["gaps"]:
                lo, hi = sorted((along_w(gap["lo_px"]), along_w(gap["hi_px"])))
                gap["span_m"] = [round(lo, 4), round(hi, 4)]
                gap["len_m"] = round(hi - lo, 4)
            face_lines.append({
                "id": f"L{len(face_lines) + 1:03d}",
                "axis": axis,
                "constant_world_axis": "x" if axis == "col" else "y",
                "pos_px": grp["pos_px"], "pos_m": pos_w(grp["pos_px"]),
                "support_cols_px": grp["support_cols_px"],
                # ⭐ The group's own two edges, in world units. Pure measurement:
                # it is where the ink starts and stops across the line. For a
                # thin stroke the two edges are 1-3 px apart; for a solid filled
                # band (the sm24 dialect) they ARE the wall's two faces. ⛔ Saying
                # which of those it is would be a judgement, so it is not said
                # here -- but withholding the numbers would lose the sm24 wall
                # entirely, which is what "observations must stand alone" means.
                "edges_m": sorted((pos_w(float(grp["support_cols_px"][0])),
                                   pos_w(float(grp["support_cols_px"][1])))),
                "support_width_m": round(grp["width_px"] * mmpx / 1000.0, 4),
                "runs_px": grp["runs_px"],
                "runs_m": [[round(v, 4) for v in sorted((along_w(lo), along_w(hi)))]
                           for lo, hi in grp["runs_px"]],
                "gaps": grp["gaps"],
                "ink_coverage_per_run": grp["ink_coverage_per_run"],
                "covered_px": grp["covered_px"], "support_px": grp["support_px"],
            })

    # ------------------------------------------------------- hypotheses ----
    # ⛔ Everything below is DERIVED and carries its basis. A consumer may drop
    # this whole block and rebuild it from observations + declarations.
    declared_px = [t / mmpx for t in cfg["declared_thickness_mm"]]
    tol_px = cfg.get("thickness_tol_px", 2.0)

    def _tol(t_px: float) -> float:
        return max(tol_px, 0.30 * t_px)

    # ⭐ 2026-08-24: the guide's rule -- CODE ENUMERATES, THE MODEL CHOOSES.
    # v2's first cut filtered candidates by the DECLARED thickness, which is the
    # very mechanism that silently lost sm24's whole batch of 120 mm partitions
    # (the drawing only calls out 240).  So there is ⛔ NO spacing threshold here
    # any more: every same-axis pair of face lines that rest on disjoint ink and
    # actually overlap along the wall is a candidate, and the declared callout is
    # attached as a LABEL, never as a gate.
    candidates = []
    for i, A in enumerate(face_lines):
        for j in range(i + 1, len(face_lines)):
            B = face_lines[j]
            if A["axis"] != B["axis"]:
                continue
            # ⭐ distinct support: two readings of ONE stroke are not a wall.
            (a0, a1), (b0, b1) = A["support_cols_px"], B["support_cols_px"]
            if min(a1, b1) > max(a0, b0):
                continue
            ov = 0
            for p in A["runs_px"]:
                for q in B["runs_px"]:
                    ov += max(0, min(p[1], q[1]) - max(p[0], q[0]))
            if ov < cfg.get("min_overlap_px", 10):
                continue          # a measurement, not a semantic threshold
            d = abs(B["pos_px"] - A["pos_px"])
            hits = [t for t in declared_px if abs(d - t) <= _tol(t)]
            candidates.append({"face_a": A["id"], "face_b": B["id"],
                               "spacing_px": round(d, 2),
                               "spacing_m": round(d * mmpx / 1000.0, 4),
                               "matched_declared_mm": [round(t * mmpx) for t in hits],
                               "overlap_px": int(ov)})
    candidates.sort(key=lambda c: (c["face_a"], c["spacing_px"]))
    by_face: dict[str, list[str]] = {}
    for c in candidates:
        by_face.setdefault(c["face_a"], []).append(c["face_b"])
        by_face.setdefault(c["face_b"], []).append(c["face_a"])

    # ⭐ THE SELECTION IS PERCEPTION AND MUST COME FROM OUTSIDE (same rule as
    # ``family_roles``).  ⛔ Absent selection is a LOUD downgrade, never a quiet
    # substitution of a code rule dressed up as the model's answer.
    sel_raw = cfg.get("wall_pairs")
    if sel_raw is None:
        pairs = None
        pairs_status = "ABSENT_NO_MODEL_SELECTION"
        pairs_note = ("no wall pairing supplied. Which two face lines are one wall is "
                      "perception (2026-08-23 user ruling) -- code enumerates the "
                      "candidates below and reconciles the answer, it does not choose. "
                      f"{len(candidates)} candidates over {len(by_face)} face lines.")
    else:
        index = {(c["face_a"], c["face_b"]): c for c in candidates}
        pairs, unknown = [], []
        for a, b in sel_raw:
            c = index.get((a, b)) or index.get((b, a))
            if c is None:
                unknown.append([a, b])
            else:
                pairs.append(dict(c, source="selected"))
        # ⭐ COMPLETENESS: every face line must be accounted for -- either it is
        # half of a wall, or perception must say out loud what it is instead.
        # ⛔ Silence about a face line is the failure mode this catches: that is
        # how the five callout-TEXT strokes of sm25 1f got quietly paired into
        # walls by the declaration-driven rule.
        declared_non_wall = set(percept.get("non_wall_face_lines", {}))
        # ⭐ a third honest answer: "this IS a wall face, but the drawing's other
        # face never reached the observations".  ⛔ Without this bucket the only
        # ways to account for such a line are to call it not-a-wall (false) or to
        # pair it with something it is not (worse).
        declared_lone = set(percept.get("unpaired_wall_faces", {}))
        # a filled band whose OWN two edges are the wall's two faces (the sm24
        # dialect): one observation, one wall, ⛔ no partner to look for.
        declared_band = set(percept.get("solid_band_walls", {}))
        # ⭐ and the answer a model must be allowed to give: "I cannot tell."
        # ⛔ Forcing a call here is how a desk edge becomes a wall face.
        declared_ambig = set(percept.get("ambiguous_face_lines", {}))
        accounted = ({x for p in pairs for x in (p["face_a"], p["face_b"])}
                     | declared_non_wall | declared_lone | declared_band
                     | declared_ambig)
        unaccounted = sorted({f["id"] for f in face_lines} - accounted)
        pairs_status = "SELECTED" if not (unknown or unaccounted) else "SELECTED_INCOMPLETE"
        pairs_note = (f"{len(pairs)} pairs selected from the candidate list; "
                      f"unknown references: {unknown}; "
                      f"face lines neither paired nor declared non-wall: {unaccounted}")

    return {
        "schema": SCHEMA,
        "image": cfg["image"],
        "image_label": cfg.get("image_label"),
        "observations": {
            "calibration": {
                "x": fx.as_dict(), "y": fy.as_dict(),
                "mm_per_px": round(mmpx, 6),
                "cross_axis_relative_deviation":
                    round(abs(fx.mm_per_px - fy.mm_per_px) / mmpx, 6),
                "world_zero_px": [round(x_zero, 3), round(y_zero, 3)],
                "world_zero_source": "chain_fit",
                "profile_bins_px": list(PROFILE_BINS_PX),
                "fill_ratio": FILL_RATIO,
            },
            "ink_palette": pal,
            "face_lines": face_lines,
            # ⛔ not "openings": components of every discovered family, keyed
            # by the family's own neutral id. Naming them is the model's job.
            "components_by_family": {
                k: _components(v, cfg.get("min_area_px", 40))
                for k, v in masks.items()},
            "dimension_witnesses": tick_map,
        },
        "declarations": {
            "thickness_callouts_mm": cfg["declared_thickness_mm"],
            "thickness_callout_note": "from the drawing's own callouts (an OCR product); "
                                      "⛔ compared verbatim, never treated as a measurement",
            "world_zero_px_declared": cfg.get("world_zero_px"),
            "chains": {cid: {k: c[k] for k in ("axis", "values_mm", "world_start_mm",
                                               "direction", "ref_coord_m") if k in c}
                       for cid, c in chains.items()},
            "drawing_box_px": cfg["drawing_box"],
        },
        "hypotheses": {
            # ⭐ Perception, not measurement. Supplied from outside and recorded
            # here with the evidence a reviewer needs to disagree with it.
            "family_roles": {
                "assignment": roles,
                "source": cfg.get("family_roles_source", "supplied (model stand-in)"),
                "evidence": {fid: {"chromaticity": f["chromaticity"],
                                   "pct_of_ink": f["pct_of_ink"],
                                   "shape": f["shape"]}
                             for f in pal["families"] for fid in [f["id"]]
                             if fid in roles.values()},
                "achromatic_only": pal["achromatic_only"],
            },
            "pair_candidates": candidates,
            "pair_candidates_basis": "every same-axis face-line pair with disjoint "
                                     "support columns and >= min_overlap_px of shared "
                                     "run; ⛔ NO spacing threshold. declared callouts "
                                     "attached as a label only.",
            "pairs": pairs,
            "non_wall_face_lines": percept.get("non_wall_face_lines", {}),
            "unpaired_wall_faces": percept.get("unpaired_wall_faces", {}),
            "solid_band_walls": percept.get("solid_band_walls", {}),
            "ambiguous_face_lines": percept.get("ambiguous_face_lines", {}),
            "perception_source": percept.get("_produced_by"),
            "pairs_status": pairs_status,
            "pairs_note": pairs_note,
            "note": "⛔ derived, not scored. Candidates are rebuildable from the "
                    "observations alone; the selection is not -- it is perception.",
        },
        "ledger": {
            "face_lines": len(face_lines),
            "runs_total": sum(len(f["runs_px"]) for f in face_lines),
            "gaps_total": sum(len(f["gaps"]) for f in face_lines),
            "pair_candidates": len(candidates),
            "faces_with_a_candidate": len(by_face),
            "pairs_selected": (len(pairs) if pairs is not None else None),
            "pairs_status": pairs_status,
            "families_discovered": len(pal["families"]),
            "families_assigned": len(roles),
            "unassigned_ink_pct": pal["unassigned_pct"],
            "bridging_applied": False,
            "gap_classified": False,
            "pairing_in_observations": False,
        },
    }


def main(cfg_path: str, out_path: str) -> int:
    doc = build(json.loads(Path(cfg_path).read_text()))
    dump(doc, out_path)
    L = doc["ledger"]
    print(f"{Path(cfg_path).stem:16s} face_lines={L['face_lines']:3d} runs={L['runs_total']:4d} "
          f"gaps={L['gaps_total']:4d} cand={L['pair_candidates']:4d} "
          f"faces_with_cand={L['faces_with_a_candidate']:3d} "
          f"pairs={L['pairs_selected']} [{L['pairs_status']}] "
          f"families={L['families_discovered']}/{L['families_assigned']} "
          f"unassigned_ink={L['unassigned_ink_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
