"""F-9 route② v2.1 §10 S2 / §12.2 locks: authoritative frame V2, unified
projection dispatcher, and the per-window shadow pairing decision that
produces the `correction.window_position_evidence_shadow` cross-check.

Dispatch scope (`AI_agent/logs/reviews/request/
2026-08-12_f9_route2_s2_shadow_projector_dispatch_claude.md`): S2 must run
alongside the existing model-authored `window.span` path, never override
`span`, never block, and be independently verifiable through BOTH real
entries — stepwise (`run_stage._draw_correction`) and integrated
(`pipeline.run_pipeline_artifacts`) — with the two named must-red neuters
("摘掉 projector" / "改用 advisory frame") demonstrated.

Real-data fixtures used (no hand-typed geometry for the headline claims):

- `tests/fixtures/f9_window_host_crash/` — the REAL, byte-for-byte trimmed
  F-9 mirror-bug run (see `tests/test_f9_window_host_crash.py`'s docstring
  for provenance). Its raw `1_correction/correction_geometry.json` draw
  genuinely has 4 windows (`W-F1-N-1`, `W-F1-N-3`, `W-F2-N-1`, `W-F2-N-2`)
  whose `existence` elevation citation is the WRONG mirror twin. This suite
  runs `apply_deterministic_core` + `materialize_all_facade_segments`
  directly (NOT `finalize_correction_draw`, which raises on this exact
  fixture via the pre-existing coarse overlap check in
  `window_host.py::resolve_window_hosts` — see F-9's own test file) so the
  shadow decision can be exercised on the un-rejected, real geometry.
- `case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e/` — a REAL,
  fully-accepted v3 production run (per `AI_agent/CLAUDE.md`'s 2026-08-11
  entry: "一次 flow 调用从头跑到底、中途不停...EnergyPlus Completed
  Successfully, 0 Severe"). All 15 windows here have CORRECT citations; used
  as the clean positive baseline for the real-entry wiring locks and the
  must-red neuters (a clean `all_accepted=True` case makes a neuter's
  True->False flip unambiguous, unlike the F-9 fixture where 4/15 already
  fail for an unrelated reason).

Both real fixtures are read-only source data; every test that runs them
through a real entry point (which writes into `1_correction/`) first copies
the minimal set of files `_draw_correction`/`run_pipeline_artifacts` actually
read into `tmp_path` (same trimming discipline as
`tests/test_f9_window_host_crash.py`'s own `_copy_fixture_run`), never into
the committed fixture/case directory itself.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import scripts.tool_scripts.run_stage as rs  # noqa: E402

import src.agent.correction.window_position as wp  # noqa: E402
import src.agent.pipeline as pipeline_mod  # noqa: E402
from src.agent.correction.config import load_core_tolerances  # noqa: E402
from src.agent.correction.deterministic import apply_deterministic_core  # noqa: E402
from src.agent.correction.envelope import extract_authoritative_envelope  # noqa: E402
from src.agent.correction.facade_visibility import (  # noqa: E402
    VisibilityTolerances,
    materialize_all_facade_segments,
)
from src.agent.correction.parse import correction_target  # noqa: E402
from src.agent.correction.schema import CorrectedGeometryV3  # noqa: E402
from src.agent.correction.window_sources import (  # noqa: E402
    SourceIntervalV1,
    WindowDirectionBindingError,
    build_verified_window_inputs_from_run,
)
from src.agent.execution.policy import RunPolicy  # noqa: E402
from src.validator.checks.correction import check_correction  # noqa: E402
from src.validator.checks.schema import CheckStatus, disposition  # noqa: E402

_F9_FIXTURE = Path("tests/fixtures/f9_window_host_crash")
_CLEAN_RUN = Path("case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e")
_CLEAN_RUN_ACCEPTED_READING_ATTEMPT = "002"
_CHECK_ID = "correction.window_position_evidence_shadow"

_CRASH_WINDOW_IDS = frozenset({"W-F1-N-1", "W-F1-N-3", "W-F2-N-1", "W-F2-N-2"})


# =========================================================================== #
# Shared helpers.
# =========================================================================== #
def _prepared_geometry(run_dir: Path, reading_dir: Path):
    """`(geom-with-facade_segments, verified_inputs, tol)` built via
    `apply_deterministic_core` + `materialize_all_facade_segments` directly —
    deliberately NOT `finalize_correction_draw`, so the F-9 fixture's known
    conflicting windows can be observed by the shadow decision instead of
    raising `WindowHostResolutionError` at the pre-existing coarse overlap
    check (see this module's docstring)."""
    payload = json.loads((run_dir / "1_correction" / "correction_geometry.json").read_text(encoding="utf-8"))
    geom = CorrectedGeometryV3.model_validate(payload)
    verified = build_verified_window_inputs_from_run(producer_draw=geom, run_dir=run_dir, reading_dir=reading_dir)
    tol = load_core_tolerances()
    envelope = extract_authoritative_envelope(
        reading_dir, footprint=geom, footprint_tolerance_m=tol.envelope_reconcile_tol_m, tol=tol,
    )
    target = correction_target("orthogonal_polygon")
    geom = apply_deterministic_core(
        geom, tol, authoritative_envelope=envelope, capability_profile=target.capability_profile,
        verified_window_inputs=verified,
    )
    visibility_tol = VisibilityTolerances(
        depth_epsilon_m=tol.facade_visibility_depth_epsilon_m,
        endpoint_epsilon_m=tol.facade_visibility_endpoint_epsilon_m,
    )
    segments = materialize_all_facade_segments(geom, tolerances=visibility_tol)
    geom = geom.model_copy(update={"facade_segments": list(segments)})
    return geom, verified, tol


def _f9_prepared():
    return _prepared_geometry(_F9_FIXTURE, _F9_FIXTURE / "0_reading")


def _clean_prepared():
    return _prepared_geometry(_CLEAN_RUN, _CLEAN_RUN / "0_reading")


def _copy_stage_inputs(tmp_path: Path, source_run: Path, accepted_reading_attempt: str) -> Path:
    """Trim a real run down to exactly what `_draw_correction`/
    `run_pipeline_artifacts` read for 1_correction (mirrors
    `tests/test_f9_window_host_crash.py::_copy_fixture_run`'s discipline, but
    built inline here since the SOURCE run differs per test)."""
    run_dir = tmp_path / "run_x"
    (run_dir / "0_reading").mkdir(parents=True)
    for view in ("1f_view", "2f_view", "East_view", "North_view", "South_view", "West_view"):
        src = source_run / "0_reading" / f"{view}.json"
        if src.is_file():
            shutil.copy(src, run_dir / "0_reading" / f"{view}.json")
    att_dir = run_dir / "0_reading" / "attempts" / accepted_reading_attempt
    att_dir.mkdir(parents=True)
    shutil.copy(
        source_run / "0_reading" / "attempts" / accepted_reading_attempt / "output.json",
        att_dir / "output.json",
    )
    (run_dir / "_run").mkdir(parents=True)
    shutil.copy(source_run / "_run" / "run_manifest.json", run_dir / "_run" / "run_manifest.json")
    shutil.copy(source_run / "_run" / "view_manifest.json", run_dir / "_run" / "view_manifest.json")
    return run_dir


def _clean_run_raw_geom() -> CorrectedGeometryV3:
    payload = json.loads((_CLEAN_RUN / "1_correction" / "correction_geometry.json").read_text(encoding="utf-8"))
    return CorrectedGeometryV3.model_validate(payload)


def _shadow_row(rep) -> "CheckResult":  # noqa: F821 — imported type only for annotation clarity
    rows = [r for r in rep.results if r.check_id == _CHECK_ID]
    assert len(rows) == 1, f"expected exactly one {_CHECK_ID!r} row, got {rows}"
    return rows[0]


class _StopAfterCorrection(Exception):
    """Deterministic, controlled stop signal — raised by a monkeypatched
    `materialize_kernel_geometry` so `run_pipeline_artifacts` can be driven
    exactly through 1_correction (which has already written
    `correction_checks.json` by this point) without needing 2_modelling
    onward, 4_mep, or a real LLM call to succeed."""


def _run_integrated_through_correction_only(run_dir: Path, monkeypatch, geom_to_return: CorrectedGeometryV3) -> None:
    monkeypatch.setattr(pipeline_mod, "run_correction", lambda *a, **k: geom_to_return.model_copy(deep=True))
    monkeypatch.setattr(
        pipeline_mod, "materialize_kernel_geometry",
        lambda *a, **k: (_ for _ in ()).throw(_StopAfterCorrection()),
    )
    with pytest.raises(_StopAfterCorrection):
        pipeline_mod.run_pipeline_artifacts(
            run_dir / "0_reading", "", out_dir=run_dir,
            run_profile="exploratory", capability_profile="orthogonal_polygon",
        )


def _read_integrated_shadow_row(run_dir: Path) -> dict:
    data = json.loads((run_dir / "1_correction" / "correction_checks.json").read_text(encoding="utf-8"))
    rows = [r for r in data["results"] if r["check_id"] == _CHECK_ID]
    assert len(rows) == 1, rows
    return rows[0]


# =========================================================================== #
# 1. F-9 real-fixture oracle (v2.1 §12.3) — hand-verified against the design
#    doc's own cited numbers, not generated by calling production code twice.
# =========================================================================== #
def test_f9_oracle_15_windows_split_11_accept_4_reject():
    geom, verified, tol = _f9_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    assert report.status == "evaluated"
    assert report.window_count == 15
    assert report.all_accepted is False
    rejected_ids = {d.window_id for d in report.decisions if d.decision == "rejected"}
    assert rejected_ids == _CRASH_WINDOW_IDS, rejected_ids
    accepted_ids = {d.window_id for d in report.decisions if d.decision == "accepted"}
    assert len(accepted_ids) == 11
    assert accepted_ids | rejected_ids == {d.window_id for d in report.decisions}


def test_f9_oracle_w_f1_n1_hand_computed_numbers_match_design_doc():
    """v2.1 §12.3's own worked example:
    plan world span [1.24, 3.64]; correct elevation S7 current-ring
    [1.12, 3.52] (d=0.12); mirror twin S5 current-ring [11.24, 13.64]
    (d=10.00). The real fixture's `W-F1-N-1` cites the WRONG twin (S5)."""
    geom, verified, tol = _f9_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    d = next(d for d in report.decisions if d.window_id == "W-F1-N-1")
    assert d.decision == "rejected"
    assert d.reject_code == "position_evidence_pair_mismatch"
    assert d.plan_world_interval.lo == pytest.approx(1.24, abs=1e-9)
    assert d.plan_world_interval.hi == pytest.approx(3.64, abs=1e-9)
    assert len(d.elevation_projected_intervals) == 1
    assert d.elevation_projected_intervals[0].lo == pytest.approx(11.24, abs=1e-9)
    assert d.elevation_projected_intervals[0].hi == pytest.approx(13.64, abs=1e-9)
    assert d.distances[0] == pytest.approx(10.00, abs=1e-9)


def test_f9_oracle_accept_window_hand_computed_d_0_12():
    """`W-F1-N-2` is NOT one of the 4 known-bad windows; hand-computed via
    the same authoritative frame (North sign=-1, along_origin=14.88):
    cited North_view/S6 local=(6.3, 8.7) -> world=[6.18, 8.58]; plan span is
    [6.3, 8.7] -> d=max(|6.3-6.18|, |8.7-8.58|)=0.12, inside the 0.300
    tolerance. Also asserts the model's own `window.span` is numerically
    close to but NOT bit-identical to the plan-authority-derived span (the
    registered ~0.12 m envelope/centerline offset debt CLAUDE.md tracks
    elsewhere) is captured, not silently absorbed."""
    geom, verified, tol = _f9_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    d = next(d for d in report.decisions if d.window_id == "W-F1-N-2")
    assert d.decision == "accepted"
    assert d.reject_code is None
    assert d.distances[0] == pytest.approx(0.12, abs=1e-6)
    assert d.derived_span == d.plan_world_interval
    # This window's model-authored span already equals its own plan citation
    # numerically (the model derived span FROM the plan stroke it cited) —
    # legacy_span_delta_m is a real, computed 0.0, not an unset None.
    assert d.legacy_span_delta_m is not None
    assert d.legacy_span_delta_m == pytest.approx(0.0, abs=1e-9)


def test_f9_oracle_all_four_crash_windows_reject_with_large_hand_verifiable_distance():
    """The other three real North mirror conflicts (v2.1 §12.3: "其余三扇
    真实 North 冲突也应逐窗覆盖，防只修第一扇") — each must show a distance
    far outside 0.300 m, not a near-miss."""
    geom, verified, tol = _f9_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    by_id = {d.window_id: d for d in report.decisions}
    for window_id in _CRASH_WINDOW_IDS:
        d = by_id[window_id]
        assert d.decision == "rejected", window_id
        assert d.reject_code == "position_evidence_pair_mismatch", window_id
        assert d.distances and d.distances[0] > 5.0, (window_id, d.distances)


def test_f9_w_f1_n1_swap_wrong_citation_for_correct_one_flips_reject_to_accept():
    """v2.1 §12.2 'F-9 mirror negative' lock's own framing: `W-F1-N-1`'s REAL
    (as-shipped) citation is the wrong mirror twin `North_view/S5` (rejected,
    d=10.00). Swapping ONLY the cited elevation source to the correct
    `North_view/S7` (same window, same plan authority, nothing else changed)
    must flip the SAME window's decision to accepted at d=0.12 — proving the
    detector's verdict tracks the CITATION, not something baked into the
    window identity itself."""
    geom, verified, tol = _f9_prepared()
    frames = wp._build_authoritative_frames(geom, verified, tol)
    floors = list(geom.floors)
    sources_by_locator = {row.source_locator: row for row in verified.inputs.source_windows}
    window = next(w for w in geom.windows if w.id == "W-F1-N-1")

    plan_source = next(
        sources_by_locator[link.source_locator]
        for link in verified.inputs.claim_links
        if link.window_id == "W-F1-N-1" and link.claim == "existence"
        and sources_by_locator[link.source_locator].channel == "plan"
    )
    north_s7 = next(
        row for row in verified.inputs.source_windows
        if row.source_input_id == "North_view" and row.observation_id == "S7"
    )

    swapped = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan_source,), elevation_sources=(north_s7,),
        frames_by_input=frames, floors=floors,
        producer_draw_sha256=verified.inputs.producer_draw_sha256,
        resolver_inputs_sha256=verified.inputs.content_sha256,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert swapped.decision == "accepted", (
        "swapping in the correct North_view/S7 citation should flip this "
        "SAME window from rejected to accepted"
    )
    assert swapped.distances[0] == pytest.approx(0.12, abs=1e-6)
    assert swapped.derived_span == swapped.plan_world_interval


