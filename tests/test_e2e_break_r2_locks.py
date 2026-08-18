"""Locks for the sm21 e2e-break isolation→correction wall (r2 + F-2c).

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
  sidecar cache key (`LEGACY_SCORE_CACHE_SCHEMA`, then named `SCORER_SCHEMA`) did
  not, so a stale sidecar short-circuited
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
from src.agent.correction.window_sources import (
    WindowResolverInputError,
    verify_reading_stage_root_against_accepted_attempt,
)
from src.agent.execution.evidence_preflight import EvidenceDebt, EvidenceDebtItem
from src.agent.execution.isolation import build_isolation_workspace, merge_isolated_output
from src.agent.execution.manifest import (
    ensure_run_manifest_v2,
    hash_file,
    hash_text,
    load_run_manifest,
)
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
    return build_isolation_workspace(
        case_dir,
        run_dir=run_dir,
        staging_root=staging_root,
        pilot_review_gate=False,
    )


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
# F-2c — merge writes flat per-view mirrors; the verifier binds them to the
# accepted archive by the accepted product's OWN contract shape (envelope wrap
# for the isolated merge, flat for the legacy writer). Three locks: end-to-end
# (isolated merge now verifies), anti-swap (one swapped coordinate still
# rejected — the gate cannot go恒真), and flat-path regression (unchanged).
# =========================================================================== #
def _isolated_merge_run(tmp_path: Path) -> Path:
    """Real clean-room build + real six-view aggregate + merge (accepted). The
    post-merge stage root is where F-2c-1's flat mirrors must land."""
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    workspace = _formal_build(_SM21, run_dir, tmp_path / "staging")
    staging = workspace.staging_root
    (staging / "out" / "output.json").write_text(
        json.dumps({"views": _real_views()}), encoding="utf-8"
    )
    merge_isolated_output(staging, run_dir)
    return run_dir


def test_f2c1_isolated_merge_mirrors_views_and_verifies(tmp_path: Path):
    """F-2c-1 + F-2c-2 end-to-end: after an isolated merge, each accepted view is
    mirrored to ``0_reading/<view_id>.json`` (content = the view object itself,
    derived from the accepted payload — never re-parsed from source), and the
    source verifier — which pre-F-2c reconstructed ``{}`` (no flat files) and
    died on the envelope/floor shape mismatch — now binds those mirrors to the
    envelope accepted archive.

    Neuter: drop the mirror-writing loop in ``merge_isolated_output`` ⇒ the
    ``0_reading/*_view.json`` glob is empty ⇒ the verifier rebuilds ``{}``,
    wraps it to ``{"views": {}}``, and reds on the canonical mismatch (and the
    mirror-existence assertions red directly)."""
    run_dir = _isolated_merge_run(tmp_path)
    assert load_run_manifest(run_dir).accepted("0_reading") is not None  # mirrors are accept-gated

    views = _real_views()
    mirrored = sorted(p.name for p in (run_dir / "0_reading").glob("*_view.json"))
    assert mirrored == sorted(f"{view_id}.json" for view_id in views)
    for view_id, view in views.items():
        assert json.loads((run_dir / "0_reading" / f"{view_id}.json").read_text()) == view

    # The wall: the isolated path now reaches correction's source verifier.
    verify_reading_stage_root_against_accepted_attempt(run_dir, run_dir / "0_reading")  # no raise


def _bump_first_coordinate(view: dict) -> None:
    """Mutate the first wall-stroke endpoint in place — a real coordinate swap
    (not a synthetic field), robust to the exact stroke order of the fixture."""
    for stroke in view.get("strokes", []):
        geometry = stroke.get("geometry") or {}
        p1 = geometry.get("p1")
        if isinstance(p1, list) and len(p1) == 2 and isinstance(p1[0], (int, float)):
            p1[0] = p1[0] + 1000.0
            return
    raise AssertionError("no mutable coordinate found in view (fixture drift)")


