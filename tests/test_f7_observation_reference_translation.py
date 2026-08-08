"""F-7 (2026-08-05): correction ``source_ids`` are observation references, not
locators — the correction LLM cannot see or compute the 64-hex locator hash
(it embeds reading-artifact bytes the draw never receives; F-5's twin defect:
a consumer contract only ever satisfied by hand-built fixtures, never by a
real draw). The fix has three parts, each locked below:

1. Translation: ``_claim_links`` translates a model-cited
   ``<expected_output_id>/<observation_id>`` reference into its internal
   locator before doing anything else; an already-valid ``src:<64hex>``
   locator still passes through unchanged (backward compatibility for
   fixtures/artifacts that already carry one). Three distinct, named failure
   codes — never a silent guess — for an unknown view, an unknown
   observation, and an ambiguous/malformed reference.
2. Prompt catalog: the legal-reference listing injected into the correction
   prompt is derived from the exact same ``_catalog`` builder the
   enforcement path validates against (mechanical single-exit derivation),
   and never contains a ``src:`` locator or a 64-hex hash.
3. Failure classification: ``WindowResolverInputError.category`` distinguishes
   a model draw mistake (``model_draw_error`` — archived as a failed
   attempt, blind-resampled) from an input-integrity fault (``input_integrity_error``
   — hard crash, no resample). This file proves both paths through the real
   stepwise orchestrator, not just the return value of a helper.

Fixtures reuse ``tests/test_c2_b5_source_routing.py``'s ``_entry``/``_manifest``/
``_reading``/``_geom``/``_base``/``_provenance`` builders (real Pydantic model
constructors, not hand-copied dict literals) rather than re-inventing them —
per this project's F-5/F-7 governance lesson, a test fixture for a contract
must be built through the contract's own constructors, never retyped.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import scripts.tool_scripts.run_stage as rs  # noqa: E402

from src.agent.correction.finalize import FinalizeResult  # noqa: E402
from src.agent.correction.feature_state import derive_feature_state_claims  # noqa: E402
from src.agent.correction.parse import correction_target, parse_correction_draw  # noqa: E402
from src.agent.correction.schema import CorrectedGeometry, CorrectedGeometryV3  # noqa: E402
from src.agent.correction.window_sources import (  # noqa: E402
    ObservationReferenceCatalogEntry,
    WindowResolverInputError,
    build_observation_reference_catalog_from_run,
    build_verified_window_resolver_inputs,
    build_window_source_offer,
    derive_observation_reference_catalog,
    format_observation_reference_catalog,
    source_locator,
)
from src.agent.execution.manifest import RunManifest  # noqa: E402
from src.agent.execution.policy import RunPolicy  # noqa: E402
from src.agent.execution.run_meta import run_meta_path  # noqa: E402
from src.agent.execution.stage_runner import StageRunner  # noqa: E402
from src.agent.execution.step_orchestrator import run_one_stage  # noqa: E402
from src.agent.execution.view_manifest import VIEW_MANIFEST_NAME  # noqa: E402
from src.validator.checks.schema import CheckLayer, CheckReport  # noqa: E402

from tests.test_c2_b5_source_routing import (  # noqa: E402
    _base,
    _entry,
    _geom,
    _manifest,
    _provenance,
    _reading,
)


# =========================================================================== #
# 1. Translation layer — positive + backward compat + three named failures
# =========================================================================== #
def test_f7_observation_reference_translates_to_the_real_locator():
    """`<view>/<observation_id>` must resolve to EXACTLY the locator a hand
    computed `source_locator(...)` call would produce for the same reading
    bytes — the translation is a pure re-derivation, not an independent path."""
    manifest, raw_manifest, artifacts, fact = _base()
    geom = _geom()
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={
        "provenance": _provenance({"existence": {"provenance": "observed", "source_ids": ["plan/W-01"]}})
    })]})
    marker = build_verified_window_resolver_inputs(
        producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,),
    )
    (link,) = marker.inputs.claim_links
    expected_locator = source_locator(
        input_id="plan", observation_id="W-01",
        output_sha256=hashlib.sha256(artifacts["plan"]).hexdigest(),
    )
    assert link.source_locator == expected_locator
    assert link.window_id == "w1" and link.claim == "existence"


def test_f7_already_valid_locator_still_passes_through_unchanged():
    """Backward compatibility: a fixture/artifact that already carries a real
    ``src:<64hex>`` locator (never an observation reference) must be accepted
    exactly as before — B5's existing test suite depends on this."""
    manifest, raw_manifest, artifacts, fact = _base()
    real_locator = source_locator(
        input_id="plan", observation_id="W-01",
        output_sha256=hashlib.sha256(artifacts["plan"]).hexdigest(),
    )
    geom = _geom()
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={
        "provenance": _provenance({"existence": {"provenance": "observed", "source_ids": [real_locator]}})
    })]})
    marker = build_verified_window_resolver_inputs(
        producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,),
    )
    (link,) = marker.inputs.claim_links
    assert link.source_locator == real_locator


