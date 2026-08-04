"""Read-only, semantically valid GT v3 fixture with all FOUR facades declared
as elevation views (test-only). ``tests/b4b_contract_fixture.py`` only wires
North/South — batch D's L-D1 lock needs a real (non-placeholder) elevation on
every facade to prove the six-panel board actually renders content on all
four, not just the two the older fixture happens to cover."""
from __future__ import annotations

from src.agent.correction.facade_visibility import VisibilityTolerances, vg_for_direction
from src.agent.correction.footprint import footprint_fingerprint
from src.agent.judge.gt_schema import (GroundTruthV3, compute_gt_v3_content_sha256,
                                       validate_gt_v3)

_HASH = "a" * 64
_TOL = {"profile_version": 1, "dxf_node_join_tolerance_m": .001, "dxf_axis_alignment_tolerance_m": .001,
        "dxf_topology_area_tolerance_m2": .000001, "opening_boundary_max_distance_m": .4,
        "opening_assignment_tie_epsilon_m": 1e-9, "elevation_match_max_distance_m": .4,
        "elevation_match_tie_epsilon_m": 1e-9, "vg_depth_epsilon_m": 1e-9, "vg_endpoint_epsilon_m": 1e-9}
_RING = [[0., 0.], [6., 0.], [6., 5.], [0., 5.]]  # simple rectangle — every facade is a single segment
_SURFACE_KEY = {"North": "surface-N", "South": "surface-S", "East": "surface-E", "West": "surface-W"}


def _ref(view_id: str, handle: str, role: str) -> dict:
    return {"source_id": "src", "view_id": view_id, "entity_handle": handle,
            "subentity_index": None, "role": role}


def _floor(floor_id: str, z: float) -> tuple[dict, dict[str, dict]]:
    fingerprint = footprint_fingerprint(_RING)
    vg = VisibilityTolerances(1e-9, 1e-9)
    items = [item for direction in ((0, 1), (0, -1), (1, 0), (-1, 0))
             for item in vg_for_direction(_RING, direction, tolerances=vg)]
    segments = []
    by_family: dict[str, dict] = {}
    for number, item in enumerate(items):
        frame = item.frame
        family = frame.facade_family
        segment = {
            "id": f"{floor_id}:boundary:{family}:{number}", "floor_id": floor_id,
            "boundary_loop_id": "exterior", "facade_family": family,
            "p1": list(frame.p1), "p2": list(frame.p2), "outward_normal": list(frame.outward_normal),
            "world_along_interval": {"lo": frame.world_along_interval[0], "hi": frame.world_along_interval[1]},
            "depth": frame.depth,
            "visible_intervals": [{"lo": lo, "hi": hi} for lo, hi in item.visible_intervals],
            "source_footprint_fingerprint": fingerprint,
            "projection_surface_keys": [_SURFACE_KEY[family]],
            "wall_thickness_m": None,
            "source_refs": [_ref(f"plan-{floor_id}", "A", "footprint_boundary")],
        }
        segments.append(segment)
        by_family.setdefault(family, segment)
    floor = {
        "id": floor_id, "name": floor_id, "z_floor_m": z, "ceiling_height_m": 3.,
        "footprint": {"exterior": {"vertices": _RING}, "interior_rings": []},
        "footprint_fingerprint": fingerprint,
        "zones": [{"id": f"Z{floor_id}", "name": f"Zone {floor_id}", "role": "office",
                   "polygon": {"exterior": {"vertices": _RING}, "interior_rings": []},
                   "source_refs": [_ref(f"plan-{floor_id}", "A", "zone_boundary")]}],
        "boundary_segments": segments,
    }
    return floor, by_family


def make_four_facade_gt_document(*, tag_openings: dict[str, str] | None = None) -> GroundTruthV3:
    """Two floors, every facade a single straight segment, one window per
    facade on F1 (result tags supplied by the caller via ``tag_openings``
    mapping facade family -> a value only used by the caller's own test
    payload, not consumed here)."""
    f1, by_family1 = _floor("F1", 0.)
    f2, _ = _floor("F2", 3.)
    plan_ref = _ref("plan-F1", "B", "opening_plan")
    openings = []
    for family, segment in sorted(by_family1.items()):
        lo, hi = segment["world_along_interval"]["lo"], segment["world_along_interval"]["hi"]
        a, b = lo + (hi - lo) * .3, lo + (hi - lo) * .7
        elev_ref = _ref(f"elev-{family[0]}", "B", "opening_elevation")
        openings.append({
            "id": f"O-{family}", "kind": "window", "floor_id": "F1", "host_zone_id": "ZF1",
            "boundary_segment_id": segment["id"],
            "world_along_interval": {"lo": a, "hi": b},
            "z_interval": {"lo": 1., "hi": 2.},
            "source_refs": sorted([elev_ref, plan_ref],
                                  key=lambda r: (r["source_id"], r["view_id"], r["entity_handle"], r["role"])),
        })
    openings.sort(key=lambda item: item["id"])
    elevation_views = [
        {"id": f"elev-{family[0]}", "kind": "elevation", "floor_ids": ["F1", "F2"],
         "projection_surface_key": key, "facade_family": family, "view_kind": "full",
         "world_along_coverage": None, "direction_semantics": "building_axis", "azimuth_deg": None}
        for family, key in sorted(_SURFACE_KEY.items())
    ]
    plan_views = [
        {"id": f"plan-{fid}", "kind": "plan", "floor_ids": [fid], "projection_surface_key": None,
         "facade_family": None, "view_kind": None, "world_along_coverage": None,
         "direction_semantics": None, "azimuth_deg": None}
        for fid in ("F1", "F2")
    ]
    payload = {
        "schema_version": 3, "case": "batch-d-four-facade",
        "geometry_profile": "c2_simple_orthogonal_no_holes", "coordinate_frame": "building_axis_world_m",
        "verification": {"status": "candidate", "reviewer_id": None, "reviewed_on": None, "methods": []},
        "generator": {"name": "energyplus-agent.gt_from_dxf", "contract_version": 1,
                      "extractor_sha256": _HASH, "validator_sha256": _HASH, "vg_implementation_sha256": _HASH,
                      "manifest_sha256": _HASH, "judge_config_sha256": _HASH, "vg_config_sha256": _HASH,
                      "tolerances": _TOL},
        "sources": [{"id": "src", "kind": "dxf", "label": "source.dxf", "content_sha256": _HASH,
                     "native_units": "m", "metres_per_unit": 1.,
                     "views": [*elevation_views, *plan_views]}],
        "north_axis_deg": 0.0, "north_axis_source_refs": [_ref("plan-F1", "C", "north_axis")],
        "floors": [f1, f2], "openings": openings, "content_sha256": "0" * 64,
    }
    document = GroundTruthV3.model_validate(payload)
    payload["content_sha256"] = compute_gt_v3_content_sha256(document)
    document = GroundTruthV3.model_validate(payload)
    validate_gt_v3(document, tolerances=document.generator.tolerances)
    return document
