"""Single source for CV toolbox recipe constants."""

from __future__ import annotations

from copy import deepcopy


CLEAN_VECTOR_V1 = {
    "recipe_id": "clean_vector_v1",
    "applicability": "clean_vector",
    # Seeded from the sm21 forensics recipe: R ~= G ~= B and 60 < v < 230.
    # The exact inclusive bounds follow the adjudicated mask contract.
    "gray_lo": 60,
    "gray_hi": 230,
    "rgb_tol": 8,
    # Low enough for full-image sm21 plan smoke, high enough to suppress small
    # gray labels/ticks in synthetic fixtures after orthogonal normalization.
    "prominence": 0.04,
    "min_peak_distance_px": 6,
    "min_cc_area_px": 20,
    "merge_gap_px": 2,
    "merge_overlap_ratio": 0.5,
    "merge_iou": 0.2,
    "calibration_warn_residual_px": 2.0,
    "calibration_warn_residual_m": 0.05,
}

_RECIPES = {
    "clean_vector_v1": CLEAN_VECTOR_V1,
}


def get_recipe(recipe_id: str = "clean_vector_v1") -> dict:
    """Return a copy of a known deterministic recipe."""

    try:
        return deepcopy(_RECIPES[recipe_id])
    except KeyError as exc:
        known = ", ".join(sorted(_RECIPES))
        raise ValueError(f"unknown CV recipe {recipe_id!r}; known recipes: {known}") from exc