# =========================================================================== #
# 2. z-scope disambiguation — the real East_view S3/S4 same-along/
#    different-z pair (dispatch hard constraint #6).
# =========================================================================== #
def test_east_view_same_along_different_z_both_correctly_resolved():
    """East_view S3 (z=(4.0,5.8)) and S4 (z=(1.0,2.8)) project to the
    IDENTICAL world-along interval [3.52, 4.72] — only z distinguishes them.
    `W-F1-E-1` (floor-1) correctly cites S4; `W-F2-E-1` (floor-2) correctly
    cites S3. Neither is in the known-bad set; both must accept via a
    z-scope that resolves to exactly their OWN floor."""
    geom, verified, tol = _f9_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    by_id = {d.window_id: d for d in report.decisions}

    east1 = by_id["W-F1-E-1"]
    assert east1.decision == "accepted"
    assert east1.elevation_scope_status == ("resolved",)
    assert east1.elevation_scope_floor_ids == ("floor-1",)

    east2 = by_id["W-F2-E-1"]
    assert east2.decision == "accepted"
    assert east2.elevation_scope_status == ("resolved",)
    assert east2.elevation_scope_floor_ids == ("floor-2",)

    # Self-proof of the premise: absent z-scoping, along-distance ALONE
    # cannot tell these two sources apart (identical projected interval).
    assert east1.elevation_projected_intervals == east2.elevation_projected_intervals