def test_f7_unknown_view_name_is_a_named_model_draw_error():
    manifest, raw_manifest, artifacts, fact = _base()
    geom = _geom()
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={
        "provenance": _provenance({"existence": {"provenance": "observed", "source_ids": ["nonexistent_view/W-01"]}})
    })]})
    with pytest.raises(WindowResolverInputError, match="observation_reference_view_unknown") as exc:
        build_verified_window_resolver_inputs(
            producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,),
        )
    assert exc.value.category == "model_draw_error"
    assert exc.value.context["expected_output_id"] == "nonexistent_view"


def test_f7_unknown_observation_id_is_a_named_model_draw_error():
    manifest, raw_manifest, artifacts, fact = _base()
    geom = _geom()
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={
        "provenance": _provenance({"existence": {"provenance": "observed", "source_ids": ["plan/W-99"]}})
    })]})
    with pytest.raises(WindowResolverInputError, match="observation_reference_observation_unknown") as exc:
        build_verified_window_resolver_inputs(
            producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,),
        )
    assert exc.value.category == "model_draw_error"
    assert exc.value.context == {
        "window_id": "w1", "claim": "existence",
        "expected_output_id": "plan", "observation_id": "W-99",
    }


@pytest.mark.parametrize("bad_reference", ["W-01", "plan/", "/W-01", ""])
def test_f7_ambiguous_or_malformed_reference_is_rejected_never_guessed(bad_reference):
    """A bare id (no `/`) or a malformed reference must be rejected outright
    — the code must never guess which view a bare id belongs to, even when
    (as here) only one view happens to contain a matching observation id."""
    manifest, raw_manifest, artifacts, fact = _base()
    geom = _geom()
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={
        "provenance": _provenance({"existence": {"provenance": "observed", "source_ids": [bad_reference]}})
    })]})
    with pytest.raises(WindowResolverInputError, match="observation_reference_ambiguous") as exc:
        build_verified_window_resolver_inputs(
            producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,),
        )
    assert exc.value.category == "model_draw_error"


# =========================================================================== #
# 2. Prompt catalog — mechanically derived, no locator leakage
# =========================================================================== #
def test_f7_observation_reference_catalog_matches_source_catalog_exactly():
    manifest, raw_manifest, artifacts, fact = _base()
    # Give the elevation view a second window observation so the catalog
    # spans two views/two observations (not a degenerate single-entry case).
    south = json.loads(artifacts["south"])
    south["strokes"] = [{"id": "E-01", "pen": "window", "geometry": {"x_range_m": [0.5, 1.5], "y_range_m": [1.0, 2.0]}}]
    artifacts = dict(artifacts, south=json.dumps(south, separators=(",", ":")).encode())

    entries = derive_observation_reference_catalog(
        raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts,
    )
    refs = sorted(entry.reference for entry in entries)
    assert refs == ["plan/W-01", "south/E-01"]  # exactly this set, not "contains"

    by_ref = {entry.reference: entry.allowed_claims for entry in entries}
    assert by_ref["plan/W-01"] == ("existence", "host", "along", "width")
    assert by_ref["south/E-01"] == ("existence", "along", "width", "sill", "head", "appearance")

    # Cross-check against the OTHER public wrapper over the same `_catalog`
    # exit (`build_window_source_offer`): both must describe the same rows.
    offer = build_window_source_offer(raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts)
    expected_output_ids = manifest.expected_output_ids()
    offer_refs = sorted(
        f"{expected_output_ids[row.source_input_id]}/{row.observation_id}"
        for row in offer.source_windows
    )
    assert offer_refs == refs

    text = format_observation_reference_catalog(entries)
    assert "plan/W-01" in text and "south/E-01" in text
    assert "src:" not in text
    assert not re.search(r"[0-9a-f]{64}", text)


