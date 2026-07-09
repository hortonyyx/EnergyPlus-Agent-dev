from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

from PIL import Image

from scripts.tool_scripts.report_assembly import (
    _correction_entries,
    _gate_entries,
    _judge_entries,
    collect_eyeball_assets,
    ensure_geometry_viewer,
)
from src.validator.checks.schema import CheckLayer, CheckReport


def _png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), (250, 250, 248)).save(path)


def test_collect_eyeball_assets_collects_stage_grades(tmp_path):
    run_dir = tmp_path / "run"
    _png(run_dir / "0_reading" / "grade.png")
    _png(run_dir / "1_correction" / "grade.png")

    result = collect_eyeball_assets(run_dir)

    names = {asset["filename"] for asset in result["assets"]}
    assert {"0_reading_grade.png", "1_correction_grade.png"} <= names
    assert (run_dir / "report" / "eyeball" / "0_reading_grade.png").exists()
    assert (run_dir / "report" / "eyeball" / "1_correction_grade.png").exists()


def test_collect_eyeball_assets_collects_per_floor_zones(tmp_path):
    run_dir = tmp_path / "run"
    _png(run_dir / "1_correction" / "zones_1f.png")
    _png(run_dir / "1_correction" / "zones_2f.png")

    result = collect_eyeball_assets(run_dir)

    names = {asset["filename"] for asset in result["assets"]}
    assert {"1_correction_zones_1f.png", "1_correction_zones_2f.png"} <= names
    assert (run_dir / "report" / "eyeball" / "1_correction_zones_1f.png").exists()
    assert (run_dir / "report" / "eyeball" / "1_correction_zones_2f.png").exists()


def test_gate_entries_indexes_blocking_and_flagged_results():
    report = CheckReport(stage="4_mep", run_profile="golden")
    report.add_fail(
        "mep.schedule_completeness",
        CheckLayer.INVARIANT,
        "incomplete schedule",
        evidence={"schedule": "Occ"},
    )
    report.add_fail(
        "mep.per_zone_coverage",
        CheckLayer.CROSS_CHECK,
        "missing lights",
        evidence={"zone": "Z1"},
    )
    validation_result = SimpleNamespace(reports={"4_mep": report})

    entries = _gate_entries(validation_result)

    assert entries == [
        {
            "id": "E:gate:4_mep:mep.schedule_completeness",
            "kind": "gate",
            "source": "4_mep",
            "payload": {
                "report_key": "4_mep",
                "stage": "4_mep",
                "check_id": "mep.schedule_completeness",
                "status": "fail",
                "layer": "invariant",
                "disposition": "block",
                "message": "incomplete schedule",
                "evidence": {"schedule": "Occ"},
            },
        },
        {
            "id": "E:gate:4_mep:mep.per_zone_coverage",
            "kind": "gate",
            "source": "4_mep",
            "payload": {
                "report_key": "4_mep",
                "stage": "4_mep",
                "check_id": "mep.per_zone_coverage",
                "status": "fail",
                "layer": "cross_check",
                "disposition": "flag",
                "message": "missing lights",
                "evidence": {"zone": "Z1"},
            },
        },
    ]


def test_judge_entries_indexes_attempt_criteria(tmp_path):
    run_dir = tmp_path / "run"
    judge_path = run_dir / "0_reading" / "attempts" / "1" / "judge.json"
    judge_path.parent.mkdir(parents=True)
    judge_path.write_text(
        json.dumps(
            {
                "root_stage": "0_reading",
                "rubric_id": "reading.v1",
                "criteria": [
                    {"id": "c-visible", "verdict": "pass"},
                    {"id": "c-dimensions", "verdict": "fail"},
                ],
            }
        ),
        encoding="utf-8",
    )

    entries = _judge_entries(run_dir)

    assert [entry["id"] for entry in entries] == [
        "E:judge:0_reading:1:c1",
        "E:judge:0_reading:1:c2",
    ]
    assert all(
        entry["source"] == "0_reading/attempts/1/judge.json" for entry in entries
    )
    assert entries[0]["payload"] == {
        "stage": "0_reading",
        "attempt": "1",
        "criterion_ordinal": 1,
        "criterion": {"id": "c-visible", "verdict": "pass"},
        "root_stage": "0_reading",
        "rubric_id": "reading.v1",
    }


def test_correction_entries_indexes_audit_sidecar_rows(tmp_path):
    run_dir = tmp_path / "run"
    sidecar = run_dir / "1_correction" / "corrections.json"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text(
        json.dumps(
            {
                "corrections": [{"id": "C 1", "action": "snap"}],
                "conflicts": [{"id": "wall/east", "reason": "ambiguous"}],
                "unsupported": [{"note": "curved wall"}],
            }
        ),
        encoding="utf-8",
    )

    entries = _correction_entries(run_dir)

    assert [entry["id"] for entry in entries] == [
        "E:corr:corrections:C_1",
        "E:corr:conflicts:wall_east",
        "E:corr:unsupported:r1",
    ]
    assert all(entry["source"] == "1_correction/corrections.json" for entry in entries)
    assert entries[2]["payload"] == {
        "kind": "unsupported",
        "ordinal": 1,
        "raw_id": None,
        "row": {"note": "curved wall"},
    }


def test_ensure_geometry_viewer_smoke_existing(tmp_path):
    run_dir = tmp_path / "run"
    viewer = run_dir / "manual_review" / "geometry_viewer.html"
    viewer.parent.mkdir(parents=True)
    viewer.write_text("<html></html>", encoding="utf-8")

    result = ensure_geometry_viewer(run_dir)

    assert result == {
        "available": True,
        "path": "manual_review/geometry_viewer.html",
        "report_link": "../manual_review/geometry_viewer.html",
        "status": "existing",
    }