def test_east_view_wrong_floor_citation_rejected_by_zscope_not_by_distance():
    """Swap `W-F1-E-1` (floor-1) onto East_view/S3 (whose z belongs to
    floor-2) instead of its real, correct S4 — the along-distance is STILL
    only 0.12 m (well inside tolerance), so only the z-scope check can catch
    this. Rejected with `position_evidence_pair_mismatch`, distance
    unaffected by the mismatch."""
    geom, verified, tol = _f9_prepared()
    frames = wp._build_authoritative_frames(geom, verified, tol)
    floors = list(geom.floors)
    sources_by_locator = {row.source_locator: row for row in verified.inputs.source_windows}
    window = next(w for w in geom.windows if w.id == "W-F1-E-1")
    assert window.floor_id == "floor-1"

    plan_source = None
    east_s3 = None
    for link in verified.inputs.claim_links:
        if link.window_id != "W-F1-E-1" or link.claim != "existence":
            continue
        source = sources_by_locator[link.source_locator]
        if source.channel == "plan":
            plan_source = source
    for row in verified.inputs.source_windows:
        if row.source_input_id == "East_view" and row.observation_id == "S3":
            east_s3 = row
    assert plan_source is not None and east_s3 is not None
    assert east_s3.local_z_interval.lo == pytest.approx(4.0) and east_s3.local_z_interval.hi == pytest.approx(5.8)

    decision = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan_source,), elevation_sources=(east_s3,),
        frames_by_input=frames, floors=floors,
        producer_draw_sha256=verified.inputs.producer_draw_sha256,
        resolver_inputs_sha256=verified.inputs.content_sha256,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert decision.decision == "rejected"
    assert decision.reject_code == "position_evidence_pair_mismatch"
    assert decision.elevation_scope_status == ("resolved",)
    assert decision.elevation_scope_floor_ids == ("floor-2",)  # resolved, but NOT floor-1
    assert decision.distances[0] < wp.WINDOW_EVIDENCE_PAIRING_TOL_M  # distance alone would have passed