def test_f7_catalog_empty_when_no_window_observations():
    manifest, raw_manifest, artifacts, fact = _base()
    plan = json.loads(artifacts["plan"]); plan["strokes"] = []
    artifacts = dict(artifacts, plan=json.dumps(plan, separators=(",", ":")).encode())
    entries = derive_observation_reference_catalog(
        raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts,
    )
    assert entries == ()
    text = format_observation_reference_catalog(entries)
    assert "src:" not in text and text  # non-empty placeholder text, still safe


def test_f7_build_observation_reference_catalog_from_run_reads_real_run_layout(tmp_path):
    """The run-directory adapter must derive the identical catalog a direct
    `derive_observation_reference_catalog` call would, from files laid out
    exactly as the real 0_reading/_run directories place them; and it must
    return None (not raise) when the manifest is not yet on disk."""
    manifest, raw_manifest, artifacts, fact = _base()
    run_dir = tmp_path / "run"
    reading_dir = run_dir / "0_reading"
    reading_dir.mkdir(parents=True)

    # Before the manifest is provisioned: advisory-only, must not raise.
    assert build_observation_reference_catalog_from_run(run_dir=run_dir, reading_dir=reading_dir) is None

    run_meta_path(run_dir, VIEW_MANIFEST_NAME, for_write=True).write_bytes(raw_manifest)
    for input_id, raw in artifacts.items():
        expected_output_id = manifest.entry_by_input_id(input_id).expected_output_id
        (reading_dir / f"{expected_output_id}.json").write_bytes(raw)

    from_run = build_observation_reference_catalog_from_run(run_dir=run_dir, reading_dir=reading_dir)
    direct = format_observation_reference_catalog(
        derive_observation_reference_catalog(raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts)
    )
    assert from_run == direct


# =========================================================================== #
# 3. Failure classification — model_draw_error resamples, input_integrity_error crashes
# =========================================================================== #
def _write_run_layout(run_dir: Path, manifest, raw_manifest: bytes, artifacts: dict) -> None:
    (run_dir / "0_reading").mkdir(parents=True, exist_ok=True)
    (run_dir / "1_correction").mkdir(parents=True, exist_ok=True)
    run_meta_path(run_dir, VIEW_MANIFEST_NAME, for_write=True).write_bytes(raw_manifest)
    for input_id, raw in artifacts.items():
        expected_output_id = manifest.entry_by_input_id(input_id).expected_output_id
        (run_dir / "0_reading" / f"{expected_output_id}.json").write_bytes(raw)


