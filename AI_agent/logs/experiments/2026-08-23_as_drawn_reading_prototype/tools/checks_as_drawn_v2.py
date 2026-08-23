"""Self-verification for the **v2** three-layer as-drawn product — ⛔ needs no gt.

This is the v2 port of ``checks_as_drawn.py``.  The v1 file consumes the old
``wall_bands`` shape, so every reverse/forward-ledger number in the experiment
README was produced by the v1 product — exactly the mixed-evidence problem the
second cross-family review rejected the design draft for.  This file re-asks the
same three questions of the shape that actually exists now.

⛔ It still does NOT render the product to an image and compare images: a
renderer sharing the reader's wrong assumption would agree with it.  Every
element is turned into PIXEL INDICES and the ORIGINAL image is sampled there.

⭐ What changed with the three-layer shape:

* **The ink families are discovered, not written down here.**  Which discovered
  family is structure / furniture is read out of the product's own
  ``hypotheses.family_roles.assignment`` — a perception output.  Point it at the
  wrong family and these checks go red, which is the point: the naming has to be
  falsifiable, or the model could have said anything.
* **Pairing is a hypothesis now**, so it is reconciled rather than assumed: do
  the referenced face lines exist, is any face line claimed twice, are the two
  supports disjoint.  Spacing-vs-callout is a separate, declaration-level check
  because an unexplained spacing is a *finding about the drawing's callouts*
  (sm24's undeclared 120 mm walls), not proof the observation is wrong.

Known blind spots (must stay stated, or the check gets trusted for more):
  * it cannot judge SEMANTICS beyond the role assignment — a correctly placed
    but mistyped opening reads green;
  * it cannot judge "should this stroke have been split in two" — that is the
    reading grade's endpoint criterion.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from as_drawn_v2 import _family_masks  # noqa: E402
from plan_ink import load_rgb  # noqa: E402

MIN_RUN_COVERAGE = 0.80   # a stroke must sit on real ink; swept in the README
SAMPLE_HALF_PX = 1        # anti-alias margin around a face line's own columns


def _strip(face: dict) -> tuple[int, int]:
    c0, c1 = face["support_cols_px"]
    return max(0, c0 - SAMPLE_HALF_PX), c1 + SAMPLE_HALF_PX


def _sample_runs(structure: np.ndarray, *, axis: str, face: dict) -> list[dict[str, Any]]:
    lo_p, hi_p = _strip(face)
    out = []
    for a, b in face["runs_px"]:
        a, b = int(min(a, b)), int(max(a, b))
        strip = structure[a:b, lo_p:hi_p] if axis == "col" else structure[lo_p:hi_p, a:b]
        along = strip.any(axis=1 if axis == "col" else 0)
        out.append({"run_px": [a, b], "length_px": b - a,
                    "ink_coverage": round(float(along.mean()) if along.size else 0.0, 4)})
    return out


# ------------------------------------------------------------------ checks ---
def check_reverse(doc: dict, structure: np.ndarray) -> dict:
    """MULTI-DRAW: every stretch the product claims must sit on real ink."""
    rows, worst, n = [], 1.0, 0
    for f in doc["observations"]["face_lines"]:
        for s in _sample_runs(structure, axis=f["axis"], face=f):
            n += 1
            s["face"] = f["id"]
            worst = min(worst, s["ink_coverage"])
            if s["ink_coverage"] < MIN_RUN_COVERAGE:
                rows.append(s)
    return {"check": "reverse_ledger_no_phantom_ink", "threshold": MIN_RUN_COVERAGE,
            "runs_sampled": n, "worst_coverage": round(worst, 4),
            "violations": rows[:40], "violation_count": len(rows),
            "status": "red" if rows else "green"}


def check_self_consistency(doc: dict) -> dict:
    """⭐ Every metre the product states must be recomputable from its own pixels.

    Two false-greens motivated this.  (1) A neuter that rewrote ``edges_m`` to
    claim every thin stroke is a 0.24 m filled band was invisible to both other
    checks, because both recompute the edges and therefore never read the claim
    -- an unread field is a place to hide.  (2) Two face lines resting on the
    SAME ink ("one stroke read twice") is what the second review's 0.2 mm twin
    exploited; disjoint support is a property of the extractor, so state it as a
    check rather than trusting the constructor to keep being right.
    """
    mm_px = doc["observations"]["calibration"]["mm_per_px"]
    m_px = mm_px / 1000.0
    tol = m_px * 1.5          # one and a half pixels
    fl = doc["observations"]["face_lines"]
    bad_edges, bad_runs, overlaps = [], [], []
    for f in fl:
        c0, c1 = f["support_cols_px"]
        # ⚠️ Recompute along the producer's OWN affine map -- pos_m = w(pos_px) --
        # ⛔ never as "pos_m +- half the support width".  That symmetric form
        # assumes the centre of the ink is the centre of the support columns; it
        # is not (pos_px is the ink centroid) and on sm24's 9 px filled bands the
        # difference reached 1.48 px, i.e. this gate nearly false-reddened an
        # honest product on an assumption the producer never made.
        sign = 1.0 if f["constant_world_axis"] == "x" else -1.0
        want = sorted((f["pos_m"] + sign * (c0 - f["pos_px"]) * m_px,
                       f["pos_m"] + sign * (c1 - f["pos_px"]) * m_px))
        got = f.get("edges_m")
        if got and max(abs(got[0] - want[0]), abs(got[1] - want[1])) > tol:
            bad_edges.append({"face": f["id"], "stated_m": [round(v, 4) for v in got],
                              "recomputed_m": [round(v, 4) for v in want]})
        for (pa, pb), (ma, mb) in zip(f["runs_px"], f["runs_m"]):
            if abs(abs(pb - pa) * m_px - abs(mb - ma)) > tol:
                bad_runs.append({"face": f["id"], "run_px": [pa, pb],
                                 "stated_len_m": round(abs(mb - ma), 4),
                                 "recomputed_len_m": round(abs(pb - pa) * m_px, 4)})
    for i, A in enumerate(fl):
        for B in fl[i + 1:]:
            if A["axis"] != B["axis"]:
                continue
            (a0, a1), (b0, b1) = A["support_cols_px"], B["support_cols_px"]
            if min(a1, b1) > max(a0, b0):
                overlaps.append({"faces": [A["id"], B["id"]],
                                 "support_cols_px": [[a0, a1], [b0, b1]]})
    bad = len(bad_edges) + len(bad_runs) + len(overlaps)
    return {"check": "observations_recomputable_from_own_pixels",
            "tolerance_m": round(tol, 4), "stated_edges_wrong": bad_edges[:20],
            "stated_runs_wrong": bad_runs[:20],
            "face_lines_sharing_ink": overlaps[:20],
            "violation_count": bad, "status": "red" if bad else "green"}


def check_opening_role_matches_ink(doc: dict, min_share: float = 0.50) -> dict:
    """⭐ Is the family called "openings" the one whose ink sits IN the wall gaps?

    Added 2026-08-24 after a perception neuter that simply swapped the openings
    and furniture role names passed all four other gt-free gates while costing
    43 points against gt (94.6 -> 51.4).  A naming nobody can check is a naming
    the model could have invented.

    ⛔ Not a semantic rule about colour: it is where the ink physically lies.
    Windows and doors are drawn INSIDE the breaks of a wall; desks are not.
    Both quantities are already measured per gap in the observation layer, so a
    consumer can recompute this from the product alone.
    """
    roles = doc["hypotheses"]["family_roles"]["assignment"]
    tot: dict[str, int] = {}
    n = 0
    for f in doc["observations"]["face_lines"]:
        for g in f.get("gaps", []):
            n += 1
            for fid, prof in g.get("ink_by_family", {}).items():
                tot[fid] = tot.get(fid, 0) + prof.get("on_line", 0)
    grand = sum(tot.values())
    named = roles.get("fenestration")
    out = {"check": "opening_role_matches_where_the_ink_sits", "gaps_measured": n,
           "ink_in_gaps_by_family": dict(sorted(tot.items())),
           "named_opening_family": named, "min_share": min_share}
    if named is None:
        out.update({"status": "degraded", "violation_count": 0,
                    "degraded_reason": "no family carries the openings role "
                                       "(monochrome drawings land here, F-69's rule)"})
        return out
    share = tot.get(named, 0) / max(1, grand)
    top = max(tot, key=tot.get) if tot else None
    out.update({"share_of_gap_ink": round(share, 4), "family_with_most_gap_ink": top,
                "violation_count": 0 if (share >= min_share and named == top) else 1,
                "status": "green" if (share >= min_share and named == top) else "red"})
    return out


def check_pair_reconciliation(doc: dict) -> dict:
    """RECONCILIATION of the model's pairing hypothesis against the observations.

    ⛔ Not "is this pairing right" — that is the grade's job.  Only the three
    things code can settle: do the cited observations exist, is one observation
    sold twice, and do the two faces rest on disjoint ink.
    """
    faces = {f["id"]: f for f in doc["observations"]["face_lines"]}
    pairs = doc["hypotheses"].get("pairs")
    if pairs is None:
        # ⛔ No selection to reconcile. A gate with nothing to check is NOT green:
        # green here would read as "the pairing is sound" (F-69's rule).
        return {"check": "pair_hypothesis_reconciles_with_observations",
                "status": "degraded", "violation_count": 0,
                "pairs": None,
                "pair_candidates": len(doc["hypotheses"].get("pair_candidates", [])),
                "degraded_reason": doc["hypotheses"].get(
                    "pairs_note", "no wall pairing selected; nothing to reconcile")}
    dangling, reused, overlapping = [], [], []
    claimed: dict[str, list[str]] = {}
    for i, p in enumerate(pairs):
        pid = p.get("id", f"P{i}")
        a, b = p.get("face_a"), p.get("face_b")
        for ref in (a, b):
            if ref not in faces:
                dangling.append({"pair": pid, "missing_face": ref})
            else:
                claimed.setdefault(ref, []).append(pid)
        if a in faces and b in faces:
            (a0, a1), (b0, b1) = faces[a]["support_cols_px"], faces[b]["support_cols_px"]
            if min(a1, b1) > max(a0, b0):
                overlapping.append({"pair": pid, "faces": [a, b],
                                    "support_cols_px": [[a0, a1], [b0, b1]]})
    for ref, ps in sorted(claimed.items()):
        if len(ps) > 1:
            reused.append({"face": ref, "claimed_by": ps})
    # ⭐ COMPLETENESS: a face line perception says nothing about is not "fine",
    # it is unaccounted for.  Silence is how the five callout-text strokes got
    # quietly paired into walls before anybody looked.
    non_wall = set(doc["hypotheses"].get("non_wall_face_lines", {}))
    lone = set(doc["hypotheses"].get("unpaired_wall_faces", {}))
    band = set(doc["hypotheses"].get("solid_band_walls", {}))
    ambiguous = set(doc["hypotheses"].get("ambiguous_face_lines", {}))
    accounted = ({x for p in pairs for x in (p.get("face_a"), p.get("face_b"))}
                 | non_wall | lone | band | ambiguous)
    unaccounted = sorted(set(faces) - accounted)
    # ⚠️ A reference the producer could not resolve is dropped before it reaches
    # this list, so the dropped-on-the-floor case is only visible in the status
    # the producer itself recorded.  Reading only the surviving rows made this
    # gate green on a perception that cited a face line that does not exist.
    status = doc["hypotheses"].get("pairs_status")
    bad = (len(dangling) + len(reused) + len(overlapping) + len(unaccounted)
           + (0 if status in (None, "SELECTED") else 1))
    if not bad and ambiguous:
        # ⛔ NOT green: perception declined on some lines, and a reader must see
        # that rather than infer "everything checked out".
        return {"check": "pair_hypothesis_reconciles_with_observations",
                "status": "degraded", "violation_count": 0, "pairs": len(pairs),
                "declared_ambiguous": sorted(ambiguous),
                "degraded_reason": f"perception declined on {len(ambiguous)} of "
                                   f"{len(faces)} face lines; the rest reconcile"}
    return {"check": "pair_hypothesis_reconciles_with_observations",
            "pairs": len(pairs), "status_from_product": doc["hypotheses"].get("pairs_status"),
            "face_lines_unaccounted_for": unaccounted,
            "declared_non_wall": sorted(non_wall),
            "declared_unpaired_wall_face": sorted(lone),
            "declared_solid_band_wall": sorted(band),
            "declared_ambiguous": sorted(ambiguous),
            "dangling_reference": dangling,
            "face_claimed_twice": reused, "supports_overlap": overlapping,
            "violation_count": bad, "status": "red" if bad else "green"}


def check_spacing_declared(doc: dict) -> dict:
    """DECLARATION cross-check: is each paired spacing explicable by a callout?

    ⛔ Does NOT snap — snapping is a conversion and belongs to 1_correction.  An
    inexplicable spacing is NAMED here instead of travelling downstream disguised
    as a thickness (F-78).  ⚠️ A red here can mean the drawing's callouts are
    incomplete (sm24's undeclared 120 mm walls), not that the measurement is wrong.
    """
    declared = [t / 1000.0 for t in doc["declarations"].get("thickness_callouts_mm", [])]
    if doc["hypotheses"].get("pairs") is None:
        return {"check": "pair_spacing_explicable_by_callouts", "status": "degraded",
                "violation_count": 0, "declared_mm":
                    doc["declarations"].get("thickness_callouts_mm", []),
                "degraded_reason": "no wall pairing selected; spacing has no owner yet"}
    rows = []
    for i, p in enumerate(doc["hypotheses"].get("pairs") or []):
        s = p.get("spacing_m")
        if s is None:
            continue
        if not declared:
            rows.append({"pair": p.get("id", f"P{i}"), "spacing_m": s,
                         "nearest_declared_m": None})
            continue
        nearest = min(declared, key=lambda t: abs(s - t))
        gap = abs(s - nearest)
        tol = max(0.30 * nearest, 0.02)
        if gap > tol:
            rows.append({"pair": p.get("id", f"P{i}"), "spacing_m": round(s, 4),
                         "nearest_declared_m": nearest, "excess_m": round(gap, 4),
                         "tolerance_m": round(tol, 4)})
    return {"check": "pair_spacing_explicable_by_callouts",
            "declared_mm": doc["declarations"].get("thickness_callouts_mm", []),
            "violations": rows, "violation_count": len(rows),
            "status": "red" if rows else "green"}


def check_forward(doc: dict, masks: dict, roles: dict, box: list[int],
                  min_component_px: int, max_unclaimed_pct: float = 8.0) -> dict:
    """MISSED-DRAW: structural ink the product never claimed."""
    from scipy import ndimage

    r0, r1, c0, c1 = box
    st = masks[roles["structure"]].copy()
    st[:r0, :] = False
    st[r1:, :] = False
    st[:, :c0] = False
    st[:, c1:] = False

    claimed = np.zeros_like(st)
    for f in doc["observations"]["face_lines"]:
        lo_p, hi_p = _strip(f)
        for a, b in f["runs_px"]:
            a, b = int(min(a, b)), int(max(a, b))
            if f["axis"] == "col":
                claimed[a:b, lo_p:hi_p] = True
            else:
                claimed[lo_p:hi_p, a:b] = True
    residue = st & ~claimed
    lab, n = ndimage.label(residue)
    sizes = ndimage.sum(residue, lab, range(1, n + 1))
    blobs = []
    for i, s in enumerate(sizes):
        if s < min_component_px:
            continue
        ys, xs = np.where(lab == i + 1)
        blobs.append({"px": int(s), "bbox_px": [int(xs.min()), int(ys.min()),
                                                int(xs.max()), int(ys.max())]})
    blobs.sort(key=lambda d: -d["px"])

    ink = sum(m.sum() for m in masks.values())
    fur_fid = roles.get("furniture")
    fur_pct = 100.0 * masks[fur_fid].sum() / max(1, ink) if fur_fid in masks else 0.0
    out = {"check": "forward_ledger_structural_ink_claimed",
           "structure_family": roles["structure"],
           "structure_px_in_box": int(st.sum()), "unclaimed_px": int(residue.sum()),
           "unclaimed_pct": round(100.0 * residue.sum() / max(1, st.sum()), 2),
           "component_floor_px": min_component_px,
           "large_unclaimed_components": blobs[:20],
           "furniture_family": fur_fid,
           "furniture_layer_pct_of_ink": round(fur_pct, 2)}
    # DIALECT GATING (same rule as the monochrome polarity downgrade, F-69):
    # the residue only measures wall coverage when furniture has its own layer.
    if fur_fid in masks and fur_pct >= 1.0:
        out["status"] = "green" if out["unclaimed_pct"] <= max_unclaimed_pct else "red"
        out["threshold_pct"] = max_unclaimed_pct
    else:
        out["status"] = "degraded"
        out["degraded_reason"] = (
            "no separate furniture ink family in this drawing's role assignment: the "
            "structural family carries furniture too, so unclaimed structural ink is "
            "NOT a wall-coverage measure here")
    return out


# ----------------------------------------------------------------- neuters ---
def _mutate(doc: dict, cfg: dict, kind: str) -> str:
    fl = doc["observations"]["face_lines"]
    if kind == "merge_runs":
        # the pre-2026-08-23 shape: every face line collapsed to [min, max]
        for f in fl:
            rs = f["runs_px"]
            f["runs_px"] = [[min(r[0] for r in rs), max(r[1] for r in rs)]]
        return "MUTATED: face-line runs collapsed to [min,max]"
    if kind == "extend_runs_full":
        # ⭐ The cheat the gt-side check cannot see: claim every face line is
        # drawn edge to edge, so every gt target is fully covered for free.
        r0, r1, c0, c1 = doc["declarations"]["drawing_box_px"]
        for f in fl:
            f["runs_px"] = [[r0, r1] if f["axis"] == "col" else [c0, c1]]
        return "MUTATED: every face line extended across the whole drawing box"
    if kind == "fabricate_pair_from_midline":
        # ⭐ "collapse to midline, then regenerate two faces at ±t/2" — the shape
        # a legacy centreline representation produces when asked for faces.
        mm_px = doc["observations"]["calibration"]["mm_per_px"]
        t_mm = max(doc["declarations"].get("thickness_callouts_mm") or [240])
        half = (t_mm / mm_px) / 2.0
        by_id = {f["id"]: f for f in fl}
        src = doc["hypotheses"].get("pairs")
        if src is None:      # no selection yet: use the callout-matching candidates
            src = [c for c in doc["hypotheses"].get("pair_candidates", [])
                   if c.get("matched_declared_mm")]
        keep, n = [], 0
        drop = set()
        for p in src:
            a, b = by_id.get(p.get("face_a")), by_id.get(p.get("face_b"))
            if not a or not b:
                continue
            mid = (a["pos_px"] + b["pos_px"]) / 2.0
            for sign, src in ((-1, a), (+1, b)):
                c = json.loads(json.dumps(a))          # both faces cloned from ONE
                c["id"] = src["id"]
                c["pos_px"] = mid + sign * half
                c["support_cols_px"] = [int(round(mid + sign * half)),
                                        int(round(mid + sign * half)) + 1]
                keep.append(c)
                n += 1
            drop |= {a["id"], b["id"]}
        doc["observations"]["face_lines"] = [f for f in fl if f["id"] not in drop] + keep
        return (f"MUTATED: {n} faces regenerated at +-{t_mm/2:.0f} mm around each pair's "
                "midline, both cloned from face_a's runs")
    if kind == "duplicate_face":
        # the twin 0.2 mm away, carried over from the gt-side neuter set so one
        # fixture can be scored by both checks
        twins = []
        for f in fl:
            t = json.loads(json.dumps(f))
            t["id"] = f["id"] + "_TWIN"
            t["pos_px"] = f["pos_px"] + 0.01
            twins.append(t)
        doc["observations"]["face_lines"] = fl + twins
        return f"MUTATED: {len(twins)} twin face lines added on the same ink"
    if kind == "widen_all":
        # claims every stroke is a 240 mm filled band, by rewriting edges_m only
        mm_px = doc["observations"]["calibration"]["mm_per_px"]
        for f in fl:
            f["edges_m"] = [f["pos_m"] - 0.12, f["pos_m"] + 0.12]
            f["support_width_m"] = 0.24
        return f"MUTATED: every face line claims a 0.24 m band in edges_m (mm/px={mm_px:.3f})"
    if kind == "swap_structure_role":
        a = doc["hypotheses"]["family_roles"]["assignment"]
        other = next((v for k, v in a.items() if k != "structure"), None)
        a["structure"] = other
        return f"MUTATED: structure role re-pointed to family {other}"
    raise SystemExit(f"unknown mutation {kind!r}")


def main(doc_path: str, cfg_path: str, out_path: str, *, mutate: str | None = None) -> int:
    doc = json.loads(Path(doc_path).read_text())
    cfg = json.loads(Path(cfg_path).read_text())
    note = _mutate(doc, cfg, mutate) if mutate else None

    a = load_rgb(cfg["image"])
    masks = _family_masks(a)
    roles = doc["hypotheses"]["family_roles"]["assignment"]
    for need in ("structure",):
        if roles.get(need) not in masks:
            raise SystemExit(f"role {need!r} points at family {roles.get(need)!r}, "
                             f"which this drawing does not have: {sorted(masks)}")
    box = doc["declarations"]["drawing_box_px"]
    st = masks[roles["structure"]].copy()
    r0, r1, c0, c1 = box
    st[:r0, :] = False
    st[r1:, :] = False
    st[:, :c0] = False
    st[:, c1:] = False

    report = {"source": doc_path, "image": cfg["image"], "schema": "as_drawn_plan_v2",
              "mutation": note, "role_assignment": roles,
              "checks": [check_reverse(doc, st),
                         check_self_consistency(doc),
                         check_opening_role_matches_ink(doc),
                         check_pair_reconciliation(doc),
                         check_spacing_declared(doc),
                         check_forward(doc, masks, roles, box,
                                       cfg.get("component_floor_px", 400),
                                       cfg.get("max_unclaimed_pct", 8.0))]}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    for c in report["checks"]:
        extra = f" worst={c['worst_coverage']}" if "worst_coverage" in c else ""
        extra += f" unclaimed={c['unclaimed_pct']}%" if "unclaimed_pct" in c else ""
        extra += " [degraded]" if c["status"] == "degraded" else ""
        print(f"  {c['status']:>8}  {c['check']:<48} violations={c['violation_count'] if 'violation_count' in c else 0}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3],
                          mutate=(sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None)))
