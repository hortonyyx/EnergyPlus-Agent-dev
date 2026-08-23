"""Third-cross-review mutations for the v2 as-drawn prototype.

These fixtures deliberately live in ``logs/experiments``.  They do not change
production code or gt.  The main probe removes a real 1.2 m stretch from the
two observed faces of sm25 1F's wall at x ~= 11.06 m.  Its cheating variant
then claims, in the *actual v2 gap schema*, that opening-family ink fills the
new gap.  This exercises the fields consumed by ``reconstruct_check_v2.py``;
the older ``punch_middle_one_pixel`` mutation writes an unused
``opening_ink`` field instead.

Usage:
    python3 tools/crossreview_mutate_v2.py INPUT OUTPUT missing_wall_middle
    python3 tools/crossreview_mutate_v2.py INPUT OUTPUT fake_opening_over_missing_wall
    python3 tools/crossreview_mutate_v2.py INPUT OUTPUT one_pixel_actual_schema
    python3 tools/crossreview_mutate_v2.py INPUT OUTPUT all_ambiguous
    python3 tools/crossreview_mutate_v2.py INPUT OUTPUT all_non_wall
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


TARGET_FACES = {"L012", "L013"}
CUT_SPAN_M = (11.4, 12.6)


def _cut_run(face: dict, run_px: list[int], run_m: list[float],
             cut_lo: float, cut_hi: float) -> list[tuple[list[int], list[float]]]:
    """Remove a world-coordinate interval while keeping px/m runs aligned."""
    pa, pb = map(int, run_px)
    ma, mb = sorted(map(float, run_m))
    if mb <= cut_lo or ma >= cut_hi:
        return [([pa, pb], [ma, mb])]

    # as_drawn_v2 maps row-axis along coordinates through +x and col-axis
    # along coordinates through -y.
    if face["axis"] == "col":
        wa, wb = mb, ma
    else:
        wa, wb = ma, mb

    def px_at(w: float) -> float:
        return pa + (w - wa) * (pb - pa) / (wb - wa)

    cut_a = max(ma, cut_lo)
    cut_b = min(mb, cut_hi)
    p0, p1 = sorted((int(round(px_at(cut_a))), int(round(px_at(cut_b)))))
    p0, p1 = max(pa, p0), min(pb, p1)

    def world_at(p: int) -> float:
        return wa + (p - pa) * (wb - wa) / (pb - pa)

    out = []
    for a, b in ((pa, p0), (p1, pb)):
        if b <= a:
            continue
        x, y = sorted((world_at(a), world_at(b)))
        out.append(([a, b], [round(x, 4), round(y, 4)]))
    return out


def _remove_middle(doc: dict, *, forge_opening: bool) -> dict:
    fen = doc["hypotheses"]["family_roles"]["assignment"]["fenestration"]
    changed = []
    for face in doc["observations"]["face_lines"]:
        if face["id"] not in TARGET_FACES:
            continue
        pieces = []
        for rp, rm in zip(face["runs_px"], face["runs_m"]):
            pieces.extend(_cut_run(face, rp, rm, *CUT_SPAN_M))
        face["runs_px"] = [p for p, _ in pieces]
        face["runs_m"] = [m for _, m in pieces]
        face["covered_px"] = sum(b - a for a, b in face["runs_px"])
        face["ink_coverage_per_run"] = [1.0] * len(face["runs_px"])
        if forge_opening:
            # This is the schema the scorer actually reads.  The claimed cyan
            # ink is absent from the source pixels, but none of the six gt-free
            # gates recomputes gap profiles or component membership.
            mm_px = doc["observations"]["calibration"]["mm_per_px"]
            length_px = int(round((CUT_SPAN_M[1] - CUT_SPAN_M[0]) * 1000 / mm_px))
            prof = {
                "on_line": length_px,
                "by_distance_px": {str(x): 0 for x in (2, 5, 10, 15, 25)},
                "span_ratio": 1.0,
                "nearest_px": 0,
            }
            face.setdefault("gaps", []).append({
                "lo_px": None,
                "hi_px": None,
                "len_px": length_px,
                "span_m": list(CUT_SPAN_M),
                "len_m": round(CUT_SPAN_M[1] - CUT_SPAN_M[0], 4),
                "ink_by_family": {fen: prof},
                "crossreview_forged": True,
            })
        changed.append(face["id"])
    if changed != sorted(TARGET_FACES):
        raise SystemExit(f"expected {sorted(TARGET_FACES)}, changed {changed}")
    doc["crossreview_mutation"] = {
        "kind": ("fake_opening_over_missing_wall" if forge_opening
                 else "missing_wall_middle"),
        "faces": sorted(TARGET_FACES),
        "missing_span_m": list(CUT_SPAN_M),
        "forged_gap_profile": forge_opening,
    }
    return doc


def _all_ambiguous(doc: dict) -> dict:
    ids = [f["id"] for f in doc["observations"]["face_lines"]]
    h = doc["hypotheses"]
    h["pairs"] = []
    h["non_wall_face_lines"] = {}
    h["unpaired_wall_faces"] = {}
    h["solid_band_walls"] = {}
    h["ambiguous_face_lines"] = {x: "cannot tell" for x in ids}
    h["pairs_status"] = "SELECTED"
    h["pairs_note"] = "cross-review fixture: perception declined on every face line"
    doc["crossreview_mutation"] = {"kind": "all_ambiguous", "faces": len(ids)}
    return doc


def _all_non_wall(doc: dict) -> dict:
    """Stronger completeness loophole: reasons are payloads the gate ignores."""
    ids = [f["id"] for f in doc["observations"]["face_lines"]]
    h = doc["hypotheses"]
    h["pairs"] = []
    h["non_wall_face_lines"] = {x: "not a wall" for x in ids}
    h["unpaired_wall_faces"] = {}
    h["solid_band_walls"] = {}
    h["ambiguous_face_lines"] = {}
    h["pairs_status"] = "SELECTED"
    h["pairs_note"] = "cross-review fixture: perception calls every face non-wall"
    doc["crossreview_mutation"] = {"kind": "all_non_wall", "faces": len(ids)}
    return doc


def _one_pixel_actual_schema(doc: dict) -> dict:
    """Port the existing one-pixel probe to the fields the scorer consumes."""
    fen = doc["hypotheses"]["family_roles"]["assignment"]["fenestration"]
    mm_px = doc["observations"]["calibration"]["mm_per_px"]
    punched = 0
    for face in doc["observations"]["face_lines"]:
        out = []
        for a, b in face["runs_m"]:
            lo, hi = sorted((a, b))
            if hi - lo > 0.5:
                out.extend([[lo, lo + 0.4 * (hi - lo)],
                            [hi - 0.4 * (hi - lo), hi]])
                punched += 1
            else:
                out.append([lo, hi])
        face["runs_m"] = out
        gaps = []
        for a, b in zip(out, out[1:]):
            lo, hi = max(a), min(b)
            if hi <= lo:
                continue
            length_px = max(1, int(round((hi - lo) * 1000 / mm_px)))
            gaps.append({
                "span_m": [lo, hi],
                "len_px": length_px,
                "ink_by_family": {fen: {
                    "on_line": 1,
                    "by_distance_px": {},
                    "span_ratio": round(1.0 / length_px, 6),
                    "nearest_px": 0,
                }},
            })
        face["gaps"] = gaps
    doc["crossreview_mutation"] = {
        "kind": "one_pixel_actual_schema",
        "punched_runs": punched,
        "note": "runs_px intentionally untouched: this probe only checks the gt-side mutation claim",
    }
    return doc


def main(src: str, dst: str, kind: str) -> int:
    doc = json.loads(Path(src).read_text())
    if kind == "missing_wall_middle":
        doc = _remove_middle(doc, forge_opening=False)
    elif kind == "fake_opening_over_missing_wall":
        doc = _remove_middle(doc, forge_opening=True)
    elif kind == "one_pixel_actual_schema":
        doc = _one_pixel_actual_schema(doc)
    elif kind == "all_ambiguous":
        doc = _all_ambiguous(doc)
    elif kind == "all_non_wall":
        doc = _all_non_wall(doc)
    else:
        raise SystemExit(f"unknown mutation {kind!r}")
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(doc["crossreview_mutation"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