def test_f2c2_tampered_mirror_coordinate_is_rejected(tmp_path: Path):
    """F-2c-2 anti-swap (the function's only reason to exist): once the mirrors
    are written, swapping ONE coordinate in ONE view's mirror MUST still be
    rejected — adding the mirrors cannot turn this gate恒真. Two-cell on the same
    post-merge run: clean verifies, then reds after a single coordinate swap.

    Neuter: collapse the canonical comparison (e.g. make it a tautology) ⇒ the
    swapped-coordinate cell stops raising ⇒ this lock reds."""
    run_dir = _isolated_merge_run(tmp_path)
    reading_dir = run_dir / "0_reading"

    # Cell 1 — clean: the accepted mirrors verify.
    verify_reading_stage_root_against_accepted_attempt(run_dir, reading_dir)

    # Cell 2 — swap one real coordinate in the 1f_view mirror only; the accepted
    # archive under attempts/ is untouched, so the mirrors now diverge from it.
    mirror = reading_dir / "1f_view.json"
    assert mirror.is_file()
    tampered = json.loads(mirror.read_text())
    _bump_first_coordinate(tampered)
    mirror.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(WindowResolverInputError, match="accepted_attempt_mismatch"):
        verify_reading_stage_root_against_accepted_attempt(run_dir, reading_dir)


