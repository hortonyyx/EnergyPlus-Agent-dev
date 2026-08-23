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
  D4 MERGE       within a group, fragments whose gap is <= MERGE_M are one run.
                 ⛔ The merge distance is a DECLARED domain parameter, reported in
                 the ledger and swept, ⛔ not silently chosen: a gap wider than
                 this is a real break (a doorway) and must survive as two runs.
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
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from src.agent.judge.gt_manifest import load_gt_tooling_config  # noqa: E402
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1  # noqa: E402

REPO = Path(__file__).resolve().parents[5]
GT_CFG = REPO / "src/configs/judge_gt.yaml"
VG_CFG = REPO / "src/configs/correction.yaml"
from src.agent.judge.tarch_normalize import _to_world, run_p1_plan_view  # noqa: E402

MERGE_M = 0.60          # declared; swept in the README
QUANT = 4               # rounding of world coordinates when grouping (0.1 mm)


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
    n_diag = 0
    for _handle, x0, y0, x1, y1 in geo.wall_lines:
        if x0 != x1 and y0 != y1:
            n_diag += 1                                  # D1: out of profile
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
    n_cap, n_face, n_cap_by_converter = 0, 0, 0
    for axis, const, lo, hi, cap_key in segs:
        n_cap_by_converter += cap_key in caps
        if _is_cap(axis, const, lo, hi):                 # D2 (geometric)
            n_cap += 1
            continue
        n_face += 1
        groups.setdefault((axis, const), []).append((lo, hi))

    targets, frag_hist = [], []
    for (axis, const), spans in sorted(groups.items()):
        frag_hist.append(len(spans))
        for lo, hi in _merge(spans, merge_m):            # D4
            targets.append({"axis": axis, "const_m": const,
                            "lo_m": round(lo, 4), "hi_m": round(hi, 4),
                            "length_m": round(hi - lo, 4)})
    frag_hist.sort()
    return {
        "rule_version": "denominator_v1",
        "view_id": view_id, "floor_id": view.floor_id,
        "params": {"merge_m": merge_m, "coordinate_round_decimals": QUANT},
        "ledger": {
            "wall_layer_segments_collected": len(geo.wall_lines),
            "excluded_jamb_caps_geometric": n_cap,
            "would_be_excluded_by_converter_length_rule": n_cap_by_converter,
            "excluded_non_orthogonal": n_diag,
            "face_segments": n_face,
            "face_lines_after_grouping": len(groups),
            "scoreable_targets_after_merge": len(targets),
            "fragments_per_face_line": {
                "min": frag_hist[0] if frag_hist else 0,
                "median": frag_hist[len(frag_hist) // 2] if frag_hist else 0,
                "max": frag_hist[-1] if frag_hist else 0},
            "total_scoreable_length_m": round(sum(t["length_m"] for t in targets), 3),
        },
        "targets": targets,
    }


def main(dxf: str, request: str, view_id: str, out: str,
         merge_m: float = MERGE_M) -> int:
    d = denominator(Path(dxf), Path(request), view_id, merge_m=merge_m)
    Path(out).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"view": view_id, **d["ledger"], "merge_m": merge_m}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
                          float(sys.argv[5]) if len(sys.argv) > 5 else MERGE_M))
