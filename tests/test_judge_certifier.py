"""Slice 2 locks for proof-carrying request-level identity arbitration."""
from __future__ import annotations

import ast
import logging
from pathlib import Path

import pytest

from src.agent.correction.geometry_validator import validate_corrected_geometry
from src.agent.correction.schema import (
    CellV3,
    CorrectedGeometryV3,
    FloorV3,
    FootprintRing,
)
from src.agent.judge import segment_score
from src.agent.judge.certifier import (
    ConflictWitness,
    DEFAULT_EVALUATOR_REGISTRY,
    JudgeDiagnostic,
    ProofStatus,
    certify_and_arbitrate_request,
)
from src.agent.judge.score_schema import ScoreContractError


FOOTPRINT = [[0.0, 0.0], [4.0, 0.0], [4.0, 10.0], [0.0, 10.0]]


def _document(
    floor_id: str,
    cells: list[CellV3],
    footprint: list[list[float]] = FOOTPRINT,
) -> CorrectedGeometryV3:
    floor = FloorV3(
        id=floor_id,
        name=floor_id,
        z_floor=0.0,
        ceiling_height=3.0,
        footprint=FootprintRing(vertices=footprint),
        cells=cells,
    )
    xs = [point[0] for point in footprint]
    ys = [point[1] for point in footprint]
    return CorrectedGeometryV3(
        schema_version="3",
        footprint_x=[min(xs), max(xs)],
        footprint_y=[min(ys), max(ys)],
        floors=[floor],
    )


def _advisory_cells() -> list[CellV3]:
    return [
        CellV3(
            id="A",
            role="office",
            x=[0.0, 2.0 + 5e-10],
            y=[0.0, 10.0],
            polygon=[[0.0, 0.0], [2.0, 0.0], [2.0 + 5e-10, 10.0], [0.0, 10.0]],
        ),
        CellV3(
            id="B",
            role="office",
            x=[2.0, 4.0],
            y=[0.0, 10.0],
            polygon=[[2.0, 0.0], [4.0, 0.0], [4.0, 10.0], [2.0 + 4e-10, 10.0]],
        ),
    ]


def _gap_plus_advisory_cells() -> list[CellV3]:
    return [
        CellV3(
            id="A",
            role="office",
            x=[0.0, 2.0 + 5e-10],
            y=[0.0, 10.0],
            polygon=[[0.0, 0.0], [2.0, 0.0], [2.0 + 5e-10, 10.0], [0.0, 10.0]],
        ),
        CellV3(
            id="B",
            role="office",
            x=[2.0, 4.0],
            y=[0.0, 5.0],
            polygon=[[2.0, 0.0], [4.0, 0.0], [4.0, 5.0], [2.0, 5.0]],
        ),
        CellV3(
            id="C",
            role="office",
            x=[2.0, 4.0],
            y=[5.0 + 1e-9, 10.0],
            polygon=[
                [2.0, 5.0 + 1e-9],
                [4.0, 5.0 + 1e-9],
                [4.0, 10.0],
                [2.0, 10.0],
            ],
        ),
    ]


def _duplicate_with_advisory_cells() -> tuple[list[CellV3], list[list[float]]]:
    footprint = FOOTPRINT
    cells = [
        CellV3(id="A", role="office", x=[0.0, 4.0], y=[0.0, 10.0], polygon=footprint),
        CellV3(id="B", role="office", x=[0.0, 4.0], y=[0.0, 10.0], polygon=footprint),
        CellV3(
            id="C",
            role="office",
            x=[0.0, 2.0 + 5e-10],
            y=[0.0, 10.0],
            polygon=[[0.0, 0.0], [2.0, 0.0], [2.0 + 5e-10, 10.0], [0.0, 10.0]],
        ),
    ]
    return cells, footprint


def _caught(document: CorrectedGeometryV3) -> ScoreContractError:
    with pytest.raises(ScoreContractError) as caught:
        segment_score.extract_correction_plan_segments(document)
    return caught.value


def test_a_l1_advisory_derivative_is_contingent_with_replayable_fact_arcs():
    geometry = _document("F", _advisory_cells())
    assert all(item.ok for item in validate_corrected_geometry(geometry))
    error = _caught(geometry)
    assert error.code == "score_unsupported_combination"
    assert error.context["reason"] == "near_orthogonal_advisory_unpaired"
    assert error.context["capability_id"].startswith("w5:")
    arcs = error.context["dependency_arcs"]
    tags = {(parent[0], child[0]) for parent, child in arcs}
    assert ("source_coordinate", "edge_endpoint") in tags
    assert ("edge_endpoint", "cut_token") in tags
    assert ("cut_token", "owner_atom") in tags
    assert error.context["complete"] is True
    assert any(
        row[3] == "CONTINGENT"
        for row in error.context["diagnostic_audit"]
    )


