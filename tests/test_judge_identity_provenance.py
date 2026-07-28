"""Slice 1 locks for source-preserving judge identity (C-L2..C-L13)."""
from __future__ import annotations

import copy
import hashlib
import shutil
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agent.correction.geometry_validator import validate_corrected_geometry
from src.agent.correction.schema import (
    CellV3,
    CorrectedGeometryV3,
    FloorV3,
    FootprintRing,
)
from src.agent.judge.gt import load_gt_document
from src.agent.judge.identity_provenance import (
    IDENTITY_CONTRACT_VERSION,
    IDENTITY_ERROR_CONTEXT_KEYS,
    CoordinateOccurrence,
    CoordinateSourceKey,
    IdentityInputEnvelope,
    SourceTopologyIndex,
    adapt_correction_floor,
    adapt_reading_floor,
    certify_alias,
)
from src.agent.judge.score_schema import ScoreContractError
from src.agent.judge import segment_score


def _key(
    owner: str,
    *,
    owner_kind: str = "cell",
    index: int = 0,
    axis: str = "x",
) -> CoordinateSourceKey:
    return CoordinateSourceKey(
        "product", "F", owner_kind, owner, "exterior", index, None, axis
    )


def _envelope(
    occurrences,
    *,
    contract_version: object = IDENTITY_CONTRACT_VERSION,
    topology: SourceTopologyIndex | None = None,
) -> IdentityInputEnvelope:
    return IdentityInputEnvelope(
        contract_version=contract_version,
        source_schema="correction_v3",
        side="product",
        floor_id="F",
        occurrences=tuple(occurrences),
        topology=topology or SourceTopologyIndex.empty(side="product", floor_id="F"),
    )


def _typed_correction(cells, footprint, *, floor_id="F"):
    floor = FloorV3(
        id=floor_id,
        name=floor_id,
        z_floor=0.0,
        ceiling_height=3.0,
        footprint=FootprintRing(vertices=footprint),
        cells=cells,
    )
    xs = [float(point[0]) for point in footprint]
    ys = [float(point[1]) for point in footprint]
    return CorrectedGeometryV3(
        schema_version="3",
        footprint_x=[min(xs), max(xs)],
        footprint_y=[min(ys), max(ys)],
        floors=[floor],
    )


def _occurrence(key, value, use_site="lock"):
    return CoordinateOccurrence.make(key, value, use_site)


def test_c_l2_same_source_spread_rejects_with_hex_and_diameter():
    key = _key("A")
    values = (1.0, 1.0 + 2e-12)
    with pytest.raises(ScoreContractError) as caught:
        segment_score._build_floor_identity(
            _envelope(_occurrence(key, value, str(index))
                      for index, value in enumerate(values))
        )
    error = caught.value
    assert error.code == "score_identity_contract_mismatch"
    assert error.context["reason"] == "same_source_coordinate_spread"
    assert error.context["source_vertex_ids"] == (key.audit_tuple(),)
    assert error.context["original_hex"] == tuple(value.hex() for value in values)
    assert error.context["diameter_hex"] == (values[1] - values[0]).hex()


def test_c_l3_guard_band_names_both_source_keys():
    left, right = _key("A"), _key("B")
    with pytest.raises(ScoreContractError) as caught:
        segment_score._build_floor_identity(_envelope((
            _occurrence(left, 1.0),
            _occurrence(right, 1.0 + 3e-12),
        )))
    error = caught.value
    assert error.code == "score_identity_guard_band_ambiguity"
    assert error.context["source_keys"] == (
        left.audit_tuple(), right.audit_tuple()
    )
    assert error.context["gap_hex"] == (3e-12 + 1.0 - 1.0).hex()


def _paired_correction(left_constant: float, right_constant: float):
    cells = [
        CellV3(
            id="A", role="office", x=[0.0, left_constant], y=[0.0, 1.0],
            polygon=[
                [0.0, 0.0], [left_constant, 0.0],
                [left_constant, 1.0], [0.0, 1.0],
            ],
        ),
        CellV3(
            id="B", role="office", x=[right_constant, 2.0], y=[0.0, 1.0],
            polygon=[
                [right_constant, 0.0], [2.0, 0.0],
                [2.0, 1.0], [right_constant, 1.0],
            ],
        ),
    ]
    return _typed_correction(
        cells, [[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]]
    )


