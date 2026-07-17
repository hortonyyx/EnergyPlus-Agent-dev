"""Read-only, semantically valid B4a→B4b typed-GT fixture (test-only)."""
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
_RING = [[0., 0.], [4., 0.], [4., 3.], [3., 3.], [3., 1.], [1., 1.], [1., 3.], [0., 3.]]


def _ref(view_id: str, handle: str, role: str) -> dict:
    return {"source_id":"src", "view_id":view_id, "entity_handle":handle, "subentity_index":None, "role":role}


def _floor(floor_id: str, z: float) -> tuple[dict, list[dict]]:
    fingerprint = footprint_fingerprint(_RING)
    vg = VisibilityTolerances(1e-9, 1e-9)
    items = [item for direction in ((0,1),(0,-1),(1,0),(-1,0)) for item in vg_for_direction(_RING, direction, tolerances=vg)]
    segments, north, east = [], None, None
    for number, item in enumerate(items):
        frame = item.frame; family = frame.facade_family
        keys = ["surface-N", "surface-N-detail"] if family == "North" else (["surface-S"] if family == "South" else [])
        segment = {"id":f"{floor_id}:boundary:{family}:{number}","floor_id":floor_id,"boundary_loop_id":"exterior","facade_family":family,
          "p1":list(frame.p1),"p2":list(frame.p2),"outward_normal":list(frame.outward_normal),
          "world_along_interval":{"lo":frame.world_along_interval[0],"hi":frame.world_along_interval[1]},"depth":frame.depth,
          "visible_intervals":[{"lo":lo,"hi":hi} for lo,hi in item.visible_intervals],"source_footprint_fingerprint":fingerprint,
          "projection_surface_keys":keys,"wall_thickness_m":None,"source_refs":[_ref(f"plan-{floor_id}","A","footprint_boundary")]}
        segments.append(segment)
        if family == "North" and item.visible_intervals and north is None: north = segment
        if family == "East" and east is None: east = segment
    rank={"North":0,"South":1,"East":2,"West":3}
    segments.sort(key=lambda item:(rank[item["facade_family"]],item["world_along_interval"]["lo"],item["world_along_interval"]["hi"],item["depth"],item["id"]))
    floor={"id":floor_id,"name":floor_id,"z_floor_m":z,"ceiling_height_m":3.,"footprint":{"exterior":{"vertices":_RING},"interior_rings":[]},"footprint_fingerprint":fingerprint,
           "zones":[{"id":f"Z{floor_id}","name":f"Zone {floor_id}","role":"office","polygon":{"exterior":{"vertices":_RING},"interior_rings":[]},"source_refs":[_ref(f"plan-{floor_id}","A","zone_boundary")] }],"boundary_segments":segments}
    return floor, [north, east]


def make_b4b_gt_document(*, observed_elevation: bool = True) -> GroundTruthV3:
    """Two-floor L input with valid Vg, hidden/depth, 0..N keys, z-null and north."""
    f1, (north, east) = _floor("F1", 0.); f2, _ = _floor("F2", 3.)
    assert north is not None and east is not None
    lo, hi = north["visible_intervals"][0]["lo"], north["visible_intervals"][0]["hi"]
    a, b = lo + (hi-lo)*.3, lo + (hi-lo)*.7
    plan_ref = _ref("plan-F1","B","opening_plan")
    elev_refs = [_ref("elev-N","B","opening_elevation"), _ref("elev-N-detail","B","opening_elevation")]
    east_a, east_b = east["world_along_interval"]["lo"], east["world_along_interval"]["hi"]
    openings = [{"id":"O1","kind":"window","floor_id":"F1","host_zone_id":"ZF1","boundary_segment_id":north["id"],"world_along_interval":{"lo":a,"hi":b},"z_interval":{"lo":1.,"hi":2.} if observed_elevation else None,"source_refs":sorted(elev_refs+[plan_ref],key=lambda r:(r["source_id"],r["view_id"],r["entity_handle"],r["role"]))},
      {"id":"O2","kind":"door","floor_id":"F1","host_zone_id":"ZF1","boundary_segment_id":east["id"],"world_along_interval":{"lo":east_a+(east_b-east_a)*.25,"hi":east_a+(east_b-east_a)*.75},"z_interval":None,"source_refs":[plan_ref]}]
    if not observed_elevation: openings = [openings[1]]
    openings.sort(key=lambda item:(item["floor_id"],item["boundary_segment_id"],item["world_along_interval"]["lo"],item["kind"],item["id"]))
    payload={"schema_version":3,"case":"b4b-contract","geometry_profile":"c2_simple_orthogonal_no_holes","coordinate_frame":"building_axis_world_m","verification":{"status":"candidate","reviewer_id":None,"reviewed_on":None,"methods":[]},
      "generator":{"name":"energyplus-agent.gt_from_dxf","contract_version":1,"extractor_sha256":_HASH,"validator_sha256":_HASH,"vg_implementation_sha256":_HASH,"manifest_sha256":_HASH,"judge_config_sha256":_HASH,"vg_config_sha256":_HASH,"tolerances":_TOL},
      "sources":[{"id":"src","kind":"dxf","label":"source.dxf","content_sha256":_HASH,"native_units":"m","metres_per_unit":1.,"views":[
        {"id":"elev-N","kind":"elevation","floor_ids":["F1","F2"],"projection_surface_key":"surface-N","facade_family":"North","view_kind":"full","world_along_coverage":None,"direction_semantics":"building_axis","azimuth_deg":None},
        {"id":"elev-N-detail","kind":"elevation","floor_ids":["F1","F2"],"projection_surface_key":"surface-N-detail","facade_family":"North","view_kind":"full","world_along_coverage":None,"direction_semantics":"building_axis","azimuth_deg":None},
        {"id":"elev-S","kind":"elevation","floor_ids":["F1","F2"],"projection_surface_key":"surface-S","facade_family":"South","view_kind":"full","world_along_coverage":None,"direction_semantics":"building_axis","azimuth_deg":None},
        *[{"id":f"plan-{fid}","kind":"plan","floor_ids":[fid],"projection_surface_key":None,"facade_family":None,"view_kind":None,"world_along_coverage":None,"direction_semantics":None,"azimuth_deg":None} for fid in ("F1","F2")]]}],
      "north_axis_deg":27.5,"north_axis_source_refs":[_ref("plan-F1","C","north_axis")],"floors":[f1,f2],"openings":openings,"content_sha256":"0"*64}
    document = GroundTruthV3.model_validate(payload)
    payload["content_sha256"] = compute_gt_v3_content_sha256(document)
    document = GroundTruthV3.model_validate(payload)
    validate_gt_v3(document, tolerances=document.generator.tolerances)
    return document
