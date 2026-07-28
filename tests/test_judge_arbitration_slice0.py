"""Slice 0 red locks for judge arbitration, conservation, and provenance.

These tests deliberately state the destination contract before the production
implementation exists.  On the cce6e83 baseline every test in this module must
be RED.  A green test is a construction stop condition.
"""
from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

from src.agent.correction.geometry_validator import validate_corrected_geometry
from src.agent.correction.footprint import footprint_fingerprint
from src.agent.correction.schema import CellV3, CorrectedGeometryV3, FloorV3, FootprintRing
from src.agent.judge.gt_schema import (
    GtBoundarySegmentV3,
    GtEntityRefV3,
    GtFloorV3,
    GtPolygonV3,
    GtRingV3,
    GtWorldIntervalV3,
    GtZoneV3,
)
from src.agent.judge.score_schema import JudgeScoreConfigV1, ScoreContractError
from src.agent.judge import segment_score


def _config() -> JudgeScoreConfigV1:
    return JudgeScoreConfigV1(
        schema_version="1",
        plan_axis_alignment_tol_m=0.05,
        plan_position_tol_m=0.3,
        plan_extent_tol_m=0.3,
        claim_complete_epsilon_m=0.05,
        opening_match_center_tol_m=0.4,
        opening_assignment_tie_epsilon=1e-9,
        along_claim_tol_m=0.4,
        width_claim_tol_m=0.4,
        sill_claim_tol_m=0.3,
        head_claim_tol_m=0.3,
        floor_line_tol_m=0.3,
    )


def _gt_floor(fid: str, footprint, zones):
    ring = SimpleNamespace(exterior=SimpleNamespace(vertices=footprint))
    return SimpleNamespace(
        id=fid,
        footprint=ring,
        boundary_segments=(),
        zones=[
            SimpleNamespace(
                id=zone_id,
                polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=polygon)),
            )
            for zone_id, polygon in zones
        ],
    )


def _typed_correction(
    cells: list[CellV3],
    footprint_vertices: list[list[float]],
    *,
    floor_id: str = "F",
) -> CorrectedGeometryV3:
    floor = FloorV3(
        id=floor_id,
        name=floor_id,
        z_floor=0.0,
        ceiling_height=3.0,
        footprint=FootprintRing(vertices=footprint_vertices),
        cells=cells,
    )
    xs = [point[0] for point in footprint_vertices]
    ys = [point[1] for point in footprint_vertices]
    return CorrectedGeometryV3(
        schema_version="3",
        footprint_x=[min(xs), max(xs)],
        footprint_y=[min(ys), max(ys)],
        floors=[floor],
    )