def test_a_l2_fixed_gap_witness_is_disjoint_from_advisory_enclosure():
    geometry = _document("F", _gap_plus_advisory_cells())
    assert all(item.ok for item in validate_corrected_geometry(geometry))
    error = _caught(geometry)
    assert error.code == "score_product_identity_invalid"
    assert error.context["reason"] == "invalid_interior_edge_pair"
    assert error.context["proof_status"] == "CERTIFIED_CONFLICT"
    assert error.context["predicate"] == "missing_reverse_owner"
    assert error.context["source_edge_ids"]
    assert error.context["depends_on_capability_ids"] == ()
    assert all("A" not in repr(edge) for edge in error.context["source_edge_ids"])


@pytest.mark.parametrize("shape", ["advisory", "duplicate"])
def test_a_l4_cell_order_does_not_change_selected_certificate(shape: str):
    if shape == "advisory":
        cells, footprint = _advisory_cells(), FOOTPRINT
    else:
        cells, footprint = _duplicate_with_advisory_cells()
    first = _caught(_document("F", cells, footprint))
    second = _caught(_document("F", list(reversed(cells)), footprint))
    assert first.code == second.code
    assert first.gate_id == second.gate_id
    assert first.context == second.context


def test_a_l5_all_floors_report_before_request_arbitration():
    advisory = _document("F1", _advisory_cells()).floors[0]
    duplicate_cells, duplicate_footprint = _duplicate_with_advisory_cells()
    duplicate = _document("F2", duplicate_cells, duplicate_footprint).floors[0]

    def run(floors: list[FloorV3]) -> ScoreContractError:
        document = CorrectedGeometryV3(
            schema_version="3",
            footprint_x=[0.0, 4.0],
            footprint_y=[0.0, 10.0],
            floors=floors,
        )
        return _caught(document)

    forward = run([advisory, duplicate])
    reverse = run([duplicate, advisory])
    assert forward.code == reverse.code == "score_product_identity_invalid"
    assert forward.context == reverse.context
    assert forward.context["reason"] == "exterior_duplicate_owner"
    assert forward.context["floor_id"] == "F2"


def test_a_l6_missing_witness_is_na_without_missing_evaluator_count(caplog):
    diagnostic = JudgeDiagnostic(
        diagnostic_id="missing-witness",
        requested_code="score_product_identity_invalid",
        gate_id="scoring.input_identity",
        reason="brand_new_shape",
        floor_id="F",
        witness=None,
        side="product",
    )
    with caplog.at_level(logging.INFO, logger="src.agent.judge.certifier"):
        with pytest.raises(ScoreContractError) as caught:
            certify_and_arbitrate_request(
                diagnostics=(diagnostic,),
                capabilities=(),
                evaluator_registry=DEFAULT_EVALUATOR_REGISTRY,
                request_key="missing-witness-request",
                identity_code="score_product_identity_invalid",
            )
    assert caught.value.code == "score_unsupported_combination"
    assert caught.value.context["reason"] == "diagnostic_evidence_incomplete"
    assert caught.value.context["resolution"] == "missing_witness"
    assert caught.value.context["diagnostic_audit"] == (
        ("missing-witness", None, None, "UNPROVEN", "missing_witness"),
    )
    summaries = [
        record for record in caplog.records
        if getattr(record, "event", None)
        == "judge_certifier_missing_evaluator_summary"
    ]
    assert len(summaries) == 1
    assert summaries[0].missing_predicate_evaluator_count == 0
    assert summaries[0].final_outcome == "na"


def _root_diagnostics() -> tuple[JudgeDiagnostic, JudgeDiagnostic]:
    root_witness = ConflictWitness(
        predicate="exterior_interior_conflict",
        predicate_schema_version="1",
        source_edge_ids=(("edge", "root-a"), ("edge", "root-b")),
        source_vertex_ids=(),
        owner_ids=("A", "B"),
        locus=((0.0, 0.0), (1.0, 0.0)),
    )
    root = JudgeDiagnostic(
        diagnostic_id="located-root",
        requested_code="score_product_identity_invalid",
        gate_id="scoring.input_identity",
        reason="exterior_interior_topology_conflict",
        floor_id="F",
        witness=root_witness,
        side="product",
    )
    derivative = JudgeDiagnostic(
        diagnostic_id="dangling-derivative",
        requested_code="score_product_identity_invalid",
        gate_id="scoring.input_identity",
        reason="invalid_interior_edge_pair",
        floor_id="F",
        witness=ConflictWitness(
            predicate="missing_reverse_owner",
            predicate_schema_version="1",
            source_edge_ids=(("edge", "dangling"),),
            owner_ids=("C",),
            locus=((2.0, 0.0), (2.0, 1.0)),
            expected_reverse_slots=(("reverse", "dangling"),),
        ),
        caused_by=("located-root",),
        side="product",
    )
    return root, derivative


