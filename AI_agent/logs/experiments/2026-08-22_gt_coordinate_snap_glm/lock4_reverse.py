#!/usr/bin/env python3
"""S1 lock 4 (reverse lock): a REAL cross-floor difference must survive the snap.

Three layers of evidence:
  A. unit level  — _transform with two affines that differ by exactly 1 mm keeps
                   the two world coordinates 1 mm apart (not absorbed), while the
                   same-mathematics pair (sm25 offsets) collapses bit-identically.
  B. extraction  — staged sm25 manifest with plan-F2 m02 shifted +2 mm (> node
                   join tolerance) fails closed with dxf_profile_floor_footprint_mismatch.
  C. extraction  — the same shift at exactly +1 mm (== tolerance, allowed by the ring
                   check) still yields DIFFERENT per-floor fingerprints: the
                   difference is preserved, never silently absorbed.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import os

os.chdir(REPO)

from src.agent.judge.gt_extraction import ExtractionInputs, ExtractionError, _transform, extract_gt_v3
from src.agent.judge.gt_manifest import PlanViewBindingV1
from src.agent.judge.gt_schema import REPO_ROOT, compute_gt_implementation_hashes
from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (TarchConversionRequestV1,
                                                    resolve_converter_tooling)

SNAP = 1e-9


class _Aff:
    def __init__(self, m00, m01, m02, m10, m11, m12):
        self.m00, self.m01, self.m02 = m00, m01, m02
        self.m10, self.m11, self.m12 = m10, m11, m12


class _View:
    def __init__(self, affine):
        self.world_from_source_m = affine


def part_a() -> bool:
    print("== A. unit level: _transform keeps a 1 mm affine difference, collapses re-association noise ==")
    v1 = _View(_Aff(0.001, 0.0, 30.469, 0.0, 0.001, -28.213600000000003))
    v2 = _View(_Aff(0.001, 0.0, -24.511800000000004, 0.0, 0.001, -28.213600000000003))
    v2_shift_1mm = _View(_Aff(0.001, 0.0, -24.511800000000004 + 0.001, 0.0, 0.001, -28.213600000000003))
    # the actual sm25 native pair for one shared corner (F1 ring vertex
    # (-25469.0, 42213.6) and the SAME corner drawn on the F2 sheet at
    # (29511.8, 42213.6); both request affines map it to world (5.0, 14.0))
    a = _transform((-25469.0, 42213.6), v1, 1.0, SNAP)
    b = _transform((29511.8, 42213.6), v2, 1.0, SNAP)
    print(f"   noise pair : {a!r} vs {b!r} -> bit-identical: {a == b}")
    c = _transform((29511.8, 42213.6), v2_shift_1mm, 1.0, SNAP)
    print(f"   1mm pair   : {a!r} vs {c!r} -> bit-identical: {a == c}; delta = ({c[0]-a[0]:.17g}, {c[1]-a[1]:.17g})")
    ok_noise = a == b
    ok_real = a != c and abs((c[0] - a[0]) - 0.001) < 1e-12 and c[1] == a[1]
    print(f"   A: noise collapsed={ok_noise}, 1mm preserved={ok_real}")
    return ok_noise and ok_real


def _staged_conversion(work: Path):
    src = work / "source.dxf"
    src.write_bytes((REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf").read_bytes())
    request = TarchConversionRequestV1.model_validate_json(
        (REPO / "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json").read_text(encoding="utf-8"))
    tooling = resolve_converter_tooling(REPO / "src/configs/judge_gt.yaml", REPO / "src/configs/correction.yaml")
    result = tn.run_tarch_conversion(src, request, tooling, work / "work")
    return result, tooling


def _shift_f2_m02(manifest, delta_m: float):
    views = []
    for view in manifest.views:
        if isinstance(view, PlanViewBindingV1) and view.id == "plan-F2":
            affine = view.world_from_source_m
            affine = affine.model_copy(update={"m02": affine.m02 + delta_m})
            view = view.model_copy(update={"world_from_source_m": affine})
        views.append(view)
    return manifest.model_copy(update={"views": views})


def part_b_and_c() -> bool:
    print("== B/C. extraction level: staged sm25 with a REAL cross-floor offset ==")
    base = Path("AI_agent/logs/experiments/2026-08-22_gt_coordinate_snap_glm/lock4")
    base.mkdir(parents=True, exist_ok=True)
    result, tooling = _staged_conversion(base)
    hashes = compute_gt_implementation_hashes(REPO_ROOT)
    inputs = ExtractionInputs(result.augmented_dxf_path, result.manifest, tooling, hashes)

    # sanity: unshifted extraction succeeds and floors are bit-identical (lock 1 in-process witness)
    doc = extract_gt_v3(inputs)
    fps = {f.id: f.footprint_fingerprint for f in doc.floors}
    print("   unshifted  : fingerprints", {k: v[:12] for k, v in fps.items()}, "-> identical:", len(set(fps.values())) == 1)

    ok = len(set(fps.values())) == 1
    for label, delta in (("B. +2mm (real, > node-join 1mm)", 0.002), ("C. +1mm (== node-join tolerance)", 0.001)):
        shifted = _shift_f2_m02(result.manifest, delta)
        try:
            doc2 = extract_gt_v3(ExtractionInputs(result.augmented_dxf_path, shifted, tooling, hashes))
        except ExtractionError as exc:
            print(f"   {label}: fail closed with ExtractionError: {exc}")
            ok = ok and ("dxf_profile_floor_footprint_mismatch" in str(exc))
            continue
        fps2 = {f.id: f.footprint_fingerprint for f in doc2.floors}
        differ = len(set(fps2.values())) != 1
        print(f"   {label}: extraction succeeded, fingerprints differ (difference NOT absorbed): {differ}")
        ok = ok and differ
    return ok


if __name__ == "__main__":
    ok = part_a() and part_b_and_c()
    print("LOCK4:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
