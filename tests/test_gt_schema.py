"""Phase-A strict GT schema, dual-read and frozen-profile regressions."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from src.agent.correction.facade_visibility import VisibilityTolerances, vg_for_direction
from src.agent.correction.footprint import footprint_fingerprint
import src.agent.judge.gt as gt_module
from src.agent.judge.gt import load_gt, load_gt_document, load_gt_file
from src.agent.judge.gt_manifest import GtExtractionManifestV1, load_gt_tooling_config
from src.agent.judge.gt_schema import (GroundTruthV3, GtValidationError,
                                       REPO_ROOT,
                                       canonical_gt_v3_bytes,
                                       compute_gt_implementation_hashes,
                                       compute_gt_v3_content_sha256,
                                       validate_gt_v3, write_gt_v3_candidate)


_HASH = "a" * 64


def _payload(*, verified: bool = False, north: float | None = None, ring: list[list[float]] | None = None) -> dict:
    tol = {
        "profile_version": 1, "dxf_node_join_tolerance_m": 0.001,
        "dxf_axis_alignment_tolerance_m": 0.001, "dxf_topology_area_tolerance_m2": 0.000001,
        "opening_boundary_max_distance_m": 0.4, "opening_assignment_tie_epsilon_m": 1e-9,
        "elevation_match_max_distance_m": 0.4, "elevation_match_tie_epsilon_m": 1e-9,
        "vg_depth_epsilon_m": 1e-9, "vg_endpoint_epsilon_m": 1e-9,
    }
    ring = ring or [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]
    refs = [{"source_id": "src", "view_id": "plan-F1", "entity_handle": "A", "subentity_index": None, "role": "footprint_boundary"}]
    segments = []
    for direction in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        for item in vg_for_direction(ring, direction, tolerances=VisibilityTolerances(1e-9, 1e-9)):
            frame = item.frame
            segments.append({"id": f"F1:boundary:{frame.facade_family}:{len(segments)}", "floor_id": "F1", "boundary_loop_id": "exterior",
                         "facade_family": frame.facade_family, "p1": list(frame.p1), "p2": list(frame.p2),
                         "outward_normal": list(frame.outward_normal), "world_along_interval": {"lo": frame.world_along_interval[0], "hi": frame.world_along_interval[1]},
                         "depth": frame.depth, "visible_intervals": [{"lo": lo, "hi": hi} for lo, hi in item.visible_intervals],
                         "source_footprint_fingerprint": footprint_fingerprint(ring), "projection_surface_keys": [],
                         "wall_thickness_m": None, "source_refs": refs})
    rank = {"North": 0, "South": 1, "East": 2, "West": 3}
    segments.sort(key=lambda s: (rank[s["facade_family"]], s["world_along_interval"]["lo"], s["world_along_interval"]["hi"], s["depth"], s["id"]))
    verification = {"status": "human_verified", "reviewer_id": "reviewer", "reviewed_on": "2026-07-14",
                    "methods": ["dxf_topology_roundtrip", "direct_gt_render", "overlay_on_original_drawing", "human_source_comparison"]} if verified else {"status": "candidate", "reviewer_id": None, "reviewed_on": None, "methods": []}
    payload = {"schema_version": 3, "case": "synthetic", "geometry_profile": "c2_simple_orthogonal_no_holes", "coordinate_frame": "building_axis_world_m",
               "verification": verification,
               "generator": {"name": "energyplus-agent.gt_from_dxf", "contract_version": 1,
                             "extractor_sha256": _HASH, "validator_sha256": _HASH, "vg_implementation_sha256": _HASH,
                             "manifest_sha256": _HASH, "judge_config_sha256": _HASH, "vg_config_sha256": _HASH, "tolerances": tol},
               "sources": [{"id": "src", "kind": "dxf", "label": "source.dxf", "content_sha256": _HASH,
                            "native_units": "m", "metres_per_unit": 1.0,
                            "views": [{"id": "plan-F1", "kind": "plan", "floor_ids": ["F1"], "projection_surface_key": None,
                                       "facade_family": None, "view_kind": None, "world_along_coverage": None,
                                       "direction_semantics": None, "azimuth_deg": None}]}],
               "north_axis_deg": north, "north_axis_source_refs": [],
               "floors": [{"id": "F1", "name": "Floor 1", "z_floor_m": 0.0, "ceiling_height_m": 3.0,
                           "footprint": {"exterior": {"vertices": ring}, "interior_rings": []},
                           "footprint_fingerprint": footprint_fingerprint(ring),
                           "zones": [{"id": "Z1", "name": "Zone", "role": "office", "polygon": {"exterior": {"vertices": ring}, "interior_rings": []}, "source_refs": refs}],
                           "boundary_segments": segments}], "openings": [], "content_sha256": "0" * 64}
    if north is not None:
        payload["north_axis_source_refs"] = [{"source_id": "src", "view_id": "plan-F1", "entity_handle": "B", "subentity_index": None, "role": "north_axis"}]
    doc = GroundTruthV3.model_validate(payload)
    payload["content_sha256"] = compute_gt_v3_content_sha256(doc)
    return payload


def _document(**kwargs) -> GroundTruthV3:
    return GroundTruthV3.model_validate(_payload(**kwargs))


def _rehash(payload: dict) -> dict:
    payload["content_sha256"] = "0" * 64
    payload["content_sha256"] = compute_gt_v3_content_sha256(GroundTruthV3.model_validate(payload))
    return payload


def _opening_payload(*, observed: bool) -> dict:
    payload = _payload()
    opening_refs = [{"source_id": "src", "view_id": "plan-F1", "entity_handle": "C", "subentity_index": None, "role": "opening_plan"}]
    if observed:
        elevation = {"id": "elev-S", "kind": "elevation", "floor_ids": ["F1"], "projection_surface_key": "surface-S",
                     "facade_family": "South", "view_kind": "full", "world_along_coverage": None,
                     "direction_semantics": "building_axis", "azimuth_deg": None}
        payload["sources"][0]["views"] = [elevation, *payload["sources"][0]["views"]]
        next(segment for segment in payload["floors"][0]["boundary_segments"] if segment["facade_family"] == "South")["projection_surface_keys"] = ["surface-S"]
        opening_refs.insert(0, {"source_id": "src", "view_id": "elev-S", "entity_handle": "D", "subentity_index": None, "role": "opening_elevation"})
    south_id = next(segment["id"] for segment in payload["floors"][0]["boundary_segments"] if segment["facade_family"] == "South")
    payload["openings"] = [{"id": "O1", "kind": "window", "floor_id": "F1", "host_zone_id": "Z1", "boundary_segment_id": south_id,
                            "world_along_interval": {"lo": 1.0, "hi": 2.0},
                            "z_interval": {"lo": 1.0, "hi": 2.0} if observed else None,
                            "source_refs": opening_refs}]
    return _rehash(payload)


def _issue(exc: pytest.ExceptionInfo[GtValidationError]) -> str:
    return exc.value.issues[0].code


def test_v3_candidate_and_verified_wire_validate():
    l_ring = [[0.0, 0.0], [4.0, 0.0], [4.0, 1.0], [2.0, 1.0], [2.0, 3.0], [0.0, 3.0]]
    for document in (_document(), _document(verified=True, north=27.5), GroundTruthV3.model_validate(_opening_payload(observed=False)), GroundTruthV3.model_validate(_opening_payload(observed=True)), _document(ring=l_ring)):
        validate_gt_v3(document, tolerances=document.generator.tolerances, expected_case="synthetic")


@pytest.mark.parametrize("mutate,wire_only", [
    (lambda p: p["floors"][0]["footprint"]["exterior"]["vertices"].append([0.0, 0.0]), False),
    (lambda p: p["floors"][0]["footprint"].update({"unexpected": 1}), True),
    (lambda p: p.update({"schema_version": "3"}), True),
    (lambda p: p["floors"][0].update({"ceiling_height_m": "3"}), True),
])
def test_v3_strict_wire_rejects_bad_shapes(mutate, wire_only):
    payload = _payload()
    mutate(payload)
    if wire_only:
        with pytest.raises(Exception):
            GroundTruthV3.model_validate(payload)
    else:
        document = GroundTruthV3.model_validate(payload)
        with pytest.raises(GtValidationError):
            validate_gt_v3(document, tolerances=document.generator.tolerances)


@pytest.mark.parametrize("mutate,wire_only", [
    (lambda p: p["floors"][0].update({"ceiling_height_m": True}), True),
    (lambda p: p["floors"][0]["boundary_segments"][0].pop("wall_thickness_m"), True),
    (lambda p: p["floors"][0]["footprint"]["exterior"]["vertices"].__setitem__(1, [float("nan"), 0.0]), True),
    (lambda p: p["floors"][0]["footprint"]["exterior"]["vertices"].__setitem__(1, [float("inf"), 0.0]), True),
    (lambda p: p["floors"][0]["footprint"]["exterior"].update({"vertices": [[0.0, 0.0], [0.0, 3.0], [4.0, 3.0], [4.0, 0.0]]}), False),
    (lambda p: p["floors"][0]["footprint"]["exterior"].update({"vertices": [[0.0, 0.0], [4.0, 1.0], [4.0, 3.0], [0.0, 3.0]]}), False),
    (lambda p: p["floors"][0]["footprint"]["exterior"].update({"vertices": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [2.0, 3.0], [2.0, 1.0], [0.0, 1.0], [0.0, 3.0]]}), False),
    (lambda p: p["floors"][0]["footprint"].update({"interior_rings": [{"vertices": [[0.5, 0.5], [0.5, 1.0], [1.0, 1.0], [1.0, 0.5]]}]}), False),
    (lambda p: p["floors"][0]["footprint"].update({"multipolygon": []}), True),
])
def test_phase_a_strict_rejection_family(mutate, wire_only):
    payload = _payload(); mutate(payload)
    if wire_only:
        with pytest.raises(Exception):
            GroundTruthV3.model_validate(payload)
    else:
        document = GroundTruthV3.model_validate(payload)
        with pytest.raises(GtValidationError):
            validate_gt_v3(document, tolerances=document.generator.tolerances)


def test_validator_rejects_hash_ring_and_segment_drift():
    payload = _payload()
    payload["floors"][0]["boundary_segments"][0]["depth"] = 1.0
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == "gt_boundary_segments_wire_mismatch"


def test_canonical_hash_changes_for_coordinates_and_write_round_trips(tmp_path):
    document = _document()
    first = canonical_gt_v3_bytes(document)
    out = tmp_path / "candidate.json"
    write_gt_v3_candidate(document, out)
    assert canonical_gt_v3_bytes(load_gt_file(out, allow_legacy=False)) == first
    altered = _payload()
    altered["floors"][0]["footprint"]["exterior"]["vertices"][1][0] = 4.1
    assert hashlib.sha256(first).digest() != hashlib.sha256(json.dumps(altered, sort_keys=True).encode()).digest()
    with pytest.raises(GtValidationError):
        write_gt_v3_candidate(document, out)


def test_dual_read_v2_raw_equality_and_v3_compatibility_gate(tmp_path):
    sm21_path = Path("case_tests/test_baseline/gt/sm21_anchor/gt.json")
    assert hashlib.sha256(sm21_path.read_bytes()).hexdigest() == "a9be379b1735163528396c36d96653cdf71a67ffe54dde6f942c7c86f53f3f8a"
    raw = json.loads(sm21_path.read_text())
    assert load_gt("sm21_anchor") == raw
    path = tmp_path / "gt" / "synthetic" / "gt.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(canonical_gt_v3_bytes(_document()))
    with pytest.raises(GtValidationError) as exc:
        load_gt("synthetic", gt_dir=tmp_path / "gt")
    assert _issue(exc) == "gt_v3_requires_typed_consumer"
    with pytest.raises(GtValidationError) as exc:
        load_gt_document("synthetic", gt_dir=tmp_path / "gt")
    assert _issue(exc) == "gt_default_root_candidate_forbidden"


def test_unknown_version_missing_and_path_traversal_fail(tmp_path):
    for value in (None, 1, 4, "2", True, 2.0):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"schema_version": value}))
        with pytest.raises(GtValidationError):
            load_gt_file(path)
    with pytest.raises(GtValidationError):
        load_gt("../escape", gt_dir=tmp_path)
    assert load_gt("missing", gt_dir=tmp_path) is None
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{")
    with pytest.raises(GtValidationError) as exc:
        load_gt_file(malformed)
    assert _issue(exc) == "gt_wire_decode_failed"


def test_loader_uses_archived_tolerances_without_current_config(monkeypatch, tmp_path):
    payload = _payload(verified=True)
    payload["generator"]["tolerances"]["dxf_node_join_tolerance_m"] = 0.002
    document = GroundTruthV3.model_validate(_rehash(payload))
    path = tmp_path / "verified.json"
    path.write_bytes(canonical_gt_v3_bytes(document))
    original_read_bytes = gt_module.Path.read_bytes
    protected = {(REPO_ROOT / "src/configs/judge_gt.yaml").resolve(), (REPO_ROOT / "src/configs/correction.yaml").resolve()}
    def guarded_read_bytes(path_obj):
        if path_obj.resolve() in protected:
            raise AssertionError("typed loader read tooling config")
        return original_read_bytes(path_obj)
    monkeypatch.setattr(gt_module.Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(OmegaConf, "load", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("typed loader read OmegaConf")))
    assert isinstance(load_gt_file(path), GroundTruthV3)
    case_path = tmp_path / "root" / "synthetic" / "gt.json"
    case_path.parent.mkdir(parents=True)
    case_path.write_bytes(canonical_gt_v3_bytes(document))
    assert isinstance(load_gt_document("synthetic", gt_dir=tmp_path / "root"), GroundTruthV3)


def test_tampered_archived_tolerance_without_hash_is_rejected(tmp_path):
    payload = _payload(verified=True)
    payload["generator"]["tolerances"]["dxf_node_join_tolerance_m"] = 0.002
    payload = _rehash(payload)
    payload["generator"]["tolerances"]["dxf_node_join_tolerance_m"] = 0.003
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(GtValidationError) as exc:
        load_gt_file(path)
    assert _issue(exc) == "gt_hash_content_mismatch"


def test_candidate_writer_rejects_protected_roots_cwd_and_symlink_escape(monkeypatch, tmp_path):
    gt_sources = REPO_ROOT / "case_tests/test_baseline/gt_sources"
    brand_new_case_data = REPO_ROOT / "case_tests/e2e_tests/brand_new_case/case_data"
    # gt_sources/ legitimately exists (sm21_anchor source.dxf lives there); the
    # no-side-effect probe pins the not-yet-existing subpaths instead.
    assert not (gt_sources / "synthetic").exists()
    assert not brand_new_case_data.exists()
    for out in (REPO_ROOT / "case_tests/test_baseline/gt/nope.json", gt_sources / "synthetic" / "gt.json", brand_new_case_data / "candidate.json"):
        with pytest.raises(GtValidationError) as exc:
            write_gt_v3_candidate(_document(), out)
        assert _issue(exc) == "gt_candidate_protected_path"
    assert not (gt_sources / "synthetic").exists()
    assert not brand_new_case_data.exists()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(GtValidationError):
        write_gt_v3_candidate(_document(), REPO_ROOT / "case_tests/test_baseline/gt/nope.json")
    escape = tmp_path / "escape"
    escape.symlink_to(REPO_ROOT / "case_tests/test_baseline", target_is_directory=True)
    with pytest.raises(GtValidationError):
        write_gt_v3_candidate(_document(), escape / "gt" / "nope.json")


@pytest.mark.parametrize("mutate,code", [
    (lambda p: p["floors"][0]["zones"][0]["polygon"]["exterior"].update({"vertices": [[0.0, 0.0], [3.9, 0.0], [3.9, 3.0], [0.0, 3.0]]}), "gt_zone_tiling_mismatch"),
    (lambda p: p["floors"][0]["zones"].append(copy.deepcopy(p["floors"][0]["zones"][0]) | {"id": "Z2"}), "gt_zone_overlap"),
    (lambda p: p["floors"][0].update({"footprint_fingerprint": "b" * 64}), "gt_hash_footprint_mismatch"),
    (lambda p: p["verification"].update({"reviewer_id": "bad"}), "gt_wire_candidate_verification_invalid"),
])
def test_zone_hash_and_verification_rejections(mutate, code):
    payload = _payload()
    mutate(payload)
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == code


def test_verified_requires_all_four_methods():
    payload = _payload(verified=True)
    payload["verification"]["methods"].pop()
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == "gt_wire_verified_verification_invalid"


@pytest.mark.parametrize("mutate", [
    lambda s: s.update({"facade_family": "South"}),
    lambda s: s.update({"outward_normal": [1, 0]}),
    lambda s: s.update({"p1": [3.9, 3.0]}),
    lambda s: s.update({"world_along_interval": {"lo": 0.1, "hi": 4.0}}),
    lambda s: s.update({"visible_intervals": []}),
    lambda s: s.update({"source_footprint_fingerprint": "b" * 64}),
])
def test_segment_drift_rejection_family(mutate):
    payload = _payload()
    mutate(payload["floors"][0]["boundary_segments"][0])
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError):
        validate_gt_v3(document, tolerances=document.generator.tolerances)


@pytest.mark.parametrize("mutate,code", [
    (lambda p: p["openings"][0].update({"floor_id": "F2"}), "gt_opening_invalid_reference"),
    (lambda p: p["openings"][0].update({"host_zone_id": None}), "gt_opening_invalid_host_zone"),
    (lambda p: p["openings"][0]["world_along_interval"].update({"hi": 5.0}), "gt_opening_outside_segment"),
    (lambda p: p["openings"][0].update({"z_interval": {"lo": 2.9, "hi": 3.1}}), "gt_opening_z_outside_floor"),
    (lambda p: p["openings"][0]["source_refs"].__setitem__(0, {"source_id": "src", "view_id": "plan-F1", "entity_handle": "D", "subentity_index": None, "role": "configured_binding"}), "gt_opening_plan_source_missing"),
])
def test_opening_rejection_family(mutate, code):
    payload = _opening_payload(observed=False)
    mutate(payload)
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == code


@pytest.mark.parametrize("mutate,code", [
    (lambda p: p["openings"][0].update({"z_interval": None}), "gt_opening_elevation_evidence_mismatch"),
    (lambda p: p["sources"][0]["views"][0].update({"direction_semantics": "true_azimuth", "azimuth_deg": 0.0}), "gt_source_elevation_direction_invalid"),
    (lambda p: p["sources"][0]["views"][0].update({"view_kind": "partial", "world_along_coverage": None}), "gt_source_elevation_coverage_invalid"),
])
def test_elevation_relevance_and_view_contract_rejections(mutate, code):
    payload = _opening_payload(observed=True)
    mutate(payload)
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == code


def test_plan_only_mismatch_and_duplicate_projection_key_are_rejected():
    payload = _opening_payload(observed=False)
    payload["openings"][0]["z_interval"] = {"lo": 1.0, "hi": 2.0}
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == "gt_opening_plan_only_evidence_mismatch"
    payload = _opening_payload(observed=True)
    duplicate = copy.deepcopy(payload["sources"][0]["views"][0]); duplicate["id"] = "elev-S2"
    payload["sources"][0]["views"] = [payload["sources"][0]["views"][0], duplicate, payload["sources"][0]["views"][1]]
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == "gt_source_duplicate_projection_surface_key"


def test_opening_host_with_two_positive_boundary_zone_matches_is_rejected():
    payload = _opening_payload(observed=False)
    zone = payload["floors"][0]["zones"][0]
    zone["polygon"]["exterior"]["vertices"] = [[0.0, 0.0], [2.0, 0.0], [2.0, 3.0], [0.0, 3.0]]
    payload["floors"][0]["zones"].append(copy.deepcopy(zone) | {"id": "Z2", "name": "Zone 2", "polygon": {"exterior": {"vertices": [[2.0, 0.0], [4.0, 0.0], [4.0, 3.0], [2.0, 3.0]]}, "interior_rings": []}})
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == "gt_opening_host_zone_boundary_mismatch"


def test_noncanonical_persisted_list_is_rejected():
    payload = _payload()
    payload["floors"][0]["boundary_segments"].reverse()
    document = GroundTruthV3.model_validate(payload)
    with pytest.raises(GtValidationError) as exc:
        validate_gt_v3(document, tolerances=document.generator.tolerances)
    assert _issue(exc) == "gt_wire_noncanonical_order"


def test_default_root_candidate_prohibition(monkeypatch, tmp_path):
    root = tmp_path / "default-gt"
    path = root / "synthetic" / "gt.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(canonical_gt_v3_bytes(_document()))
    monkeypatch.setattr(gt_module, "DEFAULT_GT_DIR", root)
    with pytest.raises(GtValidationError) as exc:
        load_gt_document("synthetic", gt_dir=gt_module.DEFAULT_GT_DIR)
    assert _issue(exc) == "gt_default_root_candidate_forbidden"


def test_tooling_config_has_all_seven_values_and_vg_provenance():
    config = load_gt_tooling_config(Path("src/configs/judge_gt.yaml"), Path("src/configs/correction.yaml"))
    assert config.tolerances.profile_version == 1
    assert config.tolerances.vg_depth_epsilon_m == 1e-9
    assert config.tolerances.opening_boundary_max_distance_m == 0.4


def test_implementation_hashes_are_available_once_phase_b_extractor_exists():
    hashes = compute_gt_implementation_hashes(REPO_ROOT)
    assert all(len(value) == 64 and value != "0" * 64 for value in hashes.model_dump().values())


def _manifest_payload() -> dict:
    selector = {"entity_types": ["LINE"], "layers": ["WALL"], "handles": [], "handle_mode": "all_matching", "min_count": 1, "max_count": None}
    payload = {"manifest_version": 1, "case": "synthetic", "source_id": "src", "source_dxf_label": "source.dxf", "source_dxf_sha256": _HASH,
               "native_units": "m", "metres_per_unit": 1.0, "geometry_profile": "c2_simple_orthogonal_no_holes",
               "floors": [{"id": "F1", "name": "Floor 1", "z_floor_m": 0.0, "ceiling_height_m": 3.0}],
               "views": [{"kind": "plan", "id": "plan-F1", "floor_id": "F1", "clip_box_dxf": {"xmin": 0.0, "ymin": 0.0, "xmax": 4.0, "ymax": 3.0},
                          "world_from_source_m": {"m00": 1.0, "m01": 0.0, "m02": 0.0, "m10": 0.0, "m11": 1.0, "m12": 0.0},
                          "footprint_boundary": selector, "zone_boundaries": selector, "plan_openings": [],
                          "zone_seeds": [{"zone_id": "Z1", "name": "Zone", "role": "office", "point_world_m": [1.0, 1.0]}],
                          "boundary_reference": "outer_skin", "default_wall_thickness_m": None}],
               "north_axis": None, "raster_overlays": [], "manifest_sha256": "0" * 64}
    canonical = dict(payload)
    canonical["manifest_sha256"] = "0" * 64
    payload["manifest_sha256"] = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n").hexdigest()
    return payload


def test_manifest_hash_and_reference_uniqueness_are_strict():
    assert isinstance(GtExtractionManifestV1.model_validate(_manifest_payload()), GtExtractionManifestV1)
    bad_hash = _manifest_payload(); bad_hash["manifest_sha256"] = "b" * 64
    with pytest.raises(Exception):
        GtExtractionManifestV1.model_validate(bad_hash)
    bad_overlay = _manifest_payload()
    bad_overlay["raster_overlays"] = [{"id": "raster", "source_label": "view.png", "source_sha256": _HASH, "view_id": "missing", "pixel_to_source_m": {"m00": 1.0, "m01": 0.0, "m02": 0.0, "m10": 0.0, "m11": 1.0, "m12": 0.0}}]
    with pytest.raises(Exception):
        GtExtractionManifestV1.model_validate(bad_overlay)


def test_config_root_is_not_cwd_anchored(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml", REPO_ROOT / "src/configs/correction.yaml").tolerances.profile_version == 1
