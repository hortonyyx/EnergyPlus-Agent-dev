from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

import scripts.tool_scripts.run_stage as rs
from src.agent.correction.deterministic import DETERMINISTIC_CORE_STAMP_VERSION
from src.agent.execution import RunManifest
import src.agent.judge.correction_score as correction_score_module
from src.agent.judge.correction_score import score_correction_geometry
from src.agent.judge.gt import load_gt
from src.agent.judge.verdict import StageVerdict
from src.validator.checks.schema import CheckLayer, CheckReport

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_grade  # noqa: E402
from _grade_transform import plan_transform  # noqa: E402


_SM21 = Path("case_tests/e2e_tests/sm21_anchor")
_DEFAULT_TOLERANCES = {
    "wall_tol_m": 0.3,
    "window_centre_tol_m": 0.4,
    "elevation_along_tol_m": 0.4,
    "sill_tol_m": 0.3,
    "head_tol_m": 0.3,
    "width_tol_m": 0.4,
    "position_tol_m": 0.3,
    "extent_tol_m": 0.3,
    "complete_eps_m": 0.05,
    "overlap_accept": 0.75,
    "overlap_complete": 0.95,
    "floor_line_tol_m": 0.3,
}


def _pass_report(stage: str) -> CheckReport:
    rep = CheckReport(stage=stage)
    rep.add_pass("x", CheckLayer.INVARIANT)
    return rep


def _copy_run_subset(tmp_path: Path, run_name: str, files: list[tuple[str, str]]) -> Path:
    case_dir = tmp_path / "sm21_anchor"
    run_dir = case_dir / "run"
    (run_dir / "_run").mkdir(parents=True)
    shutil.copy2(_SM21 / run_name / "_run" / "run_manifest.json", run_dir / "_run" / "run_manifest.json")
    for src_rel, dst_rel in files:
        dst = run_dir / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_SM21 / run_name / src_rel, dst)
    return run_dir


def test_judge_packet_scores_accepted_reading_attempt_not_mutable_flat(tmp_path, monkeypatch):
    run_dir = _copy_run_subset(
        tmp_path,
        "run_2026-06-20_gpt54_reading",
        [
            ("0_reading/attempts/002/output.json", "0_reading/attempts/002/output.json"),
            ("0_reading/1f_view.json", "0_reading/1f_view.json"),
        ],
    )
    case_dir = tmp_path / "sm21_anchor"
    flat = run_dir / "0_reading" / "1f_view.json"
    flat.write_text(json.dumps({"image_kind": "plan", "strokes": []}), encoding="utf-8")
    monkeypatch.setattr(rs, "_render_stage", lambda *_args, **_kwargs: [])

    packet = rs._judge_packet(
        "0_reading",
        "sm21_anchor",
        case_dir,
        run_dir,
        run_dir / "0_reading" / "attempts" / "002",
        _pass_report("0_reading"),
    )

    sidecar_path = Path(packet["score_vs_gt"])
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    rec = RunManifest.load(run_dir).accepted("0_reading")
    assert sidecar["stage"] == "0_reading"
    assert sidecar["attempt"] == 2
    assert sidecar["source"] == "attempt_output"
    assert sidecar["scorer_schema"] == rs.LEGACY_SCORE_CACHE_SCHEMA
    assert sidecar["output_hash"] == rec.output_hash
    assert sidecar["tolerances"] == _DEFAULT_TOLERANCES
    assert "elevation" in sidecar
    assert "floor_lines" in sidecar["elevation"]
    first_score = next(iter(sidecar["scores"].values()))
    assert "vwall_records" in first_score and "hwall_records" in first_score
    assert {c["criterion"] for c in sidecar["score_criteria"]} >= {"elevation_windows_placed"}
    assert packet["grade"] == str(run_dir / "0_reading" / "attempts" / "002" / "grade.png")
    assert Path(packet["grade"]).exists()
    assert packet["score_criteria"] == sidecar["score_criteria"]
    assert {c["criterion"] for c in packet["score_criteria"]} >= {
        "walls_complete",
        "windows_placed",
        "boundary_complete",
        "no_oversplit",
    }
    assert all("suggested_status" in c for c in packet["score_criteria"])
    with pytest.raises(Exception):
        StageVerdict.model_validate(
            {
                "stage": "0_reading",
                "rubric_id": "J0",
                "criteria": [],
                "elevation_windows_placed": "pass",
            }
        )

    # Reuse is hash-bound: corrupt the sidecar hash and ensure packet regenerates it
    # from accepted attempts/002/output.json, not from the already-tampered flat file.
    sidecar["output_hash"] = "wrong"
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    packet2 = rs._judge_packet(
        "0_reading",
        "sm21_anchor",
        case_dir,
        run_dir,
        run_dir / "0_reading" / "attempts" / "002",
        _pass_report("0_reading"),
    )
    sidecar2 = json.loads(Path(packet2["score_vs_gt"]).read_text(encoding="utf-8"))
    assert sidecar2["output_hash"] == rec.output_hash
    assert sidecar2["scores"]

    sidecar2["tolerances"] = {**_DEFAULT_TOLERANCES, "wall_tol_m": 9.9}
    sidecar_path.write_text(json.dumps(sidecar2), encoding="utf-8")
    packet3 = rs._judge_packet(
        "0_reading",
        "sm21_anchor",
        case_dir,
        run_dir,
        run_dir / "0_reading" / "attempts" / "002",
        _pass_report("0_reading"),
    )
    sidecar3 = json.loads(Path(packet3["score_vs_gt"]).read_text(encoding="utf-8"))
    assert sidecar3["tolerances"] == _DEFAULT_TOLERANCES


