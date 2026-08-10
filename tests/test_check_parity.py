from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import src.agent.pipeline as pipeline
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.validation_run import validate_case
from src.agent.intakeoutput import MepOutput
from src.validator.checks.schema import CheckReport


_SITE = {
    "latitude": 22.5,
    "longitude": 114.0,
    "time_zone": 8.0,
    "elevation": 5.0,
}

# Explicit parity exclusions. These checks are intentionally not a 1:1 match
# between inline production gates and validate_case's offline audit surface.
_EXCLUDED_ARTIFACTS = {
    "1_correction/evidence_debt_coverage_checks.json": (
        "A8 pre-core evidence sidecar; correction_checks.json is the core S1 gate"
    ),
}
_EXCLUDED_VALIDATE_CHECKS = {
    ("2_modelling", "kernel.artifact_consistency"): (
        "validate_case-only stale building_geometry.json audit"
    ),
    ("3_split_pairing", "3_split_pairing.build"): (
        "validate_case-only geometry_specs.md serializer text equality audit"
    ),
    ("downstream", "ep.end_present"): "EP baseline is downstream, not run_pipeline",
    ("downstream", "ep.completed"): "EP baseline is downstream, not run_pipeline",
    ("downstream", "ep.zero_severe"): "EP baseline is downstream, not run_pipeline",
    ("downstream", "ep.warning_threshold"): (
        "EP baseline is downstream, not run_pipeline"
    ),
    ("0_reading", "reading.view_manifest_coverage"): (
        "C2 B-M §4.4: validate_case-only read-only view-manifest audit "
        "(verify_view_manifest); run_pipeline has no view-manifest wiring yet "
        "— that is a separate, later batch, not this one"
    ),
    ("1_correction", "correction.accepted_artifact_trust"): (
        "F-20: this is validate_case's offline audit surface re-verifying the "
        "on-disk accepted-attempt chain (manifest version / hash / artifact "
        "contract); the inline run_pipeline caller consumes an already-signed, "
        "in-memory verified bundle (verify_integrated_gate1_correction) and "
        "has no on-disk accepted attempt to re-replay this against"
    ),
}


def _write_reading(vector_dir: Path) -> None:
    vector_dir.mkdir(parents=True, exist_ok=True)
    (vector_dir / "reading_summary.md").write_text("summary", encoding="utf-8")
    (vector_dir / "1f_view.json").write_text(
        json.dumps(
            {
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


def _good_geom() -> CorrectedGeometry:
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
            "corrections": [{"source": "testdata", "reason": "zone count"}],
            "unsupported": [],
        }
    )


def _zones_from_specs(zone_specs: str) -> list[str]:
    return re.findall(r"^- ([^:]+):", zone_specs, flags=re.MULTILINE)


def _mep_dict(zones: list[str], used_constructions: set[str]) -> dict:
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
            "  For: AllDays,\n"
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


def _patch_llm_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "run_correction", lambda *_args, **_kwargs: _good_geom())

    def fake_run_mep(zone_specs, used_constructions, _testdata_text, *, out_dir, **_kwargs):
        mep = MepOutput.model_validate(
            _mep_dict(_zones_from_specs(zone_specs), used_constructions)
        )
        if out_dir is not None:
            (out_dir / "mep_output.json").write_text(
                mep.model_dump_json(indent=2), encoding="utf-8"
            )
        return mep

    monkeypatch.setattr(pipeline, "run_mep", fake_run_mep)


def _normalize_s0_check_id(check_id: str) -> str:
    marker = ".reading."
    if marker in check_id:
        return check_id[check_id.index(marker) + 1 :]
    return check_id


def _artifact_check_ids(run_dir: Path) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in sorted(run_dir.rglob("*_checks.json")):
        rel = path.relative_to(run_dir).as_posix()
        if rel in _EXCLUDED_ARTIFACTS:
            continue
        report = CheckReport.model_validate_json(path.read_text(encoding="utf-8"))
        stage = path.parent.name
        for result in report.results:
            check_id = result.check_id
            if stage == "0_reading":
                check_id = _normalize_s0_check_id(check_id)
            found.add((stage, check_id))
    return found


def _validate_case_check_ids(run_dir: Path, case_dir: Path) -> set[tuple[str, str]]:
    result = validate_case(run_dir, case_dir=case_dir, write_reports=False)
    found: set[tuple[str, str]] = set()
    for key, report in result.reports.items():
        stage = key.split("::", 1)[0]
        for item in report.results:
            check_id = item.check_id
            if stage == "0_reading":
                check_id = _normalize_s0_check_id(check_id)
            normalized = (stage, check_id)
            if normalized in _EXCLUDED_VALIDATE_CHECKS:
                continue
            found.add(normalized)
    return found


def test_run_pipeline_and_validate_case_check_id_parity(tmp_path, monkeypatch):
    case_dir = tmp_path / "case"
    run_dir = case_dir / "run"
    vector_dir = run_dir / "0_reading"
    testdata = {"Floor plans": [{"thermal_zones": 1}], "site_location": _SITE}
    (case_dir / "case_data").mkdir(parents=True)
    (case_dir / "case_data" / "testdata_prompt.json").write_text(
        json.dumps(testdata), encoding="utf-8"
    )
    _write_reading(vector_dir)
    _patch_llm_stages(monkeypatch)

    pipeline.run_pipeline(vector_dir, json.dumps(testdata), out_dir=run_dir)

    artifact_ids = _artifact_check_ids(run_dir)
    validated_ids = _validate_case_check_ids(run_dir, case_dir)
    # B3 retains the established correction check_id while upgrading its
    # semantics to area-conservation v2; both paths must continue to expose it.
    assert ("1_correction", "correction.coverage") in artifact_ids
    assert artifact_ids == validated_ids
