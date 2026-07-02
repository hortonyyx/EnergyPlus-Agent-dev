"""Tests for the stepwise judge-in-the-loop orchestrator (backlog #1).

All fakes: no LLM / EP / geometry. The draw executor + the judge (the Agent) are
injected, so this exercises the decision logic — blind resample on gate① block,
the per-stage draw budget, the judge-verdict classification, and the geometry
human-confirmation gate.
"""

from __future__ import annotations

from pathlib import Path

from src.agent.execution import (
    ADVANCE_OK,
    RunManifest,
    RunPolicy,
    StageRunner,
    StageOutcome,
    StepStatus,
    TERMINAL_STOP,
    load_state,
    mark_geometry_approved,
    mark_review_approved,
    run_one_stage,
    submit_verdict,
    update_state,
)
from src.agent.execution.policy import ConfirmationPolicy
from src.agent.judge.verdict import StageVerdict
from src.validator.checks.schema import CheckLayer, CheckReport


def _judge_policy():
    """Policy with the dev-期 judge layer ON (the CLI's mode)."""
    return RunPolicy(judge_enabled=True)


# --------------------------------------------------------------------------- #
# fakes
# --------------------------------------------------------------------------- #
def _fake_draw(stage: str, results: list[bool]):
    """Draw fn returning (output, report) — `results[i]` = does draw i pass gate①.
    Records the feedback it was called with (must always be None = blind)."""
    calls = {"n": 0, "feedback": []}

    def draw(feedback):
        calls["feedback"].append(feedback)
        passed = results[min(calls["n"], len(results) - 1)]
        calls["n"] += 1
        rep = CheckReport(stage=stage)
        if passed:
            rep.add_pass("x", CheckLayer.INVARIANT)
        else:
            rep.add_fail("x", CheckLayer.INVARIANT, "bad")
        return {"draw": calls["n"]}, rep

    return draw, calls


def _runner(tmp_path):
    return StageRunner(tmp_path, RunManifest(case="t"))


def _record_attempts(tmp_path, stage: str, n: int):
    runner = _runner(tmp_path)
    draw, _ = _fake_draw(stage, [True] * n)
    for _ in range(n):
        run_one_stage(stage=stage, runner=runner, stage_dir=tmp_path / stage,
                      policy=RunPolicy(), draw_fn=draw, force_draw=True)
    return runner


def _verdict(stage, *, blocking, root="1_correction", conf=0.9):
    status = "severe" if blocking else "minor"
    return StageVerdict(
        stage=stage, rubric_id="J1",
        criteria=[{"criterion": "c", "status": status}],
        root_stage=root, root_confidence=conf,
    )


# --------------------------------------------------------------------------- #
# gate① + blind resample
# --------------------------------------------------------------------------- #
def test_stochastic_pass_first_draw_awaits_judge(tmp_path):
    draw, calls = _fake_draw("1_correction", [True])
    out = run_one_stage(stage="1_correction", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "1_correction", policy=_judge_policy(),
                        draw_fn=draw)
    assert out.status == StepStatus.AWAITING_JUDGE
    assert out.attempts_used == 1 and out.accepted_attempt == 1
    assert calls["feedback"] == [None]  # blind


def test_judge_disabled_policy_advances_without_judge(tmp_path):
    draw, _ = _fake_draw("1_correction", [True])
    out = run_one_stage(stage="1_correction", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "1_correction", policy=RunPolicy(),  # judge off
                        draw_fn=draw)
    assert out.status == StepStatus.DETERMINISTIC_PASS  # judge_enabled=False → no judge gate


def test_stochastic_block_then_pass_resamples_blind(tmp_path):
    draw, calls = _fake_draw("1_correction", [False, True])
    out = run_one_stage(stage="1_correction", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "1_correction", policy=_judge_policy(),
                        draw_fn=draw)
    assert out.status == StepStatus.AWAITING_JUDGE
    assert out.attempts_used == 2 and out.accepted_attempt == 2
    assert calls["feedback"] == [None, None]  # both blind
    # both drafts survive (append-only)
    assert (tmp_path / "1_correction" / "attempts" / "001" / "output.json").exists()
    assert (tmp_path / "1_correction" / "attempts" / "002" / "output.json").exists()