def _v3_floor(name: str, *, footprint_xy, cells, z_floor: float = 0.0, ceiling_height: float = 3.0) -> dict:
    """Minimal valid schema-v3 (`orthogonal_polygon`) floor payload: a
    rectangular footprint ring (the mandatory `floor.footprint.vertices`
    schema v3 requires and legacy v1/v2 does not have) + one or more
    axis-aligned rectangular cells, each also given an explicit orthogonal
    `polygon` alongside the legacy `x`/`y` bbox pair (schema v3's `CellV3`
    requires both). Used by the F-22 BLOCKER-1 locks that specifically
    exercise the trusted (schema-v3) output-convention path — schema v3 is
    ONE of the (now two, F-22 BLOCKER-1 2026-08-12) facts
    `_is_trusted_output_convention` requires; see `_v3_output` below for the
    other (the deterministic core's own unconditional stamp)."""
    (fx0, fx1), (fy0, fy1) = footprint_xy
    return {
        "id": name.replace(" ", "_"),
        "name": name,
        "z_floor": z_floor,
        "ceiling_height": ceiling_height,
        "footprint": {"vertices": [[fx0, fy0], [fx1, fy0], [fx1, fy1], [fx0, fy1]]},
        "cells": [
            {
                "id": c["id"],
                "role": c.get("role", "office"),
                "x": list(c["x"]),
                "y": list(c["y"]),
                "polygon": [
                    [c["x"][0], c["y"][0]],
                    [c["x"][1], c["y"][0]],
                    [c["x"][1], c["y"][1]],
                    [c["x"][0], c["y"][1]],
                ],
            }
            for c in cells
        ],
    }


def _v3_output(floors: list[dict], *, footprint_x, footprint_y, windows: list | None = None) -> dict:
    """Minimal trusted schema-v3 output payload.

    F-22 BLOCKER-1 (2026-08-12): `_is_trusted_output_convention` now ALSO
    requires an unconditional `deterministic_core_stamp` (schema v3 alone is
    no longer sufficient — see that function's docstring for why: schema
    version cannot distinguish a pre- vs. post-transform-fix product). Every
    caller of this helper is testing boundary/wall-extent scoring behaviour
    on an ASSUMED-trusted v3 product, not testing trust detection itself
    (that is `tests/test_f22_blocker1_core_stamp.py`'s job) — so the stamp is
    injected here, unconditionally, exactly like `schema_version` a few lines
    below, rather than requiring every call site to repeat it.
    """
    return {
        "schema_version": "3",
        "footprint_x": list(footprint_x),
        "footprint_y": list(footprint_y),
        "floors": floors,
        "windows": windows or [],
        "deterministic_core_stamp": {"version": DETERMINISTIC_CORE_STAMP_VERSION},
    }


def _core_proof_for(output: dict):
    """F-22 BLOCKER-1 round 2 (2026-08-13): the companion to `_v3_output`'s
    stamp injection. `_is_trusted_output_convention` now ALSO requires an
    externally issued `DeterministicCoreProofV1`, independently re-verified
    against the geometry under test -- every caller of this helper is
    testing boundary/wall-extent scoring on an ASSUMED-trusted v3 product
    (not testing trust detection itself, which is
    tests/test_f22_blocker1_core_stamp.py's job), so build a proof that
    genuinely matches THIS payload's own `core_owned_projection_v1` here,
    rather than requiring every call site to repeat that."""
    from src.agent.correction.deterministic import DeterministicCoreProofV1, core_owned_projection_v1
    from src.agent.correction.parse import ensure_corrected_geometry
    from src.agent.execution.manifest import hash_obj

    geom = ensure_corrected_geometry(output)
    return DeterministicCoreProofV1(
        core_version=DETERMINISTIC_CORE_STAMP_VERSION,
        input_hash="0" * 64,
        core_projection_hash=hash_obj(core_owned_projection_v1(geom)),
    )


