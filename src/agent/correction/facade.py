"""Facade image-local → world translation (M2a / S1).

P1b puts world placement squarely in 1_correction: 0_reading emits only
image-local facade orientation (``view_facade`` / ``local_x_positive`` /
``mirrored``); this module derives the **world** frame (axis, sign, base plane)
from the authoritative facade name + the reconciled footprint + the z-stack, and
translates an along-facade image-local coordinate into a world coordinate.

The world frame uses the standard architectural elevation convention — looking at
a facade *from outside*:

  facade  wall plane           along-facade local-x → world      outward normal
  ──────  ───────────────────  ───────────────────────────────  ──────────────
  South   y = footprint_y_min  west→east  (+x)                   −y
  North   y = footprint_y_max  east→west  (−x)                   +y
  East    x = footprint_x_max  north→south (−y)                  +x
  West    x = footprint_x_min  south→north (+y)                  −x

``mirrored=true`` flips the sign (the drawing is reversed left-for-right). Sign is
NOT taken from a VLM self-declaration: it comes from the convention + the mirror
flag, and the cross-image reconcile + window-on-wall checks (validator/checks/
correction.py) catch a wrong sign downstream.
"""

from __future__ import annotations

from dataclasses import dataclass

# Standard convention: (world_axis, base_plane_side, sign) when NOT mirrored.
# base_plane_side picks which footprint extreme is the wall plane.
_CONVENTION = {
    "South": ("x", "y_min", +1),
    "North": ("x", "y_max", -1),
    "East": ("y", "x_max", -1),
    "West": ("y", "x_min", +1),
}

# Outward normal (x, y) per facade.
FACADE_NORMAL = {
    "South": (0.0, -1.0),
    "North": (0.0, 1.0),
    "East": (1.0, 0.0),
    "West": (-1.0, 0.0),
}


@dataclass(frozen=True)
class FacadeWorldFrame:
    """Deterministic world frame for one facade, derived from image-local data."""

    facade: str
    world_axis: str          # "x" or "y" — the along-facade world axis
    sign: int                # +1 / -1 — image-left→right maps to this world dir
    base_world: float        # the constant world coordinate of the wall plane
    along_origin: float      # world coord that image-local-x = 0 maps to
    normal: tuple[float, float]

    def to_world_along(self, local_x: float) -> float:
        """Translate an image-local along-facade x to a world coordinate."""
        return self.along_origin + self.sign * local_x


def _is_mirrored(mirrored) -> bool:
    if isinstance(mirrored, bool):
        return mirrored
    return str(mirrored).lower() == "true"


def derive_facade_frame(
    *,
    view_facade: str,
    footprint_x: list[float],
    footprint_y: list[float],
    mirrored="false",
    local_x_positive: str = "image_left_to_right",
) -> FacadeWorldFrame:
    """Derive the world frame for an elevation from image-local orientation +
    the reconciled footprint. Raises on an unknown facade."""
    if view_facade not in _CONVENTION:
        raise ValueError(f"unknown view_facade '{view_facade}'")
    axis, base_side, base_sign = _CONVENTION[view_facade]
    xmin, xmax = min(footprint_x), max(footprint_x)
    ymin, ymax = min(footprint_y), max(footprint_y)

    base_world = {
        "x_min": xmin, "x_max": xmax, "y_min": ymin, "y_max": ymax,
    }[base_side]

    sign = base_sign
    # A right-to-left local convention is equivalent to a mirror.
    if local_x_positive == "image_right_to_left":
        sign = -sign
    if _is_mirrored(mirrored):
        sign = -sign

    # The along-facade extent of the building in the world axis.
    lo, hi = (xmin, xmax) if axis == "x" else (ymin, ymax)
    # image-local x=0 maps to the world extreme the along-facade direction starts
    # from: +sign starts at lo, −sign starts at hi.
    along_origin = lo if sign > 0 else hi

    return FacadeWorldFrame(
        facade=view_facade,
        world_axis=axis,
        sign=sign,
        base_world=base_world,
        along_origin=along_origin,
        normal=FACADE_NORMAL[view_facade],
    )
