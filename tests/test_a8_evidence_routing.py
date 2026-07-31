from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

import src.agent.pipeline as pipeline
from src.agent.intakeoutput import MepOutput
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.evidence_preflight import (
    EvidenceDebt,
    EvidenceDebtItem,
    compute_evidence_debt_from_vector_dir,
    project_evidence_debt,
)
from src.validator.checks.correction import check_evidence_debt_coverage
from src.validator.checks.schema import CheckLayer, CheckReport, Disposition

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import report_assembly  # noqa: E402


def _minimal_geom(*, conflicts=None, corrections=None) -> CorrectedGeometry:
    return CorrectedGeometry.model_validate(
        {
            "footprint_x": [0.0, 2.0],
            "footprint_y": [0.0, 2.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [{"id": "C1", "role": "office", "x": [0.0, 2.0], "y": [0.0, 2.0]}],
                }
            ],
            "windows": [],
            "conflicts": conflicts or [],
            "corrections": corrections or [],
            "unsupported": [],
        }
    )


def _debt(items) -> EvidenceDebt:
    return EvidenceDebt(run_profile="exploratory", debts=items)


def _write_reading(vector_dir: Path, payload: dict, name: str = "1f_view.json") -> None:
    vector_dir.mkdir(parents=True, exist_ok=True)
    (vector_dir / "reading_summary.md").write_text("summary", encoding="utf-8")
    (vector_dir / name).write_text(json.dumps(payload), encoding="utf-8")


def _mep_stub() -> MepOutput:
    return MepOutput.model_validate(
        {
            "building": {"Name": "B", "North Axis": 0.0, "Terrain": "City"},
            "site_location": {
                "Name": "S",
                "Latitude": 22.5,
                "Longitude": 114.0,
                "Time Zone": 8.0,
                "Elevation": 5.0,
            },
            "material_specs": "",
            "construction_specs": "\n".join(
                [
                    "Default_Ext_Wall",
                    "Default_Int_Wall",
                    "Default_GroundFloor",
                    "Default_Roof",
                    "Cons_InterFloor",
                ]
            ),
            "schedule_specs": "",
            "hvac_specs": "",
            "people_specs": "",
            "lights_specs": "",
        }
    )


def _patch_pipeline_to_inject_interzone_issue(tmp_path, monkeypatch):
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
                }
            ],
        },
    )
    monkeypatch.setattr(pipeline, "run_correction", lambda *_args, **_kwargs: _minimal_geom())
    monkeypatch.setattr(pipeline, "run_mep", lambda *_args, **_kwargs: _mep_stub())

    import src.validator.interzone as interzone

    monkeypatch.setattr(
        interzone,
        "validate_interzone_surface_pairs",
        lambda _idf: ["injected InterZone reciprocal mismatch"],
    )
    return vector_dir


def test_preflight_projects_empty_debt_as_noop():
    rep = CheckReport(stage="0_reading")
    rep.add_pass("reading.dimensions_present", CheckLayer.CROSS_CHECK)
    debt = project_evidence_debt(rep, run_profile="exploratory")
    assert debt.debts == []

    report = check_evidence_debt_coverage(_minimal_geom(), debt)
    assert report.results == []


def test_preflight_rejudges_with_current_run_profile():
    rep = CheckReport(stage="0_reading", run_profile="exploratory")
    rep.add_fail(
        "1f_view.reading.dimension_derived_refs",
        CheckLayer.CROSS_CHECK,
        "dimension_derived stroke has unresolved refs",
        evidence={
            "legacy_migrated": False,
            "offenders": [{"stroke_id": "S1", "dimension_refs": ["missing"]}],
        },
    )

    exploratory = project_evidence_debt(rep, run_profile="exploratory")
    regression = project_evidence_debt(rep, run_profile="regression")

    assert exploratory.debts[0].disposition == "flag"
    assert regression.debts[0].disposition == "block"
    assert regression.blocking[0].check_id == "1f_view.reading.dimension_derived_refs"


def test_exploratory_evidence_debt_is_injected_into_correction_prompt(tmp_path):
    vector_dir = tmp_path / "0_reading"
    _write_reading(vector_dir, {"image_kind": "plan", "uncaptured": [], "strokes": []})
    debt = _debt(
        [
            EvidenceDebtItem(
                check_id="1f_view.reading.dimension_derived_refs",
                canonical_check_id="reading.dimension_derived_refs",
                view="1f_view",
                status="fail",
                layer="cross_check",
                disposition="flag",
                message="bad refs",
                evidence={"offenders": [{"stroke_id": "S1"}]},
                scope="element_local",
                offender_ids=["S1"],
            )
        ]
    )

    _system, human = pipeline._build_correction_messages(
        vector_dir, "{}", evidence_debt=debt
    )

    assert "Reading evidence debt from deterministic 0_reading preflight" in human
    assert "Do not write these reading evidence-debt items to `unsupported`" in human
    assert "1f_view.reading.dimension_derived_refs" in human


def test_evidence_debt_none_does_not_inject_prompt_block(tmp_path):
    vector_dir = tmp_path / "0_reading"
    _write_reading(vector_dir, {"image_kind": "plan", "uncaptured": [], "strokes": []})

    _system, human = pipeline._build_correction_messages(
        vector_dir, "{}", evidence_debt=None
    )

    assert "Reading evidence debt from deterministic 0_reading preflight" not in human