def _unequal_certificates(document, left_value, right_value):
    values = {occ.source_key: occ.value for occ in document.envelope.occurrences}
    return [
        certificate
        for certificate in document.envelope.topology.certificates.values()
        if values.get(certificate.left) is not None
        and values.get(certificate.right) is not None
        and {
            values[certificate.left],
            values[certificate.right],
        } == {left_value, right_value}
    ]


def test_c_l4_sm24_drift_has_paired_certificate_and_extracts():
    variant = copy.deepcopy(load_gt_document("sm24_anchor"))
    z1 = next(zone for zone in variant.floors[0].zones if zone.id == "z1")
    for index, vertex in enumerate(z1.polygon.exterior.vertices):
        if float(vertex[1]) == 8.059999999999999:
            z1.polygon.exterior.vertices[index] = [float(vertex[0]), 8.06]
    document = segment_score.adapt_gt_floor(variant.floors[0])
    certificates = _unequal_certificates(
        document, 8.059999999999999, 8.06
    )
    assert certificates
    assert {certificate.kind for certificate in certificates} == {
        "paired_edge_endpoint"
    }
    segments = segment_score.extract_gt_plan_segments(variant)
    assert len([segment for segment in segments if not segment.exterior]) == 16


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (0.1 + 0.2, 0.3),
        (
            math.nextafter(1.0 + 0.5e-12, -math.inf),
            math.nextafter(1.0 + 0.5e-12, math.inf),
        ),
    ],
)
def test_c_l4_formal_reverse_edge_alias_is_structural_not_distance(left, right):
    assert left != right and abs(left - right) < 1e-12
    geometry = _paired_correction(left, right)
    document = adapt_correction_floor(geometry.floors[0])
    certificates = _unequal_certificates(document, left, right)
    assert certificates
    assert all(item.kind == "paired_edge_endpoint" for item in certificates)
    extracted = segment_score.extract_correction_plan_segments(geometry)
    assert len([segment for segment in extracted if not segment.exterior]) == 1

    certificate = certificates[0]
    assert certify_alias(
        certificate.left, certificate.right, "x", document.envelope.topology
    ) == certificate
    far_occurrences = tuple(
        replace(
            occurrence,
            value=10.0 if occurrence.source_key == certificate.left else (
                20.0 if occurrence.source_key == certificate.right
                else occurrence.value
            ),
            value_hex=(
                10.0.hex() if occurrence.source_key == certificate.left else
                20.0.hex() if occurrence.source_key == certificate.right else
                occurrence.value_hex
            ),
        )
        for occurrence in document.envelope.occurrences
    )
    far_envelope = replace(document.envelope, occurrences=far_occurrences)
    x_identity, _ = segment_score._build_floor_identity(far_envelope)
    assert x_identity.rep[certificate.left] != x_identity.rep[certificate.right]
    assert certify_alias(
        certificate.left, certificate.right, "x", document.envelope.topology
    ) == certificate


def test_c_l5_unrelated_submerge_sources_reject_without_structural_relation():
    left, right = _key("A"), _key("B")
    with pytest.raises(ScoreContractError) as caught:
        segment_score._build_floor_identity(_envelope((
            _occurrence(left, 5.0),
            _occurrence(right, 5.0 + 5e-13),
        )))
    error = caught.value
    assert error.code == "score_identity_contract_mismatch"
    assert error.context["reason"] == "unproven_cross_source_alias"
    assert error.context["candidate_pair"] == (
        left.audit_tuple(), right.audit_tuple()
    )
    assert error.context["structural_relation"] == "none"


def test_c_l6_ring_collapse_context_is_recomputable():
    geometry = _typed_correction(
        [
            CellV3(
                id="Z", role="office", x=[0.0, 1.0], y=[0.0, 1.0],
                polygon=[
                    [0.0, 0.0], [5e-13, 0.0], [1.0, 0.0],
                    [1.0, 1.0], [0.0, 1.0],
                ],
            )
        ],
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
    )
    with pytest.raises(ScoreContractError) as caught:
        segment_score.extract_correction_plan_segments(geometry)
    context = caught.value.context
    assert caught.value.code == "score_identity_merge_collapse"
    assert {"source_keys", "v1_hex", "v2_hex", "diameter_hex"} <= context.keys()
    assert IDENTITY_ERROR_CONTEXT_KEYS <= context.keys()


