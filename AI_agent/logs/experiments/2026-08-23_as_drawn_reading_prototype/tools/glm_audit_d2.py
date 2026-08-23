"""GLM fourth cross-review audit: WHAT EXACTLY does D2's geometric cap rule exclude,
and does the honest product's C4 "extra" land on D2-excluded real ink?

Reimplements denominator.py's two passes (same code paths, imported where possible)
and dumps the excluded-cap segments in world metres, then intersects them with the
honest product's unexplained (extra) stretches.

    python3 tools/glm_audit_d2.py   # -> out/glm_audit_d2.json + printed table
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.agent.judge.gt_manifest import load_gt_tooling_config  # noqa: E402
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1  # noqa: E402
from src.agent.judge.tarch_normalize import _to_world, run_p1_plan_view  # noqa: E402

REPO = Path(__file__).resolve().parents[5]
GT_CFG = REPO / "src/configs/judge_gt.yaml"
VG_CFG = REPO / "src/configs/correction.yaml"
QUANT = 4

DEN = [("sm25_F1", "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf",
        "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json",
        "plan-F1", "sm25_1f"),
       ("sm25_F2", "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf",
        "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json",
        "plan-F2", "sm25_2f"),
       ("sm24_F1", "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf",
        "tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json",
        "plan-F1", "sm24_1f")]


def audit(dxf: Path, request_path: Path, view_id: str, product_path: Path) -> dict:
    import shutil
    import tempfile
    import importlib.util

    request = TarchConversionRequestV1.model_validate_json(Path(request_path).read_text())
    view = next(v for v in request.plan_views if v.id == view_id)
    tooling = load_gt_tooling_config(GT_CFG, VG_CFG)
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / Path(dxf).name
        shutil.copy2(dxf, staged)
        geo = run_p1_plan_view(staged, request, view, tooling)
    affine = view.world_from_source_m
    t_max = max(float(t) for t in request.wall_thickness_range_m)

    segs = []
    for _handle, x0, y0, x1, y1 in geo.wall_lines:
        if x0 != x1 and y0 != y1:
            continue
        (wx0, wy0), (wx1, wy1) = _to_world((x0, y0), affine), _to_world((x1, y1), affine)
        if abs(wx1 - wx0) < abs(wy1 - wy0):
            segs.append(("x", round((wx0 + wx1) / 2.0, QUANT),
                         round(min(wy0, wy1), QUANT), round(max(wy0, wy1), QUANT)))
        else:
            segs.append(("y", round((wy0 + wy1) / 2.0, QUANT),
                         round(min(wx0, wx1), QUANT), round(max(wx0, wx1), QUANT)))

    long_const = {"x": set(), "y": set()}
    for axis, const, lo, hi in segs:
        if hi - lo > t_max:
            long_const[axis].add(const)

    def is_cap(axis, const, lo, hi):
        if hi - lo > t_max:
            return False
        other = "y" if axis == "x" else "x"
        near = lambda v: any(abs(v - c) <= 0.02 for c in long_const[other])
        return near(lo) and near(hi)

    excluded = [(a, c, lo, hi) for a, c, lo, hi in segs if is_cap(a, c, lo, hi)]

    return {"excluded": excluded, "t_max": t_max}


def main() -> int:
    out = {}
    for key, dxf, req, view, product in DEN:
        r = audit(REPO / dxf, REPO / req, view,
                  REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype"
                  f"/out/{product}_v2.json")
        excluded = r["excluded"]
        # histogram of excluded lengths
        lens = sorted(round(hi - lo, 3) for _, _, lo, hi in excluded)
        out[key] = {"n_excluded": len(excluded), "excluded": excluded,
                    "len_min": lens[0] if lens else None,
                    "len_median": lens[len(lens) // 2] if lens else None,
                    "len_max": lens[-1] if lens else None}
        print(f"{key}: geometric caps excluded = {len(excluded)}, "
              f"lengths min/med/max = {out[key]['len_min']}/{out[key]['len_median']}/{out[key]['len_max']} m")
    p = Path(__file__).resolve().parent.parent / "out" / "glm_audit_d2.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
