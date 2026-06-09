"""Deterministic-core tolerance config loader.

Single source for the geometry-correction tolerances consumed by
`deterministic.py`. Values live in `src/configs/correction.yaml` (basis tracked
in PartA-correction/A0_contract.md §4), not hardcoded in the core, so:

  - there is one place to change them (no Python-constant vs A0-doc drift), and
  - a test run can pin its own granularity via `$EP_AGENT_CORRECTION_CONFIG`
    (mirrors `$EP_AGENT_LLM_CONFIG`), without editing the shared file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from omegaconf import OmegaConf

CORRECTION_CONFIG_ENV: str = "EP_AGENT_CORRECTION_CONFIG"

_DEFAULT_CONFIG: Path = (
    Path(__file__).resolve().parent.parent.parent / "configs" / "correction.yaml"
)


def resolve_correction_config_path() -> Path:
    """Active config file: `$EP_AGENT_CORRECTION_CONFIG` if set, else the default."""
    override = os.environ.get(CORRECTION_CONFIG_ENV)
    if override:
        p = Path(override)
        if not p.is_file():
            raise FileNotFoundError(
                f"{CORRECTION_CONFIG_ENV}={override} does not point to a file"
            )
        return p
    return _DEFAULT_CONFIG


@dataclass(frozen=True)
class CoreTolerances:
    """Resolved tolerances for one deterministic-core run (all lengths in metres).

    See `src/configs/correction.yaml` for the per-field constraint each governs.
    """

    axis_jitter_tol_m: float  # same-axis identity clustering threshold
    structural_snap_grid_m: float  # grid for room/wall/footprint axes (post-cluster)
    min_edge_length_m: float  # sliver floor; no two canonical axes closer than this
    output_precision_m: float  # format precision + correction-logging threshold
    window_snap_grid_m: float  # finer grid for window span/z (no structural role)
    window_clamp_to_parent: bool  # clamp window span/z into its parent cell/floor
    gap_close_threshold_m: float  # auto-close a cell edge this close to the footprint
    gap_arbitration_band_m: float  # above gap_close, escalate to A3 (doc/A3; not code)

    def validate(self) -> None:
        """Guard the cross-field invariants the config comments promise."""
        if not (0 < self.structural_snap_grid_m <= self.min_edge_length_m):
            raise ValueError(
                "structural_snap_grid_m must be in (0, min_edge_length_m]; got "
                f"{self.structural_snap_grid_m} vs min_edge {self.min_edge_length_m}"
            )
        if self.axis_jitter_tol_m <= 0 or self.window_snap_grid_m <= 0:
            raise ValueError("jitter tol and window grid must be positive")
        # connectivity is a coarser op than identity, and below the arbitration band
        if not (self.axis_jitter_tol_m < self.gap_close_threshold_m
                < self.gap_arbitration_band_m):
            raise ValueError(
                "must hold axis_jitter_tol < gap_close_threshold < gap_arbitration_band; "
                f"got {self.axis_jitter_tol_m} / {self.gap_close_threshold_m} / "
                f"{self.gap_arbitration_band_m}"
            )


@lru_cache(maxsize=8)
def _load_cached(path_str: str) -> CoreTolerances:
    raw = OmegaConf.load(path_str)
    data = OmegaConf.to_container(raw, resolve=True)
    assert isinstance(data, dict), "correction.yaml must be a mapping"
    c = data.get("correction", data)  # tolerate a flat layout too
    tol = CoreTolerances(
        axis_jitter_tol_m=float(c["axis_jitter_tol_m"]),
        structural_snap_grid_m=float(c["structural_snap_grid_m"]),
        min_edge_length_m=float(c["min_edge_length_m"]),
        output_precision_m=float(c["output_precision_m"]),
        window_snap_grid_m=float(c["window_snap_grid_m"]),
        window_clamp_to_parent=bool(c.get("window_clamp_to_parent", True)),
        gap_close_threshold_m=float(c["gap_close_threshold_m"]),
        gap_arbitration_band_m=float(c["gap_arbitration_band_m"]),
    )
    tol.validate()
    return tol


def load_core_tolerances() -> CoreTolerances:
    """Load the active deterministic-core tolerances (cached per resolved path)."""
    return _load_cached(str(resolve_correction_config_path()))