def test_correction_scorer_maps_f1_f2_to_gt_floors():
    """F-22 BLOCKER-1 rewrite (2026-08-11): this fixture is a REAL historical
    accepted attempt with no `schema_version` declared, i.e. legacy schema
    v1 (`ensure_corrected_geometry` defaults undeclared to "1") — exactly the
    CLI's DEFAULT `capability_profile: rectangular`. Its output-convention
    identity is therefore untrusted per `_is_trusted_output_convention`, so
    boundary/interior-wall-extent scoring is explicitly refused (not
    guessed): wall_hits/boundary_hits go to 0 of their totals and `evidence`
    carries a visible `unsupported_output_convention` entry, rather than the
    previous (F-22 BLOCKER-1 bug) behaviour of silently scoring it as if it
    were outer-skin. Window matching is untouched by this gate (window spans
    were never wall-thickness-expanded either before or after F-22) so
    window_hits stays exactly as before.
    """
    gt = load_gt("sm21_anchor")
    output = json.loads(
        (_SM21 / "run_2026-06-20_sonnet_reading/1_correction/attempts/001/output.json")
        .read_text(encoding="utf-8")
    )
    assert output.get("schema_version") is None  # sanity: this IS the untrusted-legacy fixture

    result = score_correction_geometry(output, gt)

    assert result.floor_map == {"F1": "Floor 1", "F2": "Floor 2"}
    assert result.output_convention == {
        "schema_version": "1", "declared": False, "trusted": False, "identity": None,
    }
    assert [e["type"] for e in result.evidence] == ["unsupported_output_convention"]
    assert set(result.scores) == {"F1", "F2"}
    assert result.scores["F1"].wall_hits() == (0, 4)
    assert result.scores["F2"].wall_hits() == (0, 5)
    assert result.scores["F1"].window_hits() == (3, 3)
    assert result.scores["F2"].window_hits() == (4, 4)
    assert result.scores["F1"].boundary_hits() == (0, 0)
    assert result.scores["F2"].boundary_hits() == (0, 0)
    assert result.scores["F1"].boundary is None
    assert result.scores["F2"].boundary is None


def test_correction_boundary_uses_footprint_and_records_miss_delta():
    """F-22 BLOCKER-1 rewrite (2026-08-11): this test is specifically about
    boundary delta/miss reporting, which is now gated on a trusted (schema-v3)
    identity — migrated from an implicit-v1 dict to the minimal v3 shape."""
    gt = {
        "footprint": {"W_m": 15.0, "D_m": 8.0},
        "floors": [
            {"name": "Floor 1", "zones": [{"rect_m": [0, 0, 15, 8]}]},
        ],
        "windows": [],
    }
    output = _v3_output(
        [_v3_floor("Floor 1", footprint_xy=((0.12, 14.72), (0.0, 8.4)),
                   cells=[{"id": "A", "x": [0.12, 14.72], "y": [0.0, 8.4]}])],
        footprint_x=[0.12, 14.72], footprint_y=[0.0, 8.4],
    )

    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    boundary = result.scores["Floor 1"].boundary

    assert boundary is not None
    assert boundary["W"].delta == 0.12
    assert boundary["E"].delta == -0.28
    assert boundary["N"].read is None
    assert result.scores["Floor 1"].boundary_hits() == (3, 4)


def test_correction_boundary_matches_directly_for_trusted_schema_v3_with_wall_thickness_declared():
    """F-22 rewrite (2026-08-11; renamed per sol NIT-1 — was
    ``test_correction_boundary_expands_centerline_to_gt_outer_skin_when_wall_thickness_declared``,
    a name that described an action ["expands"] this scorer no longer takes;
    kept as a rename not a deletion, same scenario covered).

    Pre-F-17, a 1_correction product's exterior envelope was expressed at
    the wall CENTRELINE, so this scorer used to expand it outward by half
    `wall_thickness_m` before comparing to gt's outer-skin truth (that old
    ``_boundary_centerline_to_outer`` helper). F-17 (2026-08-09) fixed the
    deterministic core so a schema-v3 product's own footprint is now already
    expressed at the outer face — applying that expansion on top
    double-counted the offset (F-22 BLOCKER-1 bug, ``delta`` systematically
    ±half-thickness on every real schema-v3 run past F-17).

    BLOCKER-1 (sol 2026-08-11): direct comparison is only trusted for a
    verified schema-v3/orthogonal_polygon identity — this fixture is
    migrated to that minimal v3 shape (was an implicit-v1 dict) precisely
    because it is testing that trusted path. The surviving lock is that
    declaring ``wall_thickness_m`` on gt must NOT perturb the score for a
    trusted product (not merely become a no-op that happens to cancel out).
    """
    gt = {
        "footprint": {"W_m": 15.0, "D_m": 8.0},
        "wall_thickness_m": 0.24,
        "floors": [
            {"name": "Floor 1", "zones": [{"rect_m": [0, 0, 15, 8]}]},
        ],
        "windows": [],
    }
    output = _v3_output(
        [_v3_floor("Floor 1", footprint_xy=((0.0, 15.0), (0.0, 8.0)),
                   cells=[{"id": "A", "x": [0.0, 15.0], "y": [0.0, 8.0]}])],
        footprint_x=[0.0, 15.0], footprint_y=[0.0, 8.0],
    )

    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    assert result.output_convention["trusted"] is True
    boundary = result.scores["Floor 1"].boundary

    assert boundary is not None
    assert {side: match.delta for side, match in boundary.items()} == {
        "S": 0.0,
        "N": 0.0,
        "W": 0.0,
        "E": 0.0,
    }
    assert {side: match.status for side, match in boundary.items()} == {
        "S": "complete",
        "N": "complete",
        "W": "complete",
        "E": "complete",
    }
    assert result.scores["Floor 1"].boundary_hits() == (4, 4)


