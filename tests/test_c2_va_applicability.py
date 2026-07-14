"""Va applicability contract: pure in-memory, gt-blind synthetic fixtures."""
from __future__ import annotations

import importlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from src.agent.correction.facade_applicability import (
    CLAIM_ORDER, ApplicabilityIntervalV1, ElevationClaimEvidenceV1,
    ElevationViewBindingV1, FacadeApplicabilityInvariantError,
    FacadeVisibilityLedgerV1, FloorVisibilityLedgerV1, OpeningClaimTargetV1,
    OpeningClaimsV1, PlanClaimEvidenceV1, _frame_hash, _segment_payload,
    _canonical_hash, derive_opening_claim_applicability,
)
from src.agent.correction.schema import FacadeSegment, WorldInterval
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import (
    CaseMetadataSourceRef, CompletenessAssertion, Coverage, DatasetSourceRef,
    OpeningEvidence, RequiredViewEntry, UserSourceRef, ViewManifest,
)

H = "a" * 64


def interval(lo=0.0, hi=2.0):
    return ApplicabilityIntervalV1(lo=lo, hi=hi)


def segment(visible=((0.0, 2.0),)):
    return FacadeSegment(id="seg-s", floor_id="f1", facade_family="South", p1=(0.0, 0.0), p2=(2.0, 0.0),
        outward_normal=(0, -1), world_along_interval=WorldInterval(lo=0.0, hi=2.0), depth=0.0,
        visible_intervals=[WorldInterval(lo=a, hi=b) for a, b in visible], source_footprint_fingerprint=H)


def required(input_id, view_type, evidence, *, floor_ref=None, direction="South", semantics="building_axis"):
    return RequiredViewEntry(input_id=input_id, source_image=f"case_data/{input_id}.png", image_sha256=H,
        view_type=view_type, floor_ref=floor_ref, declared_direction_token=direction if view_type == "elevation" else None,
        direction_source="standard_assumption", direction_semantics=semantics, semantics_source="case_metadata",
        azimuth_deg=90.0 if semantics == "true_azimuth" else None,
        building_view_direction=direction if view_type == "elevation" and semantics == "building_axis" else None, dimensioned=True,
        expected_output_id=input_id, opening_evidence=evidence)


def completeness_evidence(claims, *, channel, source="user", assertion_id="complete"):
    if source == "user":
        source_ref = UserSourceRef(source="user", content_sha256="1" * 64)
    elif source == "dataset":
        source_ref = DatasetSourceRef(source="dataset_ref", dataset_id="d", dataset_version="1", contract_id="c", content_sha256="2" * 64)
    else:
        source_ref = CaseMetadataSourceRef(source="case_metadata", json_pointer="/views/x", case_metadata_sha256="3" * 64)
    frame, region = ("plan_floor_region", "full_floor") if channel == "plan" else ("elevation_local_along", "full_facade")
    return OpeningEvidence(potentially_observable_claims=list(claims), negative_evidence_capable_claims=list(claims),
        coverage=Coverage(frame=frame, region=region, completeness_assertion_id=assertion_id),
        completeness_assertion=CompletenessAssertion(assertion_id=assertion_id, source_ref=source_ref))


def manifest(*entries):
    entries = sorted(entries, key=lambda x: x.input_id)
    payload = {"view_manifest_schema_version": "1", "claims_vocab_version": "1", "generator_version": "1",
        "completeness_ruleset_version": "1", "case_id": "case", "case_metadata_sha256": H,
        "entries": [e.model_dump(mode="json") for e in entries]}
    return ViewManifest(**payload, content_sha256=hash_obj(payload))


