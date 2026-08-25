"""F-103 locks for distinguishable not-applicable causes in official flow."""

from __future__ import annotations

import json
from pathlib import Path


def test_official_flow_distinguishes_all_product_or_capability_na_codes(
    tmp_path, monkeypatch
):
    from scripts.tool_scripts import run_stage
    from src.agent.judge.score_schema import ScoreContractError
    import src.agent.judge.score_service as score_service
    from tests.test_c2_b4b_phase_d import _correction_v3_runstage_fixture

    causes = (
        ("score_product_segment_unresolved", "scoring.matching"),
        ("score_match_ambiguous", "scoring.matching"),
        ("score_unsupported_combination", "scoring.capability"),
    )
    observed: list[str | None] = []

    for index, (code, gate_id) in enumerate(causes):
        fixture_root = tmp_path / f"cause_{index}"
        fixture_root.mkdir()
        gt, run, manifest, gt_file = _correction_v3_runstage_fixture(
            fixture_root
        )
        accepted = manifest.accepted("1_correction")
        assert accepted is not None
        attempt = (
            run
            / "1_correction/attempts"
            / f"{accepted.accepted_attempt:03d}"
        )

        def raise_cause(*, _code=code, _gate_id=gate_id, **_kwargs):
            raise ScoreContractError(_code, _gate_id)

        monkeypatch.setattr(score_service, "score_typed_attempt", raise_cause)
        artifacts = run_stage._grade_typed_attempt_artifacts(
            "1_correction",
            gt.case,
            attempt,
            gt,
            gt_file=gt_file,
            manifest=manifest,
            grade=run_stage.GradeConfig(),
        )
        payload = json.loads(
            Path(artifacts["score_vs_gt"]).read_text(encoding="utf-8")
        )["payload"]

        assert payload["kind"] == "not_applicable"
        assert payload["reason"] == "unsupported_view_contract"
        assert payload["detail"] == code
        observed.append(artifacts["score_payload_detail"])

    expected = tuple(code for code, _gate_id in causes)
    assert tuple(observed) == expected
    assert len(set(observed)) == 3
