from __future__ import annotations

import pytest

from src.agent.execution.run_config import load_run_config


def test_run_config_missing_soft_defaults(tmp_path):
    with pytest.warns(RuntimeWarning, match="run_config.yaml not found"):
        cfg = load_run_config(tmp_path)

    assert cfg.present is False
    assert cfg.judge_mode == "stop"
    assert cfg.review_stages() == set()
    assert cfg.grade_for("0_reading").as_tolerances() == {
        "wall_tol_m": 0.3,
        "window_centre_tol_m": 0.4,
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
                "grade:",
                "  reading:",
                "    wall_tol_m: 0.2",
                "    window_centre_tol_m: 0.25",
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
    assert cfg.grade_for("0_reading").as_tolerances() == {
        "wall_tol_m": 0.2,
        "window_centre_tol_m": 0.25,
    }
    assert cfg.grade_for("1_correction").as_tolerances() == {
        "wall_tol_m": 0.3,
        "window_centre_tol_m": 0.4,
    }