def test_f2c3_flat_path_verifies_and_flat_archive_is_unchanged(tmp_path: Path):
    """F-2c-3 regression: the flat path is untouched. Its accepted archive stays
    FLAT (``{stem: view}``, no envelope) — written byte-for-byte by the real
    flat StageRunner writer, which F-2c does not modify — and the verifier binds
    the flat mirrors to that flat archive with NO envelope wrap. Catches any
    F-2c-2 change that breaks the flat path's verify (e.g. always wrapping)."""
    views = _real_views()
    run_dir = tmp_path / "flat_run"
    run_dir.mkdir()
    reading_dir = run_dir / "0_reading"
    reading_dir.mkdir(parents=True)
    # Flat reader working copy (the *_view.json mirrors the flat flow reads).
    for stem, view in views.items():
        (reading_dir / f"{stem}.json").write_text(
            json.dumps(view, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    manifest = ensure_run_manifest_v2(run_dir, view_manifest_sha256="a" * 64)
    out = {stem: json.loads((reading_dir / f"{stem}.json").read_text()) for stem in views}
    rep = CheckReport(stage="0_reading")
    rep.add_pass("flat.lock", CheckLayer.INVARIANT)
    # Archive + accept EXACTLY as the flat StageRunner writer does, then persist
    # the manifest (StageRunner.record mutates in memory only — the flat flow
    # saves after each stage; without this, accepted("0_reading") is None and the
    # verifier would early-return without ever comparing, hiding a regression).
    StageRunner(run_dir, manifest).record(
        stage="0_reading", stage_dir=reading_dir, output_obj=out, report=rep, accept=True,
    )
    manifest.save(run_dir)
    assert load_run_manifest(run_dir).accepted("0_reading") is not None  # guard against a false lock

    accepted_path = reading_dir / "attempts" / "001" / "output.json"
    accepted_text = accepted_path.read_text(encoding="utf-8")
    accepted = json.loads(accepted_text)
    assert "views" not in accepted  # FLAT, not the isolated envelope
    assert accepted == out  # the flat writer's exact payload, round-trip stable
    assert accepted_text == json.dumps(out, indent=2, ensure_ascii=False)  # byte-exact
    # The verifier binds the flat mirrors to the flat archive (no wrap).
    verify_reading_stage_root_against_accepted_attempt(run_dir, reading_dir)  # no raise


def test_f2c_rework_r1_stale_stage_root_mirrors_cleaned_before_accept(tmp_path):
    """F-2c rework r1 (MAJOR ④, sol cross-review): a REAL pre-state — the stage
    root already holds a stale/extra ``*_view.json`` left by a prior round (more
    mirrors than the accepted attempt produces). Pre-fix, merge wrote the
    accepted pointer and the new mirrors WITHOUT removing the stale one, so the
    next stage's ``verify_reading_stage_root_against_accepted_attempt`` rebuilt
    ``current`` from ALL ``*_view.json`` (stale included) and hard-crashed on
    ``accepted_attempt_mismatch`` — "accept first, crash next stage", masked by
    clean tmp fixtures. Post-fix, merge removes stale ``*_view.json`` and writes
    the accepted mirrors BEFORE the accepted pointer, so verify binds cleanly."""
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    workspace = _formal_build(_SM21, run_dir, tmp_path / "staging")
    staging = workspace.staging_root
    # Real pre-state: a previous round left a stale extra view mirror at the
    # stage root before this merge runs.
    reading_dir = run_dir / "0_reading"
    reading_dir.mkdir(parents=True)
    (reading_dir / "stale_view.json").write_text(
        json.dumps({"strokes": [], "uncaptured": []}), encoding="utf-8")

    (staging / "out" / "output.json").write_text(json.dumps({"views": _real_views()}), encoding="utf-8")
    merge_isolated_output(staging, run_dir)

    # The stale mirror is gone — exactly the accepted views remain at the root.
    mirrors = sorted(p.name for p in reading_dir.glob("*_view.json"))
    assert "stale_view.json" not in mirrors
    assert mirrors == sorted(f"{view_id}.json" for view_id in _real_views())

    # The next stage's source verifier binds cleanly (no accepted_attempt_mismatch
    # from the stale extra).
    verify_reading_stage_root_against_accepted_attempt(run_dir, reading_dir)  # no raise


# =========================================================================== #
# F-2c §3 — exactly one reading-contract detector in the repo (no second ruler)
# =========================================================================== #
def test_f2c_single_contract_detector_is_canonical():
    """F-2c §3: there is exactly ONE reading-contract shape detector.  The
    judge-side re-export points (``reading_typed_adapter``, ``score_schema``)
    must BE the reading-package object — the same function, not a same-named
    reimplementation — and a source scan of ``src/`` finds exactly one
    ``def identify_reading_contract``.  The recognized contract id is a single
    record: a recognized envelope yields ``READING_PRODUCT_CONTRACT`` (the
    dataclass field's Literal derives from that constant).  Catches a future
    re-clone — the second-ruler failure mode this project has hit repeatedly
    (scoring double-ruler, vocab double-record) — the moment it appears.

    Neuter: (a) re-``def identify_reading_contract`` anywhere in ``src/`` ⇒ the
    source-scan assertion reds; (b) stop re-exporting the canonical object from
    a judge module (e.g. redefine it there) ⇒ the ``is`` assertions red."""
    import src.agent.judge.reading_typed_adapter as rta
    import src.agent.judge.score_schema as ss
    import src.agent.reading.contract as rdc

    # The judge re-export points bind the canonical object — not clones.
    assert rta.identify_reading_contract is rdc.identify_reading_contract
    assert rta.READING_PRODUCT_CONTRACT is rdc.READING_PRODUCT_CONTRACT
    assert rta.READING_CONTRACT_DETECTOR_VERSION is rdc.READING_CONTRACT_DETECTOR_VERSION
    assert ss.READING_PRODUCT_CONTRACT is rdc.READING_PRODUCT_CONTRACT
    assert ss.READING_CONTRACT_DETECTOR_VERSION is rdc.READING_CONTRACT_DETECTOR_VERSION

    # Single record for the recognized id: a recognized envelope yields the constant.
    assert rdc.identify_reading_contract({"views": {}}).contract_id == rdc.READING_PRODUCT_CONTRACT

    # Exactly one detector definition across the production source tree.
    hits = [
        str(path)
        for path in Path("src").rglob("*.py")
        if "def identify_reading_contract" in path.read_text(encoding="utf-8")
    ]
    assert hits == ["src/agent/reading/contract.py"], hits


# =========================================================================== #
# MAJOR-1 — a stale-schema sidecar is recomputed, a current one reused (two-cell)
# =========================================================================== #
def test_major1_stale_schema_sidecar_recomputed_current_reused(tmp_path, monkeypatch):
    """MAJOR-1: when the scoring SEMANTICS change (`LEGACY_SCORE_CACHE_SCHEMA`
    bump, named `SCORER_SCHEMA` before the NIT-F25 rename), a stale sidecar
    on disk MUST be recomputed, never reused. Two-cell on a real sm21
    reading attempt + real gt:

    * stale sidecar (real shape, scorer_schema='10', the value immediately
      prior to the current one) ⇒ `_score_attempt_output` IS invoked and the
      written sidecar carries the current schema.
    * current sidecar (scorer_schema==rs.LEGACY_SCORE_CACHE_SCHEMA, currently
      '11') ⇒ `_score_attempt_output` is NOT invoked (the valid sidecar is
      reused).

    The stale sidecar is built by running the real scorer once (so its SHAPE is
    authentic, not hand-faked) then rewriting only `scorer_schema` to the old
    value — exactly the on-disk shape MAJOR-1 is about. Literal values are
    kept in sync with `rs.LEGACY_SCORE_CACHE_SCHEMA` each time it bumps
    (NIT-1, F-22 2026-08-11; F-22 BLOCKER-1 round 2, 2026-08-13, bumped "10"
    -> "11") so this docstring never reads stale against the assertions
    below. F-24 (2026-08-13, same day): this schema label is now a SEPARATE
    predicate field alongside `scoring_semantics` -- rewriting only
    `scorer_schema` still exercises the schema-label half of the predicate,
    which is what this lock is about; `scoring_semantics` stays correct
    (untouched) in both cells here, so it is not what makes cell A stale."""
    attempt_dir = tmp_path / "0_reading" / "attempts" / "001"
    attempt_dir.mkdir(parents=True)
    shutil.copy2(_REAL_VIEWS_PATH, attempt_dir / "output.json")
    gt = load_gt("sm21_anchor")
    grade = rs.GradeConfig()

    # Spy that records whether the scorer ran, then delegates to the real one.
    real_score = rs._score_attempt_output
    calls: list[bool] = []

    def spy(stage, output, gt, *, grade, core_proof=None):
        calls.append(True)
        return real_score(stage, output, gt, grade=grade, core_proof=core_proof)

    monkeypatch.setattr(rs, "_score_attempt_output", spy)

    # Produce an authentic current sidecar (no sidecar yet ⇒ forced recompute).
    # F-22 BLOCKER-1 round 2 (2026-08-13) bumped the legacy schema label
    # "10" -> "11" (trust semantics + `output_convention` sidecar shape
    # changed again — gained a `declared` key); this lock is updated to the
    # current value so the bump stays a conscious, verified act (not
    # silently masked).
    rs._grade_attempt_artifacts("0_reading", "sm21_anchor", attempt_dir, gt, grade=grade)
    sidecar_path = attempt_dir / "score_vs_gt.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["scorer_schema"] == rs.LEGACY_SCORE_CACHE_SCHEMA == "11"
    assert calls == [True]

    # Cell A — stale: rewrite the REAL sidecar's schema tag to the immediately
    # prior value (exactly what would be on disk from before the F-22
    # BLOCKER-1 round 2 bump).
    sidecar["scorer_schema"] = "10"
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    calls.clear()
    out = rs._grade_attempt_artifacts("0_reading", "sm21_anchor", attempt_dir, gt, grade=grade)
    assert calls == [True], "a stale-schema sidecar MUST be recomputed, not reused"
    rewritten = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert rewritten["scorer_schema"] == "11"
    assert out["score_vs_gt"] is not None

    # Cell B — current: the valid sidecar is reused, scorer NOT invoked.
    calls.clear()
    rs._grade_attempt_artifacts("0_reading", "sm21_anchor", attempt_dir, gt, grade=grade)
    assert calls == [], "a current-schema sidecar must be reused, not recomputed"