def test_stochastic_budget_exhausted_quarantines(tmp_path):
    draw, _ = _fake_draw("1_correction", [False, False, False, False])
    out = run_one_stage(stage="1_correction", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "1_correction",
                        policy=RunPolicy(), draw_fn=draw)
    assert out.status == StepStatus.QUARANTINED
    assert out.attempts_used == 3  # per_stage_draws default
    assert out.terminal_stop is True


def test_deterministic_pass_advances(tmp_path):
    draw, _ = _fake_draw("2_modelling", [True])
    out = run_one_stage(stage="2_modelling", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "2_modelling", policy=RunPolicy(),
                        draw_fn=draw)
    assert out.status == StepStatus.DETERMINISTIC_PASS
    assert out.can_advance is True


def test_deterministic_block_is_fail_closed_no_resample(tmp_path):
    draw, calls = _fake_draw("2_modelling", [False, True])  # would pass on resample
    out = run_one_stage(stage="2_modelling", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "2_modelling", policy=RunPolicy(),
                        draw_fn=draw)
    assert out.status == StepStatus.DETERMINISTIC_DEFECT
    assert out.attempts_used == 1  # NOT resampled — code defect, fail-closed
    assert calls["n"] == 1


def test_manual_block_requires_human_redraw(tmp_path):
    draw, _ = _fake_draw("0_reading", [False])
    out = run_one_stage(stage="0_reading", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "0_reading", policy=RunPolicy(),
                        draw_fn=draw)
    assert out.status == StepStatus.HUMAN_REDRAW_REQUIRED
    assert out.attempts_used == 1  # manual: not auto-resampled


def test_awaiting_reread_is_nonterminal_and_not_advance_ok():
    assert StepStatus.AWAITING_REREAD not in TERMINAL_STOP
    assert StepStatus.AWAITING_REREAD not in ADVANCE_OK


def test_awaiting_human_review_is_nonterminal_and_not_advance_ok():
    assert StepStatus.AWAITING_HUMAN_REVIEW not in TERMINAL_STOP
    assert StepStatus.AWAITING_HUMAN_REVIEW not in ADVANCE_OK


def test_manual_block_awaits_reread_when_runner_available(tmp_path):
    draw, calls = _fake_draw("0_reading", [False])
    out = run_one_stage(
        stage="0_reading",
        runner=_runner(tmp_path),
        stage_dir=tmp_path / "0_reading",
        policy=RunPolicy(reading_runner_available=True),
        draw_fn=draw,
    )
    assert out.status == StepStatus.AWAITING_REREAD
    assert out.terminal_stop is False
    assert out.route_target == "0_reading"
    assert out.attempts_used == 1
    assert calls["feedback"] == [None]


def test_manual_block_runner_available_budget_spent_quarantines(tmp_path):
    draw, _ = _fake_draw("0_reading", [False, False, False])
    runner = _runner(tmp_path)
    policy = RunPolicy(reading_runner_available=True)
    out1 = run_one_stage(stage="0_reading", runner=runner,
                         stage_dir=tmp_path / "0_reading", policy=policy, draw_fn=draw)
    out2 = run_one_stage(stage="0_reading", runner=runner,
                         stage_dir=tmp_path / "0_reading", policy=policy, draw_fn=draw)
    out3 = run_one_stage(stage="0_reading", runner=runner,
                         stage_dir=tmp_path / "0_reading", policy=policy, draw_fn=draw)
    assert out1.status == StepStatus.AWAITING_REREAD
    assert out2.status == StepStatus.AWAITING_REREAD
    assert out3.status == StepStatus.QUARANTINED
    assert out3.route_target == "0_reading"
    assert out3.attempts_used == 3


def test_manual_pass_awaits_judge_j0(tmp_path):
    draw, _ = _fake_draw("0_reading", [True])
    out = run_one_stage(stage="0_reading", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "0_reading", policy=_judge_policy(),
                        draw_fn=draw)
    assert out.status == StepStatus.AWAITING_JUDGE


# --------------------------------------------------------------------------- #
# judge verdict classification
# --------------------------------------------------------------------------- #
def _accept_one(tmp_path, stage):
    draw, _ = _fake_draw(stage, [True])
    return run_one_stage(stage=stage, runner=_runner(tmp_path),
                         stage_dir=tmp_path / stage, policy=_judge_policy(), draw_fn=draw)