def test_f7_model_draw_error_is_archived_as_a_failed_attempt_and_blind_resampled(tmp_path, monkeypatch):
    """Real `_draw_correction`, real `build_verified_window_inputs_from_run` /
    `_claim_links` on the FIRST (bad) attempt; a cheap legacy-v2 SECOND attempt
    that bypasses window-source resolution entirely proves the resample is a
    genuinely independent draw, not a retry of the same rejected one. Wired
    through the real `run_one_stage` stochastic loop (not asserted only on a
    helper's return value) — attempt count, both attempt files on disk, and
    the exact FAIL check_id are all locked."""
    import src.agent.pipeline as pipeline
    import src.agent.correction.finalize as finalize_mod
    import src.agent.correction.window_sources as ws
    import src.validator.checks.correction as corr_checks

    manifest, raw_manifest, artifacts, fact = _base()
    run_dir = tmp_path / "run"
    _write_run_layout(run_dir, manifest, raw_manifest, artifacts)

    bad_geom = _geom()
    bad_geom = bad_geom.model_copy(update={"windows": [bad_geom.windows[0].model_copy(update={
        "provenance": _provenance({"existence": {"provenance": "observed", "source_ids": ["plan/W-99"]}})
    })]})
    good_geom = CorrectedGeometry.model_validate(
        {**json.loads(bad_geom.model_dump_json()), "schema_version": "2", "windows": []}
    )
    assert good_geom.schema_version == "2"  # sidesteps window-source resolution entirely

    calls = {"n": 0}

    def fake_run_correction(*a, **k):
        calls["n"] += 1
        return bad_geom if calls["n"] == 1 else good_geom

    def fake_finalize(geom_or_payload, *, vector_dir, target, verified_window_inputs=None, tol=None):
        return FinalizeResult(
            geom=good_geom, audit_payload={},
            feature_state_claims=derive_feature_state_claims(target, good_geom),
        )

    monkeypatch.setattr(pipeline, "run_correction", fake_run_correction)
    monkeypatch.setattr(pipeline, "correction_draw_issues", lambda *a, **k: [])
    monkeypatch.setattr(rs, "dimensioned_view_names", lambda *a, **k: set())
    monkeypatch.setattr(ws, "verify_reading_stage_root_against_accepted_attempt", lambda *a, **k: None)
    monkeypatch.setattr(finalize_mod, "finalize_correction_draw", fake_finalize)
    monkeypatch.setattr(corr_checks, "check_correction", lambda *a, **k: CheckReport(stage="1_correction"))

    policy = RunPolicy(capability_profile="rectangular", run_profile="exploratory")
    runner = StageRunner(run_dir, RunManifest(case="f7-test"))

    def draw_fn(feedback):
        assert feedback is None  # the stochastic loop must stay blind
        return rs._draw_correction(run_dir, "testdata", expected_zones=None, relied=False, policy=policy)

    out = run_one_stage(stage="1_correction", runner=runner, stage_dir=run_dir / "1_correction",
                        policy=policy, draw_fn=draw_fn)

    assert calls["n"] == 2, "the blind resample must issue a SECOND draw, not retry the same one"
    assert out.attempts_used == 2 and out.accepted_attempt == 2
    attempt1_dir = run_dir / "1_correction" / "attempts" / "001"
    attempt2_dir = run_dir / "1_correction" / "attempts" / "002"
    assert attempt1_dir.is_dir() and attempt2_dir.is_dir()

    report1 = CheckReport.model_validate_json((attempt1_dir / "checks.json").read_bytes())
    assert report1.passed is False
    blocking_ids = {result.check_id for result in report1.blocking()}
    assert "correction.window_source_reference" in blocking_ids
    fail_result = next(r for r in report1.blocking() if r.check_id == "correction.window_source_reference")
    assert "observation_reference_observation_unknown" in fail_result.message

    report2 = CheckReport.model_validate_json((attempt2_dir / "checks.json").read_bytes())
    assert report2.passed is True


def test_f7_input_integrity_error_still_hard_crashes_no_resample(tmp_path, monkeypatch):
    """The reading artifact itself is broken (duplicate stroke ids within one
    view — an input-integrity fault per the F-7 ruling, not a model mistake):
    `_draw_correction` must RAISE, not swallow it into a failing CheckReport —
    resampling the correction draw cannot fix a broken reading artifact."""
    import src.agent.pipeline as pipeline
    import src.agent.correction.window_sources as ws

    manifest, raw_manifest, artifacts, fact = _base()
    # Corrupt the reading artifact itself: two strokes sharing one id.
    plan = json.loads(artifacts["plan"])
    plan["strokes"] = plan["strokes"] * 2
    artifacts = dict(artifacts, plan=json.dumps(plan, separators=(",", ":")).encode())

    run_dir = tmp_path / "run"
    _write_run_layout(run_dir, manifest, raw_manifest, artifacts)

    geom = _geom()  # existence source_ids already a real locator — irrelevant, dies earlier
    monkeypatch.setattr(pipeline, "run_correction", lambda *a, **k: geom)
    monkeypatch.setattr(pipeline, "correction_draw_issues", lambda *a, **k: [])
    monkeypatch.setattr(rs, "dimensioned_view_names", lambda *a, **k: set())
    monkeypatch.setattr(ws, "verify_reading_stage_root_against_accepted_attempt", lambda *a, **k: None)

    policy = RunPolicy(capability_profile="rectangular", run_profile="exploratory")
    with pytest.raises(WindowResolverInputError, match="duplicate_source_observation") as exc:
        rs._draw_correction(run_dir, "testdata", expected_zones=None, relied=False, policy=policy)
    assert exc.value.category == "input_integrity_error"
    # No attempt was ever archived for a crash that never returns to the loop.
    assert not (run_dir / "1_correction" / "attempts").exists()


