"""Two-end space contracts for 2-D affine transforms (B4-(1)).

Why this module exists
----------------------
``gt_manifest.Affine2D`` is six bare floats plus a non-singularity check.  The
*same* type, and in two cases the *same field name*, carries three different
domain/codomain pairs:

===================================  ==============================  ==========================
field                                 owner                           domain -> codomain
===================================  ==============================  ==========================
``pixel_to_source_m``                 ``RasterOverlayIntentV3`` /     ``pixel -> source_metre``
                                      ``RasterOverlayBindingV1``
``world_from_source_m``               ``PlanViewIntentV1``            ``dxf_native -> world_metre``
``world_from_source_m``               ``PlanViewBindingV1``           ``source_metre -> world_metre``
===================================  ==============================  ==========================

The last two differ by exactly one factor of ``metres_per_unit`` (0.001 for
both sm24 and sm25), i.e. **1000x**, and until this module existed the only
thing keeping them apart was a prose comment in ``tarch_normalize._build_manifest``
plus one hand-written division.  Verified on the real signed sm24 anchor:
the request affine is ``m00 = m11 = 0.001`` and the manifest affine is
``m00 = m11 = 1.0`` with byte-identical translations.

The contract is read through :func:`affine_spaces`, which accepts two carriers:

* **wire fields** (``domain_space`` / ``codomain_space``) for types whose two
  ends genuinely vary by call site -- ``gt_manifest.Affine2D``;
* **class-level declaration** (``DOMAIN_SPACE`` / ``CODOMAIN_SPACE`` class
  attributes) for types whose two ends are a single compile-time constant --
  ``score_schema.Affine2DV1``, which is built at exactly one site and applied
  at exactly one site, always ``reading_plan_local_metre -> world_metre``.
  Declaring those as class attributes keeps them out of ``model_dump`` and so
  leaves ``PlanFrameCertificateV1.preimage_sha256`` byte-identical.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, get_args

#: Every space a 2-D affine in this repo may start or end in.
AffineSpace = Literal[
    "pixel",
    "dxf_native",
    "source_metre",
    "world_metre",
    "reading_plan_local_metre",
]

AFFINE_SPACES: tuple[str, ...] = get_args(AffineSpace)

#: Keys the wire carrier uses.  Named once so the hash-stripping helper and the
#: models cannot drift apart.
AFFINE_SPACE_KEYS: tuple[str, str] = ("domain_space", "codomain_space")


class AffineSpaceError(ValueError):
    """Base for every two-end space contract failure."""


class AffineSpaceUndeclared(AffineSpaceError):
    """The affine carries neither wire fields nor a class-level declaration."""


class AffineSpaceMismatch(AffineSpaceError):
    """The affine's declared two ends are not the ones the call site requires."""


def _coerce_space(value: object, *, what: str) -> str:
    if not isinstance(value, str) or value not in AFFINE_SPACES:
        raise AffineSpaceError(f"{what} is not a known affine space: {value!r}")
    return value


def affine_spaces(affine: Any) -> tuple[str, str]:
    """Return ``(domain_space, codomain_space)`` for *affine*.

    Wire fields win when both are populated; otherwise the class-level
    declaration is used.  An affine that declares neither raises
    :class:`AffineSpaceUndeclared` -- silence is never read as "any space".
    """
    domain = getattr(affine, "domain_space", None)
    codomain = getattr(affine, "codomain_space", None)
    if domain is None or codomain is None:
        domain = getattr(type(affine), "DOMAIN_SPACE", None)
        codomain = getattr(type(affine), "CODOMAIN_SPACE", None)
    if domain is None or codomain is None:
        raise AffineSpaceUndeclared(
            f"{type(affine).__name__} declares no domain/codomain space; "
            "bind it at the owning model before use"
        )
    return (
        _coerce_space(domain, what="domain_space"),
        _coerce_space(codomain, what="codomain_space"),
    )


def require_affine_spaces(
    affine: Any,
    *,
    domain: str,
    codomain: str,
    context: str = "affine",
) -> Any:
    """Fail loudly unless *affine* declares exactly ``domain -> codomain``."""
    _coerce_space(domain, what="required domain")
    _coerce_space(codomain, what="required codomain")
    actual_domain, actual_codomain = affine_spaces(affine)
    if (actual_domain, actual_codomain) != (domain, codomain):
        raise AffineSpaceMismatch(
            f"{context}: requires {domain} -> {codomain} but the affine declares "
            f"{actual_domain} -> {actual_codomain}"
        )
    return affine


def affine_coefficients(affine: Any) -> tuple[float, float, float, float, float, float]:
    """Read ``(xx, xy, x0, yx, yy, y0)`` from either coefficient naming."""
    if hasattr(affine, "m00"):
        return (
            float(affine.m00), float(affine.m01), float(affine.m02),
            float(affine.m10), float(affine.m11), float(affine.m12),
        )
    if hasattr(affine, "xx"):
        return (
            float(affine.xx), float(affine.xy), float(affine.x0),
            float(affine.yx), float(affine.yy), float(affine.y0),
        )
    raise AffineSpaceError(
        f"{type(affine).__name__} carries no recognised affine coefficients"
    )


