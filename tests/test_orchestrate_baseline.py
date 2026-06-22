"""Tests for the dev-baseline orchestration helpers + record_baseline tool."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

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

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")
_RUN_NAME = "run_2026-06-15_baseline"


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
    b = record_baseline.record_baseline(run, date="2026-06-16", orchestrator="test")
    assert b["blocked"] is False
    assert b["case"] == "sm20_anchor" and b["run"] == _RUN_NAME
    assert b["geometry"] == {"zones": 19, "surfaces": 135, "windows": 16}
    assert b["geometry_digest"] is not None
    # files written into the run dir
    bj = json.loads((run / "baseline.json").read_text())
    assert bj["case"] == "sm20_anchor"
    report = (run / "RUN_REPORT.md").read_text()
    assert "肉视检验" in report
    assert "结论" in report
    # gate① per-stage checks also written by validate_case(write_reports=True)
    assert (run / "1_correction" / "correction_checks.json").exists()


def test_record_baseline_report_lists_eyeball_items(tmp_path):
    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    record_baseline.record_baseline(case / _RUN_NAME, date="2026-06-16", orchestrator="test")
    report = (case / _RUN_NAME / "RUN_REPORT.md").read_text()
    assert "填色区图" in report and "立面窗位图" in report and "3D 几何" in report


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
    report = (run / "RUN_REPORT.md").read_text()
    assert "## 校正审计（看错↔改错归因）" in report
    assert "（无 corrections.json）" in report


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
    report = (run / "RUN_REPORT.md").read_text()
    assert "## 校正审计（看错↔改错归因）" in report
    assert "### conflicts[]" in report
    assert "### unsupported[]" in report
    assert "### corrections[]（显示 20/25，cap=20）" in report
    assert "audit-derived [corrections_summary]" in report


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
    report = (run / "RUN_REPORT.md").read_text()
    assert "读取状态: malformed_json" in report


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
