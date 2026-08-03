"""Slice 0 RED locks for aggregate ReadingView typed scoring."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_RUN = (
    REPO_ROOT
    / "case_tests/e2e_tests/sm24_anchor"
    / "run_2026-07-27_haiku_e2e"
)
REAL_OUTPUT = REAL_RUN / "0_reading/attempts/003/output.json"
GT_FILE = REPO_ROOT / "case_tests/test_baseline/gt/sm24_anchor/gt.json"
PUBLIC_ROWS_SHA256 = (
    "ee2a4d0d3de034417acd76420a9222899d2585d23bbff6f390ebe0ce09b6635b"
)
WALL_CRITERIA_SHA256 = (
    "65cf6dfb5136df7195b8cfb7811f7a7f666c90084e8743dc3bcbbf68f9a17025"
)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _real_payload() -> dict:
    """The unmodified historical artifact is valid under the fixed-v2 frame."""
    return json.loads(REAL_OUTPUT.read_text(encoding="utf-8"))


def _grade_payload(
    tmp_path: Path,
    payload: object,
    *,
    name: str,
    run_profile: str = "exploratory",
) -> tuple[dict, dict]:
    from scripts.tool_scripts import run_stage
    from src.agent.execution.manifest import RunManifest
    from src.agent.judge.score_schema import load_score_gt_identity

    run = tmp_path / name
    attempt = run / "0_reading/attempts/003"
    attempt.mkdir(parents=True)
    meta = run / "_run"
    meta.mkdir()
    for filename in ("view_manifest.json", "judge_score_bindings.json"):
        shutil.copyfile(REAL_RUN / "_run" / filename, meta / filename)
    (attempt / "output.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )
    _identity, document = load_score_gt_identity(GT_FILE)
    assert document is not None
    artifacts = run_stage._grade_typed_attempt_artifacts(
        "0_reading",
        document.case,
        attempt,
        document,
        gt_file=GT_FILE,
        manifest=RunManifest(case=document.case),
        grade=run_stage.GradeConfig(),
        run_profile=run_profile,
    )
    assert artifacts["score_vs_gt"] is not None
    assert artifacts["grade"] is not None
    sidecar = json.loads(
        Path(artifacts["score_vs_gt"]).read_text(encoding="utf-8")
    )
    return sidecar, artifacts


def _denominator_wire(sidecar: dict) -> tuple[bytes, bytes, str, str]:
    certificate = sidecar["certificates"]["source_applicability"]
    return (
        _canonical_bytes(certificate["denominator_basis"]),
        _canonical_bytes(certificate["denominator_atoms"]),
        certificate["denominator_basis_sha256"],
        certificate["denominator_sha256"],
    )


def _reading_grade_status_lines(payload: dict) -> tuple[str, ...]:
    tool_scripts = str(REPO_ROOT / "scripts/tool_scripts")
    if tool_scripts not in sys.path:
        sys.path.insert(0, tool_scripts)
    import render_grade

    return render_grade.reading_grade_status_lines(payload)


def test_real_views_attempt_reaches_typed_total_service(tmp_path):
    """A real views envelope is the product fixture; GT never supplies its coordinates."""
    sidecar, artifacts = _grade_payload(tmp_path, _real_payload(), name="real")

    assert sidecar["schema_version"] == "9"
    assert sidecar["payload"]["kind"] in {"c2_scored", "not_applicable"}
    assert sidecar["identity"]["product"]["output_schema"] == "reading_views_v2"
    assert Path(artifacts["grade"]).read_bytes().startswith(b"\x89PNG")


def test_reading_contract_is_not_inferred_from_missing_schema(tmp_path):
    from src.agent.judge.reading_typed_adapter import identify_reading_contract

    assert identify_reading_contract({}).contract_id == "unrecognized"
    assert identify_reading_contract({"views": []}).contract_id == "unrecognized"
    assert identify_reading_contract(
        {
            "schema_version": "3",
            "segments": [],
            "openings": [],
            "elevation_observations": [],
        }
    ).contract_id == "unrecognized"
    assert identify_reading_contract({"views": {}}).contract_id == "reading_views_v2"
    assert (
        identify_reading_contract(_real_payload()).contract_id
        == "reading_views_v2"
    )

    sidecar, _artifacts = _grade_payload(
        tmp_path, _real_payload(), name="identity"
    )
    assert sidecar["identity"]["product"]["output_schema"] == "reading_views_v2"


def test_product_geometry_bytes_cannot_change_denominator(tmp_path):
    from src.agent.judge.reading_typed_adapter import (
        derive_reading_denominator_v1,
    )

    assert tuple(inspect.signature(derive_reading_denominator_v1).parameters) == (
        "gt",
        "base_manifest",
        "bindings",
        "trusted_capability_dispositions",
    )

    normal = _real_payload()
    malformed = copy.deepcopy(normal)
    for view in malformed["views"].values():
        for stroke in view.get("strokes", []):
            stroke["geometry"] = {}

    normal_sidecar, _ = _grade_payload(tmp_path, normal, name="normal")
    malformed_sidecar, _ = _grade_payload(
        tmp_path, malformed, name="all_malformed"
    )

    assert _canonical_bytes(normal) != _canonical_bytes(malformed)
    assert _denominator_wire(normal_sidecar) == _denominator_wire(
        malformed_sidecar
    )
    assert (
        normal_sidecar["certificates"]["reading_normalization"]["content_sha256"]
        != malformed_sidecar["certificates"]["reading_normalization"][
            "content_sha256"
        ]
    )
    assert (
        malformed_sidecar["payload"]["unmeasurable_observations"]
        > normal_sidecar["payload"]["unmeasurable_observations"]
    )
    assert normal_sidecar["payload"]["visibility_counts"]["elevation_local_x_sense_disagreements"] == 0
    assert malformed_sidecar["payload"]["visibility_counts"]["elevation_local_x_sense_disagreements"] == 0


def test_rect_wall_is_per_stroke_unmeasurable_and_counted(tmp_path):
    normal = _real_payload()
    with_rect = copy.deepcopy(normal)
    plan = with_rect["views"]["1f_view"]
    wall = next(
        stroke
        for stroke in plan["strokes"]
        if stroke["pen"] == "wall" and stroke["geometry"]["kind"] == "line"
    )
    p1, p2 = wall["geometry"]["p1"], wall["geometry"]["p2"]
    wall["geometry"] = {
        "kind": "rect",
        "x_range_m": sorted((p1[0], p2[0])),
        "y_range_m": sorted((p1[1], p2[1])),
    }

    normal_sidecar, _ = _grade_payload(tmp_path, normal, name="rect_normal")
    rect_sidecar, artifacts = _grade_payload(
        tmp_path, with_rect, name="one_rect"
    )
    certificate = rect_sidecar["certificates"]["reading_normalization"]
    witnesses = [
        item
        for item in certificate["unmeasurable_observation_witnesses"]
        if item["reason"] == "plan_wall_rect_has_no_centerline_contract"
    ]
    plan_component = next(
        item
        for item in certificate["component_applicability"]
        if item["source_input_id"] == "1f_view"
        and item["component"] == "plan_segments"
    )

    assert plan_component["status"] == "applicable"
    assert plan_component["denominator_disposition"] == "score"
    assert len(witnesses) == 1
    assert witnesses[0]["source_stroke_id"] == wall["id"]
    assert rect_sidecar["payload"]["unmeasurable_observations"] == 1
    assert _denominator_wire(normal_sidecar) == _denominator_wire(rect_sidecar)
    assert "Unmeasurable observations: 1" in _reading_grade_status_lines(
        rect_sidecar["payload"]
    )
    assert Path(artifacts["grade"]).read_bytes().startswith(b"\x89PNG")


def _score_rows(sidecar: dict) -> tuple[object, ...]:
    payload = sidecar["payload"]
    opening_fields = (
        "target_id", "target_kind", "claim", "source_input_id", "channel",
        "eligible_units", "result", "na_reason", "expected_intervals",
        "observed_interval", "expected_scalar", "observed_scalar",
        "error_metric", "error_value", "tolerance",
    )
    claim_fields = (
        "target_id", "target_kind", "claim", "eligible_units", "result",
        "na_reason", "outcome_slices",
    )
    criterion_fields = (
        "criterion_id", "eligible", "denominator_units", "passing_units",
        "failing_units", "na_reasons", "verdict",
    )
    return (
        payload["kind"],
        tuple(
            tuple(row[field] for field in opening_fields)
            for row in payload.get("opening_source_rows", ())
        ),
        tuple(
            tuple(row[field] for field in claim_fields)
            for row in payload.get("claim_rows", ())
        ),
        tuple(
            tuple(row[field] for field in criterion_fields)
            for row in payload.get("score_criteria", ())
        ),
    )


def _opening_row_signature(row: dict) -> tuple[object, ...]:
    return tuple(
        row[field]
        for field in (
            "target_id", "target_kind", "claim", "source_input_id", "channel",
            "eligible_units", "result", "na_reason", "expected_intervals",
            "observed_interval", "expected_scalar", "observed_scalar",
            "error_metric", "error_value", "tolerance",
        )
    )


def test_l02_local_x_declaration_is_never_a_score_input(tmp_path):
    """L-02/N-5: RTL, arbitrary and missing declarations score identically."""
    baseline, _ = _grade_payload(tmp_path, _real_payload(), name="local_x_base")
    variants: dict[str, dict] = {}
    for label, value in (("ltr", "image_left_to_right"), ("rtl", "image_right_to_left"), ("other", "audit-only"), ("missing", None)):
        payload = _real_payload()
        for view in payload["views"].values():
            if view.get("image_kind") != "elevation":
                continue
            facade = view["facade"]
            if value is None:
                facade.pop("local_x_positive", None)
            else:
                facade["local_x_positive"] = value
        variants[label], _ = _grade_payload(tmp_path, payload, name=f"local_x_{label}")

    for sidecar in variants.values():
        assert sidecar["payload"]["kind"] == "c2_scored"
        assert _denominator_wire(sidecar) == _denominator_wire(baseline)
        assert _score_rows(sidecar) == _score_rows(baseline)

    target_key = ("op_ae1", "existence", "North_view")
    baseline_target = next(
        row for row in baseline["payload"]["opening_source_rows"]
        if (row["target_id"], row["claim"], row["source_input_id"]) == target_key
    )
    assert baseline_target["result"] == "complete"
    for sidecar in variants.values():
        target = next(
            row for row in sidecar["payload"]["opening_source_rows"]
            if (row["target_id"], row["claim"], row["source_input_id"]) == target_key
        )
        assert _opening_row_signature(target) == _opening_row_signature(baseline_target)


def test_l01_mirrored_declaration_is_never_a_score_input(tmp_path):
    """L-01: honest mirror declaration changes cannot alter judged geometry."""
    baseline, _ = _grade_payload(tmp_path, _real_payload(), name="mirror_base")
    for label, value in (("unknown", "unknown"), ("true", "true"), ("false", "false"), ("missing", None)):
        payload = _real_payload()
        for view in payload["views"].values():
            if view.get("image_kind") != "elevation":
                continue
            facade = view["facade"]
            if value is None:
                facade.pop("mirrored", None)
            else:
                facade["mirrored"] = value
        sidecar, _ = _grade_payload(tmp_path, payload, name=f"mirror_{label}")
        assert sidecar["payload"]["kind"] == "c2_scored"
        assert _denominator_wire(sidecar) == _denominator_wire(baseline)
        assert _score_rows(sidecar) == _score_rows(baseline)


def test_l05_historical_wrong_local_x_cannot_decide_score(tmp_path):
    """L-05: the former local-x early return cannot manufacture a miss."""
    sidecar, _ = _grade_payload(tmp_path, _real_payload(), name="historical_rtl")
    assert sidecar["payload"]["kind"] == "c2_scored"
    assert sidecar["certificates"]["reading_normalization"][
        "elevation_frame_disagreements"
    ] == []
    assert sidecar["payload"]["visibility_counts"][
        "elevation_local_x_sense_disagreements"
    ] == 0
    target = next(
        row
        for row in sidecar["payload"]["opening_source_rows"]
        if (
            row["target_id"],
            row["claim"],
            row["source_input_id"],
        ) == ("op_ae1", "existence", "North_view")
    )
    assert target["result"] == "complete"
    assert target["eligible_units"] == 1.0
    assert target["na_reason"] is None


def test_l04_deleting_a_scored_window_flips_only_its_target_to_miss(tmp_path):
    """L-04: fixed-frame scoring distinguishes a real good answer from a miss."""
    good_payload = _real_payload()
    good, _ = _grade_payload(tmp_path, good_payload, name="g1_good")
    target_key = ("op_ae1", "existence", "North_view")
    target = next(
        row for row in good["payload"]["opening_source_rows"]
        if (row["target_id"], row["claim"], row["source_input_id"]) == target_key
    )
    assert target["result"] == "complete"
    observation_id = target["matched_observation_ids"][0]
    observation = next(
        item
        for item in good["certificates"]["reading_normalization"]["observations"]
        if item["observation_id"] == observation_id
    )
    bad_payload = copy.deepcopy(good_payload)
    raw_strokes = bad_payload["views"][observation["source_input_id"]]["strokes"]
    bad_payload["views"][observation["source_input_id"]]["strokes"] = [
        stroke for stroke in raw_strokes if stroke["id"] != observation["source_stroke_id"]
    ]
    bad, _ = _grade_payload(tmp_path, bad_payload, name="g1_window_deleted")
    assert bad["payload"]["kind"] == "c2_scored"
    bad_target = next(
        row for row in bad["payload"]["opening_source_rows"]
        if (row["target_id"], row["claim"], row["source_input_id"]) == target_key
    )
    assert bad_target["result"] == "miss"
    assert bad_target["eligible_units"] == 1.0
    assert bad_target["na_reason"] is None
    assert _denominator_wire(bad) == _denominator_wire(good)
    untouched_good = {
        (row["target_id"], row["claim"], row["source_input_id"]): _opening_row_signature(row)
        for row in good["payload"]["opening_source_rows"]
        if row["target_id"] != target_key[0]
    }
    untouched_bad = {
        (row["target_id"], row["claim"], row["source_input_id"]): _opening_row_signature(row)
        for row in bad["payload"]["opening_source_rows"]
        if row["target_id"] != target_key[0]
    }
    assert untouched_bad == untouched_good


def test_l06_reading_adapter_version_invalidates_cached_score(tmp_path):
    """L-06: the same product/exam cannot reuse a v1-adapter cache entry."""
    from src.agent.judge.score_schema import ScoreSidecarV9, load_cached_score

    _sidecar, artifacts = _grade_payload(tmp_path, _real_payload(), name="cache")
    score_path = Path(artifacts["score_vs_gt"])
    grade_path = Path(artifacts["grade"])
    sidecar = ScoreSidecarV9.model_validate_json(score_path.read_text(encoding="utf-8"))
    assert sidecar.payload.kind == "c2_scored"
    cache_row = next(
        row
        for row in sidecar.payload.opening_source_rows
        if (
            row.target_id,
            row.claim,
            row.source_input_id,
        ) == ("op_ae1", "existence", "North_view")
    )
    assert cache_row.result == "complete"
    assert sidecar.identity.helpers.reading_adapter == "reading_typed_adapter_v2"
    assert load_cached_score(score_path, grade_path=grade_path, expected_identity=sidecar.identity) == sidecar
    v1_identity = sidecar.identity.model_copy(
        update={
            "helpers": sidecar.identity.helpers.model_copy(
                update={"reading_adapter": "reading_typed_adapter_v1"}
            )
        }
    )
    assert v1_identity != sidecar.identity
    assert load_cached_score(score_path, grade_path=grade_path, expected_identity=v1_identity) is None


def test_correction_public_judgment_sha_matches_pre_v9_baseline(tmp_path):
    from scripts.tool_scripts import run_stage
    from tests.test_c2_b4b_phase_d import _correction_v3_runstage_fixture

    gt, run, manifest, gt_file = _correction_v3_runstage_fixture(tmp_path)
    accepted = manifest.accepted("1_correction")
    attempt = (
        run
        / "1_correction/attempts"
        / f"{accepted.accepted_attempt:03d}"
    )
    artifacts = run_stage._grade_typed_attempt_artifacts(
        "1_correction",
        gt.case,
        attempt,
        gt,
        gt_file=gt_file,
        manifest=manifest,
        grade=run_stage.GradeConfig(),
    )
    sidecar = json.loads(
        Path(artifacts["score_vs_gt"]).read_text(encoding="utf-8")
    )
    payload = sidecar["payload"]
    public_rows = {
        key: payload[key]
        for key in (
            "segment_rows",
            "segment_extras",
            "claim_rows",
            "claim_summaries",
            "extras",
        )
    }
    wall_ids = {
        "walls_complete",
        "boundary_complete",
        "no_extra_walls",
        "no_duplicate_wall_strokes",
    }
    wall_criteria = [
        item
        for item in payload["score_criteria"]
        if item["criterion_id"] in wall_ids
    ]
    public_sha = hashlib.sha256(_canonical_bytes(public_rows)).hexdigest()
    wall_sha = hashlib.sha256(_canonical_bytes(wall_criteria)).hexdigest()
    blocking_change = (
        public_sha != PUBLIC_ROWS_SHA256
        or wall_sha != WALL_CRITERIA_SHA256
    )
    print(f"public_rows.before_sha256={PUBLIC_ROWS_SHA256}")
    print(f"public_rows.after_sha256={public_sha}")
    print(f"wall_criteria.before_sha256={WALL_CRITERIA_SHA256}")
    print(f"wall_criteria.after_sha256={wall_sha}")
    print(f"blocking_change={str(blocking_change).lower()}")

    assert public_sha == PUBLIC_ROWS_SHA256
    assert wall_sha == WALL_CRITERIA_SHA256
    assert blocking_change is False
    assert sidecar["schema_version"] == "9"
