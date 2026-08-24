"""Elevation score-view bindings — dispatch 2026-08-22 locks.

Covers the five required locks for
``AI_agent/logs/reviews/request/2026-08-22_elevation_score_bindings_dispatch.md``:

1. forward: the sm24 five-view run scores ``c2_scored`` with the elevation
   channel ``applicable`` through the real grading entry point;
2. convention: a flipped ``sign`` is refused — Va side via
   ``derive_opening_claim_applicability`` (P3) and judge side end-to-end as a
   ``rejected`` score;
3. mirror visibility: a whole-facade reflection that fits GT better than the
   declared frame MUST surface as a FAIL criterion on the real fixture, never
   as a silently-scored miss;
4. neuter: each lock is proven to bind the *wiring* — removing the call the
   scoring chain makes turns the lock's red off (the Va leg goes through the
   real ``derive_opening_claim_applicability`` entry, GPT verdict MINOR-2);
5. the generator derives bindings without case specialization: single-floor
   sm24 reproduces the hand-authored reference byte-for-byte on fields;
   multi-floor fingerprint OR per-floor-extent disagreement fails closed
   (S1 is ratified as a gt-generator fix and the interim pending-S1 flag is
   deleted, GPT verdict MAJOR-1/MAJOR-2); orientation fields must be paired
   (GPT verdict MINOR-1).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SM24_RUN = REPO_ROOT / "case_tests/e2e_tests/sm24_anchor/run_2026-08-02_sonnet_full_unsup"
SM24_GT = REPO_ROOT / "case_tests/test_baseline/gt/sm24_anchor/gt.json"
SM25_RUN = (
    REPO_ROOT
    / "case_tests/e2e_tests/sm25-L_anchor"
    / "run_2026-08-22_orchestrator_handson_H2_fullcase"
)
SM25_GT = REPO_ROOT / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json"
BUILDER = REPO_ROOT / "scripts/tool_scripts/build_score_view_bindings.py"

MIRROR_CRITERION = "reading.elevation_mirror_visible"


def _grade_payload(tmp_path: Path, payload: object, *, name: str,
                   bindings_override: dict | None = None) -> dict:
    """Real run_stage grading entry on the real sm24 sidecars and GT."""
    from scripts.tool_scripts import run_stage
    from src.agent.execution.manifest import RunManifest
    from src.agent.judge.score_schema import load_score_gt_identity

    run = tmp_path / name
    attempt = run / "0_reading/attempts/001"
    attempt.mkdir(parents=True)
    meta = run / "_run"
    meta.mkdir()
    for filename in ("view_manifest.json", "judge_score_bindings.json"):
        text = (SM24_RUN / "_run" / filename).read_text(encoding="utf-8")
        if bindings_override is not None and filename == "judge_score_bindings.json":
            text = json.dumps(bindings_override, sort_keys=True)
        (meta / filename).write_text(text, encoding="utf-8")
    (attempt / "output.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    _identity, document = load_score_gt_identity(SM24_GT)
    assert document is not None
    artifacts = run_stage._grade_typed_attempt_artifacts(
        "0_reading", document.case, attempt, document, gt_file=SM24_GT,
        manifest=RunManifest(case=document.case), grade=run_stage.GradeConfig(),
        run_profile="exploratory",
    )
    assert artifacts["score_vs_gt"] is not None
    return json.loads(Path(artifacts["score_vs_gt"]).read_text(encoding="utf-8"))


def _real_sm24_payload() -> dict:
    return json.loads((SM24_RUN / "0_reading/attempts/001/output.json").read_text(encoding="utf-8"))


def _mirror_east_windows(payload: dict, length_m: float = 20.0) -> dict:
    """Whole-facade reflection of the real East elevation window strokes."""
    import copy

    mirrored = copy.deepcopy(payload)
    for stroke in mirrored["views"]["East_view"]["strokes"]:
        geometry = stroke.get("geometry")
        if stroke.get("pen") == "window" and isinstance(geometry, dict) and "x_range_m" in geometry:
            lo, hi = geometry["x_range_m"]
            geometry["x_range_m"] = [round(length_m - hi, 6), round(length_m - lo, 6)]
    return mirrored


def _mirror_criteria(sidecar: dict) -> list[dict]:
    return [item for item in sidecar["payload"]["score_criteria"] if item["criterion_id"] == MIRROR_CRITERION]


def _strict_reason(sidecar: dict) -> str | None:
    """Feed the strict gate the two fields it consumes (JSON round-trip turns
    StrictWire tuples into lists, which model_validate would refuse)."""
    from types import SimpleNamespace

    from src.agent.judge.score_service import strict_payload_violation_reason

    payload = sidecar["payload"]
    return strict_payload_violation_reason(
        SimpleNamespace(
            kind=payload["kind"],
            score_criteria=tuple(SimpleNamespace(**item) for item in payload["score_criteria"]),
        )
    )


# ---------------------------------------------------------------------------
# Lock 1 (forward, sm24 leg) — the sm25 leg is blocked by S1 (see the
# execution log): Va's per-floor fingerprint/extent equality in
# facade_applicability.py cannot consume one binding over two floors whose
# fingerprints differ by float residue.
# ---------------------------------------------------------------------------


def test_real_five_view_run_scores_c2_with_elevation_applicable(tmp_path):
    sidecar = _grade_payload(tmp_path, _real_sm24_payload(), name="forward")
    assert sidecar["payload"]["kind"] == "c2_scored"
    channels = {item["channel"]: item for item in sidecar["payload"]["channel_applicability"]}
    assert channels["elevation"]["status"] == "applicable"
    assert set(channels["elevation"]["applicable_components"]) == {
        "elevation_opening_xy", "elevation_opening_z",
    }
    assert not _mirror_criteria(sidecar)


# ---------------------------------------------------------------------------
# Lock 3 — mirror visibility gate on the real fixture (green + red).
# ---------------------------------------------------------------------------


def test_mirror_gate_green_on_real_reading(tmp_path):
    sidecar = _grade_payload(tmp_path, _real_sm24_payload(), name="mirror_green")
    assert sidecar["payload"]["kind"] == "c2_scored"
    assert _mirror_criteria(sidecar) == []
    assert _strict_reason(sidecar) is None


def test_mirror_gate_red_when_reflection_fits_gt_better(tmp_path):
    sidecar = _grade_payload(tmp_path, _mirror_east_windows(_real_sm24_payload()), name="mirror_red")
    assert sidecar["payload"]["kind"] == "c2_scored"
    found = _mirror_criteria(sidecar)
    assert found, "a whole-facade reflection fitting GT better must surface, not score silently"
    assert found[0]["verdict"] == "fail"
    assert found[0]["na_reasons"] == {"East_view": 3}
    assert _strict_reason(sidecar) == "elevation_mirror_disagreement"


def test_mirror_gate_neuter_removes_the_wiring(tmp_path, monkeypatch):
    """Lock 4 for the mirror gate: the red comes from the call inside
    ``assemble_reading_score`` (wiring), not from the helper alone."""
    import src.agent.judge.reading_typed_score as rts

    monkeypatch.setattr(rts, "elevation_mirror_flip_witnesses", lambda **kwargs: ())
    sidecar = _grade_payload(tmp_path, _mirror_east_windows(_real_sm24_payload()), name="mirror_neuter")
    assert sidecar["payload"]["kind"] == "c2_scored"
    assert _mirror_criteria(sidecar) == []


# ---------------------------------------------------------------------------
# Lock 2 — flipped sign refused (Va P3 + judge end-to-end).
# ---------------------------------------------------------------------------


def _va_south_fixture():
    """One-floor South fixture for the Va convention lock: a valid
    (manifest, visibility ledger, elevation binding) triple whose sign wiring
    the real entry ``derive_opening_claim_applicability`` re-derives."""
    from src.agent.correction.facade_applicability import (
        CLAIM_ORDER, ElevationViewBindingV1, FacadeVisibilityLedgerV1,
        FloorVisibilityLedgerV1, _canonical_hash, _frame_hash, _segment_payload,
    )
    from src.agent.correction.schema import FacadeSegment, WorldInterval
    from src.agent.execution.manifest import hash_obj
    from src.agent.execution.view_manifest import (
        OpeningEvidence, RequiredViewEntry, ViewManifest,
    )

    fingerprint = "a" * 64

    def segment() -> FacadeSegment:
        return FacadeSegment(id="seg-s", floor_id="f1", facade_family="South", p1=(0.0, 0.0), p2=(2.0, 0.0),
            outward_normal=(0, -1), world_along_interval=WorldInterval(lo=0.0, hi=2.0), depth=0.0,
            visible_intervals=[WorldInterval(lo=0.0, hi=2.0)], source_footprint_fingerprint=fingerprint)

    evidence = OpeningEvidence(potentially_observable_claims=list(CLAIM_ORDER))
    entry = RequiredViewEntry(input_id="south", source_image="case_data/south.png", image_sha256=fingerprint,
        view_type="elevation", floor_ref=None, declared_direction_token="South",
        direction_source="standard_assumption", direction_semantics="building_axis",
        semantics_source="case_metadata", azimuth_deg=None, building_view_direction="South",
        dimensioned=True, expected_output_id="south", opening_evidence=evidence)
    payload = {"view_manifest_schema_version": "1", "claims_vocab_version": "1", "generator_version": "1",
        "completeness_ruleset_version": "1", "case_id": "case", "case_metadata_sha256": fingerprint,
        "entries": [entry.model_dump(mode="json")]}
    vm = ViewManifest(**payload, content_sha256=hash_obj(payload))
    proto = FacadeVisibilityLedgerV1(source_kind="accepted_correction", source_schema_version="3",
        source_output_sha256="b" * 64, facade_segments_sha256="c" * 64, feature_states_sha256="d" * 64,
        helper_versions=("floor_footprint_v1", "facade_visibility_v1"),
        floors=(FloorVisibilityLedgerV1(floor_id="f1", source_footprint_fingerprint=fingerprint, segments=(segment(),)),))
    vis = proto.model_copy(update={"facade_segments_sha256": _canonical_hash(_segment_payload(proto))})
    # world_axis/sign via the single source of truth, never hand-typed here.
    from src.agent.correction import facade_convention
    axis = facade_convention.world_axis("South")
    sign = facade_convention.resolve_sign("South", mirrored=False, local_x_positive="image_left_to_right")
    origin = 0.0 if sign == 1 else 2.0
    base = ElevationViewBindingV1(input_id="south", resolved_building_direction="South",
        resolution_source="manifest_building_axis", view_manifest_sha256=vm.content_sha256,
        orientation_output_hash=None, adapter_version=None, source_footprint_fingerprint=fingerprint,
        world_axis=axis, sign=sign, along_origin=origin, mirrored=False,
        local_x_positive="image_left_to_right", frame_transform_sha256="0" * 64)
    binding = base.model_copy(update={"frame_transform_sha256": _frame_hash(base)})
    return vm, vis, binding


def _va_opening(binding):
    from src.agent.correction.facade_applicability import (
        CLAIM_ORDER, ApplicabilityIntervalV1, ElevationClaimEvidenceV1,
        ELEVATION_POTENTIALLY_OBSERVABLE_CLAIMS, OpeningClaimTargetV1, OpeningClaimsV1,
    )

    target = ApplicabilityIntervalV1(lo=0.0, hi=2.0)
    rows = []
    for claim in CLAIM_ORDER:
        evidence = tuple(ElevationClaimEvidenceV1(source_input_id="south", local_interval=target) for _ in [0]
                         if claim in ELEVATION_POTENTIALLY_OBSERVABLE_CLAIMS)
        rows.append(OpeningClaimTargetV1(claim=claim, target_world_interval=target, positive_evidence=evidence))
    return OpeningClaimsV1(opening_id="o1", floor_id="f1", floor_ref=1, facade_segment_id="seg-s",
        facade_family="South", claims=tuple(rows))


def _va_flipped(binding):
    """sign-flipped (and re-hashed, so it stays self-consistent) binding."""
    from src.agent.correction.facade_applicability import _frame_hash

    flipped = binding.model_copy(update={"sign": -binding.sign, "along_origin": 2.0 if binding.sign == 1 else 0.0})
    return flipped.model_copy(update={"frame_transform_sha256": _frame_hash(flipped)})


def test_va_rejects_flipped_sign_through_real_entry():
    from src.agent.correction.facade_applicability import (
        FacadeApplicabilityInvariantError, derive_opening_claim_applicability,
    )

    vm, vis, binding = _va_south_fixture()
    derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(binding,),
                                       openings=(_va_opening(binding),))
    flipped = _va_flipped(binding)
    with pytest.raises(FacadeApplicabilityInvariantError) as excinfo:
        derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(flipped,),
                                           openings=(_va_opening(flipped),))
    assert "va_projection_frame_invalid" in str(excinfo.value)


def test_va_neuter_removes_the_sign_wiring(monkeypatch):
    """Lock 4 for the convention lock — REWORKED per GPT verdict MINOR-2.

    The old version monkeypatched ``fa._validate_bindings`` and then called the
    very same patched helper, so it never exercised the live wiring inside the
    real entry (removing the real entry's call left the test green).  Now the
    premise is proven on the real entry first (flipped sign raises), then ONLY
    the wiring is removed — the ``_validate_bindings`` call that
    ``derive_opening_claim_applicability`` makes — and the same flipped binding
    must sail through the real entry.
    """
    import src.agent.correction.facade_applicability as fa
    from src.agent.correction.facade_applicability import (
        FacadeApplicabilityInvariantError, OpeningApplicabilityLedgerV1,
        derive_opening_claim_applicability,
    )

    vm, vis, binding = _va_south_fixture()
    flipped = _va_flipped(binding)
    with pytest.raises(FacadeApplicabilityInvariantError):
        derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(flipped,),
                                           openings=(_va_opening(flipped),))
    monkeypatch.setattr(fa, "_validate_bindings",
                        lambda manifest, bindings: {b.input_id: b for b in bindings})
    ledger = derive_opening_claim_applicability(visibility=vis, manifest=vm, elevation_views=(flipped,),
                                                openings=(_va_opening(flipped),))
    assert isinstance(ledger, OpeningApplicabilityLedgerV1)  # wiring removed: nothing refuses it


def test_judge_side_rejects_tampered_sign_end_to_end(tmp_path):
    from src.agent.judge.score_schema import canonical_sha256

    bindings = json.loads((SM24_RUN / "_run/judge_score_bindings.json").read_text(encoding="utf-8"))
    for binding in bindings["bindings"]:
        if binding.get("kind") == "elevation" and binding["input_id"] == "East_view":
            binding["sign"] = -binding["sign"]
            binding["along_origin"] = 20.0
    # Recompute the envelope hash so the tamper reaches the sign checks instead
    # of being stopped by the (separate) content_sha256 self-check.
    bindings["content_sha256"] = canonical_sha256(
        {key: value for key, value in bindings.items() if key != "content_sha256"}
    )
    sidecar = _grade_payload(tmp_path, _real_sm24_payload(), name="tampered_sign",
                             bindings_override=bindings)
    assert sidecar["payload"]["kind"] == "rejected"
    assert sidecar["payload"]["error_code"] == "score_direction_unresolved"


# ---------------------------------------------------------------------------
# Lock 5 (generator) — derivation is not case-specialized and fails closed on
# the unratified S1 multi-floor fingerprint choice.
# ---------------------------------------------------------------------------


def _run_builder(run_dir: Path, gt_file: Path, *extra: str, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BUILDER), "--run-dir", str(run_dir), "--gt", str(gt_file), "--out", str(out), *extra],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300,
    )


def test_generator_reproduces_hand_authored_sm24_bindings(tmp_path):
    out = tmp_path / "sm24_bindings.json"
    result = _run_builder(SM24_RUN, SM24_GT, out=out)
    assert result.returncode == 0, result.stderr
    built = json.loads(out.read_text(encoding="utf-8"))
    reference = json.loads((SM24_RUN / "_run/judge_score_bindings.json").read_text(encoding="utf-8"))
    assert {b["input_id"]: b for b in built["bindings"]} == {b["input_id"]: b for b in reference["bindings"]}

    from src.agent.correction import facade_convention
    for binding in built["bindings"]:
        if binding["kind"] != "elevation":
            continue
        family = binding["resolved_building_direction"]
        assert binding["world_axis"] == facade_convention.world_axis(family)
        assert binding["sign"] == facade_convention.resolve_sign(
            family, mirrored=binding["mirrored"], local_x_positive=binding["local_x_positive"])


def test_generator_fails_closed_on_sm25_multi_floor_fingerprint():
    """Re-anchored 2026-08-25 (F-93): S1 (dispatch §五, ratified 2026-08-22) is
    the fix that makes identical multi-floor outlines carry bit-identical
    footprint fingerprints, and the real sm25 gt was regenerated on that fix
    (`e982eba`, 2026-08-23) — F1/F2's South-facade fingerprints now agree
    byte-for-byte, so the CLI entry on the real run+gt no longer disagrees and
    can no longer exercise this path. The behavior this lock guards (fail
    closed when a multi-floor footprint genuinely disagrees) is still live, so
    per [[regression-case-must-prove-its-own-premise]] this now builds a
    sample that actually satisfies the premise instead of asserting on gt that
    no longer does — mirroring the sibling extent-disagreement lock below
    (MAJOR-2): a synthetic gt via ``SimpleNamespace`` calling the real
    ``_elevation_binding_fields`` directly, with two floors carrying
    DIFFERENT footprint fingerprints (not float residue, which the extent
    lock already covers).
    """
    from types import SimpleNamespace

    from scripts.tool_scripts.build_score_view_bindings import _elevation_binding_fields

    def segment(floor_id, fingerprint):
        return SimpleNamespace(floor_id=floor_id, facade_family="South",
            source_footprint_fingerprint=fingerprint,
            world_along_interval=SimpleNamespace(lo=0.0, hi=25.0))

    gt = SimpleNamespace(floors=[
        SimpleNamespace(id="F1", boundary_segments=[segment("F1", "a" * 64)]),
        SimpleNamespace(id="F2", boundary_segments=[segment("F2", "b" * 64)])])
    views = {"South": [SimpleNamespace(id="South_view", floor_ids=("F1", "F2"))]}
    entry = SimpleNamespace(input_id="South_view", view_type="elevation",
        direction_semantics="building_axis", building_view_direction="South")

    with pytest.raises(SystemExit) as excinfo:
        _elevation_binding_fields(entry, gt, views)
    assert "S1" in str(excinfo.value) and "fingerprints" in str(excinfo.value)


def test_generator_rejects_the_deleted_pending_s1_flag(tmp_path):
    """MAJOR-1 rework: the interim flag is deleted — it produced an exit-0
    sidecar that passes the frozen loader and the GT companion validator and
    only dies at the authoritative Va consumer (silent-unusable path). argparse
    must now refuse the very flag name."""
    out = tmp_path / "sm25_bindings.json"
    result = _run_builder(SM25_RUN, SM25_GT, "--elevation-fingerprint-union-pending-s1", out=out)
    assert result.returncode != 0
    assert "--elevation-fingerprint-union-pending-s1" in result.stderr
    assert "unrecognized arguments" in result.stderr
    assert not out.exists()


def test_generator_fails_closed_when_only_per_floor_extents_disagree():
    """MAJOR-2 rework: agreeing fingerprints alone are NOT enough — per-floor
    world_along extents must be exactly equal, else the origin a cross-floor
    union would produce matches no single floor of the authoritative Va
    consumer (the real sm25 North/South shape: F2 differs by a 3.55e-15 m
    float residue)."""
    from types import SimpleNamespace

    from scripts.tool_scripts.build_score_view_bindings import _elevation_binding_fields

    def gt_with(f1_extent, f2_extent, fingerprint="f" * 64):
        def segment(floor_id, extent):
            return SimpleNamespace(floor_id=floor_id, facade_family="South",
                source_footprint_fingerprint=fingerprint,
                world_along_interval=SimpleNamespace(lo=extent[0], hi=extent[1]))
        return SimpleNamespace(floors=[
            SimpleNamespace(id="F1", boundary_segments=[segment("F1", f1_extent)]),
            SimpleNamespace(id="F2", boundary_segments=[segment("F2", f2_extent)])])

    views = {"South": [SimpleNamespace(id="South_view", floor_ids=("F1", "F2"))]}
    entry = SimpleNamespace(input_id="South_view", view_type="elevation",
        direction_semantics="building_axis", building_view_direction="South")

    # identical fingerprints, extents differing only by float residue: refuse,
    # never fall back to a cross-floor union origin.
    gt = gt_with((0.0, 25.0), (-3.552713678800501e-15, 24.999999999999996))
    with pytest.raises(SystemExit) as excinfo:
        _elevation_binding_fields(entry, gt, views)
    assert "extent" in str(excinfo.value)
    assert "refuses to paper over" in str(excinfo.value)

    # per-floor state identical on every floor: a binding IS produced and
    # along_origin comes from the unique per-floor extent.
    from src.agent.correction import facade_convention
    sign = facade_convention.resolve_sign("South", mirrored=False, local_x_positive="image_left_to_right")
    fields = _elevation_binding_fields(entry, gt_with((0.0, 25.0), (0.0, 25.0)), views)
    assert fields["sign"] == sign
    assert fields["along_origin"] == (0.0 if sign == 1 else 25.0)


def test_generator_orientation_fields_must_be_paired():
    """MINOR-1 rework: a one-sided orientation fill passes the schema and the
    judge validator and only dies at the authoritative Va consumer; the builder
    refuses it at production time (patching the schema seam, not changing it)."""
    from scripts.tool_scripts.build_score_view_bindings import _assert_orientation_paired

    _assert_orientation_paired("x", None, None)          # manifest route: both absent
    _assert_orientation_paired("x", "a" * 64, "v1")      # sidecar route: both present
    with pytest.raises(SystemExit):
        _assert_orientation_paired("x", "a" * 64, None)
    with pytest.raises(SystemExit):
        _assert_orientation_paired("x", None, "v1")