def _typed_gt_three_adjacent_spans(
    x0: float,
    x1: float,
    x2: float,
    x3: float,
):
    """Build the B-L4 shape as real GroundTruthV3 nested models."""
    from tests.b4b_contract_fixture import make_b4b_gt_document

    base = make_b4b_gt_document()
    base_ref = base.floors[0].zones[0].source_refs[0].model_dump(mode="python")

    def source_ref(role: str) -> GtEntityRefV3:
        return GtEntityRefV3.model_validate({**base_ref, "role": role})

    footprint = [[x0, 0.0], [x3, 0.0], [x3, 2.0], [x0, 2.0]]
    fingerprint = footprint_fingerprint(footprint)
    zone_rows = (
        ("U", [[x0, 1.0], [x3, 1.0], [x3, 2.0], [x0, 2.0]]),
        ("L0", [[x0, 0.0], [x1, 0.0], [x1, 1.0], [x0, 1.0]]),
        ("L1", [[x1, 0.0], [x2, 0.0], [x2, 1.0], [x1, 1.0]]),
        ("L2", [[x2, 0.0], [x3, 0.0], [x3, 1.0], [x2, 1.0]]),
    )
    zones = [
        GtZoneV3(
            id=zone_id,
            name=zone_id,
            role="office",
            polygon=GtPolygonV3(
                exterior=GtRingV3(vertices=vertices),
                interior_rings=[],
            ),
            source_refs=[source_ref("zone_boundary")],
        )
        for zone_id, vertices in zone_rows
    ]
    boundary_specs = (
        ("South", [x0, 0.0], [x3, 0.0], [0, -1], x0, x3),
        ("East", [x3, 0.0], [x3, 2.0], [1, 0], 0.0, 2.0),
        ("North", [x3, 2.0], [x0, 2.0], [0, 1], x0, x3),
        ("West", [x0, 2.0], [x0, 0.0], [-1, 0], 0.0, 2.0),
    )
    boundaries = [
        GtBoundarySegmentV3(
            id=f"F:boundary:{family}",
            floor_id="F",
            boundary_loop_id="exterior",
            facade_family=family,
            p1=p1,
            p2=p2,
            outward_normal=normal,
            world_along_interval=GtWorldIntervalV3(lo=lo, hi=hi),
            depth=0.0,
            visible_intervals=[],
            source_footprint_fingerprint=fingerprint,
            projection_surface_keys=[],
            wall_thickness_m=None,
            source_refs=[source_ref("footprint_boundary")],
        )
        for family, p1, p2, normal, lo, hi in boundary_specs
    ]
    floor = GtFloorV3(
        id="F",
        name="F",
        z_floor_m=0.0,
        ceiling_height_m=3.0,
        footprint=GtPolygonV3(
            exterior=GtRingV3(vertices=footprint),
            interior_rings=[],
        ),
        footprint_fingerprint=fingerprint,
        zones=zones,
        boundary_segments=boundaries,
    )
    return base.model_copy(update={"floors": [floor], "openings": []})


def _source_key_tuple(key) -> tuple:
    return (
        key.side,
        key.floor_id,
        key.owner_kind,
        key.owner_id,
        key.ring_id,
        key.element_index,
        key.endpoint_side,
        key.axis,
    )


def test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red():
    """A-L3: an unrelated capability may not wash a fixed duplicate into NA."""
    width = height = 0.1
    lean = 5e-10
    footprint = [[0.0, 0.0], [width, 0.0], [width, height], [0.0, height]]
    geometry = _typed_correction(
        [
            CellV3(id="A", role="office", x=[0.0, width], y=[0.0, height], polygon=footprint),
            CellV3(id="B", role="office", x=[0.0, width], y=[0.0, height], polygon=footprint),
            CellV3(
                id="C",
                role="office",
                x=[0.0, 0.05 + lean],
                y=[0.0, height],
                polygon=[[0.0, 0.0], [0.05, 0.0], [0.05 + lean, height], [0.0, height]],
            ),
        ],
        footprint,
    )
    findings = validate_corrected_geometry(geometry)
    assert len(findings) == 5
    assert all(finding.ok for finding in findings)

    with pytest.raises(ScoreContractError) as caught:
        segment_score.extract_correction_plan_segments(geometry)

    error = caught.value
    assert error.code == "score_product_identity_invalid"
    assert error.gate_id == "scoring.input_identity"
    assert error.context["reason"] == "exterior_duplicate_owner"
    assert error.context["authority"] == "scoring_identity"
    assert error.context["proof_status"] == "CERTIFIED_CONFLICT"
    assert error.context["predicate"] == "owner_multiplicity"
    assert error.context["predicate_schema_version"] == "1"
    assert tuple(error.context["owner_ids"]) == ("A", "B")
    assert tuple(error.context["depends_on_capability_ids"]) == ()
    fixed_edges = tuple(error.context["source_edge_ids"])
    assert fixed_edges
    assert all(any(owner in repr(edge) for owner in ("A", "B")) for edge in fixed_edges)
    assert all("C" not in repr(edge) for edge in fixed_edges)


