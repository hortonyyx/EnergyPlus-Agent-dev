"""Self-verification for the as-drawn layer — three checks, none of which needs gt.

This is the machine form of the user's "render the reading back onto the drawing"
idea (2026-08-22).  ⛔ It deliberately does NOT render the product to an image and
compare images: a renderer that shares the reader's wrong assumption would agree
with it and hide the error.  Instead every product element is turned into a set
of PIXEL INDICES and the ORIGINAL image is sampled there.

Known blind spots (must stay stated, or the check will be trusted for more than
it does):
  * it cannot judge SEMANTICS — doors and windows sit on the same colour layer,
    so a correctly placed but mistyped opening reads green here;
  * it cannot judge "should this have been split" — a single stroke drawn along
    real ink is green even when the answer needs it cut in two.  That is what the
    grade's endpoint criterion is for.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from plan_ink import ink_families, load_rgb  # noqa: E402

# A drawn line must actually sit on ink. 0.80 leaves room for the dashes of a
# hidden line and for a perpendicular wall interrupting the sample band; below
# that the stroke is claiming ink the drawing does not have.
MIN_RUN_COVERAGE = 0.80
# Half-width of the sample strip around a face line, in px. 1 px each side
# absorbs anti-aliasing without letting the strip reach the neighbouring face
# of the same wall (the thinnest declared wall is 120 mm ~= 5.5 px).
SAMPLE_HALF_PX = 1


def _strip(face: dict) -> tuple[int, int]:
    """Pixel span to sample for one face line.

    Sample the face's OWN column group, widened by the anti-alias margin -- not
    a fixed window around its centre. A two-face-line dialect group is 1-3 px so
    the two agree; a solid filled band (sm24) is ~9 px, and sampling only its
    centre made the ledger report 15% coverage on ink that is actually solid.
    """
    c0, c1 = face.get("cols_px", [int(round(face["pos_px"])), int(round(face["pos_px"])) + 1])
    return max(0, c0 - SAMPLE_HALF_PX), c1 + SAMPLE_HALF_PX


def _sample_runs(structure: np.ndarray, *, axis: str, face: dict,
                 runs_px: list[list[int]]) -> list[dict[str, Any]]:
    """Grey-ink coverage under each run of one face line."""
    lo_p, hi_p = _strip(face)
    out = []
    for a, b in runs_px:
        if axis == "col":                       # vertical line: constant column
            strip = structure[a:b, lo_p:hi_p]
        else:                                   # horizontal line: constant row
            strip = structure[lo_p:hi_p, a:b]
        along = strip.any(axis=1 if axis == "col" else 0)
        cov = float(along.mean()) if along.size else 0.0
        out.append({"run_px": [a, b], "length_px": b - a, "ink_coverage": round(cov, 4)})
    return out


def check_reverse(doc: dict, structure: np.ndarray) -> dict:
    """MULTI-DRAW: every stroke the product claims must sit on real ink."""
    rows, worst = [], 1.0
    for band in doc["wall_bands"]:
        for face in band["faces"]:
            for s in _sample_runs(structure, axis=band["axis"], face=face,
                                  runs_px=face["runs_px"]):
                s.update({"band": band["id"], "face": face["role"]})
                worst = min(worst, s["ink_coverage"])
                if s["ink_coverage"] < MIN_RUN_COVERAGE:
                    rows.append(s)
    return {"check": "reverse_ledger_no_phantom_ink", "threshold": MIN_RUN_COVERAGE,
            "worst_coverage": round(worst, 4), "violations": rows,
            "status": "red" if rows else "green"}


def check_pairing(doc: dict) -> dict:
    """PAIRING: a band's measured spacing must match a declared thickness.

    ⛔ This does NOT snap the spacing -- snapping is a conversion and belongs to
    1_correction. It only asserts the observation is explicable by the drawing's
    own callouts, so an inexplicable band (F-78's 0.131 / 0.146 m) is named here
    instead of travelling downstream disguised as a thickness.
    """
    rows = []
    for band in doc["wall_bands"]:
        declared = [t / 1000.0 for t in band["declared_thickness_candidates_mm"]]
        gap = min(abs(band["spacing_m"] - t) for t in declared)
        nearest = min(declared, key=lambda t: abs(band["spacing_m"] - t))
        tol = max(0.30 * nearest, 0.02)
        if gap > tol:
            rows.append({"band": band["id"], "spacing_m": band["spacing_m"],
                         "nearest_declared_m": nearest, "excess_m": round(gap, 4),
                         "tolerance_m": round(tol, 4)})
    return {"check": "band_spacing_explicable_by_callouts", "violations": rows,
            "status": "red" if rows else "green"}


def check_forward(doc: dict, fams: dict, box: list[int], min_component_px: int,
                  max_unclaimed_pct: float = 8.0) -> dict:
    """MISSED-DRAW: structural ink the product never claimed.

    Counts grey pixels inside the drawing box that no face-line sample strip
    covers, grouped into connected components so a real missed wall shows up as
    one large blob rather than a haze of stragglers.
    """
    from scipy import ndimage

    r0, r1, c0, c1 = box
    st = fams["structure"].copy()
    st[:r0, :] = False
    st[r1:, :] = False
    st[:, :c0] = False
    st[:, c1:] = False

    claimed = np.zeros_like(st)
    for band in doc["wall_bands"]:
        for face in band["faces"]:
            lo_p, hi_p = _strip(face)
            for a, b in face["runs_px"]:
                if band["axis"] == "col":
                    claimed[a:b, lo_p:hi_p] = True
                else:
                    claimed[lo_p:hi_p, a:b] = True
    residue = st & ~claimed
    lab, n = ndimage.label(residue)
    sizes = ndimage.sum(residue, lab, range(1, n + 1))
    big = [int(i + 1) for i, s in enumerate(sizes) if s >= min_component_px]
    blobs = []
    for i in big:
        ys, xs = np.where(lab == i)
        blobs.append({"px": int(sizes[i - 1]),
                      "bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]})
    blobs.sort(key=lambda d: -d["px"])
    # DIALECT GATING. The residue is only interpretable when the drawing keeps
    # furniture on its own colour layer. sm25 does (furniture = 19.7% of ink,
    # structure = 31.5%) and its residue is ~4.7%; sm24 does NOT (furniture
    # layer measures 0.00%, structure 59.1%) so its residue is dominated by
    # desks and sofas -- 41.9%, with the largest blobs 87x46 / 123x77 / 155x167.
    # Reporting that as a wall-coverage figure would be a confident wrong answer,
    # so the check DEGRADES EXPLICITLY instead (same rule as the monochrome
    # polarity downgrade, F-69).
    fam = fams
    furniture_pct = 100.0 * fam["furniture"].sum() / max(1, fam["ink"].sum())
    separable = furniture_pct >= 1.0
    out = {"check": "forward_ledger_structural_ink_claimed",
           "structure_px_in_box": int(st.sum()),
           "unclaimed_px": int(residue.sum()),
           "unclaimed_pct": round(100.0 * residue.sum() / max(1, st.sum()), 2),
           "component_floor_px": min_component_px,
           "large_unclaimed_components": blobs[:20],
           "furniture_layer_pct_of_ink": round(furniture_pct, 2)}
    if separable:
        out["status"] = "green" if out["unclaimed_pct"] <= max_unclaimed_pct else "red"
        out["threshold_pct"] = max_unclaimed_pct
    else:
        out["status"] = "degraded"
        out["degraded_reason"] = ("no separate furniture ink layer: structural colour carries "
                                  "furniture too, so unclaimed structural ink is NOT a "
                                  "wall-coverage measure on this drawing")
    return out


def main(doc_path: str, cfg_path: str, out_path: str, *, mutate: str | None = None) -> int:
    doc = json.loads(Path(doc_path).read_text())
    cfg = json.loads(Path(cfg_path).read_text())
    a = load_rgb(cfg["image"])
    fams = ink_families(a)

    note = None
    if mutate == "merge_runs":
        # NEUTER: reintroduce the exact defect this layer was built to remove --
        # collapse every face line's runs back to [min, max]. If the reverse
        # ledger cannot see this, it has no discriminating power and must not be
        # adopted (the "must have gone red on a real fixture" admission rule).
        for band in doc["wall_bands"]:
            for face in band["faces"]:
                rs = face["runs_px"]
                face["runs_px"] = [[min(r[0] for r in rs), max(r[1] for r in rs)]]
        note = "MUTATED: face-line runs collapsed to [min,max] (the pre-2026-08-23 shape)"

    st = fams["structure"].copy()
    r0, r1, c0, c1 = cfg["drawing_box"]
    st[:r0, :] = False
    st[r1:, :] = False
    st[:, :c0] = False
    st[:, c1:] = False

    report = {
        "source": doc_path, "image": cfg["image"], "mutation": note,
        "checks": [check_reverse(doc, st), check_pairing(doc),
                   check_forward(doc, fams, cfg["drawing_box"], cfg.get("component_floor_px", 400),
                                 cfg.get("max_unclaimed_pct", 8.0))],
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    for c in report["checks"]:
        n = len(c.get("violations", []))
        extra = f" worst={c['worst_coverage']}" if "worst_coverage" in c else ""
        extra += f" unclaimed={c['unclaimed_pct']}%" if "unclaimed_pct" in c else ""
        extra += f" [{c['degraded_reason'][:40]}...]" if "degraded_reason" in c else ""
        print(f"  {c['status']:>5}  {c['check']:<44} violations={n}{extra}")
    return 0


if __name__ == "__main__":
    mut = sys.argv[4] if len(sys.argv) > 4 else None
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3], mutate=mut))
