"""Slice 3 locks for shared-cut exact target/observation ledgers."""
from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import itertools
import math
from pathlib import Path

import pytest

from src.agent.judge import segment_score
from src.agent.judge.interval_ledger import (
    CanonicalCutRegistry,
    IntervalAtom,
    accept_coverage_claim,
    build_coverage_claim,
    build_observation_ledger,
    build_target_ledger,
    check_target_ledger,
    exact_float,
    exact_point,
)
from src.agent.judge.score_schema import JudgeScoreConfigV1, ScoreContractError
from src.agent.judge.segment_score import PlanSegment


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


def _segment(
    key: str,
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> PlanSegment:
    return PlanSegment(key, "F", p1, p2, (), (), False)


def _match(targets, observations):
    return segment_score.match_plan_segments(
        targets=targets,
        observations=observations,
        config=_config(),
    )


@pytest.mark.parametrize(
    "overlap_start",
    [1.0, 4.0 - 5e-10, math.nextafter(4.0, -math.inf)],
    ids=["B-L1-large", "B-L2-5e-10", "B-L3-min-binary64"],
)
def test_b_l1_l2_l3_observation_multiplicity_rejects_every_positive_overlap(
    overlap_start: float,
):
    targets = (
        _segment("t1", (0.0, 0.0), (4.0, 0.0)),
        _segment("t2", (overlap_start, 0.0), (4.0, 0.0)),
    )
    observation = _segment("obs", (0.0, 0.0), (4.0, 0.0))
    with pytest.raises(ScoreContractError) as caught:
        _match(targets, (observation,))
    error = caught.value
    assert error.code == "score_denominator_nonconserving"
    assert error.context["reason"] == "observation_cover_exceeds_length"
    assert error.context["target_ids"] == ("t1", "t2")
    lo = Fraction(error.context["atom_lo_exact"])
    hi = Fraction(error.context["atom_hi_exact"])
    assert hi > lo
    assert error.context["multiplicity"] == 2
    assert error.context["mapping_certificate_ids"]


def test_multiplicity_verdict_is_recomputable_from_context_with_global_gap():
    targets = (
        _segment("t1", (0.0, 0.0), (2.0, 0.0)),
        _segment("t2", (1.0, 0.0), (3.0, 0.0)),
    )
    observation = _segment("obs", (0.0, 0.0), (10.0, 0.0))
    with pytest.raises(ScoreContractError) as caught:
        _match(targets, (observation,))
    context = caught.value.context
    lo, hi = (Fraction(value) for value in context["trigger_atom_exact"])
    duplicate_charge = Fraction(context["duplicate_charge_exact"])
    charged = Fraction(context["charged_exact"])
    domain = Fraction(context["domain_exact"])
    assert (lo, hi) == (Fraction(1), Fraction(2))
    assert context["target_ids"] == ("t1", "t2")
    assert context["multiplicity"] == len(context["target_ids"]) == 2
    assert duplicate_charge == (hi - lo) * (context["multiplicity"] - 1)
    assert duplicate_charge > 0
    assert context["excess"] == float(duplicate_charge)
    assert charged - domain < 0
    assert context["excess"] > 0


def _b_l4_fixture():
    from tests.test_judge_arbitration_slice0 import (
        _typed_correction,
        _typed_gt_three_adjacent_spans,
    )
    from src.agent.correction.schema import CellV3

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
    targets = tuple(
        item for item in segment_score.extract_gt_plan_segments(gt)
        if not item.exterior
    )
    observations = tuple(
        item for item in segment_score.extract_correction_plan_segments(geometry)
        if not item.exterior
    )
    selected = tuple(
        item for item in targets
        if item.p1[1] == item.p2[1] == 1.0
    )
    return targets, selected, observations


def test_b_l4_companion_unfiltered_segment_set_reaches_scoring_without_conservation_error():
    all_targets, selected, observations = _b_l4_fixture()
    all_rows, _ = _match(all_targets, observations)
    selected_rows, _ = _match(selected, observations)
    assert selected_rows
    assert all_rows
    assert all(row.eligible_units >= 0.0 for row in all_rows)


def test_b_l5_target_permutations_have_identical_rows_and_exact_ledger_bytes(monkeypatch):
    _all_targets, targets, observations = _b_l4_fixture()
    original = segment_score._build_observation_ledger
    outcomes = []
    direct_ledgers = []
    for permutation in itertools.permutations(targets):
        captured = []

        def capture(*args, **kwargs):
            ledger = original(*args, **kwargs)
            captured.append(ledger.canonical_bytes)
            return ledger

        with monkeypatch.context() as local:
            local.setattr(segment_score, "_build_observation_ledger", capture)
            rows, mapping = _match(permutation, observations)
        row_bytes = tuple(
            (
                None if row.target is None else row.target.key,
                None if row.observation is None else row.observation.key,
                row.status,
                (
                    row.eligible_units_exact.numerator,
                    row.eligible_units_exact.denominator,
                ),
                row.eligible_units.hex(),
            )
            for row in rows
        )
        outcomes.append((row_bytes, mapping, tuple(captured)))
        registry = CanonicalCutRegistry.empty()
        claims = tuple(
            build_coverage_claim(
                target=target,
                observation=observations[0],
                axis_error_m=0.0,
                position_error_m=0.0,
                cut_registry=registry,
            )
            for target in permutation
        )
        assert all(claim is not None for claim in claims)
        direct_ledgers.append(build_observation_ledger(
            observation_key=observations[0].key,
            domain_exact=exact_float(observations[0].length),
            claims=claims,
        ).canonical_bytes)
    assert all(item == outcomes[0] for item in outcomes)
    assert all(item == direct_ledgers[0] for item in direct_ledgers)


def test_b_l6_half_target_ledgers_partition_both_domains(monkeypatch):
    target = _segment("target", (0.0, 0.0), (4.0, 0.0))
    observation = _segment("observation", (-1.0, 0.0), (2.0, 0.0))
    target_ledgers = []
    observation_ledgers = []
    original_target = segment_score._build_target_ledger
    original_observation = segment_score._build_observation_ledger

    def capture_target(*args, **kwargs):
        ledger = original_target(*args, **kwargs)
        target_ledgers.append(ledger)
        return ledger

    def capture_observation(*args, **kwargs):
        ledger = original_observation(*args, **kwargs)
        observation_ledgers.append(ledger)
        return ledger

    monkeypatch.setattr(segment_score, "_build_target_ledger", capture_target)
    monkeypatch.setattr(
        segment_score, "_build_observation_ledger", capture_observation
    )
    _match((target,), (observation,))
    target_ledger = target_ledgers[0]
    observation_ledger = observation_ledgers[0]
    matched = sum(value for _, value in target_ledger.matched_exact)
    assert (
        matched + target_ledger.miss_exact + target_ledger.duplicate_exact
        == target_ledger.domain_exact
    )
    assert matched == 2
    assert target_ledger.miss_exact == 2
    assert (
        observation_ledger.covered_exact + observation_ledger.extra_exact
        == observation_ledger.domain_exact
    )
    assert observation_ledger.extra_exact == 1
    rows, _ = _match((target,), (observation,))
    assert all(
        float(row.eligible_units_exact) == row.eligible_units for row in rows
    )


def test_b_l7_adjacent_targets_leave_no_observation_extra(monkeypatch):
    x0 = 0.6615103026426206
    x1 = 10.189556344280527
    x2 = 16.84636437455466
    targets = (
        _segment("left", (x0, 0.0), (x1, 0.0)),
        _segment("right", (x1, 0.0), (x2, 0.0)),
    )
    observation = _segment("observation", (x0, 0.0), (x2, 0.0))
    captured = []
    original = segment_score._build_observation_ledger

    def capture(*args, **kwargs):
        ledger = original(*args, **kwargs)
        captured.append(ledger)
        return ledger

    monkeypatch.setattr(segment_score, "_build_observation_ledger", capture)
    rows, _ = _match(targets, (observation,))
    assert captured[0].extra_exact == 0
    assert captured[0].covered_exact == captured[0].domain_exact
    assert all(row.status != "extra" for row in rows)


@pytest.mark.parametrize(
    "observation",
    [
        _segment("full", (0.0, 0.05), (4.0, 0.050001)),
        _segment("partial", (-1.0, 0.05), (2.0, 0.050001)),
        _segment("reversed", (2.0, 0.050001), (-1.0, 0.05)),
    ],
)
def test_b_l8_tilted_observation_atoms_stay_in_observation_native_domain(
    observation: PlanSegment,
    monkeypatch,
):
    target = _segment("target", (0.0, 0.0), (4.0, 0.0))
    captured = []
    original = segment_score._build_observation_ledger

    def capture(*args, **kwargs):
        ledger = original(*args, **kwargs)
        captured.append(ledger)
        return ledger

    monkeypatch.setattr(segment_score, "_build_observation_ledger", capture)
    _match((target,), (observation,))
    ledger = captured[0]
    assert all(
        0 <= atom.lo_exact < atom.hi_exact <= ledger.domain_exact
        for atom in ledger.atoms
    )
    assert ledger.covered_exact + ledger.extra_exact == ledger.domain_exact
    if observation.key == "full":
        assert ledger.covered_exact == ledger.domain_exact
    else:
        assert ledger.extra_exact > 0
    for atom in ledger.atoms:
        assert atom.lo_cut_ids
        assert atom.hi_cut_ids


def test_b_l9_noncontiguous_ledger_checker_reports_exact_endpoints():
    ledger = build_target_ledger(
        target_key="target",
        domain_exact=Fraction(4),
        claims=(),
    )
    broken = replace(
        ledger,
        atoms=(
            IntervalAtom(
                Fraction(0),
                Fraction(3),
                "miss",
                lo_cut_ids=("DOMAIN_START",),
                hi_cut_ids=("broken",),
            ),
        ),
    )
    with pytest.raises(ScoreContractError) as caught:
        check_target_ledger(broken)
    assert caught.value.context["reason"] == "interval_ledger_wrong_domain_end"
    assert caught.value.context["expected_hi_exact"] == "4/1"
    assert caught.value.context["actual_hi_exact"] == "3/1"


def test_b_l10_two_domain_clip_mismatch_rejects_before_ledger():
    target = _segment("target", (0.0, 0.0), (4.0, 0.0))
    observation = _segment("observation", (0.0, 0.0), (4.0, 0.0))
    claim = build_coverage_claim(
        target=target,
        observation=observation,
        axis_error_m=0.0,
        position_error_m=0.0,
        cut_registry=CanonicalCutRegistry.empty(),
    )
    assert claim is not None
    broken = replace(
        claim,
        target_interval=(
            claim.target_interval[0],
            claim.target_interval[1] + exact_float(5e-10),
        ),
    )
    with pytest.raises(ScoreContractError) as caught:
        accept_coverage_claim(
            broken,
            target_domain=exact_float(target.length),
            observation_domain=exact_float(observation.length),
        )
    assert caught.value.context["reason"] == "coverage_claim_mapping_inconsistent"
    assert caught.value.context["mapping_certificate_id"]


def test_production_reuses_one_registry_and_one_shared_observation_cut(monkeypatch):
    targets = (
        _segment("left", (0.0, 0.0), (2.0, 0.0)),
        _segment("right", (2.0, 0.0), (4.0, 0.0)),
    )
    observation = _segment("observation", (0.0, 0.0), (4.0, 0.0))
    registry = CanonicalCutRegistry.empty()
    calls = []

    class RegistryFactory:
        @staticmethod
        def empty():
            calls.append("empty")
            return registry

    monkeypatch.setattr(
        segment_score, "CanonicalCutRegistry", RegistryFactory
    )
    _match(targets, (observation,))
    assert calls == ["empty"]
    cut_id = registry.geometry[exact_point((2.0, 0.0))].cut_id
    assert registry.observation_evaluation_count[
        (observation.key, cut_id)
    ] == 1


def test_observation_ledger_seam_return_is_consumed_by_scoring(monkeypatch):
    target = _segment("target", (0.0, 0.0), (2.0, 0.0))
    observation = _segment("observation", (0.0, 0.0), (2.0, 0.0))
    baseline, _ = _match((target,), (observation,))
    assert all(row.status != "extra" for row in baseline)
    original = segment_score._build_observation_ledger

    def perturb(*args, **kwargs):
        ledger = original(*args, **kwargs)
        return replace(ledger, extra_exact=Fraction(1, 2))

    monkeypatch.setattr(segment_score, "_build_observation_ledger", perturb)
    perturbed, _ = _match((target,), (observation,))
    extras = [row for row in perturbed if row.status == "extra"]
    assert len(extras) == 1
    assert extras[0].eligible_units == 0.5


def test_production_match_path_has_no_scalar_conservation_branch_or_tolerance():
    tree = ast.parse(
        Path("src/agent/judge/segment_score.py").read_text(encoding="utf-8")
    )
    match = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "match_plan_segments"
    )
    names = {
        node.id for node in ast.walk(match) if isinstance(node, ast.Name)
    }
    assert "_assert_target_conservation" not in names
    assert "_assert_obs_conservation" not in names
    assert "_SUBINTERVAL_SUM_TOL" not in names


