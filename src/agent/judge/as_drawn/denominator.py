"""⭐ The SCOREABLE DENOMINATOR for an as-drawn reading — a machine rule, not prose.

The third cross-family review (2026-08-24) made this the first gate on writing an
as-drawn layer into gt:

    "哪些 primitive / run 是 reading 必须画出来的，没给机器规则 ⇒ 任何写进 gt 的
     schema 都是先固化偶然实现、后补语义。"

So this file answers exactly one question, mechanically:

    Given the answer's own source drawing, WHICH line segments must a reading
    have drawn, and which ones is it merely allowed to draw?

⭐ It derives that from the CONVERTER'S OWN collection pass (``run_p1_plan_view``),
⛔ never from a second re-implementation of "what a wall line is".  That is the
lesson of the same day: a check whose recomputation does not mirror the
producer's definition measures the difference between two opinions.

## The rule (v1) — five clauses, each with its own ledger line

  D1 SOURCE      every LINE the converter collected on the wall layers of this
                 plan view, after its own quantization and clipping.
  D2 EXCLUDE     JAMB CAPS -- the short cross-section stroke at an opening or a
                 wall end.  They are AUDITED, never scored: thickness evidence,
                 not a face.
                 ⚠️⚠️ 2026-08-24: the first version deferred to the converter's
                 own cap set, on the principle "mirror the producer, do not
                 re-derive".  MEASURED, that was wrong here: the converter calls
                 a segment a cap when its LENGTH falls in the wall-thickness
                 range [0.06, 0.50] m, and sm25's corridor wall has REAL face
                 fragments of 0.36 m between adjacent doors -- 7 doors in a row,
                 so the pieces between them are shorter than the thickest wall.
                 Those real wall faces were being deleted from the answer, and
                 the reading was then charged 21 m of "多画" for drawing ink that
                 is genuinely there.  ⇒ D2 now identifies a cap GEOMETRICALLY: a
                 stroke is a cap only if it SPANS BETWEEN two face lines of the
                 opposite direction (its two endpoints sit on two such lines) and
                 is no longer than the thickest declared wall.  ⭐ "Mirror the
                 producer" applies to a quantity the producer OWNS; it does not
                 oblige me to inherit a heuristic the producer only needed for a
                 different purpose (thickness evidence, where a false positive is
                 harmless).
  D3 GROUP       remaining segments are grouped by (axis, constant coordinate)
                 after quantization: that is one drawn face line.
  D4 MERGE       within a group, fragments whose gap is <= MERGE_M are one run,
                 ⛔ NEVER across a gap that the answer itself calls an opening.
                 ⚠️⚠️ 2026-08-24, fourth cross-family review (GLM): the first
                 version merged on distance alone, and at MERGE_M = 0.60 it
                 merged straight across the answer's own 0.6 m window on the
                 north wall ([10.3, 10.9] at y = 19.76/20.0) -- the denominator
                 was deleting a real opening from the answer.  My own sweep had
                 said "0.40-0.80 is a clean plateau"; that sweep was run BEFORE
                 D2 changed and I never re-ran it.  With the opening guard the
                 distance again stops mattering (swept below).
  D5 TARGETS     each surviving run is one scoreable target, keyed by
                 (axis, const, lo, hi) in world metres.

## What is NOT scored, and why it is written down

  * jamb caps            -> D2, audited
  * anything not on a wall layer (text, furniture, dimensions, openings)
    -> never enters D1.  ⚠️ ASYMMETRY WORTH STATING: in the DXF these are
       separated by LAYER, which is free; in the raster the reader has to
       RECOGNISE them (sm25's "240" callout text is drawn in the wall colour).
       So the denominator is clean while the reading task is not -- that is a
       property of the answer source, not a claim that the task is easy.
  * a face line's two ends beyond the last fragment -> not extrapolated.

## ⛔ An EMPTY denominator is never a denominator (2026-08-29, F-126)

MEASURED: fed ``sm25-L_t3_as_received.dxf`` against the signed ``request.json``,
this function used to RETURN NORMALLY with ``targets: []``, ``opening_targets:
[]`` and ``wall_layer_segments_collected: 0`` -- because ``run_p1_plan_view``
fails closed on its source-hash gate (``tarch_input_source_hash_mismatch``,
severity BLOCK) and hands back an empty ``P1PlanViewGeometry``.  The BLOCK
diagnostic was then dropped on the floor: the returned dict had no field that
could carry it.

⇒ A zero denominator is indistinguishable, IN THE ARTIFACT, from "the product
is perfect" and from "there was nothing to score here" -- the downstream reads
"the ruler never measured" as "the measured thing is bad"
([[absence-conflates-causes-in-observables]], same root as F-64).  So:

  * ``diagnostics`` is now a top-level key, always, on every return path.
  * an empty ``targets`` RAISES ``DenominatorUnavailable`` instead of returning,
    and the two ways of being empty carry DIFFERENT reasons -- an upstream BLOCK
    (codes named in the message) versus geometry that ran clean and still found
    nothing.  ⛔ They are not collapsed into one exit.

⚠️ SCOPE, stated so it is not mistaken for an oversight: a BLOCK diagnostic
alongside a NON-empty denominator still returns.  MEASURED, that combination is
real -- re-signed, ``sm25-L_t3_as_received.dxf`` at ``plan-F1`` yields 223 wall
lines together with ``tarch_wall_nonorthogonal`` / ``tarch_wall_free_end`` --
and deciding whether such a denominator is scoreable is a policy question this
file does not own.  What F-126 fixes is the SILENCE: those codes now ride out in
``diagnostics`` where a caller can see them.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.agent.judge.gt_manifest import load_gt_tooling_config  # noqa: E402
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
GT_CFG = REPO / "src/configs/judge_gt.yaml"
VG_CFG = REPO / "src/configs/correction.yaml"
from src.agent.judge.tarch_normalize import _to_world, run_p1_plan_view  # noqa: E402

MERGE_M = 0.60          # declared; swept in the README
QUANT = 4               # rounding of stored world coordinates (0.1 mm)
# ⚠️ 2026-08-24: the GROUPING key used QUANT too, so one face line whose
# fragments quantised to 9.9399 and 9.9400 became TWO groups 0.1 mm apart -- and
# the grade's "one observation may not answer two different faces" rule then
# refused the second of them.  Group at 1 mm: finer than any tolerance in play,
# coarser than the answer's own rounding noise.
GROUP_QUANT = 3


#: reason codes for :class:`DenominatorUnavailable` -- ⛔ two DISTINCT exits, so
#: "the upstream refused to produce geometry" can never be read as "the geometry
#: is fine and this view genuinely has nothing to score".
REASON_UPSTREAM_BLOCK = "upstream_block_diagnostics"
REASON_ZERO_TARGETS = "geometry_ran_but_zero_targets"


class DenominatorUnavailable(RuntimeError):
    """⭐ F-126: raised instead of handing back a denominator with no targets.

    A caller cannot mistake this for a usable denominator -- there is no dict to
    keep using.  Everything the empty run knew is carried on the exception:
    ``reason`` (one of the two constants above), ``blocking_codes`` (the BLOCK
    diagnostic codes, named in ``str(exc)`` as well), the full ``diagnostics``
    records, and the ``ledger`` counters of the run that came up empty.
    """

    def __init__(self, reason: str, *, view_id: str, floor_id: str,
                 diagnostics: list[dict], ledger: dict) -> None:
        self.reason = reason
        self.view_id = view_id
        self.floor_id = floor_id
        self.diagnostics = diagnostics
        self.ledger = ledger
        self.blocking_codes = sorted({d["code"] for d in diagnostics
                                      if d["severity"] == "BLOCK"})
        if reason == REASON_UPSTREAM_BLOCK:
            why = ("the upstream converter refused to produce geometry; "
                   f"BLOCK diagnostics: {', '.join(self.blocking_codes)}")
        else:
            why = ("the upstream converter produced geometry with NO block "
                   "diagnostics, and the D1-D5 rule still yielded zero "
                   "scoreable targets")
        super().__init__(
            f"denominator_unavailable[{reason}] view={view_id} floor={floor_id}: {why} "
            f"(wall_layer_segments_collected="
            f"{ledger.get('wall_layer_segments_collected')}, "
            f"face_segments={ledger.get('face_segments')})")


def _diagnostic_records(geo) -> list[dict]:
    """⭐ R1: carry the converter's diagnostics OUT, ⛔ not to a log line.

    ``severity``/``stage`` are ``str`` enums and ``code`` is a plain ``Literal``
    string; normalise all three to bare strings so the result stays json-safe
    for ``main()``.
    """
    out = []
    for d in geo.diagnostics:
        out.append({
            "code": str(getattr(d.code, "value", d.code)),
            "severity": str(getattr(d.severity, "value", d.severity)),
            "stage": str(getattr(d.stage, "value", d.stage)),
            "action_code": d.action_code,
            "context": d.context,
        })
    return out


def _merge(spans: list[tuple[float, float]], gap_m: float) -> list[list[float]]:
    out: list[list[float]] = []
    for lo, hi in sorted(spans):
        if out and lo - out[-1][1] <= gap_m:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def denominator(dxf: Path, request_path: Path, view_id: str, *,
                merge_m: float = MERGE_M) -> dict:
    request = TarchConversionRequestV1.model_validate_json(Path(request_path).read_text())
    view = next(v for v in request.plan_views if v.id == view_id)
    tooling = load_gt_tooling_config(GT_CFG, VG_CFG)
    with tempfile.TemporaryDirectory() as tmp:          # staging: the answer source is protected
        staged = Path(tmp) / dxf.name
        shutil.copy2(dxf, staged)
        geo = run_p1_plan_view(staged, request, view, tooling)

    # ⭐ Use the request's OWN source->world affine (``plan_view.world_from_source_m``),
    # ⛔ never "multiply by metres_per_unit and hope": the world frame's origin is the
    # whole building's SW inner corner (invariant #2), not the DXF origin, and on a
    # multi-floor request each plan view sits somewhere else in DXF space entirely.
    affine = view.world_from_source_m
    caps = {(round(c, 6), round(lo, 6), round(hi, 6), "v")
            for c, spans in geo.jamb_caps_v.items() for lo, hi in spans}
    caps |= {(round(c, 6), round(lo, 6), round(hi, 6), "h")
             for c, spans in geo.jamb_caps_h.items() for lo, hi in spans}

    t_max = max(float(t) for t in request.wall_thickness_range_m)

    # pass 1 -- every orthogonal segment in WORLD coordinates
    segs = []
    # ⭐ 2026-08-29 (F-126, R3): D1 drops non-orthogonal strokes, and the ledger
    # used to record only HOW MANY.  A bare count cannot be pointed at: "1
    # segment was discarded" does not say WHICH 1 m of wall left the answer.  So
    # the discarded strokes are now itemised, in both frames.
    # ⛔ OUT-ACCOUNTING ONLY -- the discard rule itself is untouched here; changing
    # it is F-129 (an as-yet-unbuilt capability), deliberately not in this change.
    # ⚠️ field names say which frame they are in: ``*_dxf`` is native DXF units,
    # ``*_m`` is world metres ([[cross-representation-mutation-must-be-equivalent]]:
    # a field called ``pos_m`` that holds pixels is how the last one went wrong).
    excluded_non_orthogonal: list[dict] = []
    for _handle, x0, y0, x1, y1 in geo.wall_lines:
        if x0 != x1 and y0 != y1:
            (nx0, ny0) = _to_world((x0, y0), affine)     # D1: out of profile
            (nx1, ny1) = _to_world((x1, y1), affine)
            excluded_non_orthogonal.append({
                "handle": _handle,
                "p0_dxf": [round(x0, 6), round(y0, 6)],
                "p1_dxf": [round(x1, 6), round(y1, 6)],
                "p0_m": [round(nx0, QUANT), round(ny0, QUANT)],
                "p1_m": [round(nx1, QUANT), round(ny1, QUANT)],
                "length_m": round(((nx1 - nx0) ** 2 + (ny1 - ny0) ** 2) ** 0.5, QUANT),
            })
            continue
        (wx0, wy0), (wx1, wy1) = _to_world((x0, y0), affine), _to_world((x1, y1), affine)
        if abs(wx1 - wx0) < abs(wy1 - wy0):
            segs.append(("x", round((wx0 + wx1) / 2.0, QUANT),
                         round(min(wy0, wy1), QUANT), round(max(wy0, wy1), QUANT),
                         (round(x0, 6), round(min(y0, y1), 6), round(max(y0, y1), 6), "v")))
        else:
            segs.append(("y", round((wy0 + wy1) / 2.0, QUANT),
                         round(min(wx0, wx1), QUANT), round(max(wx0, wx1), QUANT),
                         (round(y0, 6), round(min(x0, x1), 6), round(max(x0, x1), 6), "h")))

    # pass 2 -- which consts carry a LONG stroke?  Only those can host a cap's end.
    long_const = {"x": set(), "y": set()}
    for axis, const, lo, hi, _ in segs:
        if hi - lo > t_max:
            long_const[axis].add(const)

    def _is_cap(axis, const, lo, hi):
        """D2: a cap spans BETWEEN two face lines of the opposite direction."""
        if hi - lo > t_max:
            return False
        other = "y" if axis == "x" else "x"
        near = lambda v: any(abs(v - c) <= 0.02 for c in long_const[other])
        return near(lo) and near(hi)

    groups: dict[tuple[str, float], list[tuple[float, float]]] = {}
    allowed: list[dict] = []          # ⭐ D2': drawn, allowed, not required
    n_cap, n_face, n_cap_by_converter = 0, 0, 0
    for axis, const, lo, hi, cap_key in segs:
        n_cap_by_converter += cap_key in caps
        if _is_cap(axis, const, lo, hi):                 # D2 (geometric)
            n_cap += 1
            # ⚠️ 2026-08-24, fourth cross-family review (GLM): excluding caps from
            # the targets while still counting a reading's ink on them as 多画 is
            # ASYMMETRIC -- drawing the real stroke is punished and not drawing it
            # is free.  Measured: the honest sm25 1F product's 0.36 m of "extra"
            # lands exactly on D2-excluded segments.  So caps now leave the
            # denominator as an ALLOWED set: not scored for, not scored against.
            allowed.append({"axis": axis, "const_m": const,
                            "lo_m": round(lo, QUANT), "hi_m": round(hi, QUANT)})
            continue
        n_face += 1
        groups.setdefault((axis, round(const, GROUP_QUANT)), []).append((lo, hi))

    # openings first: D4 needs them
    opening_spans: dict[str, list[tuple[float, float, float, float]]] = {"x": [], "y": []}
    for o in geo.openings:
        r = o.rect_dxf_mm
        (ax0, ay0), (ax1, ay1) = _to_world((r[0], r[1]), affine), _to_world((r[2], r[3]), affine)
        x0, x1 = sorted((ax0, ax1))
        y0, y1 = sorted((ay0, ay1))
        if (x1 - x0) >= (y1 - y0):
            opening_spans["y"].append((y0, y1, x0, x1))
        else:
            opening_spans["x"].append((x0, x1, y0, y1))

    def _crosses_opening(axis, const, a, b):
        """Is the blank between two fragments an opening the answer knows about?"""
        for c0, c1, lo, hi in opening_spans[axis]:
            if c0 - 0.05 <= const <= c1 + 0.05 and min(b, hi) - max(a, lo) > -0.05:
                return True
        return False

    # ⭐⭐ 2026-08-25 (user: "橙色标注，不扣分").  Second guard, SAME SHAPE as the
    # opening one.  Measured: at a T-junction the answer's own DXF is already in
    # two fragments -- x = 8.88 carries [9.644, 9.940] and [10.060, 10.364] with
    # the perpendicular wall's two faces sitting at exactly y = 9.94 / 10.06 --
    # and MERGE_M welded them into one 0.72 m target that then demanded ink no
    # drawing has (measured: zero ink of EVERY family across the blank).  Over
    # the whole view the distance merge invented 3.36 m that is not in the DXF
    # (278.92 -> 282.28 m).  ⛔ So this is not "excusing" a miss: the denominator
    # was requiring something the answer itself does not contain.
    #
    # ⛔ CONTAINMENT, not intersection: the blank must fit BETWEEN the two faces
    # of ONE perpendicular wall.  A mere "some wall lands inside this blank" test
    # would excuse a genuinely missed 3.64 m run (measured on 2F while this was
    # still only a picture annotation).
    LANDING_TOL_M = 0.05     # same slack the opening guard uses
    LANDING_MAX_WALL_M = 0.50  # widest thing that can still BE a wall (240/120 declared)

    perp_reach: dict[str, dict[float, list[tuple[float, float]]]] = {"x": {}, "y": {}}
    for (gax, gconst), gspans in groups.items():
        perp_reach["y" if gax == "x" else "x"].setdefault(gconst, []).extend(gspans)

    def _crosses_a_wall_landing(axis, const, a, b):
        """Is the blank exactly where ONE perpendicular wall lands on this face?"""
        reaching = sorted(c for c, sp in perp_reach[axis].items()
                          if any(lo - LANDING_TOL_M <= const <= hi + LANDING_TOL_M
                                 for lo, hi in sp))
        for i, c1 in enumerate(reaching):
            for c2 in reaching[i + 1:]:
                if c2 - c1 > LANDING_MAX_WALL_M:
                    break
                if c1 - LANDING_TOL_M <= a and b <= c2 + LANDING_TOL_M:
                    return True
        return False

    targets, frag_hist, guarded, n_holes, hole_m = [], [], 0, 0, 0.0
    for (axis, const), spans in sorted(groups.items()):
        frag_hist.append(len(spans))
        merged: list[list] = []                      # [lo, hi, holes]
        for lo, hi in sorted(spans):
            if (merged and lo - merged[-1][1] <= merge_m
                    and not _crosses_opening(axis, const, merged[-1][1], lo)):
                blank = (merged[-1][1], lo)
                # ⭐ It is still ONE wall (so it stays ONE target, and its ENDS
                # remain where a cut really is expected -- C3), but the answer
                # itself has no ink across this blank, so it is not REQUIRED.
                if blank[1] - blank[0] > 1e-9 and _crosses_a_wall_landing(axis, const, *blank):
                    merged[-1][2].append([round(blank[0], 4), round(blank[1], 4)])
                    n_holes += 1
                    hole_m += blank[1] - blank[0]
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                if merged and lo - merged[-1][1] <= merge_m:
                    guarded += 1
                merged.append([lo, hi, []])
        for lo, hi, holes in merged:
            span_m = hi - lo
            req = span_m - sum(b - a for a, b in holes)
            targets.append({"axis": axis, "const_m": const,
                            "lo_m": round(lo, 4), "hi_m": round(hi, 4),
                            "length_m": round(span_m, 4),
                            # ⭐ blanks the answer itself does not fill: ink here is
                            # neither required (C2) nor punished (C4).
                            "holes": holes,
                            "required_length_m": round(req, 4)})
    frag_hist.sort()

    # ⭐ OPENING TARGETS (2026-08-24, F-87): the answer's own resolved openings,
    # in world metres, carrying the ONE thing the reconstruction never scored --
    # door vs window.  Measured first: swapping every door and window in the
    # reading changed the reconstruction by 0.0 points, because that check only
    # ever asks "is this stretch an opening", never "which kind".
    opening_targets = []
    for o in geo.openings:
        r = o.rect_dxf_mm
        (ax0, ay0), (ax1, ay1) = _to_world((r[0], r[1]), affine), _to_world((r[2], r[3]), affine)
        x0, x1 = sorted((round(ax0, QUANT), round(ax1, QUANT)))
        y0, y1 = sorted((round(ay0, QUANT), round(ay1, QUANT)))
        # the opening lies ALONG the wall it sits in: its long side is the width
        if (x1 - x0) >= (y1 - y0):
            axis, const_lo, const_hi, lo, hi = "y", y0, y1, x0, x1
        else:
            axis, const_lo, const_hi, lo, hi = "x", x0, x1, y0, y1
        opening_targets.append({"kind": o.kind, "axis": axis,
                                "const_range_m": [const_lo, const_hi],
                                "lo_m": lo, "hi_m": hi,
                                "width_m": round(hi - lo, 4)})
    diagnostics = _diagnostic_records(geo)              # ⭐ R1: always, every path
    result = {
        "rule_version": "denominator_v1",
        "view_id": view_id, "floor_id": view.floor_id,
        "params": {"merge_m": merge_m, "coordinate_round_decimals": QUANT},
        "ledger": {
            "wall_layer_segments_collected": len(geo.wall_lines),
            "excluded_jamb_caps_geometric": n_cap,
            "would_be_excluded_by_converter_length_rule": n_cap_by_converter,
            # ⭐ the count and its itemisation are built from ONE list, so they
            # cannot drift apart (R3's lock asserts the two agree AND are > 0).
            "excluded_non_orthogonal": len(excluded_non_orthogonal),
            "face_segments": n_face,
            "face_lines_after_grouping": len(groups),
            "scoreable_targets_after_merge": len(targets),
            "fragments_per_face_line": {
                "min": frag_hist[0] if frag_hist else 0,
                "median": frag_hist[len(frag_hist) // 2] if frag_hist else 0,
                "max": frag_hist[-1] if frag_hist else 0},
            "total_scoreable_length_m": round(sum(t["length_m"] for t in targets), 3),
            "merges_blocked_by_an_opening": guarded,
            "wall_landing_holes": n_holes,
            "wall_landing_hole_length_m": round(hole_m, 4),
        },
        "targets": targets,
        "allowed_not_required": allowed,
        # ⭐ R3: the count in the ledger, the items here -- same shape as
        # ``allowed_not_required`` already uses.
        "excluded_non_orthogonal_segments": excluded_non_orthogonal,
        "opening_targets": opening_targets,
        "opening_ledger": {"total": len(opening_targets),
                           "by_kind": {k: sum(1 for o in opening_targets if o["kind"] == k)
                                       for k in sorted({o["kind"] for o in opening_targets})}},
        # ⭐ R1: the converter's own diagnostics ride out with the denominator.
        # ⛔ NOT a log line -- a log line is not in the artifact, and the artifact
        # is what the downstream reads.
        "diagnostics": diagnostics,
    }
    # ⭐⭐ R2: the loud failure.  Built the ledger first ON PURPOSE, so the
    # exception can carry everything the empty run did know.
    if not targets:
        raise DenominatorUnavailable(
            REASON_UPSTREAM_BLOCK if any(d["severity"] == "BLOCK" for d in diagnostics)
            else REASON_ZERO_TARGETS,
            view_id=view_id, floor_id=view.floor_id,
            diagnostics=diagnostics, ledger=result["ledger"])
    return result


def main(dxf: str, request: str, view_id: str, out: str,
         merge_m: float = MERGE_M) -> int:
    d = denominator(Path(dxf), Path(request), view_id, merge_m=merge_m)
    Path(out).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"view": view_id, **d["ledger"], "openings": d["opening_ledger"],
                      "merge_m": merge_m}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
                          float(sys.argv[5]) if len(sys.argv) > 5 else MERGE_M))
