"""Tests for the dev-baseline orchestration helpers + record_baseline tool."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from src.agent.execution import (
    RunManifest,
    StageRunner,
    file_stage_attempt,
    summarize_gates,
)
from src.agent.judge import StageVerdict
from src.validator.checks.schema import CheckLayer, CheckReport

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import record_baseline  # noqa: E402
import report_assembly  # noqa: E402

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")
_RUN_NAME = "run_2026-06-15_baseline"
_SM21 = Path("case_tests/e2e_tests/sm21_anchor")
_GPT54_RUN = "run_2026-06-20_gpt54_reading"
_SONNET_RUN = "run_2026-06-20_sonnet_reading"


def _minimal_run(tmp_path: Path) -> Path:
    run = tmp_path / "synthetic_case" / "run_audit"
    run.mkdir(parents=True)
    return run


def _mixed_audit_payload() -> dict:
    corrections = [
        {
            "id": "corr_a1",
            "stage": "A1",
            "rule_id": "A1_local_to_world",
            "target": "global_world_frame",
            "source_ids": ["1f_view", "South_view"],
            "original_value": "local coordinates",
            "resolved_value": "world coordinates",
            "delta": "(-0.24,-0.24)m",
            "changes_topology": False,
            "method_profile": "room_identity",
        },
        {
            "stage": "core",
            "rule_id": "deterministic_core.snap",
            "target": "x.axis[4.9100]",
            "axis": "x",
            "original_value": 4.91,
            "resolved_value": 4.9,
            "delta": -0.01,
            "tolerance_name": "SNAP_GRID",
        },
    ]
    corrections.extend(
        {"id": f"bulk_{i}", "stage": "A2", "rule_id": "bulk_rule", "target": f"axis_{i}"}
        for i in range(23)
    )
    return {
        "corrections": corrections,
        "conflicts": [
            {
                "id": "conf_1",
                "stage": "A3",
                "conflict_type": "stroke_vs_dimension",
                "candidates": [
                    {"value": 4.9, "source_ids": ["S7"]},
                    {"value": 4.94, "source_ids": ["D4", "D5"]},
                ],
                "reason_unresolved": "dimension and stroke disagree",
                "fallback_action": "used dimension chain",
            }
        ],
        "unsupported": [
            {
                "id": "unsup_1",
                "reason": "door found in elevation; doors are not modeled here",
                "regime_assumption_violated": "windows only",
            }
        ],
    }


# --------------------------------------------------------------------------- #
# orchestrate
# --------------------------------------------------------------------------- #
def test_file_stage_attempt_writes_output_checks_judge(tmp_path):
    manifest = RunManifest(case="t")
    runner = StageRunner(tmp_path, manifest)
    rep = CheckReport(stage="1_correction")
    rep.add_pass("x", CheckLayer.INVARIANT)
    verdict = StageVerdict(
        stage="1_correction", rubric_id="J1",
        criteria=[{"criterion": "redraw", "status": "pass"}],
    )
    rec = file_stage_attempt(
        runner, stage="1_correction", stage_dir=tmp_path / "1_correction",
        output_obj={"v": 1}, report=rep, verdict=verdict,
    )
    adir = Path(rec.attempt_dir)
    assert (adir / "output.json").exists()
    assert (adir / "checks.json").exists()
    assert (adir / "judge.json").exists()
    assert rec.accepted is True  # report passed → accepted
    assert manifest.accepted("1_correction").accepted_attempt == rec.attempt_index


def test_file_stage_attempt_appends_not_overwrites(tmp_path):
    manifest = RunManifest(case="t")
    runner = StageRunner(tmp_path, manifest)
    bad = CheckReport(stage="1_correction")
    bad.add_fail("x", CheckLayer.INVARIANT, "bad")
    r1 = file_stage_attempt(runner, stage="1_correction",
                            stage_dir=tmp_path / "1_correction",
                            output_obj={"v": 1}, report=bad)
    good = CheckReport(stage="1_correction")
    good.add_pass("x", CheckLayer.INVARIANT)
    r2 = file_stage_attempt(runner, stage="1_correction",
                            stage_dir=tmp_path / "1_correction",
                            output_obj={"v": 2}, report=good)
    assert r1.attempt_index == 1 and r2.attempt_index == 2
    assert r1.accepted is False and r2.accepted is True
    # both drafts survive
    assert (tmp_path / "1_correction" / "attempts" / "001" / "output.json").exists()
    assert (tmp_path / "1_correction" / "attempts" / "002" / "output.json").exists()


def test_summarize_gates_rolls_up():
    reading = CheckReport(stage="0_reading")
    reading.add_pass("a", CheckLayer.INVARIANT)
    reading.add_fail("b", CheckLayer.CROSS_CHECK, "soft")  # flag
    kernel = CheckReport(stage="2_modelling")
    kernel.add_fail("c", CheckLayer.INVARIANT, "hard")     # block
    s = summarize_gates({"0_reading::1f_view": reading, "2_modelling": kernel})
    assert s["gates"]["0_reading"]["pass"] == 1
    assert s["gates"]["0_reading"]["flag"] == 1
    assert s["gates"]["2_modelling"]["block"] == 1
    assert len(s["flags"]) == 1 and s["flags"][0]["check"] == "b"
    assert len(s["blocking"]) == 1 and s["blocking"][0]["check"] == "c"


# --------------------------------------------------------------------------- #
# record_baseline on the real anchor
# --------------------------------------------------------------------------- #
def test_record_baseline_on_anchor(tmp_path):
    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    run = case / _RUN_NAME
    (run / "RUN_REPORT.md").unlink(missing_ok=True)
    checks_before = (run / "1_correction" / "correction_checks.json").read_bytes()
    b = record_baseline.record_baseline(run, date="2026-06-16", orchestrator="test")
    assert b["blocked"] is False
    assert b["case"] == "sm20_anchor" and b["run"] == _RUN_NAME
    assert b["geometry"] == {"zones": 19, "surfaces": 135, "windows": 16}
    assert b["geometry_digest"] is not None
    # files written into the run dir
    bj = json.loads((run / "baseline.json").read_text())
    assert bj["case"] == "sm20_anchor"
    assert "evidence_index" in bj
    assert "run_state" not in bj
    facts = (run / "report" / "FACTS.md").read_text()
    report = (run / "report" / "REPORT.md").read_text()
    assert "肉视检验" in facts
    assert "结论" in facts
    assert "## 建议" in report
    assert not (run / "RUN_REPORT.md").exists()
    # record_baseline must not rewrite load-bearing gate artifacts.
    assert (run / "1_correction" / "correction_checks.json").read_bytes() == checks_before
    assert (run / "1_correction" / "correction_checks.json").exists()


def test_record_baseline_report_lists_eyeball_items(tmp_path):
    case = tmp_path / "sm21_anchor"
    shutil.copytree(_SM21, case)
    run = case / _GPT54_RUN
    record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")

    eye = run / "report" / "eyeball"
    assert (eye / "1_correction_zones.png").exists()
    assert (eye / "1_correction_elev.png").exists()
    assert (eye / "0_reading_1f_view_render.png").exists()
    assert (eye / "case_data_1f_view.png").exists()
    facts = (run / "report" / "FACTS.md").read_text()
    report = (run / "report" / "REPORT.md").read_text()
    assert "report/eyeball/1_correction_zones.png" in facts
    assert "[3D geometry viewer](../manual_review/geometry_viewer.html)" in report
    assert (run / "manual_review" / "geometry_viewer.html").exists()


def test_record_baseline_state_aware_report_suppresses_dead_viewer(tmp_path):
    case = tmp_path / "sm21_anchor"
    shutil.copytree(_SM21, case)
    run = case / _SONNET_RUN
    record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")

    report = (run / "report" / "REPORT.md").read_text()
    assert "root_stopped: human_redraw_required@1_correction" in report
    assert "### 连带缺失下游件" in report
    assert "2_modelling/building_geometry.json" in report
    assert "3D geometry viewer unavailable" in report
    assert "../manual_review/geometry_viewer.html" not in report


def test_record_baseline_missing_corrections_sidecar_does_not_change_gates(tmp_path):
    run = _minimal_run(tmp_path)
    b = record_baseline.record_baseline(run, date="2026-06-22", orchestrator="test")

    assert b["corrections_summary"]["present"] is False
    assert b["corrections_summary"]["parse_status"] == "missing"
    assert b["corrections_summary"]["sidecar_path"] == "1_correction/corrections.json"
    assert b["corrections_summary"]["counts"] == {
        "corrections": 0,
        "conflicts": 0,
        "unsupported": 0,
    }
    assert b["flags"] == []
    assert all(agg["flag"] == 0 for agg in b["gates"].values())
    facts = (run / "report" / "FACTS.md").read_text()
    assert "## 校正审计（看错↔改错归因）" in facts
    assert "（无 corrections.json）" in facts


def test_record_baseline_correction_audit_summary_is_separate_from_flags(tmp_path):
    run = _minimal_run(tmp_path)
    before = record_baseline.record_baseline(run, date="2026-06-22", orchestrator="test")
    before_flags = before["flags"]
    before_gates = before["gates"]

    audit = _mixed_audit_payload()
    sidecar = run / "1_correction" / "corrections.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")

    after = record_baseline.record_baseline(run, date="2026-06-22", orchestrator="test")
    summary = after["corrections_summary"]
    assert summary["present"] is True
    assert summary["parse_status"] == "ok"
    assert summary["sidecar_path"] == "1_correction/corrections.json"
    assert summary["counts"] == {"corrections": 25, "conflicts": 1, "unsupported": 1}
    assert summary["by_rule_id"] == {
        "A1_local_to_world": 1,
        "bulk_rule": 23,
        "deterministic_core.snap": 1,
    }
    assert summary["by_stage"]["A1"] == 1
    assert summary["by_stage"]["A2"] == 23
    assert summary["by_stage"]["A3"] == 1
    assert summary["by_stage"]["core"] == 1
    assert summary["corrections"]["total"] == 25
    assert summary["corrections"]["shown"] == 20
    assert summary["corrections"]["cap"] == 20
    assert len(summary["corrections"]["rows"]) == 20
    assert summary["corrections"]["rows"][0] == {
        "id": "corr_a1",
        "rule_id": "A1_local_to_world",
        "target": "global_world_frame",
        "source_ids": ["1f_view", "South_view"],
        "original_value": "local coordinates",
        "resolved_value": "world coordinates",
        "delta": "(-0.24,-0.24)m",
        "changes_topology": False,
    }
    assert summary["conflicts"] == audit["conflicts"]
    assert summary["unsupported"] == audit["unsupported"]

    assert after["flags"] == before_flags
    assert after["gates"] == before_gates
    ids = {entry["id"] for entry in after["evidence_index"]}
    assert "E:corr:corrections:corr_a1" in ids
    assert "E:corr:corrections:r2" in ids
    assert "E:corr:corrections:bulk_22" in ids
    assert "E:corr:conflicts:conf_1" in ids
    assert "E:corr:unsupported:unsup_1" in ids
    assert len([eid for eid in ids if eid.startswith("E:corr:")]) == 27

    facts = (run / "report" / "FACTS.md").read_text()
    assert "## 校正审计（看错↔改错归因）" in facts
    assert "### conflicts[]" in facts
    assert "### unsupported[]" in facts
    assert "### corrections[]（显示 20/25，cap=20）" in facts
    assert "audit-derived [corrections_summary]" in facts
    assert "`E:corr:corrections:bulk_22`" in facts


def test_record_baseline_malformed_corrections_sidecar_is_best_effort(tmp_path):
    run = _minimal_run(tmp_path)
    sidecar = run / "1_correction" / "corrections.json"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("{not-json", encoding="utf-8")

    b = record_baseline.record_baseline(run, date="2026-06-22", orchestrator="test")
    assert b["corrections_summary"]["present"] is True
    assert b["corrections_summary"]["parse_status"] == "malformed_json"
    assert b["corrections_summary"]["counts"] == {
        "corrections": 0,
        "conflicts": 0,
        "unsupported": 0,
    }
    facts = (run / "report" / "FACTS.md").read_text()
    assert "读取状态: malformed_json" in facts


def test_record_baseline_verdict_blocking_is_recoverability_aware():
    j0_recoverable = {
        "stage": "0_reading",
        "rubric_id": "J0",
        "criteria": [
            {
                "criterion": "stroke_vs_dimension",
                "status": "severe",
                "recoverability": "correction_recoverable",
            }
        ],
    }
    assert record_baseline._verdict_blocking(j0_recoverable) is False

    j1_recoverable = {**j0_recoverable, "stage": "1_correction", "rubric_id": "J1"}
    assert record_baseline._verdict_blocking(j1_recoverable) is True

    legacy = {
        "stage": "0_reading",
        "rubric_id": "J0",
        "criteria": [{"criterion": "legacy", "status": "severe"}],
    }
    assert record_baseline._verdict_blocking(legacy) is True


def _ok_stage(stage: str, status: str = "deterministic_pass") -> dict:
    return {
        "stage": stage,
        "status": status,
        "attempts_used": 1,
        "accepted_attempt": 1,
        "message": f"{status}@{stage}",
    }


def _all_stage_state(overrides: dict[str, str] | None = None) -> dict:
    statuses = {
        "0_reading": "judge_pass",
        "1_correction": "judge_pass",
        "2_modelling": "deterministic_pass",
        "3_split_pairing": "deterministic_pass",
        "4_mep": "deterministic_pass",
        "5_intakeoutput": "deterministic_pass",
    }
    statuses.update(overrides or {})
    return {"stages": {stage: _ok_stage(stage, status) for stage, status in statuses.items()}}


def test_run_state_completed_clean_real_geometry_gate_shape():
    state = json.loads((_SM21 / _GPT54_RUN / "orchestration_state.json").read_text())
    derived = report_assembly.derive_run_state(state, geometry_approved=True)
    assert derived["status"] == "completed_clean"
    assert derived["completed_clean"] is True
    assert derived["pending"] is None
    assert derived["ignored_pending"][0]["stage"] == "3_split_pairing"


@pytest.mark.parametrize(
    ("stage", "status"),
    [
        ("0_reading", "awaiting_judge"),
        ("1_correction", "judge_block"),
        ("0_reading", "awaiting_reread"),
        ("3_split_pairing", "awaiting_geometry_approval"),
    ],
)
def test_run_state_pending_cases(stage, status):
    derived = report_assembly.derive_run_state(
        _all_stage_state({stage: status}), geometry_approved=False)
    assert derived["status"] == "pending"
    assert derived["completed_clean"] is False
    assert derived["pending"]["stage"] == stage
    assert derived["pending"]["status"] == status


def test_run_state_non_human_terminal_precedes_pending():
    derived = report_assembly.derive_run_state(
        _all_stage_state({
            "4_mep": "quarantined",
            "5_intakeoutput": "awaiting_judge",
        }),
        geometry_approved=False,
    )
    assert derived["status"] == "root_stopped"
    assert derived["root_stop"]["stage"] == "4_mep"
    assert derived["root_stop"]["status"] == "quarantined"
    assert derived["pending"] is None
    assert derived["pending_candidates"][0]["stage"] == "5_intakeoutput"


def test_evidence_index_duplicate_id_assertion():
    with pytest.raises(AssertionError, match="duplicate evidence ids"):
        report_assembly.assert_unique_evidence_ids([
            {"id": "E:gate:0_reading::1f_view:x"},
            {"id": "E:gate:0_reading::1f_view:x"},
        ])


def _valid_recommendation_report(evidence_id: str) -> str:
    return f"""# report