def test_verdict_nonblocking_passes(tmp_path):
    _accept_one(tmp_path, "1_correction")
    out = submit_verdict(stage="1_correction", stage_dir=tmp_path / "1_correction",
                         attempt_index=1, verdict=_verdict("1_correction", blocking=False),
                         verdict_dir=tmp_path / "verdicts")
    assert out.status == StepStatus.JUDGE_PASS
    assert (tmp_path / "1_correction" / "attempts" / "001" / "judge.json").exists()
    assert len(list((tmp_path / "verdicts").glob("verdict_*.json"))) == 1


def test_j0_recoverable_pass_through_message_and_count(tmp_path):
    _accept_one(tmp_path, "0_reading")
    verdict = StageVerdict(
        stage="0_reading",
        rubric_id="J0",
        criteria=[
            {
                "criterion": "stroke_vs_dimension",
                "status": "severe",
                "recoverability": "correction_recoverable",
            }
        ],
        root_stage="0_reading",
        root_confidence=0.9,
    )
    out = submit_verdict(
        stage="0_reading",
        stage_dir=tmp_path / "0_reading",
        attempt_index=1,
        verdict=verdict,
    )
    assert out.status == StepStatus.JUDGE_PASS
    assert out.recoverable_criteria_count == 1
    assert "pass-through" in out.message
    assert out.summary()["recoverable_criteria_count"] == 1


def test_verdict_blocking_routable_resamples_same_stage(tmp_path):
    _accept_one(tmp_path, "1_correction")
    out = submit_verdict(stage="1_correction", stage_dir=tmp_path / "1_correction",
                         attempt_index=1, verdict=_verdict("1_correction", blocking=True))
    assert out.status == StepStatus.JUDGE_BLOCK
    assert out.route_target == "1_correction"


def test_verdict_routes_to_manual_upstream_root_human_redraw(tmp_path):
    # J1 verdict on 1_correction but root attributed to 0_reading (manual upstream):
    # must route to a human re-trace, NOT a 1_correction resample.
    _accept_one(tmp_path, "1_correction")
    out = submit_verdict(stage="1_correction", stage_dir=tmp_path / "1_correction",
                         attempt_index=1,
                         verdict=_verdict("1_correction", blocking=True, root="0_reading"))
    assert out.status == StepStatus.HUMAN_REDRAW_REQUIRED
    assert out.route_target == "0_reading"


def test_verdict_manual_root_awaits_reread_using_root_stage_budget(tmp_path):
    _record_attempts(tmp_path, "0_reading", 1)
    _record_attempts(tmp_path, "1_correction", 3)
    out = submit_verdict(
        stage="1_correction",
        stage_dir=tmp_path / "1_correction",
        attempt_index=3,
        verdict=_verdict("1_correction", blocking=True, root="0_reading"),
        policy=RunPolicy(reading_runner_available=True),
        stage_dir_for=lambda target: tmp_path / target,
    )
    assert out.status == StepStatus.AWAITING_REREAD
    assert out.route_target == "0_reading"
    # Proves budget used 0_reading attempts (1), not judged 1_correction attempts (3).
    assert out.attempts_used == 1


def test_verdict_manual_root_budget_spent_quarantines(tmp_path):
    _record_attempts(tmp_path, "0_reading", 3)
    _record_attempts(tmp_path, "1_correction", 1)
    out = submit_verdict(
        stage="1_correction",
        stage_dir=tmp_path / "1_correction",
        attempt_index=1,
        verdict=_verdict("1_correction", blocking=True, root="0_reading"),
        policy=RunPolicy(reading_runner_available=True),
        stage_dir_for=lambda target: tmp_path / target,
    )
    assert out.status == StepStatus.QUARANTINED
    assert out.route_target == "0_reading"
    assert out.attempts_used == 3


def test_existing_verdict_manual_root_awaits_reread(tmp_path):
    runner = _runner(tmp_path)
    reading_draw, _ = _fake_draw("0_reading", [True])
    run_one_stage(stage="0_reading", runner=runner, stage_dir=tmp_path / "0_reading",
                  policy=RunPolicy(), draw_fn=reading_draw)
    correction_draw, _ = _fake_draw("1_correction", [True])
    run_one_stage(stage="1_correction", runner=runner, stage_dir=tmp_path / "1_correction",
                  policy=_judge_policy(), draw_fn=correction_draw)
    submit_verdict(
        stage="1_correction",
        stage_dir=tmp_path / "1_correction",
        attempt_index=1,
        verdict=_verdict("1_correction", blocking=True, root="0_reading"),
        policy=RunPolicy(reading_runner_available=True),
        stage_dir_for=lambda target: tmp_path / target,
    )
    out = run_one_stage(
        stage="1_correction",
        runner=runner,
        stage_dir=tmp_path / "1_correction",
        policy=RunPolicy(judge_enabled=True, reading_runner_available=True),
        draw_fn=correction_draw,
        stage_dir_for=lambda target: tmp_path / target,
    )
    assert out.status == StepStatus.AWAITING_REREAD
    assert out.route_target == "0_reading"