def fixture(*, visible=((0.0, 2.0),), plan_claims=("existence", "host", "along", "width"), elevation_claims=CLAIM_ORDER,
        plan_negative=(), elevation_negative=()):
    p_evidence = OpeningEvidence(potentially_observable_claims=list(plan_claims))
    e_evidence = OpeningEvidence(potentially_observable_claims=list(elevation_claims))
    # Completeness is intentionally optional; these helpers keep positive and negative axes separate.
    vm = manifest(required("plan", "plan", p_evidence, floor_ref=1), required("south", "elevation", e_evidence))
    seg = segment(visible)
    floor = FloorVisibilityLedgerV1(floor_id="f1", source_footprint_fingerprint=H, segments=(seg,))
    proto = FacadeVisibilityLedgerV1(source_kind="accepted_correction", source_schema_version="3", source_output_sha256="b" * 64,
        facade_segments_sha256="c" * 64, feature_states_sha256="d" * 64,
        helper_versions=("floor_footprint_v1", "facade_visibility_v1"), floors=(floor,))
    vis = proto.model_copy(update={"facade_segments_sha256": _canonical_hash(_segment_payload(proto))})
    bind0 = ElevationViewBindingV1(input_id="south", resolved_building_direction="South", resolution_source="manifest_building_axis",
        view_manifest_sha256=vm.content_sha256, orientation_output_hash=None, adapter_version=None,
        source_footprint_fingerprint=H, world_axis="x", sign=1, along_origin=0.0, mirrored=False,
        local_x_positive="image_left_to_right", frame_transform_sha256="e" * 64)
    binding = bind0.model_copy(update={"frame_transform_sha256": _frame_hash(bind0)})
    return vm, vis, binding


def opening(*, plan=(), elevation=(), target=None):
    target = target or interval()
    rows = []
    for claim in CLAIM_ORDER:
        evidence = tuple(PlanClaimEvidenceV1(source_input_id="plan", world_interval=target) for _ in [0] if claim in plan)
        evidence += tuple(ElevationClaimEvidenceV1(source_input_id="south", local_interval=target) for _ in [0] if claim in elevation)
        rows.append(OpeningClaimTargetV1(claim=claim, target_world_interval=target, positive_evidence=evidence))
    return OpeningClaimsV1(opening_id="o1", floor_id="f1", floor_ref=1, facade_segment_id="seg-s", facade_family="South", claims=tuple(rows))


def run(**kwargs):
    vm, vis, binding = fixture(**{k: v for k, v in kwargs.items() if k in {"visible"}})
    return derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(binding,), openings=(kwargs.get("opening") or opening(),))


def binding(input_id, vm, *, family="South", semantics="manifest_building_axis", mirrored=False, local="image_left_to_right", fingerprint=H):
    axis = "x" if family in ("North", "South") else "y"
    base = 1 if family in ("South", "East") else -1
    sign = -base if mirrored ^ (local == "image_right_to_left") else base
    proto = ElevationViewBindingV1(input_id=input_id, resolved_building_direction=family, resolution_source=semantics,
        view_manifest_sha256=vm.content_sha256, orientation_output_hash="4" * 64 if semantics == "resolved_direction_sidecar" else None,
        adapter_version="adapter_v1" if semantics == "resolved_direction_sidecar" else None,
        source_footprint_fingerprint=fingerprint, world_axis=axis, sign=sign, along_origin=0.0 if sign == 1 else 2.0,
        mirrored=mirrored, local_x_positive=local, frame_transform_sha256="e" * 64)
    return proto.model_copy(update={"frame_transform_sha256": _frame_hash(proto)})


def invoke(vm, vis, bindings, openings):
    return derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=tuple(bindings), openings=tuple(openings))


def test_full_visibility_and_stable_seven_claim_output():
    ledger = run(opening=opening(plan=("existence", "host", "along", "width"), elevation=("existence", "along", "width", "sill", "head", "appearance")))
    claims = ledger.openings[0].claims
    assert tuple(c.claim for c in claims) == CLAIM_ORDER
    assert all(c.status == "applicable" and c.reason == "full_observable_coverage" for c in claims)
    assert ledger.content_sha256 == _canonical_hash(ledger.model_dump(mode="json", exclude={"content_sha256"}))


