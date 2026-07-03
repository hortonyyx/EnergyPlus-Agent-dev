"""Per-run flow configuration loaded from ``<run>/run_config.yaml``.

This file is orchestration metadata only: scope, judge/review switches, model
provenance, and judge-side grade tolerances. Missing or malformed files soft
degrade to the historical defaults so old runs remain replayable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import warnings

import yaml

DEFAULT_STAGES = (
    "0_reading",
    "1_correction",
    "2_modelling",
    "3_split_pairing",
    "4_mep",
    "5_intakeoutput",
)
RUN_CONFIG_NAME = "run_config.yaml"
DEFAULT_WALL_TOL_M = 0.30
DEFAULT_WINDOW_CENTRE_TOL_M = 0.40


@dataclass(frozen=True)
class GradeConfig:
    wall_tol_m: float = DEFAULT_WALL_TOL_M
    window_centre_tol_m: float = DEFAULT_WINDOW_CENTRE_TOL_M

    def as_tolerances(self) -> dict[str, float]:
        return {
            "wall_tol_m": float(self.wall_tol_m),
            "window_centre_tol_m": float(self.window_centre_tol_m),
        }


@dataclass(frozen=True)
class RunConfig:
    path: Path | None = None
    present: bool = False
    scope_stages: tuple[str, ...] = DEFAULT_STAGES
    judge_mode: str = "stop"
    review: dict[str, bool] = field(
        default_factory=lambda: {"reading": False, "correction": False, "geometry": False}
    )
    models: dict[str, object] = field(default_factory=dict)
    grade: dict[str, GradeConfig] = field(
        default_factory=lambda: {
            "reading": GradeConfig(),
            "correction": GradeConfig(),
        }
    )

    @classmethod
    def defaults(cls, *, path: Path | None = None, present: bool = False) -> "RunConfig":
        return cls(path=path, present=present)

    def grade_for(self, stage: str) -> GradeConfig:
        key = {"0_reading": "reading", "1_correction": "correction"}.get(stage, stage)
        return self.grade.get(key, GradeConfig())

    def review_stages(self) -> set[str]:
        mapping = {"reading": "0_reading", "correction": "1_correction"}
        return {
            stage
            for key, stage in mapping.items()
            if bool(self.review.get(key))
        }


def load_run_config(run_dir: Path | str) -> RunConfig:
    path = Path(run_dir) / RUN_CONFIG_NAME
    if not path.exists():
        warnings.warn(
            f"{RUN_CONFIG_NAME} not found under {Path(run_dir)}; using flow defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return RunConfig.defaults(path=path, present=False)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:  # noqa: BLE001 - metadata must soft-degrade
        warnings.warn(
            f"could not read {path}: {type(e).__name__}: {e}; using flow defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return RunConfig.defaults(path=path, present=False)
    if not isinstance(raw, dict):
        warnings.warn(
            f"{path} root is not a mapping; using flow defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return RunConfig.defaults(path=path, present=False)
    return _parse_run_config(raw, path)


def _parse_run_config(raw: dict, path: Path) -> RunConfig:
    scope_stages = _parse_scope_stages(raw.get("scope"), path)
    judge_mode = _parse_judge_mode(raw.get("judge"), path)
    review = _parse_review(raw.get("review"))
    models = raw.get("models") if isinstance(raw.get("models"), dict) else {}
    grade = {
        "reading": _parse_grade(raw.get("grade"), "reading", path),
        "correction": _parse_grade(raw.get("grade"), "correction", path),
    }
    return RunConfig(
        path=path,
        present=True,
        scope_stages=scope_stages,
        judge_mode=judge_mode,
        review=review,
        models=dict(models),
        grade=grade,
    )


def _parse_scope_stages(scope: object, path: Path) -> tuple[str, ...]:
    if not isinstance(scope, dict):
        return DEFAULT_STAGES
    stages = scope.get("stages")
    if not isinstance(stages, list) or not stages:
        return DEFAULT_STAGES
    out = tuple(str(s) for s in stages if str(s) in DEFAULT_STAGES)
    if not out:
        warnings.warn(f"{path} scope.stages has no known stages; using defaults", RuntimeWarning)
        return DEFAULT_STAGES
    return out


def _parse_judge_mode(judge: object, path: Path) -> str:
    if not isinstance(judge, dict):
        return "stop"
    raw = judge.get("mode", "stop")
    if raw is False:
        return "off"
    if raw is True:
        return "stop"
    mode = str(raw)
    if mode not in {"stop", "off"}:
        warnings.warn(f"{path} judge.mode={mode!r} is invalid; using stop", RuntimeWarning)
        return "stop"
    return mode


def _parse_review(review: object) -> dict[str, bool]:
    defaults = {"reading": False, "correction": False, "geometry": False}
    if not isinstance(review, dict):
        return defaults
    return {key: bool(review.get(key, defaults[key])) for key in defaults}


def _parse_grade(grade: object, key: str, path: Path) -> GradeConfig:
    if not isinstance(grade, dict):
        return GradeConfig()
    sec = grade.get(key)
    if not isinstance(sec, dict):
        return GradeConfig()
    try:
        return GradeConfig(
            wall_tol_m=float(sec.get("wall_tol_m", DEFAULT_WALL_TOL_M)),
            window_centre_tol_m=float(
                sec.get("window_centre_tol_m", DEFAULT_WINDOW_CENTRE_TOL_M)
            ),
        )
    except (TypeError, ValueError):
        warnings.warn(f"{path} grade.{key} has invalid tolerances; using defaults", RuntimeWarning)
        return GradeConfig()
