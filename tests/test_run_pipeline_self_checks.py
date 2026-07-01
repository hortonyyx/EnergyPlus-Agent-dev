from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import src.agent.pipeline as pipeline
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.validation_run import validate_case
from src.agent.intakeoutput import MepOutput
from src.agent.state import IntakeOutput
from src.validator.checks.schema import CheckReport


_SITE = {
    "latitude": 22.5,
    "longitude": 114.0,
    "time_zone": 8.0,
    "elevation": 5.0,
}


def _write_reading(vector_dir: Path, payload: dict | None = None) -> None:
    vector_dir.mkdir(parents=True, exist_ok=True)
    (vector_dir / "reading_summary.md").write_text("summary", encoding="utf-8")
    (vector_dir / "1f_view.json").write_text(
        json.dumps(
            payload
            or {
                "image_kind": "plan",
                "uncaptured": [],
                "strokes": [
                    {
                        "id": "S1",
                        "pen": "wall",
                        "provenance": "seen",
                        "confidence": "high",
                        "geometry": {"kind": "line", "p1": [0, 0], "p2": [2, 0]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _good_geom(*, corrections: list[dict] | None = None) -> CorrectedGeometry:
    return CorrectedGeometry.model_validate(
        {
            "footprint_x": [0.0, 2.0],
            "footprint_y": [0.0, 2.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {
                            "id": "C1",
                            "role": "office",
                            "x": [0.0, 2.0],
                            "y": [0.0, 2.0],
                        }
                    ],
                }
            ],
            "windows": [],
            "conflicts": [],
            "corrections": corrections or [],
            "unsupported": [],
        }
    )


def _zones_from_specs(zone_specs: str) -> list[str]:
    return re.findall(r"^- ([^:]+):", zone_specs, flags=re.MULTILINE)


def _mep_dict(
    zones: list[str],
    used_constructions: set[str],
    *,
    incomplete_schedule: bool = False,
) -> dict:
    occ_days = "Weekdays" if incomplete_schedule else "AllDays"
    people = []
    lights = []
    for zone in zones:
        people.append(
            "People,\n"
            f"  {zone}_People,\n"
            f"  {zone},\n"
            "  Occ,\n"
            "  People,\n"
            "  1,\n"
            "  ,\n"
            "  ,\n"
            "  0.3,\n"
            "  Autocalculate,\n"
            "  Activity;\n"
        )
        lights.append(
            "Lights,\n"
            f"  {zone}_Lights,\n"
            f"  {zone},\n"
            "  Occ,\n"
            "  Watts/Area,\n"
            "  ,\n"
            "  10.0;\n"
        )
    return {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", **_SITE},
        "material_specs": "Material:NoMass,\n  Mat_R,\n  Rough,\n  1.0;\n",
        "construction_specs": "".join(
            f"Construction,\n  {name},\n  Mat_R;\n\n"
            for name in sorted(used_constructions)
        ),
        "schedule_specs": (
            "ScheduleTypeLimits,\n"
            "  Fraction,\n"
            "  0,\n"
            "  1,\n"
            "  Continuous;\n\n"
            "ScheduleTypeLimits,\n"
            "  Any Number,\n"
            "  ,\n"
            "  ,\n"
            "  Continuous;\n\n"
            "Schedule:Compact,\n"
            "  Occ,\n"
            "  Fraction,\n"
            "  Through: 12/31,\n"
            f"  For: {occ_days},\n"
            "  Until: 24:00,1.0;\n\n"
            "Schedule:Compact,\n"
            "  Activity,\n"
            "  Any Number,\n"
            "  Through: 12/31,\n"
            "  For: AllDays,\n"
            "  Until: 24:00,120.0;\n"
        ),
        "hvac_specs": "",
        "people_specs": "\n".join(people),
        "lights_specs": "\n".join(lights),
    }


def _patch_llm_stages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    geom: CorrectedGeometry | None = None,
    bad_mep: bool = False,
) -> Path:
    vector_dir = tmp_path / "0_reading"
    if not (vector_dir / "1f_view.json").exists():
        _write_reading(vector_dir)
    monkeypatch.setattr(
        pipeline, "run_correction", lambda *_args, **_kwargs: geom or _good_geom()
    )

    def fake_run_mep(zone_specs, used_constructions, _testdata_text, *, out_dir, **_kwargs):
        mep = MepOutput.model_validate(
            _mep_dict(
                _zones_from_specs(zone_specs),
                used_constructions,
                incomplete_schedule=bad_mep,
            )
        )
        if out_dir is not None:
            (out_dir / "mep_output.json").write_text(
                mep.model_dump_json(indent=2), encoding="utf-8"
            )
        return mep

    monkeypatch.setattr(pipeline, "run_mep", fake_run_mep)
    return vector_dir


def _report(path: Path) -> CheckReport:
    return CheckReport.model_validate_json(path.read_text(encoding="utf-8"))


def _statuses(report: CheckReport) -> dict[str, str]:
    return {result.check_id: result.status.value for result in report.results}


def test_run_pipeline_inline_correction_mep_smoke_exploratory(tmp_path, monkeypatch):
    vector_dir = _patch_llm_stages(monkeypatch, tmp_path)
    out_dir = tmp_path / "out"

    intake = pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir)

    assert isinstance(intake, IntakeOutput)
    correction = _report(out_dir / "1_correction" / "correction_checks.json")
    mep = _report(out_dir / "4_mep" / "mep_checks.json")
    assert correction.passed, [r.check_id for r in correction.blocking()]
    assert mep.passed, [r.check_id for r in mep.blocking()]


def test_run_pipeline_exploratory_writes_and_warns_but_continues(
    tmp_path, monkeypatch
):
    vector_dir = _patch_llm_stages(monkeypatch, tmp_path, bad_mep=True)
    out_dir = tmp_path / "out"
    testdata = json.dumps({"Floor plans": [{"thermal_zones": 1}], "site_location": _SITE})
    warnings: list[str] = []
    sink = pipeline.logger.add(lambda msg: warnings.append(str(msg)), level="WARNING")
    try:
        intake = pipeline.run_pipeline(
            vector_dir, testdata, out_dir=out_dir, run_profile="exploratory"
        )
    finally:
        pipeline.logger.remove(sink)

    assert isinstance(intake, IntakeOutput)
    correction = _report(out_dir / "1_correction" / "correction_checks.json")
    mep = _report(out_dir / "4_mep" / "mep_checks.json")
    assert "correction.audit_completeness" in {
        result.check_id for result in correction.blocking()
    }
    assert "mep.schedule_completeness" in {result.check_id for result in mep.blocking()}
    assert (out_dir / "5_intakeoutput" / "intake_output.json").exists()
    assert any("1_correction self-check" in msg for msg in warnings)
    assert any("4_mep self-check" in msg for msg in warnings)


def test_run_pipeline_golden_fail_closed_after_writing_correction_report(
    tmp_path, monkeypatch
):
    vector_dir = _patch_llm_stages(monkeypatch, tmp_path, bad_mep=True)
    out_dir = tmp_path / "out"
    testdata = json.dumps({"Floor plans": [{"thermal_zones": 1}], "site_location": _SITE})

    with pytest.raises(RuntimeError, match="run_profile=golden"):
        pipeline.run_pipeline(vector_dir, testdata, out_dir=out_dir, run_profile="golden")

    correction_path = out_dir / "1_correction" / "correction_checks.json"
    assert correction_path.exists()
    assert "correction.audit_completeness" in {
        result.check_id for result in _report(correction_path).blocking()
    }
    assert not (out_dir / "4_mep" / "mep_checks.json").exists()


def test_run_pipeline_inline_reports_match_validate_case(tmp_path, monkeypatch):
    case_dir = tmp_path / "case"
    run_dir = case_dir / "run"
    vector_dir = _patch_llm_stages(
        monkeypatch,
        tmp_path,
        geom=_good_geom(corrections=[{"source": "testdata", "reason": "zone count"}]),
    )
    testdata = {"Floor plans": [{"thermal_zones": 1}], "site_location": _SITE}
    (case_dir / "case_data").mkdir(parents=True)
    (case_dir / "case_data" / "testdata_prompt.json").write_text(
        json.dumps(testdata), encoding="utf-8"
    )

    pipeline.run_pipeline(vector_dir, json.dumps(testdata), out_dir=run_dir)
    inline_correction = _statuses(
        _report(run_dir / "1_correction" / "correction_checks.json")
    )
    inline_mep = _statuses(_report(run_dir / "4_mep" / "mep_checks.json"))

    validate_case(run_dir, case_dir=case_dir, write_reports=True)

    assert inline_correction == _statuses(
        _report(run_dir / "1_correction" / "correction_checks.json")
    )
    assert inline_mep == _statuses(_report(run_dir / "4_mep" / "mep_checks.json"))


def test_run_pipeline_a8_pre_core_coverage_still_enters_correction_report(
    tmp_path, monkeypatch
):
    vector_dir = tmp_path / "0_reading"
    _write_reading(
        vector_dir,
        {
            "image_kind": "plan",
            "uncaptured": [],
            "strokes": [
                {
                    "id": "S1",
                    "pen": "wall",
                    "provenance": "dimension_derived",
                    "dimension_refs": [],
                    "geometry": {"kind": "line", "p1": [0, 0], "p2": [1, 0]},
                }
            ],
            "dimensions": [],
        },
    )
    _patch_llm_stages(monkeypatch, tmp_path)
    out_dir = tmp_path / "out"

    pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir, run_profile="exploratory")

    assert (out_dir / "1_correction" / "evidence_debt_coverage_checks.json").exists()
    correction = _report(out_dir / "1_correction" / "correction_checks.json")
    evidence = next(
        result
        for result in correction.results
        if result.check_id == "correction.evidence_debt_coverage"
    )
    assert evidence.status.value == "fail"
