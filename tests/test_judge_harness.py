"""M3 acceptance: judge harness (build plan §2.1 M3).

All judges are fake/mock — no model wording in assertions. Covers: malformed /
partial / insufficient_evidence / unknown verdicts; root attribution not routed
when unknown; judge unavailable; J4 disabled stub; the two entry points
(repair_feedback vs judge_retry_context) NOT crossing; per-stage + judge budget.
"""

from __future__ import annotations

import pytest

from src.agent.execution.invalidation import RunBudget
from src.agent.judge import (
    CriterionStatus,
    StageVerdict,
    disabled_verdict,
    retry_stage_draw,
    run_judge,
)
from src.validator.checks.schema import CheckLayer, CheckReport


# --------------------------------------------------------------------------- #
# verdict schema v2
# --------------------------------------------------------------------------- #
def test_verdict_blocking_and_routable():
    v = StageVerdict(
        stage="1_correction", rubric_id="J1",
        criteria=[{"criterion": "redraw", "status": "severe", "evidence": "x"}],
        root_stage="1_correction", root_confidence=0.9, retriable=True,
    )
    assert v.blocking is True
    assert v.routable() is True


def test_j0_severe_recoverable_is_not_blocking():
    v = StageVerdict(
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
    assert v.blocking is False
    assert v.routable() is False


def test_j1_severe_recoverable_still_blocks():
    v = StageVerdict(
        stage="1_correction",
        rubric_id="J1",
        criteria=[
            {
                "criterion": "redraw",
                "status": "severe",
                "recoverability": "correction_recoverable",
            }
        ],
        root_stage="1_correction",
        root_confidence=0.9,
    )
    assert v.blocking is True
    assert v.routable() is True


def test_severe_missing_recoverability_blocks_for_backward_compat():
    v = StageVerdict(
        stage="0_reading",
        rubric_id="J0",
        criteria=[{"criterion": "legacy", "status": "severe"}],
        root_stage="0_reading",
        root_confidence=0.9,
    )
    assert v.blocking is True
    assert v.routable() is True


def test_unknown_root_not_routable():
    """Blocking but unknown root / low confidence → NOT auto-routed (交人)."""
    v = StageVerdict(
        stage="1_correction", rubric_id="J1",
        criteria=[{"criterion": "redraw", "status": "fatal"}],
        root_stage=None, root_confidence=0.2,
    )
    assert v.blocking is True
    assert v.routable() is False


def test_insufficient_evidence_does_not_block():
    v = StageVerdict(
        stage="0_reading", rubric_id="J0",
        criteria=[{"criterion": "number_copied", "status": "insufficient_evidence"}],
    )
    assert v.blocking is False


def test_minor_flags_not_blocks():
    v = StageVerdict(
        stage="0_reading", rubric_id="J0",
        criteria=[{"criterion": "pen", "status": "minor"}],
    )
    assert v.blocking is False


def test_malformed_verdict_rejected():
    with pytest.raises(Exception):
        StageVerdict.model_validate({"stage": "0_reading", "rubric_id": "J0",
                                     "criteria": [{"criterion": "x", "status": "BOGUS"}]})


# --------------------------------------------------------------------------- #
# executor: J0/J1 enabled, J4 disabled, unavailable
# --------------------------------------------------------------------------- #
def _fake_judge(verdict_dict):
    def _fn(stage, rubric_id, artifacts):
        return verdict_dict
    return _fn


def test_j4_is_disabled_stub_not_fake_pass(tmp_path):
    called = {"n": 0}

    def judge_fn(stage, rubric_id, artifacts):
        called["n"] += 1
        return {"criteria": []}

    out = run_judge("4_mep", {}, judge_fn=judge_fn, verdict_dir=tmp_path)
    assert out.disabled is True            # explicitly disabled
    assert called["n"] == 0                # judge_fn never called for J4
    assert not out.verdict.routable()      # a disabled verdict is never routable


def test_judge_unavailable_is_not_pass(tmp_path):
    out = run_judge("0_reading", {}, judge_fn=None, verdict_dir=tmp_path)
    assert out.disabled is True            # treated as disabled, not a fake PASS


def test_enabled_judge_runs_and_quarantines_unknown(tmp_path):
    budget = RunBudget()
    verdict = {"criteria": [{"criterion": "redraw", "status": "severe"}],
               "root_stage": None, "root_confidence": 0.1}
    out = run_judge("1_correction", {}, judge_fn=_fake_judge(verdict),
                    budget=budget, verdict_dir=tmp_path)
    assert out.verdict.blocking
    assert out.quarantined is True         # blocking but unknown root → quarantine
    assert budget.judges_used == 1
    # append-only verdict written
    assert list(tmp_path.glob("verdict_*.json"))


def test_routable_verdict_not_quarantined(tmp_path):
    verdict = {"criteria": [{"criterion": "redraw", "status": "severe"}],
               "root_stage": "0_reading", "root_confidence": 0.9}
    out = run_judge("1_correction", {}, judge_fn=_fake_judge(verdict),
                    verdict_dir=tmp_path)
    assert out.quarantined is False


def test_judge_budget_enforced(tmp_path):
    budget = RunBudget(global_judges=1)
    v = {"criteria": [{"criterion": "x", "status": "pass"}]}
    run_judge("0_reading", {}, judge_fn=_fake_judge(v), budget=budget, verdict_dir=tmp_path)
    with pytest.raises(Exception):
        run_judge("1_correction", {}, judge_fn=_fake_judge(v), budget=budget, verdict_dir=tmp_path)


# --------------------------------------------------------------------------- #
# retry: the two entry points must NOT cross
# --------------------------------------------------------------------------- #
def _clean_report():
    r = CheckReport(stage="1_correction")
    r.add_pass("x", CheckLayer.INVARIANT)
    return r


def _bad_report():
    r = CheckReport(stage="1_correction")
    r.add_fail("x", CheckLayer.INVARIANT, "bad")
    return r


def test_repair_feedback_is_injected():
    seen = []

    def draw_fn(feedback):
        seen.append(feedback)
        return {"ok": True}

    retry_stage_draw(stage="1_correction", draw_fn=draw_fn,
                     validate_fn=lambda d: _clean_report(),
                     repair_feedback="fix the windows")
    assert seen == ["fix the windows"]     # repair feedback reaches the draw


def test_judge_context_is_never_injected():
    """judge_retry_context must NOT reach the draw prompt — blind resample."""
    seen = []
    oob = []

    def draw_fn(feedback):
        seen.append(feedback)
        return {"ok": True}

    retry_stage_draw(stage="1_correction", draw_fn=draw_fn,
                     validate_fn=lambda d: _clean_report(),
                     judge_retry_context="judge said the corridor is wrong",
                     out_of_band_sink=oob.append)
    assert seen == [None]                  # draw was blind (no injection)
    assert oob and "OUT-OF-BAND" in oob[0]  # commentary logged out-of-band only


def test_retry_resamples_then_succeeds():
    calls = {"n": 0}

    def draw_fn(feedback):
        calls["n"] += 1
        return {"attempt": calls["n"]}

    # fail first attempt, pass second
    reports = [_bad_report(), _clean_report()]

    def validate_fn(draw):
        return reports[calls["n"] - 1]

    res = retry_stage_draw(stage="1_correction", draw_fn=draw_fn,
                           validate_fn=validate_fn, budget=RunBudget(per_stage_draws=3))
    assert res.accepted and res.attempts == 2


def test_retry_quarantines_when_budget_spent():
    def draw_fn(feedback):
        return {}

    res = retry_stage_draw(stage="1_correction", draw_fn=draw_fn,
                           validate_fn=lambda d: _bad_report(),
                           budget=RunBudget(per_stage_draws=3))
    assert res.accepted is False
    assert res.quarantined is True
    assert res.attempts == 3


def test_disabled_verdict_helper():
    v = disabled_verdict("4_mep", "J4")
    assert v.judge_disabled and not v.blocking
    assert v.criteria == []