@dataclass(frozen=True)
class ComposedAffine:
    """The result of :func:`compose_affine`.

    Deliberately not one of the wire models: composition crosses model
    families, so nothing here should pick a home class (and so nothing here can
    accidentally be written into a hash-bound payload).
    """

    xx: float
    xy: float
    x0: float
    yx: float
    yy: float
    y0: float
    domain_space: str
    codomain_space: str

    def apply(self, point: tuple[float, float]) -> tuple[float, float]:
        return (
            self.xx * point[0] + self.xy * point[1] + self.x0,
            self.yx * point[0] + self.yy * point[1] + self.y0,
        )


def compose_affine(left: Any, right: Any, *, context: str = "compose_affine") -> ComposedAffine:
    """Compose ``left`` then ``right`` (i.e. the map ``right . left``).

    Reads left-to-right in space terms: composing ``pixel -> source_metre`` with
    ``source_metre -> world_metre`` yields ``pixel -> world_metre``.  When
    ``left``'s codomain is not ``right``'s domain the call raises
    :class:`AffineSpaceMismatch` -- the whole point of the helper.
    """
    left_domain, left_codomain = affine_spaces(left)
    right_domain, right_codomain = affine_spaces(right)
    if left_codomain != right_domain:
        raise AffineSpaceMismatch(
            f"{context}: cannot chain {left_domain} -> {left_codomain} into "
            f"{right_domain} -> {right_codomain} ({left_codomain} != {right_domain})"
        )
    a_xx, a_xy, a_x0, a_yx, a_yy, a_y0 = affine_coefficients(left)
    b_xx, b_xy, b_x0, b_yx, b_yy, b_y0 = affine_coefficients(right)
    return ComposedAffine(
        xx=b_xx * a_xx + b_xy * a_yx,
        xy=b_xx * a_xy + b_xy * a_yy,
        x0=b_xx * a_x0 + b_xy * a_y0 + b_x0,
        yx=b_yx * a_xx + b_yy * a_yx,
        yy=b_yx * a_xy + b_yy * a_yy,
        y0=b_yx * a_x0 + b_yy * a_y0 + b_y0,
        domain_space=left_domain,
        codomain_space=right_codomain,
    )


def strip_affine_space_keys(value: Any) -> Any:
    """Recursively drop the space-contract keys from a JSON-ready payload.

    Used by the canonical hash preimages so that adding the contract does not
    invalidate already-signed requests/manifests.  See the migration note on
    ``compute_request_sha256`` / ``canonical_manifest_payload``.
    """
    if isinstance(value, dict):
        return {
            key: strip_affine_space_keys(item)
            for key, item in value.items()
            if key not in AFFINE_SPACE_KEYS
        }
    if isinstance(value, list):
        return [strip_affine_space_keys(item) for item in value]
    return value


def bind_affine_spaces(model: Any, field: str, *, domain: str, codomain: str) -> None:
    """Stamp (or verify) the two-end spaces of ``model.<field>`` in place.

    Called from the owning model's ``model_validator``: the owner is the only
    place that knows which pair of spaces its affine field connects.

    * undeclared affine -> stamped with ``domain -> codomain``;
    * already declared and matching -> left alone;
    * already declared and *different* -> :class:`AffineSpaceMismatch`.

    The third branch is the one with teeth: a manifest ``world_from_source_m``
    (``source_metre -> world_metre``) handed to ``PlanViewIntentV1`` (which needs
    ``dxf_native -> world_metre``) is rejected instead of being silently used
    1000x off.
    """
    _coerce_space(domain, what="bound domain")
    _coerce_space(codomain, what="bound codomain")
    affine = getattr(model, field)
    declared = (
        getattr(affine, "domain_space", None),
        getattr(affine, "codomain_space", None),
    )
    if declared == (None, None):
        object.__setattr__(
            model,
            field,
            affine.model_copy(update={"domain_space": domain, "codomain_space": codomain}),
        )
        return
    if declared != (domain, codomain):
        raise AffineSpaceMismatch(
            f"{type(model).__name__}.{field} requires {domain} -> {codomain} but the "
            f"affine declares {declared[0]} -> {declared[1]}"
        )


__all__ = [
    "AFFINE_SPACES",
    "AFFINE_SPACE_KEYS",
    "AffineSpace",
    "AffineSpaceError",
    "AffineSpaceMismatch",
    "AffineSpaceUndeclared",
    "ComposedAffine",
    "affine_coefficients",
    "affine_spaces",
    "bind_affine_spaces",
    "compose_affine",
    "require_affine_spaces",
    "strip_affine_space_keys",
]
