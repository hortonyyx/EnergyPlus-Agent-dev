from __future__ import annotations

import pytest

import src.agent.geometry.capability as capability
from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry import build_geometry
from src.agent.geometry.adjacency import expected_internal_interface_area
from src.agent.geometry.specs import building_geometry_dict
from src.validator.checks.correction import check_correction
from src.validator.checks.kernel import check_kernel


def _single_cell(**overrides) -> CorrectedGeometry:
    data = {
        "footprint_x": [0.0, 10.0],
        "footprint_y": [0.0, 8.0],
        "floors": [
            {
                "name": "F1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "cells": [{"id": "A", "x": [0.0, 10.0], "y": [0.0, 8.0]}],
            }
        ],
        "windows": [],
        "corrections": [],
        "conflicts": [],
        "unsupported": [],
    }
    data.update(overrides)
    return CorrectedGeometry.model_validate(data)


def _two_floor_pair() -> CorrectedGeometry:
    return CorrectedGeometry.model_validate(
        {
            "footprint_x": [0.0, 10.0],
            "footprint_y": [0.0, 8.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {"id": "F1_L", "x": [0.0, 5.0], "y": [0.0, 8.0]},
                        {"id": "F1_R", "x": [5.0, 10.0], "y": [0.0, 8.0]},
                    ],
                },
                {
                    "name": "F2",
                    "z_floor": 3.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {"id": "F2_L", "x": [0.0, 5.0], "y": [0.0, 8.0]},
                        {"id": "F2_R", "x": [5.0, 10.0], "y": [0.0, 8.0]},
                    ],
                },
            ],
            "windows": [],
        }
    )


def test_schema_version_defaults_to_v1_and_unknown_blocks_gate():
    geom = _single_cell()
    assert geom.schema_version == capability.SCHEMA_VERSION_V1

    rep = check_correction(_single_cell(schema_version="future"))
    blocked = {r.check_id for r in rep.blocking()}

    assert capability.CHECK_SCHEMA_VERSION_SUPPORTED in blocked


def test_orthogonal_polygon_profile_accepts_v1_and_profile_mismatch_blocks(monkeypatch):
    geom = _single_cell()
    rep = check_correction(geom, capability_profile=capability.CAPABILITY_PROFILE_ORTHOGONAL_POLYGON)
    assert capability.CHECK_CAPABILITY_PROFILE_SHAPES not in {r.check_id for r in rep.blocking()}

    future_version = "test_polygon"
    monkeypatch.setattr(
        capability,
        "SUPPORTED_SCHEMA_VERSIONS",
        frozenset({capability.SCHEMA_VERSION_V1, future_version}),
    )
    monkeypatch.setitem(
        capability.SCHEMA_VERSION_SHAPES,
        future_version,
        frozenset({capability.SHAPE_ORTHOGONAL_POLYGON}),
    )
    rep = check_correction(_single_cell(schema_version=future_version))

    assert capability.CHECK_CAPABILITY_PROFILE_SHAPES in {r.check_id for r in rep.blocking()}


def test_v1_default_and_explicit_schema_version_are_byte_identical_geometry():
    default_bg = build_geometry(_two_floor_pair())
    explicit_bg = build_geometry(_two_floor_pair().model_copy(update={"schema_version": "1"}))

    assert building_geometry_dict(default_bg) == building_geometry_dict(explicit_bg)


def test_window_on_wall_segment_seam_fails_kernel_build():
    geom = CorrectedGeometry.model_validate(
        {
            "footprint_x": [0.0, 10.0],
            "footprint_y": [0.0, 8.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {"id": "A", "x": [0.0, 5.0], "y": [0.0, 8.0]},
                        {"id": "B", "x": [5.0, 10.0], "y": [0.0, 8.0]},
                    ],
                }
            ],
            "windows": [
                {
                    "id": "W_seam",
                    "floor": "F1",
                    "facade": "South",
                    "span": [4.0, 5.0],
                    "z": [1.0, 2.0],
                    "room": "A",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="ambiguous parent wall"):
        build_geometry(geom)


def test_coverage_check_uses_shared_expected_interface_helper():
    bg = build_geometry(_two_floor_pair())
    rep = check_kernel(bg)
    cov = next(r for r in rep.results if r.check_id == "kernel.coverage_completeness")
    expected = expected_internal_interface_area(
        bg.zone_volumes, min_share_m=0.05, z_tol_m=0.05
    )

    assert cov.evidence["expected_m2"] == round(expected, 3)