def test_correction_edge_wall_spans_match_directly_for_trusted_schema_v3_with_wall_thickness_declared():
    """F-22 rewrite (2026-08-11; renamed per sol NIT-1 — was
    ``test_correction_edge_wall_spans_expand_to_gt_outer_skin_when_wall_thickness_declared``).

    Companion to the boundary test above but for interior wall extents
    (the old ``_expand_boundary_span`` helper, also deleted in F-22). For a
    trusted schema-v3 product, interior wall extents are read verbatim from
    its cell polygons: post-F-17 they already run edge-to-edge of the outer
    footprint, matching gt's own interior-wall truth extents (which also
    touch the outer footprint — see ``derive_gt_wall_segments`` in
    reading_score.py) with no expansion needed. BLOCKER-1: interior-wall
    extraction is ALSO gated on trusted identity now (not just boundary),
    so this fixture is migrated to the minimal v3 shape.
    """
    gt = {
        "footprint": {"W_m": 10.0, "D_m": 5.0},
        "wall_thickness_m": 0.24,
        "floors": [
            {
                "name": "Floor 1",
                "zones": [
                    {"rect_m": [0.0, 0.0, 5.0, 5.0]},
                    {"rect_m": [5.0, 0.0, 10.0, 5.0]},
                ],
            },
        ],
        "windows": [],
    }
    output = _v3_output(
        [_v3_floor("Floor 1", footprint_xy=((0.0, 10.0), (0.0, 5.0)), cells=[
            {"id": "A", "x": [0.0, 5.0], "y": [0.0, 5.0]},
            {"id": "B", "x": [5.0, 10.0], "y": [0.0, 5.0]},
        ])],
        footprint_x=[0.0, 10.0], footprint_y=[0.0, 5.0],
    )

    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    assert result.output_convention["trusted"] is True
    match = result.scores["Floor 1"].vwalls[0]

    assert match.status == "complete"
    assert match.read is not None
    assert match.read.coord == 5.0
    assert match.read.start == 0.0
    assert match.read.end == 5.0


def test_correction_boundary_double_expansion_regression_self_proving():
    """F-22 regression lock, self-proving its own premise.

    Pattern per project discipline (see
    ``tests/test_f18_window_host_float_tolerance.py::_round_trip_differs``):
    first assert the deleted transform really WOULD have produced a wrong
    answer on this exact fixture (the premise), THEN assert the fix is
    correct — so a silently-neutered fixture cannot pass as an empty lock.
    """
    truth = {"S": 0.0, "N": 8.0, "W": 0.0, "E": 15.0}
    wall_thickness_m = 0.24
    half = wall_thickness_m / 2.0
    # This is exactly the deleted `_boundary_centerline_to_outer` formula
    # (correction_score.py, removed in F-22), re-derived here ONLY to prove
    # the premise below — production code no longer contains it.
    what_old_code_would_have_produced = {
        "S": truth["S"] - half,
        "N": truth["N"] + half,
        "W": truth["W"] - half,
        "E": truth["E"] + half,
    }
    # PREMISE: on a product already expressed at the outer skin (post-F-17,
    # matching gt's own outer-skin truth), the old transform is NOT a no-op —
    # it introduces a spurious half-wall-thickness offset on every side.
    assert what_old_code_would_have_produced != truth
    assert all(
        abs(what_old_code_would_have_produced[side] - truth[side]) == pytest.approx(half)
        for side in truth
    )

    gt = {
        "footprint": {"W_m": 15.0, "D_m": 8.0},
        "wall_thickness_m": wall_thickness_m,
        "floors": [{"name": "Floor 1", "zones": [{"rect_m": [0, 0, 15, 8]}]}],
        "windows": [],
    }
    # BLOCKER-1: this is testing the trusted-identity path, so use the
    # minimal v3 shape (was an implicit-v1 dict) — an untrusted product
    # returns boundary=None unconditionally and would never reach the
    # premise this test proves.
    output = _v3_output(
        [_v3_floor("Floor 1", footprint_xy=((0.0, 15.0), (0.0, 8.0)),
                   cells=[{"id": "A", "x": [0.0, 15.0], "y": [0.0, 8.0]}])],
        footprint_x=[0.0, 15.0], footprint_y=[0.0, 8.0],
    )

    # FIX: the real public entry point no longer applies that transform.
    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    assert result.output_convention["trusted"] is True  # sanity: premise applies to a trusted product
    boundary = result.scores["Floor 1"].boundary
    assert boundary is not None
    for side in ("S", "N", "W", "E"):
        assert boundary[side].read == pytest.approx(truth[side])
        assert boundary[side].delta == pytest.approx(0.0)
        assert boundary[side].status == "complete"