# =========================================================================== #
# Category spot-checks on the classification table itself (a representative
# member of each bucket, not exhaustive re-derivation of §2.4's table).
# =========================================================================== #
def test_f7_category_producer_prefill_is_model_draw_error():
    payload = _geom().model_dump(mode="json")
    payload["windows"][0]["facade_segment_id"] = "fake"
    with pytest.raises(WindowResolverInputError, match="producer_segment_ref_prefilled") as exc:
        parse_correction_draw(payload, correction_target("orthogonal_polygon"))
    assert exc.value.category == "model_draw_error"


def test_f7_category_duplicate_source_observation_is_input_integrity_error():
    _, raw_manifest, artifacts, _ = _base()
    row = {"id": "W-01", "pen": "window", "geometry": {"x_range_m": [1.0, 2.0], "y_range_m": [0.0, 1.0]}}
    artifacts = dict(artifacts, plan=_reading(row, row))
    with pytest.raises(WindowResolverInputError, match="duplicate_source_observation") as exc:
        build_window_source_offer(raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts)
    assert exc.value.category == "input_integrity_error"


# =========================================================================== #
# MAJOR ② (rework r1): model floor-count mismatch is a model_draw_error, not
# input_integrity. `_check_floor_order` used to raise one compound `A or B`
# classified input_integrity_error; B reads `producer.floors` (the model's
# output) so it must resample. A (manifest floor_refs non-contiguous) stays
# input_integrity — it reads only the manifest.
# =========================================================================== #
def _geom_with_extra_floor():
    """A v3 producer that draws TWO floors while `_base()`'s manifest declares
    only one plan floor_ref — trips the model-half (B) of `_check_floor_order`.
    The window stays on f1 with a valid existence claim so `_producer_preflight`
    and `_claim_links` pass and execution reaches `_check_floor_order`."""
    payload = _geom().model_dump(mode="json")
    payload["floors"].append({
        "id": "f2", "name": "F2", "z_floor": 3.0, "ceiling_height": 3.0,
        "footprint": {"vertices": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]},
        "cells": [{"id": "r2", "x": [0.0, 4.0], "y": [0.0, 3.0]}],
    })
    return CorrectedGeometryV3.model_validate(payload)


def test_f7_category_producer_floor_count_mismatch_is_model_draw_error():
    """Per-point audit (MAJOR ②): a model that draws a different NUMBER of floors
    than the manifest declares is the model's fault — a fresh draw can fix it —
    so it must be `model_draw_error`, not `input_integrity_error`."""
    manifest, raw_manifest, artifacts, fact = _base()
    with pytest.raises(WindowResolverInputError, match="producer_floor_count_mismatch") as exc:
        build_verified_window_resolver_inputs(
            producer_draw=_geom_with_extra_floor(), raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,),
        )
    assert exc.value.category == "model_draw_error"
    assert exc.value.context["manifest_floor_count"] == 1
    assert exc.value.context["producer_floor_count"] == 2