def test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths(caplog):
    """A-L9: missing predicate evaluators are fail-safe but never invisible."""
    certifier = importlib.import_module("src.agent.judge.certifier")
    ConflictWitness = certifier.ConflictWitness
    JudgeDiagnostic = certifier.JudgeDiagnostic
    certify_and_arbitrate_request = certifier.certify_and_arbitrate_request

    unknown = JudgeDiagnostic(
        diagnostic_id="diag-unknown",
        requested_code="score_product_identity_invalid",
        gate_id="scoring.input_identity",
        reason="novel detector reason",
        floor_id="F",
        witness=ConflictWitness(
            predicate="novel_topology_predicate",
            predicate_schema_version="1",
            source_edge_ids=(("product", "F", "edge", "U"),),
            source_vertex_ids=(("product", "F", "vertex", "U", 0),),
            owner_ids=("U",),
            locus=((0.0, 0.0), (1.0, 0.0)),
        ),
        caused_by=(),
    )
    duplicate = JudgeDiagnostic(
        diagnostic_id="diag-duplicate",
        requested_code="score_product_identity_invalid",
        gate_id="scoring.input_identity",
        reason="exterior_duplicate_owner",
        floor_id="F",
        witness=ConflictWitness(
            predicate="owner_multiplicity",
            predicate_schema_version="1",
            source_edge_ids=(
                ("product", "F", "edge", "A"),
                ("product", "F", "edge", "B"),
            ),
            source_vertex_ids=(),
            owner_ids=("A", "B"),
            locus=((0.0, 0.0), (1.0, 0.0)),
        ),
        caused_by=(),
    )

    def records(event: str):
        return [record for record in caplog.records if getattr(record, "event", None) == event]

    with caplog.at_level("INFO", logger="src.agent.judge.certifier"):
        with pytest.raises(ScoreContractError) as caught:
            certify_and_arbitrate_request(
                diagnostics=(unknown,),
                capabilities=(),
                evaluator_registry={},
                request_key="request-na",
                identity_code="score_product_identity_invalid",
            )
    assert caught.value.code == "score_unsupported_combination"
    assert caught.value.context["reason"] == "diagnostic_evidence_incomplete"
    item_events = records("judge_certifier_missing_evaluator")
    summaries = records("judge_certifier_missing_evaluator_summary")
    assert len(item_events) == 1
    assert item_events[0].diagnostic_id == "diag-unknown"
    assert len(summaries) == 1
    assert summaries[0].missing_predicate_evaluator_count == 1
    assert summaries[0].predicate_histogram == (("novel_topology_predicate", "1", 1),)
    assert summaries[0].diagnostic_ids == ("diag-unknown",)
    assert summaries[0].final_outcome == "na"

    caplog.clear()

    def certify_duplicate(*_args, **_kwargs):
        return "CERTIFIED_CONFLICT"

    with caplog.at_level("INFO", logger="src.agent.judge.certifier"):
        with pytest.raises(ScoreContractError) as caught:
            certify_and_arbitrate_request(
                diagnostics=(unknown, duplicate),
                capabilities=(),
                evaluator_registry={("owner_multiplicity", "1"): certify_duplicate},
                request_key="request-red",
                identity_code="score_product_identity_invalid",
            )
    assert caught.value.code == "score_product_identity_invalid"
    summaries = records("judge_certifier_missing_evaluator_summary")
    assert len(records("judge_certifier_missing_evaluator")) == 1
    assert len(summaries) == 1
    assert summaries[0].missing_predicate_evaluator_count == 1
    assert summaries[0].predicate_histogram == (("novel_topology_predicate", "1", 1),)
    assert summaries[0].diagnostic_ids == ("diag-unknown",)
    assert summaries[0].final_outcome == "red"

    caplog.clear()

    def disprove_unknown(*_args, **_kwargs):
        return "DISPROVED"

    with caplog.at_level("INFO", logger="src.agent.judge.certifier"):
        certify_and_arbitrate_request(
            diagnostics=(unknown,),
            capabilities=(),
            evaluator_registry={("novel_topology_predicate", "1"): disprove_unknown},
            request_key="request-registered",
            identity_code="score_product_identity_invalid",
        )
    summaries = records("judge_certifier_missing_evaluator_summary")
    assert records("judge_certifier_missing_evaluator") == []
    assert len(summaries) == 1
    assert summaries[0].missing_predicate_evaluator_count == 0
    assert summaries[0].predicate_histogram == ()
    assert summaries[0].diagnostic_ids == ()
    assert summaries[0].final_outcome == "scored"