def test_c_l6_postmerge_ring_validator_is_independently_load_bearing():
    geometry = _typed_correction(
        [
            CellV3(
                id="Z", role="office", x=[0.0, 1.0], y=[0.0, 1.0],
                polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            )
        ],
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
    )
    document = adapt_correction_floor(geometry.floors[0])
    x_identity, y_identity = segment_score._build_floor_identity(document.envelope)
    ring = next(item for item in document.rings if item.owner_kind == "cell")
    forced = dict(x_identity.rep)
    forced[ring.vertices[1].x_source] = forced[ring.vertices[0].x_source]
    with pytest.raises(ScoreContractError) as caught:
        segment_score._points(
            ring, replace(x_identity, rep=forced), y_identity,
            identity_code="score_product_identity_invalid",
        )
    assert caught.value.code == "score_identity_merge_collapse"
    assert caught.value.context["reason"] == "identity_merge_edge_collapse"


def test_c_l8_bow_tie_from_formal_adapter_is_certified_red():
    geometry = _typed_correction(
        [
            CellV3(
                id="Z", role="office", x=[0.0, 2.0], y=[0.0, 2.0],
                polygon=[[0.0, 0.0], [2.0, 2.0], [0.0, 2.0], [2.0, 0.0]],
            )
        ],
        [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]],
    )
    with pytest.raises(ScoreContractError) as caught:
        segment_score.extract_correction_plan_segments(geometry)
    assert caught.value.code == "score_product_identity_invalid"
    assert caught.value.context["reason"] == "ring_nonadjacent_edge_intersection"
    assert caught.value.context["source_edge_ids"]


def test_c_l9_same_owner_reverse_atom_is_contract_conflict():
    with pytest.raises(ScoreContractError) as caught:
        segment_score._assert_owner_atom(
            ("cell", "Z"), ("cell", "Z"), floor_id="F",
            source_edge_ids=(("edge", 1), ("edge", 2)),
        )
    assert caught.value.code == "score_identity_contract_mismatch"
    assert caught.value.context["predicate"] == "owner_atom_multiplicity"
    assert caught.value.context["owner_identities"] == (
        ("cell", "Z"), ("cell", "Z")
    )