def _boundary_south_fixture(south_offset: float) -> tuple[dict, dict]:
    """Trusted schema-v3 footprint at [south_offset, 8.0] x [0, 15] — the S
    side of the boundary is thus off from gt truth (S=0.0) by exactly
    `south_offset`. (BLOCKER-1: uses the minimal v3 shape so
    `_is_trusted_output_convention` recognizes it and the boundary tiers
    below are actually exercised, not short-circuited to None.)"""
    gt = {
        "footprint": {"W_m": 15.0, "D_m": 8.0},
        "wall_thickness_m": 0.24,
        "floors": [{"name": "Floor 1", "zones": [{"rect_m": [0, 0, 15, 8]}]}],
        "windows": [],
    }
    output = _v3_output(
        [_v3_floor("Floor 1", footprint_xy=((0.0, 15.0), (south_offset, 8.0)),
                   cells=[{"id": "A", "x": [0.0, 15.0], "y": [south_offset, 8.0]}])],
        footprint_x=[0.0, 15.0], footprint_y=[south_offset, 8.0],
    )
    return gt, output


def test_correction_boundary_status_three_tier_green_exact():
    """F-22 orange-tier lock, tier 1 of 3: 0.0 offset -> complete (green)."""
    gt, output = _boundary_south_fixture(0.0)
    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    match = result.scores["Floor 1"].boundary["S"]
    assert match.status == "complete"
    assert match.delta == pytest.approx(0.0)


def test_correction_boundary_status_three_tier_orange_within_tol():
    """F-22 orange-tier lock, tier 2 of 3: 0.12 offset (> complete_eps 0.05,
    <= position_tol 0.30) -> within_tol (orange). This is the exact drift
    magnitude the F-22 bug produced (real ±0.12 sidecar deltas) and, before
    this batch, went completely uncoloured (LineMatch had no status field)."""
    gt, output = _boundary_south_fixture(0.12)
    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    match = result.scores["Floor 1"].boundary["S"]
    assert match.status == "within_tol"
    assert match.delta == pytest.approx(0.12)
    assert match.read is not None


def test_correction_boundary_status_threshold_uses_raw_delta_not_rounded():
    """F-22 MINOR-1 (sol cross-review 2026-08-11): the complete/within_tol
    threshold must compare the RAW (unrounded) offset against `complete_eps`
    (0.05), not the value already rounded to 2dp for display — rounding
    first silently widens the green tier (0.054 rounds to 0.05 and would
    wrongly read "complete"). Exercises the exact boundary values sol used:
    0.05 (complete) / 0.054 (within_tol, NOT complete despite rounding to
    0.05) / 0.055 (within_tol) via the real `score_correction_geometry`
    entry point (not the private `_match_lines` helper directly)."""
    gt, output = _boundary_south_fixture(0.05)
    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    match = result.scores["Floor 1"].boundary["S"]
    assert match.status == "complete"
    assert match.delta == pytest.approx(0.05)

    gt, output = _boundary_south_fixture(0.054)
    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    match = result.scores["Floor 1"].boundary["S"]
    assert match.status == "within_tol"  # raw 0.054 > 0.05, even though it rounds to 0.05
    assert match.delta == pytest.approx(0.05)  # displayed delta IS rounded

    gt, output = _boundary_south_fixture(0.055)
    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    match = result.scores["Floor 1"].boundary["S"]
    assert match.status == "within_tol"
    assert match.delta == pytest.approx(0.06)


def test_boundary_match_dict_propagates_within_tol_status_for_elevation_consumer():
    """F-22: `_boundary_match_dict` (run_stage.py) used to hardcode
    ``"complete" if match.read is not None else "miss"`` — a real
    ``within_tol`` LineMatch (from the real entry point) was silently
    collapsed to "complete", which is why `_draw_elevation_boundary`'s
    already-present orange branch (`render_grade.py`) was dead code: its
    producer never emitted "within_tol". This locks the producer side."""
    gt, output = _boundary_south_fixture(0.12)
    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    match = result.scores["Floor 1"].boundary["S"]
    assert match.status == "within_tol"  # sanity: this IS the drift tier

    out = rs._boundary_match_dict(match, "S")
    assert out["status"] == "within_tol"
    assert out["status"] != "complete"


def test_correction_boundary_status_three_tier_red_miss():
    """F-22 orange-tier lock, tier 3 of 3: 0.5 offset (> position_tol 0.30)
    -> miss (red), unmatched."""
    gt, output = _boundary_south_fixture(0.5)
    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    match = result.scores["Floor 1"].boundary["S"]
    assert match.status == "miss"
    assert match.read is None
    assert match.delta is None


