"""S9 promotion (§6.1 方案A): run the P2 conversion in STAGING, then explicitly copy the
landed artefacts (augmented normalized.dxf + manifest + conversion_report + source_map +
human-review overlay) into the protected answer root gt_sources/sm24_anchor/.

The converter never runs inside the protected root (assert_staging_input refuses it);
promotion is an explicit ``cp`` of staging output.  Only a PASS result is promoted.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (
    PlanViewIntentV1, TarchConversionRequestV1, TarchDialectRulesV1,
    TarchEntitySelectorV1, ZoneIntentEntryV1, ZoneIntentSpecV1,
    compute_request_sha256, resolve_converter_tooling)

REPO = Path(__file__).resolve().parents[5]
GT_CONFIG = REPO / "src/configs/judge_gt.yaml"
VG_CONFIG = REPO / "src/configs/correction.yaml"
SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf"
DEST_ROOT = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor"
WINDOW_BLOCK = "$TCHSYS$WIN2D"


def main() -> None:
    work = Path(__file__).resolve().parent / "s9_staging"
    work.mkdir(parents=True, exist_ok=True)
    staged_source = work / "sm24_source.dxf"
    shutil.copyfile(SOURCE, staged_source)
    sha = hashlib.sha256(staged_source.read_bytes()).hexdigest()

    aff = {"m00": 0.001, "m01": 0.0, "m02": -23.0576, "m10": 0.0, "m11": 0.001, "m12": -26.5652}
    clip = {"xmin": 12276.94, "ymin": 18802.14, "xmax": 41994.33, "ymax": 51678.57}
    pv = PlanViewIntentV1(
        id="plan-F1", floor_id="F1", frame_title="1f平面图", clip_box_dxf=clip, world_from_source_m=aff,
        wall_selector=TarchEntitySelectorV1(entity_types=["LINE"], layers=["WALL"]),
        opening_selector=TarchEntitySelectorV1(entity_types=["INSERT"], layers=["WINDOW"]),
        dialect_rules=TarchDialectRulesV1(window_block_names=[WINDOW_BLOCK],
                                          door_block_prefixes=["$DorLib2D$"], classifier_version="tarch-dialect-v1"),
        zone_intent=ZoneIntentSpecV1(
            mode="intent_file", expected_count=8,
            entries=[ZoneIntentEntryV1(zone_id=f"z{i}", name=f"r{i}", role="unspecified") for i in range(8)]))
    req = TarchConversionRequestV1(
        request_version=1, case="sm24_anchor", source_dxf_label="sm24_source.dxf", source_dxf_sha256=sha,
        normalized_source_id="sm24-anchor-normalized",
        target_geometry_profile="c2_simple_orthogonal_no_holes", native_units="unitless",
        metres_per_unit=0.001, floors=[{"id": "F1", "name": "1F", "z_floor_m": 0.0, "ceiling_height_m": 4.5}],
        plan_views=[pv], request_sha256="0" * 64)
    req = req.model_copy(update={"request_sha256": compute_request_sha256(req)})

    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(staged_source, req, pv, tooling, work)
    assert res.conversion_report.status == "PASS", "refusing to promote a BLOCKED result"
    assert all(g.passed for g in res.gates), "refusing to promote a non-all-green result"

    # serialize the in-memory artefacts in staging
    (work / "manifest.json").write_text(res.manifest.model_dump_json(indent=2), encoding="utf-8")
    (work / "conversion_report.json").write_text(res.conversion_report.model_dump_json(indent=2), encoding="utf-8")
    (work / "source_map.json").write_text(res.source_map.model_dump_json(indent=2), encoding="utf-8")

    # explicit copy into the protected answer root
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    for name in ("normalized.dxf", "manifest.json", "conversion_report.json",
                 "source_map.json", "overlay_plan.svg"):
        shutil.copyfile(work / name, DEST_ROOT / name)

    gmap = {g.id: g for g in res.gates}
    print("PROMOTED to", DEST_ROOT)
    print("  zones:", len(res.zones), " G7 symdiff:", gmap["G7"].evidence["symmetric_diff_m2"],
          " overlap:", gmap["G7"].evidence["pairwise_overlap_m2"],
          " G8 symdiff:", gmap["G8"].evidence["symmetric_diff_m2"])
    print("  manifest entries:", len(res.manifest.views),
          " source_map entries:", len(res.source_map.entries))


if __name__ == "__main__":
    main()