def test_f7_floor_count_mismatch_archived_as_failed_attempt_and_resampled(tmp_path, monkeypatch):
    """Real `run_one_stage` stochastic loop: a wrong-floor-count draw is a
    model_draw_error, so `_draw_correction` must file it as a gate①-blocked
    attempt and blind-resample — NOT hard-crash (which the old compound
    input_integrity classification did). Lock pins the actual path: the bad
    attempt's check record carries the exact code, and a second draw is issued."""
    import src.agent.pipeline as pipeline
    import src.agent.correction.finalize as finalize_mod
    import src.agent.correction.window_sources as ws
    import src.validator.checks.correction as corr_checks

    manifest, raw_manifest, artifacts, fact = _base()
    run_dir = tmp_path / "run"
    _write_run_layout(run_dir, manifest, raw_manifest, artifacts)

    bad_geom = _geom_with_extra_floor()
    good_geom = CorrectedGeometry.model_validate(
        {**json.loads(bad_geom.model_dump_json()), "schema_version": "2", "windows": []}
    )
    assert good_geom.schema_version == "2"  # sidesteps window-source resolution entirely

    calls = {"n": 0}

    def fake_run_correction(*a, **k):
        calls["n"] += 1
        return bad_geom if calls["n"] == 1 else good_geom

    def fake_finalize(geom_or_payload, *, vector_dir, target, verified_window_inputs=None, tol=None):
        return FinalizeResult(
            geom=good_geom, audit_payload={},
            feature_state_claims=derive_feature_state_claims(target, good_geom),
        )

    monkeypatch.setattr(pipeline, "run_correction", fake_run_correction)
    monkeypatch.setattr(pipeline, "correction_draw_issues", lambda *a, **k: [])
    monkeypatch.setattr(rs, "dimensioned_view_names", lambda *a, **k: set())
    monkeypatch.setattr(ws, "verify_reading_stage_root_against_accepted_attempt", lambda *a, **k: None)
    monkeypatch.setattr(finalize_mod, "finalize_correction_draw", fake_finalize)
    monkeypatch.setattr(corr_checks, "check_correction", lambda *a, **k: CheckReport(stage="1_correction"))

    policy = RunPolicy(capability_profile="rectangular", run_profile="exploratory")
    runner = StageRunner(run_dir, RunManifest(case="f7-floor-test"))

    def draw_fn(feedback):
        assert feedback is None  # the stochastic loop must stay blind
        return rs._draw_correction(run_dir, "testdata", expected_zones=None, relied=False, policy=policy)

    out = run_one_stage(stage="1_correction", runner=runner, stage_dir=run_dir / "1_correction",
                        policy=policy, draw_fn=draw_fn)

    assert calls["n"] == 2, "wrong-floor-count draw must resample, not hard-crash"
    assert out.attempts_used == 2 and out.accepted_attempt == 2
    attempt1 = CheckReport.model_validate_json(
        (run_dir / "1_correction" / "attempts" / "001" / "checks.json").read_bytes())
    assert attempt1.passed is False
    fail_result = next(r for r in attempt1.blocking() if r.check_id == "correction.window_source_reference")
    assert "producer_floor_count_mismatch" in fail_result.message


# =========================================================================== #
# MAJOR ① (rework r1): under a v3 target, a non-exportable observation-reference
# catalog is a hard precondition (name the missing file + producer stage), not a
# silent None that lets the model draw blind and fails opaquely two stages later.
# Default behaviour (advisory None) is preserved for non-v3 callers.
# =========================================================================== #
def test_f7_v3_catalog_missing_manifest_raises_naming_path(tmp_path):
    manifest, raw_manifest, artifacts, _ = _base()
    run_dir = tmp_path / "run"
    reading_dir = run_dir / "0_reading"
    reading_dir.mkdir(parents=True)
    # No view manifest on disk.
    with pytest.raises(WindowResolverInputError, match="observation_reference_catalog_unavailable") as exc:
        build_observation_reference_catalog_from_run(
            run_dir=run_dir, reading_dir=reading_dir, required_for_v3=True)
    assert exc.value.context["artifact"] == "view_manifest"
    assert exc.value.context["produced_by_stage"] == "0_reading"
    assert exc.value.context["missing_artifact"]