def test_plan_bypasses_hidden_visibility_and_elevation_does_not():
    item = opening(plan=("existence", "host", "along", "width"), elevation=("sill", "head"))
    ledger = run(visible=(), opening=item)
    by_claim = {c.claim: c for c in ledger.openings[0].claims}
    assert [by_claim[x].status for x in ("existence", "host", "along", "width")] == ["applicable"] * 4
    assert [by_claim[x].status for x in ("sill", "head")] == ["not_applicable"] * 2


def test_partial_elevation_has_existence_exception_and_exact_partition():
    ledger = run(visible=((0.0, 1.0),), opening=opening(elevation=("existence", "along", "width", "sill", "head", "appearance")))
    by_claim = {c.claim: c for c in ledger.openings[0].claims}
    assert by_claim["existence"].status == "applicable"
    assert by_claim["existence"].reason == "existence_observable_fragment"
    assert by_claim["sill"].status == "partially_applicable"
    assert by_claim["sill"].applicable_intervals == (interval(0, 1),)
    assert by_claim["sill"].unobserved_intervals == (interval(1, 2),)


def test_half_open_touch_is_not_evidence():
    item = opening(elevation=("existence",), target=interval(0, 1))
    ledger = run(visible=((1.0, 2.0),), opening=item)
    assert ledger.openings[0].claims[0].status == "not_applicable"


@pytest.mark.parametrize("bad", [
    {"lo": "1", "hi": 2.0}, {"lo": True, "hi": 2.0}, {"lo": 1.0, "hi": 1.0},
    {"lo": float("nan"), "hi": 2.0}, {"lo": 1.0, "hi": float("inf")},
])
def test_strict_interval_wire_rejects_bad_scalars(bad):
    with pytest.raises(ValidationError):
        ApplicabilityIntervalV1(**bad)


def test_wrong_claim_order_and_disjoint_declaration_are_blocked():
    vm, vis, binding = fixture()
    good = opening(elevation=("existence",))
    bad_order = good.model_copy(update={"claims": tuple(reversed(good.claims))})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_claim_ledger_invalid"):
        derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(binding,), openings=(bad_order,))
    disjoint = opening(elevation=("existence",), target=interval(0, 2))
    rows = list(disjoint.claims)
    rows[0] = rows[0].model_copy(update={"positive_evidence": (ElevationClaimEvidenceV1(source_input_id="south", local_interval=interval(3, 4)),)})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_claim_ledger_invalid"):
        derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(binding,), openings=(disjoint.model_copy(update={"claims": tuple(rows)}),))


def test_identity_direction_and_frame_fail_closed():
    vm, vis, binding = fixture()
    bad_ledger = vis.model_copy(update={"facade_segments_sha256": "0" * 64})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_identity_mismatch"):
        derive_opening_claim_applicability(visibility=bad_ledger, manifest=vm, elevation_views=(binding,), openings=(opening(),))
    bad_binding = binding.model_copy(update={"sign": -1})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_projection_frame_invalid"):
        derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(bad_binding,), openings=(opening(),))


def test_input_permutation_is_canonical_and_no_input_mutation():
    vm, vis, binding = fixture()
    first = opening(elevation=("existence", "sill"))
    second = opening(elevation=("existence", "sill")).model_copy(update={"opening_id": "o0"})
    before = (vm.model_dump(), vis.model_dump(), binding.model_dump(), first.model_dump())
    a = derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(binding,), openings=(first, second))
    b = derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(binding,), openings=(second, first))
    assert a == b
    assert a.model_dump_json() == b.model_dump_json()
    assert before == (vm.model_dump(), vis.model_dump(), binding.model_dump(), first.model_dump())


def test_import_order_and_package_no_va_export():
    for statement in (
        "import src.agent.execution.view_manifest; import src.agent.correction.facade_applicability",
        "import src.agent.correction.facade_applicability; import src.agent.execution.view_manifest",
    ):
        assert subprocess.run([sys.executable, "-c", statement], check=False, capture_output=True).returncode == 0
    package = importlib.import_module("src.agent.correction")
    assert not hasattr(package, "derive_opening_claim_applicability")