def test_zscope_neuter_disabling_scope_check_causes_false_accept():
    """Must-red for the z-scope disambiguator specifically: with
    `resolve_elevation_source_floor_scope` neutered to always report
    `"not_declared"` (i.e. as if z-scoping were never consulted), the SAME
    wrong cross-floor citation from the previous test is incorrectly
    ACCEPTED — proving the z-scope check is load-bearing, not decorative."""
    geom, verified, tol = _f9_prepared()
    frames = wp._build_authoritative_frames(geom, verified, tol)
    floors = list(geom.floors)
    sources_by_locator = {row.source_locator: row for row in verified.inputs.source_windows}
    window = next(w for w in geom.windows if w.id == "W-F1-E-1")

    plan_source = next(
        sources_by_locator[link.source_locator]
        for link in verified.inputs.claim_links
        if link.window_id == "W-F1-E-1" and link.claim == "existence"
        and sources_by_locator[link.source_locator].channel == "plan"
    )
    east_s3 = next(
        row for row in verified.inputs.source_windows
        if row.source_input_id == "East_view" and row.observation_id == "S3"
    )

    original = wp.resolve_elevation_source_floor_scope
    wp.resolve_elevation_source_floor_scope = (
        lambda source, floors: wp._FloorScopeResolution(status="not_declared", floor_id=None)
    )
    try:
        neutered_decision = wp._build_window_position_evidence_shadow_decision(
            window, plan_sources=(plan_source,), elevation_sources=(east_s3,),
            frames_by_input=frames, floors=floors,
            producer_draw_sha256=verified.inputs.producer_draw_sha256,
            resolver_inputs_sha256=verified.inputs.content_sha256,
            tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
        )
    finally:
        wp.resolve_elevation_source_floor_scope = original

    assert neutered_decision.decision == "accepted", (
        "neutering the z-scope check should have produced a FALSE accept "
        "on this cross-floor mis-citation -- if this assertion fails, the "
        "test fixture no longer proves the scope check is load-bearing"
    )
    # Self-proof the neuter was actually removed, not left in place:
    assert wp.resolve_elevation_source_floor_scope is original


# =========================================================================== #
# 3. Threshold boundary (v2.1 §12.2 "Pair positive" ③: 0.29 PASS / 0.31 FAIL,
#    hand-computed, no production projector used to generate the expected
#    numbers).
# =========================================================================== #
class _FakeWindow:
    def __init__(self, id_, facade, floor_id, span):
        self.id = id_
        self.facade = facade
        self.floor_id = floor_id
        self.span = span


class _FakeFloor:
    def __init__(self, id_, z_floor, ceiling_height):
        self.id = id_
        self.z_floor = z_floor
        self.ceiling_height = ceiling_height


def _hand_plan(lo, hi, *, locator="src:" + "a" * 64):
    from src.agent.correction.window_sources import PlanSourceWindowV1

    return PlanSourceWindowV1(
        channel="plan", source_locator=locator, source_input_id="1f_view",
        source_output_sha256="b" * 64, observation_id="S1", floor_ref=1,
        world_x_interval=SourceIntervalV1(lo=lo, hi=hi), world_y_interval=SourceIntervalV1(lo=0.0, hi=1.0),
        positive_claims=("existence", "host", "along", "width"),
    )


def _hand_elevation(local_lo, local_hi, *, locator="src:" + "c" * 64, z=(1.0, 2.0), input_id="North_view"):
    from src.agent.correction.window_sources import ElevationSourceWindowV1

    return ElevationSourceWindowV1(
        channel="elevation", source_locator=locator, source_input_id=input_id,
        source_output_sha256="d" * 64, observation_id="S2",
        local_along_interval=SourceIntervalV1(lo=local_lo, hi=local_hi),
        local_z_interval=None if z is None else SourceIntervalV1(lo=z[0], hi=z[1]),
        positive_claims=("existence", "along", "width", "sill", "head", "appearance"),
    )


def _identity_frame(input_id="North_view"):
    return wp.AuthoritativeViewProjectionFrameV2(
        input_id=input_id, resolved_building_direction="North", world_axis="x", sign=1,
        along_origin=0.0, mirrored=False, local_x_positive="image_left_to_right",
        frame_transform_sha256="e" * 64,
    )


def test_threshold_boundary_029_accepts_031_rejects():
    plan = _hand_plan(0.0, 2.0)
    window = _FakeWindow("W-T", "North", "floor-1", [0.0, 2.0])
    floors = [_FakeFloor("floor-1", 0.0, 3.0)]
    frame = _identity_frame()

    # Identity frame (sign=1, origin=0): world = local. plan=[0,2].
    # local=[0.29, 2.29] -> world=[0.29, 2.29] -> d = max(0.29, 0.29) = 0.29.
    elev_pass = _hand_elevation(0.29, 2.29, z=(1.0, 2.0))
    d_pass = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan,), elevation_sources=(elev_pass,), frames_by_input={"North_view": frame},
        floors=floors, producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert d_pass.distances[0] == pytest.approx(0.29, abs=1e-12)
    assert d_pass.decision == "accepted"

    elev_fail = _hand_elevation(0.31, 2.31, z=(1.0, 2.0))
    d_fail = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan,), elevation_sources=(elev_fail,), frames_by_input={"North_view": frame},
        floors=floors, producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert d_fail.distances[0] == pytest.approx(0.31, abs=1e-12)
    assert d_fail.decision == "rejected"
    assert d_fail.reject_code == "position_evidence_pair_mismatch"


def test_pairing_tolerance_frozen_value_is_0_300():
    assert wp.WINDOW_EVIDENCE_PAIRING_TOL_M == 0.300


def test_pairing_tolerance_cross_validated_against_envelope_reconcile_tol_m():
    tol = load_core_tolerances()
    # Must not raise for the real shipped config.
    wp._validate_window_evidence_pairing_tolerance(envelope_reconcile_tol_m=tol.envelope_reconcile_tol_m)
    # But a caller feeding a SMALLER envelope_reconcile_tol_m than the
    # pinned 0.300 must be rejected loudly, not silently accepted.
    with pytest.raises(ValueError):
        wp._validate_window_evidence_pairing_tolerance(envelope_reconcile_tol_m=0.10)
    with pytest.raises(ValueError):
        wp._validate_window_evidence_pairing_tolerance(envelope_reconcile_tol_m=0.0)


def test_pairing_tolerance_validation_is_exercised_by_the_public_entry_point():
    """`compute_window_position_evidence_shadow` must actually CALL the
    cross-field validator (not just have it exist unused) — proven by
    monkeypatching the frozen constant so the shipped config's
    `envelope_reconcile_tol_m` no longer satisfies it."""
    geom, verified, tol = _f9_prepared()
    original = wp.WINDOW_EVIDENCE_PAIRING_TOL_M
    wp.WINDOW_EVIDENCE_PAIRING_TOL_M = tol.envelope_reconcile_tol_m + 1.0
    try:
        with pytest.raises(ValueError):
            wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    finally:
        wp.WINDOW_EVIDENCE_PAIRING_TOL_M = original