def test_verdict_routes_to_deterministic_root_human_triage(tmp_path):
    _accept_one(tmp_path, "1_correction")
    out = submit_verdict(stage="1_correction", stage_dir=tmp_path / "1_correction",
                         attempt_index=1,
                         verdict=_verdict("1_correction", blocking=True, root="2_modelling"))
    assert out.status == StepStatus.JUDGE_BLOCK_HUMAN
    assert out.route_target == "2_modelling"


def test_verdict_invalid_root_goes_human(tmp_path):
    _accept_one(tmp_path, "1_correction")
    out = submit_verdict(stage="1_correction", stage_dir=tmp_path / "1_correction",
                         attempt_index=1,
                         verdict=_verdict("1_correction", blocking=True, root="nonsense"))
    assert out.status == StepStatus.JUDGE_BLOCK_HUMAN


def test_verdict_blocking_unattributed_goes_human(tmp_path):
    _accept_one(tmp_path, "1_correction")
    out = submit_verdict(stage="1_correction", stage_dir=tmp_path / "1_correction",
                         attempt_index=1,
                         verdict=_verdict("1_correction", blocking=True, root=None, conf=0.0))
    assert out.status == StepStatus.JUDGE_BLOCK_HUMAN


def test_verdict_blocking_manual_self_root_human_redraw(tmp_path):
    _accept_one(tmp_path, "0_reading")
    out = submit_verdict(stage="0_reading", stage_dir=tmp_path / "0_reading",
                         attempt_index=1, verdict=_verdict("0_reading", blocking=True,
                                                           root="0_reading"))
    assert out.status == StepStatus.HUMAN_REDRAW_REQUIRED


def test_judge_block_resample_shares_budget(tmp_path):
    """A judge-driven resample draws from the same per-stage well of 3."""
    runner = _runner(tmp_path)
    sd = tmp_path / "1_correction"
    draw, _ = _fake_draw("1_correction", [True, True, True, True])
    for _ in range(3):  # 3 accepted draws, each judge-blocked
        run_one_stage(stage="1_correction", runner=runner, stage_dir=sd,
                      policy=RunPolicy(), draw_fn=draw, force_draw=True)
    # 4th resample request: budget spent → quarantine, no new draw
    out = run_one_stage(stage="1_correction", runner=runner, stage_dir=sd,
                        policy=RunPolicy(), draw_fn=draw, force_draw=True)
    assert out.status == StepStatus.QUARANTINED
    assert out.attempts_used == 3


# --------------------------------------------------------------------------- #
# geometry human-confirmation gate
# --------------------------------------------------------------------------- #
def _required_policy():
    return RunPolicy(confirmation_policy=ConfirmationPolicy.REQUIRED, judge_enabled=True)


def test_geometry_checkpoint_blocks_when_unapproved(tmp_path):
    draw, _ = _fake_draw("3_split_pairing", [True])
    out = run_one_stage(stage="3_split_pairing", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "3_split_pairing", policy=_required_policy(),
                        draw_fn=draw, geometry_approved=lambda: False)
    assert out.status == StepStatus.AWAITING_GEOMETRY_APPROVAL


def test_geometry_checkpoint_advances_when_approved(tmp_path):
    draw, _ = _fake_draw("3_split_pairing", [True])
    out = run_one_stage(stage="3_split_pairing", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "3_split_pairing", policy=_required_policy(),
                        draw_fn=draw, geometry_approved=lambda: True)
    assert out.status == StepStatus.DETERMINISTIC_PASS


def test_mep_refused_until_geometry_approved(tmp_path):
    calls = {"drawn": False}

    def draw(_fb):
        calls["drawn"] = True
        rep = CheckReport(stage="4_mep")
        rep.add_pass("x", CheckLayer.INVARIANT)
        return {}, rep

    out = run_one_stage(stage="4_mep", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "4_mep", policy=_required_policy(),
                        draw_fn=draw, geometry_approved=lambda: False)
    assert out.status == StepStatus.AWAITING_GEOMETRY_APPROVAL
    assert calls["drawn"] is False  # refused BEFORE drawing


