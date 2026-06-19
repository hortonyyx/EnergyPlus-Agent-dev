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
