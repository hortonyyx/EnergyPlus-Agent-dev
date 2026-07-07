from __future__ import annotations

import json
from pathlib import Path

import src.agent.pipeline as pipeline
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.evidence_preflight import EvidenceDebt


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


def _minimal_geom_dict() -> dict:
    return {
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
        "corrections": [],
        "unsupported": [],
    }


def test_run_correction_default_evidence_debt_path_resolves_import(
    tmp_path, monkeypatch
):
    vector_dir = tmp_path / "0_reading"
    out_dir = tmp_path / "1_correction"
    _write_reading(vector_dir)

    monkeypatch.setattr(pipeline, "_section", lambda _stage: {"model_name": "stub"})

    def fake_call_json_llm(
        _section,
        _system_prompt,
        _human,
        *,
        out_dir,
        prefix,
        attempts,
        validate,
    ):
        assert prefix == "correction"
        return _minimal_geom_dict()

    monkeypatch.setattr(pipeline, "_call_json_llm", fake_call_json_llm)

    geom = pipeline.run_correction(
        vector_dir,
        "{}",
        out_dir=out_dir,
        evidence_debt=None,
        draw_validate=None,
    )

    assert isinstance(geom, CorrectedGeometry)
    debt = EvidenceDebt.model_validate_json(
        (out_dir / "evidence_debt.json").read_text(encoding="utf-8")
    )
    assert debt.source_stage == "0_reading"