def test_module_is_gt_blind_and_uses_no_forbidden_imports():
    source = importlib.import_module("src.agent.correction.facade_applicability").__file__
    text = open(source, encoding="utf-8").read()
    assert all(token not in text for token in ("judge.gt", "src.agent.judge", "scorer", "load_core_tolerances", "materialize_"))


def test_claim_ledger_totality_and_opening_segment_rejections():
    vm, vis, south = fixture()
    good = opening()
    for bad in (
        good.model_copy(update={"claims": good.claims[:-1]}),
        good.model_copy(update={"claims": good.claims[:1] + (good.claims[0],) + good.claims[1:]}),
        good.model_copy(update={"facade_segment_id": "missing"}),
        good.model_copy(update={"floor_id": "other"}),
        good.model_copy(update={"facade_family": "North"}),
    ):
        with pytest.raises(FacadeApplicabilityInvariantError):
            invoke(vm, vis, (south,), (bad,))
    unequal = list(good.claims)
    unequal[-1] = unequal[-1].model_copy(update={"target_world_interval": interval(0, 1)})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_claim_ledger_invalid"):
        invoke(vm, vis, (south,), (good.model_copy(update={"claims": tuple(unequal)}),))


def test_visibility_identity_closure_rejects_bad_source_shapes():
    vm, vis, south = fixture()
    floor = vis.floors[0]
    cases = (
        vis.model_copy(update={"floors": (floor, floor)}),
        vis.model_copy(update={"source_kind": "accepted_correction", "feature_states_sha256": None}),
        vis.model_copy(update={"source_kind": "judge_gt", "feature_states_sha256": H}),
        vis.model_copy(update={"helper_versions": ("facade_visibility_v1",)}),
        vis.model_copy(update={"floors": (floor.model_copy(update={"source_footprint_fingerprint": "0" * 64}),)}),
    )
    for bad in cases:
        with pytest.raises(FacadeApplicabilityInvariantError):
            invoke(vm, bad, (south,), (opening(),))
    cross_floor = floor.model_copy(update={"segments": (floor.segments[0].model_copy(update={"floor_id": "f2"}),)})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_visibility_ledger_invalid"):
        invoke(vm, vis.model_copy(update={"floors": (cross_floor,)}), (south,), (opening(),))


def test_manifest_and_output_hash_tampering_fail_closed():
    vm, vis, south = fixture()
    payload = vm.model_dump(mode="json")
    payload["case_id"] = "tampered"
    with pytest.raises(ValidationError):
        ViewManifest(**payload)
    bad = south.model_copy(update={"view_manifest_sha256": "0" * 64})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_identity_mismatch"):
        invoke(vm, vis, (bad,), (opening(),))
    ledger = run()
    with pytest.raises(ValidationError):
        type(ledger)(**ledger.model_dump(mode="json", exclude={"content_sha256"}), content_sha256="0" * 64)


def test_strict_new_models_reject_unknown_string_numeric_bool_and_empty_ids():
    vm, vis, south = fixture()
    examples = ((type(south), south), (type(vis), vis), (OpeningClaimsV1, opening()))
    for model, value in examples:
        payload = value.model_dump(mode="json")
        payload["unexpected"] = True
        with pytest.raises(ValidationError):
            model(**payload)
    payload = south.model_dump(mode="json")
    payload["along_origin"] = "0"
    with pytest.raises(ValidationError):
        type(south)(**payload)
    with pytest.raises(ValidationError):
        ElevationViewBindingV1(**{**south.model_dump(mode="json"), "input_id": ""})
    with pytest.raises(ValidationError):
        ElevationViewBindingV1(**{**south.model_dump(mode="json"), "mirrored": "unknown"})