def test_output_convention_declaration_mutation_changes_scoring_behavior():
    """F-22 BLOCKER-1 self-test (sol cross-review 2026-08-11): sol's
    reproduction of the "runtime inert" defect was literally "change
    `CORRECTION_OUTPUT_CONVENTION` to a bogus string and rerun scoring on a
    real, otherwise-trusted schema-v3 product; if the result doesn't change,
    the declaration is a comment wearing a variable name, not a guard."
    This locks that exact self-test as a permanent regression check, on a
    real production artifact (not a synthetic fixture) so it can't be
    satisfied by a fixture that happens not to exercise the read site.

    F-22 BLOCKER-1 2026-08-12 unconditional-core-stamp follow-up: this exact
    run (`run_2026-08-11_continuous_e2e`) is the second row of sol's
    reproduction table — a real, post-F-17-fix, `capability_profile:
    orthogonal_polygon` production artifact that STILL lacks
    `deterministic_core_stamp` (it predates the stamp's existence). Per the
    user-ratified fix, this on-disk artifact is now UNTRUSTED as-is and needs
    a rerun to regain a score — that is locked directly below, first, as this
    test's own self-proving premise (project discipline: a regression test
    must prove the condition it depends on actually holds on this exact
    fixture, not assume it). The REST of this test (the
    `CORRECTION_OUTPUT_CONVENTION` mutation self-test) is about a DIFFERENT
    guard than the stamp — it wants an otherwise-trusted real v3 product, so
    a stamp is injected into the loaded dict, standing in for "if this run
    had been produced by today's code" (the same substitution
    `tests/test_f22_blocker1_core_stamp.py` uses to build a real
    core-verified product without needing to re-run the full pipeline).
    """
    gt = load_gt("sm21_anchor")
    output = json.loads(
        (_SM21 / "run_2026-08-11_continuous_e2e/1_correction/attempts/001/output.json")
        .read_text(encoding="utf-8")
    )
    assert output.get("schema_version") == "3"  # sanity: this IS the trusted-identity fixture

    # PREMISE (F-22 BLOCKER-1 2026-08-12): as committed to disk today, this
    # real post-F-17-fix production artifact has NO core stamp and is
    # therefore untrusted — proving the fix actually changed this run's
    # verdict (sol's exact BLOCKER-1 reproduction), not merely a synthetic
    # fixture that never had the old bug.
    assert "deterministic_core_stamp" not in output
    as_scored_on_disk = score_correction_geometry(output, gt)
    assert as_scored_on_disk.output_convention["trusted"] is False
    assert as_scored_on_disk.scores["Floor 1"].boundary is None

    output = dict(output)
    output["deterministic_core_stamp"] = {"version": DETERMINISTIC_CORE_STAMP_VERSION}
    # Round 2 (2026-08-13): a genuinely matching `core_proof` for THIS real
    # production geometry -- otherwise `trusted` could never reach True at
    # all post-round-2, and this self-test would be unable to prove its own
    # "otherwise-trusted" premise before mutating the declaration.
    proof = _core_proof_for(output)
    before = score_correction_geometry(output, gt, core_proof=proof)
    assert before.output_convention["trusted"] is True
    assert before.scores["Floor 1"].boundary is not None
    assert all(m.status == "complete" for m in before.scores["Floor 1"].boundary.values())

    original = correction_score_module.CORRECTION_OUTPUT_CONVENTION
    correction_score_module.CORRECTION_OUTPUT_CONVENTION = "bogus"
    try:
        after = score_correction_geometry(output, gt, core_proof=proof)
    finally:
        correction_score_module.CORRECTION_OUTPUT_CONVENTION = original

    # THE ASSERTION: mutating the declaration changed scoring behaviour for
    # this real, valid, otherwise-trusted schema-v3 product.
    assert after.output_convention["trusted"] is False
    assert after.scores["Floor 1"].boundary is None
    assert any(e["type"] == "unsupported_output_convention" for e in after.evidence)


def test_correction_boundary_falls_back_to_cells_bbox_when_footprint_missing():
    """F-22 BLOCKER-1 rewrite (2026-08-11).

    Original intent: no `footprint_x`/`footprint_y` declared, only cells ->
    `_extract_correction_boundary` falls back to `_floor_cells_bbox`. That
    fallback is legacy-schema machinery (schema v3's `floor.footprint` is a
    mandatory field, so "missing footprint" cannot even be constructed in a
    trusted v3 payload) and the fixture below is implicit schema v1 (no
    `schema_version` key) — i.e. untrusted per `_is_trusted_output_convention`
    regardless of whether the fallback would have derived the right bbox.
    This now locks the REFUSAL: an untrusted, footprint-less product still
    returns a safe no-data boundary (not a crash, not a guess), consistent
    with every other untrusted-identity case in this file.
    """
    gt = {
        "footprint": {"W_m": 15.0, "D_m": 8.0},
        "floors": [
            {"name": "Floor 1", "zones": [{"rect_m": [0, 0, 15, 8]}]},
        ],
        "windows": [],
    }
    output = {
        "floors": [
            {
                "name": "Floor 1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "cells": [
                    {"id": "A", "role": "office", "x": [0.0, 7.5], "y": [0.0, 8.0]},
                    {"id": "B", "role": "office", "x": [7.5, 15.0], "y": [0.0, 8.0]},
                ],
            }
        ],
        "windows": [],
    }
    assert output.get("schema_version") is None  # sanity: untrusted-legacy fixture

    result = score_correction_geometry(output, gt)

    assert result.output_convention["trusted"] is False
    assert result.scores["Floor 1"].boundary is None
    assert result.scores["Floor 1"].boundary_hits() == (0, 0)


