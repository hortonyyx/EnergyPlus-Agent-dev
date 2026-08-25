"""F-102 locks for typed correction score-cache helper identity."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_REAL_R0 = (
    _REPO_ROOT
    / "case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0"
)
_REAL_GT = _REPO_ROOT / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json"
_PRE_F102_HELPER = "reading_opening_global_assignment_v1"


def test_pre_f102_real_sidecar_misses_through_official_flow(
    tmp_path, monkeypatch
):
    """The real pre-fix R0 cache entry must be replaced, not reused.

    This copies the archived run to pytest's temporary directory because the
    official flow writes the refreshed score/grade pair.  The source fixture
    remains byte-for-byte untouched.
    """
    from scripts.tool_scripts import run_stage
    from src.agent.execution.manifest import load_run_manifest
    from src.agent.judge.gt import load_gt_file
    import src.agent.judge.score_schema as score_schema
    from src.agent.judge.score_schema import (
        CORRECTION_OPENING_MATCHER_HELPER_VERSION,
        ScoreSidecarV9,
        canonical_sha256,
    )

    run = tmp_path / "real_r0"
    shutil.copytree(_REAL_R0, run)
    attempt = run / "1_correction/attempts/001"
    score_path = attempt / "score_vs_gt.json"
    before = json.loads(score_path.read_text(encoding="utf-8"))
    assert before["identity"]["helpers"]["opening_matcher"] == _PRE_F102_HELPER
    assert before["payload"]["kind"] == "rejected"
    assert before["payload"]["error_code"] == "score_view_binding_invalid"

    real_load_cached_score = score_schema.load_cached_score
    cache_hits: list[bool] = []

    def observe_cache(path, *, grade_path, expected_identity):
        cached = real_load_cached_score(
            path,
            grade_path=grade_path,
            expected_identity=expected_identity,
        )
        cache_hits.append(cached is not None)
        return cached

    monkeypatch.setattr(score_schema, "load_cached_score", observe_cache)
    document = load_gt_file(_REAL_GT)
    manifest = load_run_manifest(run)
    assert manifest is not None
    artifacts = run_stage._grade_typed_attempt_artifacts(
        "1_correction",
        document.case,
        attempt,
        document,
        gt_file=_REAL_GT,
        manifest=manifest,
        grade=run_stage.GradeConfig(),
    )

    after = json.loads(score_path.read_text(encoding="utf-8"))
    assert cache_hits == [False]
    assert artifacts["score_vs_gt"] == str(score_path)
    assert after["identity"]["helpers"]["opening_matcher"] == (
        CORRECTION_OPENING_MATCHER_HELPER_VERSION
    )
    assert after["payload"] != before["payload"]
    assert not (
        after["payload"]["kind"] == "rejected"
        and after["payload"].get("error_code") == "score_view_binding_invalid"
    )

    # Item 2 changes correction plan-floor normalization after F-102's v2
    # release.  A sidecar produced under that intermediate v2 release must
    # also miss once the correction helper advances to v3.
    pre_item2 = deepcopy(after)
    pre_item2["identity"]["helpers"]["opening_matcher"] = (
        "correction_opening_global_assignment_v2"
    )
    pre_item2["content_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in pre_item2.items()
            if key != "content_sha256"
        }
    )
    score_path.write_text(
        ScoreSidecarV9.model_validate_json(
            json.dumps(pre_item2, separators=(",", ":"))
        ).model_dump_json(),
        encoding="utf-8",
    )
    run_stage._grade_typed_attempt_artifacts(
        "1_correction",
        document.case,
        attempt,
        document,
        gt_file=_REAL_GT,
        manifest=manifest,
        grade=run_stage.GradeConfig(),
    )
    after_item2 = json.loads(score_path.read_text(encoding="utf-8"))
    assert cache_hits == [False, False]
    assert after_item2["identity"]["helpers"]["opening_matcher"] == (
        CORRECTION_OPENING_MATCHER_HELPER_VERSION
    )