_DIRECTION_MATRIX = (
    # family, mirrored, local convention, expected sign, expected origin,
    # expected local x=0 / x=2 world endpoints.  These are frozen hand-written
    # contract values, not a reproduction of the binding helper's XOR formula.
    ("North", False, "image_left_to_right", -1, 2.0, (2.0, 0.0)),
    ("North", True, "image_left_to_right", 1, 0.0, (0.0, 2.0)),
    ("North", False, "image_right_to_left", 1, 0.0, (0.0, 2.0)),
    ("North", True, "image_right_to_left", -1, 2.0, (2.0, 0.0)),
    ("South", False, "image_left_to_right", 1, 0.0, (0.0, 2.0)),
    ("South", True, "image_left_to_right", -1, 2.0, (2.0, 0.0)),
    ("South", False, "image_right_to_left", -1, 2.0, (2.0, 0.0)),
    ("South", True, "image_right_to_left", 1, 0.0, (0.0, 2.0)),
    ("East", False, "image_left_to_right", 1, 0.0, (0.0, 2.0)),
    ("East", True, "image_left_to_right", -1, 2.0, (2.0, 0.0)),
    ("East", False, "image_right_to_left", -1, 2.0, (2.0, 0.0)),
    ("East", True, "image_right_to_left", 1, 0.0, (0.0, 2.0)),
    ("West", False, "image_left_to_right", -1, 2.0, (2.0, 0.0)),
    ("West", True, "image_left_to_right", 1, 0.0, (0.0, 2.0)),
    ("West", False, "image_right_to_left", 1, 0.0, (0.0, 2.0)),
    ("West", True, "image_right_to_left", -1, 2.0, (2.0, 0.0)),
)


def _family_segment(family):
    p1, p2, normal = {
        "North": ((0.0, 2.0), (2.0, 2.0), (0, 1)),
        "South": ((0.0, 0.0), (2.0, 0.0), (0, -1)),
        "East": ((2.0, 0.0), (2.0, 2.0), (1, 0)),
        "West": ((0.0, 0.0), (0.0, 2.0), (-1, 0)),
    }[family]
    return FacadeSegment(id=f"seg-{family}", floor_id="f1", facade_family=family, p1=p1, p2=p2,
        outward_normal=normal, world_along_interval=WorldInterval(lo=0.0, hi=2.0), depth=0.0,
        visible_intervals=[WorldInterval(lo=0.0, hi=2.0)], source_footprint_fingerprint=H)


def _matrix_visibility(family):
    floor = FloorVisibilityLedgerV1(floor_id="f1", source_footprint_fingerprint=H, segments=(_family_segment(family),))
    proto = FacadeVisibilityLedgerV1(source_kind="accepted_correction", source_schema_version="3", source_output_sha256="b" * 64,
        facade_segments_sha256="c" * 64, feature_states_sha256="d" * 64,
        helper_versions=("floor_footprint_v1", "facade_visibility_v1"), floors=(floor,))
    return proto.model_copy(update={"facade_segments_sha256": _canonical_hash(_segment_payload(proto))})


def _matrix_binding(input_id, vm, family, mirrored, local, expected_sign, expected_origin):
    proto = ElevationViewBindingV1(input_id=input_id, resolved_building_direction=family,
        resolution_source="manifest_building_axis", view_manifest_sha256=vm.content_sha256,
        orientation_output_hash=None, adapter_version=None, source_footprint_fingerprint=H,
        world_axis="x" if family in ("North", "South") else "y", sign=expected_sign,
        along_origin=expected_origin, mirrored=mirrored, local_x_positive=local,
        frame_transform_sha256="e" * 64)
    return proto.model_copy(update={"frame_transform_sha256": _frame_hash(proto)})


def _matrix_opening(family):
    rows = []
    for claim in CLAIM_ORDER:
        evidence = (ElevationClaimEvidenceV1(source_input_id="view", local_interval=interval()),) if claim == "existence" else ()
        rows.append(OpeningClaimTargetV1(claim=claim, target_world_interval=interval(), positive_evidence=evidence))
    return OpeningClaimsV1(opening_id="o1", floor_id="f1", floor_ref=1, facade_segment_id=f"seg-{family}", facade_family=family, claims=tuple(rows))