def test_post_correction_coverage_element_local_blocks_only_strict_profiles():
    debt = _debt(
        [
            EvidenceDebtItem(
                check_id="1f_view.reading.dimension_derived_refs",
                canonical_check_id="reading.dimension_derived_refs",
                view="1f_view",
                status="fail",
                layer="cross_check",
                disposition="block",
                message="bad refs",
                evidence={"offenders": [{"stroke_id": "S1"}]},
                scope="element_local",
                offender_ids=["S1"],
            )
        ]
    )
    geom = _minimal_geom()

    exploratory = check_evidence_debt_coverage(geom, debt, run_profile="exploratory")
    regression = check_evidence_debt_coverage(geom, debt, run_profile="regression")

    assert exploratory.dispositions()[0][1] == Disposition.FLAG
    assert regression.dispositions()[0][1] == Disposition.BLOCK

    covered = check_evidence_debt_coverage(
        _minimal_geom(conflicts=[{"id": "conf_s1", "source_ids": ["S1"]}]),
        debt,
        run_profile="regression",
    )
    assert covered.passed


def test_post_correction_coverage_view_global_remains_advisory_in_regression():
    debt = _debt(
        [
            EvidenceDebtItem(
                check_id="1f_view.reading.dimensions_present",
                canonical_check_id="reading.dimensions_present",
                view="1f_view",
                status="fail",
                layer="cross_check",
                disposition="block",
                message="dimensioned view has empty dimensions[]",
                evidence={"dimension_count": 0},
                scope="view_global",
            )
        ]
    )

    report = check_evidence_debt_coverage(
        _minimal_geom(), debt, run_profile="regression"
    )

    assert report.dispositions()[0][1] == Disposition.FLAG
    assert report.passed


def test_run_pipeline_writes_projection_in_exploratory_before_llm(tmp_path, monkeypatch):
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
    out_dir = tmp_path / "out"

    def stop_after_preflight(*_args, **_kwargs):
        raise RuntimeError("stop after preflight")

    monkeypatch.setattr(pipeline, "run_correction", stop_after_preflight)

    with pytest.raises(RuntimeError, match="stop after preflight"):
        pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir)

    debt = json.loads((out_dir / "1_correction" / "evidence_debt.json").read_text())
    assert debt["debts"][0]["disposition"] == "flag"


def test_run_pipeline_fail_closed_for_regression_evidence_debt(tmp_path):
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
    out_dir = tmp_path / "out"

    with pytest.raises(RuntimeError, match="preflight blocked"):
        pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir, run_profile="regression")

    debt = json.loads((out_dir / "1_correction" / "evidence_debt.json").read_text())
    assert debt["debts"][0]["disposition"] == "block"


def test_evidence_debt_sidecar_enters_report_evidence_index(tmp_path):
    run_dir = tmp_path / "case" / "run"
    sidecar = run_dir / "1_correction" / "evidence_debt.json"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text(
        EvidenceDebt(
            debts=[
                EvidenceDebtItem(
                    check_id="1f_view.reading.dimension_derived_refs",
                    canonical_check_id="reading.dimension_derived_refs",
                    view="1f_view",
                    status="fail",
                    layer="cross_check",
                    disposition="flag",
                    message="bad refs",
                    scope="element_local",
                    offender_ids=["S1"],
                )
            ]
        ).model_dump_json(),
        encoding="utf-8",
    )

    entries = report_assembly._evidence_debt_entries(run_dir)

    assert len(entries) == 1
    assert entries[0]["id"].startswith("E:debt:")
    assert entries[0]["source"] == "1_correction/evidence_debt.json"


def test_run_pipeline_exploratory_surfaces_kernel_pairing_gate_and_continues(
    tmp_path, monkeypatch
):
    vector_dir = _patch_pipeline_to_inject_interzone_issue(tmp_path, monkeypatch)
    out_dir = tmp_path / "out"

    pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir, run_profile="exploratory")

    assert (out_dir / "2_modelling" / "building_geometry.json").exists()
    assert (out_dir / "2_modelling" / "kernel_gate_report.json").exists()
    assert (out_dir / "3_split_pairing" / "geometry_specs.md").exists()
    assert (out_dir / "5_intakeoutput" / "intake_output.json").exists()

    report = CheckReport.model_validate_json(
        (out_dir / "2_modelling" / "kernel_checks.json").read_text()
    )
    pairing = next(r for r in report.results if r.check_id == "kernel.pairing_gate")
    assert pairing.status.value == "fail"
    assert report.blocking()[0].check_id == "kernel.pairing_gate"

    validation_result = SimpleNamespace(
        reports={"2_modelling": report},
        geometry_digest=None,
        geometry_approved=False,
    )
    entries = report_assembly.build_evidence_index(
        out_dir,
        validation_result,
        report_assets={"assets": []},
        run_state={},
        ep=None,
    )
    gate = next(e for e in entries if e["id"] == "E:gate:2_modelling:kernel.pairing_gate")
    assert gate["kind"] == "gate"
    assert gate["payload"]["disposition"] == "block"
    assert gate["payload"]["check_id"] == "kernel.pairing_gate"


@pytest.mark.parametrize("run_profile", ["golden", "regression"])
def test_run_pipeline_fail_closed_for_kernel_pairing_gate_profiles(
    tmp_path, monkeypatch, run_profile
):
    vector_dir = _patch_pipeline_to_inject_interzone_issue(tmp_path, monkeypatch)
    out_dir = tmp_path / "out"

    with pytest.raises(
        RuntimeError,
        match=f"2_modelling self-check blocked under run_profile={run_profile}",
    ) as exc:
        pipeline.run_pipeline(vector_dir, "{}", out_dir=out_dir, run_profile=run_profile)
    assert "kernel.pairing_gate" in str(exc.value)

    report = CheckReport.model_validate_json(
        (out_dir / "2_modelling" / "kernel_checks.json").read_text()
    )
    pairing = next(r for r in report.results if r.check_id == "kernel.pairing_gate")
    assert pairing.status.value == "fail"
    assert report.run_profile == run_profile
    assert not (out_dir / "3_split_pairing" / "geometry_specs.md").exists()