def test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger(monkeypatch):
    """B-L4: three exact neighbours tile one observation without 1-ulp overcharge."""
    x0 = 0.6615103026426206
    x1 = 10.189556344280527
    x2 = 16.84636437455466
    x3 = 21.523013020575195
    footprint = [[x0, 0.0], [x3, 0.0], [x3, 2.0], [x0, 2.0]]

    gt = _typed_gt_three_adjacent_spans(x0, x1, x2, x3)
    geometry = _typed_correction(
        [
            CellV3(
                id="U",
                role="office",
                x=[x0, x3],
                y=[1.0, 2.0],
                polygon=[[x0, 1.0], [x3, 1.0], [x3, 2.0], [x0, 2.0]],
            ),
            CellV3(
                id="L",
                role="office",
                x=[x0, x3],
                y=[0.0, 1.0],
                polygon=[[x0, 0.0], [x3, 0.0], [x3, 1.0], [x0, 1.0]],
            ),
        ],
        footprint,
    )
    findings = validate_corrected_geometry(geometry)
    assert len(findings) == 5
    assert all(finding.ok for finding in findings)

    all_targets = tuple(
        segment
        for segment in segment_score.extract_gt_plan_segments(gt)
        if not segment.exterior
    )
    targets = tuple(
        segment
        for segment in all_targets
        if segment.p1[1] == segment.p2[1] == 1.0
    )
    observations = tuple(
        segment
        for segment in segment_score.extract_correction_plan_segments(geometry)
        if not segment.exterior
    )
    target_spans = sorted(
        (min(segment.p1[0], segment.p2[0]), max(segment.p1[0], segment.p2[0]))
        for segment in targets
    )
    assert target_spans == [(x0, x1), (x1, x2), (x2, x3)]
    assert len(observations) == 1
    observation = observations[0]
    assert (min(observation.p1[0], observation.p2[0]), max(observation.p1[0], observation.p2[0])) == (x0, x3)

    # First run is intentionally uninstrumented so the current RED records the
    # actual 1-ulp production failure rather than an absent future audit seam.
    rows, observation_map = segment_score.match_plan_segments(
        targets=targets,
        observations=observations,
        config=_config(),
    )
    assert observation_map[observation.key] == tuple(sorted(segment.key for segment in targets))
    assert all(row.status != "extra" for row in rows)

    ledger_builder = getattr(segment_score, "_build_observation_ledger", None)
    assert callable(ledger_builder), "B-L4 requires the production observation-ledger seam"
    captured_ledgers = []

    def capture_ledger(*args, **kwargs):
        ledger = ledger_builder(*args, **kwargs)
        captured_ledgers.append(ledger)
        return ledger

    monkeypatch.setattr(segment_score, "_build_observation_ledger", capture_ledger)
    segment_score.match_plan_segments(
        targets=targets,
        observations=observations,
        config=_config(),
    )
    ledger = next(
        item
        for item in captured_ledgers
        if item.observation_key == observation.key
    )
    assert ledger.covered_exact == ledger.domain_exact
    assert ledger.extra_exact == 0
    assert all(len(atom.target_ids) == 1 for atom in ledger.atoms if atom.hi_exact > atom.lo_exact)