@pytest.mark.parametrize("family,mirrored,local,expected_sign,expected_origin,expected_endpoints", _DIRECTION_MATRIX)
def test_direction_frame_xor_matrix_all_families(family, mirrored, local, expected_sign, expected_origin, expected_endpoints):
    vm = manifest(required("view", "elevation", OpeningEvidence(potentially_observable_claims=["existence"]), direction=family))
    view_binding = _matrix_binding("view", vm, family, mirrored, local, expected_sign, expected_origin)
    assert view_binding.sign == expected_sign
    assert view_binding.along_origin == expected_origin
    # §11.7: assert both local endpoints themselves before checking the pure Va result.
    assert (view_binding.along_origin + view_binding.sign * 0.0,
            view_binding.along_origin + view_binding.sign * 2.0) == expected_endpoints
    ledger = invoke(vm, _matrix_visibility(family), (view_binding,), (_matrix_opening(family),))
    decision = ledger.openings[0].claims[0].source_evidence[0]
    assert decision.positive_mapped_world_interval == interval(0.0, 2.0)
    assert decision.applicable_intervals == (interval(0.0, 2.0),)
    assert ledger.openings[0].claims[0].status == "applicable"


@pytest.mark.parametrize("field,value", (("world_axis", "y"), ("along_origin", 1.0), ("source_footprint_fingerprint", "0" * 64)))
def test_projection_binding_axis_origin_and_fingerprint_drift_reject(field, value):
    vm, vis, south = fixture()
    bad = south.model_copy(update={field: value})
    # Keep the frame hash internally self-consistent: derive must reject the named
    # binding fact rather than merely catching a stale hash.
    bad = bad.model_copy(update={"frame_transform_sha256": _frame_hash(bad)})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_projection_frame_invalid"):
        invoke(vm, vis, (bad,), (opening(elevation=("existence",)),))


def test_direction_resolution_sidecar_true_azimuth_and_unknown_paths():
    for semantics in ("true_azimuth", "unknown"):
        vm = manifest(required("side", "elevation", OpeningEvidence(), direction="South", semantics=semantics))
        vis = fixture()[1]
        good = binding("side", vm, semantics="resolved_direction_sidecar")
        invoke(vm, vis, (good,), ())
        for patch in ({"orientation_output_hash": None}, {"adapter_version": None}, {"view_manifest_sha256": "0" * 64}):
            with pytest.raises(FacadeApplicabilityInvariantError):
                invoke(vm, vis, (good.model_copy(update=patch),), ())
    building_vm = manifest(required("side", "elevation", OpeningEvidence(), direction="South"))
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_direction_unresolved"):
        invoke(building_vm, fixture()[1], (binding("side", building_vm, semantics="resolved_direction_sidecar"),), ())


def test_binding_cardinality_and_building_axis_family_rejections():
    vm, vis, south = fixture()
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_direction_unresolved"):
        invoke(vm, vis, (), ())
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_direction_unresolved"):
        invoke(vm, vis, (south, south), ())
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_direction_unresolved"):
        invoke(vm, vis, (south, binding("plan", vm)), ())
    wrong = south.model_copy(update={"resolved_building_direction": "North"})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_direction_unresolved"):
        invoke(vm, vis, (wrong,), ())


def test_overreach_positive_evidence_duplicate_and_honest_absence():
    vm, vis, south = fixture()
    no_evidence = invoke(vm, vis, (south,), (opening(),))
    assert all(c.status == "not_applicable" for c in no_evidence.openings[0].claims)
    rows = list(opening().claims)
    rows[0] = rows[0].model_copy(update={"positive_evidence": (
        PlanClaimEvidenceV1(source_input_id="plan", world_interval=interval()),
        PlanClaimEvidenceV1(source_input_id="plan", world_interval=interval()),
    )})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_claim_ledger_invalid"):
        invoke(vm, vis, (south,), (opening().model_copy(update={"claims": tuple(rows)}),))
    elev_host = list(opening().claims)
    elev_host[1] = elev_host[1].model_copy(update={"positive_evidence": (ElevationClaimEvidenceV1(source_input_id="south", local_interval=interval()),)})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_claim_ledger_invalid"):
        invoke(vm, vis, (south,), (opening().model_copy(update={"claims": tuple(elev_host)}),))
    rows[4] = rows[4].model_copy(update={"positive_evidence": (PlanClaimEvidenceV1(source_input_id="plan", world_interval=interval()),)})
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_claim_ledger_invalid"):
        invoke(vm, vis, (south,), (opening().model_copy(update={"claims": tuple(rows)}),))