def test_correction_half_length_wall_scores_missing_piece():
    """F-22 BLOCKER-1 rewrite (2026-08-11): interior-wall extent/piece
    scoring is now gated on trusted (schema-v3) identity too, so this
    fixture is migrated from an implicit-v1 dict to the minimal v3 shape."""
    gt = {
        "footprint": {"W_m": 10.0, "D_m": 4.0},
        "floors": [
            {
                "name": "Floor 1",
                "zones": [
                    {"rect_m": [0, 0, 5, 4]},
                    {"rect_m": [5, 0, 10, 4]},
                ],
            },
        ],
        "windows": [],
    }
    output = _v3_output(
        [_v3_floor("Floor 1", footprint_xy=((0, 10), (0, 4)),
                   cells=[{"id": "A", "x": [0, 5], "y": [0, 2]}])],
        footprint_x=[0, 10], footprint_y=[0, 4],
    )

    result = score_correction_geometry(output, gt, core_proof=_core_proof_for(output))
    assert result.output_convention["trusted"] is True
    match = result.scores["Floor 1"].vwalls[0]

    assert match.status == "miss"
    assert match.read is not None and (match.read.coord, match.read.start, match.read.end) == (5.0, 0.0, 2.0)
    assert match.truth is not None and (match.truth.coord, match.truth.start, match.truth.end) == (5.0, 0.0, 4.0)
    assert [p.kind for p in match.pieces] == ["matched", "missing"]
    assert match.pieces[-1].span == (2.0, 4.0)


