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
  East    x = footprint_x_max  south→north (+y)                  +x
  West    x = footprint_x_min  north→south (−y)                  −x

``mirrored=true`` flips the sign (the drawing is reversed left-for-right). Sign is
NOT taken from a VLM self-declaration: it comes from the convention + the mirror
flag, and the cross-image reconcile + window-on-wall checks (validator/checks/
correction.py) catch a wrong sign downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FacadeFamily = Literal["North", "South", "East", "West"]

# Standard convention: (world_axis, base_plane_side, sign) when NOT mirrored.
# base_plane_side picks which footprint extreme is the wall plane.
_CONVENTION = {
    "South": ("x", "y_min", +1),
    "North": ("x", "y_max", -1),
    "East": ("y", "x_max", +1),
    "West": ("y", "x_min", -1),
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


# ---------------------------------------------------------------------------
# C2 Vg/Va frame split (proposals/c2_vg_detail_spec.md §3.2).
#
# `FacadeWorldFrame`/`derive_facade_frame` above stay a legacy compatibility
# wrapper for the existing rectangular cross-check only: it conflates a view's
# local->world sign with a single bbox-extreme wall plane, which cannot
# express a concave multi-segment facade. Vg/Va new code must use the two
# frames below instead and must not import the aggregate legacy type.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ViewProjectionFrame:
    """One elevation view's local-along -> world-along projection only.

    One instance per view. It owns *only* the mapping from an image-local
    along-facade x to a world coordinate — no wall plane, segment id, or
    visibility (that is `FacadeSegmentFrame`'s job). A view is not one wall
    plane: several `FacadeSegmentFrame`s at different depths may share one
    `ViewProjectionFrame`.
    """

    facade_family: FacadeFamily
    world_axis: Literal["x", "y"]
    sign: Literal[-1, 1]
    along_origin: float
    mirrored: bool
    local_x_positive: Literal["image_left_to_right", "image_right_to_left"]

    def to_world_along(self, local_x: float) -> float:
        return self.along_origin + self.sign * local_x


@dataclass(frozen=True)
class FacadeSegmentFrame:
    """One boundary-ring candidate edge's world geometry, pre-visibility.

    One instance per candidate edge (before the Vg skyline decides what part
    of it is visible). It owns *only* world geometry — no local image, mirror,
    manifest, or claim data (that is `ViewProjectionFrame`'s / Va's job).
    """

    facade_family: FacadeFamily
    p1: tuple[float, float]
    p2: tuple[float, float]
    base_world: float
    outward_normal: tuple[Literal[-1, 0, 1], Literal[-1, 0, 1]]
    world_along_interval: tuple[float, float]
    depth: float


def derive_view_projection_frame(
    *,
    vertices,
    facade_family: FacadeFamily,
    mirrored: bool = False,
    local_x_positive: Literal["image_left_to_right", "image_right_to_left"] = "image_left_to_right",
) -> ViewProjectionFrame:
    """Derive one elevation view's local-along -> world-along projection.

    `along_lo/along_hi` come only from `vertices`' extent on the family's
    world axis (§3.1); this builder does not read a manifest or reading
    artifact — direction/mirror validity is the caller's job. It only accepts
    a *resolved* bool `mirrored`; an unresolved ("unknown") mirror flag must
    fail closed before calling this, not be silently treated as `False`.

    The two flip bits (`mirrored` and a right-to-left local convention)
    combine by XOR (v2 §3.2): both non-default at once cancels out and
    restores the standard `base_sign`.
    """
    if facade_family not in _CONVENTION:
        raise ValueError(f"unknown facade_family {facade_family!r}")
    if not isinstance(mirrored, bool):
        raise ValueError(
            "derive_view_projection_frame requires a resolved bool 'mirrored' "
            "flag; an unresolved value must fail closed before this call"
        )
    if local_x_positive not in ("image_left_to_right", "image_right_to_left"):
        raise ValueError(f"unknown local_x_positive {local_x_positive!r}")

    axis, _base_side, base_sign = _CONVENTION[facade_family]
    xs = [float(p[0]) for p in vertices]
    ys = [float(p[1]) for p in vertices]
    lo, hi = (min(xs), max(xs)) if axis == "x" else (min(ys), max(ys))

    effective_flip = mirrored ^ (local_x_positive == "image_right_to_left")
    sign = -base_sign if effective_flip else base_sign
    along_origin = lo if sign > 0 else hi

    return ViewProjectionFrame(
        facade_family=facade_family,
        world_axis=axis,
        sign=sign,
        along_origin=along_origin,
        mirrored=mirrored,
        local_x_positive=local_x_positive,
    )