def test_full_occlusion_and_plan_four_claims_are_channel_specific():
    item = opening(plan=("existence", "host", "along", "width"), elevation=("existence", "along", "width", "sill", "head", "appearance"))
    result = run(visible=(), opening=item).openings[0]
    got = {x.claim: x.status for x in result.claims}
    assert [got[x] for x in ("existence", "host", "along", "width")] == ["applicable"] * 4
    assert [got[x] for x in ("sill", "head", "appearance")] == ["not_applicable"] * 3


def test_half_open_adjacent_merge_and_real_gap_do_not_bridge():
    assert _canonical_hash([[0, 1], [1, 2]])  # keeps this test independent of private merge implementation.
    vm, vis, south = fixture(visible=((0, 1), (1, 2)))
    result = invoke(vm, vis, (south,), (opening(elevation=("existence",)),)).openings[0].claims[0]
    assert result.applicable_intervals == (interval(0, 2),)
    vm, vis, south = fixture(visible=((0, 0.5), (1, 2)))
    result = invoke(vm, vis, (south,), (opening(elevation=("existence",)),)).openings[0].claims[0]
    assert result.applicable_intervals == (interval(0, 0.5), interval(1, 2))
    assert result.unobserved_intervals == (interval(0.5, 1),)


def test_multiple_elevation_sources_union_and_plan_audit_retention():
    e = OpeningEvidence(potentially_observable_claims=list(CLAIM_ORDER))
    p = OpeningEvidence(potentially_observable_claims=["existence", "host", "along", "width"])
    vm = manifest(required("a", "elevation", e), required("b", "elevation", e), required("plan", "plan", p, floor_ref=1))
    _, vis, _ = fixture()
    a, b = binding("a", vm), binding("b", vm)
    rows = []
    for claim in CLAIM_ORDER:
        evidence = ()
        if claim == "existence":
            evidence = (PlanClaimEvidenceV1(source_input_id="plan", world_interval=interval()),
                        ElevationClaimEvidenceV1(source_input_id="a", local_interval=interval(0, 1)),
                        ElevationClaimEvidenceV1(source_input_id="b", local_interval=interval(1, 2)))
        rows.append(OpeningClaimTargetV1(claim=claim, target_world_interval=interval(), positive_evidence=evidence))
    claim = invoke(vm, vis, (a, b), (opening().model_copy(update={"claims": tuple(rows)}),)).openings[0].claims[0]
    assert claim.applicable_intervals == (interval(),)
    assert claim.supporting_source_view_ids == ("plan", "a", "b")
    assert claim.considered_source_view_ids == ("plan", "a", "b")


def test_mapped_partial_target_intersection_and_target_overrun_reject():
    vm, vis, south = fixture()
    rows = list(opening().claims)
    rows[4] = rows[4].model_copy(update={"positive_evidence": (ElevationClaimEvidenceV1(source_input_id="south", local_interval=interval(-1, 1)),)})
    result = invoke(vm, vis, (south,), (opening().model_copy(update={"claims": tuple(rows)}),)).openings[0].claims[4]
    assert result.applicable_intervals == (interval(0, 1),)
    with pytest.raises(FacadeApplicabilityInvariantError, match="va_claim_ledger_invalid"):
        invoke(vm, vis, (south,), (opening(target=interval(0, 3)),))