## 建议

### 机制问题

- action: add a sharper gate
  evidence: [{evidence_id}]
  owner: scaffold

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

> note: context is allowed when explicitly marked.
- action: add a judge checklist item
  evidence: [{evidence_id}]
  owner: scaffold

### 修法

本 run 无可证据支持的建议
"""


def test_citation_linter_passes_structured_recommendations():
    index = [{"id": "E:geom:digest"}]
    assert report_assembly.lint_report_citations(
        _valid_recommendation_report("E:geom:digest"), index) == []


@pytest.mark.parametrize(
    "text",
    [
        _valid_recommendation_report("E:missing"),
        """# report

## 建议

### 机制问题

free prose is not allowed here

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

本 run 无可证据支持的建议

### 修法

本 run 无可证据支持的建议
""",
        """# report

## 建议

### 机制问题

- action: cite nothing
  evidence:
  owner: scaffold

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

本 run 无可证据支持的建议

### 修法

本 run 无可证据支持的建议
""",
    ],
)
def test_citation_linter_fails_bad_recommendations(text):
    errors = report_assembly.lint_report_citations(text, [{"id": "E:geom:digest"}])
    assert errors


def test_record_baseline_preserves_authored_report_unless_forced(tmp_path):
    case = tmp_path / "sm21_anchor"
    shutil.copytree(_SM21, case)
    run = case / _GPT54_RUN
    first = record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")
    evidence_id = first["evidence_index"][0]["id"]
    authored = _valid_recommendation_report(evidence_id).replace(
        "# report", "# authored report\n\nCustom narrative survives.")
    report_path = run / "report" / "REPORT.md"
    report_path.write_text(authored, encoding="utf-8")

    record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")
    assert "Custom narrative survives." in report_path.read_text(encoding="utf-8")

    record_baseline.record_baseline(
        run, date="2026-06-21", orchestrator="test", force_template=True)
    assert "Custom narrative survives." not in report_path.read_text(encoding="utf-8")