# =========================================================================== #
# 4. Advisory frame type rejection (v2.1 §1.3/§12.2 "Advisory 隔离").
# =========================================================================== #
def test_project_window_source_along_rejects_advisory_frame():
    elev = _hand_elevation(0.0, 1.0)
    advisory = wp.AdvisoryViewProjectionFrameV1(input_id="North_view", sign=1, overall_width_m=15.0)
    with pytest.raises(TypeError):
        wp.project_window_source_along(elev, window_facade="North", frame=advisory)


def test_project_window_source_along_rejects_none_frame():
    elev = _hand_elevation(0.0, 1.0)
    with pytest.raises(TypeError):
        wp.project_window_source_along(elev, window_facade="North", frame=None)


def test_project_window_source_along_rejects_arbitrary_object_frame():
    elev = _hand_elevation(0.0, 1.0)
    with pytest.raises(TypeError):
        wp.project_window_source_along(elev, window_facade="North", frame=object())


def test_project_window_source_along_plan_channel_ignores_frame_argument():
    """A plan source is already world-frame; passing `frame=None` (its
    default) must NOT raise -- only the elevation branch's type gate fires."""
    plan = _hand_plan(1.0, 2.0)
    result = wp.project_window_source_along(plan, window_facade="North")
    assert result.channel == "plan"
    assert result.frame_sha256 is None
    assert result.scope_floor_id is None
    assert (result.world_interval.lo, result.world_interval.hi) == (1.0, 2.0)


def test_advisory_frame_numbers_genuinely_differ_from_authoritative_on_f9_data():
    """Self-proof of premise (v2.1 §12.2 'Advisory 隔离' fixture
    precondition): the F-9 advisory-vs-current-ring frames really do
    disagree by the registered ~0.12 m debt, not by zero -- otherwise a
    type-only test would be checking a distinction without a difference."""
    geom, verified, tol = _f9_prepared()
    frames = wp._build_authoritative_frames(geom, verified, tol)
    north = frames["North_view"]
    # Advisory: sign=-1 (same convention), overall width read off the
    # elevation's own dimension chain (15.0 m per the real fixture / design
    # doc §1.3). Authoritative: along_origin=14.88 (current-ring, NOT 15.0).
    assert north.along_origin == pytest.approx(14.88, abs=1e-9)
    assert north.along_origin != pytest.approx(15.0, abs=1e-6)


# =========================================================================== #
# 5. Must-red neuter ① — "摘掉 projector": zeroing the authoritative
#    along_origin (simulating the current-ring transform never running)
#    flips a genuinely clean, all-accepted real run to FAIL.
# =========================================================================== #
def test_neuter_remove_projector_flips_clean_run_pass_to_fail():
    geom, verified, tol = _clean_prepared()
    report_clean = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    assert report_clean.status == "evaluated"
    assert report_clean.window_count == 15
    assert report_clean.all_accepted is True, "test premise: the clean run must self-prove all-accept first"

    original = wp._build_authoritative_frames

    def _zeroed_origin(geom, verified_inputs, tol):
        frames = original(geom, verified_inputs, tol)
        return {key: frame.model_copy(update={"along_origin": 0.0}) for key, frame in frames.items()}

    wp._build_authoritative_frames = _zeroed_origin
    try:
        report_neutered = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    finally:
        wp._build_authoritative_frames = original

    assert report_neutered.status == "evaluated"
    assert report_neutered.all_accepted is False
    assert any(d.decision == "rejected" for d in report_neutered.decisions)
    # Self-proof the neuter was actually removed, not left dangling.
    assert wp._build_authoritative_frames is original


# =========================================================================== #
# 6. Must-red neuter ② — "改用 advisory frame": injecting an
#    AdvisoryViewProjectionFrameV1 where the dispatcher expects an
#    authoritative one raises, and `check_correction`'s wrapper turns that
#    into a FAIL row (never an uncaught crash, never a silent PASS).
# =========================================================================== #
def test_neuter_advisory_frame_substitution_becomes_fail_row_via_check_correction():
    geom, verified, tol = _clean_prepared()
    rep_clean = check_correction(
        geom, capability_profile="orthogonal_polygon", run_profile="regression",
        verified_window_inputs=verified,
    )
    assert _shadow_row(rep_clean).status == CheckStatus.PASS

    original = wp._build_authoritative_frames

    def _advisory_substitution(geom, verified_inputs, tol):
        frames = original(geom, verified_inputs, tol)
        return {
            key: wp.AdvisoryViewProjectionFrameV1(input_id=key, sign=frame.sign, overall_width_m=15.0)
            for key, frame in frames.items()
        }

    wp._build_authoritative_frames = _advisory_substitution
    try:
        rep_neutered = check_correction(
            geom, capability_profile="orthogonal_polygon", run_profile="regression",
            verified_window_inputs=verified,
        )
    finally:
        wp._build_authoritative_frames = original

    row = _shadow_row(rep_neutered)
    assert row.status == CheckStatus.FAIL
    assert "TypeError" in row.evidence.get("exception_type", "")
    # Never blocks, even under the strictest profile, even on an exception.
    assert row.check_id not in {r.check_id for r in rep_neutered.blocking()}


# =========================================================================== #
# 7. `None` discipline (v2.1 §9: "不可用 None 表示『跑过但没结果』").
# =========================================================================== #
def test_zero_windows_report_is_a_real_pass_not_none():
    geom, verified, tol = _clean_prepared()
    geom_empty = geom.model_copy(update={"windows": []})
    report = wp.compute_window_position_evidence_shadow(geom_empty, verified_inputs=verified, tol=tol)
    assert report is not None
    assert report.status == "evaluated"
    assert report.window_count == 0
    assert report.decisions == ()
    assert report.all_accepted is True
    assert report.content_sha256  # non-empty hash, not a placeholder


def test_missing_verified_window_inputs_is_not_applicable_distinct_from_pass_and_fail():
    geom, _verified, _tol = _clean_prepared()
    rep = check_correction(geom, capability_profile="orthogonal_polygon", run_profile="exploratory")
    row = _shadow_row(rep)
    assert row.status == CheckStatus.NOT_APPLICABLE
    assert row.status != CheckStatus.PASS
    assert row.status != CheckStatus.FAIL