def test_old_score_sidecar_schema_triggers_recompute_with_boundary(tmp_path):
    from src.agent.execution.manifest import hash_text

    gt = {
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
    attempt_dir = tmp_path / "001"
    attempt_dir.mkdir()
    output = {
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
    output_text = json.dumps(output)
    (attempt_dir / "output.json").write_text(output_text, encoding="utf-8")
    old_sidecar = {
        "stage": "0_reading",
        "attempt": 1,
        "output_hash": hash_text(output_text),
        "source": "attempt_output",
        "case": "tiny",
        "tolerances": {"wall_tol_m": 0.3, "window_centre_tol_m": 0.4},
        "scores": {},
        "floor_map": {},
        "evidence": [],
        "score_criteria": [],
    }
    (attempt_dir / "score_vs_gt.json").write_text(json.dumps(old_sidecar), encoding="utf-8")

    artifacts = rs._grade_attempt_artifacts("0_reading", "tiny", attempt_dir, gt, grade=rs.GradeConfig())
    sidecar = json.loads((attempt_dir / "score_vs_gt.json").read_text(encoding="utf-8"))

    assert artifacts["score_vs_gt"] == str(attempt_dir / "score_vs_gt.json")
    assert sidecar["scorer_schema"] == rs.LEGACY_SCORE_CACHE_SCHEMA
    assert sidecar["scores"]["1f_view"]["boundary"]["N"]["read"] == 4.0


def test_judge_packet_scores_correction_attempt_and_records_floor_map(tmp_path, monkeypatch):
    run_dir = _copy_run_subset(
        tmp_path,
        "run_2026-06-20_sonnet_reading",
        [("1_correction/attempts/001/output.json", "1_correction/attempts/001/output.json")],
    )
    monkeypatch.setattr(rs, "_render_stage", lambda *_args, **_kwargs: [])

    packet = rs._judge_packet(
        "1_correction",
        "sm21_anchor",
        tmp_path / "sm21_anchor",
        run_dir,
        run_dir / "1_correction" / "attempts" / "001",
        _pass_report("1_correction"),
    )

    sidecar = json.loads(Path(packet["score_vs_gt"]).read_text(encoding="utf-8"))
    assert sidecar["stage"] == "1_correction"
    assert sidecar["source"] == "attempt_output"
    assert sidecar["scorer_schema"] == rs.LEGACY_SCORE_CACHE_SCHEMA
    assert sidecar["tolerances"] == _DEFAULT_TOLERANCES
    assert sidecar["elevation"]["summary"]["complete_total"] == 14
    assert sidecar["elevation"]["summary"]["miss_total"] == 1
    assert sidecar["elevation"]["summary"]["extra_total"] == 1
    assert "floor_lines" in sidecar["elevation"]
    assert sidecar["elevation"]["floor_lines"]["North"]["matches"]
    assert sidecar["elevation"]["boundary"]["North"]["floors"]["Floor 1"]["side_left"]["source_boundary"] == "W"
    assert sidecar["elevation"]["boundary"]["East"]["floors"]["Floor 1"]["side_right"]["source_boundary"] == "N"
    assert sidecar["floor_map"] == {"F1": "Floor 1", "F2": "Floor 2"}
    # F-22 BLOCKER-1: this fixture is a real accepted attempt with no
    # `schema_version` declared (implicit legacy v1) — untrusted per
    # `_is_trusted_output_convention`, so a visible `unsupported_output_convention`
    # evidence entry is expected rather than an empty list.
    assert [e["type"] for e in sidecar["evidence"]] == ["unsupported_output_convention"]
    assert sidecar["output_convention"] == {
        "schema_version": "1", "declared": False, "trusted": False, "identity": None,
    }
    assert Path(packet["grade"]).exists()
    assert packet["score_criteria"] == sidecar["score_criteria"]


def test_judge_side_renders_every_attempt_and_promotes_accepted_grade(tmp_path):
    run_dir = _copy_run_subset(
        tmp_path,
        "run_2026-06-20_gpt54_reading",
        [
            ("0_reading/attempts/001/output.json", "0_reading/attempts/001/output.json"),
            ("0_reading/attempts/002/output.json", "0_reading/attempts/002/output.json"),
        ],
    )
    manifest = RunManifest.load(run_dir)
    gt = load_gt("sm21_anchor")

    artifacts = rs._render_all_attempt_grades(
        "0_reading",
        "sm21_anchor",
        run_dir,
        gt,
        manifest=manifest,
        grade=rs.GradeConfig(),
    )

    assert set(artifacts) == {1, 2}
    for attempt in (1, 2):
        adir = run_dir / "0_reading" / "attempts" / f"{attempt:03d}"
        assert (adir / "score_vs_gt.json").exists()
        assert (adir / "grade.png").exists()
        sidecar = json.loads((adir / "score_vs_gt.json").read_text(encoding="utf-8"))
        assert sidecar["attempt"] == attempt
        assert sidecar["scorer_schema"] == rs.LEGACY_SCORE_CACHE_SCHEMA
        assert sidecar["tolerances"] == _DEFAULT_TOLERANCES

    accepted = run_dir / "0_reading" / "attempts" / "002" / "grade.png"
    assert (run_dir / "0_reading" / "grade.png").read_bytes() == accepted.read_bytes()


def test_grade_uses_shared_metric_transform_for_gt_and_sidecar_pixels():
    gt = {
        "case": "tiny",
        "footprint": {"W_m": 10.0, "D_m": 4.0},
        "floors": [
            {
                "name": "Floor 1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "zones": [
                    {"id": "A", "role": "office", "rect_m": [0.0, 0.0, 5.0, 4.0]},
                    {"id": "B", "role": "office", "rect_m": [5.0, 0.0, 10.0, 4.0]},
                ],
            }
        ],
        "windows": [],
        "doors": [],
    }
    sidecar = {
        "stage": "1_correction",
        "attempt": 1,
        "source": "attempt_output",
        "scorer_schema": "7",
        "tolerances": {
            "wall_tol_m": 0.3,
            "window_centre_tol_m": 0.4,
            "position_tol_m": 0.3,
            "extent_tol_m": 0.3,
            "complete_eps_m": 0.05,
            "overlap_accept": 0.75,
            "overlap_complete": 0.95,
            "floor_line_tol_m": 0.3,
        },
        "scores": {
            "Floor 1": {
                "floor": "Floor 1",
                "vwalls": [{"truth": 5.0, "read": 5.0, "delta": 0.0}],
                "hwalls": [],
                "vwall_records": [
                    {
                        "status": "complete",
                        "orientation": "v",
                        "truth": 5.0,
                        "read": 5.0,
                        "delta": 0.0,
                        "lateral_drift": False,
                        "extent_drift": False,
                        "extent_start_drift": False,
                        "extent_end_drift": False,
                        "product": [5.0, 0.0, 4.0],
                        "gt": [5.0, 0.0, 4.0],
                        "product_intervals": [[5.0, 0.0, 4.0]],
                        "gt_intervals": [[5.0, 0.0, 4.0]],
                        "pieces": [],
                    }
                ],
                "hwall_records": [],
                "windows": {"N": [], "S": [], "E": [], "W": []},
                "extra_window_records": {"N": [], "S": [], "E": [], "W": []},
            }
        },
    }

    img = render_grade.render_grade("1_correction", sidecar, gt)
    tr = plan_transform(
        10.0,
        4.0,
        scale=render_grade.SCALE,
        offset_x=0,
        offset_y=render_grade.HEADER + render_grade.LABEL_H,
        margin_m=render_grade.PLAN_MARGIN_M,
    )
    split_px = tuple(round(v) for v in tr.px(5.0, 2.0))
    fill_px = tuple(round(v) for v in tr.px(2.0, 2.0))

    assert img.mode == "RGB"
    assert img.getpixel(split_px) == render_grade.GREEN
    assert img.getpixel(fill_px) == render_grade.GT_FILL
