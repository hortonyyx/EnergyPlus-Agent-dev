"""F-24 (2026-08-13, sol re-review of F-22 BLOCKER-1 round 2): the legacy
score sidecar cache (`scripts/tool_scripts/run_stage.py::_load_valid_score_sidecar`)
did not bind "the interpreter's currently expected trust identity" into its
cache predicate -- only `scorer_schema` (a hand-maintained version number
someone has to remember to bump), `stage`/`attempt`/`output_hash`/
`tolerances`. A cached sidecar computed under one live
`DETERMINISTIC_CORE_STAMP_VERSION`/`CORRECTION_OUTPUT_CONVENTION` pair would
be silently reused after either constant changed, as long as nobody also
remembered to bump `LEGACY_SCORE_CACHE_SCHEMA` in lockstep.

Dispatch: `AI_agent/logs/reviews/request/2026-08-13_aprime_cache_identity_dispatch_claude.md`.
Finding: `AI_agent/logs/reviews/verdict/2026-08-12_round3_full_body_crossreview_sol.md` §6.

Fix: `_current_scoring_semantics_identity()` (run_stage.py) reads BOTH
constants LIVE (module-qualified, not `from ... import`) and its return
value becomes an additional, SEPARATE field (`scoring_semantics`) in both
the cache predicate and the written sidecar. It is not a new hand-maintained
version number -- it is DERIVED from the same two constants that already
gate `_is_trusted_output_convention`/`_is_declared_output_convention`
(`src/agent/judge/correction_score.py`), so a bump to either one
automatically invalidates every existing cache entry with no separate
bump required.

Two locks, per the dispatch's explicit "both directions or it doesn't count"
requirement (this project's own F-19 "只有负向断言的门,恒红结构上不可观测"
precedent is the reason a positive-only pair of locks would not be trusted
here):

* Lock 1 (POSITIVE): identity unchanged -> the cached sidecar IS reused (the
  scorer is not invoked a second time). Without this lock, "always
  recompute" would trivially satisfy the negative lock below too.
* Lock 2/3 (NEGATIVE): only the live `DETERMINISTIC_CORE_STAMP_VERSION` (Lock
  2) or only the live `CORRECTION_OUTPUT_CONVENTION` (Lock 3) changes,
  nothing else -- `scorer_schema` still matches the on-disk sidecar's value
  (proving this is NOT the same signal `LEGACY_SCORE_CACHE_SCHEMA` already
  covers) -- and the cache MUST miss, the scorer MUST be invoked again.

A cheap, real-shape (not 2x2-degenerate) `0_reading` fixture is used for all
three locks: `0_reading` never reads either constant during scoring itself
(only `1_correction`'s `_is_trusted_output_convention` does), so a stage-0
recompute demonstrates the cache-predicate mechanism in isolation, with zero
risk of confounding "the cache missed" with "the scored numbers changed for
an unrelated reason" -- exactly the over-invalidation-is-safe property
`_current_scoring_semantics_identity`'s docstring documents.
"""
from __future__ import annotations

import json
from functools import wraps
from pathlib import Path

import pytest

import scripts.tool_scripts.run_stage as rs
import src.agent.correction.deterministic as deterministic_module
import src.agent.judge.correction_score as correction_score_module
from src.agent.judge.gt import load_gt


def _tiny_reading_output() -> dict:
    """A real-shape (not degenerate) single-room plan: four wall strokes
    forming a rectangle matching a matching gt footprint below. Deliberately
    the same minimal-but-real style `test_old_score_sidecar_schema_triggers_recompute_with_boundary`
    (test_judge_batch_b.py) already uses for cache-mechanics-only locks."""
    return {
        "1f_view": {
            "image_kind": "plan",
            "strokes": [
                {"pen": "wall", "geometry": {"p1": [0, 0], "p2": [10, 0]}},
                {"pen": "wall", "geometry": {"p1": [0, 4], "p2": [10, 4]}},
                {"pen": "wall", "geometry": {"p1": [0, 0], "p2": [0, 4]}},
                {"pen": "wall", "geometry": {"p1": [10, 0], "p2": [10, 4]}},
            ],
        }
    }