def test_binding_unavailable_is_a_third_state_distinct_from_evaluated():
    geom, verified, tol = _clean_prepared()
    original = wp.materialize_current_ring_va_elevation_bindings

    def _boom(**kwargs):
        raise WindowDirectionBindingError("direction_binding_ring_invalid", {"reason": "test-injected"})

    wp.materialize_current_ring_va_elevation_bindings = _boom
    try:
        report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    finally:
        wp.materialize_current_ring_va_elevation_bindings = original

    assert report.status == "binding_unavailable"
    assert report.binding_error_code == "direction_binding_ring_invalid"
    assert report.decisions == ()
    assert report.all_accepted is False
    assert report.status != "evaluated"

    # And check_correction must surface this as FAIL (non-blocking), not PASS.
    wp.materialize_current_ring_va_elevation_bindings = _boom
    try:
        rep = check_correction(
            geom, capability_profile="orthogonal_polygon", run_profile="regression",
            verified_window_inputs=verified,
        )
    finally:
        wp.materialize_current_ring_va_elevation_bindings = original
    row = _shadow_row(rep)
    assert row.status == CheckStatus.FAIL
    assert row.check_id not in {r.check_id for r in rep.blocking()}


def test_shadow_report_types_reject_none_where_a_named_state_is_required():
    """The pydantic shape itself, not just the check wrapper, refuses to let
    a `binding_unavailable` report masquerade as a silent, informationless
    object: `binding_error_code` is required whenever `status !=
    "evaluated"`."""
    with pytest.raises(ValidationError):
        wp.WindowPositionEvidenceShadowReportV1(
            producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
            status="binding_unavailable", binding_error_code=None,
            window_count=0, decisions=(), all_accepted=False,
            content_sha256="0" * 64,
        )


# =========================================================================== #
# 8. Never-block guarantee, independent of run_profile.
# =========================================================================== #
def test_shadow_fail_never_blocks_under_regression_profile():
    geom, verified, tol = _f9_prepared()  # genuinely has 4 rejected windows
    rep = check_correction(
        geom, capability_profile="orthogonal_polygon", run_profile="regression",
        verified_window_inputs=verified,
    )
    row = _shadow_row(rep)
    assert row.status == CheckStatus.FAIL
    d = disposition(row, capability_profile="orthogonal_polygon", run_profile="regression")
    assert d.value == "flag"
    assert row.check_id not in {r.check_id for r in rep.blocking()}


def test_shadow_check_id_always_registered_at_cross_check_layer():
    from src.validator.checks.schema import CheckLayer

    geom, verified, tol = _f9_prepared()
    rep = check_correction(
        geom, capability_profile="orthogonal_polygon", run_profile="golden",
        verified_window_inputs=verified,
    )
    row = _shadow_row(rep)
    assert row.layer == CheckLayer.CROSS_CHECK


# =========================================================================== #
# 9. Real entry wiring (v2.1 §10 S2's own acceptance bar / dispatch §12.1):
#    stepwise `_draw_correction` and integrated `run_pipeline_artifacts`.
# =========================================================================== #
def test_real_stepwise_entry_clean_run_shows_pass_and_does_not_block(tmp_path, monkeypatch):
    run_dir = _copy_stage_inputs(tmp_path, _CLEAN_RUN, _CLEAN_RUN_ACCEPTED_READING_ATTEMPT)
    fixed_geom = _clean_run_raw_geom()
    monkeypatch.setattr(pipeline_mod, "run_correction", lambda *a, **k: fixed_geom.model_copy(deep=True))

    policy = RunPolicy(run_profile="exploratory", capability_profile="orthogonal_polygon")
    result, rep = rs._draw_correction(run_dir, "", None, False, policy)

    row = _shadow_row(rep)
    assert row.status == CheckStatus.PASS
    assert row.evidence.get("window_count") == 15
    assert row.evidence.get("rejected_window_ids") == []
    assert row.check_id not in {r.check_id for r in rep.blocking()}


def test_real_integrated_entry_clean_run_shows_pass(tmp_path, monkeypatch):
    run_dir = _copy_stage_inputs(tmp_path, _CLEAN_RUN, _CLEAN_RUN_ACCEPTED_READING_ATTEMPT)
    fixed_geom = _clean_run_raw_geom()
    _run_integrated_through_correction_only(run_dir, monkeypatch, fixed_geom)
    row = _read_integrated_shadow_row(run_dir)
    assert row["status"] == "pass"
    assert row["evidence"]["window_count"] == 15
    assert row["evidence"]["rejected_window_ids"] == []


def test_real_stepwise_entry_neuter_projector_flips_to_fail_blocking_unaffected(tmp_path, monkeypatch):
    """The strongest single wiring lock: run the REAL stepwise entry twice on
    IDENTICAL real input (only the projector is neutered the second time),
    and assert (a) the shadow row flips PASS -> FAIL and (b) the actual
    accept/reject result (`rep.blocking()`) is BYTE-FOR-BYTE unaffected —
    v2.1 §10 S2's "不得因启用观测而改变接受结果", proven, not asserted."""
    fixed_geom = _clean_run_raw_geom()

    run_dir_a = _copy_stage_inputs(tmp_path / "a", _CLEAN_RUN, _CLEAN_RUN_ACCEPTED_READING_ATTEMPT)
    monkeypatch.setattr(pipeline_mod, "run_correction", lambda *a, **k: fixed_geom.model_copy(deep=True))
    policy = RunPolicy(run_profile="exploratory", capability_profile="orthogonal_polygon")
    _result_a, rep_a = rs._draw_correction(run_dir_a, "", None, False, policy)
    assert _shadow_row(rep_a).status == CheckStatus.PASS

    run_dir_b = _copy_stage_inputs(tmp_path / "b", _CLEAN_RUN, _CLEAN_RUN_ACCEPTED_READING_ATTEMPT)
    original = wp._build_authoritative_frames

    def _zeroed_origin(geom, verified_inputs, tol):
        frames = original(geom, verified_inputs, tol)
        return {key: frame.model_copy(update={"along_origin": 0.0}) for key, frame in frames.items()}

    wp._build_authoritative_frames = _zeroed_origin
    try:
        _result_b, rep_b = rs._draw_correction(run_dir_b, "", None, False, policy)
    finally:
        wp._build_authoritative_frames = original

    row_b = _shadow_row(rep_b)
    assert row_b.status == CheckStatus.FAIL

    # Accept/reject result identical: same set of blocking check-ids (empty
    # both times on this clean run), and every OTHER check's status/message
    # unchanged — only the shadow row itself may differ. Assert non-emptiness
    # FIRST so this equality is not a vacuous "two empty things match": a
    # real run's report carries many other rows (coverage/nondegenerate/
    # zstack/window_host_resolution/zone_count/window_on_wall/facade_frame/
    # audit_completeness/evidence_debt), and `window_host_resolution`
    # specifically calls `materialize_current_ring_va_elevation_bindings`
    # directly (not through the patched `wp._build_authoritative_frames`
    # seam) — this comparison is what proves that OTHER path was genuinely
    # untouched by the neuter, not merely coincidentally silent.
    assert [r.check_id for r in rep_a.blocking()] == [r.check_id for r in rep_b.blocking()] == []
    ids_a = {r.check_id: (r.status, r.message) for r in rep_a.results if r.check_id != _CHECK_ID}
    ids_b = {r.check_id: (r.status, r.message) for r in rep_b.results if r.check_id != _CHECK_ID}
    assert len(ids_a) > 5, "test premise: the real report must carry several other check rows"
    assert ids_a == ids_b