def test_mep_runs_when_approved_no_enabled_judge(tmp_path):
    draw, _ = _fake_draw("4_mep", [True])
    out = run_one_stage(stage="4_mep", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "4_mep", policy=_required_policy(),
                        draw_fn=draw, geometry_approved=lambda: True)
    # 4_mep judge J4 is disabled → gate① pass advances directly
    assert out.status == StepStatus.DETERMINISTIC_PASS


# --------------------------------------------------------------------------- #
# state ledger
# --------------------------------------------------------------------------- #
def test_update_state_records_stop_reason(tmp_path):
    draw, _ = _fake_draw("1_correction", [False, False, False, False])
    out = run_one_stage(stage="1_correction", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "1_correction", policy=RunPolicy(), draw_fn=draw)
    update_state(tmp_path, out, timestamp="2026-06-19")
    state = load_state(tmp_path)
    assert state["stop_reason"] == "quarantined@1_correction"
    assert state["stages"]["1_correction"]["status"] == "quarantined"


def test_update_state_clean_has_no_stop_reason(tmp_path):
    draw, _ = _fake_draw("2_modelling", [True])
    out = run_one_stage(stage="2_modelling", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "2_modelling", policy=RunPolicy(), draw_fn=draw)
    update_state(tmp_path, out, timestamp="2026-06-19")
    assert load_state(tmp_path)["stop_reason"] is None


def test_update_state_records_awaiting_reread_stop_reason(tmp_path):
    draw, _ = _fake_draw("0_reading", [False])
    out = run_one_stage(stage="0_reading", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "0_reading",
                        policy=RunPolicy(reading_runner_available=True), draw_fn=draw)
    update_state(tmp_path, out, timestamp="2026-06-22")
    state = load_state(tmp_path)
    assert state["stop_reason"] == "awaiting_reread@0_reading"
    assert state["stages"]["0_reading"]["status"] == "awaiting_reread"


def test_geometry_approval_clears_stop_reason(tmp_path):
    draw, _ = _fake_draw("3_split_pairing", [True])
    out = run_one_stage(stage="3_split_pairing", runner=_runner(tmp_path),
                        stage_dir=tmp_path / "3_split_pairing", policy=_required_policy(),
                        draw_fn=draw, geometry_approved=lambda: False)
    update_state(tmp_path, out, timestamp="t")
    assert load_state(tmp_path)["stop_reason"] == "awaiting_geometry_approval@3_split_pairing"
    mark_geometry_approved(tmp_path, timestamp="t2")
    st = load_state(tmp_path)
    assert st["stop_reason"] is None and st["geometry_approved"] is True


def test_human_review_approval_clears_matching_stop_reason(tmp_path):
    out = StageOutcome(
        stage="1_correction",
        status=StepStatus.AWAITING_HUMAN_REVIEW,
        attempts_used=1,
        accepted_attempt=1,
        message="review",
    )
    update_state(tmp_path, out, timestamp="t")
    assert load_state(tmp_path)["stop_reason"] == "awaiting_human_review@1_correction"
    mark_review_approved(tmp_path, "1_correction", timestamp="t2")
    st = load_state(tmp_path)
    assert st["stop_reason"] is None
    assert st["human_review_approved"]["1_correction"] is True


def test_advance_clears_stale_geometry_stop_reason(tmp_path):
    # Medium fix: a successful 4_mep advance after approval must not leave a stale
    # awaiting_geometry_approval@3_split_pairing in the ledger.
    runner = _runner(tmp_path)
    d3, _ = _fake_draw("3_split_pairing", [True])
    o3 = run_one_stage(stage="3_split_pairing", runner=runner,
                       stage_dir=tmp_path / "3_split_pairing", policy=_required_policy(),
                       draw_fn=d3, geometry_approved=lambda: False)
    update_state(tmp_path, o3, timestamp="t")
    assert load_state(tmp_path)["stop_reason"] is not None
    d4, _ = _fake_draw("4_mep", [True])
    o4 = run_one_stage(stage="4_mep", runner=runner, stage_dir=tmp_path / "4_mep",
                       policy=_required_policy(), draw_fn=d4, geometry_approved=lambda: True)
    update_state(tmp_path, o4, timestamp="t2")
    assert o4.status == StepStatus.DETERMINISTIC_PASS
    assert load_state(tmp_path)["stop_reason"] is None