def test_negative_capability_sources_and_multi_elevation_family_filter():
    plan = required("plan", "plan", completeness_evidence(["existence"], channel="plan", source="case", assertion_id="p"), floor_ref=1)
    south = required("south", "elevation", completeness_evidence(["existence"], channel="elevation", source="user", assertion_id="s"), direction="South")
    east = required("east", "elevation", completeness_evidence(["existence"], channel="elevation", source="dataset", assertion_id="e"), direction="East")
    vm = manifest(plan, south, east)
    _, vis, _ = fixture(visible=((0, 1),))
    bindings = (binding("south", vm), binding("east", vm, family="East"))
    result = invoke(vm, vis, bindings, (opening(),)).openings[0].claims[0]
    assert result.considered_source_view_ids == ("plan", "south")
    by_source = {x.source_input_id: x for x in result.source_evidence}
    assert by_source["plan"].negative_evidence_intervals == (interval(),)
    assert by_source["south"].negative_evidence_intervals == (interval(0, 1),)
    assert by_source["plan"].completeness_assertion_id == "p"
    assert by_source["south"].completeness_assertion_id == "s"
    assert "east" not in by_source


def test_sm26_hidden_and_provenance_orthogonality_synthetic_fixture():
    item = opening(plan=("existence", "host", "along", "width"), elevation=("sill", "head"))
    result = run(visible=(), opening=item)
    statuses = {x.claim: x.status for x in result.openings[0].claims}
    assert [statuses[c] for c in ("existence", "host", "along", "width")] == ["applicable"] * 4
    assert statuses["sill"] == statuses["head"] == "not_applicable"
    # observed/derived/assumed are deliberately adapter-only fields: no such input enters Va.
    assert result == run(visible=(), opening=item)


def test_judge_executor_parity_and_b4b_seam_shape_without_product_or_gt_io():
    vm, product, south = fixture(visible=((0, 1),))
    judge = product.model_copy(update={"source_kind": "judge_gt", "feature_states_sha256": None,
        "source_output_sha256": "9" * 64})
    judge = judge.model_copy(update={"facade_segments_sha256": _canonical_hash(_segment_payload(judge))})
    source = opening(elevation=("existence", "sill"))
    a, b = invoke(vm, judge, (south,), (source,)), invoke(vm, judge, (south,), (source.model_copy(),))
    assert a == b
    shape = {c.claim: ("INCLUDED" if c.status == "applicable" else "PARTIAL" if c.status == "partially_applicable" else "NOT_APPLICABLE(unobserved)") for c in a.openings[0].claims}
    assert set(shape) == set(CLAIM_ORDER)
    assert "0.5" not in str(a.model_dump()) and "weight" not in str(a.model_dump())


def test_purity_concurrency_and_small_integer_partition_oracle(monkeypatch):
    import builtins
    import os
    import random
    import time
    import src.agent.correction.facade_visibility as fv
    vm, vis, south = fixture(visible=((0, 1),))
    item = opening(elevation=("existence", "sill"))
    def forbidden(*_a, **_k):
        raise AssertionError("Va must stay in-memory")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(random, "random", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(fv, "materialize_all_facade_segments", forbidden)
    expected = invoke(vm, vis, (south,), (item,))
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(x == expected for x in pool.map(lambda _: invoke(vm, vis, (south,), (item,)), range(8)))
    claim = expected.openings[0].claims[4]
    covered = {(x, x + 1) for x in range(2) if any(i.lo <= x and x + 1 <= i.hi for i in claim.applicable_intervals)}
    unobserved = {(x, x + 1) for x in range(2) if any(i.lo <= x and x + 1 <= i.hi for i in claim.unobserved_intervals)}
    assert covered.isdisjoint(unobserved) and covered | unobserved == {(0, 1), (1, 2)}


def test_zero_one_and_many_relevant_sources_do_not_assume_four_elevations():
    vm, vis, south = fixture()
    assert invoke(vm, vis, (south,), (opening(),)).openings[0].claims[0].considered_source_view_ids == ()
    assert invoke(vm, vis, (south,), (opening(elevation=("existence",)),)).openings[0].claims[0].considered_source_view_ids == ("south",)