def _tiny_gt() -> dict:
    return {
        "footprint": {"W_m": 10.0, "D_m": 4.0},
        "floors": [
            {
                "name": "Floor 1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "zones": [{"rect_m": [0.0, 0.0, 10.0, 4.0]}],
            }
        ],
        "windows": [],
    }


def _seed_attempt(tmp_path: Path) -> Path:
    attempt_dir = tmp_path / "0_reading" / "attempts" / "001"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "output.json").write_text(json.dumps(_tiny_reading_output()), encoding="utf-8")
    return attempt_dir


def _spy_on_scorer(monkeypatch):
    real_score = rs._score_attempt_output
    calls: list[bool] = []

    @wraps(real_score)
    def spy(stage, output, gt, *, grade, core_proof=None):
        calls.append(True)
        return real_score(stage, output, gt, grade=grade, core_proof=core_proof)

    monkeypatch.setattr(rs, "_score_attempt_output", spy)
    return calls


# =========================================================================== #
# Mechanism-level self-test: the identity function itself is live, not a
# frozen snapshot (the "declaration is load-bearing, not decorative"
# discipline `CORRECTION_OUTPUT_CONVENTION`'s own module docstring requires).
# =========================================================================== #
def test_current_scoring_semantics_identity_reads_live_constants(monkeypatch):
    before = rs._current_scoring_semantics_identity()
    assert before == {
        "core_stamp_version": deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION,
        "output_convention": correction_score_module.CORRECTION_OUTPUT_CONVENTION,
        "scorer_implementation_sha256": rs._scorer_implementation_sha256(),
    }

    monkeypatch.setattr(deterministic_module, "DETERMINISTIC_CORE_STAMP_VERSION", "__f24_probe_stamp__")
    after_stamp = rs._current_scoring_semantics_identity()
    assert after_stamp["core_stamp_version"] == "__f24_probe_stamp__"
    assert after_stamp != before

    monkeypatch.undo()
    monkeypatch.setattr(correction_score_module, "CORRECTION_OUTPUT_CONVENTION", "__f24_probe_convention__")
    after_convention = rs._current_scoring_semantics_identity()
    assert after_convention["output_convention"] == "__f24_probe_convention__"
    assert after_convention != before


def test_current_scoring_semantics_identity_tracks_scorer_implementation(monkeypatch):
    """F-24 third identity: this is code-derived, not a third constant."""
    before = rs._current_scoring_semantics_identity()
    real_score = rs._score_attempt_output

    def replacement(stage, output, gt, *, grade, core_proof=None):
        return real_score(stage, output, gt, grade=grade, core_proof=core_proof)

    monkeypatch.setattr(rs, "_score_attempt_output", replacement)
    after = rs._current_scoring_semantics_identity()
    assert after["scorer_implementation_sha256"] != before["scorer_implementation_sha256"]
    assert after["core_stamp_version"] == before["core_stamp_version"]
    assert after["output_convention"] == before["output_convention"]


# =========================================================================== #
# Lock 1 (POSITIVE): identity unchanged -> cache hits, scorer not re-invoked.
# =========================================================================== #
def test_lock1_cache_hits_when_identity_unchanged(tmp_path, monkeypatch):
    attempt_dir = _seed_attempt(tmp_path)
    gt = _tiny_gt()
    grade = rs.GradeConfig()

    # First call: no sidecar on disk yet -> forced compute + write.
    rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=grade)
    sidecar_path = attempt_dir / "score_vs_gt.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["scoring_semantics"] == {
        "core_stamp_version": deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION,
        "output_convention": correction_score_module.CORRECTION_OUTPUT_CONVENTION,
        "scorer_implementation_sha256": rs._scorer_implementation_sha256(),
    }

    # Second call: nothing changed on disk or in the live constants -> the
    # cached sidecar must be reused, not recomputed.
    calls = _spy_on_scorer(monkeypatch)
    rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=grade)
    assert calls == [], "identity-unchanged cache entry must be reused, not recomputed"