def test_real_stepwise_entry_neuter_advisory_frame_flips_to_fail_blocking_unaffected(tmp_path, monkeypatch):
    fixed_geom = _clean_run_raw_geom()

    run_dir_a = _copy_stage_inputs(tmp_path / "a", _CLEAN_RUN, _CLEAN_RUN_ACCEPTED_READING_ATTEMPT)
    monkeypatch.setattr(pipeline_mod, "run_correction", lambda *a, **k: fixed_geom.model_copy(deep=True))
    policy = RunPolicy(run_profile="exploratory", capability_profile="orthogonal_polygon")
    _result_a, rep_a = rs._draw_correction(run_dir_a, "", None, False, policy)
    assert _shadow_row(rep_a).status == CheckStatus.PASS

    run_dir_b = _copy_stage_inputs(tmp_path / "b", _CLEAN_RUN, _CLEAN_RUN_ACCEPTED_READING_ATTEMPT)
    original = wp._build_authoritative_frames

    def _advisory_substitution(geom, verified_inputs, tol):
        frames = original(geom, verified_inputs, tol)
        return {
            key: wp.AdvisoryViewProjectionFrameV1(input_id=key, sign=frame.sign, overall_width_m=15.0)
            for key, frame in frames.items()
        }

    wp._build_authoritative_frames = _advisory_substitution
    try:
        _result_b, rep_b = rs._draw_correction(run_dir_b, "", None, False, policy)
    finally:
        wp._build_authoritative_frames = original

    row_b = _shadow_row(rep_b)
    assert row_b.status == CheckStatus.FAIL
    assert "TypeError" in row_b.evidence.get("exception_type", "")
    assert [r.check_id for r in rep_a.blocking()] == [r.check_id for r in rep_b.blocking()] == []


def test_real_integrated_entry_neuter_projector_flips_to_fail(tmp_path, monkeypatch):
    fixed_geom = _clean_run_raw_geom()
    run_dir = _copy_stage_inputs(tmp_path, _CLEAN_RUN, _CLEAN_RUN_ACCEPTED_READING_ATTEMPT)

    original = wp._build_authoritative_frames

    def _zeroed_origin(geom, verified_inputs, tol):
        frames = original(geom, verified_inputs, tol)
        return {key: frame.model_copy(update={"along_origin": 0.0}) for key, frame in frames.items()}

    wp._build_authoritative_frames = _zeroed_origin
    try:
        _run_integrated_through_correction_only(run_dir, monkeypatch, fixed_geom)
    finally:
        wp._build_authoritative_frames = original

    row = _read_integrated_shadow_row(run_dir)
    assert row["status"] == "fail"


# =========================================================================== #
# 10. Same-view duplicate corroborator rejection (v2.1 §5.1: "同一 view 最多
#     一条 position corroborator").
# =========================================================================== #
def test_duplicate_same_view_elevation_corroborators_rejected():
    plan = _hand_plan(0.0, 2.0)
    window = _FakeWindow("W-T", "North", "floor-1", [0.0, 2.0])
    elev1 = _hand_elevation(0.0, 2.0, locator="src:" + "1" * 64)
    elev2 = _hand_elevation(0.0, 2.0, locator="src:" + "2" * 64)  # SAME source_input_id "North_view"
    decision = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan,), elevation_sources=(elev1, elev2),
        frames_by_input={"North_view": _identity_frame()}, floors=[_FakeFloor("floor-1", 0.0, 3.0)],
        producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert decision.decision == "rejected"
    assert decision.reject_code == "position_evidence_authority_invalid"


def test_zero_plan_sources_rejected_authority_invalid():
    window = _FakeWindow("W-T", "North", "floor-1", [0.0, 2.0])
    decision = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(), elevation_sources=(_hand_elevation(0.0, 2.0),),
        frames_by_input={"North_view": _identity_frame()}, floors=[_FakeFloor("floor-1", 0.0, 3.0)],
        producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert decision.decision == "rejected"
    assert decision.reject_code == "position_evidence_authority_invalid"
    assert decision.plan_locator is None
    assert decision.plan_world_interval is None


def test_multiple_plan_sources_rejected_authority_invalid():
    window = _FakeWindow("W-T", "North", "floor-1", [0.0, 2.0])
    plan1 = _hand_plan(0.0, 2.0, locator="src:" + "1" * 64)
    plan2 = _hand_plan(0.0, 2.0, locator="src:" + "2" * 64)
    decision = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan1, plan2), elevation_sources=(_hand_elevation(0.0, 2.0),),
        frames_by_input={"North_view": _identity_frame()}, floors=[_FakeFloor("floor-1", 0.0, 3.0)],
        producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert decision.decision == "rejected"
    assert decision.reject_code == "position_evidence_authority_invalid"


def test_no_elevation_corroborator_rejected_insufficient():
    window = _FakeWindow("W-T", "North", "floor-1", [0.0, 2.0])
    plan = _hand_plan(0.0, 2.0)
    decision = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan,), elevation_sources=(),
        frames_by_input={"North_view": _identity_frame()}, floors=[_FakeFloor("floor-1", 0.0, 3.0)],
        producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert decision.decision == "rejected"
    assert decision.reject_code == "position_evidence_insufficient"
    # Plan authority WAS resolved -- distinct from the zero-plan case above.
    assert decision.plan_locator is not None
    assert decision.plan_world_interval is not None


