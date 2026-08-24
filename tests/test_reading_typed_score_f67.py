"""F-67 locks: support ambiguity is per observation, never per component."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.tool_scripts import run_stage
from scripts.tool_scripts.build_score_view_bindings import build as build_score_view_bindings
from src.agent.execution.manifest import RunManifest
from src.agent.judge.score_schema import load_score_gt_identity
from tests.test_reading_typed_scoring_slice0 import _grade_payload, _real_payload


REPO = Path(__file__).resolve().parents[1]
SM25_RUN = (
    REPO
    / "case_tests/e2e_tests/sm25-L_anchor"
    / "run_2026-08-21_c2_first_sonnet_T1"
)
SM25_OUTPUT = SM25_RUN / "0_reading/attempts/001/output.json"
SM25_OUTPUT_SHA256 = (
    "6b4aa33c2c01b838eaef027e016cbb7688399a118b7658ffe3a3b45fa3bc1f94"
)
SM25_GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json"
SM24_PRE_F67_SCORE_SHA256 = (
    "9e121932806c4f1582408975f166346eebe029baf1ed59ec9e9fc21a99eee7cc"
)


def _grade_sm25_output(output_payload: dict, tmp_path_factory, name: str) -> dict:
    """Grade an sm25 ``0_reading`` product against the CURRENT gt, without ever
    writing into the checked-in historical run directory.

    F-93 1-b (2026-08-25): T1's own frozen ``_run/judge_score_bindings.json``
    was hand-frozen against the gt that predates its 08-23 re-sign
    (``gt_content_sha256=f97cea65…`` vs the current ``135b282c…``), so copying
    it verbatim trips ``score_view_binding_invalid``. This derives the binding
    live through the real generator (``build_score_view_bindings.build``, the
    same entry point F-93 1-a's lock covers) against the CURRENT gt, using
    T1's own ``view_manifest.json`` (confirmed byte-identical to the 08-25
    rescore run's — same case, same required views) — everything still lands
    in ``tmp_path``, never back into the checked-in run.
    """
    run = tmp_path_factory.mktemp(name) / "run"
    attempt = run / "0_reading/attempts/001"
    attempt.mkdir(parents=True)
    metadata = run / "_run"
    metadata.mkdir()
    for filename in ("view_manifest.json", "reading_exam_scope.json"):
        shutil.copyfile(SM25_RUN / "_run" / filename, metadata / filename)
    fresh_bindings = build_score_view_bindings(SM25_RUN, SM25_GT, None)
    (metadata / "judge_score_bindings.json").write_text(
        json.dumps(fresh_bindings.model_dump(mode="json"), sort_keys=True),
        encoding="utf-8",
    )
    shutil.copyfile(SM25_RUN / "run_config.yaml", run / "run_config.yaml")
    (attempt / "output.json").write_text(
        json.dumps(output_payload, sort_keys=True), encoding="utf-8"
    )

    _identity, document = load_score_gt_identity(SM25_GT)
    assert document is not None
    artifacts = run_stage._grade_typed_attempt_artifacts(
        "0_reading",
        document.case,
        attempt,
        document,
        gt_file=SM25_GT,
        manifest=RunManifest(case=document.case),
        grade=run_stage.GradeConfig(),
        run_profile="exploratory",
    )
    return json.loads(Path(artifacts["score_vs_gt"]).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sm25_f67_sidecar(tmp_path_factory) -> dict:
    """Grade the signed real product without mutating its historical run."""
    assert hashlib.sha256(SM25_OUTPUT.read_bytes()).hexdigest() == (
        SM25_OUTPUT_SHA256
    )
    real_payload = json.loads(SM25_OUTPUT.read_text(encoding="utf-8"))
    return _grade_sm25_output(real_payload, tmp_path_factory, "sm25_f67")


def _source_components(sidecar: dict) -> list[dict]:
    return sidecar["certificates"]["source_applicability"][
        "component_applicability"
    ]


def _ambiguities(sidecar: dict) -> list[dict]:
    return sidecar["certificates"]["source_applicability"][
        "ambiguity_witnesses"
    ]


def test_f67_real_sm25_isolates_two_observations_and_measures_the_remainder(
    sm25_f67_sidecar, tmp_path_factory,
):
    """Real premise, re-measured 2026-08-25 (F-93 1-b): one opening and TWO
    wall strokes are support-ambiguous against the CURRENT gt.

    This was "one opening and one wall stroke" when written 2026-08-22
    against the gt that predated the 08-23 re-sign (`e982eba`). Re-anchoring
    the fixture's binding to the current gt (see ``_grade_sm25_output``) does
    not merely fix an identity-hash mismatch: the gt's own float-precision
    cleanup (S1; e.g. a boundary vertex moved from 5.9999999999999964 to
    6.0 — same real-world point, cleaner float) tips one more plan segment
    into a genuine tie between the exterior boundary and a nearby interior
    partition ~0.12 m away (well inside ``plan_position_tol_m=0.30`` — the
    known axis-vs-exterior half-wall-thickness ambiguity for this project).
    Verified this delta is 100% attributable to the gt content (not to this
    fixture's own rework): rebuilding T1's binding fresh against the OLD gt
    (checked out from `f2d359e`, the commit before the resign) reproduces
    exactly the historical 2-ambiguity count byte-for-byte.
    """
    sidecar = sm25_f67_sidecar
    components = {
        (item["source_input_id"], item["component"]): item
        for item in _source_components(sidecar)
    }
    assert components[("1f_view", "plan_openings")]["status"] == "applicable"
    assert components[("1f_view", "plan_segments")]["status"] == "applicable"
    ambiguities = [
        item for item in _ambiguities(sidecar)
        if item["reason"] == "multiple_support_lines"
    ]
    assert [(item["component"], len(item["observation_ids"])) for item in ambiguities] == [
        ("plan_openings", 1),
        ("plan_segments", 1),
        ("plan_segments", 1),
    ]
    assert all(len(item["candidate_target_ids"]) == 2 for item in ambiguities)
    assert sidecar["payload"]["unmeasurable_observations"] == 3

    statuses = {item["status"] for item in sidecar["payload"]["segment_rows"]}
    assert "complete" in statuses and "miss" in statuses

    # Product ambiguity never changes the GT-derived denominator: re-anchored
    # 2026-08-25 to a self-contained same-gt comparison (grading the SAME
    # product with every 1f_view stroke stripped out) instead of diffing
    # against the historical run's OWN score_vs_gt.json — that file was
    # scored under the OLD gt, so after the resign it is no longer a
    # same-gt reference and the comparison would conflate "gt changed" with
    # "product ambiguity changed the denominator" (exactly what this
    # assertion exists to rule out).
    stripped_payload = copy.deepcopy(
        json.loads(SM25_OUTPUT.read_text(encoding="utf-8"))
    )
    stripped_payload["views"]["1f_view"]["strokes"] = []
    stripped_sidecar = _grade_sm25_output(
        stripped_payload, tmp_path_factory, "sm25_f67_denominator_control"
    )
    current_applicability = sidecar["certificates"]["source_applicability"]
    stripped_applicability = stripped_sidecar["certificates"]["source_applicability"]
    assert current_applicability["denominator_atoms"] == stripped_applicability[
        "denominator_atoms"
    ]
    assert current_applicability["denominator_sha256"] == stripped_applicability[
        "denominator_sha256"
    ]


def test_f67_ambiguous_observations_cannot_enter_any_passing_numerator(
    sm25_f67_sidecar,
):
    """Must-red if a sorted-first repair lets either ambiguous observation score."""
    sidecar = sm25_f67_sidecar
    ambiguous_ids = {
        observation_id
        for item in _ambiguities(sidecar)
        if item["reason"] == "multiple_support_lines"
        for observation_id in item["observation_ids"]
    }
    assert len(ambiguous_ids) == 3  # re-measured 2026-08-25, see F-93 1-b above
    passing_opening_ids = {
        observation_id
        for row in sidecar["payload"]["opening_source_rows"]
        if row["result"] in {"complete", "within_tolerance"}
        for observation_id in row["matched_observation_ids"]
    }
    passing_segment_ids = {
        row["observation_id"]
        for row in sidecar["payload"]["segment_rows"]
        if row["status"] in {"complete", "within_tolerance"}
        and row["observation_id"] is not None
    }
    assert passing_opening_ids and passing_segment_ids
    assert ambiguous_ids.isdisjoint(passing_opening_ids | passing_segment_ids)


def test_f67_filtered_unread_inputs_do_not_degrade_channel_status(
    sm25_f67_sidecar,
):
    """Must-red if 2F/facade filter rows re-enter channel aggregation."""
    sidecar = sm25_f67_sidecar
    filtered = [
        item for item in _source_components(sidecar)
        if item["denominator_disposition"] == "filter"
    ]
    assert filtered
    assert any(item["source_input_id"] == "2f_view" for item in filtered)
    channels = {
        item["channel"]: item
        for item in sidecar["payload"]["channel_applicability"]
    }
    assert channels["plan"]["status"] == "applicable"
    assert channels["plan"]["source_input_ids"] == ["1f_view"]
    assert channels["elevation"]["status"] == "not_applicable"
    assert channels["elevation"]["source_input_ids"] == []


def test_f67_sm24_score_sidecar_is_field_stable(tmp_path):
    """No ambiguity in sm24: the canonical full-sidecar hash cannot move."""
    sidecar, _artifacts = _grade_payload(
        tmp_path,
        _real_payload(),
        name="sm24_f67_field_lock",
    )
    assert sidecar["content_sha256"] == SM24_PRE_F67_SCORE_SHA256