def test_exact_error_context_true_has_one_static_origin():
    production = tuple(sorted(Path("src/agent/judge").rglob("*.py")))
    origins = []
    string_origins = []
    for path in production:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        string_origins.extend(
            path.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and node.value == "_exact_error_context"
        )
        for function in (
            node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ):
            for call in (
                node for node in ast.walk(function) if isinstance(node, ast.Call)
            ):
                for keyword in call.keywords:
                    if (
                        keyword.arg == "_exact_error_context"
                    ):
                        origins.append(
                            (path.name, function.name, ast.dump(keyword.value))
                        )
    assert origins == [
        (
            "score_service.py",
            "_raise_score_input_contract",
            "Constant(value=True)",
        )
    ]
    # The sole string-key read is the closed admission bridge itself.  A future
    # ``**{"_exact_error_context": value}`` setter is therefore enumerated too.
    assert string_origins == ["identity_provenance.py"]


def test_score_input_exemption_hardcodes_only_typed_admission_predicate():
    tree = ast.parse(
        Path("src/agent/judge/score_service.py").read_text(encoding="utf-8")
    )
    helper = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_raise_score_input_contract"
    )
    calls = [
        node for node in ast.walk(helper)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "raise_identity_conflict"
    ]
    assert len(calls) == 1
    predicate = next(
        keyword.value for keyword in calls[0].keywords
        if keyword.arg == "predicate"
    )
    assert isinstance(predicate, ast.Constant)
    assert predicate.value == "typed_score_input_contract"
    assert "predicate" not in {argument.arg for argument in helper.args.args}


def test_score_input_exemption_still_delegates_severity_to_arbiter(monkeypatch):
    from src.agent.judge import certifier, score_service

    class ArbiterReached(RuntimeError):
        pass

    def sentinel(**_kwargs):
        raise ArbiterReached

    monkeypatch.setattr(certifier, "certify_and_arbitrate_request", sentinel)
    with pytest.raises(ArbiterReached):
        score_service._raise_score_input_contract(
            "score_product_identity_invalid",
            reason="test_admission",
        )
