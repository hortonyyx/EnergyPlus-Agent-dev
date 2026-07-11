"""C2 B-M §3: strict typed view-manifest schema — discriminated union,
conditional constraints, and the §3.6 CompletenessAssertion wire (frozen)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.agent.correction.claims import CLAIMS_VOCAB_VERSION
from src.agent.execution.view_manifest import (
    CaseMetadataSourceRef,
    CompletenessAssertion,
    Coverage,
    DatasetSourceRef,
    ExcludedInputEntry,
    OpeningEvidence,
    RequiredViewEntry,
    UserSourceRef,
    ViewManifest,
    compute_content_hash,
)

HEX64_A = "a" * 64
HEX64_B = "b" * 64


def _plan_entry(**overrides) -> RequiredViewEntry:
    fields = dict(
        input_id="1f_view",
        source_image="case_data/1f_view.png",
        image_sha256=HEX64_A,
        view_type="plan",
        floor_ref=1,
        direction_source="standard_assumption",
        direction_semantics="building_axis",
        semantics_source="standard_assumption",
        dimensioned=True,
        expected_output_id="1f_view",
        opening_evidence=OpeningEvidence(potentially_observable_claims=["existence", "host", "along", "width"]),
    )
    fields.update(overrides)
    return RequiredViewEntry(**fields)


def _elevation_entry(**overrides) -> RequiredViewEntry:
    fields = dict(
        input_id="South_view",
        source_image="case_data/South_view.png",
        image_sha256=HEX64_A,
        view_type="elevation",
        declared_direction_token="South",
        direction_source="user",
        direction_semantics="building_axis",
        semantics_source="standard_assumption",
        building_view_direction="South",
        dimensioned=True,
        expected_output_id="South_view",
        opening_evidence=OpeningEvidence(
            potentially_observable_claims=["existence", "along", "width", "sill", "head", "appearance"]
        ),
    )
    fields.update(overrides)
    return RequiredViewEntry(**fields)


# --------------------------------------------------------------------------- #
# basic construction
# --------------------------------------------------------------------------- #
def test_plan_and_elevation_entries_construct():
    plan = _plan_entry()
    elev = _elevation_entry()
    assert plan.kind == "required_view"
    assert elev.direction_semantics == "building_axis"


def test_excluded_input_entry_construct():
    entry = ExcludedInputEntry(
        input_id="1f_view_source",
        source_image="case_data/1f_view_source.png",
        image_sha256=HEX64_A,
        excluded_reason="derived_working_copy",
        parent_input_id="1f_view",
    )
    assert entry.kind == "excluded_input"


# --------------------------------------------------------------------------- #
# reader_output_required is structurally frozen True in C2 (§2 铁律)
# --------------------------------------------------------------------------- #
def test_reader_output_required_cannot_be_false():
    with pytest.raises(ValidationError):
        _plan_entry(reader_output_required=False)


# --------------------------------------------------------------------------- #
# RequiredViewEntry conditional constraints
# --------------------------------------------------------------------------- #
def test_floor_ref_required_for_plan():
    with pytest.raises(ValidationError):
        _plan_entry(floor_ref=None)


def test_floor_ref_forbidden_for_non_plan():
    with pytest.raises(ValidationError):
        _elevation_entry(floor_ref=1)


def test_declared_direction_token_required_for_elevation():
    with pytest.raises(ValidationError):
        _elevation_entry(declared_direction_token=None, building_view_direction=None)


def test_true_azimuth_requires_azimuth_deg_in_range():
    with pytest.raises(ValidationError):
        _elevation_entry(direction_semantics="true_azimuth", building_view_direction=None, azimuth_deg=None)
    with pytest.raises(ValidationError):
        _elevation_entry(direction_semantics="true_azimuth", building_view_direction=None, azimuth_deg=360.0)
    with pytest.raises(ValidationError):
        _elevation_entry(direction_semantics="true_azimuth", building_view_direction=None, azimuth_deg=float("nan"))
    ok = _elevation_entry(direction_semantics="true_azimuth", building_view_direction=None, azimuth_deg=90.0)
    assert ok.azimuth_deg == 90.0


def test_azimuth_deg_forbidden_outside_true_azimuth():
    with pytest.raises(ValidationError):
        _elevation_entry(azimuth_deg=90.0)  # direction_semantics=building_axis here


def test_building_view_direction_forbidden_outside_building_axis():
    with pytest.raises(ValidationError):
        _elevation_entry(
            direction_semantics="true_azimuth", azimuth_deg=90.0, building_view_direction="South"
        )
    with pytest.raises(ValidationError):
        _elevation_entry(
            direction_semantics="unknown", building_view_direction="South"
        )


def test_source_image_must_be_normalized_case_data_relative():
    for bad in ("/abs/case_data/x.png", "case_data/../x.png", "case_data/sub/x.png", "elsewhere/x.png"):
        with pytest.raises(ValidationError):
            _plan_entry(source_image=bad)


def test_image_sha256_must_be_hex64():
    with pytest.raises(ValidationError):
        _plan_entry(image_sha256="not-a-hash")
    with pytest.raises(ValidationError):
        _plan_entry(image_sha256="A" * 64)  # uppercase not accepted (canonical lowercase)
    with pytest.raises(ValidationError):
        _plan_entry(image_sha256="a" * 63)


# --------------------------------------------------------------------------- #
# ExcludedInputEntry conditional constraints
# --------------------------------------------------------------------------- #
def test_derived_working_copy_requires_parent_input_id():
    with pytest.raises(ValidationError):
        ExcludedInputEntry(
            input_id="x_source", source_image="case_data/x_source.png",
            image_sha256=HEX64_A, excluded_reason="derived_working_copy", parent_input_id=None,
        )


def test_non_drawing_asset_forbids_parent_input_id():
    with pytest.raises(ValidationError):
        ExcludedInputEntry(
            input_id="logo", source_image="case_data/logo.png",
            image_sha256=HEX64_A, excluded_reason="non_drawing_asset", parent_input_id="1f_view",
        )


# --------------------------------------------------------------------------- #
# claims vocabulary
# --------------------------------------------------------------------------- #
def test_opening_evidence_rejects_unknown_claim():
    with pytest.raises(ValidationError):
        OpeningEvidence(potentially_observable_claims=["existence", "bogus_claim"])


def test_opening_evidence_dedups_and_sorts_claims():
    ev = OpeningEvidence(potentially_observable_claims=["width", "existence", "width", "along"])
    assert ev.potentially_observable_claims == ["along", "existence", "width"]


# --------------------------------------------------------------------------- #
# ViewManifest top-level: canonical sort + dup detection
# --------------------------------------------------------------------------- #
def _minimal_manifest(entries: list) -> dict:
    return dict(
        claims_vocab_version=CLAIMS_VOCAB_VERSION,
        case_id="synth",
        case_metadata_sha256=HEX64_A,
        entries=entries,
        content_sha256=HEX64_B,
    )


def test_entries_must_be_sorted_by_input_id():
    a = _plan_entry(input_id="b_view", expected_output_id="b_view")
    b = _plan_entry(input_id="a_view", expected_output_id="a_view", floor_ref=2)
    with pytest.raises(ValidationError):
        ViewManifest(**_minimal_manifest([a, b]))
    ViewManifest(**_minimal_manifest([b, a]))  # sorted order is fine


def test_duplicate_input_id_rejected():
    a = _plan_entry(input_id="1f_view")
    b = _plan_entry(input_id="1f_view", floor_ref=2)
    with pytest.raises(ValidationError):
        ViewManifest(**_minimal_manifest([a, b]))


def test_content_hash_excludes_itself_and_is_recomputable():
    m = ViewManifest(**_minimal_manifest([_plan_entry()]))
    recomputed = compute_content_hash(m)
    tampered = m.model_copy(update={"case_id": "different"})
    assert compute_content_hash(tampered) != recomputed
    # content_sha256 field itself never participates in its own hash
    same_except_hash = m.model_copy(update={"content_sha256": "f" * 64})
    assert compute_content_hash(same_except_hash) == recomputed


# --------------------------------------------------------------------------- #
# §3.6 CompletenessAssertion wire — three source positives
# --------------------------------------------------------------------------- #
def _coverage_and_assertion(source_ref, *, frame="plan_floor_region", region="full_floor"):
    assertion = CompletenessAssertion(assertion_id="A1", source_ref=source_ref)
    coverage = Coverage(frame=frame, region=region, completeness_assertion_id="A1")
    return coverage, assertion


def test_completeness_source_case_metadata_positive():
    ref = CaseMetadataSourceRef(
        source="case_metadata", json_pointer="/views/1f_view/completeness", case_metadata_sha256=HEX64_A
    )
    coverage, assertion = _coverage_and_assertion(ref)
    ev = OpeningEvidence(
        potentially_observable_claims=["existence", "host", "along", "width"],
        negative_evidence_capable_claims=["existence"],
        coverage=coverage,
        completeness_assertion=assertion,
    )
    assert ev.completeness_assertion.source_ref.source == "case_metadata"


def test_completeness_source_user_positive():
    ref = UserSourceRef(source="user", content_sha256=HEX64_A)
    coverage, assertion = _coverage_and_assertion(ref)
    ev = OpeningEvidence(
        potentially_observable_claims=["existence"],
        negative_evidence_capable_claims=["existence"],
        coverage=coverage,
        completeness_assertion=assertion,
    )
    assert ev.completeness_assertion.source_ref.source == "user"


def test_completeness_source_dataset_ref_positive():
    ref = DatasetSourceRef(
        source="dataset_ref",
        dataset_id="knowledge/window_modules", dataset_version="1", contract_id="c1",
        content_sha256=HEX64_A,
    )
    coverage, assertion = _coverage_and_assertion(ref, frame="elevation_local_along", region="full_facade")
    ev = OpeningEvidence(
        potentially_observable_claims=["existence", "along"],
        negative_evidence_capable_claims=["along"],
        coverage=coverage,
        completeness_assertion=assertion,
    )
    assert ev.completeness_assertion.source_ref.source == "dataset_ref"


# --------------------------------------------------------------------------- #
# §3.6 five negatives + the coverage-unknown-field r5 fix
# --------------------------------------------------------------------------- #
def test_negative_dangling_assertion_id():
    ref = UserSourceRef(source="user", content_sha256=HEX64_A)
    assertion = CompletenessAssertion(assertion_id="A1", source_ref=ref)
    coverage = Coverage(frame="plan_floor_region", region="full_floor", completeness_assertion_id="A2-DANGLING")
    with pytest.raises(ValidationError):
        OpeningEvidence(
            potentially_observable_claims=["existence"],
            negative_evidence_capable_claims=["existence"],
            coverage=coverage,
            completeness_assertion=assertion,
        )


def test_negative_wrong_frame_region_pairing():
    ref = UserSourceRef(source="user", content_sha256=HEX64_A)
    coverage, assertion = _coverage_and_assertion(ref, frame="plan_floor_region", region="full_facade")
    with pytest.raises(ValidationError):
        OpeningEvidence(
            potentially_observable_claims=["existence"],
            negative_evidence_capable_claims=["existence"],
            coverage=coverage,
            completeness_assertion=assertion,
        )


def test_negative_negative_claims_not_subset_of_observable():
    ref = UserSourceRef(source="user", content_sha256=HEX64_A)
    coverage, assertion = _coverage_and_assertion(ref)
    with pytest.raises(ValidationError):
        OpeningEvidence(
            potentially_observable_claims=["existence"],
            negative_evidence_capable_claims=["existence", "sill"],  # sill not observable here
            coverage=coverage,
            completeness_assertion=assertion,
        )


def test_negative_empty_nonempty_linkage_broken():
    ref = UserSourceRef(source="user", content_sha256=HEX64_A)
    coverage, assertion = _coverage_and_assertion(ref)
    # negative claims non-empty but coverage/assertion absent
    with pytest.raises(ValidationError):
        OpeningEvidence(
            potentially_observable_claims=["existence"],
            negative_evidence_capable_claims=["existence"],
        )
    # coverage/assertion present but negative claims empty
    with pytest.raises(ValidationError):
        OpeningEvidence(
            potentially_observable_claims=["existence"],
            negative_evidence_capable_claims=[],
            coverage=coverage,
            completeness_assertion=assertion,
        )


def test_negative_dataset_ref_content_hash_malformed():
    """"dataset 原地换内容（hash 不符）" at the wire level: content_sha256 is the
    identity-binding field for a dataset_ref (§3.6) — a malformed/wrong-shaped
    hash is rejected structurally. (Verifying that a *reused* dataset_id at a
    *different* content_sha256 is treated as changed content is a consumer-side
    concern — B4b — this module only owns the typed wire, not that policy.)"""
    with pytest.raises(ValidationError):
        DatasetSourceRef(
            source="dataset_ref",
            dataset_id="knowledge/window_modules", dataset_version="1", contract_id="c1",
            content_sha256="deadbeef",
        )


def test_coverage_rejects_unknown_field_no_bare_source_ref():
    """r5 fix: coverage has no independent source declaration — any attempt to
    smuggle a source-like field onto Coverage is an unknown-field hard rejection
    (extra="forbid"), not silently ignored."""
    with pytest.raises(ValidationError):
        Coverage(
            frame="plan_floor_region", region="full_floor", completeness_assertion_id="A1",
            source_ref={"source": "user", "content_sha256": HEX64_A},
        )
    with pytest.raises(ValidationError):
        Coverage(
            frame="plan_floor_region", region="full_floor", completeness_assertion_id="A1",
            source="user",
        )
