from __future__ import annotations

import pytest

from src.agent.execution.run_config import load_run_config
from src.agent.execution.run_config import GradeConfig


def test_run_config_missing_soft_defaults(tmp_path):
    with pytest.warns(RuntimeWarning, match="run_config.yaml not found"):
        cfg = load_run_config(tmp_path)

    assert cfg.present is False
    assert cfg.judge_mode == "stop"
    assert cfg.review_stages() == set()
    assert cfg.grade_for("0_reading").as_tolerances() == {
        "wall_tol_m": 0.3,
        "window_centre_tol_m": 0.4,
        "elevation_along_tol_m": 0.4,
        "sill_tol_m": 0.3,
        "head_tol_m": 0.3,
        "width_tol_m": 0.4,
        "position_tol_m": 0.3,
        "extent_tol_m": 0.3,
        "complete_eps_m": 0.05,
        "overlap_accept": 0.75,
        "overlap_complete": 0.95,
        "floor_line_tol_m": 0.3,
    }


def test_run_config_loads_scope_review_models_and_grade(tmp_path):
    (tmp_path / "run_config.yaml").write_text(
        "\n".join(
            [
                "scope:",
                "  stages: [0_reading, 1_correction]",
                "judge:",
                "  mode: off",
                "review:",
                "  reading: true",
                "  correction: false",
                "models:",
                "  reading: claude-sonnet-5",
                "capability_profile: orthogonal_polygon",
                "grade:",
                "  reading:",
                "    wall_tol_m: 0.2",
                "    window_centre_tol_m: 0.25",
                "    elevation_along_tol_m: 0.35",
                "    sill_tol_m: 0.15",
                "    head_tol_m: 0.16",
                "    width_tol_m: 0.5",
                "    position_tol_m: 0.21",
                "    extent_tol_m: 0.22",
                "    complete_eps_m: 0.04",
                "    overlap_accept: 0.8",
                "    overlap_complete: 0.97",
                "    floor_line_tol_m: 0.28",
            ]
        ),
        encoding="utf-8",
    )

    cfg = load_run_config(tmp_path)

    assert cfg.present is True
    assert cfg.scope_stages == ("0_reading", "1_correction")
    assert cfg.judge_mode == "off"
    assert cfg.review_stages() == {"0_reading"}
    assert cfg.models["reading"] == "claude-sonnet-5"
    assert cfg.capability_profile == "orthogonal_polygon"
    assert cfg.grade_for("0_reading").as_tolerances() == {
        "wall_tol_m": 0.2,
        "window_centre_tol_m": 0.25,
        "elevation_along_tol_m": 0.35,
        "sill_tol_m": 0.15,
        "head_tol_m": 0.16,
        "width_tol_m": 0.5,
        "position_tol_m": 0.21,
        "extent_tol_m": 0.22,
        "complete_eps_m": 0.04,
        "overlap_accept": 0.8,
        "overlap_complete": 0.97,
        "floor_line_tol_m": 0.28,
    }
    assert cfg.grade_for("1_correction").as_tolerances() == {
        "wall_tol_m": 0.3,
        "window_centre_tol_m": 0.4,
        "elevation_along_tol_m": 0.4,
        "sill_tol_m": 0.3,
        "head_tol_m": 0.3,
        "width_tol_m": 0.4,
        "position_tol_m": 0.3,
        "extent_tol_m": 0.3,
        "complete_eps_m": 0.05,
        "overlap_accept": 0.75,
        "overlap_complete": 0.95,
        "floor_line_tol_m": 0.3,
    }


def test_grade_config_rejects_invalid_tolerance_ordering():
    with pytest.raises(ValueError, match="complete_eps_m"):
        GradeConfig(complete_eps_m=0.4, extent_tol_m=0.3)
    with pytest.raises(ValueError, match="overlap_accept"):
        GradeConfig(overlap_accept=0.96, overlap_complete=0.95)
    with pytest.raises(ValueError, match="overlap_complete"):
        GradeConfig(overlap_complete=1.1)
    with pytest.raises(ValueError, match="wall_tol_m"):
        GradeConfig(wall_tol_m=-0.1)


def test_run_config_invalid_capability_profile_fails_closed(tmp_path):
    """r2-1 (ruling 2026-08-04 §r2-1): a present-but-invalid capability_profile
    (e.g. curved_polygon / a one-letter typo) is fail-closed on load, not
    warn+None. Previously an invalid value warned and returned None, which
    _resolve_run_profiles then fell back past to the CLI rectangular default —
    so a typo silently demoted a declared orthogonal_polygon capability (and
    capability decides correction v2 vs v3 schema). Symmetric with run_profile
    (R1-2). Absent (key not present) still returns None — see
    test_run_config_present_fields_parse."""
    (tmp_path / "run_config.yaml").write_text(
        "capability_profile: curved_polygon\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="capability_profile_invalid"):
        load_run_config(tmp_path)