def test_a_l7_caused_by_root_is_stable_under_detector_order():
    root, derivative = _root_diagnostics()
    contexts = []
    for diagnostics in ((root, derivative), (derivative, root)):
        with pytest.raises(ScoreContractError) as caught:
            certify_and_arbitrate_request(
                diagnostics=diagnostics,
                capabilities=(),
                evaluator_registry=DEFAULT_EVALUATOR_REGISTRY,
                request_key="root-request",
                identity_code="score_product_identity_invalid",
            )
        contexts.append(caught.value.context)
    assert contexts[0] == contexts[1]
    assert contexts[0]["diagnostic_id"] == "located-root"
    assert contexts[0]["reason"] == "exterior_interior_topology_conflict"


def test_a_l8_red_request_keeps_advisory_log_with_capability_id(caplog):
    geometry = _document("F", _gap_plus_advisory_cells())
    with caplog.at_level(logging.INFO, logger="src.agent.judge.segment_score"):
        error = _caught(geometry)
    assert error.code == "score_product_identity_invalid"
    events = [
        record for record in caplog.records
        if getattr(record, "event", None)
        == "near_orthogonal_advisory_unpaired"
    ]
    assert events
    assert all(record.floor_id == "F" for record in events)
    assert all(record.capability_id.startswith("w5:") for record in events)
    assert all(record.p1_hex and record.p2_hex for record in events)


def test_registered_evaluator_result_is_a_closed_enum():
    diagnostic = JudgeDiagnostic(
        diagnostic_id="garbage-status",
        requested_code="score_product_identity_invalid",
        gate_id="scoring.input_identity",
        reason="shape",
        floor_id="F",
        witness=ConflictWitness(
            predicate="custom",
            predicate_schema_version="1",
            source_edge_ids=(("edge",),),
        ),
    )
    with pytest.raises(ValueError, match="invalid proof status"):
        certify_and_arbitrate_request(
            diagnostics=(diagnostic,),
            capabilities=(),
            evaluator_registry={("custom", "1"): lambda *_: "MAYBE"},
            request_key="garbage-request",
            identity_code="score_product_identity_invalid",
        )
    assert set(ProofStatus) == {
        ProofStatus.CERTIFIED_CONFLICT,
        ProofStatus.CONTINGENT,
        ProofStatus.DISPROVED,
        ProofStatus.UNPROVEN,
    }


def test_first_five_predicate_evaluators_are_registered():
    assert set(DEFAULT_EVALUATOR_REGISTRY) == {
        ("owner_multiplicity", "1"),
        ("missing_reverse_owner", "1"),
        ("exterior_interior_conflict", "1"),
        ("ring_identity_conflict", "1"),
        ("segment_merge_conflict", "1"),
    }


def test_identity_scorecontracterror_has_one_raise_origin_with_no_exceptions():
    """Static proof: scoring identity raises originate only in the arbiter.

    Slice 4 deleted the scheduled legacy exception.  Denominator integrity is a
    different error class.
    """
    paths = (
        Path("src/agent/judge/identity_provenance.py"),
        Path("src/agent/judge/segment_score.py"),
        Path("src/agent/judge/score_service.py"),
    )
    direct_raises: list[tuple[str, str]] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Raise) or child.exc is None:
                    continue
                call = child.exc
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "ScoreContractError"
                    and len(call.args) >= 2
                    and isinstance(call.args[1], ast.Constant)
                    and call.args[1].value == "scoring.input_identity"
                ):
                    direct_raises.append((path.name, node.name))
    assert direct_raises == []
    certifier = ast.parse(
        Path("src/agent/judge/certifier.py").read_text(encoding="utf-8")
    )
    arbiters = [
        node for node in ast.walk(certifier)
        if isinstance(node, ast.FunctionDef)
        and node.name == "certify_and_arbitrate_request"
    ]
    assert len(arbiters) == 1
    assert sum(isinstance(node, ast.Raise) for node in ast.walk(arbiters[0])) >= 2


def test_all_judge_input_identity_raise_origins_are_closed():
    """Full-domain proof: no judge module can hide beyond a hand list."""
    direct_raises: list[tuple[str, str, str]] = []
    for path in sorted(Path("src/agent/judge").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in (
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            for node in ast.walk(function):
                if not isinstance(node, ast.Raise) or node.exc is None:
                    continue
                call = node.exc
                if not (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "ScoreContractError"
                    and len(call.args) >= 2
                    and isinstance(call.args[0], ast.Constant)
                    and isinstance(call.args[1], ast.Constant)
                    and call.args[1].value == "scoring.input_identity"
                ):
                    continue
                direct_raises.append((
                    path.name,
                    function.name,
                    str(call.args[0].value),
                ))
    assert direct_raises == [
        (
            "elevation_score.py",
            "project_typed_elevation_observation",
            "score_product_identity_invalid",
        ),
        (
            "elevation_score.py",
            "score_typed_elevation_floor_lines",
            "score_product_identity_invalid",
        ),
        (
            "score_config.py",
            "load_judge_score_config",
            "score_gt_identity_invalid",
        ),
        (
            "score_schema.py",
            "load_score_gt_identity",
            "score_gt_identity_invalid",
        ),
    ]
