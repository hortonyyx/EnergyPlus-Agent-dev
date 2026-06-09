"""Step-4 wiring: the deterministic geometry kernel runs inside phase 2 as an
advisory stage — it materializes a building_geometry.json + gate report and
returns gate issues, but never raises (phase2b stays authoritative)."""

from __future__ import annotations

import json

from src.agent.correction.schema import CorrectedGeometry
from src.agent.phase2 import materialize_kernel_geometry


def _clean_two_floor() -> CorrectedGeometry:
    return CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
                {"id": "F1_L", "x": [0, 5], "y": [0, 8]},
                {"id": "F1_R", "x": [5, 10], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.0, "ceiling_height": 3.0, "cells": [
                {"id": "F2_L", "x": [0, 4], "y": [0, 8]},
                {"id": "F2_R", "x": [4, 10], "y": [0, 8]}]},
        ],
    )


def test_kernel_wiring_clean_build_materializes(tmp_path):
    bg, issues = materialize_kernel_geometry(_clean_two_floor(), tmp_path)
    assert issues == [], issues
    assert bg is not None and bg.zones and bg.surfaces
    geo = json.loads((tmp_path / "building_geometry.json").read_text())
    assert geo["zones"] and geo["surfaces"]
    report = json.loads((tmp_path / "kernel_gate_report.json").read_text())
    assert report["gate_issues"] == []


def test_kernel_wiring_no_outdir_is_silent():
    """Advisory stage tolerates out_dir=None (no materialization, still returns)."""
    bg, issues = materialize_kernel_geometry(_clean_two_floor(), None)
    assert issues == [] and bg is not None


def test_kernel_wiring_never_raises_on_overlap(tmp_path):
    """A phase2a tiling defect (overlap) is reported via notes, not an exception."""
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
            {"id": "Room", "x": [0, 5], "y": [3, 5]},
            {"id": "Corridor", "x": [0, 10], "y": [3, 5]},
        ]}],
    )
    materialize_kernel_geometry(g, tmp_path)  # must not raise
    report = json.loads((tmp_path / "kernel_gate_report.json").read_text())
    assert any("OVERLAP" in n for n in report["build_notes"])
