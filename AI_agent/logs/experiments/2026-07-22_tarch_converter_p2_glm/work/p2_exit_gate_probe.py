"""P2 exit-gate probe: INDEPENDENTLY derive the sm24 退出门 numbers by running
run_p2_conversion (never copied from the P1 probes as an expectation).

Prints: cavity count, zone count, G6/G7/G8 evidence (symdiff + overlap +
reconstruction symdiff), gate pass/fail, S9 artefact paths, near-threshold
faces.  Persisted so the delivery note + tests cite real run output.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (
    PlanViewIntentV1, TarchConversionRequestV1, TarchDialectRulesV1,
    TarchEntitySelectorV1, ZoneIntentEntryV1, ZoneIntentSpecV1,
    compute_request_sha256, resolve_converter_tooling)

# probe lives 6 levels deep (work/<date>_<case>_gt/experiments/logs/AI_agent/<repo>)
REPO = Path(__file__).resolve().parents[5]
GT_CONFIG = REPO / "src/configs/judge_gt.yaml"
VG_CONFIG = REPO / "src/configs/correction.yaml"
SM24 = Path(__file__).resolve().parent / "sm24_source.dxf"

WINDOW_BLOCK = "$TCHSYS$WIN2D"


def main():
    sha = hashlib.sha256(SM24.read_bytes()).hexdigest()
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
    work = Path(__file__).resolve().parent
    res = tn.run_p2_conversion(SM24, req, pv, tooling, work)

    gmap = {g.id: g for g in res.gates}
    out = {
        "cavity_count": len(res.cavities),
        "expected_count": 8,
        "claimed_zones": len(res.zones),
        "G6": gmap["G6"].model_dump(),
        "G7_symdiff_m2": gmap["G7"].evidence.get("symmetric_diff_m2"),
        "G7_overlap_m2": gmap["G7"].evidence.get("pairwise_overlap_m2"),
        "G7_passed": gmap["G7"].passed,
        "G8_symdiff_m2": gmap["G8"].evidence.get("symmetric_diff_m2"),
        "G8_passed": gmap["G8"].passed,
        "G4": gmap["G4"].model_dump(),
        "G9": gmap["G9"].model_dump(),
        "G10": gmap["G10"].model_dump(),
        "all_gates_passed": all(g.passed for g in res.gates),
        "has_block": res.has_block,
        "diagnostic_codes_set": sorted({d.code for d in res.diagnostics}),
        "near_threshold_faces": res.near_threshold_faces,
        "zone_areas_m2": [round(z.area_m2, 6) for z in res.zones],
        "augmented_dxf": str(res.augmented_dxf_path) if res.augmented_dxf_path else None,
        "overlay_path": str(res.overlay_path) if res.overlay_path else None,
        "manifest_present": res.manifest is not None,
        "source_map_present": res.source_map is not None,
        "conversion_report_status": res.conversion_report.status if res.conversion_report else None,
    }
    print(json.dumps(out, indent=2, default=str))
    (Path(__file__).resolve().parent / "p2_exit_gate_output.json").write_text(
        json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