def test_c_l10_boundary_duplicate_after_merge_carries_four_raw_endpoints():
    ring = SimpleNamespace(
        exterior=SimpleNamespace(
            vertices=[(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
        ),
        interior_rings=[],
    )
    source_ref = SimpleNamespace(view_id="plan")
    interval = SimpleNamespace(lo=0.0, hi=2.0)
    boundary_common = {
        "source_refs": (source_ref,),
        "boundary_loop_id": "exterior",
        "source_footprint_fingerprint": "f" * 64,
        "facade_family": "South",
        "outward_normal": (0, -1),
        "world_along_interval": interval,
    }
    boundaries = [
        SimpleNamespace(id="b1", p1=(0.0, 5e-13), p2=(2.0, 5e-13),
                        **boundary_common),
        SimpleNamespace(id="b2", p1=(2.0, 9e-13), p2=(0.0, 9e-13),
                        **boundary_common),
    ]
    zone = SimpleNamespace(id="Z", polygon=ring)
    floor = SimpleNamespace(
        id="F", footprint=ring, zones=[zone], boundary_segments=boundaries
    )
    with pytest.raises(ScoreContractError) as caught:
        segment_score.extract_gt_plan_segments(SimpleNamespace(floors=[floor]))
    context = caught.value.context
    assert context["reason"] == "identity_boundary_duplicate_after_merge"
    assert len(context["raw_endpoints"]) == 4
    assert len(context["endpoint_hex"]) == 4
    assert len(context["source_keys"]) == 8


def test_c_l11_contract_version_is_exact_string_without_coercion():
    for invalid in ("2", 2):
        with pytest.raises(ScoreContractError) as caught:
            segment_score._build_floor_identity(
                _envelope((), contract_version=invalid)
            )
        assert caught.value.context["expected_contract_version"] == "1"
        assert caught.value.context["observed_contract_version"] == invalid


def test_c_l12_duplicate_reading_id_rejects_in_adapter():
    rows = [
        segment_score.PlanSegment("R", "F", (0.0, 0.0), (1.0, 0.0)),
        segment_score.PlanSegment("R", "F", (0.0, 1.0), (1.0, 1.0)),
    ]
    with pytest.raises(ScoreContractError) as caught:
        adapt_reading_floor("F", rows)
    assert caught.value.code == "score_identity_contract_mismatch"
    assert caught.value.context["reason"] == "duplicate_reading_id"


def test_c_l13_generic_nonorthogonal_concave_passes_and_bow_tie_rejects():
    concave = _typed_correction(
        [
            CellV3(
                id="Z", role="office", x=[0.0, 3.0], y=[0.0, 3.0],
                polygon=[
                    [0.0, 0.0], [3.0, 0.0], [2.0, 1.0],
                    [3.0, 3.0], [0.0, 3.0],
                ],
            )
        ],
        [[0.0, 0.0], [3.0, 0.0], [3.0, 3.0], [0.0, 3.0]],
    )
    document = adapt_correction_floor(concave.floors[0])
    x_identity, y_identity = segment_score._build_floor_identity(document.envelope)
    ring = next(item for item in document.rings if item.owner_kind == "cell")
    assert len(segment_score._points(
        ring, x_identity, y_identity,
        identity_code="score_product_identity_invalid",
    )) == 5

    bow_tie = replace(
        ring,
        vertices=(
            ring.vertices[0], ring.vertices[3],
            ring.vertices[4], ring.vertices[1],
        ),
    )
    with pytest.raises(ScoreContractError) as caught:
        segment_score._points(
            bow_tie, x_identity, y_identity,
            identity_code="score_product_identity_invalid",
        )
    assert caught.value.context["reason"] == "ring_nonadjacent_edge_intersection"


def test_owner_identity_uses_kind_and_id_when_cell_id_equals_floor_id():
    geometry = _typed_correction(
        [
            CellV3(
                id="F", role="office", x=[0.0, 2.0], y=[0.0, 1.0],
                polygon=[[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]],
            )
        ],
        [[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]],
    )
    document = adapt_correction_floor(geometry.floors[0])
    assert {ring.owner for ring in document.rings} == {
        ("footprint", "F"), ("cell", "F")
    }
    assert len(segment_score.extract_correction_plan_segments(geometry)) == 4


def test_production_adapters_never_enter_legacy_float_cluster(monkeypatch):
    def bomb(*_args, **_kwargs):
        raise AssertionError("production collapsed back to raw float identity")

    monkeypatch.setattr(segment_score, "_cluster_legacy_axis", bomb)
    geometry = _paired_correction(0.1 + 0.2, 0.3)
    segment_score.extract_correction_plan_segments(geometry)
    segment_score.coerce_plan_observations([
        {"id": "R", "floor_id": "F", "p1": [0.0, 0.0], "p2": [1.0, 0.0]}
    ])
    gt = load_gt_document("sm24_anchor")
    segment_score.extract_gt_plan_segments(gt)


def test_c_l15_sm21_score_pixels_and_dispatch_do_not_instantiate_new_adapter(
    tmp_path, monkeypatch
):
    import scripts.tool_scripts.run_stage as run_stage
    from src.agent.judge.gt import load_gt
    from src.agent.judge import identity_provenance

    source = Path(
        "case_tests/e2e_tests/sm21_anchor/"
        "run_2026-06-20_gpt54_reading/0_reading/attempts/002/output.json"
    )
    baseline_dir = tmp_path / "baseline" / "002"
    bombed_dir = tmp_path / "bombed" / "002"
    baseline_dir.mkdir(parents=True)
    bombed_dir.mkdir(parents=True)
    shutil.copy2(source, baseline_dir / "output.json")
    shutil.copy2(source, bombed_dir / "output.json")
    gt = load_gt("sm21_anchor")

    run_stage._grade_attempt_artifacts(
        "0_reading", "sm21_anchor", baseline_dir, gt,
        grade=run_stage.GradeConfig(),
    )
    expected_score = (baseline_dir / "score_vs_gt.json").read_bytes()
    expected_pixels = hashlib.sha256(
        (baseline_dir / "grade.png").read_bytes()
    ).hexdigest()

    def bomb(*_args, **_kwargs):
        raise AssertionError("sm21 legacy dispatch instantiated identity adapter")

    for name in ("adapt_gt_floor", "adapt_correction_floor", "adapt_reading_floor"):
        monkeypatch.setattr(identity_provenance, name, bomb)
        monkeypatch.setattr(segment_score, name, bomb)
    run_stage._grade_attempt_artifacts(
        "0_reading", "sm21_anchor", bombed_dir, gt,
        grade=run_stage.GradeConfig(),
    )
    assert (bombed_dir / "score_vs_gt.json").read_bytes() == expected_score
    assert hashlib.sha256(
        (bombed_dir / "grade.png").read_bytes()
    ).hexdigest() == expected_pixels
