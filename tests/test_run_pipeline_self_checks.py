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
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus


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
                # a plan must declare its world frame to clear gate① under the
                # acceptance profiles (7.31 plan-frame gate)
                "scale_origin": {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None},
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
        "material_specs": (
            "Material,\n"
            "  Mat_Mass,\n"
            "  MediumRough,\n"
            "  0.1,\n"
            "  1.4,\n"
            "  2200,\n"
            "  880;\n"
        ),
        "construction_specs": "".join(
            f"Construction,\n  {name},\n  Mat_Mass;\n\n"
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
    assembly = _report(out_dir / "5_intakeoutput" / "assembly_checks.json")
    assert correction.passed, [r.check_id for r in correction.blocking()]
    assert mep.passed, [r.check_id for r in mep.blocking()]
    assert assembly.passed, [r.check_id for r in assembly.blocking()]


def _patch_kernel_check_non_pairing_blocker(
    monkeypatch: pytest.MonkeyPatch,
    *,
    check_id: str = "kernel.coverage_completeness",
) -> None:
    import src.validator.checks.kernel as kernel_checks

    def fake_check_kernel(
        _bg,
        *,
        window_host_proof=None,
        capability_profile: str = "rectangular",
        interzone_issues: list[str] | None = None,
        run_profile: str = "exploratory",
    ) -> CheckReport:
        assert window_host_proof is None
        assert not interzone_issues
        rep = CheckReport(
            stage="2_modelling",
            capability_profile=capability_profile,
            run_profile=run_profile,
        )
        rep.add("kernel.pairing_gate", CheckStatus.PASS, CheckLayer.INVARIANT)
        rep.add(
            check_id,
            CheckStatus.FAIL,
            CheckLayer.INVARIANT,
            message="injected non-pairing kernel invariant",
            evidence={"source": "test"},
        )
        return rep

    monkeypatch.setattr(kernel_checks, "check_kernel", fake_check_kernel)


def test_run_pipeline_golden_blocks_on_non_pairing_kernel_invariant(
    tmp_path, monkeypatch
):
    vector_dir = _patch_llm_stages(monkeypatch, tmp_path)
    _patch_kernel_check_non_pairing_blocker(monkeypatch)
    out_dir = tmp_path / "out"

    with pytest.raises(
        RuntimeError,
        match="2_modelling self-check blocked under run_profile=golden",
    ) as exc:
        pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir, run_profile="golden")

    assert "kernel.coverage_completeness" in str(exc.value)
    assert (out_dir / "2_modelling" / "building_geometry.json").exists()
    assert (out_dir / "2_modelling" / "kernel_gate_report.json").exists()
    kernel = _report(out_dir / "2_modelling" / "kernel_checks.json")
    assert "kernel.coverage_completeness" in {
        result.check_id for result in kernel.blocking()
    }
    assert not (out_dir / "3_split_pairing" / "geometry_specs.md").exists()


def test_run_pipeline_golden_blocks_on_mep_invariant_after_clean_correction(
    tmp_path, monkeypatch
):
    vector_dir = _patch_llm_stages(monkeypatch, tmp_path, bad_mep=True)

    exploratory_warnings: list[str] = []
    sink_id = pipeline.logger.add(
        lambda message: exploratory_warnings.append(str(message)),
        level="WARNING",
    )
    try:
        intake = pipeline.run_pipeline(
            vector_dir,
            "{}",
            out_dir=tmp_path / "out_exploratory",
            run_profile="exploratory",
        )
    finally:
        pipeline.logger.remove(sink_id)

    assert isinstance(intake, IntakeOutput)
    exploratory_mep = _report(tmp_path / "out_exploratory" / "4_mep" / "mep_checks.json")
    assert "mep.schedule_completeness" in _statuses(exploratory_mep)
    assert "mep.schedule_completeness" in [
        result.check_id for result in exploratory_mep.blocking()
    ]
    assert any(
        "4_mep self-check reported" in warning
        and "continuing" in warning
        and "mep.schedule_completeness" in warning
        for warning in exploratory_warnings
    )

    with pytest.raises(
        RuntimeError,
        match="4_mep self-check blocked under run_profile=golden",
    ) as exc:
        pipeline.run_pipeline(
            vector_dir,
            "{}",
            out_dir=tmp_path / "out_golden",
            run_profile="golden",
        )

    assert "mep.schedule_completeness" in str(exc.value)


