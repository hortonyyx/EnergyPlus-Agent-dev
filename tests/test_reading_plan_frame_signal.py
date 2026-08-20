"""Locks for the 2026-08-20 silent-zero guard on a null ``scale_origin``.

A plan view without ``scale_origin`` is a LEGAL product (guide.md §1: "leave
null rather than guess", relaxed to SHOULD on 2026-08-17).  The typed judge
cannot rebuild the plan-local → world frame from anything else, so the whole
plan channel scores every gt target as a miss — a structural zero whose score
rows and criteria were indistinguishable from bad tracing (measured on
2026-08-20 against the sm24 07-27 artifact: same strokes, origin deleted →
20/20 miss rows, no frame-related criterion, ``c2_scored`` kind so no strict
refusal).  The guard under test makes that zero loud instead of changing it:

1. contract — the score carries a first-class FAIL criterion naming the
   structural cause, while the miss rows (and thus the retained denominator)
   stay exactly as they were — NOT a filter escape hatch;
2. decision — strict profiles (golden/regression) refuse the score after the
   artifacts are committed, mirroring the top-level-NA refusal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_reading_typed_scoring_slice0 import (
    _grade_payload,
    _real_payload,
)


def _null_plan_origin_payload() -> dict:
    """The real artifact with every plan's ``scale_origin`` nulled, strokes untouched."""
    payload = json.loads(json.dumps(_real_payload()))
    nulled = 0
    for view in payload["views"].values():
        if (view.get("image_kind") or "").lower() == "plan":
            view["scale_origin"] = None
            nulled += 1
    assert nulled, "fixture must contain at least one plan view"
    return payload


def _criterion(criteria: list[dict], criterion_id: str) -> dict | None:
    return next(
        (item for item in criteria if item["criterion_id"] == criterion_id),
        None,
    )


def test_plan_frame_zero_is_loud_and_stays_in_denominator(tmp_path):
    """Contract: the structural zero is named in the criteria, not re-scored.

    Before the guard this exact fixture scored 20 miss rows with no
    frame-related criterion anywhere — the loudness asserted here is the new
    behaviour, and the unchanged miss rows are what keep it from being a
    filter-style escape hatch.
    """
    sidecar, artifacts = _grade_payload(
        tmp_path,
        _null_plan_origin_payload(),
        name="frame_na_contract",
    )
    criterion = _criterion(
        artifacts["score_criteria"], "reading.plan_frame_declared"
    )
    assert criterion is not None, (
        "null scale_origin must produce an explicit "
        "reading.plan_frame_declared criterion, not a bare miss pattern"
    )
    assert criterion["verdict"] == "fail"
    assert criterion["eligible"] is True, (
        "the plan channel must stay in the denominator (retain_as_miss), "
        "never filter out of it"
    )
    # One plan view × the two plan components (plan_segments, plan_openings).
    assert criterion["na_reasons"] == {"plan_frame_unavailable": 2}

    # The structural zero itself is unchanged: every plan target row is a
    # miss against the retained denominator, exactly as before the guard.
    rows = sidecar["payload"]["segment_rows"]
    assert rows and all(row["status"] == "miss" for row in rows)

    # Loudness is specific: a declared origin produces no such criterion.
    _, declared_artifacts = _grade_payload(
        tmp_path,
        _real_payload(),
        name="frame_declared_control",
    )
    assert _criterion(
        declared_artifacts["score_criteria"], "reading.plan_frame_declared"
    ) is None


@pytest.mark.parametrize("run_profile", ["golden", "regression"])
def test_strict_profile_fails_closed_on_structural_plan_frame_na(
    tmp_path, run_profile
):
    """Decision: acceptance profiles refuse the frame-less score after commit."""
    from src.agent.judge.score_service import TopLevelNotApplicableError

    with pytest.raises(TopLevelNotApplicableError) as excinfo:
        _grade_payload(
            tmp_path,
            _null_plan_origin_payload(),
            name=f"frame_na_strict_{run_profile}",
            run_profile=run_profile,
        )
    assert "plan_frame_unavailable" in str(excinfo.value)
    # Commit-then-raise: the refused score is still on disk for audit.
    attempt = (
        tmp_path / f"frame_na_strict_{run_profile}/0_reading/attempts/003"
    )
    assert (attempt / "score_vs_gt.json").exists()
    assert (attempt / "grade.png").read_bytes().startswith(b"\x89PNG")


@pytest.mark.parametrize("run_profile", ["exploratory", "dev"])
def test_soft_profiles_score_on_with_the_loud_criterion(
    tmp_path, run_profile
):
    """Decision: diagnostic profiles keep the score readable and flagged."""
    _, artifacts = _grade_payload(
        tmp_path,
        _null_plan_origin_payload(),
        name=f"frame_na_soft_{run_profile}",
        run_profile=run_profile,
    )
    criterion = _criterion(
        artifacts["score_criteria"], "reading.plan_frame_declared"
    )
    assert criterion is not None and criterion["verdict"] == "fail"
