"""B4-(1): the two-end space contract on 2-D affines.

Every fixture below is a REAL signed anchor -- no synthetic affine is used for
the discriminating assertions.  The hazard being locked is concrete: the request
and the manifest both carry a field literally named ``world_from_source_m`` of
the same type ``Affine2D``, and on every anchor they differ by exactly
``metres_per_unit`` (1000x).  Before this contract the only thing separating
them was a prose comment in ``tarch_normalize._build_manifest``.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from src.agent.judge.affine_space import (
    AffineSpaceMismatch,
    AffineSpaceUndeclared,
    affine_spaces,
    bind_affine_spaces,
    compose_affine,
    strip_affine_space_keys,
)
from src.agent.judge.gt_manifest import (
    Affine2D,
    GtExtractionManifestV1,
    MANIFEST_VERSIONS_WITHOUT_SPACE_BINDING,
    _normalise,
    compute_manifest_sha256,
)
from src.agent.judge.reading_typed_adapter import _plan_frame, apply_affine_2d
from src.agent.judge.score_schema import Affine2DV1
from src.agent.judge.tarch_converter_schema import (
    REQUEST_VERSIONS_WITHOUT_SPACE_BINDING,
    TarchConversionRequestV1,
    compute_request_sha256,
)

GT_SOURCES = Path(__file__).resolve().parents[1] / "case_tests" / "test_baseline" / "gt_sources"

#: The signed inventory this file locks.  Listed explicitly rather than globbed
#: so a fixture that disappears turns the suite RED instead of quietly reducing
#: the lock to nothing.  sm21_anchor ships only ``source.dxf`` -- it has neither
#: a request nor a manifest, so there is no signature of its to preserve.
SIGNED_REQUESTS = ("sm25-L_anchor", "sm24_anchor")
SIGNED_MANIFESTS = ("sm24_anchor",)
UNSIGNED_ANCHORS = ("sm21_anchor",)


def _load_request(case: str) -> tuple[dict, TarchConversionRequestV1]:
    raw = json.loads((GT_SOURCES / case / "request.json").read_text(encoding="utf-8"))
    return raw, TarchConversionRequestV1.model_validate(copy.deepcopy(raw))


def _load_manifest(case: str) -> tuple[dict, GtExtractionManifestV1]:
    raw = json.loads((GT_SOURCES / case / "manifest.json").read_text(encoding="utf-8"))
    return raw, GtExtractionManifestV1.model_validate(copy.deepcopy(raw))


def _plan_view_binding(manifest: GtExtractionManifestV1):
    return next(view for view in manifest.views if view.kind == "plan")


# --------------------------------------------------------------------------- #
# Acceptance 1 -- already-signed answers keep their hash byte-for-byte
# --------------------------------------------------------------------------- #
def test_signed_fixture_inventory_is_what_this_file_claims():
    for case in SIGNED_REQUESTS:
        assert (GT_SOURCES / case / "request.json").is_file(), case
    for case in SIGNED_MANIFESTS:
        assert (GT_SOURCES / case / "manifest.json").is_file(), case
    for case in UNSIGNED_ANCHORS:
        assert not (GT_SOURCES / case / "request.json").exists(), case
        assert not (GT_SOURCES / case / "manifest.json").exists(), case


@pytest.mark.parametrize("case", SIGNED_REQUESTS)
def test_signed_request_hash_survives_the_space_contract(case):
    raw, request = _load_request(case)
    assert compute_request_sha256(request) == raw["request_sha256"]


@pytest.mark.parametrize("case", SIGNED_MANIFESTS)
def test_signed_manifest_hash_survives_the_space_contract(case):
    raw, manifest = _load_manifest(case)
    assert compute_manifest_sha256(manifest) == raw["manifest_sha256"]


@pytest.mark.parametrize("case", SIGNED_REQUESTS)
def test_stripping_is_load_bearing_not_vacuous(case):
    """The preceding two tests must not be green because nothing was stamped.

    Hashing the payload WITHOUT the migration strip has to produce a different
    digest -- otherwise the space contract never reached the wire and 'signature
    preserved' would mean nothing.
    """
    _, request = _load_request(case)
    payload = request.model_dump(mode="json")
    payload["request_sha256"] = "0" * 64
    stripped = strip_affine_space_keys(payload)
    assert stripped != payload, "no affine on this request carries a space contract"
    unstripped_digest = hashlib.sha256(
        json.dumps(_normalise(payload), sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    ).hexdigest()
    assert unstripped_digest != compute_request_sha256(request)


def test_stripping_is_load_bearing_for_the_manifest_too():
    _, manifest = _load_manifest("sm24_anchor")
    payload = manifest.model_dump(mode="json")
    payload["manifest_sha256"] = "0" * 64
    assert strip_affine_space_keys(payload) != payload


def test_version_exclusion_sets_cover_every_legal_version():
    """Tripwire: adding a request/manifest version must force a signing decision.

    While a version sits in these sets its affine spaces are NOT part of the
    signature -- the contract protects code paths, not signed artifacts.
    """
    request_versions = set(
        get_args(TarchConversionRequestV1.model_fields["request_version"].annotation)
    )
    assert request_versions <= REQUEST_VERSIONS_WITHOUT_SPACE_BINDING
    manifest_versions = set(
        get_args(GtExtractionManifestV1.model_fields["manifest_version"].annotation)
    )
    assert manifest_versions <= MANIFEST_VERSIONS_WITHOUT_SPACE_BINDING


# --------------------------------------------------------------------------- #
# Acceptance 2 -- the type gate has teeth, on the real 1000x pair
# --------------------------------------------------------------------------- #
def test_the_two_same_named_affines_really_are_1000x_apart():
    """Prove the fixture below is the real hazard, not a manufactured one."""
    raw_request, request = _load_request("sm24_anchor")
    _, manifest = _load_manifest("sm24_anchor")
    intent = next(view for view in request.plan_views if view.id == "plan-F1")
    binding = _plan_view_binding(manifest)
    assert binding.id == intent.id
    mpu = request.metres_per_unit
    assert mpu == manifest.metres_per_unit == 0.001
    request_affine = intent.world_from_source_m
    manifest_affine = binding.world_from_source_m
    for left, right in (("m00", "m00"), ("m01", "m01"), ("m10", "m10"), ("m11", "m11")):
        assert getattr(manifest_affine, right) == pytest.approx(
            getattr(request_affine, left) / mpu, rel=1e-12, abs=1e-15)
    # translations are already world-metres on both sides -> byte-identical
    assert (manifest_affine.m02, manifest_affine.m12) == (request_affine.m02, request_affine.m12)
    # ... and the two ends they declare are different
    assert affine_spaces(request_affine) == ("dxf_native", "world_metre")
    assert affine_spaces(manifest_affine) == ("source_metre", "world_metre")


def test_swapping_the_two_affines_is_numerically_catastrophic_and_silent_to_the_old_checks():
    """The damage the contract exists to stop, measured on the real anchor."""
    _, request = _load_request("sm24_anchor")
    _, manifest = _load_manifest("sm24_anchor")
    intent = next(view for view in request.plan_views if view.id == "plan-F1")
    manifest_affine = _plan_view_binding(manifest).world_from_source_m
    native = (intent.clip_box_dxf.xmin, intent.clip_box_dxf.ymin)

    def apply(affine, point):
        return (affine.m00 * point[0] + affine.m01 * point[1] + affine.m02,
                affine.m10 * point[0] + affine.m11 * point[1] + affine.m12)

    correct = apply(intent.world_from_source_m, native)
    wrong = apply(manifest_affine, native)
    assert abs(wrong[0] - correct[0]) > 12_000.0  # metres
    # The pre-existing checks (finite, non-singular) cannot see any of this:
    coefficients = {key: getattr(manifest_affine, key)
                    for key in ("m00", "m01", "m02", "m10", "m11", "m12")}
    assert Affine2D(**coefficients).m00 == 1.0


def test_manifest_affine_is_rejected_where_a_native_affine_is_required():
    raw_request, _ = _load_request("sm24_anchor")
    _, manifest = _load_manifest("sm24_anchor")
    manifest_affine = _plan_view_binding(manifest).world_from_source_m

    payload = copy.deepcopy(raw_request)
    plan_view = next(view for view in payload["plan_views"] if view["id"] == "plan-F1")
    plan_view["world_from_source_m"] = manifest_affine.model_dump(mode="json")

    with pytest.raises(ValidationError) as excinfo:
        TarchConversionRequestV1.model_validate(payload)
    message = str(excinfo.value)
    assert "dxf_native" in message and "source_metre" in message


def test_request_affine_is_rejected_where_a_source_metre_affine_is_required():
    _, request = _load_request("sm24_anchor")
    raw_manifest, _ = _load_manifest("sm24_anchor")
    intent = next(view for view in request.plan_views if view.id == "plan-F1")

    payload = copy.deepcopy(raw_manifest)
    view = next(item for item in payload["views"] if item["kind"] == "plan")
    view["world_from_source_m"] = intent.world_from_source_m.model_dump(mode="json")

    with pytest.raises(ValidationError) as excinfo:
        GtExtractionManifestV1.model_validate(payload)
    message = str(excinfo.value)
    assert "source_metre" in message and "dxf_native" in message


def test_bind_affine_spaces_raises_the_contract_error_directly():
    _, manifest = _load_manifest("sm24_anchor")
    binding = _plan_view_binding(manifest)
    with pytest.raises(AffineSpaceMismatch):
        bind_affine_spaces(binding, "world_from_source_m",
                           domain="dxf_native", codomain="world_metre")


def test_undeclared_affine_is_an_error_not_a_wildcard():
    """Absence must not be readable as 'any space'."""
    loose = Affine2D(m00=1.0, m01=0.0, m02=0.0, m10=0.0, m11=1.0, m12=0.0)
    with pytest.raises(AffineSpaceUndeclared):
        affine_spaces(loose)


def test_half_declared_space_contract_is_refused():
    with pytest.raises(ValidationError):
        Affine2D(m00=1.0, m01=0.0, m02=0.0, m10=0.0, m11=1.0, m12=0.0,
                 domain_space="pixel")


# --------------------------------------------------------------------------- #
# R2 -- compose_affine checks the joint
# --------------------------------------------------------------------------- #
def test_compose_affine_chains_pixel_through_source_metre_to_world():
    _, request = _load_request("sm25-L_anchor")
    overlay = next(item for item in request.raster_overlays if item.view_id == "plan-F1")
    intent = next(view for view in request.plan_views if view.id == "plan-F1")
    mpu = request.metres_per_unit
    source_to_world = Affine2D(
        m00=intent.world_from_source_m.m00 / mpu, m01=intent.world_from_source_m.m01 / mpu,
        m02=intent.world_from_source_m.m02,
        m10=intent.world_from_source_m.m10 / mpu, m11=intent.world_from_source_m.m11 / mpu,
        m12=intent.world_from_source_m.m12,
        domain_space="source_metre", codomain_space="world_metre")

    chained = compose_affine(overlay.pixel_to_source_m, source_to_world)
    assert (chained.domain_space, chained.codomain_space) == ("pixel", "world_metre")

    # numerically identical to applying the two steps by hand
    pixel = (137.0, 902.0)
    step = (overlay.pixel_to_source_m.m00 * pixel[0] + overlay.pixel_to_source_m.m01 * pixel[1]
            + overlay.pixel_to_source_m.m02,
            overlay.pixel_to_source_m.m10 * pixel[0] + overlay.pixel_to_source_m.m11 * pixel[1]
            + overlay.pixel_to_source_m.m12)
    by_hand = (source_to_world.m00 * step[0] + source_to_world.m01 * step[1] + source_to_world.m02,
               source_to_world.m10 * step[0] + source_to_world.m11 * step[1] + source_to_world.m12)
    assert chained.apply(pixel) == pytest.approx(by_hand, rel=1e-12, abs=1e-12)


def test_compose_affine_refuses_a_broken_joint():
    _, request = _load_request("sm25-L_anchor")
    overlay = next(item for item in request.raster_overlays if item.view_id == "plan-F1")
    intent = next(view for view in request.plan_views if view.id == "plan-F1")
    # pixel -> source_metre  followed by  dxf_native -> world_metre
    with pytest.raises(AffineSpaceMismatch) as excinfo:
        compose_affine(overlay.pixel_to_source_m, intent.world_from_source_m)
    assert "source_metre" in str(excinfo.value) and "dxf_native" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Acceptance 3 -- Affine2DV1 is covered too
# --------------------------------------------------------------------------- #
def test_affine2dv1_declares_its_two_ends():
    frame = _plan_frame(input_id="1f_view", floor_id="F1", x0=0.0, y0=0.0)
    assert isinstance(frame.affine, Affine2DV1)
    assert affine_spaces(frame.affine) == ("reading_plan_local_metre", "world_metre")


def test_affine2dv1_spaces_stay_off_the_wire():
    """Declared as class attributes, so no persisted certificate hash moves.

    ``preimage_sha256`` is stamped onto every plan observation as
    ``transform_sha256`` and persisted in every ``score_vs_gt.json``; the literal
    below is the value already sitting in
    ``case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0``.
    """
    assert "domain_space" not in Affine2DV1.model_fields
    assert "codomain_space" not in Affine2DV1.model_fields
    frame = _plan_frame(input_id="1f_view", floor_id="F1", x0=0.0, y0=0.0)
    assert frame.preimage_sha256 == (
        "05a29dc35ffb4d93eaedf9356a69de81a86909988d0f8ed901d12e3af6a32c7e")


def test_affine2dv1_participates_in_the_same_gate():
    _, manifest = _load_manifest("sm24_anchor")
    manifest_affine = _plan_view_binding(manifest).world_from_source_m
    frame = _plan_frame(input_id="1f_view", floor_id="F1", x0=0.0, y0=0.0)
    # world_metre -> reading_plan_local_metre is not a joint
    with pytest.raises(AffineSpaceMismatch):
        compose_affine(manifest_affine, frame.affine)
    # ... and the reading application site refuses a foreign affine by name
    with pytest.raises(AffineSpaceMismatch):
        apply_affine_2d(manifest_affine, (1.0, 2.0))


def test_apply_affine_2d_still_transforms_the_declared_pair():
    frame = _plan_frame(input_id="1f_view", floor_id="F1", x0=3.0, y0=-4.0)
    assert apply_affine_2d(frame.affine, (1.0, 2.0)) == (4.0, -2.0)