# =========================================================================== #
# Lock 2 (NEGATIVE): only the live core-stamp-version constant changes ->
# cache MUST miss even though `scorer_schema` on disk still matches.
# =========================================================================== #
def test_lock2_core_stamp_version_bump_invalidates_cache(tmp_path, monkeypatch):
    attempt_dir = _seed_attempt(tmp_path)
    gt = _tiny_gt()
    grade = rs.GradeConfig()

    rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=grade)
    sidecar_path = attempt_dir / "score_vs_gt.json"
    sidecar_before = json.loads(sidecar_path.read_text(encoding="utf-8"))

    # Simulate a live core-version bump WITHOUT touching the on-disk sidecar
    # and WITHOUT bumping `LEGACY_SCORE_CACHE_SCHEMA` -- exactly sol's dynamic
    # probe ("先构造合法 cache,再只改 live expected stamp version").
    monkeypatch.setattr(deterministic_module, "DETERMINISTIC_CORE_STAMP_VERSION", "__f24_bumped__")
    calls = _spy_on_scorer(monkeypatch)
    rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=grade)
    assert calls == [True], "a live core-stamp-version bump must invalidate the cache"

    sidecar_after = json.loads(sidecar_path.read_text(encoding="utf-8"))
    # Proves this is NOT the signal `scorer_schema` alone already covers: the
    # legacy schema label is untouched on both sides of the bump.
    assert sidecar_before["scorer_schema"] == sidecar_after["scorer_schema"] == rs.LEGACY_SCORE_CACHE_SCHEMA
    assert sidecar_after["scoring_semantics"]["core_stamp_version"] == "__f24_bumped__"


# =========================================================================== #
# Lock 3 (NEGATIVE): only the live output-convention constant changes ->
# cache MUST miss, same discipline as Lock 2 for the other identity half.
# =========================================================================== #
def test_lock3_output_convention_change_invalidates_cache(tmp_path, monkeypatch):
    attempt_dir = _seed_attempt(tmp_path)
    gt = _tiny_gt()
    grade = rs.GradeConfig()

    rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=grade)
    sidecar_path = attempt_dir / "score_vs_gt.json"
    sidecar_before = json.loads(sidecar_path.read_text(encoding="utf-8"))

    monkeypatch.setattr(correction_score_module, "CORRECTION_OUTPUT_CONVENTION", "__f24_bumped_convention__")
    calls = _spy_on_scorer(monkeypatch)
    rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=grade)
    assert calls == [True], "a live output-convention change must invalidate the cache"

    sidecar_after = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar_before["scorer_schema"] == sidecar_after["scorer_schema"] == rs.LEGACY_SCORE_CACHE_SCHEMA
    assert sidecar_after["scoring_semantics"]["output_convention"] == "__f24_bumped_convention__"


def test_lock4_scorer_implementation_replacement_invalidates_cache(tmp_path, monkeypatch):
    """Replacing scorer code invalidates a sidecar with both constants live."""
    attempt_dir = _seed_attempt(tmp_path)
    gt = _tiny_gt()
    grade = rs.GradeConfig()
    rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=grade)
    before = json.loads((attempt_dir / "score_vs_gt.json").read_text(encoding="utf-8"))
    real_score = rs._score_attempt_output
    calls: list[bool] = []

    def replacement(stage, output, gt, *, grade, core_proof=None):
        calls.append(True)
        return real_score(stage, output, gt, grade=grade, core_proof=core_proof)

    monkeypatch.setattr(rs, "_score_attempt_output", replacement)
    rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=grade)
    after = json.loads((attempt_dir / "score_vs_gt.json").read_text(encoding="utf-8"))
    assert calls == [True]
    assert before["scorer_schema"] == after["scorer_schema"] == rs.LEGACY_SCORE_CACHE_SCHEMA
    assert before["scoring_semantics"]["core_stamp_version"] == after["scoring_semantics"]["core_stamp_version"]
    assert before["scoring_semantics"]["output_convention"] == after["scoring_semantics"]["output_convention"]
    assert before["scoring_semantics"]["scorer_implementation_sha256"] != after["scoring_semantics"]["scorer_implementation_sha256"]