def test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity(monkeypatch):
    """C-L1: GT, correction, and reading occurrences reach clustering with provenance."""
    from tests.b4b_contract_fixture import make_b4b_gt_document

    original_cluster = segment_score._cluster_axis
    captured_occurrences = []
    captured_identities = []

    def capture_cluster(raw_values, *args, **kwargs):
        materialized = tuple(raw_values)
        captured_occurrences.extend(materialized)
        identity = original_cluster(materialized, *args, **kwargs)
        captured_identities.append(identity)
        return identity

    monkeypatch.setattr(segment_score, "_cluster_axis", capture_cluster)

    gt = make_b4b_gt_document()
    segment_score.extract_gt_plan_segments(gt)

    correction = _typed_correction(
        [
            CellV3(
                id="C",
                role="office",
                x=[0.0, 2.0],
                y=[0.0, 1.0],
                polygon=[[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]],
            )
        ],
        [[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]],
    )
    segment_score.extract_correction_plan_segments(correction)

    segment_score.coerce_plan_observations(
        [
            {
                "id": "R1",
                "floor_id": "F",
                "p1": [0.0, 0.0],
                "p2": [2.0, 0.0],
                "exterior": True,
            }
        ]
    )

    assert captured_occurrences
    assert all(
        hasattr(occurrence, "source_key")
        and hasattr(occurrence, "value")
        and occurrence.value_hex == float(occurrence.value).hex()
        for occurrence in captured_occurrences
    ), "C-L1: raw floats reached _cluster_axis before source identity was preserved"

    source_keys = {_source_key_tuple(occurrence.source_key) for occurrence in captured_occurrences}
    assert (
        "gt",
        "F1",
        "zone",
        "ZF1",
        "exterior",
        0,
        None,
        "x",
    ) in source_keys
    assert (
        "product",
        "F",
        "cell",
        "C",
        "exterior",
        0,
        None,
        "y",
    ) in source_keys
    assert (
        "product",
        "F",
        "reading",
        "R1",
        None,
        None,
        "p1",
        "x",
    ) in source_keys

    for identity in captured_identities:
        assert identity.rep
        assert all(hasattr(key, "owner_kind") for key in identity.rep)
        represented = {occurrence.source_key for occurrence in captured_occurrences}
        assert set(identity.rep).issubset(represented)


def test_c_l7_nonadjacent_duplicate_self_touch_is_certified_red():
    """C-L7: a repeated non-neighbour vertex cannot pair one owner with itself."""
    footprint = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
    ring = [
        [0.0, 0.0],
        [4.0, 0.0],
        [4.0, 4.0],
        [0.0, 4.0],
        [0.0, 2.0],
        [2.0, 2.0],
        [0.0, 2.0],
    ]
    geometry = _typed_correction(
        [CellV3(id="Z", role="office", x=[0.0, 4.0], y=[0.0, 4.0], polygon=ring)],
        footprint,
    )

    with pytest.raises(ScoreContractError) as caught:
        segment_score.extract_correction_plan_segments(geometry)

    error = caught.value
    assert error.code == "score_product_identity_invalid"
    assert error.gate_id == "scoring.input_identity"
    assert error.context["authority"] == "scoring_identity"
    assert error.context["proof_status"] == "CERTIFIED_CONFLICT"
    assert error.context["predicate"] == "ring_identity_conflict"
    assert tuple(error.context["owner_ids"]) == ("Z",)
    assert {tuple(vertex_id)[-1] for vertex_id in error.context["source_vertex_ids"]} >= {4, 6}
    assert error.context.get("zone_ids") != ("Z", "Z")


def test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder():
    """C-L11: a typed adapter cannot feed contract v2 into the v1 identity builder."""
    provenance = importlib.import_module("src.agent.judge.identity_provenance")
    envelope = provenance.IdentityInputEnvelope(
        contract_version="2",
        source_schema="correction_v3",
        side="product",
        floor_id="F",
        occurrences=(),
        topology=provenance.SourceTopologyIndex.empty(side="product", floor_id="F"),
    )

    with pytest.raises(ScoreContractError) as caught:
        segment_score._build_floor_identity(envelope)

    error = caught.value
    assert error.code == "score_identity_contract_mismatch"
    assert error.gate_id == "scoring.input_identity"
    assert error.context["reason"] == "identity_contract_version_mismatch"
    assert error.context["authority"] == "scoring_identity"
    assert error.context["expected_contract_version"] == "1"
    assert error.context["observed_contract_version"] == "2"
