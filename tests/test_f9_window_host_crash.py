"""F-9 (2026-08-06): `resolve_window_hosts` conflicts hard-crash 1_correction.

Two real, independent接线缺口 (per the investigation
`AI_agent/logs/reviews/execution/2026-08-06_f9_rediagnosis_investigation_claude.md`
and the dispatch `AI_agent/logs/reviews/request/2026-08-06_f9_fix_and_c_design_dispatch_claude.md`):

1. `apply_v3_envelope_transaction`'s PRE-transform dry resolve
   (`envelope_transform.py:536`) had no `except WindowHostResolutionError`,
   unlike its POST-transform sibling (`:577-591`) — an asymmetry that let a
   raw `WindowHostResolutionError` escape the transaction entirely instead of
   being folded into a structured, audited `EnvelopeTransformRejected`.
2. `WindowHostResolutionError` carried no `.category` (unlike F-7's sibling
   `WindowResolverInputError`), so even a correctly-folded rejection could
   not be routed through `run_stage.py`'s existing "model_draw_error → file
   as failed attempt" mechanism — it had no fault classification to key on.

Both gaps had to close together: fixing (1) alone does NOT stop the crash,
because `finalize_correction_draw`'s OWN unconditional "final phase"
`resolve_window_hosts` call (`finalize.py:142`) reproduces the identical
conflicts on the same (unchanged) windows and is not wrapped by anything in
`finalize.py` — the exception still needs somewhere to land. This file's
first lock (`test_real_crash_run_no_longer_hard_crashes`) exercises the REAL
entry point end-to-end and would still be RED if either gap were fixed alone
(see the neuter notes below each test).

Fixture provenance (`tests/fixtures/f9_window_host_crash/`): a byte-for-byte
trim of the real crashing run
`run_2026-08-05_f7_verify_sonnet` (sm21_anchor, F-7-verify smoke run,
`.claude/worktrees/f7-manual`, only the files `_draw_correction` actually
reads: the six accepted `0_reading` stage-root views + attempt 001's
archived output, `_run/run_manifest.json` + `_run/view_manifest.json`, and
the crashing `1_correction/correction_geometry.json` + `evidence_debt.json`.
No bytes inside these files were edited.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import scripts.tool_scripts.run_stage as rs  # noqa: E402

from src.agent.correction.envelope_transform import (  # noqa: E402
    EnvelopeTransformRejected,
    apply_v3_envelope_transaction,
)
from src.agent.correction.finalize import finalize_correction_draw, FinalizeResult  # noqa: E402
from src.agent.correction.schema import CorrectedGeometryV3  # noqa: E402
from src.agent.correction.window_host import (  # noqa: E402
    WindowHostConflictV1,
    WindowHostResolutionError,
)
from src.agent.execution.policy import RunPolicy  # noqa: E402

_FIXTURE = Path("tests/fixtures/f9_window_host_crash")


def _copy_fixture_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run_x"
    shutil.copytree(_FIXTURE, run_dir)
    return run_dir


def _crashing_draw_geom(run_dir: Path) -> CorrectedGeometryV3:
    payload = json.loads((run_dir / "1_correction" / "correction_geometry.json").read_text(encoding="utf-8"))
    return CorrectedGeometryV3.model_validate(payload)


# =========================================================================== #
# Lock 1 — real entry point (`_draw_correction`, the actual 1_correction draw
# function StageRunner/step_orchestrator calls), with ONLY the LLM boundary
# (`run_correction`) stubbed to return the archived crashing draw. Every line
# of exception handling downstream — envelope reconcile, finalize, and the
# run_stage.py classification wiring — runs for real.
# =========================================================================== #
def test_real_crash_run_no_longer_hard_crashes(tmp_path, monkeypatch):
    run_dir = _copy_fixture_run(tmp_path)
    fixed_geom = _crashing_draw_geom(run_dir)

    import src.agent.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "run_correction", lambda *a, **k: fixed_geom.model_copy(deep=True))

    policy = RunPolicy(run_profile="exploratory", capability_profile="orthogonal_polygon")
    geom, rep = rs._draw_correction(run_dir, "", None, False, policy)

    # Must not raise (was the F-9 crash: WindowHostResolutionError propagating
    # uncaught out of `_draw_correction`). Must be filed as a blocked draw —
    # NOT silently accepted (a FinalizeResult would mean the mispairing rode
    # through undetected).
    assert not isinstance(geom, FinalizeResult)
    blocking_ids = {f.check_id for f in rep.blocking()}
    assert "correction.window_host_resolution" in blocking_ids, blocking_ids
    # The report must carry the actual conflicting window ids, not a vague
    # "something failed" — i.e. it consumed the real `.conflicts` payload.
    combined_message = " ".join(f.message for f in rep.results)
    for window_id in ("W-F1-N-1", "W-F1-N-3", "W-F2-N-1", "W-F2-N-2"):
        assert window_id in combined_message, combined_message


def test_real_crash_run_neuter_run_stage_wiring_removed_restores_crash(tmp_path, monkeypatch):
    """Neuter #1 (接线缺口 2.2): if run_stage.py stops catching
    `WindowHostResolutionError` (reverting to only catching
    `WindowResolverInputError`, its F-9-dispatch state), the SAME real run
    must crash again — proves lock 1 is bound to the run_stage.py wiring,
    not merely to the envelope_transform.py symmetry fix."""
    run_dir = _copy_fixture_run(tmp_path)
    fixed_geom = _crashing_draw_geom(run_dir)

    import src.agent.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "run_correction", lambda *a, **k: fixed_geom.model_copy(deep=True))

    # Neuter the throw site's own classification rather than the call site:
    # force `.category` to something run_stage.py's `!= "model_draw_error"`
    # branch will treat as non-recoverable, i.e. simulate "no classification
    # wired" by making every WindowHostResolutionError re-raise.
    monkeypatch.setattr(
        WindowHostResolutionError, "category", property(lambda self: "input_integrity_error")
    )

    policy = RunPolicy(run_profile="exploratory", capability_profile="orthogonal_polygon")
    with pytest.raises(WindowHostResolutionError):
        rs._draw_correction(run_dir, "", None, False, policy)


# =========================================================================== #
# Lock 2 — `WindowHostResolutionError.category`, the throw-site classification
# itself. Derived from each conflict's OWN `fallback_action` (set at ITS throw
# site inside window_host.py — never inferred from `str(exc)` / message text,
# never defaulted): any `invariant_no_geometry_commit` conflict marks the
# whole exception `input_integrity_error` (no resample can help); only when
# EVERY conflict is the softer `needs_input_no_geometry_commit` is it
# `model_draw_error` (a candidate for F-7's blind-resample archive-and-retry).
# =========================================================================== #
def _conflict(window_id: str, fallback_action: str, reason_code: str = "source_geometry_mismatch") -> WindowHostConflictV1:
    return WindowHostConflictV1(
        kind="window_host_conflict", conflict_schema_version="1", window_id=window_id,
        floor_id="floor-1", branch="elevation", reason_code=reason_code, raw_span=None,
        source_input_ids=(), candidate_segment_ids=(), candidate_room_ids=(), crossed_segment_ids=(),
        trusted_negative=(), upstream_error_code=None,
        failed_gate_id="correction.window_host_resolution", fallback_action=fallback_action, blocking=True,
    )


def test_category_all_model_draw_conflicts_is_model_draw_error():
    exc = WindowHostResolutionError((
        _conflict("W-1", "needs_input_no_geometry_commit"),
        _conflict("W-2", "needs_input_no_geometry_commit"),
    ))
    assert exc.category == "model_draw_error"


def test_category_any_invariant_conflict_is_input_integrity_error():
    exc = WindowHostResolutionError((
        _conflict("W-1", "needs_input_no_geometry_commit"),
        _conflict("W-2", "invariant_no_geometry_commit", reason_code="resolver_output_tampered"),
    ))
    assert exc.category == "input_integrity_error"


def test_category_all_invariant_conflicts_is_input_integrity_error():
    exc = WindowHostResolutionError((
        _conflict("W-1", "invariant_no_geometry_commit", reason_code="source_identity_invalid"),
    ))
    assert exc.category == "input_integrity_error"


def test_real_crash_conflicts_classify_as_model_draw_error(tmp_path, monkeypatch):
    """The real F-9 conflicts (4x `source_geometry_mismatch`,
    `needs_input_no_geometry_commit`) classify as `model_draw_error` — this is
    the throw-site-derived judgment call §2.2 of the dispatch asks for: a
    systematic mispairing of the correction draw's own OWN `source_ids`, not
    corrupted upstream data."""
    run_dir = _copy_fixture_run(tmp_path)
    fixed_geom = _crashing_draw_geom(run_dir)
    from src.agent.correction.window_sources import build_verified_window_inputs_from_run

    verified = build_verified_window_inputs_from_run(
        producer_draw=fixed_geom, run_dir=run_dir, reading_dir=run_dir / "0_reading",
    )
    with pytest.raises(WindowHostResolutionError) as excinfo:
        finalize_correction_draw(
            fixed_geom, vector_dir=run_dir / "0_reading",
            target=__import__("src.agent.correction.parse", fromlist=["correction_target"]).correction_target(
                "orthogonal_polygon"
            ),
            verified_window_inputs=verified,
        )
    assert excinfo.value.category == "model_draw_error"
    assert len(excinfo.value.conflicts) == 4
    assert {c.window_id for c in excinfo.value.conflicts} == {
        "W-F1-N-1", "W-F1-N-3", "W-F2-N-1", "W-F2-N-2",
    }
    assert {c.reason_code for c in excinfo.value.conflicts} == {"source_geometry_mismatch"}


# =========================================================================== #
# Lock 3 — `apply_v3_envelope_transaction`'s PRE-transform dry resolve is now
# symmetric with its POST-transform sibling: a non-invariant
# `WindowHostResolutionError` folds into a structured `EnvelopeTransformRejected`
# → the transaction returns `ok=False` with the conflict recorded in
# `.geom.conflicts` (NOT raised); an `invariant_no_geometry_commit` conflict
# still escapes as a raw raise (the "must never silently allow a commit"
# escape hatch flagged by the dispatch must survive the fix).
# =========================================================================== #
def test_pre_transform_conflict_folds_to_rejected_not_raised(tmp_path, monkeypatch):
    run_dir = _copy_fixture_run(tmp_path)
    fixed_geom = _crashing_draw_geom(run_dir)
    from src.agent.correction.window_sources import build_verified_window_inputs_from_run
    from src.agent.correction.config import load_core_tolerances
    from src.agent.correction.envelope import extract_authoritative_envelope

    verified = build_verified_window_inputs_from_run(
        producer_draw=fixed_geom, run_dir=run_dir, reading_dir=run_dir / "0_reading",
    )
    tol = load_core_tolerances()
    envelope = extract_authoritative_envelope(
        run_dir / "0_reading", footprint=fixed_geom, footprint_tolerance_m=tol.envelope_reconcile_tol_m, tol=tol,
    )
    result = apply_v3_envelope_transaction(
        fixed_geom, tol, envelope, verified_window_inputs=verified,
    )
    assert result.committed is False
    assert result.failed_gate_id == "correction.window_host_resolution"
    conflict_rows = [c for c in result.geom.conflicts if c.get("failed_gate_id") == "correction.window_host_resolution"]
    assert conflict_rows, result.geom.conflicts
    evidence_conflicts = conflict_rows[-1]["evidence"]["conflicts"]
    assert {row["window_id"] for row in evidence_conflicts} == {
        "W-F1-N-1", "W-F1-N-3", "W-F2-N-1", "W-F2-N-2",
    }


def test_pre_transform_invariant_conflict_still_raises(monkeypatch):
    """The `invariant_no_geometry_commit` escape hatch (dispatch §2.1 warning)
    must survive: neuter `_dry_resolve_current_ring` to raise an
    invariant-level conflict and confirm `apply_v3_envelope_transaction`
    still lets it through as a raw raise rather than folding it away."""
    import src.agent.correction.envelope_transform as et_mod

    def _fake_dry_resolve(geom, *, verified_window_inputs, tol, phase):
        if phase == "dry_pre_transform":
            raise WindowHostResolutionError((
                _conflict("W-X", "invariant_no_geometry_commit", reason_code="resolver_output_tampered"),
            ))
        raise AssertionError("post-transform dry resolve should not be reached in this test")

    monkeypatch.setattr(et_mod, "_dry_resolve_current_ring", _fake_dry_resolve)

    from src.agent.correction.schema import CorrectedGeometryV3
    from src.agent.correction.config import load_core_tolerances
    from src.agent.correction.envelope import AuthoritativeEnvelope

    # A geometry with no move intents still reaches the pre-transform dry
    # resolve (it only short-circuits on `not intents`, which is AFTER the
    # pre-transform call at :536) — but to keep this test hermetic we drive
    # `apply_v3_envelope_transaction` directly with a minimal v3 geom carrying
    # one window, matching the shape `_dry_resolve_current_ring` is invoked
    # under (`verified_window_inputs is not None`).
    tol = load_core_tolerances()
    run_dir = Path("tests/fixtures/f9_window_host_crash")
    payload = json.loads((run_dir / "1_correction" / "correction_geometry.json").read_text(encoding="utf-8"))
    geom = CorrectedGeometryV3.model_validate(payload)
    from src.agent.correction.window_sources import build_verified_window_inputs_from_run
    from src.agent.correction.envelope import extract_authoritative_envelope

    verified = build_verified_window_inputs_from_run(
        producer_draw=geom, run_dir=run_dir, reading_dir=run_dir / "0_reading",
    )
    envelope = extract_authoritative_envelope(
        run_dir / "0_reading", footprint=geom, footprint_tolerance_m=tol.envelope_reconcile_tol_m, tol=tol,
    )
    with pytest.raises(WindowHostResolutionError):
        apply_v3_envelope_transaction(geom, tol, envelope, verified_window_inputs=verified)
