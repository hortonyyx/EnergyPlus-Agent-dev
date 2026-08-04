"""Locks for the sm21 e2e-break r2 dispatch (commit following 4a11097).

Three real defects, each with a "摘掉即红" lock and (where the fix is a
judgment) a discriminating two-/four-cell matrix on REAL-scale payloads:

* **F-3** — `1_correction` accepted an unfinalized draft (raw v3 geom) under a
  `base_v2` record; two stages later `load_verified_accepted_correction`
  fail-closed with an opaque message.
  - F-3a (root cause): the evidence-debt early-exit in `_draw_correction` keyed
    on ``any(FAIL)`` instead of ``.blocking()``, so an ADVISORY debt (FLAG under
    exploratory) early-exited with the raw geom. Two-cell: exploratory advisory
    FAIL ⇒ finalize (FinalizeResult); regression same FAIL ⇒ early-exit.
  - F-3b (write-point lock): StageRunner refuses a v3 raw geom accepted under a
    `base_v2` `1_correction` record. Two-cell: v3 rejects, v2 (legacy) allowed.
* **F-2** — isolation `merge` carried only `output.json`, stranding
  `reading_summary.md` (a hard dependency of `_build_correction_messages`).
  - F-2a: merge carries the summary to the stage root + records its hash in the
    audited isolation provenance.
  - F-2b: a missing summary is a named, localizable failure (merge boundary and
    correction entry), not a bare FileNotFoundError.
* **MAJOR-1** — legacy scoring semantics changed (4a11097 F-1a/F-1b) but the
  sidecar cache key (`SCORER_SCHEMA`) did not, so a stale sidecar short-circuited
  re-grading. Bumped 8→9; lock: a real-shape stale-schema sidecar MUST recompute
  (two-cell: stale recomputes, current reuses).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

import scripts.tool_scripts.run_stage as rs
from src.agent.correction.feature_state import derive_feature_state_claims
from src.agent.correction.finalize import FinalizeResult, finalize_correction_draw
from src.agent.correction.parse import correction_target
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.evidence_preflight import EvidenceDebt, EvidenceDebtItem
from src.agent.execution.isolation import build_isolation_workspace, merge_isolated_output
from src.agent.execution.manifest import ensure_run_manifest_v2, hash_file, hash_text
from src.agent.execution.stage_runner import StageRunner
from src.agent.execution.view_manifest import provision_view_manifest
from src.agent.execution.policy import RunPolicy
from src.agent.judge.gt import load_gt
from src.validator.checks.schema import CheckLayer, CheckReport

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))


# --------------------------------------------------------------------------- #
# Real-scale payloads (committed artifacts only — never the untracked orchestrator runs).
# --------------------------------------------------------------------------- #
_SM21 = Path("case_tests/e2e_tests/sm21_anchor")
_REAL_SNAPPED = _SM21 / "run_2026-07-07_haiku_cv_retest" / "1_correction" / "correction_geometry_snapped.json"
_REAL_VIEWS_PATH = _SM21 / "run_2026-06-20_gpt54_reading" / "0_reading" / "attempts" / "002" / "output.json"


def _real_geom() -> CorrectedGeometry:
    """A real, committed sm21 correction geom (produced by a real run)."""
    return CorrectedGeometry.model_validate(json.loads(_REAL_SNAPPED.read_text(encoding="utf-8")))


def _element_local_debt_json() -> str:
    """A real evidence_debt whose single item is element-local and NOT resolved
    by the real geom's audit ⇒ check_evidence_debt_coverage emits exactly one
    FAIL with evidence scope='element_local' (BLOCK under golden/regression,
    FLAG under exploratory — the disposition split F-3a keys on)."""
    return EvidenceDebt(
        debts=[
            EvidenceDebtItem(
                check_id="1f_view.reading.dimension_chain_closure",
                canonical_check_id="reading.dimension_chain_closure",
                view="1f_view",
                status="fail",
                layer="cross_check",
                disposition="flag",
                message="element-local evidence debt not covered by the audit",
                scope="element_local",
                offender_ids=["D_nonexistent_X"],
            )
        ]
    ).model_dump_json()


# =========================================================================== #
# F-3a — debt early-exit is profile-aware (two-cell, real geom + real debt)
# =========================================================================== #
def _draw_correction_with_debt(run_dir: Path, run_profile: str, finalize_spy: list, monkeypatch):
    """Drive the REAL `_draw_correction` with the LLM + unrelated heavy steps
    stubbed, but keep `check_evidence_debt_coverage` + the F-3a early-exit line
    + the routing REAL. Isolates exactly the debt early-exit decision."""
    import src.agent.pipeline as pipeline
    import src.agent.correction.finalize as finalize_mod
    import src.agent.correction.window_sources as ws
    import src.validator.checks.correction as corr_checks

    geom = _real_geom()
    (run_dir / "1_correction").mkdir(parents=True, exist_ok=True)
    (run_dir / "0_reading").mkdir(parents=True, exist_ok=True)
    (run_dir / "1_correction" / "evidence_debt.json").write_text(_element_local_debt_json(), encoding="utf-8")
    target = correction_target("rectangular")

    def fake_finalize(geom_or_payload, *, vector_dir, target, verified_window_inputs=None, tol=None):
        finalize_spy.append(True)
        return FinalizeResult(
            geom=geom, audit_payload={},
            feature_state_claims=derive_feature_state_claims(target, geom),
        )

    # LLM -> real geom; the OTHER early-exit (draw_quality) + post-finalize check
    # + reading-root verifier are stubbed so they never mask the debt decision.
    # run_correction/correction_draw_issues are local imports in _draw_correction
    # (read from src.agent.pipeline at call time); dimensioned_view_names is a
    # module-level import in run_stage (read from case_metadata), so patch rs.
    monkeypatch.setattr(pipeline, "run_correction", lambda *a, **k: geom)
    monkeypatch.setattr(pipeline, "correction_draw_issues", lambda *a, **k: [])
    monkeypatch.setattr(rs, "dimensioned_view_names", lambda *a, **k: set())
    monkeypatch.setattr(finalize_mod, "finalize_correction_draw", fake_finalize)
    monkeypatch.setattr(ws, "verify_reading_stage_root_against_accepted_attempt", lambda *a, **k: None)
    monkeypatch.setattr(corr_checks, "check_correction", lambda *a, **k: CheckReport(stage="1_correction"))
    policy = RunPolicy(capability_profile="rectangular", run_profile=run_profile)
    return rs._draw_correction(run_dir, "testdata", expected_zones=None, relied=False, policy=policy)


def test_f3a_debt_early_exit_two_cell_profile_matrix(tmp_path, monkeypatch):
    """F-3a two-cell: the SAME element-local evidence-debt FAIL is advisory under
    exploratory (⇒ finalize runs, a FinalizeResult is returned) and blocking
    under regression (⇒ early-exit with the raw geom, finalize NOT called).

    This is the discriminating-power lock the neuter-lesson demands: the fix
    changed ``any(FAIL)`` → ``.blocking()``, and these two cells prove the
    predicate the line now uses actually separates the two outcomes on a real
    geom + real debt (not a退化 fixture)."""
    # Sanity: the判据 itself is discriminating on the real payload.
    from src.validator.checks.correction import check_evidence_debt_coverage

    debt = EvidenceDebt.model_validate_json(_element_local_debt_json())
    geom = _real_geom()
    exp = check_evidence_debt_coverage(geom, debt, capability_profile="rectangular", run_profile="exploratory")
    reg = check_evidence_debt_coverage(geom, debt, capability_profile="rectangular", run_profile="regression")
    assert len(exp.results) == len(reg.results) == 1  # exactly the one debt FAIL
    assert exp.blocking() == [] and len(reg.blocking()) == 1

    # Cell 1 — exploratory (advisory): flows through to finalize.
    spy_exp: list = []
    out_exp = _draw_correction_with_debt(tmp_path / "run_exp", "exploratory", spy_exp, monkeypatch)
    assert spy_exp == [True], "exploratory advisory debt must NOT early-exit — finalize must run"
    assert isinstance(out_exp[0], FinalizeResult)
    assert out_exp[1].blocking() == []

    # Cell 2 — regression (same FAIL becomes blocking): early-exits, no finalize.
    spy_reg: list = []
    out_reg = _draw_correction_with_debt(tmp_path / "run_reg", "regression", spy_reg, monkeypatch)
    assert spy_reg == [], "regression blocking debt must early-exit — finalize must NOT run"
    assert isinstance(out_reg[0], CorrectedGeometry) and not isinstance(out_reg[0], FinalizeResult)
    assert len(out_reg[1].blocking()) == 1


# =========================================================================== #
# F-3b — StageRunner refuses an unfinalized v3 draft under base_v2 (two-cell)
# =========================================================================== #
def _v3_payload():
    # Same minimal real-shape v3 correction payload shape used by the B5 legacy
    # suite (test_c2_b5_legacy._payload) — model-validated, not a mock.
    return {
        "schema_version": "3",
        "footprint_x": [0.0, 4.0], "footprint_y": [0.0, 3.0],
        "floors": [{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
                    "cells": [{"id": "A", "x": [0.0, 4.0], "y": [0.0, 3.0]}]}],
        "windows": [],
    }


def test_f3b_stage_runner_rejects_v3_draft_but_allows_v2(tmp_path):
    """F-3b: accepting a 1_correction record that would land a v3 raw geom under
    the catch-all `base_v2` contract fail-closes at the WRITE point (not two
    stages later in the reader). v2 raw geom under base_v2 is the legitimate
    legacy path and must still pass — the lock is narrow, not over-blocking."""
    run_dir = tmp_path / "run"
    s1 = run_dir / "1_correction"
    s1.mkdir(parents=True)
    manifest = ensure_run_manifest_v2(run_dir, view_manifest_sha256="a" * 64)
    rep = CheckReport(stage="1_correction")
    rep.add_pass("x", CheckLayer.INVARIANT)

    # Cell 1 — v3 raw draft under base_v2 1_correction: rejected (F-3b).
    v3 = CorrectedGeometry.model_validate(_v3_payload())
    assert v3.schema_version == "3"
    with pytest.raises(ValueError, match="F-3b"):
        StageRunner(run_dir, manifest).record(
            stage="1_correction", stage_dir=s1, output_obj=v3, report=rep, accept=True,
        )
    assert manifest.accepted("1_correction") is None, "the rejected draft must not be accepted"

    # Cell 2 — v2 raw geom under base_v2 1_correction: legacy, still allowed.
    v2 = CorrectedGeometry.model_validate({**_v3_payload(), "schema_version": "2"})
    assert v2.schema_version == "2"
    rec = StageRunner(run_dir, manifest).record(
        stage="1_correction", stage_dir=s1, output_obj=v2, report=rep, accept=True,
    )
    assert rec.accepted
    accepted = manifest.accepted("1_correction")
    assert accepted is not None and accepted.artifact_contract == "base_v2"


# =========================================================================== #
# F-2a / F-2b — isolation merge carries the reading summary (or fails named)
# =========================================================================== #
def _formal_build(case_dir: Path, run_dir: Path, staging_root: Path):
    provision_view_manifest(case_dir, run_dir)
    return build_isolation_workspace(case_dir, run_dir=run_dir, staging_root=staging_root)


def _real_views() -> dict:
    return json.loads(_REAL_VIEWS_PATH.read_text(encoding="utf-8"))


def test_f2a_merge_carries_reading_summary_to_stage_root_with_hash(tmp_path):
    """F-2a: merge carries `out/reading_summary.md` to `<run>/0_reading/` (where
    `_build_correction_messages` reads it) and records its hash in the audited
    isolation provenance — same accounting as output.json. Real clean-room build
    + real six-view aggregate + a real summary."""
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(_SM21, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    (staging / "out" / "output.json").write_text(json.dumps({"views": _real_views()}), encoding="utf-8")
    summary_text = "# Reading summary — real scale\nGrade line at 0.000; windows span 1.2 m.\n"
    (staging / "out" / "reading_summary.md").write_text(summary_text, encoding="utf-8")

    attempt_dir = merge_isolated_output(staging, run_dir)

    # The summary lands at the stage root — exactly where correction reads it.
    stage_summary = run_dir / "0_reading" / "reading_summary.md"
    assert stage_summary.is_file()
    assert stage_summary.read_text(encoding="utf-8") == summary_text
    # Its hash is recorded in the audited provenance (bound through the
    # isolation_provenance hash; reading_isolated_v2 permits only
    # output/checks/isolation_provenance manifest keys, so the summary is
    # deliberately not a manifest artifact key).
    prov = json.loads((attempt_dir / "isolation_provenance.json").read_text(encoding="utf-8"))
    assert prov["reading_summary_sha256"] == hash_text(summary_text)


def test_f2b_merge_without_summary_succeeds_and_records_null_hash(tmp_path):
    """F-2a/b boundary: merge copies the summary IF present and otherwise
    proceeds (the named failure for a genuinely missing summary fires at the
    correction entry — see test_f2b_correction_entry_names_missing_summary —
    which the kickoff contract makes the hard dependency). When the reader
    omitted the summary, merge must NOT silently invent one: no stage-root file
    is written and the provenance records an explicit ``None`` hash (auditable,
    not hidden)."""
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(_SM21, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    (staging / "out" / "output.json").write_text(json.dumps({"views": _real_views()}), encoding="utf-8")
    # NOTE: no out/reading_summary.md written.

    attempt_dir = merge_isolated_output(staging, run_dir)  # does not raise
    assert not (run_dir / "0_reading" / "reading_summary.md").exists()
    prov = json.loads((attempt_dir / "isolation_provenance.json").read_text(encoding="utf-8"))
    assert prov["reading_summary_sha256"] is None


def test_f2b_correction_entry_names_missing_summary(tmp_path):
    """F-2b defense-in-depth at the correction entry: even on a non-isolated
    path (flat reader that forgot the summary), `_build_correction_messages`
    raises a named FileNotFoundError pointing at the reading-stage contract —
    not a bare OSError from `read_text`."""
    from src.agent.pipeline import _build_correction_messages

    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    assert not (vector_dir / "reading_summary.md").exists()
    # Match a phrase unique to the NAMED error — a bare read_text OSError only
    # carries the path, so matching "1_correction requires" proves the named,
    # contextual failure (not the bare one) and goes red if the guard is removed.
    with pytest.raises(FileNotFoundError, match="1_correction requires"):
        _build_correction_messages(vector_dir, "testdata prompt")


# =========================================================================== #
# MAJOR-1 — a stale-schema sidecar is recomputed, a current one reused (two-cell)
# =========================================================================== #
def test_major1_stale_schema_sidecar_recomputed_current_reused(tmp_path, monkeypatch):
    """MAJOR-1: when the scoring SEMANTICS change (SCORER_SCHEMA bump), a stale
    sidecar on disk MUST be recomputed, never reused. Two-cell on a real sm21
    reading attempt + real gt:

    * stale sidecar (real shape, scorer_schema='8') ⇒ `_score_attempt_output`
      IS invoked and the written sidecar carries the current schema.
    * current sidecar (scorer_schema=='9') ⇒ `_score_attempt_output` is NOT
      invoked (the valid sidecar is reused).

    The stale sidecar is built by running the real scorer once (so its SHAPE is
    authentic, not hand-faked) then rewriting only `scorer_schema` to the old
    value — exactly the on-disk shape MAJOR-1 is about."""
    attempt_dir = tmp_path / "0_reading" / "attempts" / "001"
    attempt_dir.mkdir(parents=True)
    shutil.copy2(_REAL_VIEWS_PATH, attempt_dir / "output.json")
    gt = load_gt("sm21_anchor")
    grade = rs.GradeConfig()

    # Spy that records whether the scorer ran, then delegates to the real one.
    real_score = rs._score_attempt_output
    calls: list[bool] = []

    def spy(stage, output, gt, *, grade):
        calls.append(True)
        return real_score(stage, output, gt, grade=grade)

    monkeypatch.setattr(rs, "_score_attempt_output", spy)

    # Produce an authentic current sidecar (no sidecar yet ⇒ forced recompute).
    rs._grade_attempt_artifacts("0_reading", "sm21_anchor", attempt_dir, gt, grade=grade)
    sidecar_path = attempt_dir / "score_vs_gt.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["scorer_schema"] == rs.SCORER_SCHEMA == "9"
    assert calls == [True]

    # Cell A — stale: rewrite the REAL sidecar's schema tag to the old value.
    sidecar["scorer_schema"] = "8"
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    calls.clear()
    out = rs._grade_attempt_artifacts("0_reading", "sm21_anchor", attempt_dir, gt, grade=grade)
    assert calls == [True], "a stale-schema sidecar MUST be recomputed, not reused"
    rewritten = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert rewritten["scorer_schema"] == "9"
    assert out["score_vs_gt"] is not None

    # Cell B — current: the valid sidecar is reused, scorer NOT invoked.
    calls.clear()
    rs._grade_attempt_artifacts("0_reading", "sm21_anchor", attempt_dir, gt, grade=grade)
    assert calls == [], "a current-schema sidecar must be reused, not recomputed"