def test_run_pipeline_exploratory_warns_and_continues_on_non_pairing_kernel_invariant(
    tmp_path, monkeypatch
):
    vector_dir = _patch_llm_stages(monkeypatch, tmp_path)
    _patch_kernel_check_non_pairing_blocker(monkeypatch, check_id="kernel.normals")
    out_dir = tmp_path / "out"
    warnings: list[str] = []
    sink = pipeline.logger.add(lambda msg: warnings.append(str(msg)), level="WARNING")
    try:
        intake = pipeline.run_pipeline(
            vector_dir, "{}", out_dir=out_dir, run_profile="exploratory"
        )
    finally:
        pipeline.logger.remove(sink)

    assert isinstance(intake, IntakeOutput)
    kernel = _report(out_dir / "2_modelling" / "kernel_checks.json")
    assert "kernel.normals" in {result.check_id for result in kernel.blocking()}
    assert any("2_modelling self-check" in msg for msg in warnings)
    assert any("kernel.normals" in msg for msg in warnings)
    assert (out_dir / "3_split_pairing" / "geometry_specs.md").exists()
    assert (out_dir / "5_intakeoutput" / "intake_output.json").exists()


def test_run_pipeline_exploratory_correction_blocking_fails_closed_without_contract(
    tmp_path, monkeypatch
):
    """BO-CR2 (E4-oc v2 §3.4, review-ask #1 REJECT): a blocking gate①
    correction leaves the run without an accepted identity to bind the
    output-coordinate contract — even under `exploratory` the pipeline must
    HARD FAIL rather than fall back to contract-less pre-E4 assembly. The
    correction report is still persisted first (attribution evidence), and
    the exploratory warn is still logged; nothing downstream runs."""
    vector_dir = _patch_llm_stages(monkeypatch, tmp_path, bad_mep=True)
    out_dir = tmp_path / "out"
    testdata = json.dumps({"Floor plans": [{"thermal_zones": 1}], "site_location": _SITE})
    warnings: list[str] = []
    sink = pipeline.logger.add(lambda msg: warnings.append(str(msg)), level="WARNING")
    try:
        with pytest.raises(RuntimeError, match="output-coordinate contract"):
            pipeline.run_pipeline(
                vector_dir, testdata, out_dir=out_dir, run_profile="exploratory"
            )
    finally:
        pipeline.logger.remove(sink)

    correction = _report(out_dir / "1_correction" / "correction_checks.json")
    assert "correction.audit_completeness" in {
        result.check_id for result in correction.blocking()
    }
    assert any("1_correction self-check" in msg for msg in warnings)
    # nothing downstream of the identity gate may exist
    assert not (out_dir / "4_mep" / "mep_checks.json").exists()
    assert not (out_dir / "5_intakeoutput" / "intake_output.json").exists()


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


def test_run_pipeline_golden_blocks_on_reading_invariant_after_sidecars(
    tmp_path, monkeypatch
):
    vector_dir = tmp_path / "0_reading"
    _write_reading(
        vector_dir,
        {
            "image_kind": "plan",
            "uncaptured": [],
            "scale_origin": {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None},
            "strokes": [
                {
                    "id": "S1",
                    "pen": "wall",
                    "provenance": "seen",
                    "confidence": "high",
                    "geometry": {"kind": "line", "p1": [0, 0], "p2": [2, 0]},
                },
                {
                    "id": "S2",
                    "pen": "not_a_pen",
                    "provenance": "seen",
                    "confidence": "high",
                    "geometry": {"kind": "line", "p1": [0, 0], "p2": [2, 0]},
                }
            ],
        },
    )
    _patch_llm_stages(monkeypatch, tmp_path)
    out_dir = tmp_path / "out"

    with pytest.raises(
        RuntimeError,
        match="0_reading self-check blocked under run_profile=golden",
    ) as exc:
        pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir, run_profile="golden")

    assert "1f_view.reading.pen_kind_valid" in str(exc.value)
    reading = _report(out_dir / "0_reading" / "reading_checks.json")
    assert "1f_view.reading.pen_kind_valid" in {
        result.check_id for result in reading.blocking()
    }
    debt = json.loads((out_dir / "1_correction" / "evidence_debt.json").read_text())
    assert debt["debts"] == []
    assert not (out_dir / "1_correction" / "correction_checks.json").exists()