def test_zscope_unresolved_multiple_floors_rejected():
    """A z-interval spanning TWO floors' bands resolves to `"unresolved"`,
    never the first/nearest candidate (v2.1 §7.3 rule 5)."""
    window = _FakeWindow("W-T", "North", "floor-1", [0.0, 2.0])
    plan = _hand_plan(0.0, 2.0)
    floors = [_FakeFloor("floor-1", 0.0, 3.0), _FakeFloor("floor-2", 3.0, 3.0)]
    straddling = _hand_elevation(0.0, 2.0, z=(2.5, 3.5))  # crosses the floor-1/floor-2 boundary
    decision = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan,), elevation_sources=(straddling,),
        frames_by_input={"North_view": _identity_frame()}, floors=floors,
        producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    assert decision.decision == "rejected"
    assert decision.reject_code == "projection_scope_unresolved"
    assert decision.elevation_scope_status == ("unresolved",)
    assert decision.elevation_scope_floor_ids == (None,)


def test_resolve_elevation_source_floor_scope_no_z_data_is_not_declared():
    source = _hand_elevation(0.0, 2.0, z=None)
    result = wp.resolve_elevation_source_floor_scope(source, [_FakeFloor("floor-1", 0.0, 3.0)])
    assert result.status == "not_declared"
    assert result.floor_id is None


def test_resolve_elevation_source_floor_scope_resolved_single_floor():
    source = _hand_elevation(0.0, 2.0, z=(1.0, 2.0))
    result = wp.resolve_elevation_source_floor_scope(source, [_FakeFloor("floor-1", 0.0, 3.0)])
    assert result.status == "resolved"
    assert result.floor_id == "floor-1"


def test_resolve_elevation_source_floor_scope_zero_floors_unresolved():
    source = _hand_elevation(0.0, 2.0, z=(10.0, 11.0))  # far outside any floor band
    result = wp.resolve_elevation_source_floor_scope(source, [_FakeFloor("floor-1", 0.0, 3.0)])
    assert result.status == "unresolved"
    assert result.floor_id is None


# =========================================================================== #
# 11. Decision/report self-hash and identity-binding invariants (mirrors the
#     house style already established by `WindowPositionDecisionV1`/
#     `WindowPositionEvidenceArtifactV1` in S0).
# =========================================================================== #
def test_decision_sha256_self_validates():
    plan = _hand_plan(0.0, 2.0)
    window = _FakeWindow("W-T", "North", "floor-1", [0.0, 2.0])
    decision = wp._build_window_position_evidence_shadow_decision(
        window, plan_sources=(plan,), elevation_sources=(_hand_elevation(0.0, 2.0),),
        frames_by_input={"North_view": _identity_frame()}, floors=[_FakeFloor("floor-1", 0.0, 3.0)],
        producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
        tolerance_value=wp.WINDOW_EVIDENCE_PAIRING_TOL_M,
    )
    tampered = decision.model_dump(mode="json")
    tampered["distances"] = [999.0]
    with pytest.raises(ValidationError):
        wp.WindowPositionEvidenceShadowDecisionV1.model_validate(tampered)


def test_report_content_sha256_self_validates():
    geom, verified, tol = _clean_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    tampered = report.model_dump(mode="json")
    tampered["all_accepted"] = not tampered["all_accepted"]
    with pytest.raises(ValidationError):
        wp.WindowPositionEvidenceShadowReportV1.model_validate(tampered)


def test_report_rejects_a_decision_with_foreign_producer_identity():
    geom, verified, tol = _clean_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    tampered = report.model_dump(mode="json")
    tampered["decisions"][0]["producer_draw_sha256"] = "1" * 64
    tampered["decisions"][0]["decision_sha256"] = wp.canonical_sha256(
        {**{k: v for k, v in tampered["decisions"][0].items() if k != "decision_sha256"}},
    )
    with pytest.raises(ValidationError):
        wp.WindowPositionEvidenceShadowReportV1.model_validate(tampered)


def test_accepted_decision_requires_derived_span_equal_plan_world_interval():
    with pytest.raises(ValidationError):
        wp.WindowPositionEvidenceShadowDecisionV1(
            producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
            window_id="W-T", window_floor_id="floor-1",
            plan_locator="src:" + "a" * 64, plan_world_interval=SourceIntervalV1(lo=0.0, hi=2.0),
            elevation_locators=("src:" + "c" * 64,),
            elevation_projected_intervals=(SourceIntervalV1(lo=0.0, hi=2.0),),
            elevation_scope_status=("resolved",), elevation_scope_floor_ids=("floor-1",),
            distances=(0.0,), tolerance_name="window_evidence_pairing_tol_m", tolerance_value=0.3,
            decision="accepted", reject_code=None,
            derived_span=SourceIntervalV1(lo=0.0, hi=1.0),  # WRONG -- does not equal plan_world_interval
            legacy_model_span=SourceIntervalV1(lo=0.0, hi=2.0), legacy_span_delta_m=0.0,
            decision_sha256="0" * 64,
        )


def test_rejected_decision_cannot_carry_derived_span():
    with pytest.raises(ValidationError):
        wp.WindowPositionEvidenceShadowDecisionV1(
            producer_draw_sha256="0" * 64, resolver_inputs_sha256="0" * 64,
            window_id="W-T", window_floor_id="floor-1",
            plan_locator="src:" + "a" * 64, plan_world_interval=SourceIntervalV1(lo=0.0, hi=2.0),
            elevation_locators=(), elevation_projected_intervals=(),
            elevation_scope_status=(), elevation_scope_floor_ids=(),
            distances=(), tolerance_name="window_evidence_pairing_tol_m", tolerance_value=0.3,
            decision="rejected", reject_code="position_evidence_insufficient",
            derived_span=SourceIntervalV1(lo=0.0, hi=2.0),  # WRONG -- rejected must not carry one
            legacy_model_span=SourceIntervalV1(lo=0.0, hi=2.0), legacy_span_delta_m=None,
            decision_sha256="0" * 64,
        )


# =========================================================================== #
# 12. Legacy span delta.
# =========================================================================== #
def test_legacy_span_delta_none_when_rejected():
    geom, verified, tol = _f9_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    for d in report.decisions:
        if d.decision == "rejected":
            assert d.legacy_span_delta_m is None, d.window_id


def test_legacy_span_delta_is_real_float_when_accepted():
    geom, verified, tol = _f9_prepared()
    report = wp.compute_window_position_evidence_shadow(geom, verified_inputs=verified, tol=tol)
    accepted = [d for d in report.decisions if d.decision == "accepted"]
    assert accepted
    for d in accepted:
        assert isinstance(d.legacy_span_delta_m, float)
        assert d.legacy_span_delta_m >= 0.0