def test_f7_v3_catalog_missing_reading_raises_naming_path(tmp_path):
    manifest, raw_manifest, artifacts, _ = _base()
    run_dir = tmp_path / "run"
    reading_dir = run_dir / "0_reading"
    reading_dir.mkdir(parents=True)
    run_meta_path(run_dir, VIEW_MANIFEST_NAME, for_write=True).write_bytes(raw_manifest)
    # Provision every required reading EXCEPT the elevation -> catalog cannot export.
    for input_id in ("plan",):
        expected_output_id = manifest.entry_by_input_id(input_id).expected_output_id
        (reading_dir / f"{expected_output_id}.json").write_bytes(artifacts[input_id])
    with pytest.raises(WindowResolverInputError, match="observation_reference_catalog_unavailable") as exc:
        build_observation_reference_catalog_from_run(
            run_dir=run_dir, reading_dir=reading_dir, required_for_v3=True)
    assert exc.value.context["artifact"] == "reading"
    assert exc.value.context["expected_output_id"] == "south"
    assert "south.json" in exc.value.context["missing_artifact"]
    assert exc.value.context["produced_by_stage"] == "0_reading"


def test_f7_v3_catalog_complete_injects_normally(tmp_path):
    manifest, raw_manifest, artifacts, _ = _base()
    run_dir = tmp_path / "run"
    reading_dir = run_dir / "0_reading"
    reading_dir.mkdir(parents=True)
    run_meta_path(run_dir, VIEW_MANIFEST_NAME, for_write=True).write_bytes(raw_manifest)
    for input_id, raw in artifacts.items():
        expected_output_id = manifest.entry_by_input_id(input_id).expected_output_id
        (reading_dir / f"{expected_output_id}.json").write_bytes(raw)
    # When everything is on disk, required_for_v3 must NOT raise — same text as advisory path.
    injected = build_observation_reference_catalog_from_run(
        run_dir=run_dir, reading_dir=reading_dir, required_for_v3=True)
    advisory = build_observation_reference_catalog_from_run(
        run_dir=run_dir, reading_dir=reading_dir)
    assert injected == advisory and injected is not None


def test_f7_v3_missing_catalog_hard_fails_at_draw_correction_entry(tmp_path, monkeypatch):
    """Real-entry lock: the precondition surfaces at `_draw_correction`'s entry
    (the catalog call sits before run_correction with no try/except), so a v3 run
    with no manifest fails loudly instead of drawing blind."""
    import src.agent.correction.window_sources as ws
    run_dir = tmp_path / "run"
    monkeypatch.setattr(ws, "verify_reading_stage_root_against_accepted_attempt", lambda *a, **k: None)
    policy = RunPolicy(capability_profile="orthogonal_polygon", run_profile="exploratory")
    with pytest.raises(WindowResolverInputError, match="observation_reference_catalog_unavailable") as exc:
        rs._draw_correction(run_dir, "testdata", expected_zones=None, relied=False, policy=policy)
    assert exc.value.context["produced_by_stage"] == "0_reading"
    assert exc.value.context["artifact"] == "view_manifest"


# =========================================================================== #
# MAJOR ③ (rework r1): parse.py's two prefilled-raise sites are NOT a
# classification point — they live in the inner-retry validator and never reach
# run_stage's model_draw_error->archive classifier. This pins the ACTUAL path.
# =========================================================================== #
def test_f7_parse_prefilled_raises_in_inner_validator_not_outer_classifier():
    """The inner validator `_draw_correction` actually wires
    (`_schema_only_correction_validator`) rejects a prefilled payload — that is
    the inner blind-retry trigger, not the outer classifier. If someone removes
    these raises thinking classification covers prefill elsewhere, this goes red
    (the inner self-correction chance is lost)."""
    from src.agent.pipeline import _schema_only_correction_validator
    target = correction_target("orthogonal_polygon")

    payload_seg = _geom().model_dump(mode="json")
    payload_seg["windows"][0]["facade_segment_id"] = "fake"
    with pytest.raises(WindowResolverInputError, match="producer_segment_ref_prefilled"):
        _schema_only_correction_validator(payload_seg, target)

    payload_audit = _geom().model_dump(mode="json")
    payload_audit["corrections"] = [{"kind": "window_host_resolution"}]
    # F-16 (2026-08-08, §6 摊一 Step 2): strip the round-tripped, derived
    # `floor` so this isolates the audit-row door, not the unrelated
    # `producer_window_floor_populated` one.
    for window in payload_audit["windows"]:
        window.pop("floor", None)
    with pytest.raises(WindowResolverInputError, match="producer_resolver_audit_prefilled"):
        _schema_only_correction_validator(payload_audit, target)