def test_run_pipeline_exploratory_warns_and_continues_on_reading_invariant(
    tmp_path, monkeypatch
):
    vector_dir = tmp_path / "0_reading"
    _write_reading(
        vector_dir,
        {
            "image_kind": "plan",
            "uncaptured": [],
            "scale_origin": {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None},
            "strokes": [
                {
                    "id": "S1",
                    "pen": "wall",
                    "provenance": "seen",
                    "confidence": "high",
                    "geometry": {"kind": "line", "p1": [0, 0], "p2": [2, 0]},
                },
                {
                    "id": "S2",
                    "pen": "not_a_pen",
                    "provenance": "seen",
                    "confidence": "high",
                    "geometry": {"kind": "line", "p1": [0, 0], "p2": [2, 0]},
                }
            ],
        },
    )
    _patch_llm_stages(monkeypatch, tmp_path)
    out_dir = tmp_path / "out"
    warnings: list[str] = []
    sink = pipeline.logger.add(lambda msg: warnings.append(str(msg)), level="WARNING")
    try:
        intake = pipeline.run_pipeline(
            vector_dir, "{}", out_dir=out_dir, run_profile="exploratory"
        )
    finally:
        pipeline.logger.remove(sink)

    assert isinstance(intake, IntakeOutput)
    reading = _report(out_dir / "0_reading" / "reading_checks.json")
    assert "1f_view.reading.pen_kind_valid" in {
        result.check_id for result in reading.blocking()
    }
    assert any("0_reading self-check" in msg for msg in warnings)
    assert any("1f_view.reading.pen_kind_valid" in msg for msg in warnings)
    assert (out_dir / "5_intakeoutput" / "intake_output.json").exists()


def test_run_pipeline_golden_blocks_on_future_assembly_invariant(
    tmp_path, monkeypatch
):
    vector_dir = _patch_llm_stages(monkeypatch, tmp_path)
    out_dir = tmp_path / "out"

    import src.validator.checks.assembly as assembly_checks

    def fake_check_assembly(
        _intake,
        used_constructions,
        *,
        capability_profile: str = "rectangular",
        run_profile: str = "exploratory",
    ) -> CheckReport:
        rep = CheckReport(
            stage="5_intakeoutput",
            capability_profile=capability_profile,
            run_profile=run_profile,
        )
        rep.add_pass(
            "assembly.contract_backstop",
            CheckLayer.INVARIANT,
            evidence={"checked": len(used_constructions)},
        )
        rep.add_fail(
            "assembly.future_blocker",
            CheckLayer.INVARIANT,
            "injected assembly invariant",
            evidence={"source": "test"},
        )
        return rep

    monkeypatch.setattr(assembly_checks, "check_assembly", fake_check_assembly)

    with pytest.raises(
        RuntimeError,
        match="5_intakeoutput self-check blocked under run_profile=golden",
    ) as exc:
        pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir, run_profile="golden")

    assert "assembly.future_blocker" in str(exc.value)
    assembly = _report(out_dir / "5_intakeoutput" / "assembly_checks.json")
    assert "assembly.future_blocker" in {
        result.check_id for result in assembly.blocking()
    }
    assert not (out_dir / "5_intakeoutput" / "contract_issues.json").exists()
    assert not (out_dir / "5_intakeoutput" / "intake_output.json").exists()


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
    inline_assembly = _statuses(
        _report(run_dir / "5_intakeoutput" / "assembly_checks.json")
    )
    assert inline_assembly == {"assembly.contract_backstop": "pass"}

    validate_case(run_dir, case_dir=case_dir, write_reports=True)

    post_validate_correction = _statuses(
        _report(run_dir / "1_correction" / "correction_checks.json")
    )
    # F-20: validate_case's own accepted-attempt trust-root re-verification
    # check (`correction.accepted_artifact_trust` — same named exemption as
    # tests/test_check_parity.py's `_EXCLUDED_VALIDATE_CHECKS`). This run has
    # no manifest at all, so the trust resolver reports NOT_APPLICABLE and
    # continues under the pre-F-20 stage-root audit path; the inline
    # run_pipeline path never produces this check_id — it consumes an
    # already-signed in-memory verified bundle, not an on-disk accepted
    # attempt to re-replay against.
    assert post_validate_correction.pop("correction.accepted_artifact_trust") == "not_applicable"
    assert inline_correction == post_validate_correction
    assert inline_mep == _statuses(_report(run_dir / "4_mep" / "mep_checks.json"))
    assert inline_assembly == _statuses(
        _report(run_dir / "5_intakeoutput" / "assembly_checks.json")
    )


def test_run_pipeline_a8_pre_core_coverage_still_enters_correction_report(
    tmp_path, monkeypatch
):
    vector_dir = tmp_path / "0_reading"
    _write_reading(
        vector_dir,
        {
            "image_kind": "plan",
            "uncaptured": [],
            "scale_origin": {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None},
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
